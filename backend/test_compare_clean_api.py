# -*- coding: utf-8 -*-
"""快速验证：8013 新代码下 create 返回完整 results，去噪对 triposr 无副作用。"""
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8013"
IMAGE = Path(
    r"D:\软创赛\QiJianQianNian\benchmark\三维重建评测_InstantMesh_Meshroom"
    r"\三维重建评测_InstantMesh_Meshroom\InstantMesh\P01\P01-black-glazed-jar.jpg"
)


def main():
    s = requests.Session()
    username = f"clean_{int(time.time()) % 100000}"
    reg = s.post(
        f"{BASE}/api/auth/register",
        json={"username": username, "password": "testpass123"},
    )
    if reg.status_code >= 400:
        s.post(
            f"{BASE}/api/auth/login",
            json={"username": username, "password": "testpass123"},
        ).raise_for_status()

    with open(IMAGE, "rb") as fh:
        resp = s.post(
            f"{BASE}/api/engine-compare",
            files={"file": (IMAGE.name, fh, "image/jpeg")},
            data={"engines": "triposr"},
        )
    resp.raise_for_status()
    created = resp.json()
    assert "results" in created, "create 必须返回完整 results"
    print("create 返回字段:", sorted(created.keys()))
    job_id = created["compareId"]

    while True:
        job = s.get(f"{BASE}/api/engine-compare/{job_id}", timeout=30).json()
        if job["status"] in {"success", "partial", "error"}:
            break
        time.sleep(3)

    r = job["results"]["triposr"]
    print("最终:", job["status"])
    print(
        f"triposr: 顶点{r['vertices']} 面{r['faces']} "
        f"水密{r['geometricWatertight']} euler{r['euler']} "
        f"GLB {r['glbSizeBytes']/1024/1024:.2f}MB"
    )
    assert r["status"] == "success"
    print("通过：去噪函数未破坏 triposr 正常流程")


if __name__ == "__main__":
    main()
