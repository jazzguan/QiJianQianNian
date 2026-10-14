import { PorcelainReconstructionService as service } from '../services/PorcelainReconstructionService'
import type { ReconstructionResult } from '../types/porcelain'
export async function reconstructFromImage(
  image: File | string,
): Promise<ReconstructionResult> {
  const task = await service.reconstruct(image)
  while (true) {
    const status = await service.getTask(task.taskId)
    if (status.status === 'success') {
      const model = await service.getModel(task.taskId)
      return {
        id: task.taskId,
        status: 'done',
        porcelain: model.porcelain,
        note: model.note,
      }
    }
    if (status.status !== 'processing')
      throw new Error(status.error ?? '任务已取消')
    await new Promise((resolve) => setTimeout(resolve, 1500))
  }
}
