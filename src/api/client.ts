const BACKEND_ORIGIN = String(
  import.meta.env.VITE_BACKEND_ORIGIN ?? '',
).replace(/\/$/, '')
const API_BASE: string =
  import.meta.env.VITE_API_BASE ?? `${BACKEND_ORIGIN}/api`
const TOKEN_KEY = 'qjqn-native-token'
const assetAccessCache = new Map<string, Promise<string>>()

export function setAccessToken(token?: string | null) {
  assetAccessCache.clear()
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export function resolveBackendUrl(path?: string | null): string | undefined {
  if (!path) return undefined
  if (/^(https?:|blob:|data:)/i.test(path)) return path
  return BACKEND_ORIGIN && path.startsWith('/') ? BACKEND_ORIGIN + path : path
}

export function backendEndpoint(path: string): string {
  return resolveBackendUrl(path) ?? path
}

async function resolvePrivateAsset(path: string, headers: Headers) {
  const parsed = new URL(path, BACKEND_ORIGIN || window.location.origin)
  if (parsed.searchParams.has('ticket')) return resolveBackendUrl(path) ?? path
  const cacheKey = `${localStorage.getItem(TOKEN_KEY) ?? ''}:${parsed.pathname}`
  let pending = assetAccessCache.get(cacheKey)
  if (!pending) {
    pending = fetch(
      `${API_BASE}/files/access?path=${encodeURIComponent(parsed.pathname)}`,
      { headers, credentials: 'include' },
    )
      .then(async (response) => {
        if (!response.ok) throw new Error('无法获取模型文件访问权限。')
        const result = (await response.json()) as { url: string }
        return resolveBackendUrl(result.url) ?? result.url
      })
      .catch((error) => {
        assetAccessCache.delete(cacheKey)
        throw error
      })
    assetAccessCache.set(cacheKey, pending)
  }
  return pending
}

async function resolveAssets<T>(value: T, headers: Headers): Promise<T> {
  if (typeof value === 'string') {
    const parsed = new URL(value, BACKEND_ORIGIN || window.location.origin)
    if (parsed.pathname.startsWith('/files/'))
      return (await resolvePrivateAsset(value, headers)) as T
    return (
      parsed.pathname.startsWith('/media/') ? resolveBackendUrl(value) : value
    ) as T
  }
  if (Array.isArray(value))
    return (await Promise.all(
      value.map((item) => resolveAssets(item, headers)),
    )) as T
  if (value && typeof value === 'object') {
    for (const [key, item] of Object.entries(value)) {
      ;(value as Record<string, unknown>)[key] = await resolveAssets(
        item,
        headers,
      )
    }
  }
  return value
}
export const delay = (ms: number) =>
  new Promise<void>((resolve) => setTimeout(resolve, ms))
export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  const accessToken = localStorage.getItem(TOKEN_KEY)
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
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
  return resolveAssets((await res.json()) as T, headers)
}
