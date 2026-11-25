# -*- coding: utf-8 -*-
import httpx

for repo in ["tencent/Hunyuan3D-2mini", "tencent/Hunyuan3D-2"]:
    print("=====", repo)
    r = httpx.get(
        f"https://huggingface.co/api/models/{repo}",
        params={"blobs": True},
        timeout=30,
    )
    for sib in r.json().get("siblings", []):
        size = sib.get("size")
        if size:
            print(f"  {sib['rfilename']:55} {size/1e6:8.1f} MB")
        else:
            print(f"  {sib['rfilename']:55} (size n/a)")
