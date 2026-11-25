# -*- coding: utf-8 -*-
"""拦截 InstantMesh 的 SSE 原始消息，定位 generate_mvs 的真实报错。"""
import json

import httpx
from gradio_client import Client, handle_file
from gradio_client.client import ServerMessage  # noqa: F401

SERVICE = "https://tencentarc-instantmesh.hf.space/"
INPUT = r"D:\软创赛\QiJianQianNian\benchmark\三维重建评测_InstantMesh_Meshroom\三维重建评测_InstantMesh_Meshroom\InstantMesh\P01\P01-black-glazed-jar.jpg"


def install_spy(client):
    def spy_stream_messages(protocol, session_hash):
        try:
            httpx_kwargs = client.httpx_kwargs.copy()
            httpx_kwargs.setdefault("timeout", httpx.Timeout(timeout=None))
            with httpx.Client(verify=client.ssl_verify, **httpx_kwargs) as hc:
                with hc.stream(
                    "GET", client.sse_url,
                    params={"session_hash": session_hash},
                    headers=client.headers, cookies=client.cookies,
                ) as response:
                    buffer = b""
                    for chunk in response.iter_bytes():
                        buffer += chunk
                        while b"\n\n" in buffer:
                            line, buffer = buffer.split(b"\n\n", 1)
                            line = line.decode("utf-8").rstrip("\n")
                            if not line:
                                continue
                            if line.startswith("data:"):
                                resp = json.loads(line[5:])
                                print("=== SSE MSG ===")
                                print(json.dumps(resp, ensure_ascii=False, indent=2))
                                if resp.get("msg") == ServerMessage.heartbeat:
                                    continue
                                event_id = resp["event_id"]
                                client.pending_messages_per_event.setdefault(
                                    event_id, []
                                ).append(resp)
                            else:
                                print("NON-DATA LINE:", line)
        except httpx.RemoteProtocolError:
            return

    client.stream_messages = spy_stream_messages


def main():
    client = Client(SERVICE, verbose=False, httpx_kwargs={"timeout": 180})
    install_spy(client)
    processed = client.predict(handle_file(INPUT), True, api_name="/preprocess")
    print("preprocessed:", processed)
    try:
        mvs = client.predict(processed, 75, 42, api_name="/generate_mvs")
        print("mvs:", mvs)
    except Exception as exc:  # noqa: BLE001
        print("PREDICT RAISED:", type(exc).__name__, str(exc))


if __name__ == "__main__":
    main()
