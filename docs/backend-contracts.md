# 后端契约与功能状态

更新：2026-10-14。分支：`codex/morphology-comparison`。已完成与未完成项见[分支状态](branch-status.md)，实际接口见[API 文档](API.md)。

形态对比已实现。下文保留原有历史演化、AI 讲解、数据库及分工设计，这些模块仍待接入真实数据与后端。

## 0. 现状总览

| 功能 | 前端 | 后端 / 数据 / AI |
| --- | --- | --- |
| 三维重建 | ✅ | ✅ 已实现（TripoSR，见[接口文档](API.md)） |
| 历史演化 | ✅ | ❌ 待做（当前 `mock/data.ts`） |
| 形态对比 | ✅ | ✅ 自动测量、GLB导入、归一化和规则差异分析，见[实现文档](morphology-comparison.md) |
| AI 讲解 | ✅ | ❌ 待做（当前 `mock/data.ts` 的 `getPartAnswer`） |

共享类型在 `src/types/porcelain.ts`，当前器物通过 `PorcelainModelManager` 跨页面共享。形态对比请求层已使用真实接口，历史演化与 AI 讲解仍按下面契约待开发。

---

## 1. 数据库设计

建议后端用 SQLite（起步）或 PostgreSQL，表结构如下（与 `types/porcelain.ts` 对齐）：

### period（朝代）
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | `tang/song/yuan/ming/qing` |
| name | string | 唐/宋/元/明/清 |
| start_year / end_year | int | 618 / 907 … |
| intro | text | 朝代瓷器概况 |

### artifact（瓷器）
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | `tang-yueyao` 等 |
| name | string | 器物名 |
| category | string | 器型类别：梅瓶/玉壶春/天球瓶/罐… |
| period_id | string | 外键 → period |
| period_label | string | 「北宋 · 汝窑」等展示用 |
| summary / description / history | text | |
| params | json | `{height, maxBellyDiameter, mouthDiameter, footDiameter}` |
| shape | json | 侧面轮廓 `[[radius, height], ...]`（程序化 3D 用） |
| glaze | json | `{color, roughness, metalness, clearcoat, decoration}` |
| image_uri | string | 真实图片地址（可空） |
| model_uri | string | 真实 GLB 地址（可空，缺省用 shape 程序化） |

### artifact_feature（器型/纹饰/工艺特征）
| 字段 | 类型 |
| --- | --- |
| id | int |
| artifact_id | string → artifact |
| feature_type | enum: `form` / `decoration` / `craft` |
| content | text |

### artifact_part（部位讲解，AI 讲解用）
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | int | |
| artifact_id | string → artifact | |
| part_id | string | `mouth/neck/body/foot/decoration` |
| name | string | 器口/器颈/器身/器足/纹饰 |
| y_min / y_max | float | 部位在器物高度坐标系的区间（点击热点用） |
| form_desc / history / knowledge | text | 三段讲解文案 |

### knowledge_source（知识来源，AI 讲解可信性用）
| 字段 | 类型 |
| --- | --- |
| id | int |
| title | string |
| institution | string |
| url | string |
| doc_type | string |
| artifact_id / part_id | string（可空） |

### evolution_match（个性化演化匹配）
| 字段 | 类型 |
| --- | --- |
| category | string（器型类别） |
| dynasty | string |
| artifact_id | string（可空 = 无匹配） |
| difference | text（与上传瓷器的差异） |

---

## 2. 历史演化 —— 接口契约

负责人：**成员 A**。目标：真实瓷器数据集 + 朝代/器物查询 + 个性化匹配。

| 方法 | 路径 | 请求 | 响应 |
| --- | --- | --- | --- |
| GET | `/api/timeline` | — | `{ dynasties: DynastyInfo[] }` |
| GET | `/api/timeline/:dynasty` | — | `Porcelain`（该朝代代表器物） |
| GET | `/api/porcelain/:id` | — | `Porcelain` |
| POST | `/api/evolution/match` | `{ category }` | `{ matches: PersonalizedMatch[] }` |

`DynastyInfo`：`{id, name, years, intro, porcelainId}`。
`Porcelain`：见 `src/types/porcelain.ts`。
`PersonalizedMatch`：`{dynasty, porcelainId: string|null, difference, emptyReason?}`（`porcelainId=null` 表示该朝无同类案例）。

**前端替换位置**：`src/api/timeline.ts` 的三个函数 + `src/mock/personalizedEvolutionData.ts` 的 `getPersonalizedMatches`。

---

## 3. 形态对比 —— 接口契约

接口已实现于 `backend/app/morphology_routes.py`。目录示例从原有五件器物轮廓测量；导入或重建的GLB从实际网格截面测量。独立运行、完整返回字段与验证方式见[形态对比文档](morphology-comparison.md)。

负责人：**成员 B**。目标：从 3D 网格自动测量形态参数 + 跨时期对比。

| 方法 | 路径 | 请求 | 响应 |
| --- | --- | --- | --- |
| GET | `/api/comparison/artifacts` | — | 内置示例与本机导入目录 |
| POST | `/api/measure` | `{ modelUrl }` 或 `{ artifactId }` | 六项测量与归一化截面轮廓 |
| POST | `/api/measure/upload` | multipart `file / upAxis` | 测量、器物和归一化 GLB 地址 |
| GET | `/api/comparison/models/{id}.glb` | — | 导入的归一化 GLB |
| POST | `/api/compare` | `{ leftId, rightId, leftModelUrl?, rightModelUrl? }` | 参数表、规则洞察、双方器物和测量结果 |

`ComparisonRow`：`{label, left, right}`（如 高度/最大腹径/口径/高腹径比）。

**已实现测量**：网格测量模块从 GLB/`trimesh` 提取：
- `height`：y 轴范围；
- `maxBellyDiameter`：最大截面直径；
- `mouthDiameter`：顶部口沿截面直径；
- `footDiameter`：底部圈足直径；
- `heightBellyRatio` = height / maxBellyDiameter；
- `bellyPosition`：最大腹径所在的相对高度（偏上/居中/偏下）。

尺寸需归一化后再对比；洞察文案可基于参数差值规则生成。**测量值必须标注为"自动提取"，非权威实测。**

**当前前端**：`src/api/comparison.ts` 已调用目录、导入和对比接口；`src/pages/Comparison/index.tsx` 使用后端测量数据展示参数、轮廓和差异，支持 GLB 导入与 CSV 导出。

---

## 4. AI 讲解 —— 接口契约

负责人：**成员 C**。目标：瓷器知识库 + RAG + LLM 生成讲解。

| 方法 | 路径 | 请求 | 响应 |
| --- | --- | --- | --- |
| GET | `/api/ask/parts/:porcelainId` | — | `PorcelainPart[]`（部位列表） |
| POST | `/api/ask/part` | `{ porcelainId, partId }` | `{partId, partName, form, history, knowledge, sources[]}` |
| POST | `/api/ask` | `{ question }` | `{ question, answer, sources[] }` |

`source`：`{title, institution, url}`（可信性：区分「已验证事实」与「AI 辅助解释」）。

**技术路线**：
1. 知识库：`artifact` + `artifact_part` + `knowledge_source` 的文本，向量化（embedding）。
2. 检索：向量库（chroma / faiss / pgvector）取 top-k。
3. 生成：拼 prompt 调 LLM（通义千问 / DeepSeek / GLM 的 API，或本地 Ollama）。
4. 部位识别：前端已有人工标注的 `parts`（y 区间），直接映射到知识条目，**无需自动识别算法**。

**前端替换位置**：`src/api/ai.ts` 的 `fetchPartExplanation` / `askQuestion`。

---

## 5. 分工与依赖

```
成员 A（历史演化·数据）  ──先做，是地基
      ├──→ 成员 B（形态对比） 要它的历史瓷器 mesh 做参照
      └──→ 成员 C（AI 讲解）  要它的知识库
```

- **成员 A** 先交付数据集 + 查询接口（`mock/data.ts` 里的 5 件瓷器可直接作为首批数据）。
- **成员 B / C** 在 A 的接口就绪后并行开发。

## 6. 前端已就绪的协作接口（直接用，别重复造）

- `src/types/porcelain.ts` —— 统一类型。
- `src/api/timeline.ts` / `comparison.ts` / `ai.ts` —— 各改各的，内部 Mock → `request()`。
- `src/stores/PorcelainModelManager.tsx` —— `usePorcelainModel()` 拿到共享的上传对象（`current`）。
- `src/api/client.ts` —— `request()` 统一 fetch 封装，`API_BASE` 默认 `/api`，`USE_MOCK` 由 `VITE_USE_MOCK` 控制。

**Mock → 真实后端**：把对应 `api/*.ts` 里的 `if (USE_MOCK)` 分支换成 `request('/...')` 即可，页面零改动。
