"""多视角（Meshroom）重建任务 API。

接收同一物体的多张环绕照片，后台调用本地 Meshroom 管线，输出带真实贴图的
归一化 GLB、浏览网格与形态参数。任务存储、状态查询与文件接口复用现有机制。
"""
import io
import tempfile
import time
import uuid
from pathlib import Path

import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from . import config, storage
from .platform_routes import require_user

router = APIRouter(prefix="/api", tags=["多视角重建"])

MAX_IMAGES = 40
PER_IMAGE_BYTES = 12 * 1024 * 1024
MULTIVIEW_MAX_EDGE = int(__import__("os").environ.get("MULTIVIEW_MAX_EDGE", "4096"))


def _update(task_id, **values):
    task = storage.reconstruction(task_id)
    if task["status"] == "cancelled":
        raise RuntimeError("任务已取消")
    owner = task.pop("owner_id")
    task.update(values)
    storage.save_reconstruction(task_id, task, owner)


def _rotation_for_orientation(axis):
    import trimesh.transformations as tt

    if axis == 1:
        return np.eye(4)
    if axis == 0:
        # 绕 Z 轴 +90°：x -> y
        return tt.rotation_matrix(np.pi / 2, [0, 0, 1])
    # axis == 2：绕 X 轴 -90°
    return tt.rotation_matrix(-np.pi / 2, [1, 0, 0])


def _normalize_scene(scene):
    """复刻 orient_upright + normalize_mesh，但对整个场景统一变换、保留贴图。"""
    bounds = scene.bounds
    extents = bounds[1] - bounds[0]
    axis = int(np.argmax(extents))
    scene.apply_transform(_rotation_for_orientation(axis))

    bounds = scene.bounds
    center = (bounds[0] + bounds[1]) / 2.0
    ymin = bounds[0][1]
    height = bounds[1][1] - bounds[0][1]
    scale = config.DISPLAY_HEIGHT / max(height, 1e-6)

    import trimesh.transformations as tt

    scene.apply_transform(
        tt.translation_matrix([-center[0], -ymin, -center[2]])
    )
    scene.apply_transform(tt.scale_matrix(scale))
    return scene


def _run_multiview(task_id, image_paths):
    started = time.time()
    try:
        from .reconstruction_engine import reconstruct_multi

        # Meshroom/aliceVision 无法处理含中文的路径，因此整条管线（工作目录、
        # 原始 GLB）都放在纯英文系统临时目录；完成后再用 Python 把最终产物
        # 写回项目 outputs（trimesh 支持中文路径）。
        with tempfile.TemporaryDirectory(prefix="qjqn_mv_") as temp_dir:
            temp_work = Path(temp_dir)
            raw_glb = temp_work / "raw.glb"
            mesh_workdir = temp_work / "pipeline"

            _update(task_id, stage="SfM 相机配准", progress=15)
            mesh, engine = reconstruct_multi(
                image_paths,
                lambda s, v: _update(task_id, stage=s, progress=v),
                workdir=str(mesh_workdir),
                export_glb=str(raw_glb),
            )

            _update(task_id, stage="归一化与纹理整理", progress=82)
            import trimesh

            scene = trimesh.load(raw_glb, force="scene")
            scene = _normalize_scene(scene)

            full_glb = Path(config.OUTPUT_DIR) / f"{task_id}.glb"
            scene.export(str(full_glb))

            merged = scene.to_geometry() if hasattr(scene, "to_geometry") else trimesh.util.concatenate(
                tuple(scene.geometry.values())
            )

            _update(task_id, stage="生成浏览网格", progress=90)
            face_target = min(18000, len(merged.faces))
            preview = merged.simplify_quadric_decimation(face_count=face_target)
            preview_glb = Path(config.OUTPUT_DIR) / f"{task_id}.preview.glb"
            preview.export(str(preview_glb))

            _update(task_id, stage="计算形态参数", progress=95)
            from .uncertainty import compute_coarse_shape
            from .morphology import measure_profile

            shape = compute_coarse_shape(merged)
            params = measure_profile(shape)
            porcelain = dict(
                id=task_id,
                name="多视角重建模型",
                dynasty="unknown",
                dynastyName="年代未定",
                category="多视角重建",
                summary="基于多张环绕照片的本地摄影测量重建，几何与贴图来自真实拍摄。",
                shape=shape,
                params=params,
                modelMethod="MESHROOM 多视角重建（真实几何 + 实拍贴图）",
                imageCount=len(image_paths),
                modelUrl=f"/files/{task_id}/mesh.glb",
                previewUrl=f"/files/{task_id}/preview.glb",
            )
            _update(
                task_id,
                status="success",
                stage="完成",
                progress=100,
                porcelain=porcelain,
                shape=shape,
                modelUrl=f"/files/{task_id}/mesh.glb",
                previewUrl=f"/files/{task_id}/preview.glb",
                report={"elapsedMs": int((time.time() - started) * 1000)},
                note=f"{engine.upper()} 多视角重建 · 共 {len(image_paths)} 张照片",
            )
    except Exception as exc:  # noqa: BLE001
        task = storage.reconstruction(task_id)
        if task and task["status"] != "cancelled":
            _update(task_id, status="error", error=str(exc)[:600], stage="失败")


@router.post("/reconstruct/multiview")
async def reconstruct_multiview(
    files: list[UploadFile] = File(...), user=Depends(require_user)
):
    if not 2 <= len(files) <= MAX_IMAGES:
        raise HTTPException(422, f"照片数量需在 2～{MAX_IMAGES} 张之间")

    with storage.connect() as db:
        active = [
            __import__("json").loads(r[0])
            for r in db.execute(
                "SELECT data FROM reconstructions WHERE owner_id=?", (user["id"],)
            )
        ]
    if any(x["status"] == "processing" for x in active):
        raise HTTPException(409, "已有重建任务进行中")

    task_id = str(uuid.uuid4())
    image_dir = Path(config.OUTPUT_DIR) / f"{task_id}.images"
    image_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for index, upload in enumerate(files):
        data = await upload.read(PER_IMAGE_BYTES + 1)
        if len(data) > PER_IMAGE_BYTES:
            raise HTTPException(413, "单张图片不能超过 12MB")
        try:
            img = Image.open(io.BytesIO(data))
            img = img.convert("RGB")
            # 摄影测量依赖高分辨率细节，保留到长边 4096，仅在超限时缩小。
            img.thumbnail((MULTIVIEW_MAX_EDGE, MULTIVIEW_MAX_EDGE))
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise HTTPException(422, f"第 {index + 1} 张图片无法读取") from None
        target = image_dir / f"img_{index:03d}.jpg"
        img.save(target, format="JPEG", quality=95)
        saved_paths.append(str(target))

    storage.save_reconstruction(
        task_id,
        dict(
            taskId=task_id,
            status="processing",
            stage="等待处理",
            progress=0,
            created=time.time(),
            mode="multiview",
            imageCount=len(saved_paths),
        ),
        user["id"],
    )
    import threading

    threading.Thread(
        target=_run_multiview, args=(task_id, saved_paths), daemon=True
    ).start()
    return {"taskId": task_id, "status": "processing", "imageCount": len(saved_paths)}
