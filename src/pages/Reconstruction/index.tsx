import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { PorcelainViewer } from '../../components/PorcelainViewer'
import { UploadPanel } from '../../components/UploadPanel'
import {
  asCurrent,
  PorcelainReconstructionService as service,
} from '../../services/PorcelainReconstructionService'
import { usePorcelainModel } from '../../stores/PorcelainModelManager'
import { useAuth } from '../../stores/Platform'
import { request } from '../../api/client'
import type { ModelInfo, ReconstructTask } from '../../types/porcelain'
export default function Reconstruction() {
  const { user } = useAuth(),
    { current, setCurrent } = usePorcelainModel()
  const [task, setTask] = useState<ReconstructTask | null>(null),
    [result, setResult] = useState<ModelInfo | null>(null),
    [error, setError] = useState(''),
    [heatmap, setHeatmap] = useState(false),
    [saved, setSaved] = useState(false)
  const active = useRef(true)
  useEffect(() => {
    active.current = true
    return () => {
      active.current = false
    }
  }, [])
  const loading = task?.status === 'processing'
  async function watch(id: string) {
    const pending = 'qjqn-pending:' + user?.id
    try {
      while (active.current) {
        const status = await service.getTask(id)
        if (!active.current) return
        setTask(status)
        if (status.status === 'success') {
          const model = await service.getModel(id)
          if (!active.current) return
          setResult(model)
          setCurrent(asCurrent(model))
          localStorage.removeItem(pending)
          break
        }
        if (status.status !== 'processing') {
          setError(status.error ?? '任务已取消')
          localStorage.removeItem(pending)
          break
        }
        await new Promise((resolve) => setTimeout(resolve, 1500))
      }
    } catch (e) {
      if (active.current) {
        setError((e as Error).message)
        setTask(null)
      }
    }
  }
  useEffect(() => {
    if (!user) return
    const id = localStorage.getItem('qjqn-pending:' + user.id)
    if (id) {
      setTask({ taskId: id, status: 'processing' })
      void watch(id)
    }
  }, [user?.id])
  async function upload(file: File) {
    setError('')
    setResult(null)
    setSaved(false)
    try {
      const created = await service.reconstruct(file)
      setTask(created)
      localStorage.setItem('qjqn-pending:' + user?.id, created.taskId)
      await watch(created.taskId)
    } catch (e) {
      setError((e as Error).message)
      setTask(null)
    }
  }
  const shown =
    result ??
    (current?.porcelain
      ? {
          porcelain: current.porcelain,
          modelUrl: current.modelUrl,
          heatmapUrl: current.heatmapUrl,
          report: current.report,
          note: '',
        }
      : null)
  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="font-display text-3xl">瓷器三维复原</h1>
      <p className="mt-2 text-sm text-ink-soft">
        上传瓷器照片，识别可见器型并生成可交互的三维模型。
      </p>
      {!user ? (
        <div className="panel mt-8 p-6">
          <Link className="btn-gold" to="/auth?next=/reconstruction">
            登录后上传并保存模型
          </Link>
        </div>
      ) : (
        <div className="mt-8 grid gap-8 lg:grid-cols-[340px_1fr]">
          <UploadPanel loading={!!loading} onReconstruct={upload} />
          <div className="panel relative h-[480px]">
            {loading ? (
              <div className="flex h-full flex-col items-center justify-center gap-5 p-8">
                <span className="h-10 w-10 animate-spin rounded-full border-2 border-gold/30 border-t-gold" />
                <p role="status">{task?.stage ?? '等待处理'}</p>
                <progress
                  aria-label="重建进度"
                  max={100}
                  value={task?.progress ?? 0}
                  className="w-full accent-gold"
                />
                <span>{task?.progress ?? 0}%</span>
                <button
                  className="btn-ghost"
                  onClick={() =>
                    request('/task/' + task?.taskId, {
                      method: 'DELETE',
                    }).catch((e) => setError(e.message))
                  }
                >
                  取消任务
                </button>
              </div>
            ) : shown ? (
              <>
                <PorcelainViewer
                  photoTexture={!!shown.porcelain.textureProjection}
                  modelUrl={result?.previewUrl ?? shown.modelUrl ?? undefined}
                  heatmapUrl={shown.heatmapUrl ?? undefined}
                  showHeatmap={heatmap}
                  shape={shown.porcelain.shape}
                  glaze={shown.porcelain.glaze}
                  parts={shown.porcelain.parts}
                  showControls
                />
                <button
                  className="btn-ghost absolute right-4 top-4"
                  onClick={() => setHeatmap(!heatmap)}
                >
                  {heatmap ? '显示纹理' : '显示可观测性热力图'}
                </button>
              </>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-ink-soft">
                上传照片后，三维模型将在此显示。
              </div>
            )}
          </div>
        </div>
      )}
      {error && (
        <p role="alert" className="panel mt-5 p-5 text-red-700">
          {error}
        </p>
      )}
      {result && (
        <div className="panel mt-6 space-y-4 p-6">
          <h2 className="font-display text-xl">{result.porcelain.name}</h2>
          <p>识别器型：{result.recognition?.category}</p>
          <p className="text-sm text-ink-soft">
            {result.recognition?.features.join(' · ')}
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              className="btn-gold"
              disabled={saved}
              onClick={async () => {
                try {
                  await request('/models/' + result.porcelain.id + '/save', {
                    method: 'POST',
                  })
                  setSaved(true)
                } catch (e) {
                  setError((e as Error).message)
                }
              }}
            >
              {saved ? '已保存' : '保存模型'}
            </button>
            <a
              href={result.modelUrl ?? ''}
              download={result.porcelain.id + '.glb'}
              className="btn-ghost"
            >
              下载完整GLB
            </a>
            <Link to="/timeline" className="btn-ghost">
              寻找历史器型
            </Link>
            <Link to="/ai-explain" className="btn-ghost">
              AI讲解
            </Link>
          </div>
          {result.report && (
            <div className="grid gap-4 border-t border-ink/10 pt-4 text-sm sm:grid-cols-4">
              <p>顶点 {result.report.vertices.toLocaleString()}</p>
              <p>面数 {result.report.faces.toLocaleString()}</p>
              <p>水密：{result.report.watertight ? '是' : '否'}</p>
              <p>耗时 {(result.report.elapsedMs / 1000).toFixed(1)} 秒</p>
              <p className="sm:col-span-4 text-ink-soft">
                表面可观测性估计：可见{' '}
                {Math.round(result.report.observedRatio * 100)}% · 推断{' '}
                {Math.round(result.report.inferredRatio * 100)}%
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
