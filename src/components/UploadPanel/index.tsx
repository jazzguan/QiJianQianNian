import { useEffect, useRef, useState } from "react";
import type { DragEvent, ChangeEvent } from "react";
import { Capacitor } from "@capacitor/core";
import {
  Camera,
  CameraDirection,
  CameraErrorCode,
  MediaTypeSelection,
} from "@capacitor/camera";
import type { MediaResult } from "@capacitor/camera";

export type ReconstructMode = "auto" | "hunyuan";

interface UploadPanelProps {
  onReconstruct: (file: File) => void;
  loading?: boolean;
  mode?: ReconstructMode;
  onModeChange?: (mode: ReconstructMode) => void;
  hunyuanAvailable?: boolean;
}

export function UploadPanel({
  onReconstruct,
  loading,
  mode = "auto",
  onModeChange,
  hunyuanAvailable = true,
}: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [checking, setChecking] = useState(false);
  const [picking, setPicking] = useState(false);
  const [pickError, setPickError] = useState("");
  const [checks, setChecks] = useState<
    { label: string; passed: boolean; detail: string }[]
  >([]);

  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );

  async function inspectImage(f: File) {
    setChecking(true);
    try {
      const bitmap = await createImageBitmap(f);
      const originalWidth = bitmap.width;
      const originalHeight = bitmap.height;
      const width = Math.min(originalWidth, 320);
      const height = Math.max(
        1,
        Math.round((originalHeight / originalWidth) * width),
      );
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d", { willReadFrequently: true });
      if (!context) return;
      context.drawImage(bitmap, 0, 0, width, height);
      bitmap.close();
      const pixels = context.getImageData(0, 0, width, height).data;
      const gray = new Float32Array(width * height);
      let brightness = 0;
      for (let i = 0, p = 0; i < pixels.length; i += 4, p++) {
        gray[p] =
          pixels[i] * 0.299 + pixels[i + 1] * 0.587 + pixels[i + 2] * 0.114;
        brightness += gray[p];
      }
      brightness /= gray.length;
      let edgeEnergy = 0;
      let edgeCount = 0;
      for (let y = 1; y < height - 1; y++) {
        for (let x = 1; x < width - 1; x++) {
          const i = y * width + x;
          edgeEnergy += Math.abs(
            gray[i] * 4 -
              gray[i - 1] -
              gray[i + 1] -
              gray[i - width] -
              gray[i + width],
          );
          edgeCount++;
        }
      }
      const sharpness = edgeEnergy / Math.max(edgeCount, 1);

      // 用四角像素估计背景色，再按"与背景色差异"粗略判断器物范围。
      // 只是为了给拍摄提示，不追求精确分割，所以阈值取得比较保守。
      const corner = Math.max(6, Math.round(Math.min(width, height) * 0.08));
      const bgSamples: number[][] = [[], [], []];
      for (const [cx, cy] of [
        [0, 0],
        [width - corner, 0],
        [0, height - corner],
        [width - corner, height - corner],
      ]) {
        for (let y = cy; y < cy + corner; y++) {
          for (let x = cx; x < cx + corner; x++) {
            const i = (y * width + x) * 4;
            bgSamples[0].push(pixels[i]);
            bgSamples[1].push(pixels[i + 1]);
            bgSamples[2].push(pixels[i + 2]);
          }
        }
      }
      const median = (values: number[]) => {
        const sorted = values.slice().sort((a, b) => a - b);
        return sorted[Math.floor(sorted.length / 2)] ?? 128;
      };
      const bgColor = bgSamples.map(median);

      const foreground = new Uint8Array(width * height);
      let highlights = 0;
      for (let p = 0; p < width * height; p++) {
        const i = p * 4;
        const distance = Math.hypot(
          pixels[i] - bgColor[0],
          pixels[i + 1] - bgColor[1],
          pixels[i + 2] - bgColor[2],
        );
        if (distance > 60) foreground[p] = 1;
        if (gray[p] > 245) highlights++;
      }

      const band = Math.max(2, Math.round(Math.min(width, height) * 0.06));
      let bandTotal = 0;
      let bandForeground = 0;
      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          if (
            x >= band &&
            y >= band &&
            x < width - band &&
            y < height - band
          )
            continue;
          bandTotal++;
          if (foreground[y * width + x]) bandForeground++;
        }
      }
      const edgeRatio = bandForeground / Math.max(bandTotal, 1);

      let minX = width,
        maxX = -1,
        minY = height,
        maxY = -1;
      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          if (!foreground[y * width + x]) continue;
          if (x < minX) minX = x;
          if (x > maxX) maxX = x;
          if (y < minY) minY = y;
          if (y > maxY) maxY = y;
        }
      }
      const fillRatio =
        maxX < 0
          ? 0
          : Math.max(
              (maxX - minX + 1) / width,
              (maxY - minY + 1) / height,
            );
      const highlightRatio = highlights / (width * height);

      setChecks([
        {
          label: "分辨率",
          passed: originalWidth >= 720 || originalHeight >= 720,
          detail: `${originalWidth} × ${originalHeight}`,
        },
        {
          label: "曝光",
          passed: brightness >= 40 && brightness <= 215,
          detail:
            brightness < 40
              ? "画面偏暗"
              : brightness > 215
                ? "画面偏亮"
                : "亮度正常",
        },
        {
          label: "细节",
          passed: sharpness >= 7,
          detail: sharpness >= 7 ? "边缘较清楚" : "可能模糊，请稳住手机重拍",
        },
        {
          label: "器型完整",
          passed: edgeRatio < 0.35,
          detail:
            edgeRatio >= 0.35
              ? "器物贴到画面边缘，口沿或底部可能被裁掉"
              : "主体四周留有余量",
        },
        {
          label: "反光",
          passed: highlightRatio < 0.06,
          detail:
            highlightRatio >= 0.06
              ? `高光占 ${(highlightRatio * 100).toFixed(1)}%，玻璃或釉面反射偏强`
              : "高光可控",
        },
        {
          label: "占幅",
          passed: fillRatio >= 0.4 && fillRatio <= 0.98,
          detail:
            fillRatio < 0.4
              ? `主体只占 ${Math.round(fillRatio * 100)}%，请靠近一些`
              : fillRatio > 0.98
                ? "主体几乎占满画面，容易切边"
                : `主体占 ${Math.round(fillRatio * 100)}%`,
        },
      ]);
    } catch {
      setChecks([
        {
          label: "图片检查",
          passed: false,
          detail: "无法自动检查，请确认照片清晰",
        },
      ]);
    } finally {
      setChecking(false);
    }
  }

  const acceptFile = (f: File | undefined) => {
    if (!f || !f.type.startsWith("image/")) return;
    if (preview) URL.revokeObjectURL(preview);
    setFile(f);
    setPreview(URL.createObjectURL(f));
    void inspectImage(f);
  };

  async function mediaResultToFile(result: MediaResult, prefix: string) {
    const source =
      result.webPath ??
      (result.uri ? Capacitor.convertFileSrc(result.uri) : undefined);
    if (!source) throw new Error("没有读取到照片，请重试。");
    const response = await fetch(source);
    if (!response.ok) throw new Error("照片读取失败，请重试。");
    const blob = await response.blob();
    const format = result.metadata?.format?.replace("jpeg", "jpg") || "jpg";
    return new File([blob], `${prefix}-${Date.now()}.${format}`, {
      type: blob.type || `image/${format === "jpg" ? "jpeg" : format}`,
    });
  }

  function isCancelled(error: unknown) {
    const code = (error as { code?: string })?.code;
    return (
      code === CameraErrorCode.TakePhotoCancelled ||
      code === CameraErrorCode.ChooseMediaCancelled
    );
  }

  async function takePhoto() {
    if (!Capacitor.isNativePlatform()) {
      cameraRef.current?.click();
      return;
    }
    setPicking(true);
    setPickError("");
    try {
      const photo = await Camera.takePhoto({
        cameraDirection: CameraDirection.Rear,
        quality: 92,
        targetWidth: 2048,
        targetHeight: 2048,
        correctOrientation: true,
        saveToGallery: false,
        editable: "no",
        includeMetadata: true,
      });
      acceptFile(await mediaResultToFile(photo, "camera"));
    } catch (error) {
      if (!isCancelled(error))
        setPickError(
          (error as Error).message || "无法打开相机，请检查相机权限。",
        );
    } finally {
      setPicking(false);
    }
  }

  async function choosePhoto() {
    if (!Capacitor.isNativePlatform()) {
      inputRef.current?.click();
      return;
    }
    setPicking(true);
    setPickError("");
    try {
      const gallery = await Camera.chooseFromGallery({
        mediaType: MediaTypeSelection.Photo,
        allowMultipleSelection: false,
        quality: 92,
        targetWidth: 2048,
        targetHeight: 2048,
        correctOrientation: true,
        includeMetadata: true,
      });
      const selected = gallery.results[0];
      if (selected) acceptFile(await mediaResultToFile(selected, "gallery"));
    } catch (error) {
      if (!isCancelled(error))
        setPickError(
          (error as Error).message || "无法读取相册，请检查照片权限。",
        );
    } finally {
      setPicking(false);
    }
  }

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    acceptFile(e.dataTransfer.files?.[0]);
  };

  const onPick = (e: ChangeEvent<HTMLInputElement>) => {
    acceptFile(e.target.files?.[0]);
    e.target.value = "";
  };

  return (
    <div className="panel flex flex-col gap-4 p-4 sm:gap-5 sm:p-6">
      <div>
        <span className="eyebrow">拍摄 / 选择瓷器图片</span>
        <p className="mt-2 text-sm leading-relaxed text-ink-soft">
          正面拍摄，完整保留器口与器足；避免强反光和杂乱背景。
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label="重建模式">
        {(
          [
            {
              value: "auto" as const,
              title: "快速",
              detail: "约 10 秒 · 4–5 万面",
              hint: "先用它看器型对不对",
            },
            {
              value: "hunyuan" as const,
              title: "精细",
              detail: "约 1 分钟 · 约 50 万面",
              hint: "结构更完整，适合看细节",
            },
          ]
        ).map((item) => {
          const selected = mode === item.value;
          const disabled =
            loading || (item.value === "hunyuan" && !hunyuanAvailable);
          return (
            <button
              key={item.value}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={disabled}
              onClick={() => onModeChange?.(item.value)}
              className={
                "rounded-lg border px-3 py-2.5 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50 " +
                (selected
                  ? "border-gold bg-gold/10"
                  : "border-ink/15 bg-ivory/60 hover:border-gold/50")
              }
            >
              <span className="flex items-center justify-between">
                <span className="text-sm font-medium">{item.title}</span>
                {selected && <span className="text-[11px] text-gold">已选</span>}
              </span>
              <span className="mt-0.5 block text-[11px] leading-4 text-ink-soft">
                {item.detail}
              </span>
              <span className="mt-0.5 block text-[11px] leading-4 text-ink-soft/80">
                {item.hint}
              </span>
            </button>
          );
        })}
      </div>
      {mode === "hunyuan" && hunyuanAvailable && (
        <p className="-mt-1 text-[11px] leading-5 text-ink-soft">
          精细模式第一次使用要先加载模型，约 2–3 分钟；之后每次 1 分钟左右。
        </p>
      )}

      <ol className="grid gap-1.5 text-xs sm:grid-cols-2 sm:gap-2">
        {[
          "器物完整入镜，口沿和器足别被裁掉",
          "镜头与器物大致平齐，避免俯拍变形",
          "避开展柜灯光直射和玻璃反射",
          "主体占画面一半以上，背景尽量干净",
        ].map((item, index) => (
          <li
            key={item}
            className="flex items-start gap-2 rounded-md border border-ink/10 bg-ivory/60 px-3 py-2"
          >
            <span className="shrink-0 text-gold">0{index + 1}</span>
            <span className="leading-5">{item}</span>
          </li>
        ))}
      </ol>

      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={
          "flex min-h-[180px] cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border border-dashed p-3 text-center transition-colors sm:min-h-[240px] sm:p-4 " +
          (dragging
            ? "border-gold bg-gold/5"
            : "border-ink/25 hover:border-gold/60")
        }
      >
        {preview ? (
          <img
            src={preview}
            alt="预览"
            className="max-h-44 max-w-full object-contain sm:max-h-56"
          />
        ) : (
          <>
            <span className="text-3xl text-gold">＋</span>
            <span className="text-sm text-ink-soft">
              拖入图片，或使用下方按钮
            </span>
          </>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        hidden
        onChange={onPick}
      />
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        onChange={onPick}
      />

      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          className="btn-gold"
          disabled={picking || loading}
          onClick={() => void takePhoto()}
        >
          {picking ? "请稍候…" : "手机拍照"}
        </button>
        <button
          type="button"
          className="btn-ghost"
          disabled={picking || loading}
          onClick={() => void choosePhoto()}
        >
          从相册选择
        </button>
      </div>

      {pickError && (
        <p role="alert" className="text-xs leading-5 text-red-700">
          {pickError}
        </p>
      )}

      {(checking || checks.length > 0) && (
        <div
          className="space-y-2 border-t border-ink/10 pt-4"
          aria-live="polite"
        >
          <p className="text-xs text-ink-soft">
            {checking ? "正在检查照片…" : "拍摄质量检查"}
          </p>
          {!checking &&
            checks.map((check) => (
              <div
                key={check.label}
                className="flex items-center justify-between gap-3 text-xs"
              >
                <span>
                  {check.passed ? "✓" : "!"} {check.label}
                </span>
                <span
                  className={
                    check.passed ? "text-emerald-700" : "text-amber-700"
                  }
                >
                  {check.detail}
                </span>
              </div>
            ))}
        </div>
      )}

      {!checking && checks.some((check) => !check.passed) && (
        <p className="text-[11px] leading-5 text-amber-700">
          有 {checks.filter((check) => !check.passed).length}{" "}
          项没达标，可以继续，但补拍后效果通常更好。
        </p>
      )}

      <button
        type="button"
        className="btn-gold disabled:cursor-not-allowed disabled:opacity-50"
        disabled={!file || loading}
        onClick={() => file && onReconstruct(file)}
      >
        {loading ? "正在复原…" : "开始三维复原"}
      </button>
    </div>
  );
}

export default UploadPanel;
