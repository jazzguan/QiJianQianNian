# zjz 分支：已完成与未完成

更新：2026-10-14。分支：`zjz`。

## 功能状态

| 模块 | 已完成 | 未完成或数据缺口 |
| --- | --- | --- |
| 前端 + 三维重建 | React 三维界面；Gemini 图片识别；U2NetP 前景分割；TripoSR CPU 重建；实际进度、取消、简化网格、保存、恢复、GLB 下载；原照片纹饰贴图和前后镜像 | 多张照片重建、真实背面纹饰恢复；Hunyuan、Meshy、Tripo、TRELLIS 等新重建服务接入 |
| 历史演化 | 唐、宋、元、明、清时间轴；20 件馆藏；器型筛选；根据上传器型和特征检索同类；多个案例；相邻时期对比入口 | 各器型在每个朝代都有案例的数据覆盖；拖动时间轴时自动生成 AI 演化解释 |
| 形态对比 | 馆藏之间、本人重建模型与馆藏之间对比；六项参数自动计算；同步旋转缩放；部位对齐；工艺与年代资料对照；带来源的 AI 差异分析 | 独立分支的任意 GLB 导入、竖直轴选择、截面轮廓叠加、CSV 导出尚未合并；厘米尺度校准、内口径、胎壁厚度测量；自动部位语义分割 |
| AI 讲解 | 整体与部位讲解、自由问答；当前器物上下文；TF-IDF 检索馆藏文本；Atria 生成回答；引用馆藏来源 | Embedding 检索及 FAISS / Chroma / pgvector 向量库；超出当前 20 件馆藏资料的历史与工艺文献库 |
| 文物库与模型数据 | 20 件克利夫兰艺术博物馆 CC0 馆藏记录和照片，各朝代 4 件；搜索、筛选、尺寸、馆藏编号、来源；全部生成照片轮廓旋转成体 GLB | 官方扫描网格导入；当前 20 件馆藏 GLB 都由照片轮廓建模，背面纹饰采用正面镜像 |
| 账号与学习 | 注册登录、会话、个人数据隔离、SQLite 持久化；收藏、探索记录、时长与进度；63 道任务；服务端判分、AI 解释题评阅；首页推荐 | — |

六项形态参数为高度、最大腹径、口径、足径、高腹径比、最大腹径的相对高度。展示高度统一为 30，测量口径和足径采用外轮廓；馆藏厘米尺寸单独保存在资料字段中。

## 与形态对比独立分支的关系

`zjz` 集成文物库、重建、演化、问答、账号和学习功能。`codex/morphology-comparison` 从仓库 master 单独实现形态对比，两者尚未合并。

独立分支新增的 GLB 导入、竖直轴选择、轮廓叠加和 CSV 导出不在当前 `zjz` 页面中；独立分支也未包含 `zjz` 的 20 件真实馆藏、云端讲解、账号和学习中心。详见[独立分支状态](https://github.com/jazzguan/QiJianQianNian/blob/codex/morphology-comparison/docs/branch-status.md)。

## 已有验证记录

- TypeScript 与 Vite 构建通过。
- `test_photo_surface`、`test_platform`、`test_morphology` 共 20 项后端测试通过。
- 真实 Gemini 图片识别、Atria 问答、对比解释和解释题评阅通过。
- CPU 重建生成 13,140 个顶点、26,276 个面；模型下载、保存、恢复和形态测量通过。
- 正面纹饰、前后镜像、UV 接缝及 GLB 贴图检查通过。

## 源码与运行说明

- [完整实现记录](implementation.md)、[运行与安装](../README.md)、[实际 API](API.md)。
- [重建路由](../backend/app/main.py)、[纹饰投影](../backend/app/photo_surface.py)。
- [馆藏、演化、账号与学习](../backend/app/platform_routes.py)、[存储](../backend/app/storage.py)。
- [形态测量](../backend/app/morphology.py)、[形态接口](../backend/app/morphology_routes.py)、[对比页面](../src/pages/Comparison/index.tsx)。
- [知识检索与生成](../backend/app/knowledge.py)、[讲解页面](../src/pages/AIExplain/index.tsx)。
