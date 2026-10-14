# codex/morphology-comparison 分支接口与公共模块

更新：2026-10-14。功能完成情况见[分支状态](branch-status.md)。

## 已实现服务

| 服务 | 入口与端口 | 已实现 |
| --- | --- | --- |
| 独立形态对比 | `app.morphology_app:app`，8001 | 目录、自动测量、GLB 导入与文件读取、形态对比、前端 /comparison 页面 |
| 原有三维重建 | `app.main:app`，8000 | TripoSR 单图重建、任务查询、GLB、热力图和质量报告；同时注册形态路由 |

`./start-comparison.ps1` 安装独立依赖、构建页面并启动 8001 服务。使用该脚本无需 TripoSR 或云端模型。原有重建服务的安装步骤见[后端 README](../backend/README.md)。

## 形态对比接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/comparison/artifacts` | 内置 5 件示例及本机导入目录 |
| POST | `/api/measure` | artifactId 或 modelUrl 二选一，返回六项参数和截面轮廓 |
| POST | `/api/measure/upload` | multipart file / upAxis，导入 GLB、持久保存并返回器物与测量 |
| GET | `/api/comparison/models/{id}.glb` | 本机导入的归一化 GLB |
| POST | `/api/compare` | 左右器物或模型，返回参数、规则洞察、双方器物和测量结果 |

请求层 [src/api/comparison.ts](../src/api/comparison.ts)始终访问真实接口，`VITE_COMPARISON_BASE` 可指定服务地址。Vite 开发代理将形态接口转发到 8001。具体字段、测量方法及导入限制见[形态对比文档](morphology-comparison.md)。

## 原有重建接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 模型加载状态 |
| POST | `/api/reconstruct` | multipart file 创建重建任务 |
| GET | `/api/task/{id}` | 任务状态 |
| GET | `/api/model/{id}` | 模型、热力图、报告、轮廓 |
| GET | `/files/{id}/mesh.glb`、`/files/{id}/heatmap.glb` | 输出模型 |

[重建服务](../src/services/PorcelainReconstructionService.ts)默认访问 `VITE_RECONSTRUCT_BASE`（默认 localhost:8000）；设置 `VITE_USE_MOCK=true` 时使用模拟重建。真实重建分支返回实际 GLB，但器物元数据仍取固定的元青花梅瓶示例。

## 公共模块与数据

- [PorcelainModelManager](../src/stores/PorcelainModelManager.tsx)保存跨页面共享的当前器物信息与模型 URL。
- [PorcelainViewer](../src/components/PorcelainViewer/index.tsx)展示 GLB 或轮廓，支持模型归一化、区域聚焦和高亮；对比页面的 GLB 加载失败显示错误。
- [CompareViewer](../src/components/CompareViewer/index.tsx)控制同步视角、独立交互和部位对齐。
- [共享类型](../src/types/porcelain.ts)定义器物、参数、部位、问答及重建数据。
- [morphology_catalog.json](../backend/app/morphology_catalog.json)保存 5 件示例轮廓；导入 GLB 和目录 JSON 保存在 `backend/comparison-models`，刷新后可重新选择。

## 未实现的接口与数据

历史演化和 AI 讲解的 `src/api/timeline.ts`、`src/api/ai.ts` 默认使用 Mock；本分支没有接入真实馆藏、视觉识别、历史匹配、云端问答、RAG 或账号学习数据库。对应后端契约中的未完成设计见[后端契约](backend-contracts.md)。

形态差异说明使用参数规则；材质、用途和历史对照使用提供的元数据，缺失字段显示“未提供资料”。当前测量为高度 30 的归一化外形测量，尚未测量内孔、胎壁或厘米尺度。
