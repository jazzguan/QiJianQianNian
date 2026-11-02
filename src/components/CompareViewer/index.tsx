import { useRef, useState } from "react";
import type { ReactNode } from "react";
import { PorcelainViewer } from "../PorcelainViewer";
import type { SyncState } from "../PorcelainViewer";
import type { Porcelain } from "../../types/porcelain";

interface CompareViewerProps {
  left: Porcelain;
  right: Porcelain;
  leftLabel?: string;
  rightLabel?: string;
}

function ViewerCard({
  porcelain,
  label,
  children,
}: {
  porcelain: Porcelain;
  label?: string;
  children: ReactNode;
}) {
  return (
    <div className="panel flex flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-ink/10 px-5 py-3">
        <div>
          <span className="eyebrow">{label ?? porcelain.dynastyName}</span>
          <h3 className="mt-0.5 font-display text-base text-ink">
            {porcelain.name}
          </h3>
        </div>
        <span className="text-xs text-ink-soft">{porcelain.period}</span>
      </div>
      <div className="h-[380px] bg-ivory/40">{children}</div>
    </div>
  );
}

export function CompareViewer({
  left,
  right,
  leftLabel,
  rightLabel,
}: CompareViewerProps) {
  const [sync, setSync] = useState(true);
  const [resetToken, setResetToken] = useState(0);
  const [selectedPart, setSelectedPart] = useState("");
  const syncRef = useRef<SyncState | null>(null);
  const partDefinitions: [string, string, number, number][] = [
    ["mouth", "器口", 0.92, 1],
    ["neck", "器颈", 0.78, 0.92],
    ["shoulder", "肩部", 0.62, 0.78],
    ["body", "腹部", 0.12, 0.62],
    ["foot", "器足", 0, 0.12],
  ];
  const withParts = (item: Porcelain): Porcelain => ({
    ...item,
    parts: partDefinitions.map(
      ([id, name, lo, hi]) =>
        item.parts.find((p) => p.id === id) ?? {
          id,
          name,
          yMin: lo * 30,
          yMax: hi * 30,
          formDescription: "",
          history: "",
          knowledge: "",
        },
    ),
  });
  left = withParts(left);
  right = withParts(right);
  const framingRadius = Math.max(
    ...left.shape.map((p) => p[0]),
    ...right.shape.map((p) => p[0]),
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-ink-soft">
          拖动任一模型即可旋转 / 缩放，
          {sync ? "当前为同步交互" : "当前为单独交互"}。
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            className="btn-ghost !px-3 !py-1.5 !text-xs"
            onClick={() => {
              syncRef.current = null;
              setSync((v) => !v);
              setResetToken((v) => v + 1);
            }}
          >
            {sync ? "同步旋转：开" : "同步旋转：关"}
          </button>
          <button
            type="button"
            className="btn-ghost !px-3 !py-1.5 !text-xs"
            onClick={() => {
              syncRef.current = null;
              setSelectedPart("");
              setResetToken((v) => v + 1);
            }}
          >
            重置视角
          </button>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {left.parts.map((p) => (
          <button
            key={p.id}
            className={
              "btn-ghost !px-3 !py-1 " +
              (selectedPart === p.id ? "!border-gold !text-gold" : "")
            }
            onClick={() => setSelectedPart(p.id)}
          >
            对齐观察{p.name}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ViewerCard porcelain={left} label={leftLabel}>
          <PorcelainViewer
            key={`left-${left.id}-${left.modelUrl ?? ""}`}
            modelUrl={left.modelUrl}
            photoTexture={left.textureProjection?.coverage === "symmetric-full"}
            framingRadius={framingRadius}
            shape={left.shape}
            glaze={left.glaze}
            parts={left.parts}
            selectedPartId={selectedPart}
            onPartSelect={setSelectedPart}
            viewId="left"
            syncEnabled={sync}
            syncRef={syncRef}
            resetToken={resetToken}
            className="h-full w-full"
          />
        </ViewerCard>
        <ViewerCard porcelain={right} label={rightLabel}>
          <PorcelainViewer
            key={`right-${right.id}-${right.modelUrl ?? ""}`}
            modelUrl={right.modelUrl}
            photoTexture={
              right.textureProjection?.coverage === "symmetric-full"
            }
            framingRadius={framingRadius}
            shape={right.shape}
            glaze={right.glaze}
            parts={right.parts}
            selectedPartId={selectedPart}
            onPartSelect={setSelectedPart}
            viewId="right"
            syncEnabled={sync}
            syncRef={syncRef}
            resetToken={resetToken}
            className="h-full w-full"
          />
        </ViewerCard>
      </div>
    </div>
  );
}

export default CompareViewer;
