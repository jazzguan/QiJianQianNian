import { useEffect, useState } from 'react'
import { CompareViewer } from '../../components/CompareViewer'
import { EvolutionModeSwitch } from '../../components/EvolutionModeSwitch'
import { fetchComparisonPair } from '../../api/comparison'
import { useSearchParams } from 'react-router-dom'
import { useCatalog, useAuth, track } from '../../stores/Platform'
import Sources from '../../components/Sources'
import { request } from '../../api/client'
import { usePorcelainModel } from '../../stores/PorcelainModelManager'
import type {
  AIQueryAnswer,
  ComparisonPair,
  ComparisonRow,
  MorphologyMeasurement,
  Porcelain,
} from '../../types/porcelain'

function ParamsTable({
  rows,
  leftLabel,
  rightLabel,
}: {
  rows: ComparisonRow[]
  leftLabel: string
  rightLabel: string
}) {
  return (
    <div className="panel overflow-x-auto">
      <div className="border-b border-ink/10 px-6 py-4">
        <span className="eyebrow">关键参数对比 · 自动提取</span>
        <p className="mt-2 text-xs text-ink-soft">
          高度统一为 30，直径采用相同归一化单位。
        </p>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-ink/10 text-left text-ink-soft">
            <th className="px-6 py-3 font-medium">参数</th>
            <th className="px-6 py-3 font-medium">{leftLabel}</th>
            <th className="px-6 py-3 font-medium">{rightLabel}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label} className="border-b border-ink/5 last:border-0">
              <td className="px-6 py-3 text-ink-soft">{row.label}</td>
              <td className="px-6 py-3 font-display text-ink">{row.left}</td>
              <td className="px-6 py-3 font-display text-ink">{row.right}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function measuredPorcelain(
  porcelain: Porcelain,
  measurement: MorphologyMeasurement,
): Porcelain {
  return { ...porcelain, shape: measurement.shape, params: measurement }
}

export default function Comparison() {
  const { items: porcelains, error: catalogError } = useCatalog()
  const { user } = useAuth()
  const [params] = useSearchParams()
  const getPorcelainById = (id: string) => porcelains.find((x) => x.id === id)!
  const { current, clearCurrent } = usePorcelainModel()
  const personalized = !!current?.porcelain && !params.get('left')
  const [leftId, setLeftId] = useState(params.get('left') ?? '')
  const [rightId, setRightId] = useState(params.get('right') ?? '')
  useEffect(() => {
    if (porcelains.length) {
      if (!leftId) setLeftId(porcelains[0].id)
      if (!rightId) setRightId((porcelains[1] ?? porcelains[0]).id)
    }
  }, [porcelains])
  const [pair, setPair] = useState<ComparisonPair | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [retry, setRetry] = useState(0)
  const [explanation, setExplanation] = useState<AIQueryAnswer | null>(null),
    [explaining, setExplaining] = useState(false)
  const selectedLeft = personalized ? current.id : leftId
  const modelUrl = personalized ? current.modelUrl : null

  useEffect(() => {
    const controller = new AbortController()
    setPair(null)
    setError(null)
    setExplanation(null)
    if (!selectedLeft || !rightId) return () => controller.abort()
    if (personalized && !modelUrl) {
      setError('当前瓷器没有重建模型，请先在三维复原页面生成模型。')
      return () => controller.abort()
    }
    fetchComparisonPair(
      { leftId: selectedLeft, rightId, leftModelUrl: modelUrl ?? undefined },
      controller.signal,
    )
      .then((data) => {
        if (!controller.signal.aborted) {
          setPair(data)
          if (user) {
            track(selectedLeft, 'compare').catch(() => {})
            track(rightId, 'compare').catch(() => {})
          }
        }
      })
      .catch((reason) => {
        if (!controller.signal.aborted) {
          setError(
            reason instanceof TypeError
              ? '无法连接形态对比服务，请启动后端后重试。'
              : reason.message,
          )
        }
      })
    return () => controller.abort()
  }, [selectedLeft, rightId, modelUrl, personalized, retry])

  const activePair =
    pair?.leftId === selectedLeft && pair.rightId === rightId ? pair : null
  const leftMeasurement = activePair?.leftMeasurement
  const rightMeasurement = activePair?.rightMeasurement
  const left =
    leftMeasurement && (personalized || getPorcelainById(leftId))
      ? measuredPorcelain(
          personalized
            ? {
                ...current.porcelain!,
                id: current.id,
                name: current.name,
                period: '上传重建模型',
                modelUrl: current.previewUrl ?? modelUrl ?? undefined,
              }
            : getPorcelainById(leftId),
          leftMeasurement,
        )
      : null
  const right =
    rightMeasurement && getPorcelainById(rightId)
      ? measuredPorcelain(getPorcelainById(rightId), rightMeasurement)
      : null

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="font-display text-3xl font-semibold text-ink">
        跨时期形态对比
      </h1>
      <p className="mt-2 text-sm text-ink-soft">
        统一器物高度，比较口、腹、足的比例和最大腹径位置。
      </p>
      {personalized && (
        <div className="mt-6">
          <EvolutionModeSwitch
            label="我的瓷器 · 形态对比"
            backLabel="返回经典对比"
            onBack={clearCurrent}
          />
        </div>
      )}
      <div className="panel mt-8 grid gap-4 p-5 sm:grid-cols-2">
        <label className="flex flex-col gap-2 text-sm text-ink-soft">
          左侧器物
          {personalized ? (
            <span className="py-2 text-ink">{current.name}</span>
          ) : (
            <select
              aria-label="左侧器物"
              className="rounded border border-ink/20 bg-ivory p-2 text-ink"
              value={leftId}
              onChange={(event) => setLeftId(event.target.value)}
            >
              {porcelains.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.dynastyName} · {p.name}
                </option>
              ))}
            </select>
          )}
        </label>
        <label className="flex flex-col gap-2 text-sm text-ink-soft">
          右侧历史参考
          <select
            aria-label="右侧历史参考"
            className="rounded border border-ink/20 bg-ivory p-2 text-ink"
            value={rightId}
            onChange={(event) => setRightId(event.target.value)}
          >
            {porcelains.map((p) => (
              <option key={p.id} value={p.id}>
                {p.dynastyName} · {p.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error || catalogError ? (
        <div role="alert" className="panel mt-8 p-6 text-sm text-ink-soft">
          <p>{error || catalogError}</p>
          <button
            className="btn-ghost mt-4"
            type="button"
            onClick={() => setRetry((value) => value + 1)}
          >
            重试
          </button>
        </div>
      ) : activePair && left && right ? (
        <div className="mt-8 flex flex-col gap-8">
          <CompareViewer
            left={left}
            right={right}
            leftLabel={personalized ? '我的瓷器（上传）' : left.dynastyName}
            rightLabel={right.dynastyName}
          />
          <ParamsTable
            rows={activePair.rows}
            leftLabel={left.name}
            rightLabel={right.name}
          />
          {activePair.featureRows && (
            <ParamsTable
              rows={activePair.featureRows}
              leftLabel={left.name}
              rightLabel={right.name}
            />
          )}
          <Sources sources={activePair.sources} />
          <div className="panel p-6">
            <button
              className="btn-gold"
              disabled={explaining}
              onClick={async () => {
                setExplaining(true)
                try {
                  setExplanation(
                    await request('/compare/explain', {
                      method: 'POST',
                      body: JSON.stringify({
                        leftId: selectedLeft,
                        rightId,
                        leftModelUrl: modelUrl ?? undefined,
                      }),
                    }),
                  )
                } catch (e) {
                  setError((e as Error).message)
                } finally {
                  setExplaining(false)
                }
              }}
            >
              {explaining ? '正在检索资料…' : 'AI分析形态、纹饰与工艺差异'}
            </button>
            {explanation && (
              <>
                <p className="mt-4 whitespace-pre-line text-sm leading-7">
                  {explanation.answer}
                </p>
                <Sources sources={explanation.sources} />
              </>
            )}
          </div>
          <div className="border-l-2 border-gold/40 pl-4">
            <span className="eyebrow">差异洞察</span>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink-soft">
              {activePair.insight}
            </p>
            <p className="mt-3 text-xs text-ink-soft">
              左侧：{leftMeasurement?.method}；右侧：{rightMeasurement?.method}
              。 网格口径、足径取顶部和底部邻近 3% 高度的截面外径。
            </p>
          </div>
        </div>
      ) : (
        <div
          role="status"
          className="mt-8 flex h-64 items-center justify-center text-sm text-ink-soft"
        >
          正在提取形态参数…
        </div>
      )}
    </div>
  )
}
