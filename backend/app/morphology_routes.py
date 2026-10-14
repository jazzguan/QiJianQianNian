"""独立形态对比API：目录、测量、GLB导入及跨时期对比。"""
import io
import json
import re
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import trimesh
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from .morphology import measure_mesh,measure_profile,normalize_mesh,compare_measurements

router=APIRouter(prefix='/api')
BASE_DIR=Path(__file__).resolve().parents[1]
MODEL_DIR=BASE_DIR/'comparison-models'
CATALOG_PATH=Path(__file__).with_name('morphology_catalog.json')


def catalog():
    items=json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
    for path in sorted(MODEL_DIR.glob('*.json')):
        if path.with_suffix('.glb').is_file(): items.append(json.loads(path.read_text(encoding='utf-8')))
    return items


def artifact(artifact_id):
    item=next((x for x in catalog() if x['id']==artifact_id),None)
    if not item: raise HTTPException(404,'参考器物不存在')
    return item


def load_mesh(data):
    # GLB必须完整、自包含；不读取外部纹理或几何文件。
    if len(data)<20 or data[:4]!=b'glTF' or int.from_bytes(data[8:12],'little')!=len(data):
        raise ValueError('请上传有效的GLB文件')
    if data[16:20]!=b'JSON': raise ValueError('GLB缺少JSON块')
    length=int.from_bytes(data[12:16],'little')
    document=json.loads(data[20:20+length].decode('utf-8'))
    for entry in [*document.get('buffers',[]),*document.get('images',[])]:
        if entry.get('uri') and not entry['uri'].startswith('data:'):
            raise ValueError('GLB包含外部资源，请导出自包含GLB')
    try:
        scene=trimesh.load(io.BytesIO(data),file_type='glb',force='scene',process=False)
        mesh=scene.to_geometry() if isinstance(scene,trimesh.Scene) else scene
    except Exception as exc:
        raise ValueError('无法解析GLB网格') from exc
    if not isinstance(mesh,trimesh.Trimesh) or not len(mesh.faces): raise ValueError('GLB没有三角网格')
    return mesh


def model_path(model_url):
    parts=urlsplit(model_url)
    if parts.scheme not in ('','http','https') or (parts.netloc and parts.hostname not in ('localhost','127.0.0.1','::1')):
        raise HTTPException(422,'只接受本服务模型地址，请用GLB导入外部模型')
    match=re.fullmatch(r'/api/comparison/models/([0-9a-f-]{36})\.glb',parts.path)
    if match: path=MODEL_DIR/(match[1]+'.glb')
    else:
        match=re.fullmatch(r'/files/([0-9a-f-]{36})/mesh\.glb',parts.path)
        if not match: raise HTTPException(422,'模型地址格式无效')
        path=BASE_DIR/'outputs'/(match[1]+'.glb')
    if not path.is_file(): raise HTTPException(404,'模型文件不存在，请重新导入')
    if path.stat().st_size > 20*1024*1024: raise HTTPException(413,'GLB不能超过20MB')
    return path


def normalized_artifact(item,measurement,model_url=None):
    source_height=max(p[1] for p in item['shape'])-min(p[1] for p in item['shape'])
    source_low=min(p[1] for p in item['shape'])
    parts=[{**p,'yMin':(p['yMin']-source_low)*30/source_height,'yMax':(p['yMax']-source_low)*30/source_height}
           for p in item.get('parts',[])]
    return {**item,'shape':measurement['shape'],'params':{k:measurement[k] for k in ['height','maxBellyDiameter','mouthDiameter','footDiameter']},
            'parts':parts,'modelUrl':model_url or item.get('modelUrl'),'measurementSource':measurement['source']}


def imported_artifact(identifier,label,measurement,model_url):
    return dict(id=identifier,name=label,dynasty=None,dynastyName='导入模型',period='GLB',summary='',description='',history='',
                shape=measurement['shape'],params={k:measurement[k] for k in ['height','maxBellyDiameter','mouthDiameter','footDiameter']},
                modelUrl=model_url,glaze=dict(color='#ddd6c4',roughness=.5,metalness=0,clearcoat=0,decoration='plain'),
                parts=[],formFeatures=[],decorationFeatures=[],craftFeatures=[],measurementSource='mesh')


def select(item_id,model_url,label):
    if model_url:
        measurement=measure_mesh(normalize_mesh(load_mesh(model_path(model_url).read_bytes())))
        item=imported_artifact(item_id or model_url,label or '导入模型',measurement,model_url)
    else:
        item=artifact(item_id)
        if item.get('modelUrl'): return select(item_id,item['modelUrl'],label or item['name'])
        measurement=measure_profile(item['shape'])
        item=normalized_artifact(item,measurement)
    return item,measurement


class MeasureRequest(BaseModel):
    modelUrl: str | None = Field(default=None,max_length=2048)
    artifactId: str | None = Field(default=None,max_length=100)


class CompareRequest(BaseModel):
    leftId: str | None = Field(default=None,max_length=150)
    rightId: str | None = Field(default=None,max_length=150)
    leftModelUrl: str | None = Field(default=None,max_length=2048)
    rightModelUrl: str | None = Field(default=None,max_length=2048)
    leftLabel: str | None = Field(default=None,max_length=80)
    rightLabel: str | None = Field(default=None,max_length=80)


@router.get('/comparison/artifacts')
def list_artifacts():
    return [x if x.get('modelUrl') else normalized_artifact(x,measure_profile(x['shape'])) for x in catalog()]


@router.post('/measure')
def measure(request:MeasureRequest):
    if bool(request.modelUrl)==bool(request.artifactId): raise HTTPException(422,'请选择一个模型地址或参考器物')
    try: return select(request.artifactId,request.modelUrl,None)[1]
    except (ValueError,TypeError,KeyError,OSError) as exc: raise HTTPException(422,str(exc)) from None


def import_model(data,name,up_axis):
    mesh=normalize_mesh(load_mesh(data),up_axis)
    measurement=measure_mesh(mesh)
    identifier=str(uuid.uuid4())
    MODEL_DIR.mkdir(parents=True,exist_ok=True)
    mesh.export(MODEL_DIR/(identifier+'.glb'))
    url=f'/api/comparison/models/{identifier}.glb'
    item=imported_artifact(identifier,Path(name).stem[:80] or '导入模型',measurement,url)
    (MODEL_DIR/(identifier+'.json')).write_text(json.dumps(item,ensure_ascii=False),encoding='utf-8')
    return dict(artifact=item,measurement=measurement,modelUrl=url)


@router.post('/measure/upload')
async def upload(file:UploadFile=File(...),upAxis:str=Form('y')):
    if not (file.filename or '').lower().endswith('.glb'): raise HTTPException(422,'请上传GLB模型')
    data=await file.read(20*1024*1024+1)
    if len(data)>20*1024*1024: raise HTTPException(413,'GLB不能超过20MB')
    try: return await run_in_threadpool(import_model,data,file.filename,upAxis)
    except (ValueError,TypeError,KeyError,OSError) as exc: raise HTTPException(422,'无法测量：'+str(exc)) from None


@router.get('/comparison/models/{identifier}.glb')
def model(identifier:str):
    path=model_path(f'/api/comparison/models/{identifier}.glb')
    return FileResponse(path,media_type='model/gltf-binary')


@router.post('/compare')
def compare(request:CompareRequest):
    if not (request.leftId or request.leftModelUrl) or not (request.rightId or request.rightModelUrl):
        raise HTTPException(422,'请选择左右两个器物')
    try:
        left,lm=select(request.leftId,request.leftModelUrl,request.leftLabel)
        right,rm=select(request.rightId,request.rightModelUrl,request.rightLabel)
        return dict(id=f'{left["id"]}--{right["id"]}',leftId=left['id'],rightId=right['id'],left=left,right=right,
                    **compare_measurements(lm,rm,left['name'],right['name']))
    except (ValueError,TypeError,KeyError,OSError) as exc: raise HTTPException(422,'无法测量：'+str(exc)) from None
