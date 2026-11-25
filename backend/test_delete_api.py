# -*- coding: utf-8 -*-
"""删除任务 API 闭环：登录 → 上传 → 取消 → 删除 → 验证记录与文件清理。"""
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8012"
IMAGE = Path(
    r"D:\软创赛\QiJianQianNian\benchmark\三维重建评测_InstantMesh_Meshroom"
    r"\三维重建评测_InstantMesh_Meshroom\InstantMesh\P01\P01-black-glazed-jar.jpg"
)
OUT = Path(r"D:\软创赛\QiJianQianNian\backend\outputs")


def main():
    s = requests.Session()
    username = f"del_{int(time.time()) % 100000}"
    password = "testpass123"
    s.post(
        f"{BASE}/api/auth/register",
        json={"username": username, "password": password},
    )
    print("登录:", username)

    with open(IMAGE, "rb") as fh:
        resp = s.post(
            f"{BASE}/api/reconstruct",
            files={"file": (IMAGE.name, fh, "image/jpeg")},
        )
    resp.raise_for_status()
    task_id = resp.json()["taskId"]
    print("创建任务:", task_id)

    jpg_path = OUT / f"{task_id}.jpg"
    assert jpg_path.is_file(), "上传图应已落盘"
    print("确认上传图存在:", jpg_path.name)

    # 取消任务，使其可删除
    cancel = s.delete(f"{BASE}/api/task/{task_id}")
    cancel.raise_for_status()
    print("取消:", cancel.json())

    # 彻底删除
    deleted = s.delete(f"{BASE}/api/models/{task_id}")
    print("删除响应:", deleted.status_code, deleted.text)
    deleted.raise_for_status()

    # 记录已不存在
    check = s.get(f"{BASE}/api/task/{task_id}")
    print("删除后查询状态码:", check.status_code)
    assert check.status_code == 404, "删除后任务应返回 404"

    # 文件已清理
    assert not jpg_path.exists(), "上传图应已删除"
    for suffix in [".glb", ".preview.glb", ".heatmap.glb"]:
        assert not (OUT / f"{task_id}{suffix}").exists()
    assert not (OUT / f"{task_id}.images").exists()
    print("全部文件与记录已清理，测试通过")


if __name__ == "__main__":
    main()
