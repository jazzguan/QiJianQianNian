"""后端配置：路径、模型标识、归一化约定。"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# TripoSR 仓库克隆目录（含 tsr 包）
TRIPOSR_DIR = os.path.join(BASE_DIR, "TripoSR")

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
