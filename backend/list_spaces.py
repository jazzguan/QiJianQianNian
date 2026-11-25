# -*- coding: utf-8 -*-
import httpx

r = httpx.get(
    "https://huggingface.co/api/spaces",
    params={"search": "InstantMesh", "limit": 50},
    timeout=30,
)
for x in r.json():
    print(
        x["id"],
        "| sdk:", x.get("sdk"),
        "| hw:", x.get("hardware"),
        "| likes:", x.get("likes"),
    )
