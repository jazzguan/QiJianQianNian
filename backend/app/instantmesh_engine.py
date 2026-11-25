"""InstantMesh 单图三维重建引擎（云端 ZeroGPU，无需本地权重与 GPU）。

通过 gradio_client 调用 TencentARC 官方 Hugging Face Space：
preprocess（去背景）→ generate_mvs（多视角扩散）→ make3d（前馈网格）。

匿名访问走 ZeroGPU 共享池、每日 GPU 时长很短且不稳定；配置 HF_TOKEN 后
使用账号配额，调用更稳定。这里只做真实远程调用，不伪造任何结果。
"""
import os
import tempfile
import threading
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

SERVICE = os.environ.get(
    "INSTANTMESH_SERVICE", "https://tencentarc-instantmesh.hf.space/"
)
SAMPLE_STEPS = int(os.environ.get("INSTANTMESH_STEPS", "75"))
SAMPLE_SEED = int(os.environ.get("INSTANTMESH_SEED", "42"))
REMOVE_BACKGROUND = os.environ.get("INSTANTMESH_REMOVE_BG", "true").lower() in {
    "1", "true", "yes", "on"
}
MAX_RETRIES = int(os.environ.get("INSTANTMESH_MAX_RETRIES", "3"))

_lock = threading.Lock()
_state = {
    "status": "ready",
    "stage": "云端服务，无需本地预热",
    "progress": 0,
    "error": None,
    "service": SERVICE,
}


def _token():
    return (
        os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        or None
    )


def model_status():
    """云端引擎没有本地加载过程，健康检查直接反映服务配置。"""
    with _lock:
        return {**_state, "authenticated": bool(_token())}


def start_preload():
    """云端服务无需预热，保持与本地引擎一致的接口。"""
    return None


def _is_quota_error(text):
    lowered = text.lower()
    return "quota" in lowered or "exceeded" in lowered


def _is_auth_error(text):
    lowered = text.lower()
    return "401" in lowered or "unauthorized" in lowered or "login" in lowered


def _run_remote(image_bytes, progress):
    from gradio_client import Client, handle_file
    import trimesh

    with tempfile.TemporaryDirectory(prefix="instantmesh_") as workdir:
        input_path = Path(workdir) / "input.jpg"
        Image.open(BytesIO(image_bytes)).convert("RGB").save(input_path, quality=95)

        client = Client(
            SERVICE,
            hf_token=_token(),
            verbose=False,
            download_files=str(Path(workdir) / "downloads"),
            httpx_kwargs={"timeout": 180},
        )

        progress("云端去背景预处理", 30)
        processed = client.predict(
            handle_file(str(input_path)), REMOVE_BACKGROUND, api_name="/preprocess"
        )

        progress("云端生成多视角图像", 50)
        mvs = client.predict(
            processed, float(SAMPLE_STEPS), SAMPLE_SEED, api_name="/generate_mvs"
        )

        progress("云端前馈生成三维网格", 72)
        _obj_path, glb_path = client.predict(api_name="/make3d")

        mesh = trimesh.load(glb_path, force="mesh")
        if not hasattr(mesh.visual, "vertex_colors") or mesh.visual.vertex_colors is None:
            mesh.visual.vertex_colors = np.full(
                (len(mesh.vertices), 4), 200, dtype=np.uint8
            )
        return mesh


def reconstruct(image_bytes: bytes, progress=lambda stage, value: None):
    """输入图片字节，输出带顶点色的 trimesh.Trimesh。"""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return _run_remote(image_bytes, progress)
        except Exception as exc:  # noqa: BLE001
            text = str(exc)
            last_error = text
            # 配额 / 认证问题：重试无意义，直接给出可操作提示。
            if _is_quota_error(text) or _is_auth_error(text):
                hint = (
                    "InstantMesh 云端配额不足或需要认证：请在 backend/.env 配置 "
                    "HF_TOKEN（Hugging Face 令牌）后重试。原始错误：" + text[:300]
                )
                _state.update(error=hint)
                raise RuntimeError(hint) from exc
            # 网络抖动或上游 GPU 共享池临时故障：退避后重试。
            if attempt < MAX_RETRIES:
                progress(f"云端调用失败，第 {attempt} 次重试", 25)
                import time

                time.sleep(3 * attempt)
    hint = (
        "InstantMesh 云端多次调用失败，匿名 ZeroGPU 共享池可能不可用；"
        "建议在 backend/.env 配置 HF_TOKEN 后重试。原始错误：" + str(last_error)[:300]
    )
    _state.update(error=hint)
    raise RuntimeError(hint)
