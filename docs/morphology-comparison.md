# 形态对比

源码基线：GitHub master 提交 `c104cdc01b929f733ec046b5626d49736e603dc4`。形态对比通过独立服务运行，也已注册到原有后端。

## 功能

- 左右选择目录器物、当前重建模型或直接导入 GLB。
- 导入模型与目录信息保存在本机，刷新后可再次选择。
- 网格按选定竖直轴转为 Y 轴，底部归零，高度统一为30；保留模型纹理。
- 同步旋转、缩放；可切换独立交互并重置视角。
- 器口、器颈、肩部、腹部、器足定位、高亮和双侧聚焦。
- 六项形态测量、截面轮廓叠加、规则生成的差异说明和 CSV 导出。
- 器型、纹饰、工艺、材质、用途与历史背景对照；未提供的目录字段显示“未提供资料”。
- 加载、导入、计算失败状态与重试；切换选择后清除旧结果。

## 运行

需要 Python 3.12 和 Node.js 20 或更高版本。在项目根目录运行：

```powershell
./start-comparison.ps1
```

脚本首次安装独立依赖，构建前端，并启动 `http://127.0.0.1:8001/comparison`。本功能无需 TripoSR 权重或云端模型密钥。

开发模式：启动 `app.morphology_app:app` 的8001端口后运行 `npm run dev`，Vite转发形态对比接口。`VITE_COMPARISON_BASE` 可指定独立服务地址。其他模块仍采用仓库现有接口。

## 测量

测量值标注“自动提取”，单位为“归一化单位（高度=30）”。口径、足径表示外径。

| 参数 | 方法 |
| --- | --- |
| 高度 | Y轴范围，统一缩放至30 |
| 最大腹径 | 101个水平截面外径的最大值 |
| 口径 | 顶部邻近3%高度截面外径的中位数 |
| 足径 | 底部邻近3%高度截面外径的中位数 |
| 高腹径比 | 原网格高度除以最大截面外径 |
| 腹径位置 | 最大截面距底部的相对高度；小于40%偏下，大于60%偏上 |

截面由三角网格与平面求交得到；外径通过二维凸包和旋转卡尺计算。GLB场景节点变换应用后再测量，支持非水密网格。GLB导入上限20MB、30万面，支持Y/Z/X及反向竖直轴。模型必须自包含。

内置五件器物来自仓库原有示例轮廓，保存于 `backend/app/morphology_catalog.json`；参数均从轮廓重新计算。目录可按共享 `Porcelain` 类型补充真实轮廓、形制和工艺资料。目录字段 `material`、`use` 分别用于材质与用途对照。部位优先使用目录的标注区间，缺少标注时按高度区间定位。

## 接口

| 方法 | 路径 | 输入或输出 |
| --- | --- | --- |
| GET | `/api/comparison/artifacts` | 归一化目录器物 |
| POST | `/api/measure` | `{artifactId}`或`{modelUrl}`，返回六项测量及截面轮廓 |
| POST | `/api/measure/upload` | multipart的`file`与`upAxis`，返回测量、器物和归一化GLB地址 |
| GET | `/api/comparison/models/{id}.glb` | 导入后的归一化模型 |
| POST | `/api/compare` | `leftId/rightId`，可带`leftModelUrl/rightModelUrl`与标签 |

对比响应保留原契约的 `rows/insight/leftLabel/rightLabel`，并附 `left/right/leftMeasurement/rightMeasurement`。本模块按本服务文件路径读取模型；重建模型地址支持 `/files/{taskId}/mesh.glb`。

## 验证

```powershell
cd backend
./.venv-morphology/Scripts/python.exe -m unittest test_morphology -v
```

覆盖解析形状的测量误差、缩放和平移不变性、场景节点变换、竖直轴转换、GLB导入下载再测量、目录对比及无效输入。
