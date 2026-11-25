import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { PorcelainViewer } from "../../components/PorcelainViewer";
import { UploadPanel } from "../../components/UploadPanel";
import type { ReconstructMode } from "../../components/UploadPanel";
import {
  asCurrent,
  PorcelainReconstructionService as service,
} from "../../services/PorcelainReconstructionService";
import { usePorcelainModel } from "../../stores/PorcelainModelManager";
import { useAuth } from "../../stores/Platform";
import { backendEndpoint, request } from "../../api/client";
import type { ModelInfo, ReconstructTask } from "../../types/porcelain";

interface ModelPreloadStatus {
  status: "idle" | "loading" | "ready" | "error";
  stage: string;
  progress: number;
  error?: string | null;
  device: string;
}

export default function Reconstruction() {
  const { user } = useAuth(),
    { current, setCurrent, clearCurrent } = usePorcelainModel();
  const [task, setTask] = useState<ReconstructTask | null>(null),
    [result, setResult] = useState<ModelInfo | null>(null),
    [error, setError] = useState(""),
    [heatmap, setHeatmap] = useState(false),
    [saved, setSaved] = useState(false),
    [confirmDelete, setConfirmDelete] = useState(false),
    [mode, setMode] = useState<ReconstructMode>("auto"),
    [hunyuanAvailable, setHunyuanAvailable] = useState(true),
    [preload, setPreload] = useState<ModelPreloadStatus | null>(null);
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function pollModelStatus() {
      try {
        const response = await fetch(backendEndpoint("/health"));
        const health = await response.json();
        const state = health.triposrModel as ModelPreloadStatus | undefined;
        const engines = health.singleImageEngines as
          | { name: string; available: boolean }[]
          | undefined;
        const hunyuan = engines?.find((item) => item.name === "hunyuan");
        if (!stopped && hunyuan) setHunyuanAvailable(hunyuan.available);
        if (!stopped && state) {
          setPreload(state);
          // idle 表示引擎还没加载或已被释放，上传后会按需加载，不必再轮询。
          if (
            state.status !== "ready" &&
            state.status !== "error" &&
            state.status !== "idle"
          )
            timer = setTimeout(pollModelStatus, 2000);
        }
      } catch {
        if (!stopped) timer = setTimeout(pollModelStatus, 3000);
      }
    }
    void pollModelStatus();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }, []);
  const loading = task?.status === "processing";
  // 只在"纯加载"阶段用不定进度条；图像分割、结构推理这些阶段照实给百分比。
  const preparingModel =
    !!loading &&
    /导入|读取本地权重|读取权重|构建网络|构建管线|预热|加载模型到/i.test(
      task?.stage ?? "",
    );
  async function watch(id: string) {
    const pending = "qjqn-pending:" + user?.id;
    try {
      while (active.current) {
        const status = await service.getTask(id);
        if (!active.current) return;
        setTask(status);
        if (status.status === "success") {
          const model = await service.getModel(id);
          if (!active.current) return;
          setResult(model);
          setCurrent(asCurrent(model));
          localStorage.removeItem(pending);
          break;
        }
        if (status.status !== "processing") {
          setError(status.error ?? "任务已取消");
          localStorage.removeItem(pending);
          break;
        }
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }
    } catch (e) {
      if (active.current) {
        setError((e as Error).message);
        setTask(null);
      }
    }
  }
  useEffect(() => {
    if (!user) return;
    const id = localStorage.getItem("qjqn-pending:" + user.id);
    if (id) {
      setTask({ taskId: id, status: "processing" });
      void watch(id);
    }
  }, [user?.id]);
  async function upload(file: File) {
    setError("");
    setResult(null);
    setSaved(false);
    try {
      const created = await service.reconstruct(file, mode);
      setTask(created);
      localStorage.setItem("qjqn-pending:" + user?.id, created.taskId);
      await watch(created.taskId);
    } catch (e) {
      setError((e as Error).message);
      setTask(null);
    }
  }
  async function remove() {
    if (!result) return;
    try {
      await service.deleteModel(result.porcelain.id);
      setResult(null);
      setTask(null);
      clearCurrent();
      setSaved(false);
      setConfirmDelete(false);
    } catch (e) {
      setError((e as Error).message);
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
          note: "",
        }
      : null);
  return (
    <div className="page-shell">
      <h1 className="font-display text-3xl">瓷器三维复原</h1>
      <p className="mt-2 text-sm text-ink-soft">
        上传瓷器照片，识别可见器型并生成可交互的三维模型。快速模式几秒出结果，先确认器型；
        精细模式重建结构更完整。想同时比较多个引擎，去{" "}
        <Link to="/engine-compare" className="text-gold underline">多引擎同图对比</Link>。
      </p>
      <p className="mt-1 text-xs text-ink-soft">
        能绕器物拍一圈的话，用{" "}
        <Link to="/multiview" className="text-gold underline">环绕建档</Link>{" "}
        拿真实几何（多点摄影测量，慢一些）。
      </p>
      {preload && (
        <div
          className={
            "mt-5 flex flex-wrap items-center justify-between gap-2 border px-4 py-3 text-sm " +
            (preload.status === "error"
              ? "border-red-300 bg-red-50 text-red-800"
              : preload.status === "ready"
                ? "border-emerald-300 bg-emerald-50 text-emerald-800"
                : "border-gold/30 bg-gold/5 text-ink-soft")
          }
        >
          <span>
            三维引擎：{preload.status === "idle" ? "待命，上传后自动加载" : preload.stage}
          </span>
          <span>
            {preload.status === "ready"
              ? `${preload.device.toUpperCase()} · 可立即重建`
              : preload.status === "error"
                ? (preload.error ?? "加载失败")
                : "网页可正常浏览，模型正在后台准备"}
          </span>
        </div>
      )}
      {!user ? (
        <div className="panel mt-8 p-5">
          <Link className="btn-gold w-full" to="/auth?next=/reconstruction">
            登录后上传并保存模型
          </Link>
        </div>
      ) : (
        <div className="mt-6 grid gap-5 sm:mt-8 sm:gap-8 lg:grid-cols-[340px_1fr]">
          <UploadPanel
            loading={!!loading}
            onReconstruct={upload}
            mode={mode}
            onModeChange={setMode}
            hunyuanAvailable={hunyuanAvailable}
          />
          <div className="panel relative h-[360px] overflow-hidden sm:h-[480px]">
            {loading ? (
              <div className="flex h-full flex-col items-center justify-center gap-4 p-4 sm:gap-5 sm:p-8">
                <span className="h-10 w-10 animate-spin rounded-full border-2 border-gold/30 border-t-gold" />
                <p role="status">{task?.stage ?? "等待处理"}</p>
                {mode === "hunyuan" && /结构推理/.test(task?.stage ?? "") && (
                  <p className="text-xs text-ink-soft">
                    扩散去噪中，通常 30–60 秒；这一步进度条不会动。
                  </p>
                )}
                <progress
                  aria-label="重建进度"
                  max={100}
                  value={preparingModel ? undefined : (task?.progress ?? 0)}
                  className="w-full accent-gold"
                />
                <span>
                  {preparingModel
                    ? "模型加载中，通常十几秒，首次会更久"
                    : `${task?.progress ?? 0}%`}
                </span>
                <button
                  className="btn-ghost"
                  onClick={() =>
                    request("/task/" + task?.taskId, {
                      method: "DELETE",
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
                  className="btn-ghost absolute right-2 top-2 !min-h-9 max-w-36 !px-2 !py-1.5 !text-[11px] sm:right-4 sm:top-4 sm:max-w-none sm:!px-3 sm:!text-xs"
                  onClick={() => setHeatmap(!heatmap)}
                >
                  {heatmap ? "显示纹理" : "显示可观测性热力图"}
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
        <div className="panel mt-6 space-y-4 p-4 sm:p-6">
          <h2 className="font-display text-xl">{result.porcelain.name}</h2>
          <p>识别器型：{result.recognition?.category}</p>
          <p className="text-sm text-ink-soft">
            {result.recognition?.features.join(" · ")}
          </p>
          <div className="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap">
            <button
              className="btn-gold"
              disabled={saved}
              onClick={async () => {
                try {
                  await request("/models/" + result.porcelain.id + "/save", {
                    method: "POST",
                  });
                  setSaved(true);
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
            >
              {saved ? "已保存" : "保存模型"}
            </button>
            <a
              href={result.modelUrl ?? ""}
              download={result.porcelain.id + ".glb"}
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
            {confirmDelete ? (
              <>
                <button
                  type="button"
                  className="btn-ghost border-red-600 text-red-700"
                  onClick={() => void remove()}
                >
                  确认删除
                </button>
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => setConfirmDelete(false)}
                >
                  取消
                </button>
              </>
            ) : (
              <button
                type="button"
                className="btn-ghost border-red-600 text-red-700"
                onClick={() => setConfirmDelete(true)}
              >
                删除
              </button>
            )}
          </div>
          {result.report && (
            <div className="grid gap-4 border-t border-ink/10 pt-4 text-sm sm:grid-cols-4">
              <p>顶点 {result.report.vertices.toLocaleString()}</p>
              <p>面数 {result.report.faces.toLocaleString()}</p>
              <p>水密：{result.report.watertight ? "是" : "否"}</p>
              <p>耗时 {(result.report.elapsedMs / 1000).toFixed(1)} 秒</p>
              <p className="sm:col-span-4 text-ink-soft">
                表面可观测性估计：可见{" "}
                {Math.round(result.report.observedRatio * 100)}% · 推断{" "}
                {Math.round(result.report.inferredRatio * 100)}%
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
