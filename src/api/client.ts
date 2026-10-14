const API_BASE: string = import.meta.env.VITE_API_BASE ?? '/api'
export const USE_MOCK = false
export const delay = (ms: number) =>
  new Promise<void>((resolve) => setTimeout(resolve, ms))
export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData))
    headers.set('Content-Type', 'application/json')
  let res: Response
  try {
    res = await fetch(API_BASE + path, {
      ...options,
      headers,
      credentials: 'include',
    })
  } catch {
    throw new Error('无法连接服务，请确认后端已启动。')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(
      typeof body?.detail === 'string'
        ? body.detail
        : '请求失败（' + res.status + '）',
    )
  }
  return res.json() as Promise<T>
}
