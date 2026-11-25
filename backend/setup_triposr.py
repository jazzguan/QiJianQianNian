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
def marching_cubes(volume, level):
    from skimage.measure import marching_cubes as extract
    vertices, faces, _, _ = extract(volume.detach().cpu().numpy(), level=level)
    return torch.from_numpy(vertices[:, ::-1].copy()), torch.from_numpy(faces.copy()).long()
''',encoding='utf-8')
# 大权重在 Windows 上使用普通 torch.load 冷启动很慢；内存映射并直接绑定参数，
# 避免先完整复制 1.68 GB checkpoint。仅改加载方式，不改模型结构和权重。
system_path = root / 'tsr' / 'system.py'
system_source = system_path.read_text(encoding='utf-8')
old_load = '''        ckpt = torch.load(weight_path, map_location="cpu")
        model.load_state_dict(ckpt)'''
new_load = '''        ckpt = torch.load(
            weight_path, map_location="cpu", mmap=True, weights_only=True
        )
        model.load_state_dict(ckpt, assign=True)'''
if old_load in system_source:
    system_path.write_text(system_source.replace(old_load,new_load),encoding='utf-8')
# rembg/onnxruntime 只在分割时使用，避免启动导入 TripoSR 时提前加载。
utils_path = root / 'tsr' / 'utils.py'
utils_source = utils_path.read_text(encoding='utf-8')
utils_source = utils_source.replace('\nimport rembg\n','\n')
utils_source = utils_source.replace(
    '        image = rembg.remove(image, session=rembg_session, **rembg_kwargs)',
    '        import rembg\n        image = rembg.remove(image, session=rembg_session, **rembg_kwargs)',
)
utils_path.write_text(utils_source,encoding='utf-8')
print('TripoSR 源码与 CPU 适配已准备')
