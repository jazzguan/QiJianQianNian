import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { request } from '../../api/client'
import { useAuth, useCatalog } from '../../stores/Platform'
import { usePorcelainModel } from '../../stores/PorcelainModelManager'
import { asCurrent } from '../../services/PorcelainReconstructionService'
import type { ModelInfo, Source } from '../../types/porcelain'
import ArtifactCard from '../../components/ArtifactCard'
import Sources from '../../components/Sources'
import CompareViewer from '../../components/CompareViewer'
interface Summary {
  exploredIds: string[]
  favorites: string[]
  attempts: {
    task_id: string
    correct: number
    feedback: string
    created: number
  }[]
  completedTasks: number
  totalTasks: number
  durationSeconds: number
  progress: number
}
interface Task {
  id: string
  type: string
  prompt: string
  artifactIds: string[]
  options: string[]
  inputType?: 'text'
}
interface Feedback {
  correct: boolean
  correctAnswer: string | string[]
  feedback: string
  sources: Source[]
}
type SavedModel = ModelInfo & {
  taskId: string
  status: string
  stage: string
  error?: string
  created: number
  saved: boolean
}
function Exercise({
  task,
  onComplete,
}: {
  task: Task
  onComplete: () => void
}) {
  const { items } = useCatalog(),
    [answer, setAnswer] = useState(''),
    [order, setOrder] = useState(task.artifactIds),
    [feedback, setFeedback] = useState<Feedback | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('')
  const objects = task.artifactIds
    .map((id) => items.find((x) => x.id === id))
    .filter((x): x is NonNullable<typeof x> => !!x)
  return (
    <div className="panel space-y-4 p-6">
      <span className="eyebrow">{task.type}任务</span>
      <h3 className="text-lg">{task.prompt}</h3>
      {task.type === '观察' && objects.length >= 2 ? (
        <CompareViewer left={objects[0]} right={objects[1]} />
      ) : (
        <div className="flex flex-wrap gap-4">
          {objects.map((x) => (
            <Link
              key={x.id}
              to={'/library/' + x.id}
              className="text-center text-sm text-blue"
            >
              <img
                src={x.imageUrl}
                alt={x.name}
                className="mb-2 h-24 w-24 object-contain"
              />
              {x.name}
            </Link>
          ))}
        </div>
      )}
      {task.type === '排序' ? (
        <ol className="space-y-2">
          {order.map((id, i) => (
            <li
              key={id}
              className="flex items-center gap-3 border border-ink/10 p-2"
            >
              <span className="min-w-0 flex-1">
                {i + 1}. {items.find((x) => x.id === id)?.name}
              </span>
              <button
                className="btn-ghost !p-1"
                disabled={i === 0 || busy}
                onClick={() =>
                  setOrder((prev) => {
                    const n = [...prev]
                    ;[n[i - 1], n[i]] = [n[i], n[i - 1]]
                    return n
                  })
                }
              >
                上移
              </button>
              <button
                className="btn-ghost !p-1"
                disabled={i === order.length - 1 || busy}
                onClick={() =>
                  setOrder((prev) => {
                    const n = [...prev]
                    ;[n[i], n[i + 1]] = [n[i + 1], n[i]]
                    return n
                  })
                }
              >
                下移
              </button>
            </li>
          ))}
        </ol>
      ) : task.inputType === 'text' ? (
        <label className="block text-sm">
          写下你的解释
          <textarea
            aria-label="解释答案"
            value={answer}
            maxLength={1600}
            onChange={(e) => setAnswer(e.target.value)}
            className="mt-2 min-h-28 w-full border border-ink/20 bg-ivory p-3"
            placeholder="根据馆藏资料，描述你理解的工艺与装饰方式。"
          />
        </label>
      ) : (
        <fieldset className="space-y-2">
          {task.options.map((option) => (
            <label
              className="flex cursor-pointer items-start gap-3 border border-ink/10 p-3 text-sm"
              key={option}
            >
              <input
                type="radio"
                name={task.id}
                value={option}
                checked={answer === option}
                onChange={() => {
                  setAnswer(option)
                  setFeedback(null)
                }}
              />
              {option}
            </label>
          ))}
        </fieldset>
      )}
      <button
        className="btn-gold"
        disabled={busy || (task.type !== '排序' && !answer)}
        onClick={async () => {
          setBusy(true)
          setError('')
          try {
            setFeedback(
              await request('/learning/attempts', {
                method: 'POST',
                body: JSON.stringify({
                  taskId: task.id,
                  answer: task.type === '排序' ? order : answer,
                }),
              }),
            )
            onComplete()
          } catch (e) {
            setError((e as Error).message)
          } finally {
            setBusy(false)
          }
        }}
      >
        {busy ? '提交中…' : '提交答案'}
      </button>
      {feedback && (
        <div role="status" className="border-l-2 border-gold p-3">
          <strong>{feedback.correct ? '回答正确' : '再观察一下'}</strong>
          <p className="mt-2 text-sm">{feedback.feedback}</p>
          <Sources sources={feedback.sources} />
        </div>
      )}
      {error && <p role="alert">{error}</p>}
    </div>
  )
}
export default function Learning() {
  const { user, ready } = useAuth(),
    { items } = useCatalog(),
    { setCurrent } = usePorcelainModel(),
    [params] = useSearchParams()
  const [summary, setSummary] = useState<Summary | null>(null),
    [tasks, setTasks] = useState<Task[]>([]),
    [models, setModels] = useState<SavedModel[]>([]),
    [error, setError] = useState(''),
    [type, setType] = useState(''),
    [selected, setSelected] = useState(''),
    [message, setMessage] = useState('')
  const refresh = useCallback(() => {
    if (!user) return
    request<Summary>('/learning')
      .then(setSummary)
      .catch((e) => setError(e.message))
    request<{ items: SavedModel[] }>('/models')
      .then((r) => setModels(r.items))
      .catch((e) => setError(e.message))
  }, [user?.id])
  useEffect(() => {
    refresh()
    request<{ items: Task[] }>('/learning/tasks')
      .then((r) => setTasks(r.items))
      .catch((e) => setError(e.message))
  }, [refresh])
  const filtered = tasks.filter(
    (t) =>
      (!type || t.type === type) &&
      (!params.get('artifact') ||
        t.artifactIds.includes(params.get('artifact')!)),
  )
  const active = filtered.find((t) => t.id === selected) ?? filtered[0]
  if (!ready) return <p className="p-12">加载账号…</p>
  if (!user)
    return (
      <div className="mx-auto max-w-6xl px-6 py-16">
        <h1 className="font-display text-3xl">学习中心</h1>
        <p className="mt-4 text-ink-soft">
          登录后保存探索记录、收藏文物和学习成绩。
        </p>
        <Link to="/auth?next=/learning" className="btn-gold mt-6">
          登录 / 注册
        </Link>
      </div>
    )
  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="font-display text-3xl">{user.username}的学习中心</h1>
      {error && (
        <p role="alert" className="mt-6">
          {error}
          <button className="btn-ghost ml-3" onClick={refresh}>
            重试
          </button>
        </p>
      )}
      {summary && (
        <>
          <div className="mt-8 grid gap-4 sm:grid-cols-4">
            {[
              ['探索文物', summary.exploredIds.length + ' 件'],
              [
                '已完成任务',
                summary.completedTasks + ' / ' + summary.totalTasks,
              ],
              ['学习时长', Math.floor(summary.durationSeconds / 60) + ' 分钟'],
              ['学习进度', summary.progress + '%'],
            ].map(([label, value]) => (
              <div className="panel p-5" key={label}>
                <p className="text-sm text-ink-soft">{label}</p>
                <p className="mt-3 font-display text-2xl">{value}</p>
              </div>
            ))}
          </div>
          <progress
            aria-label="学习进度"
            value={summary.progress}
            max={100}
            className="mt-4 h-2 w-full accent-gold"
          />
        </>
      )}
      <h2 className="mt-10 font-display text-2xl">互动学习</h2>
      <div className="my-5 flex flex-wrap gap-3">
        <select
          aria-label="任务类型"
          className="border border-ink/20 bg-paper p-2"
          value={type}
          onChange={(e) => {
            setType(e.target.value)
            setSelected('')
          }}
        >
          <option value="">全部任务</option>
          {[...new Set(tasks.map((t) => t.type))].map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <select
          aria-label="选择任务"
          className="max-w-full border border-ink/20 bg-paper p-2"
          value={active?.id ?? ''}
          onChange={(e) => setSelected(e.target.value)}
        >
          {filtered.map((t) => (
            <option key={t.id} value={t.id}>
              {t.prompt}
            </option>
          ))}
        </select>
      </div>
      {active && (
        <Exercise key={active.id} task={active} onComplete={refresh} />
      )}
      <h2 className="mt-10 font-display text-2xl">我的模型</h2>
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        {models.map((m) => (
          <div className="panel p-5" key={m.taskId}>
            <p>
              {m.porcelain?.name ?? '重建任务'} ·{' '}
              {m.status === 'success' ? '完成' : m.stage}
            </p>
            <p className="mt-1 text-xs text-ink-soft">
              {new Date(m.created * 1000).toLocaleString()}
            </p>
            {m.error && <p className="mt-2 text-sm">{m.error}</p>}
            {m.status === 'success' && (
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  className="btn-ghost"
                  onClick={() => {
                    setCurrent(asCurrent(m))
                    setMessage('已设为当前器物，可进入讲解和对比。')
                  }}
                >
                  恢复模型
                </button>
                <button
                  className="btn-ghost"
                  onClick={async () => {
                    try {
                      await request('/models/' + m.taskId + '/save', {
                        method: m.saved ? 'DELETE' : 'POST',
                      })
                      refresh()
                    } catch (e) {
                      setError((e as Error).message)
                    }
                  }}
                >
                  {m.saved ? '取消保存' : '保存模型'}
                </button>
                <a
                  href={m.modelUrl ?? ''}
                  download={m.taskId + '.glb'}
                  className="btn-ghost"
                >
                  下载GLB
                </a>
              </div>
            )}
            {m.status === 'processing' && (
              <Link to="/reconstruction" className="text-blue">
                查看进度
              </Link>
            )}
          </div>
        ))}
      </div>
      {!models.length && (
        <p className="mt-4 text-sm text-ink-soft">还没有重建模型。</p>
      )}
      {message && <p className="mt-3 text-sm">{message}</p>}
      <h2 className="mt-10 font-display text-2xl">收藏文物</h2>
      <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {items
          .filter((x) => summary?.favorites.includes(x.id))
          .map((x) => (
            <ArtifactCard key={x.id} item={x} />
          ))}
      </div>
      <h2 className="mt-10 font-display text-2xl">最近学习记录</h2>
      <div className="mt-5 space-y-2">
        {summary?.attempts.map((a, i) => (
          <div key={i} className="panel p-4 text-sm">
            <span className="text-gold">{a.correct ? '答对' : '练习'} · </span>
            {tasks.find((t) => t.id === a.task_id)?.prompt}
            <p className="mt-2 text-ink-soft">{a.feedback}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
