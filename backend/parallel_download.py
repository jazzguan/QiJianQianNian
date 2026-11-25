# -*- coding: utf-8 -*-
"""多线程分块并行下载（HTTP Range），用于突破单连接限速。"""
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

MB_ = 1024 * 1024


def get_size(url):
    r = httpx.head(url, follow_redirects=True, timeout=30)
    size = int(r.headers.get("content-length", 0))
    accept = r.headers.get("accept-ranges", "")
    return size, accept


def download(url, out, workers=8, test_seconds=0):
    size, _ = get_size(url)
    if not size:
        raise RuntimeError("无法获取文件大小")
    print(f"文件 {size/MB_:.1f} MB，{workers} 线程")
    chunk = (size + workers - 1) // workers
    progress = {"done": 0}
    lock = threading.Lock()
    start = time.time()

    def fetch(idx):
        lo = idx * chunk
        hi = min(lo + chunk - 1, size - 1)
        headers = {"Range": f"bytes={lo}-{hi}"}
        with httpx.Client(follow_redirects=True, timeout=60) as c:
            with c.stream("GET", url, headers=headers) as r:
                r.raise_for_status()
                local = 0
                with open(f"{out}.part{idx}", "wb") as f:
                    for block in r.iter_bytes(chunk_size=256 * 1024):
                        f.write(block)
                        local += len(block)
                        with lock:
                            progress["done"] += len(block)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(fetch, i) for i in range(workers)]
        if test_seconds:
            time.sleep(test_seconds)
            mb = progress["done"] / 1e6
            print(f"[测速] {test_seconds}s 下载 {mb:.1f} MB，"
                  f"约 {progress['done']/1024/test_seconds:.0f} KB/s")
            return
        for f in futures:
            f.result()

    with open(out, "wb") as merged:
        for i in range(workers):
            p = f"{out}.part{i}"
            with open(p, "rb") as f:
                merged.write(f.read())
            os.remove(p)
    print(f"完成，实际 {os.path.getsize(out)/1e6:.1f} MB，"
          f"用时 {time.time()-start:.0f}s")


if __name__ == "__main__":
    mode = sys.argv[1]
    url = sys.argv[2]
    out = sys.argv[3]
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    if mode == "test":
        download(url, out, workers=workers, test_seconds=15)
    else:
        download(url, out, workers=workers)
