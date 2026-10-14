# zjz 分支形态对比

更新：2026-10-14。整体功能状态见[分支状态](branch-status.md)。

## 已完成

左右可选择 20 件真实馆藏，左侧也可使用当前账号上传并重建的模型。后端计算六项形态参数；两个查看器支持同步旋转缩放和部位对齐。页面显示馆藏工艺、年代与来源，并可调用 Atria 生成带引用的差异分析。

## 运行

按照[项目 README](../README.md)安装依赖、配置云端模型后，在项目根目录运行：

```powershell
npm run build
./start.ps1
```

打开 `http://127.0.0.1:8000/comparison`。开发时运行 `npm run dev`，Vite 转发请求到 8000 端口。本分支通过平台后端运行，入口为 `app.main:app`。

## 测量方法与数据

- Y 轴为竖直轴，所有参数按器物高度统一缩放至 30。
- 重建 GLB：应用场景节点变换后合并网格，在 0.5%–99.5% 高度取 101 个水平截面；外径为截面凸包上两点的最大距离。
- 最大腹径取截面外径最大值；腹部位置为相应截面距底部的高度占比，多个接近最大值的截面取平均位置。
- 口径、足径分别取顶部、底部邻近 3% 高度范围的截面外径中位数。
- 馆藏器物从照片提取的 `[半径, 高度]` 轮廓测量：最大半径的两倍为腹径，首尾端半径的两倍为足径和口径。
- 高腹径比为原始高度除以最大腹径；腹部位置小于 40% 为偏下，大于 60% 为偏上，其余居中。
- 规则差异说明根据高腹径比、口径、足径和腹部位置的差值生成；AI 分析另从馆藏资料取得证据。

目录由 [storage.artifacts()](../backend/app/storage.py)读取，种子为 [backend/data/artifacts.json](../backend/data/artifacts.json)。目录包含唐、宋、元、明、清各 4 件馆藏。当前 20 件馆藏 GLB 都由照片轮廓建模，纹饰取自正面照片，背面采用镜像。

## 接口

### POST /api/measure

请求二选一：

```json
{"artifactId": "cma-94820"}
```

```json
{"modelUrl": "/files/11ae72b9-178f-473f-bba8-609258ecd712/mesh.glb"}
```

模型标识需替换为本人已成功完成的任务。返回 `height`、`maxBellyDiameter`、`mouthDiameter`、`footDiameter`、`heightBellyRatio`、`bellyPosition`、`bellyPositionLabel`、`shape`、`source`、`method`、`unit`。

`source` 为 `mesh` 或 `profile`；馆藏的 `method` 使用记录中的建模方法，重建网格为“自动提取”。`modelUrl` 解析为后端本地输出文件，测量前校验账号与任务归属。

### POST /api/compare

```json
{"leftId": "cma-94820", "rightId": "cma-111799"}
```

上传重建模式附带 `leftModelUrl`，此时测量实际 GLB；接口也接受 `rightModelUrl`。返回器物标识、`rows`、`insight`、双方标签与测量结果，以及馆藏的 `featureRows`、`sources`。

### POST /api/compare/explain

请求字段与 `/api/compare` 相同。根据测量和馆藏证据调用文本模型，返回 `answer`、`sources`。

未知器物或不存在的模型返回 404；无效输入或无法测量的几何返回 422；需要本人模型但未登录时返回 401；云端生成失败返回 502。

## 未完成

- 任意 GLB 导入、竖直轴选择、截面轮廓叠加、CSV 导出在独立形态分支中，尚未合并至本分支。
- 测量尚未按厘米尺度校准，未测内口径与胎壁厚度。
- 部位选择使用标注的高度区间，未实现自动部位语义分割。
- 官方扫描网格尚未导入，馆藏参考为照片轮廓模型。

独立功能与数据状态见[形态对比分支](https://github.com/jazzguan/QiJianQianNian/blob/codex/morphology-comparison/docs/branch-status.md)。

## 验证记录

形态算法和接口的 9 项测试通过，覆盖解析几何、缩放和平移、朝向、场景节点变换、重建模型对比、同器物对比和异常输入；全平台共 20 项后端测试及前端构建通过。

```powershell
Push-Location backend
& .venv/Scripts/python.exe -m unittest test_morphology -v
Pop-Location
npm run build
```
