import { useEffect, useState } from "react";

const names = ["正面（0°）", "右侧（90°）", "背面（180°）", "左侧（270°）"];
export default function MultiViewUpload({
  loading,
  onReconstruct,
}: {
  loading: boolean;
  onReconstruct: (files: File[]) => Promise<void>;
}) {
  const [files, setFiles] = useState<(File | null)[]>([null, null, null, null]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    const urls = files.map((file) => (file ? URL.createObjectURL(file) : ""));
    setPreviews(urls);
    return () =>
      urls.forEach((url) => {
        if (url) URL.revokeObjectURL(url);
      });
  }, [files]);
  return (
    <div className="panel space-y-4 p-5">
      <h2 className="font-display text-xl">四视角轮廓重建</h2>
      <p className="text-xs leading-6 text-ink-soft">
        保持相机高度与焦距一致，水平拍摄同一器物的四个方向。各方向的纹饰使用对应照片，背面使用背面照片。
      </p>
      <div className="grid grid-cols-2 gap-3">
        {names.map((name, index) => (
          <label
            key={name}
            className="block rounded border border-ink/15 p-2 text-xs"
          >
            {name}
            {previews[index] && (
              <img
                className="mt-2 h-24 w-full object-contain"
                src={previews[index]}
                alt={name}
              />
            )}
            <input
              aria-label={"多视角" + name}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={loading}
              className="mt-2 w-full text-xs"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                if (file.size > 12 * 1024 * 1024) {
                  setError("每张照片不能超过12MB");
                  return;
                }
                setError("");
                setFiles((old) =>
                  old.map((value, i) => (i === index ? file : value)),
                );
              }}
            />
          </label>
        ))}
      </div>
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      <button
        className="btn-gold w-full"
        disabled={loading || files.some((file) => !file)}
        onClick={() => void onReconstruct(files as File[])}
      >
        {loading ? "正在重建…" : "使用四张照片重建"}
      </button>
    </div>
  );
}
