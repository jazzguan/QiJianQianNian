# -*- coding: utf-8 -*-
import trimesh

NEW = r"D:\软创赛\QiJianQianNian\backend\outputs\554effe9-c1c6-4283-a685-9f8192183bbe.glb"
OLD = r"D:\meshroom_work\mv01\output\texturedMesh.glb"

for label, path in (("NEW API", NEW), ("OLD direct", OLD)):
    s = trimesh.load(path, force="scene")
    total = sum(len(g.faces) for g in s.geometry.values())
    print(f"--- {label}: {len(s.geometry)} geometries, total faces {total}")
    print("  bounds:", s.bounds)
