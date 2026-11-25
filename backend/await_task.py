# -*- coding: utf-8 -*-
"""等待指定任务完成（轮询带连接重试）并验证最终 GLB 产物。"""
import sys
import time
from pathlib import Path

import requests
import trimesh

BASE = "http://127.0.0.1:8011"


def poll(session, task_id):
    last = None
    while True:
        try:
            t = session.get(f"{BASE}/api/task/{task_id}", timeout=30).json()
        except requests.RequestException as exc:
            print("轮询连接问题，10s 后重试:", type(exc).__name__)
            time.sleep(10)
            continue
        marker = (t["status"], t.get("stage"), t.get("progress"))
        if marker != last:
            print("任务:", marker)
            last = marker
        if t["status"] in {"success", "error"}:
            return t
        time.sleep(6)


def main():
    task_id = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3] if len(sys.argv) > 3 else "testpass123"

    s = requests.Session()
    login = s.post(
        f"{BASE}/api/auth/login",
        json={"username": username, "password": password},
    )
    login.raise_for_status()
    print("登录成功:", username)

    t = poll(s, task_id)
    if t["status"] != "success":
        print("任务失败:", t.get("error"))
        return

    model = s.get(f"{BASE}/api/model/{task_id}").json()
    print("模型方法:", model["porcelain"]["modelMethod"])
    print("照片数:", model["porcelain"]["imageCount"])

    ticket = s.get(
        f"{BASE}/api/files/access",
        params={"path": f"/files/{task_id}/mesh.glb"},
    ).json()
    glb = s.get(BASE + ticket["url"], timeout=120)
    glb.raise_for_status()
    out = Path(r"D:\meshroom_work\api_result.glb")
    out.write_bytes(glb.content)
    print("下载 GLB MB:", round(len(glb.content) / (1024 * 1024), 2))
    mesh = trimesh.load(out, force="mesh")
    print("验证 faces:", len(mesh.faces), "vertices:", len(mesh.vertices))


if __name__ == "__main__":
    main()
