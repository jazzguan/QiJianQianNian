import type { ComparisonPair, ComparisonRequest, MorphologyMeasurement, Porcelain } from '../types/porcelain'

const BASE = (import.meta.env.VITE_COMPARISON_BASE ?? '').replace(/\/$/, '')

function viewModel(item: Porcelain): Porcelain {
  return item.modelUrl?.startsWith('/') && BASE ? { ...item, modelUrl: BASE + item.modelUrl } : item
}

function localModel(url?: string) {
  return url && BASE && url.startsWith(BASE + '/') ? url.slice(BASE.length) : url
}

async function call<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try { response = await fetch(`${BASE}/api${path}`, options) }
  catch (error) {
    if (error instanceof TypeError) throw new Error('无法连接形态对比服务，请确认服务已启动。')
    throw error
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `形态对比服务请求失败（${response.status}）`)
  }
  return response.json()
}

export async function fetchComparisonCatalog(signal?: AbortSignal): Promise<Porcelain[]> {
  return (await call<Porcelain[]>('/comparison/artifacts', { signal })).map(viewModel)
}

export async function fetchComparisonPair(selection: ComparisonRequest = { leftId: 'song-ruyao', rightId: 'ming-qinghua' }, signal?: AbortSignal): Promise<ComparisonPair> {
  const payload = { ...selection, leftModelUrl: localModel(selection.leftModelUrl), rightModelUrl: localModel(selection.rightModelUrl) }
  const pair = await call<ComparisonPair>('/compare', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal })
  return { ...pair, left: pair.left && viewModel(pair.left), right: pair.right && viewModel(pair.right) }
}

export function measureModel(modelUrl: string, signal?: AbortSignal): Promise<MorphologyMeasurement> {
  return call('/measure', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ modelUrl: localModel(modelUrl) }), signal })
}

export async function importComparisonModel(file: File, upAxis: string, signal?: AbortSignal): Promise<{ artifact: Porcelain; measurement: MorphologyMeasurement }> {
  const form = new FormData()
  form.set('file', file)
  form.set('upAxis', upAxis)
  const result = await call<{ artifact: Porcelain; measurement: MorphologyMeasurement }>('/measure/upload', { method: 'POST', body: form, signal })
  return { ...result, artifact: viewModel(result.artifact) }
}
