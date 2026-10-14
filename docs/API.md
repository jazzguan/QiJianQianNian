# 器见千年 · 前端协同开发接口文档

本文档面向后续多人协作开发，说明公共模块、共享数据类型、Mock 数据组织方式，以及未来接入真实后端时需要替换的位置。

> 形态对比已接入真实测量接口，见[形态对比文档](morphology-comparison.md)；三维重建使用原有TripoSR服务，其他模块仍沿用原实现。

---

## 1. 目录结构与模块边界

```
src/
├── services/
│   └── PorcelainReconstructionService.ts    # 三维重建服务（接口 + Mock 实现）
├── stores/
│   └── PorcelainModelManager.tsx            # 共享状态（React Context）
├── components/
│   ├── PorcelainViewer/                     # 公共 3D 查看器
│   ├── CompareViewer/                       # 双模型对比
│   ├── Timeline/                            # 时间轴
│   ├── EvolutionModeSwitch/                 # 个性化模式切换条
│   ├── HistoricalPorcelainCard/             # 历史参考案例卡片
│   ├── UploadPanel/                         # 图片上传
│   ├── AIExplainPanel/                      # AI 讲解面板
│   └── Navbar/
├── pages/                                   # 四个业务页面
│   ├── Reconstruction/  Timeline/  Comparison/  AIExplain/
├── api/                                     # 低层 HTTP 封装（未来真实后端）
│   ├── client.ts  reconstruction.ts  timeline.ts  comparison.ts  ai.ts
├── mock/                                    # Mock 数据
│   ├── data.ts                              # 朝代 + 瓷器 + 部位讲解 + 对比
│   └── personalizedEvolutionData.ts         # 上传后的识别 / 匹配 / 对比
├── types/
│   └── porcelain.ts                         # 全部共享类型
└── App.tsx                                  # 挂载 PorcelainModelManagerProvider
```

**依赖规则**（务必遵守）：

1. 业务页面可调用公共组件、Service、共享状态。
2. `PorcelainViewer` 不依赖任何业务页面，不负责上传 / 匹配 / 讲解。
3. `PorcelainReconstructionService` 不负责布局与渲染。
4. 历史演化 / 形态对比 / AI 讲解可复用模型数据，但**不能相互直接依赖页面实现**。
5. 共享类型统一放在 `types/porcelain.ts`。
6. 页面**不得**自行创建另一套三维模型状态（统一走 `PorcelainModelManager`）。

---

## 2. 三个公共模块

### 2.1 PorcelainReconstructionService（三维重建服务）

文件：`src/services/PorcelainReconstructionService.ts`

| 方法 | 签名 | 说明 |
| --- | --- | --- |
| `reconstruct` | `(image: File \| string) => Promise<ReconstructTask>` | 提交图片，立即返回任务 id 与 `processing` 状态 |
| `getTaskStatus` | `(taskId: string) => Promise<TaskStatus>` | 查询任务状态 |
| `getModel` | `(taskId: string) => Promise<ModelInfo>` | 成功后获取模型信息 |

任务状态 `TaskStatus`：`idle | processing | success | error`。

当前为 **Mock 实现**：`reconstruct` 内部延迟约 2.4s 后把任务置为 `success`，`getModel` 返回示例瓷器（元青花梅瓶，`modelUrl: null`）。

> **未来替换真实后端时，只改这一个文件**：把三个方法改成调用 HTTP 接口即可，四个页面无需改动。

### 2.2 PorcelainViewer（公共 3D 查看器）

文件：`src/components/PorcelainViewer/index.tsx`

| Prop | 类型 | 说明 |
| --- | --- | --- |
| `modelUrl` | `string?` | 真实 GLB 地址，优先于 `shape` 加载；加载失败回退到程序化轮廓 |
| `shape` | `PorcelainShape?` | 器物侧面轮廓（程序化生成，见下） |
| `glaze` | `GlazeStyle?` | 釉色 / 纹饰配置 |
| `autoRotate` | `boolean?` | 自动旋转 |
| `interactive` | `boolean?` | 允许旋转 / 缩放 |
| `showControls` | `boolean?` | 显示「重置视角 / 自动旋转」按钮 |
| `parts` | `PorcelainPart[]?` | 部位标注数据 |
| `selectedPartId` | `string?` | 当前选中部位 id（查看器据此高亮） |
| `onPartSelect` | `(partId: string) => void?` | 点击部位回调 |
| `resetToken` | `number?` | 外部触发视角重置（值变化即重置） |
| `viewId` / `syncEnabled` / `syncRef` | 双模型同步交互用 | 见 `CompareViewer` |

已实现：模型加载状态、加载失败兜底、`modelUrl` 变化时清理旧资源、旋转 / 缩放 / 重置 / 自动旋转、部位高亮与点击热点。

> 说明：当前无真实 GLB 资源，查看器用 `shape`（旋转轮廓）程序化生成瓷器。等真实重建算法产出 GLB 后，把后端返回的 `model_url` 直接传给 `modelUrl` 即可，查看器会自动优先加载 GLB。

### 2.3 PorcelainModelManager（共享状态）

文件：`src/stores/PorcelainModelManager.tsx`

通过 React Context 提供，Hook 为：

```ts
const { current, setCurrent, clearCurrent } = usePorcelainModel()
```

- `current: CurrentPorcelain | null` —— 当前瓷器信息（上传对象 / 演示对象）。
- `setCurrent(c)` —— 写入当前对象（三维复原页成功时调用）。
- `clearCurrent()` —— 清除当前对象（各页"返回经典 / 示例"按钮调用，清除后各页恢复默认）。

**只存 URL / 标识 / 元数据，不存大模型文件。**

---

## 3. 共享数据类型（`src/types/porcelain.ts`）

核心类型：

```ts
type DynastyId = 'tang' | 'song' | 'yuan' | 'ming' | 'qing'
type DecorationStyle = 'celadon' | 'bluewhite' | 'fencai' | 'sancai' | 'plain'
type ShapeProfile = Array<[number, number]>   // [半径, 高度] cm，旋转成体

interface GlazeStyle { color: string; roughness: number; metalness: number; clearcoat: number; decoration: DecorationStyle }

interface PorcelainParams { height; maxBellyDiameter; mouthDiameter; footDiameter }

interface PorcelainPart { id; name; yMin; yMax; formDescription; history; knowledge }

interface Porcelain {
  id; name; dynasty; dynastyName; period; summary; description;
  shape: ShapeProfile; glaze: GlazeStyle;
  modelUrl?: string; imageUrl?: string;
  params: PorcelainParams;
  formFeatures: string[]; decorationFeatures: string[]; craftFeatures: string[]; history: string;
  parts: PorcelainPart[];
}

type TaskStatus = 'idle' | 'processing' | 'success' | 'error'
interface ReconstructTask { taskId: string; status: TaskStatus }
interface ModelInfo { porcelain: Porcelain; modelUrl: string | null; note: string }
type ModelSource = 'uploaded' | 'historical' | 'demo'
interface CurrentPorcelain {
  id; name; imageUrl; modelUrl; source: ModelSource; status: TaskStatus;
  dynasty: DynastyId | null; category: string | null;
  porcelain: Porcelain | null; recognition: RecognitionResult | null;
}
interface RecognitionResult { category: string; type: string; features: string[]; note: string }
interface PersonalizedMatch { dynasty: DynastyId; porcelainId: string | null; difference: string; emptyReason?: string }
```

---

## 4. Mock 数据组织

| 文件 | 内容 |
| --- | --- |
| `mock/data.ts` | `dynasties`（5 朝代）、`porcelains`（5 件瓷器，含部位讲解）、`comparisonPair`、AI 问答、`makeGenericParts`（通用部位讲解）、`mockReconstruct` |
| `mock/personalizedEvolutionData.ts` | `recognizeUploaded`（模拟识别）、`getPersonalizedMatches`（按朝代匹配）、`getPersonalizedComparison`（个性化对比参考案例） |

**新增一件瓷器**：在 `mock/data.ts` 的 `porcelains` 数组追加一条（补充 `shape`/`glaze`/`params`/特征文案），朝代列表同步在 `dynasties` 中登记即可。

---

## 5. 四个页面如何调用公共模块

| 页面 | 调用方式 |
| --- | --- |
| 三维复原 | `PorcelainReconstructionService.reconstruct → getTaskStatus → getModel`，成功后 `setCurrent(...)`；`PorcelainViewer` 展示模型 |
| 历史演化 | 读 `usePorcelainModel().current`；有上传对象走个性化模式（`getPersonalizedMatches`），否则走经典模式（`api/timeline`） |
| 形态对比 | 有上传对象 → 上传瓷器 vs 历史参考（`getPersonalizedComparison`）；否则默认宋 vs 明（`api/comparison`）；两侧各用一个 `PorcelainViewer` |
| AI 讲解 | 有上传对象 → 上传瓷器讲解；否则默认汝窑讲解；`PorcelainViewer` 复用部位点击（`parts` / `selectedPartId` / `onPartSelect`） |

---

## 6. 后端接口契约

**三维重建已实现真实后端**（Python + TripoSR，见第 9 节），`PorcelainReconstructionService` 默认调用它（地址 `VITE_RECONSTRUCT_BASE`，默认 `http://localhost:8000`）；设 `VITE_USE_MOCK=true` 回退前端 Mock。

时间轴与AI问答仍为前端Mock；形态对比已实现，下表保留其他模块的接口契约：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/reconstruction` | 上传图片（multipart），返回重建任务（已实现于 `backend/`） |
| GET | `/api/porcelain/:id` | 获取单件瓷器详情 |
| GET | `/api/timeline` | 获取朝代列表 |
| GET | `/api/timeline/:dynasty` | 获取某朝代代表瓷器 |
| POST | `/api/compare` | 获取形态对比数据 |
| POST | `/api/ask` | AI 部位讲解 / 问答 |

真实后端替换步骤：`PorcelainReconstructionService` 已对接 `backend/`；其余 `api/*.ts` 把 Mock 分支换成 `request(...)` 即可，页面与查看器无需改动。

---

## 7. 手动验收步骤

1. 打开首页、历史演化、形态对比、AI 讲解：瓷器完整展示（上半部分不再被裁）。
2. 历史演化默认即可浏览唐/宋/元/明/清五件瓷器，点击朝代内容随之切换。
3. 三维复原页上传图片 → 等待生成 → 出现模型。
4. 上传后进入历史演化：显示「我的瓷器 · 个性化演化」+ 上传图片 + 识别结果；点击不同朝代显示参考案例或空状态；点「返回经典演化」恢复默认。
5. 上传后进入 AI 讲解：显示「我的瓷器 · AI 讲解」+ 上传缩略图；可点部位查看讲解；点「返回示例讲解」恢复汝窑示例。
6. 上传后进入形态对比：显示「我的瓷器 · 形态对比」，左侧上传瓷器 vs 右侧明代参考，参数表 + 差异洞察；点「返回经典对比」恢复宋 vs 明。
7. 清除上传（点各页「返回…」按钮）后，所有页面恢复默认示例。

## 8. 尚未实现（明确不在本阶段范围）

- 真实 AI 识别与 RAG 讲解（重建后的"部位识别/个性化匹配"仍为启发式/模拟）。
- 数据库、用户系统、持久化存储（刷新页面会丢失上传状态）。
- GPU 加速（当前 TripoSR 为 CPU 推理，单张约 1–3 分钟）。

## 9. 真实三维重建后端（TripoSR）

详见 `backend/README.md`。要点：

- 模型：TripoSR（`stabilityai/TripoSR` 权重），CPU 推理。
- 流程：上传图片 → rembg 去背景 → TripoSR 推理 → marching cubes（`scikit-image`，已替换 `torchmcubes` 以避免 Windows 编译）→ 导出 GLB。
- 归一化：网格居中、底部置 y=0、高度缩放到 30（展示单位，无物理意义）。
- 可观测性/不确定性：`uncertainty = 1 - dot(normal, +z)`（启发式，非真实置信度），输出 `heatmap.glb` 热力图。
- 质量报告：顶点/面数、水密性、尺寸、可观测/推断比例、耗时、局限说明。

前端「三维复原」页加载真实 GLB，提供「原始纹理 / 不确定性热力图」切换与质量报告。
