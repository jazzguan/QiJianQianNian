"""TripoSR 单图三维重建引擎（优先 CUDA，缺失时回退 CPU）。

基于 VAST-AI-Research/TripoSR 开源模型（stabilityai/TripoSR 权重）。
仅做真实推理，不伪造结果；模型不可用时抛出明确异常。
"""
import sys
import os
import threading
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from . import config

sys.path.insert(0, config.TRIPOSR_DIR)

_lock = threading.Lock()
_preload_lock = threading.Lock()
_ready = threading.Event()
_preload_thread = None
_model = None
_device = None
_state = {
    "status": "idle",
    "stage": "等待加载",
    "progress": 0,
    "error": None,
}
torch.set_num_threads(min(8,os.cpu_count() or 1))


def _set_state(status: str, stage: str, progress: int, error=None):
    with _preload_lock:
        _state.update(status=status, stage=stage, progress=progress, error=error)


def model_status():
    """Return a thread-safe snapshot for health checks and task progress."""
    with _preload_lock:
        return {**_state, "device": _device or selected_device()}


def _local_weights_ready() -> bool:
    """Avoid Hugging Face network probes once the complete official snapshot exists."""
    hub = Path(os.environ.get("HF_HOME", Path(config.BASE_DIR) / "cache" / "huggingface")) / "hub"
    snapshots = hub / "models--stabilityai--TripoSR" / "snapshots"
    return any(
        (snapshot / config.CONFIG_NAME).is_file()
        and (snapshot / config.WEIGHT_NAME).stat().st_size > 1_000_000_000
        for snapshot in snapshots.glob("*")
    ) if snapshots.is_dir() else False


@contextmanager
def _skip_parameter_initialization():
    """Skip random initialization because every persistent parameter is replaced by ckpt."""
    names = (
        "uniform_", "normal_", "trunc_normal_", "xavier_uniform_",
        "xavier_normal_", "kaiming_uniform_", "kaiming_normal_", "orthogonal_",
    )
    originals = {name: getattr(torch.nn.init, name) for name in names}

    def unchanged(tensor, *args, **kwargs):
        return tensor

    try:
        for name in names:
            setattr(torch.nn.init, name, unchanged)
        yield
    finally:
        for name, function in originals.items():
            setattr(torch.nn.init, name, function)


def selected_device() -> str:
    requested = os.environ.get("QJQN_DEVICE", "auto").lower()
    if requested not in {"auto", "cpu", "cuda"}:
        raise RuntimeError("QJQN_DEVICE 只能是 auto、cpu 或 cuda")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("已要求使用 CUDA，但 PyTorch 未检测到可用 NVIDIA GPU")
    return "cuda" if requested == "cuda" or (requested == "auto" and torch.cuda.is_available()) else "cpu"


def get_model():
    """惰性加载 TripoSR 模型（进程内单例）。"""
    global _model, _device
    with _lock:
        if _model is not None:
            return _model
        _ready.clear()
        _set_state("loading", "导入 TripoSR 运行库", 8)
        try:
            if _local_weights_ready():
                os.environ["HF_HUB_OFFLINE"] = "1"
                _set_state("loading", "使用本地 TripoSR 权重缓存", 9)
            from tsr.system import TSR  # noqa: WPS433
            _set_state("loading", "下载/读取权重并构建网络", 10)
            device = selected_device()
            with _skip_parameter_initialization():
                model = TSR.from_pretrained(
                    config.MODEL_ID,
                    config_name=config.CONFIG_NAME,
                    weight_name=config.WEIGHT_NAME,
                )
            _set_state("loading", f"加载模型到 {device.upper()}", 18)
            # 8GB 显存也使用较小分块；只影响速度，不降低网格分辨率。
            try:
                model.renderer.set_chunk_size(8192)
            except Exception:  # noqa: BLE001
                pass
            model.to(device)
            model.eval()
            _model = model
            _device = device
            _set_state("loading", "预热 U2NetP 前景分割", 19)
            from .foreground import get_session
            get_session()
            _set_state("ready", "三维模型已就绪", 20)
            return _model
        except Exception as exc:  # noqa: BLE001
            message = str(exc)[:500]
            if "TSR" not in locals():
                message = (
                    "无法导入 TripoSR：请确认已克隆 TripoSR 仓库到 backend/TripoSR，"
                    f"并安装其依赖。原始错误：{message}"
                )
            _set_state("error", "三维模型加载失败", 0, message)
            raise RuntimeError(message) from exc
        finally:
            _ready.set()


def release():
    """把 TripoSR 从显存里卸掉，给别的引擎腾地方；下次重建会自动重新加载。"""
    global _model
    if _model is None:
        return False
    with _lock:
        _model = None
        _ready.clear()
    _set_state("idle", "已释放显存，下次重建时重新加载", 0)
    import gc

    gc.collect()
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001
        pass
    return True


def _preload_worker():
    try:
        get_model()
    except Exception:  # 状态和错误已由 get_model 记录，后台线程不重复打印堆栈。
        pass


def start_preload():
    """Start one non-blocking model preload and return its current status."""
    global _preload_thread
    with _preload_lock:
        if _model is not None or (_preload_thread and _preload_thread.is_alive()):
            return {**_state, "device": _device or selected_device()}
        _state.update(status="loading", stage="准备预热三维模型", progress=5, error=None)
        _preload_thread = threading.Thread(
            target=_preload_worker, name="triposr-preload", daemon=True
        )
        _preload_thread.start()
        return {**_state, "device": _device or selected_device()}


def wait_for_model(progress=lambda stage,value: None):
    """Wait for background preload while forwarding meaningful stage changes."""
    start_preload()
    last_stage = None
    while True:
        state = model_status()
        if state["stage"] != last_stage:
            progress(state["stage"], state["progress"])
            last_stage = state["stage"]
        if state["status"] == "ready":
            return get_model()
        if state["status"] == "error":
            raise RuntimeError(state["error"] or "三维模型加载失败")
        _ready.wait(0.5)


def reconstruct(image_bytes: bytes, progress=lambda stage,value: None) -> "object":
    """输入图片字节，输出 trimesh.Trimesh（含顶点色）。"""
    model = wait_for_model(progress)
    progress('图像分割',35)
    from tsr.utils import resize_foreground  # noqa: WPS433
    from .foreground import remove_background

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image = remove_background(image)
    image = resize_foreground(image, 0.85)

    # 官方处理：rembg 返回 RGBA，将前景按 alpha 合成到 0.5 灰背景，转回 RGB
    arr = np.array(image).astype(np.float32) / 255.0
    arr = arr[:, :, :3] * arr[:, :, 3:4] + (1.0 - arr[:, :, 3:4]) * 0.5
    image = Image.fromarray((arr * 255.0).astype(np.uint8))

    progress('三维结构推理',55)
    with torch.inference_mode():
        scene_codes = model([image], device=_device)
    progress('提取三维网格',70)
    mesh = model.extract_mesh(scene_codes, True, resolution=config.RESOLUTION)[0]

    # 转 numpy 顶点色（部分版本返回 trimesh 已带 color）
    if not hasattr(mesh.visual, "vertex_colors") or mesh.visual.vertex_colors is None:
        mesh.visual.vertex_colors = np.full((len(mesh.vertices), 4), 200, dtype=np.uint8)

    return mesh
