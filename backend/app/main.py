"""器见千年 API 与持久化重建任务。"""
import io
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from . import config, storage
from .comparison_routes import router as comparison_router
from .morphology_routes import router as morphology_router
from .multiview_routes import router as multiview_router
from .platform_routes import current_user, inspect_image, require_user, router as platform_router
from .providers import ProviderError, provider_status
from .uncertainty import build_report, compute_coarse_shape, make_heatmap_mesh, normalize_mesh, orient_upright, vertex_uncertainty

app = FastAPI(title='器见千年 · 文物学习平台')
app.include_router(comparison_router)
app.include_router(morphology_router)
app.include_router(multiview_router)
app.include_router(platform_router)
(storage.DATA_DIR / 'images').mkdir(exist_ok=True)
app.mount('/media', StaticFiles(directory=storage.DATA_DIR / 'images'), name='media')
app.add_middleware(CORSMiddleware, allow_origins=[
                       'http://localhost:5173','http://127.0.0.1:5173',
                       'http://localhost','https://localhost','capacitor://localhost'],
                   allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
_worker = threading.Semaphore(1)
_file_signing_key = secrets.token_bytes(32)
MODEL_LOADED = False


def _file_ticket(task_id, filename, expires):
    message = f'{task_id}/{filename}/{expires}'.encode()
    return hmac.new(_file_signing_key,message,hashlib.sha256).hexdigest()


def _valid_file_ticket(task_id, filename, ticket):
    try:
        expires_text,signature = ticket.split('.',1)
        expires = int(expires_text)
    except (AttributeError,ValueError):
        return False
    return expires >= int(time.time()) and hmac.compare_digest(
        signature,_file_ticket(task_id,filename,expires))


def _recognize_for_reconstruction(image_bytes):
    """Use cloud recognition when available without making it a rebuild prerequisite."""
    try:
        return inspect_image(image_bytes), None
    except ProviderError as exc:
        return {
            'category': '未知',
            'type': '上传器物',
            'features': [],
            'decorationFeatures': [],
            'note': '未进行云端器型识别；三维模型由本地重建引擎生成。',
            'model': 'local-fallback',
        }, str(exc)[:200]


def owned_task(task_id, user):
    task = storage.reconstruction(task_id)
    if not task or task['owner_id'] != user['id']: raise HTTPException(404,'任务不存在')
    return task


def update(task_id, **values):
    task = storage.reconstruction(task_id)
    if task['status'] == 'cancelled': raise RuntimeError('任务已取消')
    owner = task.pop('owner_id'); task.update(values)
    storage.save_reconstruction(task_id,task,owner)


def _run_task(task_id, image_bytes, engine=None):
    global MODEL_LOADED
    started = time.time()
    try:
        with _worker:
            update(task_id,stage='器物识别',progress=8)
            recognition, recognition_warning = _recognize_for_reconstruction(image_bytes)
            recognition_update = dict(recognition=recognition,stage='加载三维模型',progress=20)
            if recognition_warning:
                recognition_update['recognitionWarning'] = recognition_warning
            update(task_id,**recognition_update)
            from .reconstruction_engine import reconstruct
            mesh, engine = reconstruct(image_bytes,lambda stage,value: update(task_id,stage=stage,progress=value),engine=engine)
            MODEL_LOADED = True
            update(task_id,stage='校正网格与生成热力图',progress=82)
            mesh = normalize_mesh(orient_upright(mesh),config.DISPLAY_HEIGHT)
            uncertainty = vertex_uncertainty(mesh)
            heatmap = make_heatmap_mesh(mesh,uncertainty)
            report=build_report(mesh,uncertainty,(time.time()-started)*1000)
            update(task_id,stage='提取照片轮廓与纹理',progress=86)
            from .photo_surface import PHOTO_SURFACE_VERSION,photo_surface,apply_photo_texture,export_photo_model
            _,atlas,projection=photo_surface(Image.open(io.BytesIO(image_bytes)))
            mesh=apply_photo_texture(mesh,atlas)
            update(task_id,stage='写入完整三维模型',progress=90)
            export_photo_model(mesh,Path(config.OUTPUT_DIR)/f'{task_id}.glb')
            heatmap.export(str(Path(config.OUTPUT_DIR)/f'{task_id}.heatmap.glb'))
            update(task_id,stage='简化浏览网格',progress=93)
            low = mesh.simplify_quadric_decimation(face_count=min(18000,len(mesh.faces)))
            low=apply_photo_texture(low,atlas)
            update(task_id,stage='写入浏览模型',progress=96)
            export_photo_model(low,Path(config.OUTPUT_DIR)/f'{task_id}.preview.glb')
            update(task_id,stage='计算形态参数',progress=98)
            shape = compute_coarse_shape(mesh)
            from .morphology import measure_profile
            params = measure_profile(shape)
            parts = [{'id':key,'name':name,'yMin':a*30,'yMax':b*30,'formDescription':'','history':'','knowledge':''}
                     for key,name,a,b in [('foot','器足',0,.12),('mouth','器口',.92,1),('neck','器颈',.75,.92),('decoration','纹饰区域',.45,.60),('body','器身',.12,.75)]]
            porcelain = dict(id=task_id,name=recognition['type'],dynasty='unknown',dynastyName='年代未定',period='',
                category=recognition['category'],summary=recognition['note'],description=recognition['note'],history='',
                formFeatures=recognition['features'],decorationFeatures=recognition['decorationFeatures'],craftFeatures=[],
                shape=shape,params=params,parts=parts,sources=[],modelMethod=f'{engine.upper()} 单图重建 + 前后镜像纹饰',textureProjection=projection,
                imageUrl=f'/files/{task_id}/image.jpg',modelUrl=f'/files/{task_id}/mesh.glb?v=photo-{PHOTO_SURFACE_VERSION}',
                glaze={'color':'#ede5d3','roughness':.38,'metalness':.05,'clearcoat':.5,'decoration':'plain'})
            update(task_id,status='success',stage='完成',progress=100,porcelain=porcelain,shape=shape,
                   report={**report,'elapsedMs':int((time.time()-started)*1000)},textureProjection=projection,
                   modelUrl=f'/files/{task_id}/mesh.glb?v=photo-{PHOTO_SURFACE_VERSION}',previewUrl=f'/files/{task_id}/preview.glb?v=photo-{PHOTO_SURFACE_VERSION}',
                   heatmapUrl=f'/files/{task_id}/heatmap.glb',note=f'{engine.upper()} 单图重建 · 浏览网格已简化')
    except Exception as exc:
        task = storage.reconstruction(task_id)
        if task and task['status'] != 'cancelled': update(task_id,status='error',error=str(exc)[:600],stage='失败')


@app.on_event('startup')
def startup():
    storage.initialize()
    with storage.connect() as db:
        for row in db.execute('SELECT * FROM reconstructions').fetchall():
            task = json.loads(row['data'])
            if task['status']=='processing':
                task.update(status='error',stage='中断',error='服务重启中断了任务，请重新上传。')
                db.execute('UPDATE reconstructions SET data=? WHERE id=?',(json.dumps(task,ensure_ascii=False),row['id']))
    if os.environ.get('QJQN_PRELOAD_MODELS','true').lower() not in {'0','false','no','off'}:
        from .reconstruction_engine import start_preload
        start_preload()


@app.get('/health')
def health():
    from .reconstruction_engine import status
    from .triposr_engine import selected_device
    engine_status = status()
    model_ready = engine_status.get('triposrModel',{}).get('status') == 'ready'
    return {'ok':True,'modelLoaded':MODEL_LOADED or model_ready,'device':selected_device(),
            'visionOptionalForReconstruction':True,**engine_status,**provider_status()}


@app.post('/api/reconstruct')
async def reconstruct(file: UploadFile=File(...),engine: str=Form(None),user=Depends(require_user)):
    image_bytes = await file.read(12*1024*1024+1)
    if len(image_bytes)>12*1024*1024: raise HTTPException(413,'图片不能超过12MB')
    try:
        image = Image.open(io.BytesIO(image_bytes))
        if image.width*image.height>25_000_000: raise HTTPException(413,'图片像素过大')
        image = image.convert('RGB'); image.thumbnail((1600,1600))
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError): raise HTTPException(422,'无法读取图片') from None
    from .reconstruction_engine import SINGLE_IMAGE_ENGINES
    requested = (engine or '').strip().lower() or None
    if requested and requested not in {'auto',*SINGLE_IMAGE_ENGINES}:
        raise HTTPException(400,'不支持的引擎：'+requested+'，可选 auto、'+'、'.join(SINGLE_IMAGE_ENGINES))
    with storage.connect() as db:
        active = [json.loads(r[0]) for r in db.execute('SELECT data FROM reconstructions WHERE owner_id=?',(user['id'],))]
    if any(x['status']=='processing' for x in active): raise HTTPException(409,'已有重建任务进行中')
    task_id = str(uuid.uuid4())
    output = io.BytesIO(); image.save(output,format='JPEG',quality=90)
    Path(config.OUTPUT_DIR,f'{task_id}.jpg').write_bytes(output.getvalue())
    storage.save_reconstruction(task_id,dict(taskId=task_id,status='processing',stage='等待处理',progress=0,created=time.time(),engine=requested or 'auto'),user['id'])
    threading.Thread(target=_run_task,args=(task_id,output.getvalue(),requested),daemon=True).start()
    return {'taskId':task_id,'status':'processing','engine':requested or 'auto'}


@app.get('/api/task/{task_id}')
def task_status(task_id: str,user=Depends(require_user)):
    task = owned_task(task_id,user)
    return {key:task.get(key) for key in ('taskId','status','stage','progress','error')}


@app.delete('/api/task/{task_id}')
def cancel_task(task_id: str,user=Depends(require_user)):
    task = owned_task(task_id,user)
    if task['status']=='processing': update(task_id,status='cancelled',stage='已取消')
    return {'ok':True}


@app.delete('/api/models/{task_id}')
def delete_task(task_id: str,user=Depends(require_user)):
    """彻底删除我的任务：上传图片、三维模型、浏览网格、热力图和数据库记录。"""
    task = owned_task(task_id,user)
    if task['status']=='processing':
        raise HTTPException(409,'任务进行中，请先取消再删除')
    output_dir = Path(config.OUTPUT_DIR)
    # 精确文件名白名单，避免误删；只在产物目录内操作。
    file_names = [
        f'{task_id}.glb', f'{task_id}.preview.glb',
        f'{task_id}.heatmap.glb', f'{task_id}.jpg',
        f'.{task_id}.building.glb',
    ]
    removed_files = 0
    for name in file_names:
        target = output_dir / name
        if target.is_file():
            target.unlink()
            removed_files += 1
    image_dir = output_dir / f'{task_id}.images'
    if image_dir.is_dir():
        shutil.rmtree(image_dir)
    storage.delete_reconstruction(task_id)
    return {'ok':True,'removedFiles':removed_files}


@app.get('/api/model/{task_id}')
def model(task_id: str,user=Depends(require_user)):
    task = owned_task(task_id,user)
    if task['status']!='success': raise HTTPException(409,task.get('error') or '模型尚未完成')
    return {k:v for k,v in task.items() if k!='owner_id'}


@app.get('/api/models')
def models(user=Depends(require_user)):
    with storage.connect() as db:
        rows = db.execute('SELECT r.*,s.task_id AS saved FROM reconstructions r LEFT JOIN saved_models s ON s.task_id=r.id AND s.user_id=? WHERE r.owner_id=? ORDER BY r.created DESC',(user['id'],user['id'])).fetchall()
    return {'items':[{**json.loads(row['data']),'saved':bool(row['saved'])} for row in rows]}


@app.post('/api/models/{task_id}/save')
def save_model(task_id: str,user=Depends(require_user)):
    task = owned_task(task_id,user)
    if task['status']!='success': raise HTTPException(409,'模型尚未完成')
    with storage.connect() as db: db.execute('INSERT OR IGNORE INTO saved_models VALUES(?,?,?)',(user['id'],task_id,time.time()))
    return {'ok':True}


@app.delete('/api/models/{task_id}/save')
def unsave_model(task_id: str,user=Depends(require_user)):
    owned_task(task_id,user)
    with storage.connect() as db: db.execute('DELETE FROM saved_models WHERE user_id=? AND task_id=?',(user['id'],task_id))
    return {'ok':True}


@app.get('/api/files/access')
def file_access(path: str,user=Depends(require_user)):
    """为原生 WebView 和普通浏览器签发短时、单文件访问地址。"""
    clean_path = urlparse(path).path
    match = re.fullmatch(r'/files/([0-9a-fA-F-]{36})/(mesh\.glb|heatmap\.glb|preview\.glb|image\.jpg)',clean_path)
    if not match: raise HTTPException(422,'文件地址无效')
    task_id,filename = match.groups()
    owned_task(task_id,user)
    expires = int(time.time())+2*60*60
    ticket = f'{expires}.{_file_ticket(task_id,filename,expires)}'
    return {'url':f'/files/{task_id}/{filename}?ticket={ticket}'}


@app.get('/files/{task_id}/{filename}')
def model_file(task_id: str,filename: str,request: Request,ticket: str=''):
    user = current_user(request)
    if user:
        task = owned_task(task_id,user)
    elif _valid_file_ticket(task_id,filename,ticket):
        task = storage.reconstruction(task_id)
        if not task: raise HTTPException(404,'任务不存在')
    else:
        raise HTTPException(401,'请先登录')
    suffix = {'mesh.glb':'.glb','heatmap.glb':'.heatmap.glb','preview.glb':'.preview.glb','image.jpg':'.jpg'}.get(filename)
    if not suffix: raise HTTPException(404,'文件不存在')
    path = Path(config.OUTPUT_DIR,f'{task_id}{suffix}')
    if not path.is_file() or (filename!='image.jpg' and task['status']!='success'): raise HTTPException(404,'文件尚未生成')
    return FileResponse(path,media_type='image/jpeg' if filename=='image.jpg' else 'model/gltf-binary',headers={'Cache-Control':'private, max-age=7200'})


@app.get('/{page:path}',include_in_schema=False)
def frontend(page:str):
    dist=Path(__file__).resolve().parents[2]/'dist'
    target=(dist/page).resolve()
    if not target.is_relative_to(dist.resolve()):raise HTTPException(404,'页面不存在')
    if target.is_file():return FileResponse(target)
    if page.split('/')[0] in ['','library','learning','auth','reconstruction','multiview','timeline','comparison','engine-compare','ai-explain'] and (dist/'index.html').is_file():
        return FileResponse(dist/'index.html')
    raise HTTPException(404,'页面不存在')
