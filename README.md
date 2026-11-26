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

打开 http://127.0.0.1:8000 。启动脚本优先使用 `qjqn-gpu` Conda 环境；首次启动时会在后台下载并预热模型权重。服务同时提供前端页面与 API；开发时可另行运行 `npm run dev`，Vite 将 API、图片和模型请求转发至 8000 端口。Gemini 图片识别是可选增强项：未配置密钥或视觉服务暂时不可用时，系统会跳过器型识别并继续执行本地三维重建。

后端启动后会在后台预热当前使用的三维模型，网页和普通 API 不会被阻塞。`/health` 和三维复原页面会显示“读取权重、加载到 CUDA、已就绪”等状态；保持后端进程运行可避免重复冷加载。若只需运行不使用重建的轻量服务，可在 `.env` 设置 `QJQN_PRELOAD_MODELS=false`。

## Android 真机运行

Android 端已经使用 Capacitor 接入，包名为 `cn.qijianqiannian.app`。本机工具位于 `D:\SoftWare`：Android Studio、JDK 21、Android SDK 36 与 Gradle 均由项目脚本自动识别，手机和电脑需连接同一局域网。

```powershell
# 1. 自动把电脑当前局域网 IPv4 写入本机 Android 配置
npm run android:configure

# 识别失败时可手动指定
npm run android:configure -- 192.168.1.11

# 2. 构建网页并同步到 Android 工程
npm run android:sync

# 3. 允许手机访问后端（网页本机运行仍使用普通的 ./start.ps1）
./start.ps1 -Lan

# 4. 打开 Android Studio，连接手机后点击 Run
npm run android:open

# 或直接生成调试 APK
npm run android:apk
```

真机首次调试若无法连接，先在手机浏览器访问 `http://电脑IPv4:8000/health`；无法打开通常是网络不同或 Windows 防火墙未允许 Python。局域网地址变化后重新执行 `android:configure` 和 `android:sync`。Android 端支持后置摄像头拍照、相册选择和分辨率/曝光/清晰度预检；账号采用 Bearer 会话，私人图片和 GLB 使用两小时有效的单文件签名链接，不会公开模型目录。

## 新环境安装

推荐 Python 3.10、Node.js 20 或更高版本。RTX 4060 8GB 等 NVIDIA 显卡使用 CUDA 环境：

```powershell
conda create -n qjqn-gpu python=3.10 pip -y
conda run -n qjqn-gpu python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
conda run -n qjqn-gpu python -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
./scripts/fetch_weights.ps1
```

上面最后一条会把三个引擎的源码和权重一次装齐（也可以分步：`python backend/setup_triposr.py` 只装 TripoSR 源码，权重第一次重建时自动下）。

### 模型权重与 Meshroom

仓库不放权重：TripoSR 约 1.6GB、Hunyuan3D-2mini 约 3.6GB、Meshroom 便携版约 2.6GB，合计十几 GB，GitHub 单文件上限 100MB，放不进仓库。三者都有公开下载源，`./scripts/fetch_weights.ps1` 会按顺序补齐，已存在的自动跳过：

| 组件 | 来源 | 落到哪 | 大小 |
| --- | --- | --- | --- |
| TripoSR 源码 | GitHub VAST-AI-Research/TripoSR | `backend/TripoSR/` | 约 20MB |
| TripoSR 权重 | Hugging Face `stabilityai/TripoSR` | `backend/cache/huggingface/` | 约 1.6GB |
| Hunyuan3D-2mini 形状权重 | Hugging Face `tencent/Hunyuan3D-2mini`，只取 `hunyuan3d-dit-v2-mini` 子目录 | `backend/cache/hf_cache/` | 约 3.6GB |
| Meshroom 2023.3.0 | GitHub alicevision/Meshroom release | `backend/cache/Meshroom-2023.3.0/` | 约 2.6GB |

默认直连 Hugging Face。国内网络走镜像就加 `-Mirror "https://hf-mirror.com"`；镜像和直连哪个通，按自己网络实测选。下载中断直接重跑，curl 会续传。只装一部分用 `-SkipHunyuan` / `-SkipMeshroom` / `-SkipTripoSR`。

同城或同校的话，最省事的是从已装好的机器直接拷 `backend/cache` 整个目录（约 12GB，U 盘十几分钟），比任何网盘都快。

装完启动后端，`/health` 里 `triposrInstalled`、`hunyuanInstalled`、`meshroomInstalled` 三个都为 true 就齐了；缺哪个，页面上对应功能会置灰，不会影响其余部分。

在 `backend/.env` 填写模型配置。密钥只由后端读取，文件已被 Git 忽略。

| 配置 | 用途 |
| --- | --- |
| ATRIA_BASE_URL / ATRIA_MODEL / ATRIA_API_KEY | 知识问答、对比分析与解释题评阅 |
| GOOGLE_GEMINI_BASE_URL / GEMINI_MODEL / GEMINI_API_KEY | 图片识别与馆藏资料翻译 |
| TRIPOSR_RESOLUTION | 网格提取分辨率，默认 128 |
| QJQN_DEVICE | `auto` 优先 CUDA，亦可强制设为 `cuda` 或 `cpu` |
| QJQN_RECONSTRUCTION_ENGINE | `auto` 默认按 TripoSR→InstantMesh 顺序选择；也可显式指定 triposr/sf3d/instantmesh/hunyuan 一种。页面上的快速/精细开关会按请求覆盖这一项 |
| SF3D_BAKE_RESOLUTION | SF3D 纹理烘焙分辨率，8GB 显存建议 1024 |
| QJQN_DB_PATH | 可选 SQLite 路径，默认 backend/data/app.sqlite3 |

当前本地可直接跑的是 TripoSR（快速）和 Hunyuan3D-2mini（精细，8GB 显存可跑）；InstantMesh 走云端 Space、需 HF token；SF3D 按团队当前安排暂停接入。各引擎权重均缓存于 `backend/cache`，推理优先使用 CUDA；Windows 等值面提取使用 scikit-image 以避免本地编译扩展。SF3D 若后续启用，其权重需先在 Hugging Face 接受 `stabilityai/stable-fast-3d` 的许可并登录。各方法的客观指标对比见 [benchmark/客观工程指标汇总.md](benchmark/客观工程指标汇总.md)。

## 已接入功能

- 文物库：20 件馆藏，唐、宋、元、明、清各 4 件；名称搜索、朝代与器型筛选、图片、尺寸、馆藏编号、来源与收藏。
- 三维重建：可选器型识别、**快速（TripoSR，约 10 秒）与精细（Hunyuan3D，约 1 分钟）两档可在页面直接切换**、无视觉密钥降级、实际阶段进度、取消任务、简化浏览网格、完整 GLB 下载、模型保存与恢复，以及彻底删除任务及其上传图片和模型。
- 环绕建档（页面 `/multiview`）：上传 2–40 张环绕照片，走 Meshroom 摄影测量得到真实几何与实拍贴图；适合能绕器物一周拍摄的教学标本，展柜内文物仍走单图复原。
- 多引擎同图对比（页面 `/engine-compare`）：同一张照片分别用不同引擎生成，统一朝向和尺度，并排展示可旋转模型与顶点、面数、几何水密、欧拉数、GLB 大小；导出前自动去除体积解码产生的微小退化碎片，保留主体。
- 历史演化：可拖动时间轴；上传器物按器型和可见特征检索同类馆藏；缺少同类记录时显示空状态。
- 形态对比：统一展示高度，计算口径、腹径、足径、比例和腹径位置；同步视角、部位对齐和带资料来源的 AI 差异分析。
- AI 讲解：整体与部位问答、自由输入、当前器物上下文、TF-IDF 检索和馆藏引用。
- 学习中心：注册登录、探索记录、学习时长、进度、收藏、判断、工艺、观察、排序和自由解释题；服务端判分与 AI 评阅。
- 首页：根据已探索器型推荐未探索馆藏与未完成任务。

馆藏数据与照片来自[克利夫兰艺术博物馆 Open Access](https://www.clevelandart.org/open-access)，逐件记录 CC0 许可和原始链接。历史器物三维形态采用前景分割后的照片轮廓建模，正面纹饰由原照片投影并嵌入GLB；上传器物采用本地三维引擎网格，同样保留正面照片纹饰。背面采用正面镜像纹理，前后对称。馆藏厘米尺寸与高度统一为30的展示坐标分别保存。

## 数据与隐私

- 上传的照片、生成的三维模型和浏览网格只保存在运行后端的本机（`backend/data` 与 `backend/outputs`），不随前端分发；私人文件通过两小时有效的单文件签名链接访问，不公开模型目录。
- 用户可以随时删除自己的上传内容：调用 `DELETE /api/models/{taskId}` 会永久删除该任务的原图、完整 GLB、浏览网格、热力图和数据库记录。进行中的任务需先取消再删除。
- 学习中心的答题记录属于学习成果，删除模型时会保留，不会一并清除。
- 没有配置云端密钥时，整条重建链路可完全离线运行，图片不会发送到第三方。

## 验证

```powershell
Set-Location backend
# 使用 qjqn-gpu 环境的 python（按本机实际路径替换）
& "D:\SoftWare\Anaconda\envs\qjqn-gpu\python.exe" -m unittest test_photo_surface test_platform test_morphology -v
# 真实 API 与重建全流程验证（会调用已配置模型服务）
& "D:\SoftWare\Anaconda\envs\qjqn-gpu\python.exe" live_smoke.py
# 页面引擎选择闭环：非法引擎应 400，指定引擎产物的 modelMethod 应回显该引擎
& "D:\SoftWare\Anaconda\envs\qjqn-gpu\python.exe" test_engine_select_api.py 8000 triposr
```

`live_smoke.py` 使用独立的 `backend/cache/smoke.sqlite3` 数据库，验证问答、识别、重建、文件访问、保存和对比。

数据重新导入：

```powershell
& "D:\SoftWare\Anaconda\envs\qjqn-gpu\python.exe" backend/import_collection.py
```

项目实现说明见 [docs/implementation.md](docs/implementation.md)，API 入口与存储说明见 [backend/README.md](backend/README.md)。
