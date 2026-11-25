"""Meshroom 多视角三维重建引擎（本地摄影测量，离线，无需账号）。

通过 subprocess 调用 Meshroom 便携版的 meshroom_batch.exe，对同一物体的
一组环绕照片执行完整 SfM + MVS 管线。8GB 显存下使用 2048 贴图、downscale=4
（8K/4K 会内存不足，这是在本机实测可行的配置）。

输出带贴图 OBJ，再用 trimesh 加载为可操作网格。只做真实本地计算，不伪造结果。
"""
import os
import shutil
import subprocess
import threading
from pathlib import Path

from . import config

_lock = threading.Lock()
TEXTURE_SIDE = os.environ.get("MESHROOM_TEXTURE_SIDE", "2048")
DOWNSCALE = os.environ.get("MESHROOM_DOWNSCALE", "4")


def is_available():
    return Path(config.MESHROOM_BATCH).is_file()


def model_status():
    return {
        "status": "ready" if is_available() else "missing",
        "stage": "本地 Meshroom，按需调用",
        "error": None if is_available() else "未找到 meshroom_batch.exe，请先下载便携版",
        "executable": config.MESHROOM_BATCH,
    }


def start_preload():
    """本地管线无常驻模型，保持与其他引擎一致的接口。"""
    return None


def _find_textured_obj(output_dir):
    candidates = sorted(
        Path(output_dir).rglob("*.obj"),
        key=lambda p: p.stat().st_size,
        reverse=True,
    )
    if not candidates:
        raise RuntimeError("Meshroom 运行结束但未找到输出 OBJ")
    return candidates[0]


def reconstruct(
    image_paths,
    progress=lambda stage, value: None,
    workdir=None,
    export_glb=None,
):
    """输入同一物体的多张照片路径，执行重建并返回 trimesh 网格（含贴图）。

    export_glb 给定时，会把完整带贴图场景另存为单文件 GLB。
    注意：aliceVision 无法处理含非 ASCII（如中文）的工作路径，workdir 必须
    是纯英文路径；默认使用系统临时目录（纯英文），无需手动指定。
    """
    if not is_available():
        raise RuntimeError(
            "Meshroom 便携版未就绪：请先下载并解压到 " + config.MESHROOM_DIR
        )
    if len(image_paths) < 2:
        raise RuntimeError("Meshroom 多视角重建至少需要 2 张照片")

    import tempfile

    with _lock:
        if workdir is None:
            # 系统临时目录默认是纯英文路径，规避 aliceVision 中文路径缺陷。
            temp_ctx = tempfile.TemporaryDirectory(prefix="meshroom_")
            workdir = temp_ctx.name
        else:
            temp_ctx = None
        if not workdir.isascii():
            raise RuntimeError(
                "Meshroom 工作目录含非 ASCII 字符（aliceVision 不支持中文路径），"
                "请改用纯英文路径，或不指定 workdir 以使用系统临时目录。"
            )
        try:
            work = Path(workdir)
            input_dir = work / "inputs"
            output_dir = work / "output"
            cache_dir = work / "cache"
            for d in (input_dir, output_dir, cache_dir):
                d.mkdir(parents=True, exist_ok=True)

            # 复制到统一输入目录，避免原路径含特殊字符或空格带来的问题。
            for index, src in enumerate(image_paths):
                src_path = Path(src)
                ext = src_path.suffix.lower() or ".jpg"
                shutil.copy2(
                    src_path, input_dir / f"img_{index:03d}{ext}"
                )

            progress("SfM 特征提取与相机配准", 20)
            command = [
                config.MESHROOM_BATCH,
                "--input", str(input_dir),
                "--output", str(output_dir),
                "--cache", str(cache_dir),
                "--paramOverrides",
                f"Texturing_1.textureSide={TEXTURE_SIDE}",
                f"Texturing_1.downscale={DOWNSCALE}",
                "Texturing_1.colorMapping.colorMappingFileType=png",
            ]
            sensor_db = Path(
                config.MESHROOM_DIR, "aliceVision", "share", "aliceVision",
                "cameraSensors.db",
            )
            if sensor_db.is_file():
                command.extend(
                    [f"CameraInit_1.sensorDatabase={sensor_db}"]
                )

            # 中文 Windows 下 meshroom 输出为本地编码（GBK），用字节模式读取
            # 再容错解码，避免 UTF-8 解码线程崩溃。
            result = subprocess.run(
                command,
                capture_output=True,
                timeout=int(os.environ.get("MESHROOM_TIMEOUT", "1800")),
            )
            if result.returncode != 0:
                stdout = result.stdout.decode("utf-8", errors="replace")
                stderr = result.stderr.decode("utf-8", errors="replace")
                tail = stdout[-800:] + stderr[-800:]
                raise RuntimeError(
                    f"meshroom_batch 退出码 {result.returncode}：{tail}"
                )

            progress("MVS 稠密重建与纹理生成", 80)
            obj_path = _find_textured_obj(output_dir)

            import trimesh

            loaded = trimesh.load(obj_path, force="scene")
            if export_glb is not None:
                if not str(export_glb).isascii():
                    raise RuntimeError("GLB 导出路径含非 ASCII 字符，请改用纯英文路径")
                loaded.export(str(export_glb))
            if isinstance(loaded, trimesh.Scene):
                mesh = loaded.to_geometry() if hasattr(loaded, "to_geometry") else trimesh.util.concatenate(
                    tuple(loaded.geometry.values())
                )
            else:
                mesh = loaded
            progress("重建完成", 98)
            mesh.metadata["source_obj"] = str(obj_path)
            if export_glb is not None:
                mesh.metadata["exported_glb"] = str(export_glb)
            return mesh
        finally:
            if temp_ctx is not None:
                temp_ctx.cleanup()
