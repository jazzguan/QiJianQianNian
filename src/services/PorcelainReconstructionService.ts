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
  async reconstruct(image: File | string): Promise<ReconstructTask> {
    if (!(image instanceof File)) throw new Error('请选择本地图片')
    const body = new FormData()
    body.append('file', image)
    return request('/reconstruct', { method: 'POST', body })
  },
  getTask(taskId: string): Promise<ReconstructTask> {
    return request('/task/' + taskId)
  },
  async getTaskStatus(taskId: string) {
    return (await this.getTask(taskId)).status
  },
  getModel(taskId: string): Promise<ModelInfo> {
    return request('/model/' + taskId)
  },
}
export default PorcelainReconstructionService
