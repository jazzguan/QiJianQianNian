"""真实馆藏、私人GLB与重建模型的测量、尺度标定和比较。"""
import io
import json
import re
import time
import uuid
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import trimesh
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from . import config, storage
from .morphology import calibrate, compare_measurements, measure_mesh, measure_profile, normalize_mesh

router=APIRouter(prefix='/api', tags=['形态对比'])

class MeasureRequest(BaseModel):
    modelUrl: str | None = Field(default=None,max_length=2048)
    artifactId: str | None = Field(default=None,max_length=100)
    heightCm: float | None = Field(default=None,gt=0,le=1000)

class CompareRequest(BaseModel):
    leftId: str = Field(max_length=100)
    rightId: str = Field(max_length=100)
    leftModelUrl: str | None = Field(default=None,max_length=2048)
    rightModelUrl: str | None = Field(default=None,max_length=2048)
    leftHeightCm: float | None = Field(default=None,gt=0,le=1000)
    rightHeightCm: float | None = Field(default=None,gt=0,le=1000)

def catalog(): return {x['id']:x for x in storage.artifacts()}

def local_model_path(model_url):
    url=urlparse(model_url)
    if url.scheme not in ('','http','https'): raise HTTPException(422,'模型地址格式无效')
    match=re.fullmatch(r'/files/([0-9a-fA-F-]{36})/mesh\.glb',url.path)
    if not match: raise HTTPException(422,'请从目录选择模型或导入GLB文件')
    target=Path(config.OUTPUT_DIR)/(match[1]+'.glb')
    if not target.is_file(): raise HTTPException(404,'模型文件不存在')
    return target

def private_item(identifier,request):
    from .platform_routes import current_user
    user=current_user(request)
    if not user: raise HTTPException(401,'请先登录')
    task=storage.reconstruction(identifier)
    if not task or task['owner_id']!=user['id'] or task.get('status')!='success': raise HTTPException(404,'模型不存在')
    return task

def authorize_model(model_url,request):
    if model_url: return private_item(local_model_path(model_url).stem,request)

def load_glb(data):
    if len(data)>20*1024*1024: raise ValueError('GLB不能超过20MB')
    if len(data)<20 or data[:4]!=b'glTF' or int.from_bytes(data[8:12],'little')!=len(data) or data[16:20]!=b'JSON':
        raise ValueError('请上传有效的GLB模型')
    length=int.from_bytes(data[12:16],'little')
    document=json.loads(data[20:20+length].decode('utf-8'))
    for entry in [*document.get('buffers',[]),*document.get('images',[])]:
        if entry.get('uri') and not entry['uri'].startswith('data:'): raise ValueError('请导出包含纹理和几何的自包含GLB')
    scene=trimesh.load(io.BytesIO(data),file_type='glb',force='scene',process=False)
    mesh=scene.to_geometry()
    if not isinstance(mesh,trimesh.Trimesh) or not len(mesh.faces): raise ValueError('GLB没有三角网格')
    if len(mesh.faces)>300000: raise ValueError('模型超过30万面，请先简化网格')
    return mesh

@lru_cache(maxsize=32)
def cached_measure(path,mtime,size):
    return measure_mesh(load_glb(Path(path).read_bytes()))

def measure_file(path):
    stat=path.stat()
    return cached_measure(str(path),stat.st_mtime_ns,stat.st_size)

def known_height(item):
    if item.get('physicalHeightCm'): return item['physicalHeightCm']
    text=item.get('measurementsText','')
    explicit=re.search(r'(?:height|\bH)\s*:?\s*([\d.]+)\s*cm',text,re.I)
    if explicit: return float(explicit[1])
    if item.get('category') in ['瓶','梅瓶','长颈瓶','罐','执壶','杯']:
        overall=re.search(r'Overall:\s*([\d.]+)(?:\s*cm|\s*x\s*[\d.]+(?:\s*x\s*[\d.]+)?\s*cm)',text,re.I)
        if overall: return float(overall[1])
    return None

def select(identifier,model_url,request,height_cm=None):
    item=catalog().get(identifier) if not model_url else None
    if item:
        if item.get('geometrySource')=='scan':
            path=storage.DATA_DIR/'images'/f'{item["id"]}.glb'
            if not path.is_file(): raise HTTPException(404,'扫描模型尚未下载')
            measurement=measure_file(path)
        else: measurement=measure_profile(item['shape'])
        measurement={**measurement,'method':item.get('modelMethod','照片轮廓测量')}
    else:
        task=authorize_model(model_url,request) if model_url else private_item(identifier,request)
        measurement=measure_file(local_model_path(task.get('modelUrl') or model_url or ''))
        item=task.get('porcelain') or dict(id=identifier or local_model_path(model_url).stem,name='我的瓷器',
            dynasty='unknown',dynastyName='重建模型',period='',summary='',description='',history='',
            shape=measurement['shape'],params=measurement,parts=[],sources=[],formFeatures=[],decorationFeatures=[],craftFeatures=[],
            modelUrl=model_url,glaze=dict(color='#ddd6c4',roughness=.5,metalness=0,clearcoat=0,decoration='plain'))
    height=height_cm if height_cm is not None else known_height(item)
    measurement=calibrate(measurement,height,'用户输入高度' if height_cm is not None else '馆藏尺寸记录' if item.get('institution') else '导入模型标定高度')
    return {**item,'shape':measurement['shape'],'params':measurement,'physicalHeightCm':height},measurement

@router.get('/comparison/artifacts')
def comparison_artifacts(request:Request):
    from .platform_routes import current_user
    items=storage.artifacts(); user=current_user(request)
    if user:
        with storage.connect() as db:
            rows=db.execute('SELECT data FROM reconstructions WHERE owner_id=? ORDER BY created',(user['id'],)).fetchall()
        items += [t['porcelain'] for row in rows if (t:=json.loads(row['data'])).get('status')=='success' and t.get('porcelain')]
    return items

@router.post('/measure')
def api_measure(payload:MeasureRequest,request:Request):
    if bool(payload.modelUrl)==bool(payload.artifactId): raise HTTPException(422,'请提供modelUrl或artifactId中的一项')
    if payload.artifactId and payload.artifactId not in catalog():
        task=storage.reconstruction(payload.artifactId)
        if not task: raise HTTPException(404,'参考器物不存在')
    try: return select(payload.artifactId,payload.modelUrl,request,payload.heightCm)[1]
    except (ValueError,TypeError,KeyError,OSError) as exc: raise HTTPException(422,f'形态测量失败：{exc}') from None

def import_model(data,name,up_axis,height_cm,user):
    mesh=normalize_mesh(load_glb(data),up_axis)
    measurement=calibrate(measure_mesh(mesh),height_cm)
    identifier=str(uuid.uuid4()); url=f'/files/{identifier}/mesh.glb'
    mesh.export(str(Path(config.OUTPUT_DIR)/(identifier+'.glb')))
    item=dict(id=identifier,name=Path(name).stem[:80] or '导入模型',dynasty='unknown',dynastyName='导入模型',period='',
        category='未知',summary='',description='',history='',shape=measurement['shape'],params=measurement,
        physicalHeightCm=height_cm,modelUrl=url,modelMethod='导入GLB网格测量',geometrySource='imported',
        formFeatures=[],decorationFeatures=[],craftFeatures=[],parts=[],sources=[],
        glaze=dict(color='#ddd6c4',roughness=.5,metalness=0,clearcoat=0,decoration='plain'))
    storage.save_reconstruction(identifier,dict(taskId=identifier,status='success',stage='完成',progress=100,
        created=time.time(),kind='imported',porcelain=item,modelUrl=url,note='GLB导入'),user['id'])
    return dict(artifact=item,measurement=measurement,modelUrl=url)

@router.post('/measure/upload')
async def upload(request:Request,file:UploadFile=File(...),upAxis:str=Form('y'),heightCm:float|None=Form(None)):
    from .platform_routes import current_user
    user=current_user(request)
    if not user: raise HTTPException(401,'请先登录后导入模型')
    if not (file.filename or '').lower().endswith('.glb'): raise HTTPException(422,'请上传GLB模型')
    data=await file.read(20*1024*1024+1)
    if len(data)>20*1024*1024: raise HTTPException(413,'GLB不能超过20MB')
    try: return await run_in_threadpool(import_model,data,file.filename,upAxis,heightCm,user)
    except (ValueError,TypeError,KeyError,OSError) as exc: raise HTTPException(422,f'导入失败：{exc}') from None

@router.post('/compare')
def api_compare(payload:CompareRequest,request:Request):
    for identifier,url in [(payload.leftId,payload.leftModelUrl),(payload.rightId,payload.rightModelUrl)]:
        if not url and identifier not in catalog() and not storage.reconstruction(identifier):
            raise HTTPException(404,'参考器物不存在')
    try:
        left,lm=select(payload.leftId,payload.leftModelUrl,request,payload.leftHeightCm)
        right,rm=select(payload.rightId,payload.rightModelUrl,request,payload.rightHeightCm)
    except (ValueError,TypeError,KeyError,OSError) as exc: raise HTTPException(422,f'形态测量失败：{exc}') from None
    result=compare_measurements(lm,rm,left['name'],right['name'])
    result['cavityRows']=[dict(label=label,left=f'{lm[key]:.3f}' if lm.get(key) else '无内壁数据',right=f'{rm[key]:.3f}' if rm.get(key) else '无内壁数据')
        for key,label in [('innerMouthDiameter','内口径'),('wallThickness','器口壁厚')]]
    def physical(m,key):
        if not m.get('physical'): return '未标定'
        value=m['physical'].get(key)
        return f'{value:.3f} cm' if value is not None else '无内壁数据'
    result['physicalRows']=[dict(label=label,left=physical(lm,key),right=physical(rm,key)) for key,label in
        [('height','实物高度'),('maxBellyDiameter','最大腹径'),('mouthDiameter','口部外径'),('footDiameter','足部外径'),('innerMouthDiameter','内口径'),('wallThickness','器口壁厚')]]
    def describe(item,key):
        value=item.get(key)
        return '；'.join(value) if isinstance(value,list) and value else str(value or '未提供资料')
    result['featureRows']=[dict(label=label,left=describe(left,key),right=describe(right,key)) for label,key in
        [('所属时期','period'),('器型','formFeatures'),('纹饰','decorationFeatures'),('工艺','craftFeatures'),('材质','material'),('用途','use'),('历史背景','history')]]
    result['sources']=left.get('sources',[])+right.get('sources',[])
    return dict(id=f'{left["id"]}--{right["id"]}',leftId=left['id'],rightId=right['id'],left=left,right=right,**result)

@router.post('/compare/explain')
def explain_comparison(payload:CompareRequest,request:Request):
    comparison=api_compare(payload,request)
    from .knowledge import text_of
    from .providers import text_completion,ProviderError
    items=[comparison['left'],comparison['right']]
    sources=[];evidence=[]
    for item in items:
        for source in item.get('sources',[]):
            if source['url'] not in [x['url'] for x in sources]:
                sources.append(dict(source,id=len(sources)+1));evidence.append(f'[{len(sources)}] {text_of(item)}')
    try:
        answer=text_completion([{'role':'system','content':'根据测量与馆藏资料比较两件器物的形态、纹饰和工艺。用[1]等引用提供的来源。上传模型无历史资料时仅比较几何，不推测身份、年代或工艺原因。中文300字以内。'},
            {'role':'user','content':f'左侧：{items[0]["name"]}；右侧：{items[1]["name"]}；测量：{json.dumps(comparison["rows"],ensure_ascii=False)}；资料：'+'\n'.join(evidence)}])
    except ProviderError as exc: raise HTTPException(502,str(exc)) from None
    return dict(answer=answer,sources=sources)
