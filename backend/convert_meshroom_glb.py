# -*- coding: utf-8 -*-
"""把 Meshroom 输出的带贴图 OBJ 转换为单文件 GLB 并验证可重新加载。"""
import os

import trimesh

OBJ = r"D:\meshroom_work\mv01\output\texturedMesh.obj"
GLB = r"D:\meshroom_work\mv01\output\texturedMesh.glb"


def main():
    scene = trimesh.load(OBJ, force="scene")
    print("scene geometries:", len(scene.geometry))
    scene.export(GLB)
    print("glb MB:", round(os.path.getsize(GLB) / (1024 * 1024), 2))
    reloaded = trimesh.load(GLB, force="scene")
    print("reload geometries:", len(reloaded.geometry))
    mesh = trimesh.load(GLB, force="mesh")
    print("mesh faces:", len(mesh.faces))
    print("mesh vertices:", len(mesh.vertices))


if __name__ == "__main__":
    main()
