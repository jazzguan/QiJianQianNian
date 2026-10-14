import { useMemo, useState } from 'react'
import { useCatalog } from '../../stores/Platform'
import ArtifactCard from '../../components/ArtifactCard'
export default function Library() {
  const { items, loading, error, reload } = useCatalog()
  const [q, setQ] = useState(''),
    [dynasty, setDynasty] = useState(''),
    [category, setCategory] = useState('')
  const filtered = useMemo(
    () =>
      items.filter(
        (x) =>
          (!dynasty || x.dynasty === dynasty) &&
          (!category || x.category === category) &&
          (!q ||
            [x.name, x.originalName, x.description, x.summary]
              .join(' ')
              .toLowerCase()
              .includes(q.toLowerCase())),
      ),
    [items, q, dynasty, category],
  )
  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="font-display text-3xl">文物库</h1>
      <p className="mt-2 text-sm text-ink-soft">
        从馆藏照片、三维形态和馆方资料认识器物。
      </p>
      <div className="panel mt-8 grid gap-4 p-5 sm:grid-cols-3">
        <input
          aria-label="搜索文物"
          placeholder="搜索名称、纹饰或工艺"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="border border-ink/20 bg-ivory p-2"
        />
        <select
          aria-label="朝代筛选"
          value={dynasty}
          onChange={(e) => setDynasty(e.target.value)}
          className="border border-ink/20 bg-ivory p-2"
        >
          <option value="">全部朝代</option>
          {[
            ['tang', '唐'],
            ['song', '宋'],
            ['yuan', '元'],
            ['ming', '明'],
            ['qing', '清'],
          ].map(([id, name]) => (
            <option key={id} value={id}>
              {name}
            </option>
          ))}
        </select>
        <select
          aria-label="器型筛选"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="border border-ink/20 bg-ivory p-2"
        >
          <option value="">全部器型</option>
          {[...new Set(items.map((x) => x.category))].map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </div>
      {error ? (
        <div role="alert" className="mt-6">
          {error}
          <button onClick={reload} className="btn-ghost ml-4">
            重试
          </button>
        </div>
      ) : loading ? (
        <p className="mt-8">正在加载馆藏…</p>
      ) : (
        <>
          <p className="my-5 text-sm text-ink-soft">共 {filtered.length} 件</p>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {filtered.map((x) => (
              <ArtifactCard key={x.id} item={x} />
            ))}
          </div>
          {!filtered.length && (
            <p className="py-16 text-center">没有符合条件的器物。</p>
          )}
        </>
      )}
    </div>
  )
}
