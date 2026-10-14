# 器见千年 —— 瓷器智能学习与演化分析平台

以中国传统瓷器为主题的数字化学习与展示平台。前端为 React 数字博物馆界面，
后端提供基于 TripoSR 的**真实单图三维重建**（CPU 推理）+ 可观测性/不确定性分析。

> 口号：**一张照片，重现一件文物；一条时间轴，探索千年文明。**

四个核心功能：三维复原 · 历史演化 · 形态对比 · AI 讲解。

---

## 技术栈

| 端 | 技术 |
| --- | --- |
| 前端 | React 18 · TypeScript · Vite 5 · Tailwind CSS 4 · Three.js（React Three Fiber + drei） |
| 后端 | Python 3.11 · FastAPI · TripoSR（单图 3D 重建）· scikit-image |

---

## 快速开始

### 独立运行形态对比

在项目根目录执行 `./start-comparison.ps1`，打开 `http://127.0.0.1:8001/comparison`。
支持六项自动测量、GLB导入、同步交互、关键区域定位、轮廓叠加与CSV导出。
运行方式和接口见[形态对比文档](docs/morphology-comparison.md)。

### 环境要求
- Node.js ≥ 18（推荐 20+）
- Anaconda / conda

### 1. 前端

```bash
cd D:\软创
npm install        # 首次
npm run dev        # 开发，打开 http://localhost:5173
```

### 2. 后端（三维重建服务）

首次需安装依赖（详见 `backend/README.md`）：

```bash
cd D:\软创\backend

# 建环境
conda create -n qjqn python=3.11 -y

# 装 torch（CPU 版）
"D:/SoftWare/Anaconda/envs/qjqn/python.exe" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 装其余依赖
"D:/SoftWare/Anaconda/envs/qjqn/python.exe" -m pip install -r requirements.txt

# 启动（PowerShell 记得加 &）
"D:/SoftWare/Anaconda/envs/qjqn/python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> 首次启动会从 HuggingFace 下载模型权重（约 1.7GB + 编码器 330MB），并预热约 30 秒。
> 查看 `http://localhost:8000/health`，`modelLoaded: true` 表示就绪。
> 国内访问 HuggingFace 慢可先设置镜像：`$env:HF_ENDPOINT="https://hf-mirror.com"`（PowerShell）。

### 3. 前端环境变量（可选）

在项目根目录建 `.env.local`：

```bash
# 重建服务地址（默认就是 localhost:8000，一般不用改）
VITE_RECONSTRUCT_BASE=http://localhost:8000

# 设为 true 则三维复原走前端 Mock，不依赖后端（离线演示用）
VITE_USE_MOCK=true
```

---

## 项目结构

```
D:\软创
├── src/                          # 前端源码
│   ├── components/
│   │   ├── PorcelainViewer/      # ★ 公共 3D 查看器（模型加载/旋转/部位点击/热力图）
│   │   ├── CompareViewer/        # 双模型对比
│   │   ├── Timeline/             # 历史时间轴
│   │   ├── EvolutionModeSwitch/  # 个性化模式切换条
│   │   ├── HistoricalPorcelainCard/  # 历史参考案例卡片
│   │   ├── UploadPanel/          # 图片上传
│   │   ├── AIExplainPanel/       # AI 讲解面板
│   │   └── Navbar/
│   ├── pages/                    # 5 个页面
│   │   ├── Home/                 # 首页
│   │   ├── Reconstruction/       # 三维复原
│   │   ├── Timeline/             # 历史演化
│   │   ├── Comparison/           # 形态对比
│   │   └── AIExplain/            # AI 讲解
│   ├── api/                      # 接口层（Mock ↔ 真实后端）
│   │   ├── client.ts             # 统一 fetch 封装
│   │   ├── reconstruction.ts / timeline.ts / comparison.ts / ai.ts
│   ├── services/
│   │   └── PorcelainReconstructionService.ts  # 重建服务
│   ├── stores/
│   │   └── PorcelainModelManager.tsx          # 共享状态（上传对象）
│   ├── mock/                     # Mock 数据
│   │   ├── data.ts               # 朝代 + 瓷器 + 对比 + AI
│   │   └── personalizedEvolutionData.ts       # 上传后的识别/匹配
│   ├── types/porcelain.ts        # ★ 全部共享类型
│   ├── App.tsx                   # 路由
│   └── main.tsx                  # 入口
│
├── backend/                      # Python 后端（三维重建）
│   ├── app/
│   │   ├── main.py               # FastAPI 路由
│   │   ├── triposr_engine.py     # TripoSR 推理
│   │   └── uncertainty.py        # 定向/归一化/热力图/补色
│   ├── TripoSR/                  # 第三方模型代码（克隆，含 isosurface 补丁）
│   ├── requirements.txt
│   └── README.md                 # 后端详细安装说明
│
├── docs/
│   ├── API.md                    # 前端架构 + 重建后端说明
│   └── backend-contracts.md      # ★ 三功能后端契约 + 数据库 + 分工
├── index.html
├── package.json
└── vite.config.ts
```

---

## 文档索引

- **如何协作、三个功能怎么做**：`docs/backend-contracts.md`
- **前端架构与重建后端**：`docs/API.md`
- **后端安装运行**：`backend/README.md`
- **源码阅读顺序**：见 `docs/API.md` 末尾（或直接看 `src/types/porcelain.ts` → `App.tsx` → 各 `pages/`）

---

## 团队分工（四人）

| 成员 | 负责 |
| --- | --- |
| 前端 + 三维重建 | ✅ 已完成 |
| 历史演化（时空数据 + 知识库） | `docs/backend-contracts.md` §2 |
| 形态对比（3D 形态测量） | `docs/backend-contracts.md` §3 |
| AI 讲解（RAG + LLM） | `docs/backend-contracts.md` §4 |

各功能的**前端已就绪**，后端成员按契约实现接口、把 `src/api/*.ts` 里的 Mock 换成真实调用即可，页面无需改动。
