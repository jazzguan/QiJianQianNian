# -*- coding: utf-8 -*-
from importlib.metadata import PackageNotFoundError, version

WANT = [
    "ninja", "pybind11", "diffusers", "einops", "opencv-python", "numpy",
    "torch", "transformers", "torchvision", "omegaconf", "trimesh",
    "pymeshlab", "pygltflib", "xatlas", "accelerate", "gradio", "fastapi",
    "uvicorn", "rembg", "onnxruntime", "pillow",
]
for name in WANT:
    try:
        print(f"{name:16} {version(name)}")
    except PackageNotFoundError:
        print(f"{name:16} MISSING")
