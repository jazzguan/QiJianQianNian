"""后端配置：路径、模型标识、归一化约定。"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# TripoSR 仓库克隆目录（含 tsr 包）
TRIPOSR_DIR = os.path.join(BASE_DIR, "TripoSR")
SF3D_DIR = os.path.join(BASE_DIR, "SF3D")

# Meshroom 便携版目录（含 meshroom_batch.exe），可用环境变量覆盖
MESHROOM_DIR = os.environ.get(
    "MESHROOM_DIR", os.path.join(BASE_DIR, "cache", "Meshroom-2023.3.0")
)
MESHROOM_BATCH = os.path.join(MESHROOM_DIR, "meshroom_batch.exe")

# Hunyuan3D-2 代码目录（archive 解压，非 git）与本地权重根目录
HUNYUAN_DIR = os.path.join(BASE_DIR, "cache", "Hunyuan3D-2-main")
HUNYUAN_MODEL_ROOT = os.path.join(BASE_DIR, "cache", "hy3dgen")
HUNYUAN_REPO = "tencent/Hunyuan3D-2mini"
HUNYUAN_SUBFOLDER = "hunyuan3d-dit-v2-mini"
# 形状推理参数（8GB 显存实测可跑）
HUNYUAN_STEPS = int(os.environ.get("HUNYUAN_STEPS", "30"))
HUNYUAN_OCTREE = int(os.environ.get("HUNYUAN_OCTREE", "256"))

# 生成产物目录
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.environ.setdefault('HF_HOME',os.path.join(BASE_DIR,'cache','huggingface'))
os.environ.setdefault('U2NET_HOME',os.path.join(BASE_DIR,'cache','rembg'))

# HuggingFace 模型标识（TripoSR 官方权重）
MODEL_ID = "stabilityai/TripoSR"
CONFIG_NAME = "config.yaml"
WEIGHT_NAME = "model.ckpt"

# 归一化约定：重建网格统一缩放到"展示高度"，底部置于 y=0，
# 便于前端查看器按相同坐标系取景。单位无物理意义，仅用于展示。
DISPLAY_HEIGHT = 30.0

# 重建分辨率（marching cubes 网格密度）
RESOLUTION = int(os.environ.get('TRIPOSR_RESOLUTION','128'))
