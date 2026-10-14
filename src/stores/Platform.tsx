import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'
import type { ReactNode } from 'react'
import { request } from '../api/client'
import type { Porcelain } from '../types/porcelain'

interface User {
  id: string
  username: string
}
const Auth = createContext<{
  user: User | null
  ready: boolean
  authenticate: (
    register: boolean,
    username: string,
    password: string,
  ) => Promise<void>
  logout: () => Promise<void>
}>(null!)
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null),
    [ready, setReady] = useState(false)
  useEffect(() => {
    request<{ user: User | null }>('/auth/me')
      .then((r) => setUser(r.user))
      .catch(() => setUser(null))
      .finally(() => setReady(true))
  }, [])
  async function authenticate(
    register: boolean,
    username: string,
    password: string,
  ) {
    setUser(
      await request<User>(register ? '/auth/register' : '/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      }),
    )
  }
  async function logout() {
    await request('/auth/logout', { method: 'POST' })
    setUser(null)
  }
  return (
    <Auth.Provider value={{ user, ready, authenticate, logout }}>
      {children}
    </Auth.Provider>
  )
}
export const useAuth = () => useContext(Auth)
const Catalog = createContext<{
  items: Porcelain[]
  loading: boolean
  error: string
  reload: () => void
}>(null!)
export function CatalogProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Porcelain[]>([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState('')
  const reload = useCallback(() => {
    setLoading(true)
    setError('')
    request<{ items: Porcelain[] }>('/artifacts')
      .then((r) => setItems(r.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])
  useEffect(reload, [reload])
  return (
    <Catalog.Provider value={{ items, loading, error, reload }}>
      {children}
    </Catalog.Provider>
  )
}
export const useCatalog = () => useContext(Catalog)
export function track(
  artifactId: string,
  kind = 'explore',
  durationSeconds = 0,
) {
  return request('/learning/events', {
    method: 'POST',
    body: JSON.stringify({ artifactId, kind, durationSeconds }),
  })
}
