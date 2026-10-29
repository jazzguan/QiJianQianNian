"""FastAPI 服务：单图三维重建 + 可观测性/不确定性分析。"""
import os
import threading
import time
import uuid

import trimesh
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import config
from .triposr_engine import reconstruct
from .uncertainty import (
    build_report,
    compute_coarse_shape,
    enhance_colors,
    make_heatmap_mesh,
    normalize_mesh,
    orient_upright,
    vertex_uncertainty,
)
from .timeline import router as timeline_router

app = FastAPI(title="器见千年 · 三维重建服务")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(timeline_router)

# task_id -> {"status", "model_url", "heatmap_url", "report", "shape", "error"}
tasks: dict = {}
_lock = threading.Lock()

MODEL_LOADED = False


def _load_model_once() -> None:
    """后台预热模型，避免首次请求超时。"""
    global MODEL_LOADED
    try:
        from .triposr_engine import get_model

        get_model()
        MODEL_LOADED = True
    except Exception:  # noqa: BLE001
        MODEL_LOADED = False


def _run_task(task_id: str, image_bytes: bytes) -> None:
    started = time.time()
    try:
        mesh = reconstruct(image_bytes)
        mesh = orient_upright(mesh)
        mesh = normalize_mesh(mesh, config.DISPLAY_HEIGHT)
        uncertainty = vertex_uncertainty(mesh)
        mesh = enhance_colors(mesh, uncertainty)
        heatmap = make_heatmap_mesh(mesh, uncertainty)

        mesh_path = os.path.join(config.OUTPUT_DIR, f"{task_id}.glb")
        heatmap_path = os.path.join(config.OUTPUT_DIR, f"{task_id}.heatmap.glb")
        mesh.export(str(mesh_path))
        heatmap.export(str(heatmap_path))

        report = build_report(mesh, uncertainty, (time.time() - started) * 1000)
        shape = compute_coarse_shape(mesh)

        with _lock:
            tasks[task_id].update(
                {
                    "status": "success",
                    "mesh_path": str(mesh_path),
                    "heatmap_path": str(heatmap_path),
                    "report": report,
                    "shape": shape,
                }
            )
    except Exception as exc:  # noqa: BLE001
        with _lock:
            tasks[task_id].update({"status": "error", "error": str(exc)})


@app.on_event("startup")
def _startup() -> None:
    threading.Thread(target=_load_model_once, daemon=True).start()


@app.get("/health")
def health() -> dict:
    return {"ok": True, "modelLoaded": MODEL_LOADED, "device": "cpu"}


@app.post("/api/reconstruct")
async def api_reconstruct(file: UploadFile = File(...)) -> dict:
    task_id = str(uuid.uuid4())
    image_bytes = await file.read()
    with _lock:
        tasks[task_id] = {"status": "processing"}
    threading.Thread(target=_run_task, args=(task_id, image_bytes), daemon=True).start()
    return {"taskId": task_id, "status": "processing"}


@app.get("/api/task/{task_id}")
def api_task(task_id: str) -> dict:
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"taskId": task_id, "status": task["status"]}


@app.get("/api/model/{task_id}")
def api_model(task_id: str, request: Request) -> dict:
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task["status"] != "success":
        raise HTTPException(status_code=409, detail="模型尚未生成或生成失败")
    base = str(request.base_url).rstrip("/")
    return {
        "modelUrl": f"{base}/files/{task_id}/mesh.glb",
        "heatmapUrl": f"{base}/files/{task_id}/heatmap.glb",
        "report": task["report"],
        "shape": task["shape"],
        "note": "真实 TripoSR 重建结果（CPU 推理）。",
    }


@app.get("/files/{task_id}/mesh.glb")
def file_mesh(task_id: str):
    task = tasks.get(task_id)
    if not task or "mesh_path" not in task:
        raise HTTPException(status_code=404, detail="模型不存在")
    return FileResponse(task["mesh_path"], media_type="model/gltf-binary")


@app.get("/files/{task_id}/heatmap.glb")
def file_heatmap(task_id: str):
    task = tasks.get(task_id)
    if not task or "heatmap_path" not in task:
        raise HTTPException(status_code=404, detail="热力图不存在")
    return FileResponse(task["heatmap_path"], media_type="model/gltf-binary")
