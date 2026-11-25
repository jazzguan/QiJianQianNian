# -*- coding: utf-8 -*-
"""诊断 Hunyuan 形状输出在不同处理阶段的水密性。"""
from pathlib import Path

from app import hunyuan_engine

INPUT = Path(
    r"D:\软创赛\QiJianQianNian\benchmark\三维重建评测InstantMesh_Meshroom"
    r"\三维重建评测_InstantMesh_Meshroom\InstantMesh\P01\P01-black-glazed-jar.jpg"
)
if not INPUT.exists():
    INPUT = Path(
        r"D:\软创赛\QiJianQianNian\benchmark\三维重建评测_InstantMesh_Meshroom"
        r"\三维重建评测_InstantMesh_Meshroom\InstantMesh\P01\P01-black-glazed-jar.jpg"
    )

mesh = hunyuan_engine.reconstruct(INPUT.read_bytes())
print("原始输出: watertight", mesh.is_watertight, "euler", mesh.euler_number)
print("  顶点", len(mesh.vertices), "面", len(mesh.faces))

proc = mesh.process()
print("process 后: watertight", proc.is_watertight, "euler", proc.euler_number,
      "面", len(proc.faces))

tmp = Path(r"D:\软创赛\QiJianQianNian\backend\cache\wt_check.glb")
proc.export(str(tmp))
import trimesh
back = trimesh.load(str(tmp))
back = back.geometry[list(back.geometry)[0]] if hasattr(back, "geometry") else back
print("导出 GLB 再加载: watertight", back.is_watertight, "euler", back.euler_number)
tmp.unlink()
