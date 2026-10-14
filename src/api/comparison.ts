import type {
  ComparisonPair,
  ComparisonRequest,
  MorphologyMeasurement,
} from '../types/porcelain'

const BASE = (import.meta.env.VITE_COMPARISON_BASE ?? '').replace(/\/$/, '')

async function post<T>(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`${BASE}/api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
    credentials: 'include',
  })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(
      typeof error?.detail === 'string'
        ? error.detail
        : `对比请求失败（${response.status}）`,
    )
  }
  return response.json() as Promise<T>
}

export function measureModel(
  modelUrl: string,
  signal?: AbortSignal,
): Promise<MorphologyMeasurement> {
  return post('/measure', { modelUrl }, signal)
}

export function fetchComparisonPair(
  selection: ComparisonRequest = {
    leftId: 'song-ruyao',
    rightId: 'ming-qinghua',
  },
  signal?: AbortSignal,
): Promise<ComparisonPair> {
  return post('/compare', selection, signal)
}
