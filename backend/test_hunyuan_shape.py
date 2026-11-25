# -*- coding: utf-8 -*-
"""Hunyuan3D-2mini 形状生成真实测试（8GB 显存，不编译贴图扩展）。

权重经 robust_download.py 下载到本地 HY3DGEN_MODELS 目录；
单个 DiT safetensors 已含 model/vae/conditioner 三部分权重，无需单独下 VAE；
去背景复用项目已缓存的 u2netp，不额外下载。
"""
import os
import sys
import time
from pathlib import Path

CACHE_ROOT = Path(r"D:\软创赛\QiJianQianNian\backend\cache")
os.environ["HF_HOME"] = str(CACHE_ROOT / "hf_cache")
os.environ["U2NET_HOME"] = str(CACHE_ROOT / "rembg")
# 让 smart_load_model 直接从本地目录加载，不再触发 snapshot_download。
os.environ["HY3DGEN_MODELS"] = str(CACHE_ROOT / "hy3dgen")
# xet 后端在当前网络下会卡住且不写目标文件，强制走经典 HTTP 下载。
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")

ROOT = str(CACHE_ROOT / "Hunyuan3D-2-main")
sys.path.insert(0, ROOT)

import torch  # noqa: E402
from PIL import Image  # noqa: E402
from rembg import remove, new_session  # noqa: E402

from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline  # noqa: E402

INPUT = Path(
    r"D:\软创赛\QiJianQianNian\benchmark\三维重建评测_InstantMesh_Meshroom"
    r"\三维重建评测_InstantMesh_Meshroom\InstantMesh\P01\P01-black-glazed-jar.jpg"
)
OUT = Path(r"D:\软创赛\QiJianQianNian\backend\outputs\hunyuan_mini_shape.glb")


def main():
    print("CUDA:", torch.cuda.get_device_name(0))
    print("[1/3] u2netp 去背景 ...")
    image = Image.open(INPUT).convert("RGB")
    session = new_session("u2netp")
    cut = remove(image, session=session, bgcolor=[255, 255, 255, 0])

    print("[2/3] 加载 mini 管线（首次会下载权重）...")
    t0 = time.time()
    pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
        "tencent/Hunyuan3D-2mini",
        subfolder="hunyuan3d-dit-v2-mini",
        device="cuda",
    )
    print("  加载耗时 %.1fs" % (time.time() - t0))

    print("[3/3] 形状推理 ...")
    t0 = time.time()
    torch.cuda.reset_peak_memory_stats()
    mesh = pipeline(image=cut, num_inference_steps=30, octree_resolution=256)[0]
    torch.cuda.synchronize()
    peak = torch.cuda.max_memory_allocated() / (1024**3)
    print("  推理耗时 %.1fs，峰值显存 %.2f GB" % (time.time() - t0, peak))
    print("  vertices=%d faces=%d" % (len(mesh.vertices), len(mesh.faces)))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(OUT))
    print("已导出:", OUT, "%.2f MB" % (OUT.stat().st_size / 1024**2))


if __name__ == "__main__":
    main()
