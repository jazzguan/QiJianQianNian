import { request } from '../api/client'
import type {
  CurrentPorcelain,
  ModelInfo,
  ReconstructTask,
} from '../types/porcelain'
export function asCurrent(model: ModelInfo): CurrentPorcelain {
  return {
    id: model.porcelain.id,
    name: model.porcelain.name,
    imageUrl: model.porcelain.imageUrl ?? null,
    modelUrl: model.modelUrl,
    previewUrl: model.previewUrl,
    heatmapUrl: model.heatmapUrl,
    source: 'uploaded',
    status: 'success',
    dynasty: null,
    category: model.recognition?.category ?? null,
    porcelain: model.porcelain,
    recognition: model.recognition ?? null,
    report: model.report,
  }
}
export const PorcelainReconstructionService = {
  async reconstruct(
    image: File | string,
    engine?: string,
  ): Promise<ReconstructTask> {
    if (!(image instanceof File)) throw new Error('请选择本地图片')
    const body = new FormData()
    body.append('file', image)
    if (engine && engine !== 'auto') body.append('engine', engine)
    return request('/reconstruct', { method: 'POST', body })
  },
  getTask(taskId: string): Promise<ReconstructTask> {
    return request('/task/' + taskId)
  },
  /** 环绕建档：2～40 张多视角照片，走摄影测量（Meshroom）。 */
  async reconstructMultiview(files: File[]): Promise<ReconstructTask> {
    if (files.length < 2) throw new Error('至少需要 2 张照片')
    if (files.length > 40) throw new Error('最多 40 张照片')
    const body = new FormData()
    files.forEach((file) => body.append('files', file))
    return request('/reconstruct/multiview', { method: 'POST', body })
  },
  async getTaskStatus(taskId: string) {
    return (await this.getTask(taskId)).status
  },
  getModel(taskId: string): Promise<ModelInfo> {
    return request('/model/' + taskId)
  },
  deleteModel(taskId: string): Promise<{ ok: boolean; removedFiles: number }> {
    return request('/models/' + taskId, { method: 'DELETE' })
  },
}
export default PorcelainReconstructionService
