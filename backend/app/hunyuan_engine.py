"""Hunyuan3D-2mini 单图形状生成引擎（本地，8GB 显存可跑）。

基于 Tencent/Hunyuan3D-2 开源仓库的 mini DiT（0.6B）形状管线。
形状管线条件端只有图像（DINOv2），本模块先实现"图→形状"；
文字条件需经 text2image 中转，由后续多模态接口接入，此处不伪造。
仅做真实推理，权重或代码缺失时抛出明确异常。
"""
import os
import sys
import threading
from io import BytesIO
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from . import config

# 让 Hunyuan 代码与本地权重可被定位，并避开会卡死的 xet 后端。
os.environ.setdefault("HF_HOME", os.path.join(config.BASE_DIR, "cache", "hf_cache"))
os.environ.setdefault("U2NET_HOME", os.path.join(config.BASE_DIR, "cache", "rembg"))
os.environ["HY3DGEN_MODELS"] = config.HUNYUAN_MODEL_ROOT
os.environ["HF_HUB_DISABLE_XET"] = "1"
sys.path.insert(0, config.HUNYUAN_DIR)

_lock = threading.Lock()
_state_lock = threading.Lock()
_pipeline = None
_device = None
_state = {
    "status": "idle",
    "stage": "等待加载",
    "progress": 0,
    "error": None,
}


def _set_state(status, stage, progress, error=None):
    with _state_lock:
        _state.update(status=status, stage=stage, progress=progress, error=error)


def is_available():
    """代码目录与 DiT 权重都在才算就绪。"""
    code_ok = (Path(config.HUNYUAN_DIR) / "hy3dgen").is_dir()
    weight = (
        Path(config.HUNYUAN_MODEL_ROOT)
        / config.HUNYUAN_REPO
        / config.HUNYUAN_SUBFOLDER
        / "model.fp16.safetensors"
    )
    return code_ok and weight.is_file() and weight.stat().st_size > 1_000_000_000


def model_status():
    with _state_lock:
        return {**_state, "device": _device or selected_device()}


def selected_device():
    if not torch.cuda.is_available():
        raise RuntimeError("Hunyuan3D 形状管线需要 CUDA，但未检测到可用 NVIDIA GPU")
    return "cuda"


def get_pipeline():
    """惰性加载 Hunyuan 形状管线（进程内单例）。"""
    global _pipeline, _device
    with _lock:
        if _pipeline is not None:
            return _pipeline
        _set_state("loading", "导入 Hunyuan3D 运行库", 8)
        try:
            from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

            _set_state("loading", "读取本地权重并构建管线", 12)
            device = selected_device()
            _pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
                config.HUNYUAN_REPO,
                subfolder=config.HUNYUAN_SUBFOLDER,
                device=device,
            )
            _device = device
            _set_state("ready", "Hunyuan3D 管线已就绪", 20)
            return _pipeline
        except Exception as exc:  # noqa: BLE001
            message = str(exc)[:500]
            _set_state("error", "Hunyuan3D 管线加载失败", 0, message)
            raise RuntimeError(message) from exc


def release():
    """释放 Hunyuan 形状管线；下次重建时重新加载（约 12 秒），换来别的引擎不被拖慢。"""
    global _pipeline, _device
    if _pipeline is None:
        return False
    with _lock:
        _pipeline = None
        _device = None
    _set_state("idle", "已释放显存，下次重建时重新加载", 0)
    import gc

    gc.collect()
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001
        pass
    return True


def _remove_background(image):
    """复用项目已缓存的 u2netp，输出带 alpha 的 RGBA。"""
    from rembg import remove, new_session

    session = new_session("u2netp")
    return remove(image, session=session, bgcolor=[255, 255, 255, 0])


def reconstruct(image_bytes: bytes, progress=lambda stage, value: None):
    """输入图片字节，输出 trimesh.Trimesh（白模带默认顶点色）。"""
    if not is_available():
        raise RuntimeError(
            "Hunyuan3D 未就绪：请确认代码目录与 DiT 权重（model.fp16.safetensors）"
        )
    pipeline = get_pipeline()

    progress("图像分割", 35)
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    cut = _remove_background(image)

    progress("三维结构推理", 55)
    t0 = __import__("time").time()
    with torch.inference_mode():
        mesh = pipeline(
            image=cut,
            num_inference_steps=config.HUNYUAN_STEPS,
            octree_resolution=config.HUNYUAN_OCTREE,
        )[0]
    torch.cuda.synchronize()
    _set_state("ready", "三维模型已就绪", 90)

    # 多数情况下输出已水密；偶发边缘孔洞导致不水密时，仅在此时做一次修复。
    if not mesh.is_watertight:
        repaired = mesh.process()
        if repaired.is_watertight:
            mesh = repaired

    # 形状管线输出无材质白模，补统一顶点色，保证前端可稳定渲染。
    if not hasattr(mesh.visual, "vertex_colors") or mesh.visual.vertex_colors is None:
        mesh.visual.vertex_colors = np.full((len(mesh.vertices), 4), 200, dtype=np.uint8)

    progress("提取三维网格", 95)
    _set_state("ready", "三维模型已就绪", 100)
    _state["elapsed"] = round(__import__("time").time() - t0, 1)
    return mesh
