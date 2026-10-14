"""TripoSR 单图三维重建引擎（CPU 推理）。

基于 VAST-AI-Research/TripoSR 开源模型（stabilityai/TripoSR 权重）。
仅做真实推理，不伪造结果；模型不可用时抛出明确异常。
"""
import sys
import os
import threading
from io import BytesIO

import numpy as np
import torch
from PIL import Image

from . import config

sys.path.insert(0, config.TRIPOSR_DIR)

_lock = threading.Lock()
_model = None
torch.set_num_threads(min(8,os.cpu_count() or 1))


def _is_available() -> tuple[bool, str]:
    if not torch.cuda.is_available():
        return True, "cpu"
    return True, "cuda"


def get_model():
    """惰性加载 TripoSR 模型（进程内单例）。"""
    global _model
    with _lock:
        if _model is not None:
            return _model

        try:
            from tsr.system import TSR  # noqa: WPS433
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "无法导入 TripoSR：请确认已克隆 TripoSR 仓库到 backend/TripoSR，"
                f"并安装其依赖。原始错误：{exc}"
            ) from exc

        device = "cpu"
        model = TSR.from_pretrained(
            config.MODEL_ID,
            config_name=config.CONFIG_NAME,
            weight_name=config.WEIGHT_NAME,
        )
        # CPU 推理：降低 chunk size，避免显存/内存溢出
        try:
            model.renderer.set_chunk_size(8192)
        except Exception:  # noqa: BLE001
            pass
        model.to(device)
        model.eval()
        _model = model
        return _model


def reconstruct(image_bytes: bytes, progress=lambda stage,value: None) -> "object":
    """输入图片字节，输出 trimesh.Trimesh（含顶点色）。"""
    model = get_model()
    progress('图像分割',35)
    from tsr.utils import resize_foreground  # noqa: WPS433
    from rembg import new_session, remove

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image = remove(image,session=new_session('u2netp'))
    image = resize_foreground(image, 0.85)

    # 官方处理：rembg 返回 RGBA，将前景按 alpha 合成到 0.5 灰背景，转回 RGB
    arr = np.array(image).astype(np.float32) / 255.0
    arr = arr[:, :, :3] * arr[:, :, 3:4] + (1.0 - arr[:, :, 3:4]) * 0.5
    image = Image.fromarray((arr * 255.0).astype(np.uint8))

    progress('三维结构推理',55)
    with torch.no_grad():
        scene_codes = model([image], device="cpu")
    progress('提取三维网格',70)
    mesh = model.extract_mesh(scene_codes, True, resolution=config.RESOLUTION)[0]

    # 转 numpy 顶点色（部分版本返回 trimesh 已带 color）
    if not hasattr(mesh.visual, "vertex_colors") or mesh.visual.vertex_colors is None:
        mesh.visual.vertex_colors = np.full((len(mesh.vertices), 4), 200, dtype=np.uint8)

    return mesh
