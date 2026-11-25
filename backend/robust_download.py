# -*- coding: utf-8 -*-
"""健壮的分块并行下载：requests + 每块断点续传 + 自动重试 + 进度打印。"""
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

MB = 1024 * 1024
_lock = threading.Lock()
_state = {"done": 0, "last_print": 0}


def head_size(url):
    r = requests.head(url, allow_redirects=True, timeout=30)
    return int(r.headers["content-length"])


def download_part(url, part_path, lo, hi):
    existing = os.path.getsize(part_path) if os.path.exists(part_path) else 0
    if existing > 0:
        with _lock:
            _state["done"] += existing
    cur = lo + existing
    while cur <= hi:
        headers = {"Range": f"bytes={cur}-{hi}"}
        try:
            with requests.get(url, headers=headers, stream=True, timeout=45) as r:
                r.raise_for_status()
                with open(part_path, "ab") as f:
                    for block in r.iter_content(chunk_size=128 * 1024):
                        n = f.write(block)
                        cur += n
                        with _lock:
                            _state["done"] += n
        except requests.RequestException:
            time.sleep(3)
            cur = lo + (os.path.getsize(part_path) if os.path.exists(part_path) else 0)


def progress_monitor(total):
    while True:
        time.sleep(10)
        now = time.time()
        with _lock:
            done = _state["done"]
        pct = done / total * 100
        print(f"  {done/MB:.0f}/{total/MB:.0f} MB ({pct:.1f}%)", flush=True)
        if done >= total:
            return


def download(url, out, workers=8):
    total = head_size(url)
    print(f"总大小 {total/MB:.0f} MB，{workers} 线程")
    span = (total + workers - 1) // workers
    t = threading.Thread(target=progress_monitor, args=(total,), daemon=True)
    t.start()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = []
        for i in range(workers):
            lo = i * span
            hi = min(lo + span - 1, total - 1)
            futures.append(
                ex.submit(download_part, url, f"{out}.part{i}", lo, hi)
            )
        for f in futures:
            f.result()
    with open(out, "wb") as merged:
        for i in range(workers):
            p = f"{out}.part{i}"
            with open(p, "rb") as f:
                merged.write(f.read())
            os.remove(p)
    print(f"完成，实际 {os.path.getsize(out)/MB:.1f} MB")


if __name__ == "__main__":
    download(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8)
