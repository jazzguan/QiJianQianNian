import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import type { ReactNode } from 'react'
import type { CurrentPorcelain } from '../types/porcelain'
import { useAuth } from './Platform'
import {
  asCurrent,
  PorcelainReconstructionService,
} from '../services/PorcelainReconstructionService'
interface Value {
  current: CurrentPorcelain | null
  setCurrent: (c: CurrentPorcelain) => void
  clearCurrent: () => void
}
const Context = createContext<Value | null>(null)
export function PorcelainModelManagerProvider({
  children,
}: {
  children: ReactNode
}) {
  const { user } = useAuth(),
    [current, setValue] = useState<CurrentPorcelain | null>(null)
  const key = user ? 'qjqn-model:' + user.id : ''
  useEffect(() => {
    let alive = true
    setValue(null)
    if (key) {
      const id = localStorage.getItem(key)
      if (id)
        PorcelainReconstructionService.getModel(id)
          .then((m) => {
            if (alive) setValue(asCurrent(m))
          })
          .catch(() => localStorage.removeItem(key))
    }
    return () => {
      alive = false
    }
  }, [key])
  const setCurrent = useCallback(
    (c: CurrentPorcelain) => {
      setValue(c)
      if (key && c.source === 'uploaded') localStorage.setItem(key, c.id)
    },
    [key],
  )
  const clearCurrent = useCallback(() => {
    setValue(null)
    if (key) localStorage.removeItem(key)
  }, [key])
  const value = useMemo(
    () => ({ current, setCurrent, clearCurrent }),
    [current, setCurrent, clearCurrent],
  )
  return <Context.Provider value={value}>{children}</Context.Provider>
}
export function usePorcelainModel() {
  const c = useContext(Context)
  if (!c) throw new Error('模型上下文尚未初始化')
  return c
}
export default PorcelainModelManagerProvider
