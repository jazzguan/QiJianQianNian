# -*- coding: utf-8 -*-
"""验证：去除微小退化连通体后，主体水密、euler=2。"""
import trimesh
from trimesh import grouping

path = r"D:\软创赛\QiJianQianNian\backend\outputs\compare\03f998a5-b794-4a9c-959c-5b49e529b89b\hunyuan.glb"
mesh = trimesh.load(path, force="mesh", process=False)

_, inv = grouping.unique_rows(mesh.vertices)
g = trimesh.Trimesh(vertices=mesh.vertices, faces=inv[mesh.faces], process=True)
bodies = g.split(only_watertight=False)
total = len(g.faces)
threshold = max(100, int(0.001 * total))
keep = [b for b in bodies if len(b.faces) >= threshold]
print("原连通体:", len(bodies), "阈值面数:", threshold, "保留:", len(keep))
cleaned = trimesh.util.concatenate(keep)
cleaned.merge_vertices()
cleaned.process()
print("清理后: 顶点", len(cleaned.vertices), "面", len(cleaned.faces),
      "watertight", cleaned.is_watertight, "euler", cleaned.euler_number)
