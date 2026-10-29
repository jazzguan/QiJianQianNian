# 器见千年：瓷器智能学习与演化分析平台

“器见千年”是一个面向中国古代瓷器学习的 Web 3D 平台。用户可以浏览不同历史时期的瓷器，旋转观察三维模型，比较器型和装饰变化，并通过 AI 讲解理解文物背后的历史信息。

> 一张照片，重现一件文物；一条时间轴，探索千年文明。

## 当前功能

- **首页**：平台入口和功能导航。
- **三维复原**：上传单张瓷器图片，调用 TripoSR 生成 GLB 三维模型；同时提供不确定性热力图和质量报告。
- **历史演化**：浏览唐、宋、元、明、清五个时期的代表瓷器；支持上传器物后的同类历史案例匹配。
- **形态对比**：并排查看两个时期的瓷器模型和形态参数。
- **AI 讲解**：按器口、器颈、器身、器足和纹饰查看讲解内容。

当前历史演化后端使用本地 JSON 数据文件，FastAPI 接口已经接入前端；形态对比和 AI 问答仍保留 Mock 数据。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 前端 | React 18、TypeScript、Vite 5、Tailwind CSS 4、Three.js、React Three Fiber |
| 后端 | Python 3.11、FastAPI、Uvicorn、TripoSR、trimesh |
| 历史演化数据 | `backend/data/timeline.json` |
| 模型格式 | GLB / glTF |

## 项目结构

```text
.
├── src/
│   ├── api/                         # 前端请求层，支持 Mock / FastAPI
│   ├── components/                  # 3D 查看器、时间轴、对比等公共组件
│   ├── mock/                        # 前端演示数据
│   ├── pages/                       # 首页、三维复原、历史演化等页面
│   ├── services/                    # 三维复原服务
│   └── types/                       # 共享 TypeScript 类型
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI 应用入口
│   │   ├── timeline.py              # 历史演化路由
│   │   ├── timeline_service.py      # 历史演化数据访问与匹配
│   │   ├── schemas.py               # FastAPI/Pydantic 数据模型
│   │   ├── triposr_engine.py        # TripoSR 推理
│   │   └── uncertainty.py            # 归一化和不确定性热力图
│   ├── data/
│   │   └── timeline.json            # 五朝代瓷器和匹配数据
│   ├── outputs/                     # 三维复原生成的 GLB 文件
│   ├── requirements.txt
│   └── README.md
├── docs/
│   ├── API.md
│   └── backend-contracts.md
├── package.json
└── vite.config.ts
```

## 环境要求

- Node.js 18 或更高版本（推荐 Node.js 20+）
- Python 3.11
- Anaconda / Miniconda
- 运行真实三维复原需要能够下载 TripoSR 权重；历史演化接口本身不需要模型权重

以下命令均以项目根目录为当前目录。Windows PowerShell 下使用 `&` 调用带空格或特殊字符的可执行文件路径。

## 前端安装与启动

```powershell
npm install
npm run dev
```

开发服务器默认地址：<http://localhost:5173>

Vite 已配置 `/api` 代理到 `http://localhost:8000`。

### 使用真实历史演化接口

在项目根目录创建 `.env.local`：

```env
VITE_USE_MOCK=false
VITE_RECONSTRUCT_BASE=http://localhost:8000
```

未设置 `VITE_USE_MOCK=false` 时，时间轴、对比和 AI 页面会使用前端 Mock 数据。设置后，历史演化页面会请求 FastAPI 的时间轴接口。

## 后端安装与启动

进入后端目录：

```powershell
cd backend
```

### 1. 创建环境

```powershell
conda create -n qjqn python=3.11 -y
conda activate qjqn
```

### 2. 安装 PyTorch CPU 版

```powershell
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### 3. 安装其他依赖

```powershell
python -m pip install -r requirements.txt
```

### 4. 准备 TripoSR 源码

如果 `backend/TripoSR` 目录为空，需要执行：

```powershell
git clone --depth 1 https://github.com/VAST-AI-Research/TripoSR.git backend/TripoSR
```

首次运行 TripoSR 时还会从 Hugging Face 下载模型权重。国内网络较慢时，可以先设置：

```powershell
$env:HF_ENDPOINT="https://hf-mirror.com"
```

### 5. 启动 FastAPI

当前目录应为 `backend`：

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

健康检查：<http://localhost:8000/health>

## 历史演化 API

历史演化数据位于 `backend/data/timeline.json`，不依赖外部数据库。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/timeline` | 返回五个朝代的时间轴信息 |
| GET | `/api/timeline/{dynasty}` | 返回指定朝代的代表瓷器 |
| GET | `/api/porcelain/{porcelain_id}` | 按 ID 返回瓷器详情 |
| POST | `/api/evolution/match` | 按器型类别返回跨朝代历史匹配 |

匹配请求示例：

```json
{"category": "梅瓶"}
```

匹配响应示例：

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

历史演化后端代码边界：

- `backend/app/timeline.py`：只负责路由和 HTTP 状态码。
- `backend/app/timeline_service.py`：负责读取 JSON、查询和匹配规则。
- `backend/app/schemas.py`：负责接口数据结构。
- `backend/data/timeline.json`：负责首期数据内容。

将来迁移到 SQLite 或 PostgreSQL 时，优先替换 `timeline_service.py` 的数据访问实现，并保持 API 响应结构不变。

## 三维复原 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 服务健康状态和模型加载状态 |
| POST | `/api/reconstruct` | 上传图片并创建重建任务 |
| GET | `/api/task/{task_id}` | 查询任务状态 |
| GET | `/api/model/{task_id}` | 获取 GLB 地址、轮廓和质量报告 |
| GET | `/files/{task_id}/mesh.glb` | 下载原始纹理模型 |
| GET | `/files/{task_id}/heatmap.glb` | 下载不确定性热力图模型 |

单张图片无法获得文物背面和内部结构，三维复原结果属于探索性数字复原。不确定性热力图是基于可观测性的启发式估计，不是真实概率置信度。

## 验证方式

前端构建：

```powershell
npm run build
```

历史演化接口可用以下方式检查：

```powershell
Invoke-RestMethod http://localhost:8000/api/timeline
Invoke-RestMethod http://localhost:8000/api/porcelain/yuan-qinghua
Invoke-RestMethod -Uri http://localhost:8000/api/evolution/match `
  -Method Post -ContentType "application/json" -Body '{"category":"梅瓶"}'
```

## 协作说明

- `src/types/porcelain.ts` 是前端共享类型定义的位置。
- 页面应通过 `src/api/*.ts` 获取数据，不要在页面内直接读取 Mock 数据。
- 历史演化数据修改优先编辑 `backend/data/timeline.json`。
- 不要提交 `node_modules/`、`dist/`、模型缓存、临时日志和本地环境文件。
- 形态对比、AI 讲解等后续后端接口约定见 `docs/backend-contracts.md`。
