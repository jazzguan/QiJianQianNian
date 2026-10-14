import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { PorcelainViewer } from '../../components/PorcelainViewer'
import { useCatalog, useAuth } from '../../stores/Platform'
import { request } from '../../api/client'
import type { Porcelain } from '../../types/porcelain'
import ArtifactCard from '../../components/ArtifactCard'

const features = [
  {
    no: '01',
    title: '三维复原',
    desc: '一张照片，让瓷器“立起来”',
    to: '/reconstruction',
  },
  {
    no: '02',
    title: '历史演化',
    desc: '沿着时间轴，看见千年变化',
    to: '/timeline',
  },
  {
    no: '03',
    title: '形态对比',
    desc: '把两件瓷器放在一起比较',
    to: '/comparison',
  },
  {
    no: '04',
    title: 'AI讲解',
    desc: '点击器物，听懂它的故事',
    to: '/ai-explain',
  },
]

export default function Home() {
  const { items } = useCatalog()
  const { user } = useAuth()
  const [recommendation, setRecommendation] = useState<{
    items: Porcelain[]
    tasks: { id: string; prompt: string; artifactIds: string[] }[]
    reason: string
  } | null>(null)
  useEffect(() => {
    request<typeof recommendation>('/recommendations')
      .then(setRecommendation)
      .catch(() => setRecommendation(null))
  }, [user?.id])
  const hero = items.find((x) => x.dynasty === 'song') ?? items[0]
  return (
    <div>
      {/* Hero */}
      <section className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 px-6 py-16 lg:grid-cols-2 lg:py-24">
        <div>
          <span className="eyebrow">QIJIAN QIANNIAN · 瓷器数字博物馆</span>
          <h1 className="mt-4 font-display text-5xl font-semibold leading-tight text-ink">
            器见千年
          </h1>
          <p className="mt-4 font-display text-xl text-ink-soft">
            从一件瓷器，看见千年形制演化
          </p>
          <p className="mt-5 max-w-md text-sm leading-relaxed text-ink-soft">
            将传统二维瓷器图像转化为可交互的三维数字对象，沿历史时间轴观察器型、纹饰与工艺的流变，
            在观察、比较与问答中读懂一件瓷器。
          </p>
          <div className="mt-8 flex items-center gap-4">
            <Link to="/timeline" className="btn-gold">
              开始探索
            </Link>
            <Link to="/reconstruction" className="btn-ghost">
              上传文物
            </Link>
          </div>
        </div>

        <div className="h-[420px] lg:h-[480px]">
          {hero && (
            <PorcelainViewer
              modelUrl={hero.modelUrl}
              photoTexture={!!hero.textureProjection}
              shape={hero.shape}
              glaze={hero.glaze}
              autoRotate
              className="h-full w-full"
            />
          )}
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-6 pb-16">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-2xl">
            {recommendation?.reason ?? '馆藏探索'}
          </h2>
          <Link to="/library" className="text-blue">
            浏览文物库 →
          </Link>
        </div>
        <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {(recommendation?.items ?? items.slice(0, 4)).map((x) => (
            <ArtifactCard key={x.id} item={x} />
          ))}
        </div>
        <Link to="/learning" className="btn-ghost mt-6">
          完成观察、判断、排序与解释任务
        </Link>
        <div className="mt-5 grid gap-4 sm:grid-cols-3">
          {recommendation?.tasks.map((t) => (
            <Link
              key={t.id}
              to={'/learning?artifact=' + t.artifactIds[0]}
              className="panel p-4 text-sm leading-6 text-ink-soft"
            >
              {t.prompt} →
            </Link>
          ))}
        </div>
      </section>
      <section className="border-t border-ink/10 bg-paper">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <div className="flex items-center gap-4">
            <span className="eyebrow">核心功能</span>
            <div className="gold-rule" />
          </div>
          <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            {features.map((f) => (
              <Link
                key={f.no}
                to={f.to}
                className="group panel flex flex-col gap-3 p-6 transition-colors hover:border-gold/40"
              >
                <span className="font-display text-3xl text-gold/50 transition-colors group-hover:text-gold">
                  {f.no}
                </span>
                <h3 className="font-display text-lg text-ink">{f.title}</h3>
                <p className="text-sm leading-relaxed text-ink-soft">
                  {f.desc}
                </p>
                <span className="mt-auto text-xs tracking-wider text-gold opacity-0 transition-opacity group-hover:opacity-100">
                  进入 →
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
