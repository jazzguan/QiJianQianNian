"""按仓库名把 Hugging Face 权重下到指定 HF_HOME，供 scripts/fetch_weights.ps1 调用。

单独拆出来是因为 huggingface_hub 在 import 时就读 HF_HOME / HF_ENDPOINT，
不同模型要落不同缓存目录，只能一个仓库一个进程。
"""
import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='下载 Hugging Face 权重到指定缓存目录')
    parser.add_argument('--repo', required=True, help='仓库名，例如 stabilityai/TripoSR')
    parser.add_argument('--home', required=True, help='HF_HOME 目录，权重会落在 <home>/hub 下')
    parser.add_argument('--allow', action='append', default=[], help='只下匹配的子路径，可重复传')
    parser.add_argument('--mirror', default='', help='HF_ENDPOINT，默认直连；国内可传 https://hf-mirror.com')
    args = parser.parse_args()

    os.environ['HF_HOME'] = str(Path(args.home).resolve())
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    if args.mirror:
        os.environ['HF_ENDPOINT'] = args.mirror

    from huggingface_hub import snapshot_download  # noqa: E402  必须在环境变量设好后再导入

    path = snapshot_download(repo_id=args.repo, allow_patterns=args.allow or None)
    print(path)


if __name__ == '__main__':
    main()
