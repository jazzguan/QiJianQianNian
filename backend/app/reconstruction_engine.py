"""可替换的单图重建入口：SF3D 优先，GPU TripoSR 兜底。"""
import os
from pathlib import Path

from . import config


def _available(name: str) -> bool:
    root = Path(config.SF3D_DIR if name == "sf3d" else config.TRIPOSR_DIR)
    return (root / ("sf3d" if name == "sf3d" else "tsr")).is_dir()


def reconstruct(image_bytes, progress):
    requested = os.environ.get("QJQN_RECONSTRUCTION_ENGINE", "auto").lower()
    if requested not in {"auto", "sf3d", "triposr"}:
        raise RuntimeError("QJQN_RECONSTRUCTION_ENGINE 只能是 auto、sf3d 或 triposr")
    order = ["sf3d", "triposr"] if requested == "auto" else [requested]
    errors = []
    for name in order:
        if not _available(name):
            errors.append(f"{name} 源码未安装")
            continue
        try:
            module = __import__(f"app.{name}_engine", fromlist=["reconstruct"])
            return module.reconstruct(image_bytes, progress), name
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            if requested != "auto":
                raise
    raise RuntimeError("没有可用的三维重建引擎：" + "；".join(errors))


def status():
    return {
        "reconstructionEngine": os.environ.get("QJQN_RECONSTRUCTION_ENGINE", "auto"),
        "sf3dInstalled": _available("sf3d"),
        "triposrInstalled": _available("triposr"),
    }
