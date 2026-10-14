export type DynastyId = 'tang' | 'song' | 'yuan' | 'ming' | 'qing'

export type DecorationStyle = 'celadon' | 'bluewhite' | 'fencai' | 'sancai' | 'plain'

/** 器物侧面轮廓：数组元素为 [半径, 高度]（单位 cm），沿中轴旋转成体 */
export type ShapeProfile = Array<[number, number]>

/** 别名：轮廓类型在查看器组件中的惯用名 */
export type PorcelainShape = ShapeProfile

export interface GlazeStyle {
  /** 材质基色（celadon 为青釉色，bluewhite/fencai 为近白釉色） */
  color: string
  roughness: number
  metalness: number
  clearcoat: number
  decoration: DecorationStyle
}

export interface PorcelainParams {
  height: number
  maxBellyDiameter: number
  mouthDiameter: number
  footDiameter: number
}

export interface PorcelainPart {
  id: string
  name: string
  /** 归一化到器物高度坐标系的区域范围（单位 cm，与 ShapeProfile 同坐标系） */
  yMin: number
  yMax: number
  formDescription: string
  history: string
  knowledge: string
}

export interface Porcelain {
  id: string
  name: string
  dynasty: DynastyId | null
  dynastyName: string
  period: string
  summary: string
  description: string
  shape: ShapeProfile
  glaze: GlazeStyle
  /** 未来后端返回的真实 GLB 地址，前端优先使用，缺省时回退到程序化轮廓 */
  modelUrl?: string
  measurementSource?: 'profile' | 'mesh'
  imageUrl?: string
  params: PorcelainParams
  formFeatures: string[]
  decorationFeatures: string[]
  craftFeatures: string[]
  history: string
  material?: string
  use?: string
  parts: PorcelainPart[]
}

export interface DynastyInfo {
  id: DynastyId
  name: string
  years: string
  intro: string
  porcelainId: string
  evolutionNote: string
}

export interface ReconstructionResult {
  id: string
  status: 'processing' | 'done'
  porcelain: Porcelain
  note: string
}

export interface ComparisonRow {
  label: string
  left: string
  right: string
}

export interface ComparisonPair {
  id: string
  leftId: string
  rightId: string
  rows: ComparisonRow[]
  insight: string
  left?: Porcelain
  right?: Porcelain
  leftLabel?: string
  rightLabel?: string
  leftMeasurement?: MorphologyMeasurement
  rightMeasurement?: MorphologyMeasurement
}

export interface MorphologyMeasurement extends PorcelainParams {
  heightBellyRatio: number
  bellyPosition: number
  bellyPositionLabel: string
  shape: ShapeProfile
  source: 'profile' | 'mesh'
  method: '自动提取'
  unit: string
}

export interface ComparisonRequest {
  leftId?: string
  rightId?: string
  leftModelUrl?: string
  rightModelUrl?: string
  leftLabel?: string
  rightLabel?: string
}

export interface AIAnswer {
  partId: string
  partName: string
  formDescription: string
  history: string
  knowledge: string
}

export interface AIQueryAnswer {
  question: string
  answer: string
}

export interface AIQuerySuggestion {
  id: string
  question: string
}

/** 上传图片后的模拟器型识别结果 */
export interface RecognitionResult {
  category: string
  type: string
  features: string[]
  note: string
}

/** 个性化演化中，某朝代的历史参考案例匹配结果 */
export interface PersonalizedMatch {
  dynasty: DynastyId
  porcelainId: string | null
  difference: string
  emptyReason?: string
}

export type TaskStatus = 'idle' | 'processing' | 'success' | 'error'

export interface ReconstructTask {
  taskId: string
  status: TaskStatus
}

/** 三维重建得到的模型信息。modelUrl 为真实 GLB 地址，Mock 时为 null（用程序化轮廓）。 */
export interface ModelInfo {
  /** 程序化兜底瓷器（Mock 或真实后端缺失时用于展示/识别） */
  porcelain: Porcelain
  modelUrl: string | null
  /** 不确定性热力图 GLB 地址（真实重建时返回） */
  heatmapUrl?: string | null
  /** 粗略侧面轮廓 [半径, 高度]，用于取景 / 程序化兜底 */
  shape?: PorcelainShape | null
  /** 重建质量报告 */
  report?: ReconstructionReport | null
  note: string
}

/** 重建质量报告（含可观测性/不确定性启发式统计与已知局限）。 */
export interface ReconstructionReport {
  vertices: number
  faces: number
  watertight: boolean
  bbox: [number, number, number]
  observedRatio: number
  inferredRatio: number
  elapsedMs: number
  note: string
}

export type ModelSource = 'uploaded' | 'historical' | 'demo'

/** 共享的"当前瓷器"信息（上传对象 / 演示对象）。 */
export interface CurrentPorcelain {
  id: string
  name: string
  imageUrl: string | null
  modelUrl: string | null
  heatmapUrl?: string | null
  source: ModelSource
  status: TaskStatus
  dynasty: DynastyId | null
  category: string | null
  porcelain: Porcelain | null
  recognition: RecognitionResult | null
  report?: ReconstructionReport | null
}
