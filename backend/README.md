# 后端运行与 API

后端采用 FastAPI、SQLite、Gemini、Atria 与 TripoSR。安装和启动步骤见项目根目录 README。

## 接口

| 方法 | 路径 | 内容 |
| --- | --- | --- |
| GET | /health | 服务、模型配置与加载状态 |
| POST | /api/auth/register、/api/auth/login | 注册或登录 |
| GET、POST | /api/auth/me、/api/auth/logout | 当前账号、退出 |
| GET | /api/artifacts、/api/porcelain/{id} | 搜索馆藏、详情 |
| GET | /api/timeline | 时间轴 |
| POST | /api/recognize | multipart file 图片识别 |
| POST | /api/evolution/match | 器型与特征匹配 |
| POST | /api/reconstruct | 登录后上传并创建任务 |
| GET、DELETE | /api/task/{id} | 实际进度、取消 |
| GET | /api/model/{id}、/api/models | 单个模型、本人历史任务 |
| POST、DELETE | /api/models/{id}/save | 保存或取消保存 |
| GET | /files/{id}/{filename} | 本人的图片、完整网格、浏览网格、热力图 |
| POST | /api/measure、/api/compare | 几何测量与对比 |
| POST | /api/compare/explain | 根据测量与馆藏资料解释差异 |
| POST | /api/ask、/api/ask/part | 自由问答、部位讲解 |
| GET | /api/learning、/api/learning/tasks | 本人学习汇总、公开题目 |
| POST | /api/learning/events、/api/learning/attempts | 记录行为、提交答案 |
| POST、DELETE | /api/favorites/{id} | 收藏或取消 |
| GET | /api/recommendations | 器物与任务推荐 |

完整字段定义可在服务启动后访问 /docs 。

## 数据

- backend/data/artifacts.json：20 件馆藏及原始元数据、许可、来源和分割轮廓。
- backend/data/images：压缩后的 CC0 馆藏照片。
- backend/data/app.sqlite3：账号、会话、收藏、学习事件、答题记录、任务与模型保存状态。
- backend/outputs：重建图片与模型；文件接口校验账号归属。
- backend/cache：模型权重与真实接口验证数据库。

密码使用带随机盐的 PBKDF2-SHA256 保存；会话令牌以哈希保存，浏览器使用 HttpOnly cookie。上传图片最多12MB；任务按账号保存，服务重启后进行中的任务标为中断，可重新上传。

## 模型与形态

TripoSR使用CPU，默认等值面分辨率128。完整网格用于几何测量，浏览版本简化至最多18,000面；两个版本均嵌入原照片的正面纹饰贴图。三维展示统一高度30；实际馆藏尺寸保留在measurementsText。

photo_surface.py将正面照片投影到模型，并关于前后分界平面镜像到背面，按器物高度和水平曲面位置计算UV，保持侧面衔接。GLB采用KHR_materials_unlit，避免照片中已有的明暗被二次照明改变。update_surfaces.py可在本机为已下载的馆藏及已完成的上传模型重新生成纹理，无需再次调用云端服务。

热力图以表面法线和假设相机方向计算可观测性指标。TripoSR 源码与许可证从[官方仓库](https://github.com/VAST-AI-Research/TripoSR)下载；setup_triposr.py 在源码目录增加 scikit-image marching cubes 的 CPU 适配模块。
