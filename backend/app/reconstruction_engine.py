"""三维重建统一入口：单图引擎（本地/云端）与多图 Meshroom 分开装配。

单图引擎：triposr（本地，稳定默认）、instantmesh（云端高质量对照）、
sf3d（本地，需显式选择）、hunyuan（本地多模态形状，需显式选择）。
多图引擎：meshroom（本地摄影测量，独立入口）。
"""
import os
from pathlib import Path

from . import config

# hunyuan 可显式调用，但不在 DEFAULT_AUTO_ORDER 中，auto 默认不会选它。
SINGLE_IMAGE_ENGINES = ("triposr", "sf3d", "instantmesh", "hunyuan")
DEFAULT_AUTO_ORDER = ("triposr", "instantmesh")


def _available(name: str) -> bool:
    if name == "sf3d":
        # 适配器还缺 from_pretrained 必要参数、权重受 gated 限制，默认不算可用；
        # 真要启用时设 QJQN_ENABLE_SF3D=1，并自己确认能跑通。
        if os.environ.get("QJQN_ENABLE_SF3D", "").lower() not in {"1", "true", "yes"}:
            return False
        return (Path(config.SF3D_DIR) / "sf3d").is_dir()
    if name == "triposr":
        return (Path(config.TRIPOSR_DIR) / "tsr").is_dir()
    if name == "instantmesh":
        try:
            import gradio_client  # noqa: F401
        except ImportError:
            return False
        # 匿名调用 ZeroGPU 的 GPU 阶段稳定失败；只有配了 HF token 才算可用。
        return bool(
            os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        )
    if name == "meshroom":
        from .meshroom_engine import is_available

        return is_available()
    if name == "hunyuan":
        from .hunyuan_engine import is_available

        return is_available()
    return False


def _auto_order():
    override = os.environ.get("QJQN_SINGLE_IMAGE_ORDER")
    if override:
        order = [x.strip() for x in override.split(",") if x.strip()]
    else:
        order = list(DEFAULT_AUTO_ORDER)
    return [x for x in order if x in SINGLE_IMAGE_ENGINES]


# 会占用显存的生成式引擎；8GB 卡上让它们同时驻留会把扩散步拖慢十倍。
_GPU_ENGINES = ("triposr", "hunyuan")


def _release_others(target: str) -> None:
    """切换引擎前先卸掉另一个占显存的模型，避免显存互相挤压。"""
    for name in _GPU_ENGINES:
        if name == target:
            continue
        try:
            module = __import__(f"app.{name}_engine", fromlist=["release"])
            release = getattr(module, "release", None)
            if callable(release):
                release()
        except Exception:  # noqa: BLE001
            pass


def reconstruct(image_bytes, progress, engine=None):
    """单图重建：返回 (trimesh, 引擎名)。

    engine 为请求级指定（"triposr"/"hunyuan"/.../"auto"），由前端按用户选择传入；
    为空时回退到环境变量 QJQN_RECONSTRUCTION_ENGINE，保证既有调用行为不变。
    """
    requested = (engine or os.environ.get("QJQN_RECONSTRUCTION_ENGINE", "auto")).lower()
    valid = {"auto", *SINGLE_IMAGE_ENGINES}
    if requested not in valid:
        raise RuntimeError(
            "QJQN_RECONSTRUCTION_ENGINE 只能是 auto、" + "、".join(SINGLE_IMAGE_ENGINES)
        )
    order = _auto_order() if requested == "auto" else [requested]
    errors = []
    for name in order:
        if not _available(name):
            errors.append(f"{name} 未就绪")
            continue
        try:
            module = __import__(f"app.{name}_engine", fromlist=["reconstruct"])
            _release_others(name)
            return module.reconstruct(image_bytes, progress), name
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            if requested != "auto":
                raise
    raise RuntimeError("没有可用的单图重建引擎：" + "；".join(errors))


def reconstruct_multi(image_paths, progress, workdir=None, export_glb=None):
    """多图重建：仅支持 Meshroom，返回 (trimesh, 'meshroom')。"""
    if not _available("meshroom"):
        raise RuntimeError("Meshroom 未就绪：请先下载便携版并确认 meshroom_batch.exe")
    from .meshroom_engine import reconstruct as meshroom_reconstruct

    return (
        meshroom_reconstruct(
            image_paths, progress, workdir=workdir, export_glb=export_glb
        ),
        "meshroom",
    )


def status():
    result = {
        "reconstructionEngine": os.environ.get("QJQN_RECONSTRUCTION_ENGINE", "auto"),
        "triposrInstalled": _available("triposr"),
        "sf3dInstalled": _available("sf3d"),
        "instantmeshInstalled": _available("instantmesh"),
        "meshroomInstalled": _available("meshroom"),
        "hunyuanInstalled": _available("hunyuan"),
    }
    # 供前端判断"快速 / 精细"两个模式哪些可点。
    result["singleImageEngines"] = [
        {"name": name, "available": _available(name)} for name in SINGLE_IMAGE_ENGINES
    ]
    if result["instantmeshInstalled"]:
        from .instantmesh_engine import model_status as instant_status

        result["instantmeshModel"] = instant_status()
    if result["meshroomInstalled"]:
        from .meshroom_engine import model_status as meshroom_status

        result["meshroomModel"] = meshroom_status()
    if result["triposrInstalled"]:
        from .triposr_engine import model_status

        result["triposrModel"] = model_status()
    if result["hunyuanInstalled"]:
        from .hunyuan_engine import model_status as hunyuan_status

        result["hunyuanModel"] = hunyuan_status()
    return result


def start_preload():
    """启动 auto 模式会优先选择的本地引擎预热，云端引擎无需预热。"""
    requested = os.environ.get("QJQN_RECONSTRUCTION_ENGINE", "auto").lower()
    if requested == "triposr" or (
        requested == "auto" and _available("triposr")
    ):
        from .triposr_engine import start_preload as start_triposr_preload

        return start_triposr_preload()
    return None
