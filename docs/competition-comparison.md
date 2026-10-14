# 器见千年与历届软件设计创新赛获奖作品对比

检索日期：2026 年 10 月 13 日。赛事：全国大学生软件创新大赛·软件设计创新赛。

本文中的项目状态记录于 2026-10-13 后续功能开发前，源码链接指向当时提交；2026-10-14 的已完成与未完成项见[zjz 分支状态](branch-status.md)。

**对比判断：器见千年已经有三维重建接入和形态测量实现，项目的差异集中在瓷器跨时期观察与定量比较；当前完整度受到固定识别结果、模拟历史匹配和未实现的知识问答影响。**

## 公开获奖仓库

| 作品 | 届次及奖项出处 | 公开内容 | 与器见千年的对应关系 |
| --- | --- | --- | --- |
| [BrainDance／流光·记](https://github.com/tianxingleo/BrainDance) | 2026 年第 19 届全国一等奖；[大连理工大学报道](https://m.thepaper.cn/newsDetail_forward_33307806) | 手机采集、三维重建、空间语义检索、时间回看；公开移动端、计算服务、数据库及测试文档 | 三维重建、时间维度和知识检索与本项目最接近；对象是生活空间，本项目对象是瓷器 |
| [乐府](https://github.com/MitochondriaCN/Yuefu) | 2026 年第 19 届全国二等奖；仓库 README | 拍照识谱、结构化乐谱、钢琴键盘瀑布流；另有[模型仓库](https://github.com/Flutter-Misdreavus/Yuefu-OMR-model)和[答辩资料](https://github.com/Flutter-Misdreavus/yuefu-presentation) | 同为“图片输入→结构化对象→交互学习”；模型仓库说明使用开源 Legato |
| [AI 阴阳眼](https://github.com/Eliot-Shen/AI-YinYang-Eyes) | 2025 年第 18 届全国三等奖、华东赛区一等奖；仓库 README | AI 伪造图像检测、视频通话检测场景、Android 源码、服务端及 APK | 同样使用开源视觉模型；公开交付物包括可以安装的客户端 |
| [heartmelody](https://github.com/yoikura/heartmelody) | 2023 年第 16 届二等奖；仓库 README 标注 | AI 音乐与 VR 场景；仓库有前端和 Java 后端，包含场景、歌单、用户及记录接口 | 与本项目的生成内容、沉浸式展示和用户记录有关 |
| [JoyStickPC](https://github.com/SWC-JoyStick/JoyStickPC) | 2022 年第 15 届全国三等奖；仓库说明 | Qt/C++ 桌面端源码，包含屏幕采集、编解码、渲染、控制及 Android 连接模块 | 展示了跨设备交互的软件实现，技术路线与文物学习不同 |
| [三彩知因／AntiqueID](https://github.com/agno3xzy/AntiqueID) | 2019 年第 12 届全国二等奖；仓库 README，[当届获奖名单报道](https://www.52jingsai.com/article-8486-1.html) | 唐三彩图片上传、类别和颜色分析、鉴赏报告；公开 Django 与 JSP 工程 | 直接相关的文博题材先例，本项目增加了三维形态与跨时期比较 |

2024 年第 17 届的[山东大学获奖报道](https://www.view.sdu.edu.cn/info/1003/191860.htm)列有“画中人生 Life in Portrait”“声之形”等一等奖作品；检索未找到能对应这些作品与奖项的公开源码仓库。

## 关键实现对照

### 三维重建与后续使用

BrainDance 的三维结果进入空间检索和时间回看流程。公开的[搜索入口](https://github.com/tianxingleo/BrainDance/blob/main/supabase/functions/search-models/index.ts)接受自然语言查询并调用共享检索逻辑；其[评测报告](https://github.com/tianxingleo/BrainDance/blob/main/docs/04-%E6%9C%AC%E5%9C%B0%E9%97%AE%E7%AD%94%E4%B8%8E%E5%BE%AE%E8%B0%83/Qwen3-1.7B-LoRA-%E4%B8%A5%E6%A0%BC%E6%97%A0%E6%B3%84%E6%BC%8F%E5%AF%B9%E6%A0%87%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A-2026-03-22.md)同时记录测试集、对照模型和证据利用等指标。

器见千年的 [TripoSR 引擎](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/backend/app/triposr_engine.py)调用预训练模型进行 CPU 推理，后端导出 GLB、热力图和报告。[形态测量](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/backend/app/morphology.py)从网格的 101 个水平截面提取外轮廓参数，计算口径、足径、高腹径比和腹部位置，并生成差异说明。这是项目中已有具体算法与测试支撑的部分。

### 文博题材与识别

三彩知因已经采用“上传器物照片→提取特征→生成鉴赏报告”的流程。[分类源码](https://github.com/agno3xzy/AntiqueID/blob/master/app-django-demo/mysite/classification/views.py)包含图片预处理、颜色分析、分类预测与报告保存。

器见千年的上传重建结果目前仍附带固定的元青花梅瓶元数据：[重建服务](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/src/services/PorcelainReconstructionService.ts)的真实接口分支也返回 `getPorcelainById('yuan-qinghua')`。[识别与匹配模块](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/src/mock/personalizedEvolutionData.ts)固定返回“梅瓶”，历史匹配函数没有使用传入的器型类别。因此，生成网格与后续器物身份、历史关联尚未形成真实的数据衔接。

### 学习交互与交付材料

乐府围绕图片识谱，将识别结果转为可操作的乐谱与播放界面，公开模型工程及答辩、演示材料。器见千年的设计报告包含“探索→观察→比较→提问→测试→记录”，目前 [应用路由](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/src/App.tsx)包含首页、重建、历史演化、形态对比、AI 讲解五个页面，尚无学习测试或个人记录页面。

AI 阴阳眼公开了 Android 源码和 APK，[服务端](https://github.com/Eliot-Shen/AI-YinYang-Eyes/blob/main/Server/app.py)有文件上传、模型预测和检测结果返回。器见千年的交付形态目前是 React Web 前端与 Python 后端，仓库内已有设计报告和答辩 PPT。

## 2026-10-13 开发前项目状态

| 功能 | 代码中的实际状态 | 源码依据 |
| --- | --- | --- |
| 图片三维重建 | 已接入 TripoSR 推理、任务轮询、GLB 导出；重建服务默认走真实接口 | [重建服务](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/src/services/PorcelainReconstructionService.ts)、[后端路由](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/backend/app/main.py) |
| 重建热力图 | 按法线与固定视线方向的夹角生成启发式评分；代码未做实测误差或概率校准 | [热力图计算](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/backend/app/uncertainty.py) |
| 形态对比 | 上传模型从 GLB 测量；五件历史参考器物从预设轮廓计算；高度统一归一化到 30 | [测量算法](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/backend/app/morphology.py)、[方法文档](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/docs/morphology-comparison.md) |
| 历史演化 | 唐、宋、元、明、清五组样例；接口默认使用 Mock，后端未提供时间轴路由 | [时间轴接口](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/src/api/timeline.ts)、[请求开关](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/src/api/client.ts) |
| 上传器物识别 | 固定示例元数据与“梅瓶”类别 | [识别模块](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/src/mock/personalizedEvolutionData.ts) |
| 个性化历史匹配 | 固定参考列表，未根据上传器物类别检索 | [匹配模块](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/src/mock/personalizedEvolutionData.ts) |
| AI 讲解与 RAG | 当前使用预设问答；后端未提供 `/ask` 路由，知识库与向量检索写在后端契约中 | [AI 接口](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/src/api/ai.ts)、[后端契约](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/docs/backend-contracts.md) |
| 模型与用户记录 | 当前器物保存在 React Context；重建任务保存在进程内字典；设计中的学习记录未落地 | [模型状态](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/src/stores/PorcelainModelManager.tsx)、[后端任务](https://github.com/jazzguan/QiJianQianNian/blob/57981905ad9b6088feaac7d5f3404a5159fa2ad1/backend/app/main.py) |

## 对比结论

**题材方面**，AI 文博应用已有三彩知因这样的获奖先例；三维重建结合时间与知识交互也已有 BrainDance。器见千年的区别在于瓷器形态测量和跨朝代比较的组合。

**技术方面**，公开获奖仓库中也有使用开源模型的作品，如乐府使用 Legato、AI 阴阳眼基于 UniversalFakeDetect。器见千年已有的具体工作包括模型后处理、三维查看器、截面测量和参数差异计算。当前历史参考来自五件预设轮廓，尚未形成同类器物的真实演化数据集。

**完整度方面**，当前能够从代码确认的主要链路是“上传→重建→三维查看→形态测量与对比”。“识别→匹配历史案例→知识讲解→学习测试与记录”尚未完成。

**验证方面**，2026 年 10 月 13 日执行 `npm run build` 通过；现有 `test_morphology` 的 8 项测试全部通过，覆盖已知几何尺寸、尺度和平移不变性、历史轮廓、GLB 场景变换、上传对比及异常输入。此次未运行 TripoSR 端到端推理，构建与几何测试不包含真实文物重建精度和学习效果评测。
