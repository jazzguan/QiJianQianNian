# -*- coding: utf-8 -*-
"""Hunyuan 单图 API 闭环：注册/登录 → 上传一张图 → 轮询 → 下载验证 GLB。"""
import time
from pathlib import Path

import requests
import trimesh

BASE = "http://127.0.0.1:8011"
IMAGE = Path(
    r"D:\软创赛\QiJianQianNian\benchmark\三维重建评测_InstantMesh_Meshroom"
    r"\三维重建评测_InstantMesh_Meshroom\InstantMesh\P01\P01-black-glazed-jar.jpg"
)


def main():
    s = requests.Session()
    username = f"hy_{int(time.time()) % 100000}"
    password = "testpass123"
    reg = s.post(
        f"{BASE}/api/auth/register",
        json={"username": username, "password": password},
    )
    if reg.status_code >= 400:
        s.post(
            f"{BASE}/api/auth/login",
            json={"username": username, "password": password},
        ).raise_for_status()
    print("登录成功:", username)

    with open(IMAGE, "rb") as fh:
        resp = s.post(
            f"{BASE}/api/reconstruct",
            files={"file": (IMAGE.name, fh, "image/jpeg")},
        )
    print("上传状态:", resp.status_code, resp.text)
    resp.raise_for_status()
    task_id = resp.json()["taskId"]

    last = None
    while True:
        try:
            t = s.get(f"{BASE}/api/task/{task_id}", timeout=30).json()
        except requests.RequestException as exc:
            print("轮询连接问题，10s 后重试:", type(exc).__name__)
            time.sleep(10)
            continue
        marker = (t["status"], t.get("stage"), t.get("progress"))
        if marker != last:
            print("任务:", marker)
            last = marker
        if t["status"] in {"success", "error"}:
            break
        time.sleep(5)

    if t["status"] != "success":
        print("任务失败:", t.get("error"))
        raise SystemExit(1)

    model = s.get(f"{BASE}/api/model/{task_id}").json()
    print("模型方法:", model["porcelain"]["modelMethod"])
    print("报告:", {k: model["report"][k] for k in
          ("elapsedMs", "vertices", "faces") if k in model["report"]})

    ticket = s.get(
        f"{BASE}/api/files/access",
        params={"path": f"/files/{task_id}/mesh.glb"},
    ).json()
    glb = s.get(BASE + ticket["url"])
    glb.raise_for_status()
    out = Path(r"D:\软创赛\QiJianQianNian\backend\outputs\hunyuan_api_result.glb")
    out.write_bytes(glb.content)
    print("下载 GLB MB:", round(len(glb.content) / (1024 * 1024), 2))
    mesh = trimesh.load(out, force="mesh")
    print("验证 faces:", len(mesh.faces), "vertices:", len(mesh.vertices),
          "watertight:", mesh.is_watertight)


if __name__ == "__main__":
    main()
