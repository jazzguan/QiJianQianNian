# 器见千年

瓷器智能学习与演化分析平台：文物库、单图三维重建、历史时间轴、形态对比、带来源的知识问答和互动学习。

分支：`zjz`。各模块的已完成、未完成、数据缺口及与独立形态分支的区别见[分支完成情况](docs/branch-status.md)。

## 本机运行

在项目目录运行 PowerShell：

```powershell
npm install
npm run build
./start.ps1
```

打开 http://127.0.0.1:8000 。当前电脑已经安装后端依赖并下载重建权重。服务同时提供前端页面与 API；开发时可另行运行 `npm run dev`，Vite 将 API、图片和模型请求转发至 8000 端口。

## 新环境安装

需要 Python 3.12、Node.js 20 或更高版本。

```powershell
python -m venv backend/.venv
& backend/.venv/Scripts/python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
& backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
& backend/.venv/Scripts/python.exe backend/setup_triposr.py
& backend/.venv/Scripts/python.exe backend/setup_semantic.py
Copy-Item backend/.env.example backend/.env
```

在 `backend/.env` 填写模型配置。密钥只由后端读取，文件已被 Git 忽略。

| 配置 | 用途 |
| --- | --- |
| ATRIA_BASE_URL / ATRIA_MODEL / ATRIA_API_KEY | 知识问答、对比分析与解释题评阅 |
| GOOGLE_GEMINI_BASE_URL / GEMINI_MODEL / GEMINI_API_KEY | 图片识别与馆藏资料翻译 |
| TRIPOSR_RESOLUTION | 网格提取分辨率，默认 128 |
| QJQN_DB_PATH | 可选 SQLite 路径，默认 backend/data/app.sqlite3 |

首次重建下载官方 TripoSR、DINO 编码器与 U2NetP 权重，缓存保存在 `backend/cache`。TripoSR 源码由安装脚本获取，Windows CPU 等值面提取使用 scikit-image。

## 已接入功能

- 文物库：38件真实馆藏，含2件Smithsonian官方扫描；罐、碗、盘、杯覆盖唐宋元明清，支持搜索、筛选、尺寸、来源与收藏。
- 三维重建：Gemini 器型识别、TripoSR 生成网格、实际阶段进度、取消任务、简化浏览网格、完整 GLB 下载、模型保存与恢复。
- 多视角重建：上传正面、右侧、背面、左侧四张水平照片，按轮廓交集生成网格，各方向投影对应照片纹饰。
- 历史演化：可拖动时间轴、同器型匹配、时期覆盖表，切换后自动生成带引用的解释并缓存。
- 形态对比：双侧GLB导入、轴选择、六项参数、内口径和器口壁厚、厘米标定、同步视角、部位对齐、轮廓叠加、CSV导出与AI分析；导入文件按账号隔离。
- AI讲解：整体与部位问答、自由输入、BGE中文语义向量、SQLite持久化、FAISS检索和博物馆资料引用；文本主服务配额耗尽或不可用时接续已有Gemini接口。
- 学习中心：注册登录、探索记录、学习时长、进度、收藏、判断、工艺、观察、排序和自由解释题；服务端判分与 AI 评阅。
- 首页：根据已探索器型推荐未探索馆藏与未完成任务。

36件馆藏照片和资料来自[克利夫兰艺术博物馆Open Access](https://www.clevelandart.org/open-access)，2件扫描来自[Smithsonian 3D](https://3d-api.si.edu/api-docs/)，逐件保留许可和来源。照片轮廓模型仍使用前后镜像纹饰；扫描模型保留原纹理；四视角上传使用各自照片。馆藏厘米尺寸与高度30的展示坐标分别保存，内壁测量在网格具备相应几何时提供。

## 验证

```powershell
Set-Location backend
& .venv/Scripts/python.exe -m unittest test_photo_surface test_platform test_morphology test_extensions -v
# 真实 API 与重建全流程验证（会调用已配置模型服务）
& .venv/Scripts/python.exe live_smoke.py
```

`live_smoke.py` 使用独立的 `backend/cache/smoke.sqlite3` 数据库，验证问答、识别、重建、文件访问、保存和对比。

数据重新导入：

```powershell
& backend/.venv/Scripts/python.exe backend/import_collection.py
```

项目实现说明见 [docs/implementation.md](docs/implementation.md)，API 入口与存储说明见 [backend/README.md](backend/README.md)。
