import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth, useCatalog, track } from '../../stores/Platform'
import { request } from '../../api/client'
import PorcelainViewer from '../../components/PorcelainViewer'
import Sources from '../../components/Sources'
export default function Artifact() {
  const { id } = useParams(),
    { items, loading, error } = useCatalog(),
    { user } = useAuth(),
    [part, setPart] = useState(''),
    [saved, setSaved] = useState(false),
    [message, setMessage] = useState('')
  const item = items.find((x) => x.id === id)
  useEffect(() => {
    setSaved(false)
    setMessage('')
    if (!id || !user) return
    let alive = true
    const start = Date.now()
    track(id).catch(() => {})
    request<{ favorites: string[] }>('/learning')
      .then((r) => {
        if (alive) setSaved(r.favorites.includes(id))
      })
      .catch(() => {})
    return () => {
      alive = false
      track(
        id,
        'time',
        Math.min(600, Math.floor((Date.now() - start) / 1000)),
      ).catch(() => {})
    }
  }, [id, user?.id])
  if (!item)
    return (
      <p className="p-12">{error || (loading ? '加载馆藏…' : '文物不存在')}</p>
    )
  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <Link to="/library" className="text-sm text-blue">
        ← 文物库
      </Link>
      <h1 className="mt-5 font-display text-3xl">{item.name}</h1>
      <p className="mt-2 text-ink-soft">
        {item.dynastyName} · {item.period} · {item.category}
      </p>
      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <div>
          <img
            src={item.imageUrl}
            alt={item.name}
            className="panel h-96 w-full object-contain p-4"
          />
          <p className="mt-2 text-xs text-ink-soft">
            馆藏照片 · {item.institution}
          </p>
          <Sources sources={item.sources} />
        </div>
        <div>
          <div className="panel h-96">
            <PorcelainViewer
              shape={item.shape}
              glaze={item.glaze}
              modelUrl={item.modelUrl}
              photoTexture={!!item.textureProjection}
              parts={item.parts}
              selectedPartId={part}
              onPartSelect={setPart}
              showControls
            />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {item.parts.map((p) => (
              <button
                className="btn-ghost !px-3 !py-1"
                key={p.id}
                onClick={() => setPart(p.id)}
              >
                {p.name}
              </button>
            ))}
          </div>
          <p className="mt-3 text-xs text-ink-soft">{item.modelMethod}</p>
          {item.textureProjection && (
            <p className="mt-1 text-xs text-ink-soft">
              纹饰来自正面照片 · 背面采用正面镜像纹理
            </p>
          )}
        </div>
      </div>
      <div className="panel mt-8 space-y-4 p-6">
        <p className="leading-7">{item.description || item.summary}</p>
        <p>工艺：{item.summary}</p>
        <p>文化与年代：{item.history}</p>
        <p>馆藏尺寸：{item.measurementsText}</p>
        <p className="text-xs text-ink-soft">
          馆藏编号：{item.accessionNumber}
        </p>
        <div className="flex flex-wrap gap-3">
          <Link to={'/ai-explain?artifact=' + item.id} className="btn-gold">
            AI讲解
          </Link>
          <Link to={'/comparison?left=' + item.id} className="btn-ghost">
            形态对比
          </Link>
          <Link to={'/learning?artifact=' + item.id} className="btn-ghost">
            相关学习任务
          </Link>
          {user ? (
            <button
              className="btn-ghost"
              onClick={async () => {
                try {
                  await request('/favorites/' + item.id, {
                    method: saved ? 'DELETE' : 'POST',
                  })
                  setSaved(!saved)
                } catch (e) {
                  setMessage((e as Error).message)
                }
              }}
            >
              {saved ? '取消收藏' : '收藏文物'}
            </button>
          ) : (
            <Link className="btn-ghost" to={'/auth?next=/library/' + item.id}>
              登录后收藏
            </Link>
          )}
        </div>
        {message && <p role="alert">{message}</p>}
      </div>
    </div>
  )
}
