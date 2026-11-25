# -*- coding: utf-8 -*-
"""重建引擎选择 API 闭环：登录 → 指定 engine 上传 → 轮询 → 校验产物标记。

用法:
    python test_engine_select_api.py [端口] [引擎]
    python test_engine_select_api.py 8000 triposr
    python test_engine_select_api.py 8000 hunyuan
"""
import sys
import time
from pathlib import Path

import requests

PORT = sys.argv[1] if len(sys.argv) > 1 else "8000"
ENGINE = sys.argv[2] if len(sys.argv) > 2 else "triposr"
BASE = f"http://127.0.0.1:{PORT}"
IMAGE = Path(
    r"D:\软创赛\QiJianQianNian\benchmark\三维重建评测_InstantMesh_Meshroom"
    r"\三维重建评测_InstantMesh_Meshroom\InstantMesh\P04"
    r"\P04-blue-white-double-ear-jar.jpg"
)


def login(session):
    username = f"eng_{int(time.time()) % 1000000}"
    password = "testpass123"
    session.post(
        f"{BASE}/api/auth/register",
        json={"username": username, "password": password},
    )
    resp = session.post(
        f"{BASE}/api/auth/login",
        json={"username": username, "password": password},
    )
    resp.raise_for_status()
    print("登录:", username)


def main():
    session = requests.Session()
    login(session)

    # 1) 非法引擎必须 400，不能悄悄跑默认引擎
    with open(IMAGE, "rb") as fh:
        bad = session.post(
            f"{BASE}/api/reconstruct",
            files={"file": (IMAGE.name, fh, "image/jpeg")},
            data={"engine": "not-a-real-engine"},
        )
    assert bad.status_code == 400, f"期望 400，实际 {bad.status_code}: {bad.text}"
    print("非法引擎被拒:", bad.json()["detail"])

    # 2) 指定引擎创建任务，返回值里应回显 engine
    with open(IMAGE, "rb") as fh:
        created = session.post(
            f"{BASE}/api/reconstruct",
            files={"file": (IMAGE.name, fh, "image/jpeg")},
            data={"engine": ENGINE},
        )
    created.raise_for_status()
    payload = created.json()
    print("创建任务:", payload)
    assert payload.get("engine") == ENGINE, payload
    task_id = payload["taskId"]

    last = None
    status = {}
    while True:
        status = session.get(f"{BASE}/api/task/{task_id}", timeout=30).json()
        state = (status["status"], status.get("stage"), status.get("progress"))
        if state != last:
            print("状态:", state)
            last = state
        if status["status"] in ("success", "error", "cancelled"):
            break
        time.sleep(2)
    assert status["status"] == "success", status.get("error")

    model = session.get(f"{BASE}/api/model/{task_id}", timeout=30).json()
    report = model.get("report") or {}
    method = model["porcelain"].get("modelMethod", "")
    print("引擎标记:", method)
    print("顶点/面数:", report.get("vertices"), "/", report.get("faces"))
    print("耗时秒:", round((report.get("elapsedMs") or 0) / 1000, 1))
    assert ENGINE.upper() in method, f"产物的 modelMethod 未标记 {ENGINE}: {method}"
    print("PASS", ENGINE)


if __name__ == "__main__":
    main()
