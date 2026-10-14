# zjz 分支接口与公共模块

更新：2026-10-14。已完成与未完成项见[分支状态](branch-status.md)。

## 请求方式

后端入口为 `app.main:app`，启动方式见[项目 README](../README.md)。`./start.ps1` 使用 8000 端口同时提供页面和 API；开发时 Vite 将 `/api`、`/files`、`/media`、`/health` 转发到该服务。

[统一请求层](../src/api/client.ts)默认使用相对路径 `/api` 并携带会话 cookie；`USE_MOCK=false`。目录、时间轴、对比、识别和问答已接通后端。形态对比可通过 `VITE_COMPARISON_BASE` 指定服务地址。

## 已实现接口

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| GET | `/health`、`/api/providers/status` | 服务、模型加载和云端配置状态 |
| POST | `/api/auth/register`、`/api/auth/login`、`/api/auth/logout` | 注册、登录、退出 |
| GET | `/api/auth/me` | 当前账号 |
| GET | `/api/artifacts` | 馆藏列表，支持 q / dynasty / category 筛选 |
| GET | `/api/porcelain/{id}` | 馆藏详情 |
| GET | `/api/timeline`、`/api/timeline/{dynasty}` | 朝代列表、该朝代代表器物 |
| POST | `/api/recognize` | multipart file 图片识别 |
| POST | `/api/evolution/match` | 按 category / features 匹配同类馆藏 |
| POST | `/api/reconstruct` | multipart file 创建重建任务 |
| GET、DELETE | `/api/task/{id}` | 查询任务进度、取消 |
| GET | `/api/model/{id}`、`/api/models` | 模型信息、本人任务列表 |
| POST、DELETE | `/api/models/{id}/save` | 保存、取消保存 |
| GET | `/files/{id}/{filename}` | 本人的图片、完整网格、浏览网格、热力图 |
| POST | `/api/measure`、`/api/compare` | 几何测量与形态对比 |
| POST | `/api/compare/explain` | 根据测量和馆藏证据生成 AI 对比解释 |
| GET | `/api/ask/parts/{id}`、`/api/ask/suggestions` | 部位列表、推荐问题 |
| POST | `/api/ask`、`/api/ask/part` | 自由问答、部位讲解 |
| GET | `/api/learning`、`/api/learning/tasks` | 本人学习汇总、公开任务 |
| POST | `/api/learning/events`、`/api/learning/attempts` | 记录行为、提交答案 |
| POST、DELETE | `/api/favorites/{id}` | 收藏、取消收藏 |
| GET | `/api/recommendations` | 馆藏与任务推荐 |

创建重建任务、访问本人模型、保存模型、收藏及学习记录接口要求登录。历史馆藏与其轮廓测量公开；对重建模型调用测量和对比时校验所属账号。上传图片上限为 12MB。请求字段和返回模型见服务的 `/docs`。

## 公共模块

| 文件 | 当前作用 |
| --- | --- |
| [PorcelainReconstructionService](../src/services/PorcelainReconstructionService.ts) | 上传图片、轮询实际任务、获取模型、转换共享器物状态 |
| [PorcelainModelManager](../src/stores/PorcelainModelManager.tsx) | 跨页面共享当前模型 URL、识别结果、器物信息与报告 |
| [Platform](../src/stores/Platform.tsx) | 账号与馆藏状态、学习行为记录 |
| [PorcelainViewer](../src/components/PorcelainViewer/index.tsx) | GLB / 轮廓展示、旋转缩放平移、部位高亮、聚焦 |
| [CompareViewer](../src/components/CompareViewer/index.tsx) | 两侧模型、视角同步和部位对齐 |
| [共享类型](../src/types/porcelain.ts) | 器物、识别、测量、问答与重建数据类型 |

业务页面通过 `src/api/*.ts` 与重建服务读取数据；共享模型使用 `usePorcelainModel()`。馆藏从后端读取，新增馆藏数据入口为 `backend/data/artifacts.json`。

## 数据与生成

SQLite 保存馆藏、账号、会话、收藏、学习事件、答题记录及重建任务；GLB 与上传图片保存于 `backend/outputs`。重建使用 TripoSR CPU 推理；知识问答使用 TF-IDF 检索馆藏文本后调用 Atria；图片识别调用配置的 Gemini 服务。

形态单位为归一化单位（高度=30），实际馆藏尺寸独立保存。馆藏模型来自照片轮廓建模，前后纹饰使用正面照片和镜像。具体算法见[形态对比文档](morphology-comparison.md)，完整存储说明见[后端 README](../backend/README.md)。
