import { useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { PorcelainViewer } from '../PorcelainViewer'
import type { SyncState } from '../PorcelainViewer'
import type { Porcelain } from '../../types/porcelain'

interface CompareViewerProps { left: Porcelain; right: Porcelain; leftLabel?: string; rightLabel?: string }
const regions: Record<string, [string, number, number]> = {
  mouth: ['器口', .92, 1], neck: ['器颈', .78, .92], shoulder: ['肩部', .62, .78],
  body: ['腹部', .12, .62], foot: ['器足', 0, .12],
}
function ViewerCard({ porcelain, label, children }: { porcelain: Porcelain; label?: string; children: ReactNode }) {
  return <div className="panel flex flex-col overflow-hidden">
    <div className="flex items-center justify-between gap-3 border-b border-ink/10 px-5 py-3">
      <div><span className="eyebrow">{label ?? porcelain.dynastyName}</span><h3 className="mt-1 font-display text-base">{porcelain.name}</h3></div>
      <span className="text-xs text-ink-soft">{porcelain.period}</span>
    </div><div className="h-[380px] bg-ivory/40">{children}</div>
  </div>
}

export function CompareViewer({ left, right, leftLabel, rightLabel }: CompareViewerProps) {
  const [sync, setSync] = useState(true)
  const [resetToken, setResetToken] = useState(0)
  const [part, setPart] = useState('')
  const syncRef = useRef<SyncState | null>(null)
  const radius = Math.max(...left.shape.map(p => p[0]), ...right.shape.map(p => p[0]))
  const regionFor = (item: Porcelain) => {
    if (!part) return undefined
    const marked = item.parts.find(p => p.id === part)
    return marked ? { yMin: marked.yMin, yMax: marked.yMax } : { yMin: regions[part][1]*30, yMax: regions[part][2]*30 }
  }
  const leftRegion = useMemo(() => regionFor(left), [part, left])
  const rightRegion = useMemo(() => regionFor(right), [part, right])
  function reset(nextPart = '') { syncRef.current = null; setPart(nextPart); setResetToken(v => v+1) }

  return <div className="flex flex-col gap-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-ink-soft">拖动旋转，滚轮缩放 · {sync ? '同步交互' : '独立交互'}</p>
      <div className="flex gap-2">
        <button type="button" aria-pressed={sync} className="btn-ghost !px-3 !py-1.5 !text-xs"
          onClick={() => { syncRef.current = null; setSync(v => !v); setResetToken(v => v+1) }}>{sync ? '同步旋转 / 缩放：开' : '同步旋转 / 缩放：关'}</button>
        <button type="button" className="btn-ghost !px-3 !py-1.5 !text-xs" onClick={() => reset()}>重置视角</button>
      </div>
    </div>
    <div className="flex flex-wrap items-center gap-2" aria-label="关键区域定位">
      <button className={part ? 'btn-ghost' : 'btn-gold'} onClick={() => reset()}>整体</button>
      {Object.entries(regions).map(([key,[name]]) => <button key={key} aria-pressed={part === key}
        className={part === key ? 'btn-gold' : 'btn-ghost'} onClick={() => reset(key)}>{name}</button>)}
      {part && <span className="text-xs text-ink-soft">两侧已聚焦{regions[part][0]}区域</span>}
    </div>
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {[{ item: left, label: leftLabel, id: 'left', region: leftRegion }, { item: right, label: rightLabel, id: 'right', region: rightRegion }].map(({item,label,id,region}) =>
        <ViewerCard key={id+item.id} porcelain={item} label={label}>
          <PorcelainViewer shape={item.shape} glaze={item.glaze} modelUrl={item.modelUrl} normalizeModel
            viewId={id} syncEnabled={sync} syncRef={syncRef} resetToken={resetToken}
            framingRadius={radius} focusRegion={region} className="h-full w-full" />
        </ViewerCard>)}
    </div>
  </div>
}
export default CompareViewer
