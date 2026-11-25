# -*- coding: utf-8 -*-
"""InstantMesh 端到端联通测试：真实调用三阶段并加载返回的 GLB。"""
import os
import time
from pathlib import Path

import trimesh
from gradio_client import Client, handle_file

SERVICE = "https://tencentarc-instantmesh.hf.space/"
INPUT = Path(
    r"D:\软创赛\QiJianQianNian\benchmark\三维重建评测_InstantMesh_Meshroom"
    r"\三维重建评测_InstantMesh_Meshroom\InstantMesh\P01\P01-black-glazed-jar.jpg"
)


def main():
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    print("hf token:", "configured" if token else "anonymous")
    client = Client(
        SERVICE,
        hf_token=token or None,
        verbose=False,
        httpx_kwargs={"timeout": 180},
    )

    t0 = time.time()
    print("[1/3] preprocess ...")
    processed = client.predict(handle_file(str(INPUT)), True, api_name="/preprocess")
    print("   ->", processed, f"{time.time()-t0:.1f}s")

    print("[2/3] generate_mvs ...")
    mvs = client.predict(processed, 75, 42, api_name="/generate_mvs")
    print("   ->", mvs, f"{time.time()-t0:.1f}s")

    print("[3/3] make3d ...")
    obj_path, glb_path = client.predict(api_name="/make3d")
    print("   obj:", obj_path)
    print("   glb:", glb_path, f"{time.time()-t0:.1f}s")

    mesh = trimesh.load(glb_path, force="mesh")
    print("loaded mesh:", type(mesh).__name__)
    print("vertices:", len(mesh.vertices), "faces:", len(mesh.faces))
    print("has vertex colors:", hasattr(mesh.visual, "vertex_colors"))
    print("total wall:", f"{time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
