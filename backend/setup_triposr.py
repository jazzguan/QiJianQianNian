"""下载官方 TripoSR 源码，安装 Windows CPU marching cubes 适配。"""
import io
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

root = Path(__file__).resolve().parent / 'TripoSR'
root.mkdir(exist_ok=True)
with urlopen(Request('https://codeload.github.com/VAST-AI-Research/TripoSR/zip/refs/heads/main',headers={'User-Agent':'QiJianQianNian'}),timeout=90) as response:
    archive = zipfile.ZipFile(io.BytesIO(response.read()))
for item in archive.infolist():
    relative = Path(*Path(item.filename).parts[1:])
    destination = (root / relative).resolve()
    if not destination.is_relative_to(root.resolve()): raise RuntimeError('源码路径无效')
    if item.is_dir(): destination.mkdir(parents=True,exist_ok=True)
    else:
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(archive.read(item))
# 上游依赖 torchmcubes 的 C++ 扩展；CPU 使用相同等值面算法的 scikit-image 实现。
(root/'torchmcubes.py').write_text('''import torch
from skimage.measure import marching_cubes as extract
def marching_cubes(volume, level):
    vertices, faces, _, _ = extract(volume.detach().cpu().numpy(), level=level)
    return torch.from_numpy(vertices[:, ::-1].copy()), torch.from_numpy(faces.copy()).long()
''',encoding='utf-8')
print('TripoSR 源码与 CPU 适配已准备')
