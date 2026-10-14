"""器见千年 API 与持久化重建任务。"""
import io
import json
import threading
import time
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from . import config, storage
from .morphology_routes import router as morphology_router
from .platform_routes import inspect_image, require_user, router as platform_router
from .providers import provider_status
from .uncertainty import build_report, compute_coarse_shape, make_heatmap_mesh, normalize_mesh, orient_upright, vertex_uncertainty

app = FastAPI(title='器见千年 · 文物学习平台')
app.include_router(morphology_router)
app.include_router(platform_router)
(storage.DATA_DIR / 'images').mkdir(exist_ok=True)
app.mount('/media', StaticFiles(directory=storage.DATA_DIR / 'images'), name='media')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],
                   allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
_worker = threading.Semaphore(1)
MODEL_LOADED = False


def owned_task(task_id, user):
    task = storage.reconstruction(task_id)
    if not task or task['owner_id'] != user['id']: raise HTTPException(404,'任务不存在')
    return task


def update(task_id, **values):
    task = storage.reconstruction(task_id)
    if task['status'] == 'cancelled': raise RuntimeError('任务已取消')
    owner = task.pop('owner_id'); task.update(values)
    storage.save_reconstruction(task_id,task,owner)


def _run_task(task_id, image_bytes):
    global MODEL_LOADED
    started = time.time()
    try:
        with _worker:
            update(task_id,stage='器物识别',progress=8)
            recognition = inspect_image(image_bytes)
            update(task_id,recognition=recognition,stage='加载三维模型',progress=20)
            from .triposr_engine import reconstruct
            mesh = reconstruct(image_bytes,lambda stage,value: update(task_id,stage=stage,progress=value))
            MODEL_LOADED = True
            update(task_id,stage='网格与纹理处理',progress=82)
            mesh = normalize_mesh(orient_upright(mesh),config.DISPLAY_HEIGHT)
            uncertainty = vertex_uncertainty(mesh)
            heatmap = make_heatmap_mesh(mesh,uncertainty)
            report=build_report(mesh,uncertainty,(time.time()-started)*1000)
            from .photo_surface import PHOTO_SURFACE_VERSION,photo_surface,apply_photo_texture,export_photo_model
            _,atlas,projection=photo_surface(Image.open(io.BytesIO(image_bytes)))
            mesh=apply_photo_texture(mesh,atlas)
            export_photo_model(mesh,Path(config.OUTPUT_DIR)/f'{task_id}.glb')
            heatmap.export(str(Path(config.OUTPUT_DIR)/f'{task_id}.heatmap.glb'))
            low = mesh.simplify_quadric_decimation(face_count=min(18000,len(mesh.faces)))
            low=apply_photo_texture(low,atlas)
            export_photo_model(low,Path(config.OUTPUT_DIR)/f'{task_id}.preview.glb')
            shape = compute_coarse_shape(mesh)
            from .morphology import measure_profile
            params = measure_profile(shape)
            parts = [{'id':key,'name':name,'yMin':a*30,'yMax':b*30,'formDescription':'','history':'','knowledge':''}
                     for key,name,a,b in [('foot','器足',0,.12),('mouth','器口',.92,1),('neck','器颈',.75,.92),('decoration','纹饰区域',.45,.60),('body','器身',.12,.75)]]
            porcelain = dict(id=task_id,name=recognition['type'],dynasty='unknown',dynastyName='年代未定',period='',
                category=recognition['category'],summary=recognition['note'],description=recognition['note'],history='',
                formFeatures=recognition['features'],decorationFeatures=recognition['decorationFeatures'],craftFeatures=[],
                shape=shape,params=params,parts=parts,sources=[],modelMethod='TripoSR 单图重建 + 前后镜像纹饰',textureProjection=projection,
                imageUrl=f'/files/{task_id}/image.jpg',modelUrl=f'/files/{task_id}/mesh.glb?v=photo-{PHOTO_SURFACE_VERSION}',
                glaze={'color':'#ede5d3','roughness':.38,'metalness':.05,'clearcoat':.5,'decoration':'plain'})
            update(task_id,status='success',stage='完成',progress=100,porcelain=porcelain,shape=shape,
                   report={**report,'elapsedMs':int((time.time()-started)*1000)},textureProjection=projection,
                   modelUrl=f'/files/{task_id}/mesh.glb?v=photo-{PHOTO_SURFACE_VERSION}',previewUrl=f'/files/{task_id}/preview.glb?v=photo-{PHOTO_SURFACE_VERSION}',
                   heatmapUrl=f'/files/{task_id}/heatmap.glb',note='TripoSR 单图重建 · 浏览网格已简化')
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


@app.get('/health')
def health(): return {'ok':True,'modelLoaded':MODEL_LOADED,**provider_status()}


@app.post('/api/reconstruct')
async def reconstruct(file: UploadFile=File(...),user=Depends(require_user)):
    image_bytes = await file.read(12*1024*1024+1)
    if len(image_bytes)>12*1024*1024: raise HTTPException(413,'图片不能超过12MB')
    try:
        image = Image.open(io.BytesIO(image_bytes))
        if image.width*image.height>25_000_000: raise HTTPException(413,'图片像素过大')
        image = image.convert('RGB'); image.thumbnail((1600,1600))
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError): raise HTTPException(422,'无法读取图片') from None
    with storage.connect() as db:
        active = [json.loads(r[0]) for r in db.execute('SELECT data FROM reconstructions WHERE owner_id=?',(user['id'],))]
    if any(x['status']=='processing' for x in active): raise HTTPException(409,'已有重建任务进行中')
    task_id = str(uuid.uuid4())
    output = io.BytesIO(); image.save(output,format='JPEG',quality=90)
    Path(config.OUTPUT_DIR,f'{task_id}.jpg').write_bytes(output.getvalue())
    storage.save_reconstruction(task_id,dict(taskId=task_id,status='processing',stage='等待处理',progress=0,created=time.time()),user['id'])
    threading.Thread(target=_run_task,args=(task_id,output.getvalue()),daemon=True).start()
    return {'taskId':task_id,'status':'processing'}


@app.get('/api/task/{task_id}')
def task_status(task_id: str,user=Depends(require_user)):
    task = owned_task(task_id,user)
    return {key:task.get(key) for key in ('taskId','status','stage','progress','error')}


@app.delete('/api/task/{task_id}')
def cancel_task(task_id: str,user=Depends(require_user)):
    task = owned_task(task_id,user)
    if task['status']=='processing': update(task_id,status='cancelled',stage='已取消')
    return {'ok':True}


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


@app.get('/files/{task_id}/{filename}')
def model_file(task_id: str,filename: str,user=Depends(require_user)):
    task = owned_task(task_id,user)
    suffix = {'mesh.glb':'.glb','heatmap.glb':'.heatmap.glb','preview.glb':'.preview.glb','image.jpg':'.jpg'}.get(filename)
    if not suffix: raise HTTPException(404,'文件不存在')
    path = Path(config.OUTPUT_DIR,f'{task_id}{suffix}')
    if not path.is_file() or (filename!='image.jpg' and task['status']!='success'): raise HTTPException(404,'文件尚未生成')
    return FileResponse(path,media_type='image/jpeg' if filename=='image.jpg' else 'model/gltf-binary')


@app.get('/{page:path}',include_in_schema=False)
def frontend(page:str):
    dist=Path(__file__).resolve().parents[2]/'dist'
    target=(dist/page).resolve()
    if not target.is_relative_to(dist.resolve()):raise HTTPException(404,'页面不存在')
    if target.is_file():return FileResponse(target)
    if page.split('/')[0] in ['','library','learning','auth','reconstruction','timeline','comparison','ai-explain'] and (dist/'index.html').is_file():
        return FileResponse(dist/'index.html')
    raise HTTPException(404,'页面不存在')
