import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { PorcelainViewer } from "../../components/PorcelainViewer";
import {
  asCurrent,
  PorcelainReconstructionService as service,
} from "../../services/PorcelainReconstructionService";
import { usePorcelainModel } from "../../stores/PorcelainModelManager";
import { useAuth } from "../../stores/Platform";
import { request } from "../../api/client";
import type { ModelInfo, ReconstructTask } from "../../types/porcelain";

const MAX_IMAGES = 40;
const MAX_BYTES = 12 * 1024 * 1024;

interface Shot {
  file: File;
  url: string;
}

export default function Multiview() {
  const { user } = useAuth(),
    { setCurrent, clearCurrent } = usePorcelainModel();
  const [shots, setShots] = useState<Shot[]>([]),
    [dragging, setDragging] = useState(false),
    [task, setTask] = useState<ReconstructTask | null>(null),
    [result, setResult] = useState<ModelInfo | null>(null),
    [error, setError] = useState(""),
    [saved, setSaved] = useState(false),
    [confirmDelete, setConfirmDelete] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const active = useRef(true);
  // 卸载时按最新列表回收 object URL；单独用 ref 是为了不随每次增删触发回收。
  const shotsRef = useRef<Shot[]>([]);
  shotsRef.current = shots;
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      shotsRef.current.forEach((shot) => URL.revokeObjectURL(shot.url));
    };
  }, []);

  function addFiles(list: FileList | File[] | null) {
    if (!list) return;
    const incoming = Array.from(list).filter((file) =>
      file.type.startsWith("image/"),
    );
    if (!incoming.length) return;
    setError("");
    const oversize = incoming.find((file) => file.size > MAX_BYTES);
    if (oversize) {
      setError(`「${oversize.name}」超过 12MB，换一张小一点的`);
      return;
    }
    setShots((previous) => {
      const next = [...previous];
      for (const file of incoming) {
        if (next.length >= MAX_IMAGES) break;
        next.push({ file, url: URL.createObjectURL(file) });
      }
      return next;
    });
  }

  function removeAt(index: number) {
    const target = shots[index];
    if (target) URL.revokeObjectURL(target.url);
    setShots((previous) => previous.filter((_, i) => i !== index));
  }

  const loading = task?.status === "processing";

  async function watch(id: string) {
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
          break;
        }
        if (status.status !== "processing") {
          setError(status.error ?? "任务已取消");
          break;
        }
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }
    } catch (e) {
      if (active.current) {
        setError((e as Error).message);
        setTask(null);
      }
    }
  }

  async function submit() {
    setError("");
    setResult(null);
    setSaved(false);
    try {
      const created = await service.reconstructMultiview(
        shots.map((shot) => shot.file),
      );
      setTask(created);
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
      setConfirmDelete(false);
      clearCurrent();
      setSaved(false);
    } catch (e) {
      setError((e as Error).message);
      setConfirmDelete(false);
    }
  }

  return (
    <div className="page-shell">
      <h1 className="font-display text-3xl">环绕建档</h1>
      <p className="mt-2 text-sm leading-relaxed text-ink-soft">
        围着器物拍一圈，2–40 张照片，用摄影测量重建真实几何。适合能绕到器物四周拍的场景，
        比如教学标本或自藏器物；展柜里的文物隔着玻璃拍不了整圈，用{" "}
        <Link to="/reconstruction" className="text-gold underline">
          单图复原
        </Link>{" "}
        就行。
      </p>
      <p className="mt-1 text-xs text-ink-soft">
        这一档不走推断，几何全部来自实拍，代价是慢：20 张照片大约 8–10 分钟。
      </p>

      {!user ? (
        <div className="panel mt-8 p-5">
          <Link className="btn-gold w-full" to="/auth?next=/multiview">
            登录后建档并保存模型
          </Link>
        </div>
      ) : (
        <div className="mt-6 grid gap-5 sm:mt-8 sm:gap-8 lg:grid-cols-[340px_1fr]">
          <div className="panel flex flex-col gap-4 p-4 sm:p-6">
            <div>
              <span className="eyebrow">环绕照片</span>
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">
                沿一个方向匀速绕拍，每张之间转动约 15°，相邻照片重叠六成以上。
              </p>
            </div>

            <div
              role="button"
              tabIndex={0}
              onClick={() => inputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                addFiles(e.dataTransfer.files);
              }}
              className={
                "flex min-h-[130px] cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-3 text-center transition-colors " +
                (dragging
                  ? "border-gold bg-gold/5"
                  : "border-ink/25 hover:border-gold/60")
              }
            >
              <span className="text-2xl text-gold">＋</span>
              <span className="text-sm text-ink-soft">
                点这里选照片，或把一批照片拖进来
              </span>
              <span className="text-xs text-ink-soft/80">
                已选 {shots.length} / {MAX_IMAGES} 张
              </span>
            </div>
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              multiple
              hidden
              onChange={(e) => {
                addFiles(e.target.files);
                e.target.value = "";
              }}
            />

            {shots.length > 0 && (
              <div className="grid grid-cols-4 gap-2">
                {shots.map((shot, index) => (
                  <div key={shot.url} className="group relative">
                    <img
                      src={shot.url}
                      alt={`第 ${index + 1} 张`}
                      className="aspect-square w-full rounded object-cover"
                    />
                    <button
                      type="button"
                      aria-label={`移除第 ${index + 1} 张`}
                      disabled={loading}
                      onClick={() => removeAt(index)}
                      className="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-ink/70 text-xs text-white disabled:opacity-40"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}

            {error && (
              <p role="alert" className="text-xs leading-5 text-red-700">
                {error}
              </p>
            )}

            <button
              type="button"
              className="btn-gold disabled:cursor-not-allowed disabled:opacity-50"
              disabled={loading || shots.length < 2}
              onClick={() => void submit()}
            >
              {loading
                ? "正在建档…"
                : shots.length < 2
                  ? "至少需要 2 张照片"
                  : `开始环绕建档（${shots.length} 张）`}
            </button>
          </div>

          <div className="panel relative h-[360px] overflow-hidden sm:h-[480px]">
            {loading ? (
              <div className="flex h-full flex-col items-center justify-center gap-4 p-4 sm:gap-5 sm:p-8">
                <span className="h-10 w-10 animate-spin rounded-full border-2 border-gold/30 border-t-gold" />
                <p role="status">{task?.stage ?? "等待处理"}</p>
                {/相机配准|SfM/i.test(task?.stage ?? "") && (
                  <p className="text-xs text-ink-soft">
                    相机配准是最慢的一步，20 张照片通常要两三分钟。
                  </p>
                )}
                <progress
                  aria-label="建档进度"
                  max={100}
                  value={task?.progress ?? 0}
                  className="w-full accent-gold"
                />
                <span>{task?.progress ?? 0}%</span>
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
            ) : result ? (
              <PorcelainViewer
                modelUrl={result.previewUrl ?? result.modelUrl ?? undefined}
                showControls
              />
            ) : (
              <div className="flex h-full items-center justify-center px-6 text-center text-sm text-ink-soft">
                提交后，重建模型会在这里出现。
              </div>
            )}
          </div>
        </div>
      )}

      {result && (
        <div className="panel mt-6 space-y-4 p-4 sm:p-6">
          <h2 className="font-display text-xl">{result.porcelain.name}</h2>
          <p className="text-sm text-ink-soft">
            {result.note ?? "多视角摄影测量重建"}
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
              download={result.porcelain.id + "-full.glb"}
              className="btn-ghost"
            >
              下载完整GLB
            </a>
            <Link to="/comparison" className="btn-ghost">
              形态对比
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
            <div className="grid gap-4 border-t border-ink/10 pt-4 text-sm sm:grid-cols-3">
              {result.report.vertices != null && (
                <p>顶点 {result.report.vertices.toLocaleString()}</p>
              )}
              {result.report.faces != null && (
                <p>面数 {result.report.faces.toLocaleString()}</p>
              )}
              {result.report.elapsedMs != null && (
                <p>耗时 {(result.report.elapsedMs / 1000).toFixed(0)} 秒</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
