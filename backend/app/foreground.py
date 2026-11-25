"""Lightweight U2NetP foreground segmentation without rembg's PyMatting import."""
import hashlib
import os
import threading
from pathlib import Path
from urllib import request

import numpy as np
from PIL import Image


MODEL_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx"
MODEL_MD5 = "8e83ca70e441ab06c318d82300c84806"
_lock = threading.Lock()
_session = None


def _model_path() -> Path:
    root = Path(os.environ.get("U2NET_HOME", Path(__file__).resolve().parents[1] / "cache" / "rembg"))
    return root / "u2netp.onnx"


def _ensure_model() -> Path:
    path = _model_path()
    if path.is_file() and hashlib.md5(path.read_bytes()).hexdigest() == MODEL_MD5:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".onnx.download")
    try:
        req = request.Request(MODEL_URL, headers={"User-Agent": "QiJianQianNian"})
        with request.urlopen(req, timeout=120) as response, temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        if hashlib.md5(temporary.read_bytes()).hexdigest() != MODEL_MD5:
            raise RuntimeError("U2NetP 模型校验失败")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def get_session():
    """Create the CPU ONNX session once and reuse it for every reconstruction."""
    global _session
    with _lock:
        if _session is not None:
            return _session
        import onnxruntime as ort

        options = ort.SessionOptions()
        options.log_severity_level = 3
        options.intra_op_num_threads = min(8, os.cpu_count() or 1)
        _session = ort.InferenceSession(
            str(_ensure_model()),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        return _session


def remove_background(image: Image.Image) -> Image.Image:
    """Return RGBA foreground using rembg U2NetP's default preprocessing."""
    session = get_session()
    original = image.convert("RGBA")
    resized = image.convert("RGB").resize((320, 320), Image.Resampling.LANCZOS)
    array = np.asarray(resized, dtype=np.float32)
    array /= max(float(np.max(array)), 1e-6)
    mean = np.asarray((0.485, 0.456, 0.406), dtype=np.float32)
    std = np.asarray((0.229, 0.224, 0.225), dtype=np.float32)
    tensor = ((array - mean) / std).transpose(2, 0, 1)[None].astype(np.float32)
    input_name = session.get_inputs()[0].name
    prediction = session.run(None, {input_name: tensor})[0][:, 0, :, :]
    low, high = float(np.min(prediction)), float(np.max(prediction))
    prediction = (prediction - low) / max(high - low, 1e-6)
    mask = Image.fromarray((np.squeeze(prediction) * 255).astype(np.uint8), mode="L")
    original.putalpha(mask.resize(original.size, Image.Resampling.LANCZOS))
    return original
