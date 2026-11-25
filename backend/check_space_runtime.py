# -*- coding: utf-8 -*-
import json

import httpx

CANDIDATES = [
    "TencentARC/InstantMesh",
    "cocktailpeanut/InstantMesh",
    "SIGMitch/InstantMesh",
    "willdphan/InstantMesh",
    "makululinux/InstantMesh-img-to-3D",
]
for sid in CANDIDATES:
    d = httpx.get(f"https://huggingface.co/api/spaces/{sid}", timeout=30).json()
    print("===", sid)
    print("  hardware:", d.get("hardware"))
    print("  runtime:", json.dumps(d.get("runtime"), ensure_ascii=False))
    print("  sdk:", d.get("sdk"), d.get("sdkVersion"))
