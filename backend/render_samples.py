# -*- coding: utf-8 -*-
"""用 matplotlib 离屏渲染 GLB 多视角，输出 PNG 核对形态。"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh

OUT = Path(r"D:\软创赛\QiJianQianNian\backend\outputs")


def load_simplified(glb_path, target=20000):
    mesh = trimesh.load(glb_path, force="mesh")
    if len(mesh.faces) > target:
        mesh = mesh.simplify_quadric_decimation(face_count=target)
    return mesh


def render(glb_path, name):
    mesh = load_simplified(glb_path)
    # 每个面的三角片
    tri = mesh.vertices[mesh.faces]
    views = {"front": (20, -90), "side": (20, 0), "back": (20, 90), "top": (89, -90)}
    for view, (elev, azim) in views.items():
        fig = plt.figure(figsize=(5, 5))
        ax = fig.add_subplot(111, projection="3d")
        coll = Poly3DCollection(tri, facecolor=(0.7, 0.7, 0.72),
                                edgecolor="none", linewidths=0)
        ax.add_collection3d(coll)
        c = mesh.bounding_box.centroid
        s = mesh.scale * 0.6
        ax.set_xlim(c[0]-s, c[0]+s); ax.set_ylim(c[1]-s, c[1]+s)
        ax.set_zlim(c[2]-s, c[2]+s)
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        p = OUT / f"{name}_{view}.png"
        fig.savefig(p, dpi=110, bbox_inches="tight", pad_inches=0)
        plt.close(fig)
        print("saved", p)


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2])
