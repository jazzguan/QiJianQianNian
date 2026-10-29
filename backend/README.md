# 器见千年 · 三维重建后端（TripoSR CPU）

基于 [VAST-AI-Research/TripoSR](https://github.com/VAST-AI-Research/TripoSR) 的单图三维重建服务，
运行于 CPU（无 NVIDIA GPU 环境）。提供真实重建、可观测性分析与不确定性热力图。

> 重要：本服务只做**真实推理**，不伪造结果。不确定性为**基于可观测性的启发式估计**，不是真实概率置信度。

## 1. 环境要求

- Anaconda / conda
- Python 3.11（TripoSR 依赖兼容性最好）
- 无 GPU 也可运行（CPU 推理）

## 2. 安装

```bash
cd backend

# 1) 克隆 TripoSR 仓库（已克隆可跳过）
git clone --depth 1 https://github.com/VAST-AI-Research/TripoSR.git

# 2) 建 conda 环境
conda create -n qjqn python=3.11 -y

# 3) 安装 torch CPU 版
"D:/SoftWare/Anaconda/envs/qjqn/python.exe" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 4) 安装其余依赖
"D:/SoftWare/Anaconda/envs/qjqn/python.exe" -m pip install -r requirements.txt

# 5) 下载模型权重（首次运行会自动下载到 HF 缓存）
#    若 HuggingFace 访问慢/被墙，先设置镜像再运行：
#    export HF_ENDPOINT=https://hf-mirror.com
```

> 已对 `TripoSR/tsr/models/isosurface.py` 打补丁：用 `scikit-image` 的 marching cubes 替代
> `torchmcubes`（后者是 C++ 扩展，Windows 无 MSVC 会编译失败）。这是唯一的第三方改动。

## 3. 启动服务

```bash
cd backend
"D:/SoftWare/Anaconda/envs/qjqn/python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

首次启动会在后台加载模型权重（约 250MB），`/health` 返回 `modelLoaded: true` 表示就绪。

## 4. API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查（模型是否已加载） |
| POST | `/api/reconstruct` | 上传图片（multipart `file`），返回 `{taskId, status}` |
| GET | `/api/task/{taskId}` | 查询任务状态 `processing / success / error` |
| GET | `/api/model/{taskId}` | 成功后返回 `{modelUrl, heatmapUrl, report, shape, note}` |
| GET | `/files/{taskId}/mesh.glb` | 原始纹理 GLB |
| GET | `/files/{taskId}/heatmap.glb` | 不确定性热力图 GLB |

## 5. 输出与不确定性

- `mesh.glb`：TripoSR 重建网格（含顶点色纹理），归一化到展示高度、底部置 y=0。
- `heatmap.glb`：逐顶点可观测性热力图（蓝=可观测/低不确定，红=推断/高不确定）。
- `report`：顶点/面数、水密性、尺寸、可观测/推断比例、耗时，以及明确标注"启发式、非置信度"。

可观测性计算：`uncertainty = 1 - dot(vertex_normal, view_dir)`，其中 `view_dir = +z`（启发式假设相机朝向）。
这是区分"照片直接可见区域"与"背面/底部推断区域"的简化代理，非真实重建误差。

## 6. 已知限制

- 无 GPU，单张约 1–3 分钟（分辨率 256）。
- 背面/底部为模型推断结果，不代表真实文物数据。
- 首次运行需联网下载权重与 rembg 的 u2net 模型。

## 7. 历史演化接口（本地 JSON 数据）

历史演化功能当前使用 `backend/data/timeline.json`，不依赖外部数据库。
服务启动后提供以下接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/timeline` | 返回唐、宋、元、明、清朝代列表 |
| GET | `/api/timeline/{dynasty}` | 返回指定朝代的代表瓷器 |
| GET | `/api/porcelain/{porcelain_id}` | 按 ID 返回瓷器详情 |
| POST | `/api/evolution/match` | 按器型类别返回跨朝代匹配结果 |

匹配请求示例：

```json
{"category": "梅瓶"}
```

匹配响应格式：

```json
{
  "matches": [
    {
      "dynasty": "yuan",
      "porcelainId": "yuan-qinghua",
      "difference": "与上传器物同属元代青花梅瓶，器型最为接近，可作为同期参照。"
    }
  ]
}
```

该本地数据方案便于当前分支开发和演示。后续接入 SQLite 或 PostgreSQL 时，保持上述接口结构即可替换数据访问层。

前端开发服务器已配置 `/api` 到 `http://localhost:8000` 的代理。将 `VITE_USE_MOCK=false` 后，历史演化页面会请求本地 FastAPI 接口；保持默认值则继续使用前端 Mock 数据。
