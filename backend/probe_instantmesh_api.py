# -*- coding: utf-8 -*-
"""一次性探查 InstantMesh HF Space 的 API 结构（端点、参数、输出类型）。"""
import json

from gradio_client import Client

SERVICE = "https://tencentarc-instantmesh.hf.space/"


def main():
    client = Client(SERVICE, verbose=False, httpx_kwargs={"timeout": 120})
    info = client.view_api(return_format="dict")
    named_endpoints = info.get("named_endpoints", {})
    print("=== named endpoints ===")
    for name, spec in named_endpoints.items():
        print("\n### endpoint:", name)
        print(json.dumps(spec, ensure_ascii=False, indent=2))
    # 组件类型速览，帮助理解参数编号
    print("\n=== components ===")
    for comp in info.get("components", []):
        print(comp)


if __name__ == "__main__":
    main()
