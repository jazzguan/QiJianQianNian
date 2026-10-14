import { PorcelainViewer } from '../PorcelainViewer'
import type { Porcelain } from '../../types/porcelain'

interface HistoricalPorcelainCardProps {
  porcelain: Porcelain
  tag?: string
  difference?: string
}

/** 历史参考案例卡片：明确区分于用户上传对象。 */
export function HistoricalPorcelainCard({
  porcelain,
  tag = '历史参考案例',
  difference,
}: HistoricalPorcelainCardProps) {
  return (
    <div className="panel overflow-hidden">
      <div className="flex items-center justify-between border-b border-ink/10 px-5 py-3">
        <div>
          <span className="eyebrow">
            {tag} · {porcelain.dynastyName}
          </span>
          <h3 className="mt-0.5 font-display text-lg text-ink">
            {porcelain.name}
          </h3>
        </div>
        <span className="text-xs text-ink-soft">{porcelain.period}</span>
      </div>

      <div className="h-[340px] bg-ivory/40">
        <PorcelainViewer
          modelUrl={porcelain.modelUrl}
          photoTexture={!!porcelain.textureProjection}
          shape={porcelain.shape}
          glaze={porcelain.glaze}
          autoRotate
          className="h-full w-full"
        />
      </div>

      {difference && (
        <div className="border-t border-dashed border-ink/15 px-5 py-3">
          <span className="eyebrow">与上传瓷器的差异</span>
          <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">
            {difference}
          </p>
        </div>
      )}
    </div>
  )
}

export default HistoricalPorcelainCard
