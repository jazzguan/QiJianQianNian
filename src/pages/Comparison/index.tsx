import { useEffect, useRef, useState } from 'react'
import { CompareViewer } from '../../components/CompareViewer'
import { fetchComparisonCatalog, fetchComparisonPair, importComparisonModel } from '../../api/comparison'
import { usePorcelainModel } from '../../stores/PorcelainModelManager'
import type { ComparisonPair, Porcelain, ShapeProfile } from '../../types/porcelain'

function ProfileChart({ left, right }: { left: ShapeProfile; right: ShapeProfile }) {
  const radius = Math.max(...left.map(p => p[0]), ...right.map(p => p[0]), 1)
  const points = (shape: ShapeProfile) => [...shape.map(([r,y]) => [r,y]), ...[...shape].reverse().map(([r,y]) => [-r,y])]
    .map(([r,y]) => `${220 + r/radius*155},${310-y/30*280}`).join(' ')
  return <div className="panel p-5">
    <h2 className="font-display text-lg">截面外径轮廓</h2>
    <p className="mt-1 text-xs text-ink-soft">统一高度30，叠加观察腹径与口足的相对变化。</p>
    <svg viewBox="0 0 440 350" role="img" aria-label="左右器物的归一化截面轮廓叠加" className="mx-auto mt-4 w-full max-w-md">
      {[0,10,20,30].map(y => <g key={y}><line x1="55" x2="405" y1={310-y/30*280} y2={310-y/30*280} stroke="#bcb7aa" opacity=".35"/><text x="22" y={315-y/30*280} fontSize="12" fill="#676354">{y}</text></g>)}
      <line x1="220" x2="220" y1="30" y2="310" stroke="#bcb7aa" strokeDasharray="4 4"/>
      <polygon points={points(left)} fill="#387087" fillOpacity=".08" stroke="#387087" strokeWidth="2"/>
      <polygon points={points(right)} fill="#ac792d" fillOpacity=".06" stroke="#ac792d" strokeWidth="2" strokeDasharray="5 3"/>
      <text x="95" y="340" fill="#387087" fontSize="13">实线：左侧</text><text x="260" y="340" fill="#ac792d" fontSize="13">虚线：右侧</text>
    </svg>
  </div>
}

function exportCsv(pair: ComparisonPair) {
  const cell = (value: string) => '"' + (/^[=+@-]/.test(value) ? "'" : '') + value.replace(/"/g, '""') + '"'
  const rows = [['参数（自动提取；归一化高度30）', pair.leftLabel ?? '', pair.rightLabel ?? ''],
    ...pair.rows.map(row => [row.label, row.left, row.right]), ['差异洞察', pair.insight, '']]
  const url = URL.createObjectURL(new Blob(['\uFEFF' + rows.map(row => row.map(cell).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a'); link.href = url; link.download = '形态对比.csv'; link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export default function Comparison() {
  const { current } = usePorcelainModel()
  const [items, setItems] = useState<Porcelain[]>([])
  const [leftId, setLeftId] = useState('song-ruyao')
  const [rightId, setRightId] = useState('ming-qinghua')
  const [pair, setPair] = useState<ComparisonPair | null>(null)
  const [loading, setLoading] = useState(false)
  const [catalogLoading, setCatalogLoading] = useState(true)
  const [uploading, setUploading] = useState<'left' | 'right' | null>(null)
  const [axis, setAxis] = useState('y')
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)
  const [ready, setReady] = useState(false)
  const activeRequest = useRef<AbortController | null>(null)
  const uploadRequest = useRef<AbortController | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    activeRequest.current?.abort()
    setCatalogLoading(true); setLoading(false); setPair(null); setError('')
    fetchComparisonCatalog(controller.signal).then(data => {
      if (controller.signal.aborted) return
      const shared = current?.source === 'uploaded' && current.modelUrl && current.porcelain
        ? { ...current.porcelain, id: current.id, modelUrl: current.modelUrl, name: current.name || '我的瓷器', measurementSource: 'mesh' as const } : null
      setItems(shared ? [...data, shared] : data)
      setLeftId(shared?.id ?? 'song-ruyao'); setRightId('ming-qinghua'); setReady(true)
    }).catch(e => { if (!controller.signal.aborted) setError(e.message) })
      .finally(() => { if (!controller.signal.aborted) setCatalogLoading(false) })
    return () => controller.abort()
  }, [reload, current?.id, current?.modelUrl])

  useEffect(() => () => { activeRequest.current?.abort(); uploadRequest.current?.abort() }, [])

  async function compare(left = leftId, right = rightId) {
    const a = items.find(x => x.id === left), b = items.find(x => x.id === right)
    if (!a || !b) return
    activeRequest.current?.abort()
    const controller = new AbortController(); activeRequest.current = controller
    setLoading(true); setError(''); setPair(null)
    try {
      const result = await fetchComparisonPair({
        leftId: a.id, rightId: b.id, leftModelUrl: a.modelUrl, rightModelUrl: b.modelUrl,
        leftLabel: a.name, rightLabel: b.name,
      }, controller.signal)
      if (!controller.signal.aborted) setPair(result)
    } catch (e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : '对比失败') }
    finally { if (!controller.signal.aborted) setLoading(false) }
  }

  useEffect(() => { if (ready) { setReady(false); void compare() } }, [ready, items])

  function choose(side: 'left' | 'right', value: string) {
    activeRequest.current?.abort(); setLoading(false); setPair(null); setError('')
    if (side === 'left') setLeftId(value); else setRightId(value)
  }

  async function upload(side: 'left' | 'right', file?: File) {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.glb')) { setError('请上传GLB模型'); return }
    if (file.size > 20 * 1024 * 1024) { setError('GLB不能超过20MB'); return }
    const controller = new AbortController(); uploadRequest.current = controller
    setUploading(side); setError('')
    try {
      const result = await importComparisonModel(file, axis, controller.signal)
      if (controller.signal.aborted) return
      setItems(old => [...old, result.artifact]); choose(side, result.artifact.id)
    } catch (e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : '导入失败') }
    finally { if (!controller.signal.aborted) setUploading(null) }
  }

  const features: Array<[string, keyof Porcelain]> = [
    ['器型', 'formFeatures'], ['纹饰', 'decorationFeatures'], ['工艺', 'craftFeatures'], ['材质', 'material'], ['用途', 'use'], ['历史背景', 'history'],
  ]
  const describe = (item: Porcelain, key: keyof Porcelain) => {
    const value = item[key]; return Array.isArray(value) ? value.join('；') || '未提供资料' : String(value || '未提供资料')
  }

  return <div className="mx-auto max-w-6xl px-6 py-12">
    <h1 className="font-display text-3xl font-semibold">跨时期形态对比</h1>
    <p className="mt-2 text-sm text-ink-soft">选择两件器物或导入GLB，从三维截面测量形态，观察比例、纹饰与工艺的差异。</p>
    <div className="panel mt-6 space-y-5 p-5">
      <div className="grid gap-5 sm:grid-cols-2">
        {(['left', 'right'] as const).map(side => <div key={side}>
          <label htmlFor={side+'-artifact'} className="mb-2 block text-sm">{side === 'left' ? '左侧器物' : '右侧器物'}</label>
          <select id={side+'-artifact'} value={side === 'left' ? leftId : rightId} disabled={catalogLoading || !!uploading}
            onChange={e => choose(side, e.target.value)} className="w-full border border-ink/20 bg-paper p-2">
            {items.map(item => <option key={item.id} value={item.id}>{item.dynastyName} · {item.name}</option>)}
          </select>
          <label className="mt-3 inline-flex cursor-pointer items-center text-sm text-blue">
            {uploading === side ? '正在导入与测量…' : '导入GLB模型'}
            <input aria-label={side === 'left' ? '导入左侧GLB' : '导入右侧GLB'} type="file" accept=".glb" disabled={catalogLoading || !!uploading}
              className="ml-3 max-w-[230px] text-xs" onChange={e => { void upload(side, e.target.files?.[0]); e.target.value = '' }} />
          </label>
        </div>)}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="text-sm text-ink-soft">导入模型的竖直轴
          <select aria-label="导入模型竖直轴" value={axis} disabled={!!uploading} onChange={e => setAxis(e.target.value)} className="ml-2 border border-ink/20 bg-paper p-1">
            {['y','z','x','-y','-z','-x'].map(a => <option key={a} value={a}>{a.toUpperCase()}</option>)}
          </select>
        </label>
        <button className="btn-gold" disabled={loading || catalogLoading || !!uploading || !items.length} onClick={() => void compare()}>
          {loading ? '正在计算…' : '开始对比'}
        </button>
      </div>
      <p className="text-xs text-ink-soft">内置五件目录器物使用示例轮廓；导入GLB和当前重建模型使用网格截面。测量值标为自动提取，统一高度30。</p>
    </div>
    {error && <div role="alert" className="panel mt-5 flex flex-wrap items-center justify-between gap-3 border-red-300 p-4">
      <p>{error}</p><button className="btn-ghost" onClick={() => catalogLoading || !items.length ? setReload(x => x+1) : void compare()}>重试</button>
    </div>}
    {(loading || catalogLoading) && <p role="status" className="mt-8 text-center text-sm">正在加载与测量…</p>}
    {!loading && !catalogLoading && !pair && !error && <p className="panel mt-8 p-8 text-center text-ink-soft">已选择器物，点击“开始对比”查看测量结果。</p>}
    {pair?.left && pair.right && <div className="mt-8 space-y-6">
      <CompareViewer key={pair.id} left={pair.left} right={pair.right} />
      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <div className="panel overflow-x-auto">
          <div className="flex items-center justify-between gap-3 border-b border-ink/10 p-5">
            <div><h2 className="font-display text-lg">形态参数 · 自动提取</h2><p className="mt-1 text-xs text-ink-soft">归一化单位（高度=30）</p></div>
            <button className="btn-ghost !px-3 !py-2 text-xs" onClick={() => exportCsv(pair)}>导出CSV</button>
          </div>
          <table className="w-full text-sm"><thead><tr className="border-b border-ink/10 text-left text-ink-soft">
            <th className="p-4">参数</th><th className="p-4">{pair.leftLabel}</th><th className="p-4">{pair.rightLabel}</th>
          </tr></thead><tbody>{pair.rows.map(row => <tr key={row.label} className="border-b border-ink/5">
            <td className="p-4">{row.label}</td><td className="p-4">{row.left}</td><td className="p-4">{row.right}</td>
          </tr>)}</tbody></table>
          <p className="p-4 text-xs text-ink-soft">左侧：{pair.leftMeasurement?.source === 'mesh' ? 'GLB网格截面' : '目录示例轮廓'} · 右侧：{pair.rightMeasurement?.source === 'mesh' ? 'GLB网格截面' : '目录示例轮廓'}。口足测量顶部、底部邻近截面的外径。</p>
        </div>
        <ProfileChart left={pair.left.shape} right={pair.right.shape} />
      </div>
      <div className="panel p-6"><h2 className="font-display text-xl">形态差异</h2><p className="mt-3 text-sm leading-7">{pair.insight}</p></div>
      <div className="panel overflow-x-auto">
        <h2 className="border-b border-ink/10 p-5 font-display text-lg">目录特征对照</h2>
        <table className="w-full text-sm"><thead><tr className="border-b border-ink/10 text-left"><th className="p-4">特征</th><th className="p-4">{pair.leftLabel}</th><th className="p-4">{pair.rightLabel}</th></tr></thead>
          <tbody>{features.map(([label,key]) => <tr key={key} className="border-b border-ink/5"><td className="p-4">{label}</td><td className="p-4 leading-7">{describe(pair.left!,key)}</td><td className="p-4 leading-7">{describe(pair.right!,key)}</td></tr>)}</tbody>
        </table>
      </div>
    </div>}
  </div>
}
