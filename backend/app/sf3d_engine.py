"""Stable Fast 3D 单图重建适配器。官方源码按需放在 backend/SF3D。"""
import os
import sys
import threading
from io import BytesIO

import torch
from PIL import Image

from . import config
from .triposr_engine import selected_device

sys.path.insert(0, config.SF3D_DIR)
_lock = threading.Lock()
_model = None


def get_model():
    global _model
    with _lock:
        if _model is not None:
            return _model
        try:
            from sf3d.system import SF3D
        except Exception as exc:
            raise RuntimeError(
                "无法导入 SF3D；请先运行 setup-sf3d.ps1，并确认官方源码及依赖安装完成。"
            ) from exc
        _model = SF3D.from_pretrained("stabilityai/stable-fast-3d").to(selected_device()).eval()
        return _model


def reconstruct(image_bytes: bytes, progress=lambda stage, value: None):
    model = get_model()
    from sf3d.utils import resize_foreground
    from .foreground import remove_background

    progress("图像分割", 35)
    image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    image = resize_foreground(remove_background(image), 0.85)
    progress("SF3D 几何与材质推理", 55)
    with torch.inference_mode():
        mesh, _ = model.run_image(
            image,
            bake_resolution=int(os.environ.get("SF3D_BAKE_RESOLUTION", "1024")),
            remesh="triangle",
        )
    progress("提取三维网格", 75)
    return mesh
