# zjz 分支：已完成与未完成

更新：2026-10-15。分支：`zjz`。

## 当前功能

| 模块 | 已完成 | 仍有的数据或技术缺口 |
| --- | --- | --- |
| 形态对比 | 双侧 GLB 导入、六方向竖直轴选择、账号隔离和刷新恢复；同步旋转缩放、五部位对齐；截面轮廓叠加；参数、馆藏特征和来源对照；CSV 导出；真实 AI 差异解释 | 部位定位使用目录标注或高度区间，自动语义分割尚未实现 |
| 尺度与内壁测量 | 输入实物高度标定厘米尺寸；已有明确高度的馆藏自动使用记录；包含内壁的网格可计算内口径和器口壁厚；无内壁时显示“无内壁数据” | 照片轮廓和实心网格不能提供缺失的内壁；当前壁厚取器口邻近截面，未测全器身壁厚分布 |
| 三维重建与纹饰 | 原有 Gemini 识别和 TripoSR 单图重建；新增正面、右侧、背面、左侧四视角轮廓重建，各方向投影对应照片纹饰；保存、恢复和 GLB 下载 | 四视角流程要求水平四方向照片；任意角度照片的自动相机位姿估计尚未接入 |
| 真实扫描与馆藏 | 38 件真实馆藏：36 件照片轮廓模型、2 件 Smithsonian 官方扫描；扫描保留各方向纹饰，按实际 Z 轴转为竖直 Y 轴 | 36 件照片轮廓模型仍采用正面与背面镜像；全部馆藏替换为真实扫描尚未完成 |
| 历史演化 | 罐、碗、盘、杯均覆盖唐宋元明清；器型与特征匹配；时期覆盖表；选择时期后自动生成带来源的解释；切换取消旧请求；服务端缓存解释 | 梅瓶、长颈瓶等细分器型仍有时期样本缺口 |
| AI 与知识检索 | BGE-small-zh-v1.5 中文语义向量、SQLite 持久化和 FAISS 检索；器物匹配结合 TF-IDF；38 件馆藏文本与4篇博物馆工艺资料摘要；Atria 文本生成，配额耗尽或服务不可用时接续已有 Gemini | 尚未导入更大规模的历史与考古文献全文 |
| 账号与学习 | 注册登录、会话、个人数据隔离、收藏、学习事件、时长、进度、任务判分与 AI 评阅；任务随馆藏数据生成 | — |

六项主要参数仍为高度、最大腹径、口径、足径、高腹径比及最大腹径位置。比例对比统一高度 30，厘米尺寸在单独表格展示。内口径和壁厚为附加测量，不改变六项基础接口字段。

## 数据来源

- [克利夫兰艺术博物馆 Open Access](https://www.clevelandart.org/open-access)：36 件 CC0 馆藏照片、尺寸与元数据。
- [Smithsonian 3D API](https://3d-api.si.edu/api-docs/)：2 件国家亚洲艺术博物馆的清代觚式瓶扫描，来源、原始模型与尺寸保存在各自记录。
- [V&A 青花瓷](https://www.vam.ac.uk/articles/chinese-blue-and-white-ceramics)、[德化白瓷](https://www.vam.ac.uk/articles/blanc-de-chine-white-porcelain-from-china)。
- [大都会博物馆珐琅专题](https://www.metmuseum.org/exhibitions/embracing-color)、[中国陶瓷演化与交流](https://www.metmuseum.org/it/press-releases/chinese-ceramics-on-great-hall-balcony-2012-exhibitions)。

## 已有验证记录

开发过程中已执行27项后端测试并通过，覆盖原平台、GLB导入与账号隔离、轴转换、厘米标定、内壁测量、语义索引更新、四视角生成和背面照片纹饰。真实云端问答与跨时期解释已返回带引用的内容。官方扫描的方向已按原始模型坐标和馆方高径尺寸校正。

## 分支关系与运行

独立形态分支的 GLB 导入、轴向选择、轮廓叠加和 CSV 导出已移植到当前 `zjz`，并接入当前账号、真实馆藏和 AI 解释；独立分支本身未合并本次平台扩展。

- [运行与安装](../README.md)、[形态对比方法](morphology-comparison.md)、[实际 API](API.md)。
- [内壁与尺度测量](../backend/app/morphology.py)、[私人模型接口](../backend/app/morphology_routes.py)。
- [四视角重建](../backend/app/multiview.py)、[语义索引](../backend/app/semantic.py)、[工艺资料](../backend/data/knowledge.json)。
