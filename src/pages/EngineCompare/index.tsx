import { useEffect, useRef, useState } from "react"
import { Link } from "react-router-dom"
import { ModelCompareViewer } from "../../components/ModelCompareViewer"
import { backendEndpoint } from "../../api/client"
import { useAuth } from "../../stores/Platform"
import {
  ENGINE_LABELS,
  EngineCompareService,
} from "../../services/EngineCompareService"
import type {
  EngineName,
  EngineCompareJob,
  EngineResult,
} from "../../services/EngineCompareService"

// 可勾选的引擎；instantmesh 需要 HF token，默认不勾。
const CHOICES: { name: EngineName; hint: string }[] = [
  { name: "triposr", hint: "本地快速，面数少" },
  { name: "hunyuan", hint: "本地精细，几何水密" },
  { name: "instantmesh", hint: "云端，需 HF token" },
]

function formatBytes(bytes?: number): string {
  if (!bytes) return "-"
  return (bytes / 1024 / 1024).toFixed(2) + " MB"
}

function ResultCard({ result }: { result: EngineResult }) {
  return (
    <div className="panel flex flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-ink/10 px-5 py-3">
        <h3 className="font-display text-base text-ink">
          {ENGINE_LABELS[result.engine]}
        </h3>
        <span className="text-xs text-ink-soft">
          {result.status === "success"
            ? `${result.elapsedMs ? (result.elapsedMs / 1000).toFixed(1) : "-"} 秒`
            : result.status}
        </span>
      </div>
      {result.status === "success" && result.meshUrl ? (
        <>
          <div className="h-[300px] bg-ivory/40 sm:h-[360px]">
            <ModelCompareViewer url={result.meshUrl} />
          </div>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 border-t border-ink/10 px-5 py-4 text-xs sm:grid-cols-3">
            <div>
              <dt className="text-ink-soft">顶点</dt>
              <dd>{result.vertices?.toLocaleString()}</dd>
            </div>
            <div>
              <dt className="text-ink-soft">面数</dt>
              <dd>{result.faces?.toLocaleString()}</dd>
            </div>
            <div>
              <dt className="text-ink-soft">几何水密</dt>
              <dd>{result.geometricWatertight ? "是" : "否"}</dd>
            </div>
            <div>
              <dt className="text-ink-soft">欧拉数</dt>
              <dd>{result.euler}</dd>
            </div>
            <div>
              <dt className="text-ink-soft">GLB 大小</dt>
              <dd>{formatBytes(result.glbSizeBytes)}</dd>
            </div>
          </dl>
        </>
      ) : (
        <div className="flex h-40 items-center justify-center px-5 text-sm text-red-700">
          {result.error ?? "未生成"}
        </div>
      )}
    </div>
  )
}

export default function EngineCompare() {
  const { user } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [picked, setPicked] = useState<EngineName[]>(["triposr", "hunyuan"])
  const [ready, setReady] = useState<Record<string, boolean>>({})
  const [job, setJob] = useState<EngineCompareJob | null>(null)
  const [error, setError] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)
  const activeRef = useRef(true)

  useEffect(() => {
    activeRef.current = true
    return () => {
      activeRef.current = false
    }
  }, [])

  // 预览图地址单独回收：之前和 activeRef 写在同一个 effect 里，
  // 换一张图就会把 activeRef 置 false，正在跑的对比轮询被中断。
  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview)
    },
    [preview],
  )

  // 从后端取真实可用性，别让用户勾了跑不通的引擎。
  useEffect(() => {
    fetch(backendEndpoint("/health"))
      .then((response) => response.json())
      .then((health) => {
        const state: Record<string, boolean> = {
          triposr: !!health.triposrInstalled,
          hunyuan: !!health.hunyuanInstalled,
          instantmesh: !!health.instantmeshInstalled,
        }
        setReady(state)
        setPicked((prev) => prev.filter((name) => state[name] !== false))
      })
      .catch(() => {
        // 拿不到状态就保持默认，提交后后端会给出明确原因。
      })
  }, [])

  function chooseFile(f?: File) {
    if (!f || !f.type.startsWith("image/")) return
    if (preview) URL.revokeObjectURL(preview)
    setFile(f)
    setPreview(URL.createObjectURL(f))
  }

  function toggle(name: EngineName) {
    setPicked((prev) =>
      prev.includes(name) ? prev.filter((x) => x !== name) : [...prev, name],
    )
  }

  async function watch(compareId: string) {
    while (activeRef.current) {
      const current = await EngineCompareService.get(compareId)
      if (!activeRef.current) return
      setJob(current)
      if (["success", "partial", "error"].includes(current.status)) break
      await new Promise((resolve) => setTimeout(resolve, 2000))
    }
  }

  async function start() {
    if (!file) return
    setError("")
    setJob(null)
    try {
      const created = await EngineCompareService.create(file, picked)
      setJob(created)
      await watch(created.compareId)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const running = job?.status === "processing"

  return (
    <div className="page-shell">
      <h1 className="font-display text-3xl">多引擎同图对比</h1>
      <p className="mt-2 text-sm text-ink-soft">
        同一张照片分别用不同引擎生成，统一朝向和尺度，直接比较几何细节与工程表现。
      </p>
      <p className="mt-1 text-xs text-ink-soft">
        这里只导出灰模，为的是排除贴图干扰、只看几何；带照片纹理的成品在{" "}
        <Link to="/reconstruction" className="text-gold underline">
          三维复原
        </Link>
        。
      </p>

      {!user ? (
        <div className="panel mt-8 p-5">
          <Link className="btn-gold w-full" to="/auth?next=/engine-compare">
            登录后开始对比
          </Link>
        </div>
      ) : (
        <div className="mt-6 grid gap-5 sm:mt-8 lg:grid-cols-[340px_1fr] lg:gap-8">
          <div className="panel flex flex-col gap-4 p-4 sm:p-6">
            <div
              role="button"
              tabIndex={0}
              onClick={() => inputRef.current?.click()}
              className="flex min-h-[170px] cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-ink/25 p-3 text-center transition-colors hover:border-gold/60"
            >
              {preview ? (
                <img
                  src={preview}
                  alt="预览"
                  className="max-h-44 max-w-full object-contain"
                />
              ) : (
                <span className="text-sm text-ink-soft">
                  点击选择瓷器照片
                </span>
              )}
            </div>
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              hidden
              onChange={(e) => {
                chooseFile(e.target.files?.[0])
                e.target.value = ""
              }}
            />

            <div className="space-y-2">
              <span className="eyebrow">选择引擎</span>
              {CHOICES.map((choice) => {
                const disabled = ready[choice.name] === false
                return (
                  <label
                    key={choice.name}
                    className={
                      "flex items-center justify-between gap-3 rounded-md border border-ink/10 px-3 py-2.5 text-sm transition-colors " +
                      (disabled
                        ? "cursor-not-allowed opacity-50"
                        : "cursor-pointer hover:border-gold/40")
                    }
                  >
                    <span className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        disabled={disabled}
                        checked={picked.includes(choice.name)}
                        onChange={() => toggle(choice.name)}
                      />
                      {ENGINE_LABELS[choice.name]}
                    </span>
                    <span className="text-xs text-ink-soft">
                      {disabled ? "当前不可用" : choice.hint}
                    </span>
                  </label>
                )
              })}
            </div>

            <button
              type="button"
              className="btn-gold disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!file || running || picked.length === 0}
              onClick={() => void start()}
            >
              {running ? "对比进行中…" : "开始对比"}
            </button>
          </div>

          <div className="space-y-4">
            {error && (
              <p role="alert" className="panel p-5 text-red-700">
                {error}
              </p>
            )}
            {!job && !error && (
              <div className="panel flex h-40 items-center justify-center text-sm text-ink-soft">
                选择图片和引擎后，结果将在此显示。
              </div>
            )}
            {job && (
              <>
                {running && (
                  <div className="panel flex items-center gap-3 p-4 text-sm">
                    <span className="h-5 w-5 animate-spin rounded-full border-2 border-gold/30 border-t-gold" />
                    {Object.values(job.results ?? {}).map((r) => (
                      <span key={r.engine} className="text-ink-soft">
                        {ENGINE_LABELS[r.engine]}：{r.status}
                      </span>
                    ))}
                  </div>
                )}
                <div className="grid gap-5 xl:grid-cols-2">
                  {job.engines.map((name) => (
                    <ResultCard
                      key={name}
                      result={job.results?.[name] ?? { engine: name, status: "pending" }}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
