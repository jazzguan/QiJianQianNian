# -*- coding: utf-8 -*-
"""用 MV01 的 20 张环绕照片，通过新适配器完整复现 Meshroom 重建。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.meshroom_engine import reconstruct, is_available  # noqa: E402

MV01 = Path(
    r"D:\软创赛\QiJianQianNian\benchmark\三维重建评测_InstantMesh_Meshroom"
    r"\三维重建评测_InstantMesh_Meshroom\Meshroom\MV01\inputs"
)
WORKDIR = Path(r"D:\meshroom_work\mv01")


def main():
    print("available:", is_available())
    images = sorted(
        p for p in MV01.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    print("image count:", len(images))
    WORKDIR.mkdir(parents=True, exist_ok=True)

    def progress(stage, value):
        print(f"[{value:>3}%] {stage}")

    t0 = time.time()
    mesh = reconstruct(
        [str(p) for p in images], progress, workdir=str(WORKDIR)
    )
    wall = time.time() - t0
    print("--- result ---")
    print("type:", type(mesh).__name__)
    print("vertices:", len(mesh.vertices))
    print("faces:", len(mesh.faces))
    print("wall seconds:", round(wall, 1))
    print("source obj:", mesh.metadata.get("source_obj"))


if __name__ == "__main__":
    main()
