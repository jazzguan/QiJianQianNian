"""历史轮廓和本服务生成 GLB 的测量与对比 API。"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import trimesh
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from . import config
from . import storage
from .morphology import compare_measurements, measure_mesh, measure_profile

router = APIRouter(prefix="/api", tags=["形态对比"])


def catalog():
    return {x['id']:x for x in storage.artifacts()}


class MeasureRequest(BaseModel):
    modelUrl: str | None = None
    artifactId: str | None = None


class CompareRequest(BaseModel):
    leftId: str
    rightId: str
    leftModelUrl: str | None = None
    rightModelUrl: str | None = None


def local_model_path(model_url):
    # 只解析重建服务的模型标识，不访问 URL，避免下载任意地址或读取任意本地文件。
    path = urlparse(model_url).path
    match = re.fullmatch(r"/files/([0-9a-fA-F-]{36})/mesh\.glb", path)
    if not match:
        raise HTTPException(422, "modelUrl 必须为重建服务生成的 /files/{taskId}/mesh.glb")
    target = Path(config.OUTPUT_DIR) / f"{match[1]}.glb"
    if not target.is_file():
        raise HTTPException(404, "模型文件不存在")
    return target

def authorize_model(model_url,request):
    if not model_url:return
    # 保留历史轮廓的公开查询；上传网格的测量也校验账号归属。
    from .platform_routes import current_user
    user = current_user(request)
    if not user: raise HTTPException(401,'请先登录')
    path = local_model_path(model_url)
    task = storage.reconstruction(path.stem)
    if not task or task['owner_id']!=user['id']: raise HTTPException(404,'模型不存在')


def measure(artifact_id=None, model_url=None):
    try:
        if model_url:
            scene = trimesh.load(local_model_path(model_url), force="scene", process=False)
            # dump 合并应用每个节点的变换。
            return measure_mesh(scene.to_geometry())
        item = catalog().get(artifact_id)
        if item is None:
            raise HTTPException(404, "参考器物不存在")
        result = measure_profile(item["shape"])
        result['method'] = item.get('modelMethod','历史示例轮廓')
        return result
    except (ValueError, TypeError, IndexError) as exc:
        raise HTTPException(422, f"形态测量失败：{exc}") from exc


@router.post("/measure")
def api_measure(payload: MeasureRequest,request: Request):
    if bool(payload.modelUrl) == bool(payload.artifactId):
        raise HTTPException(422, "请提供 modelUrl 或 artifactId 中的一项")
    authorize_model(payload.modelUrl,request)
    return measure(payload.artifactId, payload.modelUrl)


@router.post("/compare")
def api_compare(payload: CompareRequest,request: Request):
    authorize_model(payload.leftModelUrl,request)
    authorize_model(payload.rightModelUrl,request)
    left = measure(payload.leftId, payload.leftModelUrl)
    right = measure(payload.rightId, payload.rightModelUrl)
    left_label = "我的瓷器" if payload.leftModelUrl else catalog()[payload.leftId]["name"]
    right_label = "我的瓷器" if payload.rightModelUrl else catalog()[payload.rightId]["name"]
    result = compare_measurements(left, right, left_label, right_label)
    left_item = catalog().get(payload.leftId,{})
    right_item = catalog().get(payload.rightId,{})
    result['featureRows'] = [{'label':label,'left':left_item.get(key,'上传对象尚无馆藏记录') if not payload.leftModelUrl else '上传对象尚无馆藏记录',
                            'right':right_item.get(key,'')} for label,key in [('所属时期','period'),('制作工艺','summary'),('文化与年代','history')]]
    result['sources'] = left_item.get('sources',[])+right_item.get('sources',[])
    return {"id": f"{payload.leftId}-vs-{payload.rightId}",
            "leftId": payload.leftId, "rightId": payload.rightId, **result}


@router.post('/compare/explain')
def explain_comparison(payload: CompareRequest,request: Request):
    comparison=api_compare(payload,request)
    from .knowledge import text_of
    from .providers import text_completion,ProviderError
    items=[storage.artifact_by_id(artifact_id) for artifact_id in [payload.leftId,payload.rightId]]
    items=[item for item in items if item]
    sources=[dict(item['sources'][0],id=i+1) for i,item in enumerate(items)]
    evidence='\n\n'.join(f'[{i+1}] {text_of(item)}' for i,item in enumerate(items))
    try:
        answer=text_completion([{'role':'system','content':'根据形态测量与馆藏资料，比较两件器物的比例、纹饰和制作工艺。用[1]等编号引用资料。'
            '不将馆藏记录当作上传器物的身份，不推测资料没有记载的变化原因。中文300字以内。'},
            {'role':'user','content':f'测量：{json.dumps(comparison["rows"],ensure_ascii=False)}\n左侧：{comparison.get("leftLabel")}；右侧：{comparison.get("rightLabel")}\n资料：{evidence}'}])
    except ProviderError as exc:raise HTTPException(502,str(exc)) from None
    return {'answer':answer,'sources':sources}
