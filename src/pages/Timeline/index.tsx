import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Timeline } from '../../components/Timeline'
import { PorcelainViewer } from '../../components/PorcelainViewer'
import { CompareViewer } from '../../components/CompareViewer'
import { fetchTimeline } from '../../api/timeline'
import { request } from '../../api/client'
import { useCatalog, useAuth, track } from '../../stores/Platform'
import { usePorcelainModel } from '../../stores/PorcelainModelManager'
import Sources from '../../components/Sources'
import type {
  DynastyId,
  DynastyInfo,
  PersonalizedMatch,
} from '../../types/porcelain'
export default function TimelinePage() {
  const { items, error: catalogError } = useCatalog(),
    { current, clearCurrent } = usePorcelainModel(),
    { user } = useAuth()
  const [dynasties, setDynasties] = useState<DynastyInfo[]>([]),
    [activeId, setActiveId] = useState<DynastyId>('tang'),
    [selected, setSelected] = useState(''),
    [category, setCategory] = useState(''),
    [matches, setMatches] = useState<PersonalizedMatch[]>([]),
    [error, setError] = useState('')
  const uploaded = current?.source === 'uploaded' && current.porcelain
  useEffect(() => {
    fetchTimeline()
      .then(setDynasties)
      .catch((e) => setError(e.message))
  }, [])
  useEffect(() => {
    if (!uploaded || !current.recognition) return
    const controller = new AbortController()
    setMatches([])
    request<{ matches: PersonalizedMatch[] }>('/evolution/match', {
      method: 'POST',
      body: JSON.stringify(current.recognition),
      signal: controller.signal,
    })
      .then((r) => setMatches(r.matches))
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message)
      })
    return () => controller.abort()
  }, [current?.id])
  const choices = items.filter(
    (x) => x.dynasty === activeId && (!category || x.category === category),
  )
  const match = matches.find((x) => x.dynasty === activeId)
  const item = uploaded
    ? items.find((x) => x.id === match?.porcelainId)
    : (choices.find((x) => x.id === selected) ?? choices[0])
  const index = dynasties.findIndex((d) => d.id === activeId)
  const previous = items.find(
    (x) =>
      x.dynasty === dynasties[index - 1]?.id && x.category === item?.category,
  )
  useEffect(() => {
    if (item && user) track(item.id).catch(() => {})
  }, [item?.id, user?.id])
  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="font-display text-3xl">瓷器历史演化</h1>
      <p className="mt-2 text-sm text-ink-soft">
        拖动时间轴，观察不同朝代馆藏器物的形态、纹饰与工艺。
      </p>
      {uploaded && (
        <div className="panel mt-6 flex flex-wrap items-center justify-between gap-3 p-5">
          <p>
            我的瓷器 · {current.recognition?.category} ·{' '}
            {current.recognition?.features.join('、')}
          </p>
          <button className="btn-ghost" onClick={clearCurrent}>
            浏览全部馆藏
          </button>
        </div>
      )}
      <div className="mt-8">
        <Timeline
          dynasties={dynasties}
          activeId={activeId}
          onChange={setActiveId}
        />
        {dynasties.length > 1 && (
          <input
            aria-label="拖动历史时间轴"
            type="range"
            min={0}
            max={dynasties.length - 1}
            step={1}
            value={index < 0 ? 0 : index}
            onChange={(e) => {
              setActiveId(dynasties[Number(e.target.value)].id)
              setSelected('')
            }}
            className="mt-6 w-full accent-gold"
          />
        )}
      </div>
      {!uploaded && (
        <div className="my-6 flex flex-wrap gap-3">
          <select
            aria-label="历史器型筛选"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value)
              setSelected('')
            }}
            className="border border-ink/20 bg-paper p-2"
          >
            <option value="">全部器型</option>
            {[...new Set(items.map((x) => x.category))].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <select
            aria-label="选择历史器物"
            value={item?.id ?? ''}
            onChange={(e) => setSelected(e.target.value)}
            className="border border-ink/20 bg-paper p-2"
          >
            {choices.map((x) => (
              <option key={x.id} value={x.id}>
                {x.name}
              </option>
            ))}
          </select>
        </div>
      )}
      {(error || catalogError) && (
        <p role="alert" className="my-5">
          {error || catalogError}
        </p>
      )}
      {item ? (
        <>
          <div className="mt-8 grid gap-6 lg:grid-cols-2">
            {uploaded ? (
              <CompareViewer
                left={{
                  ...current.porcelain!,
                  modelUrl: current.modelUrl ?? undefined,
                }}
                right={item}
              />
            ) : (
              <div className="panel h-[440px]">
                <PorcelainViewer
                  shape={item.shape}
                  glaze={item.glaze}
                  modelUrl={item.modelUrl}
                  photoTexture={!!item.textureProjection}
                  showControls
                />
              </div>
            )}
            <div className="panel space-y-5 p-6">
              <span className="eyebrow">
                {item.dynastyName} · {item.period}
              </span>
              <h2 className="font-display text-2xl">{item.name}</h2>
              <img
                src={item.imageUrl}
                alt={item.name}
                className="h-40 w-full object-contain"
              />
              {[
                ['器型', item.formFeatures],
                ['纹饰', item.decorationFeatures],
                ['工艺', item.craftFeatures],
              ].map(([label, features]) => (
                <p className="text-sm leading-7" key={String(label)}>
                  <strong>{String(label)}：</strong>
                  {(features as string[]).join('；') || '馆藏资料未记载'}
                </p>
              ))}
              <p className="text-sm leading-7">{item.description}</p>
              <Sources sources={item.sources} />
              <Link className="text-blue" to={'/library/' + item.id}>
                查看馆藏详情 →
              </Link>
            </div>
          </div>
          {previous && (
            <div className="panel mt-6 space-y-3 p-6">
              <h3 className="font-display text-xl">相邻时期 · 同器型观察</h3>
              <p className="text-sm">
                {previous.dynastyName}代「{previous.name}」：{previous.summary}
              </p>
              <p className="text-sm">
                {item.dynastyName}代「{item.name}」：{item.summary}
              </p>
              <Link
                className="btn-ghost"
                to={'/comparison?left=' + previous.id + '&right=' + item.id}
              >
                比较形态与馆藏工艺
              </Link>
            </div>
          )}
        </>
      ) : (
        <p className="panel mt-8 p-12 text-center">
          {match?.emptyReason ?? '该时期暂无符合条件的器物。'}
        </p>
      )}
    </div>
  )
}
