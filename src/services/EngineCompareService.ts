import { request } from '../api/client'

export type EngineName = 'triposr' | 'instantmesh' | 'hunyuan'

export interface EngineResult {
  engine: EngineName
  status: 'pending' | 'running' | 'success' | 'error'
  stage?: string
  vertices?: number
  faces?: number
  elapsedMs?: number
  geometricWatertight?: boolean
  euler?: number
  glbSizeBytes?: number
  meshUrl?: string
  error?: string
}

export interface EngineCompareJob {
  compareId: string
  status: 'processing' | 'success' | 'partial' | 'error' | 'cancelled'
  engines: EngineName[]
  results?: Record<string, EngineResult>
  created: number
  totalElapsedMs?: number
  error?: string
}

export const ENGINE_LABELS: Record<EngineName, string> = {
  triposr: 'TripoSR',
  instantmesh: 'InstantMesh',
  hunyuan: 'Hunyuan3D',
}

export const EngineCompareService = {
  async create(image: File, engines: EngineName[]): Promise<EngineCompareJob> {
    const body = new FormData()
    body.append('file', image)
    body.append('engines', engines.join(','))
    return request('/engine-compare', { method: 'POST', body })
  },
  get(compareId: string): Promise<EngineCompareJob> {
    return request('/engine-compare/' + compareId)
  },
}

export default EngineCompareService
