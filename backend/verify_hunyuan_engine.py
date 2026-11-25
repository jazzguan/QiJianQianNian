# -*- coding: utf-8 -*-
"""验证 app.hunyuan_engine 作为后端引擎模块可被直接调用。"""
from pathlib import Path

from app import hunyuan_engine

INPUT = Path(
    r"D:\软创赛\QiJianQianNian\benchmark\三维重建评测_InstantMesh_Meshroom"
    r"\三维重建评测_InstantMesh_Meshroom\InstantMesh\P01\P01-black-glazed-jar.jpg"
)


def show(stage, value):
    print(f"  进度 {value}%：{stage}")


print("is_available:", hunyuan_engine.is_available())
mesh = hunyuan_engine.reconstruct(INPUT.read_bytes(), show)
print("vertices=%d faces=%d" % (len(mesh.vertices), len(mesh.faces)))
print("watertight:", mesh.is_watertight)
print("model_status:", hunyuan_engine.model_status())
