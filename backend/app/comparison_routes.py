# -*- coding: utf-8 -*-
"""同一张图、多个单图引擎横向对比。

POST /api/engine-compare          上传一张图并指定引擎，返回 compareId
GET  /api/engine-compare/{id}     查询整体与各引擎状态、指标
GET  /api/engine-compare/{id}/mesh/{engine}.glb   下载某个引擎的归一化产物

注意：/api/compare 已被 morphology_routes 用于两件器物形态对比，本模块用独立前缀避免冲突。

只做引擎几何本身的对比，不重复单图任务里的识别/热力/照片纹理流程；
所有引擎产物统一朝向、统一缩放到展示高度，保证可直接并排比较。
"""
import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path

import trimesh
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image

from . import config, storage
from .platform_routes import require_user
from .reconstruction_engine import _available, _release_others
from .uncertainty import normalize_mesh, orient_upright

router = APIRouter(prefix="/api/engine-compare", tags=["engine-compare"])

# 对比任务串行执行，避免多个引擎同时占满显存。
_gate = threading.Semaphore(1)

# 允许参与对比的单图引擎（sf3d 按团队当前决定暂不开放）。
SUPPORTED = ("triposr", "instantmesh", "hunyuan")
DEFAULT_ENGINES = ("triposr", "hunyuan")


# --------------------------------------------------------------------------
# 持久化（同一 SQLite 文件，独立表）
# --------------------------------------------------------------------------
def _connect():
    db = sqlite3.connect(storage.DB_PATH, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute(
        """CREATE TABLE IF NOT EXISTS compare_jobs(
            id TEXT PRIMARY KEY, owner_id TEXT, data TEXT NOT NULL, created REAL NOT NULL)"""
    )
    return db


def _save(job_id, data, owner):
    with _connect() as db:
        db.execute(
            "INSERT INTO compare_jobs VALUES(?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
            (job_id, owner, json.dumps(data, ensure_ascii=False), time.time()),
        )


def _load(job_id):
    with _connect() as db:
        row = db.execute("SELECT * FROM compare_jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        return None
    return {"owner_id": row["owner_id"], **json.loads(row["data"])}


# --------------------------------------------------------------------------
# 指标计算
# --------------------------------------------------------------------------
def geometric_watertight(mesh):
    """按 3D 位置合并后再判断，忽略 UV 接缝复制，返回(水密, euler)。"""
    from trimesh import grouping

    vertices = mesh.vertices
    _, inv = grouping.unique_rows(vertices)
    g = trimesh.Trimesh(vertices=vertices, faces=inv[mesh.faces], process=True)
    return g.is_watertight, int(g.euler_number)


def drop_degenerate_components(mesh):
    """去除体积解码产生的微小退化碎片（如 3 顶点 2 面的孤立噪声），保留主体。

    规则：按连通体拆分，丢弃面数低于 max(100, 总面数 0.1%) 的体。
    主体器物本身面数远大于该阈值，不会被误删。
    """
    from trimesh import grouping

    vertices = mesh.vertices
    _, inv = grouping.unique_rows(vertices)
    merged = trimesh.Trimesh(
        vertices=vertices, faces=inv[mesh.faces], process=True
    )
    bodies = merged.split(only_watertight=False)
    threshold = max(100, int(0.001 * len(merged.faces)))
    keep = [b for b in bodies if len(b.faces) >= threshold]
    if not keep or len(keep) == len(bodies):
        # 全部被判定为碎片时原样返回，避免误删；无碎片时也避免无谓重建。
        return mesh
    cleaned = trimesh.util.concatenate(keep)
    cleaned.merge_vertices()
    return cleaned


def _engine_module(name):
    return __import__(f"app.{name}_engine", fromlist=["reconstruct"])


def _run_compare(job_id, image_bytes, engines, owner):
    started = time.time()
    job_dir = Path(config.OUTPUT_DIR) / "compare" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    try:
        with _gate:
            for name in engines:
                job = _load(job_id)
                if job["status"] == "cancelled":
                    return
                job["results"][name]["status"] = "running"
                job["results"][name]["stage"] = "引擎推理中"
                _save(job_id, job, owner)

                t0 = time.time()
                try:
                    module = _engine_module(name)
                    # 同图对比是串行跑的，每个引擎开跑前先卸掉另一个占显存的模型，
                    # 否则 8GB 卡上 Hunyuan 扩散会被挤到十几分钟。
                    _release_others(name)
                    mesh = module.reconstruct(
                        image_bytes, lambda stage, value: None
                    )
                    mesh = normalize_mesh(orient_upright(mesh), config.DISPLAY_HEIGHT)
                    mesh = drop_degenerate_components(mesh)
                    watertight, euler = geometric_watertight(mesh)
                    glb_path = job_dir / f"{name}.glb"
                    mesh.export(str(glb_path))

                    result = {
                        "status": "success",
                        "engine": name,
                        "vertices": len(mesh.vertices),
                        "faces": len(mesh.faces),
                        "elapsedMs": int((time.time() - t0) * 1000),
                        "geometricWatertight": watertight,
                        "euler": euler,
                        "glbSizeBytes": glb_path.stat().st_size,
                        "meshUrl": f"/api/engine-compare/{job_id}/mesh/{name}.glb",
                    }
                except Exception as exc:  # noqa: BLE001 单个引擎失败不拖垮其他
                    result = {
                        "status": "error",
                        "engine": name,
                        "error": str(exc)[:500],
                        "elapsedMs": int((time.time() - t0) * 1000),
                    }

                job = _load(job_id)
                job["results"][name] = result
                _save(job_id, job, owner)

        job = _load(job_id)
        statuses = [r["status"] for r in job["results"].values()]
        job["status"] = "success" if all(s == "success" for s in statuses) else (
            "partial" if any(s == "success" for s in statuses) else "error"
        )
        job["totalElapsedMs"] = int((time.time() - started) * 1000)
        _save(job_id, job, owner)
    except Exception as exc:  # noqa: BLE001
        job = _load(job_id)
        if job and job["status"] != "cancelled":
            job["status"] = "error"
            job["error"] = str(exc)[:500]
            _save(job_id, job, owner)


# --------------------------------------------------------------------------
# 路由
# --------------------------------------------------------------------------
@router.post("")
async def create_compare(
    file: UploadFile = File(...),
    engines: str = Form(default=""),
    user=Depends(require_user),
):
    image_bytes = await file.read(12 * 1024 * 1024 + 1)
    if len(image_bytes) > 12 * 1024 * 1024:
        raise HTTPException(413, "图片不能超过 12MB")
    try:
        image = Image.open(__import__("io").BytesIO(image_bytes)).convert("RGB")
        image.thumbnail((1600, 1600))
    except Exception:  # noqa: BLE001
        raise HTTPException(422, "无法读取图片") from None

    if engines.strip():
        requested = [x.strip().lower() for x in engines.split(",") if x.strip()]
        unknown = [x for x in requested if x not in SUPPORTED]
        if unknown:
            raise HTTPException(422, f"不支持的引擎：{', '.join(unknown)}")
    else:
        requested = list(DEFAULT_ENGINES)
    # 去重保留顺序；点名了不可用的引擎就直接说明，避免悄悄少跑一个。
    chosen = list(dict.fromkeys(requested))
    not_ready = [name for name in chosen if not _available(name)]
    if not_ready:
        raise HTTPException(409, "这些引擎当前不可用：" + "、".join(not_ready))

    job_id = str(uuid.uuid4())
    results = {
        name: {"engine": name, "status": "pending", "stage": "等待处理"}
        for name in chosen
    }
    job = {
        "compareId": job_id,
        "status": "processing",
        "engines": chosen,
        "results": results,
        "created": time.time(),
    }
    _save(job_id, job, user["id"])
    threading.Thread(
        target=_run_compare,
        args=(job_id, image_bytes, chosen, user["id"]),
        daemon=True,
    ).start()
    return _load(job_id)


@router.get("/{job_id}")
def get_compare(job_id: str, user=Depends(require_user)):
    job = _load(job_id)
    if not job or job["owner_id"] != user["id"]:
        raise HTTPException(404, "对比任务不存在")
    return job


@router.get("/{job_id}/mesh/{engine}.glb")
def compare_mesh(job_id: str, engine: str, user=Depends(require_user)):
    job = _load(job_id)
    if not job or job["owner_id"] != user["id"]:
        raise HTTPException(404, "对比任务不存在")
    if engine not in job["engines"]:
        raise HTTPException(404, "该引擎未参与对比")
    path = Path(config.OUTPUT_DIR) / "compare" / job_id / f"{engine}.glb"
    if not path.is_file():
        raise HTTPException(404, "模型尚未生成")
    return FileResponse(path, media_type="model/gltf-binary")
