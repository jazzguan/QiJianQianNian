import { useEffect, useState } from 'react'
import { Timeline } from '../../components/Timeline'
import { PorcelainViewer } from '../../components/PorcelainViewer'
import { EvolutionModeSwitch } from '../../components/EvolutionModeSwitch'
import { HistoricalPorcelainCard } from '../../components/HistoricalPorcelainCard'
import { fetchDynastyPorcelain, fetchPersonalizedMatches, fetchPorcelain, fetchTimeline } from '../../api/timeline'
import { usePorcelainModel } from '../../stores/PorcelainModelManager'
import type { DynastyId, DynastyInfo, PersonalizedMatch, Porcelain } from '../../types/porcelain'

function FeatureList({ title, items }: { title: string; items: string[] }) {
  return (
    <section>
      <h4 className="mb-2 font-medium text-gold">{title}</h4>
      <ul className="flex flex-col gap-1.5">
        {items.map((it) => (
          <li key={it} className="flex gap-2 text-sm leading-relaxed text-ink-soft">
            <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-gold/60" />
            {it}
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function TimelinePage() {
  const { current, clearCurrent } = usePorcelainModel()
  const personalized = !!current

  const [dynasties, setDynasties] = useState<DynastyInfo[]>([])
  const [activeId, setActiveId] = useState<DynastyId>('tang')
  const [porcelain, setPorcelain] = useState<Porcelain | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [matches, setMatches] = useState<PersonalizedMatch[]>([])
  const [reference, setReference] = useState<Porcelain | null>(null)
  const [personalizedLoading, setPersonalizedLoading] = useState(false)

  useEffect(() => {
    let alive = true
    fetchTimeline()
      .then((items) => {
        if (alive) setDynasties(items)
      })
      .catch(() => {
        if (alive) setError('历史朝代数据加载失败，请确认后端服务已启动。')
      })
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    if (personalized) return
    let alive = true
    setLoading(true)
    setError(null)
    fetchDynastyPorcelain(activeId).then((p) => {
      if (!alive) return
      setPorcelain(p)
      setLoading(false)
    }).catch(() => {
      if (!alive) return
      setPorcelain(null)
      setLoading(false)
      setError('该朝代的瓷器数据加载失败。')
    })
    return () => {
      alive = false
    }
  }, [activeId, personalized])

  const activeDynasty = dynasties.find((d) => d.id === activeId)

  useEffect(() => {
    if (!personalized || !current?.recognition) {
      setMatches([])
      setReference(null)
      return
    }
    let alive = true
    setPersonalizedLoading(true)
    setError(null)
    fetchPersonalizedMatches(current.recognition.category)
      .then((items) => {
        if (alive) setMatches(items)
      })
      .catch(() => {
        if (alive) setError('个性化历史匹配加载失败。')
      })
      .finally(() => {
        if (alive) setPersonalizedLoading(false)
      })
    return () => {
      alive = false
    }
  }, [personalized, current?.recognition?.category])

  const activeMatch = matches.find((m) => m.dynasty === activeId)

  useEffect(() => {
    if (!activeMatch?.porcelainId) {
      setReference(null)
      return
    }
    let alive = true
    setPersonalizedLoading(true)
    fetchPorcelain(activeMatch.porcelainId)
      .then((item) => {
        if (alive) setReference(item)
      })
      .catch(() => {
        if (alive) {
          setReference(null)
          setError('历史参考瓷器详情加载失败。')
        }
      })
      .finally(() => {
        if (alive) setPersonalizedLoading(false)
      })
    return () => {
      alive = false
    }
  }, [activeMatch?.porcelainId])

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="font-display text-3xl font-semibold text-ink">瓷器历史演化</h1>
      <p className="mt-2 text-sm text-ink-soft">
        从不同历史时期的瓷器中，观察器型、纹饰与工艺的变化。
      </p>

      {error && <p className="mt-4 text-sm text-red-700">{error}</p>}

      {personalized && (
        <div className="mt-6">
          <EvolutionModeSwitch label="我的瓷器 · 个性化演化" onBack={clearCurrent} />
        </div>
      )}

      <div className="mt-8">
        <Timeline dynasties={dynasties} activeId={activeId} onChange={setActiveId} />
      </div>

      {personalized ? (
        <div className="mt-8 flex flex-col gap-6">
          {/* 上传对象 + 模拟识别 */}
          <div className="panel flex flex-col gap-4 p-5 sm:flex-row sm:items-start">
            {current?.imageUrl && (
              <img
                src={current.imageUrl}
                alt="上传瓷器"
                className="h-28 w-28 shrink-0 rounded-sm border border-ink/10 object-cover"
              />
            )}
            <div>
              <span className="eyebrow">我的瓷器（上传对象）</span>
              <h3 className="mt-1 font-display text-lg text-ink">{current?.name}</h3>
              {current?.recognition && (
                <div className="mt-2 flex flex-col gap-2">
                  <p className="text-sm text-ink-soft">
                    器型类别：<span className="text-gold">{current.recognition.category}</span>
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {current.recognition.features.map((f) => (
                      <span key={f} className="border border-ink/15 px-2 py-0.5 text-xs text-ink-soft">
                        {f}
                      </span>
                    ))}
                  </div>
                  <p className="text-xs text-ink-soft/70">{current.recognition.note}</p>
                </div>
              )}
            </div>
          </div>

          {/* 历史参考案例 / 空状态 */}
          {personalizedLoading ? (
            <div className="panel flex h-40 items-center justify-center p-6 text-center text-sm text-ink-soft">
              加载历史匹配中…
            </div>
          ) : reference ? (
            <HistoricalPorcelainCard porcelain={reference} difference={activeMatch?.difference} />
          ) : (
            <div className="panel flex h-40 items-center justify-center p-6 text-center text-sm text-ink-soft">
              {activeMatch?.emptyReason ?? '暂未找到可靠的同类参考案例'}
            </div>
          )}
        </div>
      ) : (
        <>
          {activeDynasty && (
            <div className="mt-10">
              <div className="flex flex-col gap-1 border-l-2 border-gold/40 pl-4">
                <span className="eyebrow">
                  当前 · {activeDynasty.name}朝（{activeDynasty.years}）
                </span>
                <p className="max-w-3xl text-sm leading-relaxed text-ink-soft">{activeDynasty.intro}</p>
              </div>
            </div>
          )}

          <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-[420px_1fr]">
            <div className="panel h-[440px] overflow-hidden bg-ivory/40">
              {loading || !porcelain ? (
                <div className="flex h-full items-center justify-center text-sm text-ink-soft">加载中…</div>
              ) : (
                <PorcelainViewer
                  shape={porcelain.shape}
                  glaze={porcelain.glaze}
                  autoRotate
                  className="h-full w-full"
                />
              )}
            </div>

            <div className="panel flex flex-col gap-6 p-6">
              {porcelain && (
                <>
                  <div>
                    <span className="eyebrow">{porcelain.dynastyName}</span>
                    <h2 className="mt-1 font-display text-2xl text-ink">{porcelain.name}</h2>
                    <p className="mt-1 text-xs text-ink-soft">{porcelain.period}</p>
                  </div>

                  <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                    <FeatureList title="器型特点" items={porcelain.formFeatures} />
                    <FeatureList title="纹饰特点" items={porcelain.decorationFeatures} />
                    <FeatureList title="工艺特点" items={porcelain.craftFeatures} />
                    <FeatureList title="历史介绍" items={[porcelain.history]} />
                  </div>

                  <div className="border-t border-dashed border-ink/15 pt-4">
                    <span className="eyebrow">演化观察</span>
                    <p className="mt-2 text-sm leading-relaxed text-ink-soft">
                      {activeDynasty?.evolutionNote}
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
