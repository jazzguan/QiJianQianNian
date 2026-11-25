# -*- coding: utf-8 -*-
"""用 benchmark 样本评估 Hunyuan 形状输出（面数、水密、耗时），导出 GLB。"""
import sys
import time
from pathlib import Path

from trimesh import grouping

from app import hunyuan_engine

BASE = Path(
    r"D:\软创赛\QiJianQianNian\benchmark\三维重建评测_InstantMesh_Meshroom"
    r"\三维重建评测_InstantMesh_Meshroom\InstantMesh"
)
OUT_DIR = Path(r"D:\软创赛\QiJianQianNian\backend\outputs")


def geometric_watertight(mesh):
    """按 3D 位置合并后的几何水密口径（忽略 UV 接缝复制）。"""
    v = mesh.vertices
    _, inv = grouping.unique_rows(v)
    import trimesh
    g = trimesh.Trimesh(vertices=v, faces=inv[mesh.faces], process=True)
    return g.is_watertight, g.euler_number


def run(sample):
    folder = BASE / sample
    img = next(p for p in folder.glob("*.jpg") if "comparison" not in p.name)
    t0 = time.time()
    mesh = hunyuan_engine.reconstruct(img.read_bytes())
    elapsed = time.time() - t0
    wt, euler = geometric_watertight(mesh)
    out = OUT_DIR / f"hunyuan_{sample.lower()}.glb"
    mesh.export(str(out))
    print(f"{sample}: 顶点 {len(mesh.vertices)} 面 {len(mesh.faces)} "
          f"几何水密 {wt} euler {euler} 耗时 {elapsed:.1f}s "
          f"GLB {out.stat().st_size/MB_:.2f}MB")
    return mesh


MB_ = 1024 * 1024

if __name__ == "__main__":
    samples = sys.argv[1:] or ["P04"]
    for s in samples:
        run(s)
