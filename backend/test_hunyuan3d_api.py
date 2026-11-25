"""腾讯云「混元生3D」API 冒烟脚本 —— 接入产品前先单独验证效果。

为什么单独写：产品里接第三方 API 之前先确认三件事——能不能通、出模型怎么样、一次扣多少积分。
这个脚本只做这三件事，不动产品代码。

一、开通与拿 key（约 10 分钟，需要你自己操作）
1. 登录 https://console.cloud.tencent.com/ ，搜「混元生3D」进控制台，点「开通」。
2. 控制台里找「免费资源包」，手动领取 100 积分（一次性，1 年有效）。
   极速版一次 15 积分，100 积分够跑 6 次；专业版单价更高，够跑 2～3 次。
3. 打开 https://console.cloud.tencent.com/cam/capi 生成 SecretId / SecretKey（子账号也可以）。
4. 写进 backend/.env（不要提交到仓库）：
       QJQN_TC_SECRET_ID=...
       QJQN_TC_SECRET_KEY=...
   或者临时设环境变量也行。

二、三种模式
    # 图生 3D（照片 → 模型），极速版，15 积分
    python test_hunyuan3d_api.py --mode image --image "D:\...\P04.jpg"

    # 文生 3D（只有文字），极速版，15 积分
    python test_hunyuan3d_api.py --mode text --prompt "青花缠枝莲纹梅瓶，小口、丰肩、敛腹、圈足"

    # 草图 + 文字（唯一能「图和文字同一次请求」的模式），专业版 Sketch，25 积分
    python test_hunyuan3d_api.py --mode sketch --image sketch.png --prompt "青花缠枝莲纹梅瓶，小口丰肩"

注意：腾讯混元生3D 的普通图生 3D **不接受文字提示**（Prompt 和 ImageBase64/ImageUrl 互斥），
只有 GenerateType=Sketch 时两者可以一起传。这是脚本里把 sketch 单独列出来的原因。

三、产出
   backend/outputs/api_test/<mode>_<时间戳>.glb
   终端会打印任务状态、耗时、返回的积分与文件地址。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests

HOST = "ai3d.tencentcloudapi.com"
SERVICE = "ai3d"
VERSION = "2025-05-13"
REGION = os.environ.get("QJQN_TC_REGION", "ap-guangzhou")
OUT_DIR = Path(__file__).resolve().parent / "outputs" / "api_test"


def load_env(path: Path) -> None:
    """极简 .env 读取，避免多装一个依赖。"""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hmac_hex(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def signed_post(action: str, payload: dict) -> dict:
    """TC3-HMAC-SHA256 签名，纯标准库实现。"""
    secret_id = os.environ.get("QJQN_TC_SECRET_ID")
    secret_key = os.environ.get("QJQN_TC_SECRET_KEY")
    if not secret_id or not secret_key:
        sys.exit("缺 QJQN_TC_SECRET_ID / QJQN_TC_SECRET_KEY，先按文件开头步骤开通并填进 backend/.env")

    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    timestamp = int(time.time())
    date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")

    canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{HOST}\n"
    signed_headers = "content-type;host"
    canonical_request = "\n".join(
        ["POST", "/", "", canonical_headers, signed_headers, _sha256_hex(body.encode())]
    )
    hashed_canonical = _sha256_hex(canonical_request.encode())
    scope = f"{date}/{SERVICE}/tc3_request"
    string_to_sign = "\n".join(
        ["TC3-HMAC-SHA256", str(timestamp), scope, hashed_canonical]
    )
    signing_key = _hmac_hex(_hmac_hex(_hmac_hex(secret_key.encode(), date), SERVICE), "tc3_request")
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    headers = {
        "Authorization": (
            f"TC3-HMAC-SHA256 Credential={secret_id}/{scope} "
            f"SignedHeaders={signed_headers} Signature={signature}"
        ),
        "Content-Type": "application/json; charset=utf-8",
        "Host": HOST,
        "X-TC-Action": action,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Version": VERSION,
        "X-TC-Region": REGION,
    }
    resp = requests.post(f"https://{HOST}", headers=headers, data=body, timeout=60)
    resp.raise_for_status()
    data = resp.json().get("Response", {})
    if "Error" in data:
        sys.exit(f"{action} 失败：[{data['Error'].get('Code')}] {data['Error'].get('Message')}")
    return data


def image_to_base64(path: str) -> str:
    raw = Path(path).read_bytes()
    if len(raw) > 5 * 1024 * 1024:
        sys.exit(f"图片 {len(raw)/1024/1024:.1f}MB，超过 5MB（base64 后会更大），先压一下")
    if raw[:3] == b"\xff\xd8\xff":
        mime = "jpeg"
    elif raw[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "png"
    else:
        mime = "jpeg"
    return f"data:image/{mime};base64,{base64.b64encode(raw).decode()}"


def submit(mode: str, image: str | None, prompt: str | None) -> tuple[str, str]:
    """返回 (submit_action, query_action)。"""
    if mode == "image":
        payload = {
            "ImageBase64": image_to_base64(image),
            "ResultFormat": "GLB",
            "EnablePBR": False,
        }
        job = signed_post("SubmitHunyuanTo3DRapidJob", payload)["JobId"]
        return job, "QueryHunyuanTo3DRapidJob"
    if mode == "text":
        payload = {"Prompt": prompt, "ResultFormat": "GLB", "EnablePBR": False}
        job = signed_post("SubmitHunyuanTo3DRapidJob", payload)["JobId"]
        return job, "QueryHunyuanTo3DRapidJob"
    if mode == "sketch":
        payload = {
            "Model": "3.0",
            "ImageBase64": image_to_base64(image),
            "Prompt": prompt,
            "GenerateType": "Sketch",
            "FaceCount": 300000,
            "EnablePBR": False,
        }
        job = signed_post("SubmitHunyuanTo3DProJob", payload)["JobId"]
        return job, "QueryHunyuanTo3DProJob"
    sys.exit(f"未知模式 {mode}")


def poll(query_action: str, job_id: str, interval: int = 5, timeout: int = 900) -> dict:
    started = time.time()
    last = ""
    while time.time() - started < timeout:
        data = signed_post(query_action, {"JobId": job_id})
        status = data.get("Status") or ""
        msg = data.get("ErrorMessage") or data.get("ErrorCode") or ""
        if status != last:
            print(f"[{int(time.time()-started):>4}s] {status} {msg}")
            last = status
        if status == "DONE":
            credits = data.get("ResultCreditConsumed")
            if credits is not None:
                print(f"本次消耗积分：{credits}  {data.get('ResultCreditDetails') or ''}")
            return data
        if status == "FAIL":
            sys.exit(f"任务失败：[{data.get('ErrorCode')}] {msg}")
        time.sleep(interval)
    sys.exit("轮询超时（15 分钟）")


def download(result: dict, mode: str) -> Path:
    files = result.get("ResultFile3Ds") or []
    glb = next((f for f in files if str(f.get("Type", "")).upper() == "GLB"), None)
    if not glb:
        print("返回文件：", json.dumps(files, ensure_ascii=False)[:600])
        sys.exit("没有 GLB 产物，看看上面的返回结构")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / f"{mode}_{datetime.now().strftime('%m%d-%H%M%S')}.glb"
    url = glb["Url"]
    with requests.get(url, timeout=120, stream=True) as resp:
        resp.raise_for_status()
        with open(target, "wb") as handle:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                handle.write(chunk)
    print(f"已保存 {target}  ({target.stat().st_size/1024/1024:.2f}MB)")
    preview = glb.get("PreviewImageUrl")
    if preview:
        print(f"预览图 {preview}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["image", "text", "sketch"], required=True)
    parser.add_argument("--image", help="本地图片路径（image / sketch 模式必填）")
    parser.add_argument("--prompt", help="文字提示（text / sketch 模式必填）")
    args = parser.parse_args()

    if args.mode in ("image", "sketch") and not args.image:
        sys.exit("该模式需要 --image")
    if args.mode in ("text", "sketch") and not args.prompt:
        sys.exit("该模式需要 --prompt")

    load_env(Path(__file__).resolve().parent / ".env")
    print(f"region={REGION}  mode={args.mode}")

    job_id, query_action = submit(args.mode, args.image, args.prompt)
    print(f"已提交，JobId={job_id}，开始轮询…")
    result = poll(query_action, job_id)
    download(result, args.mode)


if __name__ == "__main__":
    main()
