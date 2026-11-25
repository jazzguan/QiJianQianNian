# -*- coding: utf-8 -*-
"""多引擎同图对比 API 闭环：登录 → 上传图 → 轮询 → 下载各引擎 GLB 验证。"""
import sys
import time
from pathlib import Path

import requests
import trimesh

PORT = sys.argv[1] if len(sys.argv) > 1 else "8012"
BASE = f"http://127.0.0.1:{PORT}"
IMAGE = Path(
    r"D:\软创赛\QiJianQianNian\benchmark\三维重建评测_InstantMesh_Meshroom"
    r"\三维重建评测_InstantMesh_Meshroom\InstantMesh\P01\P01-black-glazed-jar.jpg"
)


def main():
    s = requests.Session()
    username = f"cmp_{int(time.time()) % 100000}"
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
            f"{BASE}/api/engine-compare",
            files={"file": (IMAGE.name, fh, "image/jpeg")},
            data={"engines": "triposr,hunyuan"},
        )
    print("创建对比:", resp.status_code, resp.text)
    resp.raise_for_status()
    job_id = resp.json()["compareId"]
    engines = resp.json()["engines"]

    last = None
    while True:
        job = s.get(f"{BASE}/api/engine-compare/{job_id}", timeout=30).json()
        states = {k: v["status"] for k, v in job["results"].items()}
        if states != last:
            print("状态:", job["status"], states)
            last = states
        if job["status"] in {"success", "partial", "error"}:
            break
        time.sleep(5)

    print("最终状态:", job["status"], "总耗时ms:", job.get("totalElapsedMs"))
    for name in engines:
        r = job["results"][name]
        if r["status"] != "success":
            print("引擎失败:", name, r.get("error"))
            continue
        print(f"  {name}: 顶点 {r['vertices']} 面 {r['faces']} "
              f"耗时 {r['elapsedMs']}ms 几何水密 {r['geometricWatertight']} "
              f"euler {r['euler']}")
        glb = s.get(BASE + r["meshUrl"])
        glb.raise_for_status()
        out = Path(rf"D:\软创赛\QiJianQianNian\backend\outputs\compare_{name}.glb")
        out.write_bytes(glb.content)
        mesh = trimesh.load(out, force="mesh")
        print(f"    下载验证: {len(mesh.faces)} 面, GLB {len(glb.content)/1024/1024:.2f}MB")

    if not any(job["results"][e]["status"] == "success" for e in engines):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
