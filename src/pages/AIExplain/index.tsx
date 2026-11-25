import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PorcelainViewer } from "../../components/PorcelainViewer";
import { AIExplainPanel } from "../../components/AIExplainPanel";
import { useCatalog } from "../../stores/Platform";
import { usePorcelainModel } from "../../stores/PorcelainModelManager";
export default function AIExplain() {
  const { current, clearCurrent } = usePorcelainModel(),
    { items, error, loading } = useCatalog(),
    [params] = useSearchParams();
  const [selectedId, setSelectedId] = useState(params.get("artifact") ?? ""),
    [part, setPart] = useState("body");
  const artifactParam = params.get("artifact");
  // 从别的页面点不同器物进来时 URL 变了但组件已挂载，要跟着换，不能沿用旧选择。
  useEffect(() => {
    setSelectedId(artifactParam ?? "");
    setPart("body");
  }, [artifactParam]);
  const uploaded = !params.get("artifact") && !!current?.porcelain;
  const porcelain = uploaded
    ? current!.porcelain!
    : (items.find((x) => x.id === selectedId) ?? items[0]);
  return (
    <div className="page-shell">
      <h1 className="font-display text-3xl">AI瓷器讲解</h1>
      <p className="mt-2 text-sm text-ink-soft">
        点击三维器物部位，结合馆藏资料提问并查看来源。
      </p>
      {uploaded ? (
        <div className="mt-6 flex flex-wrap items-center gap-3 sm:gap-4">
          <p>{current?.name}</p>
          <button className="btn-ghost" onClick={clearCurrent}>
            浏览馆藏讲解
          </button>
        </div>
      ) : (
        <select
          aria-label="讲解器物"
          className="field mt-6 sm:w-auto sm:max-w-full"
          value={porcelain?.id ?? ""}
          onChange={(e) => {
            setSelectedId(e.target.value);
            setPart("body");
          }}
        >
          {items.map((x) => (
            <option key={x.id} value={x.id}>
              {x.dynastyName} · {x.name}
            </option>
          ))}
        </select>
      )}
      {!porcelain ? (
        <p className="mt-10">
          {error || (loading ? "加载馆藏…" : "馆藏数据为空")}
        </p>
      ) : (
        <div className="mt-6 grid gap-5 sm:mt-8 sm:gap-8 lg:grid-cols-[1fr_400px]">
          <div>
            <div className="panel h-[360px] overflow-hidden sm:h-[440px] lg:h-[520px]">
              <PorcelainViewer
                photoTexture={!!porcelain.textureProjection}
                modelUrl={
                  uploaded
                    ? (current?.previewUrl ?? current?.modelUrl ?? undefined)
                    : porcelain.modelUrl
                }
                shape={porcelain.shape}
                glaze={porcelain.glaze}
                parts={porcelain.parts}
                selectedPartId={part}
                onPartSelect={setPart}
                showControls
              />
            </div>
            <p className="mt-3 text-xs text-ink-soft">
              拖动旋转 · 滚轮缩放 · 右键平移 · 双击聚焦
            </p>
            <img
              src={porcelain.imageUrl}
              alt={porcelain.name}
              className="mt-4 h-32 w-full object-contain sm:mt-5 sm:h-40"
            />
          </div>
          <AIExplainPanel
            key={porcelain.id}
            porcelain={porcelain}
            selectedPartId={part}
            onSelectPart={setPart}
          />
        </div>
      )}
    </div>
  );
}
