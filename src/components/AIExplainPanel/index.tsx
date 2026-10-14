import { useEffect, useState } from 'react'
import {
  askQuestion,
  fetchPartExplanation,
  fetchSuggestions,
} from '../../api/ai'
import { track, useAuth } from '../../stores/Platform'
import Sources from '../Sources'
import type {
  AIAnswer,
  AIQueryAnswer,
  AIQuerySuggestion,
  Porcelain,
} from '../../types/porcelain'
interface Props {
  porcelain: Porcelain
  selectedPartId: string
  onSelectPart: (id: string) => void
  personalized?: boolean
}
export function AIExplainPanel({
  porcelain,
  selectedPartId,
  onSelectPart,
}: Props) {
  const { user } = useAuth(),
    [answer, setAnswer] = useState<AIAnswer | null>(null),
    [qa, setQa] = useState<AIQueryAnswer[]>([]),
    [suggestions, setSuggestions] = useState<AIQuerySuggestion[]>([]),
    [question, setQuestion] = useState(''),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [retry, setRetry] = useState(0)
  useEffect(() => {
    fetchSuggestions()
      .then(setSuggestions)
      .catch((e) => setError(e.message))
  }, [])
  useEffect(() => {
    setQa([])
    setQuestion('')
  }, [porcelain.id])
  useEffect(() => {
    const controller = new AbortController()
    setBusy(true)
    setAnswer(null)
    setError('')
    fetchPartExplanation(porcelain, selectedPartId, controller.signal)
      .then((a) => {
        if (!controller.signal.aborted) setAnswer(a)
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false)
      })
    return () => controller.abort()
  }, [porcelain.id, selectedPartId, retry])
  async function ask(q: string) {
    if (!q.trim() || busy) return
    setBusy(true)
    setError('')
    try {
      const result = await askQuestion(q, porcelain)
      setQa((prev) => [...prev, result])
      setQuestion('')
      if (user) track(porcelain.id, 'ask').catch(() => {})
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="space-y-5">
      <div className="panel space-y-4 p-5">
        <h2 className="font-display text-xl">{porcelain.name}</h2>
        <p className="text-sm leading-7 text-ink-soft">
          {porcelain.description}
        </p>
        <div className="flex flex-wrap gap-2">
          {porcelain.parts.map((p) => (
            <button
              type="button"
              key={p.id}
              onClick={() => onSelectPart(p.id)}
              className={
                'border px-3 py-2 text-sm ' +
                (selectedPartId === p.id
                  ? 'border-gold bg-gold text-paper'
                  : 'border-ink/20')
              }
            >
              {p.name}
            </button>
          ))}
        </div>
        <h3 className="text-gold">
          {porcelain.parts.find((p) => p.id === selectedPartId)?.name}讲解
        </h3>
        {busy && !answer ? (
          <p role="status" className="text-sm">
            正在检索馆藏资料并生成讲解…
          </p>
        ) : (
          <>
            <p className="whitespace-pre-line text-sm leading-7">
              {answer?.formDescription}
            </p>
            <Sources sources={answer?.sources} />
          </>
        )}
        {error && (
          <div role="alert" className="text-sm">
            <p>{error}</p>
            <button
              onClick={() => setRetry((x) => x + 1)}
              className="btn-ghost mt-3"
              disabled={busy}
            >
              重试讲解
            </button>
          </div>
        )}
      </div>
      <form
        className="panel space-y-3 p-5"
        onSubmit={(e) => {
          e.preventDefault()
          void ask(question)
        }}
      >
        <label htmlFor="artifact-question" className="eyebrow">
          向器物提问
        </label>
        <textarea
          id="artifact-question"
          value={question}
          maxLength={1600}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="输入关于器型、纹饰或工艺的问题"
          className="min-h-24 w-full border border-ink/20 bg-ivory p-3 text-sm"
          required
        />
        <button className="btn-gold" disabled={busy || !question.trim()}>
          {busy ? '生成中…' : '提问'}
        </button>
      </form>
      <div className="space-y-2">
        {suggestions.map((s) => (
          <button
            key={s.id}
            disabled={busy}
            className="block text-left text-sm text-blue disabled:opacity-50"
            onClick={() => ask(s.question)}
          >
            {s.question}
          </button>
        ))}
      </div>
      {qa.map((item, i) => (
        <div key={i} className="panel p-5">
          <h3 className="font-medium">{item.question}</h3>
          <p className="mt-3 whitespace-pre-line text-sm leading-7">
            {item.answer}
          </p>
          <Sources sources={item.sources} />
        </div>
      ))}
    </div>
  )
}
export default AIExplainPanel
