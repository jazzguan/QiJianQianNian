import { useEffect, useRef, useState } from "react";
import { CompareViewer } from "../../components/CompareViewer";
import {
  fetchComparisonCatalog,
  fetchComparisonPair,
  importComparisonModel,
} from "../../api/comparison";
import { usePorcelainModel } from "../../stores/PorcelainModelManager";
import { useSearchParams } from "react-router-dom";
import { useAuth, track } from "../../stores/Platform";
import { request } from "../../api/client";
import Sources from "../../components/Sources";
import type {
  AIQueryAnswer,
  ComparisonPair,
  Porcelain,
  ShapeProfile,
} from "../../types/porcelain";

function ProfileChart({
  left,
  right,
}: {
  left: ShapeProfile;
  right: ShapeProfile;
}) {
  const radius = Math.max(
    ...left.map((p) => p[0]),
    ...right.map((p) => p[0]),
    1,
  );
  const points = (shape: ShapeProfile) =>
    [
      ...shape.map(([r, y]) => [r, y]),
      ...[...shape].reverse().map(([r, y]) => [-r, y]),
    ]
      .map(([r, y]) => `${220 + (r / radius) * 155},${310 - (y / 30) * 280}`)
      .join(" ");
  return (
    <div className="panel p-5">
      <h2 className="font-display text-lg">截面外径轮廓</h2>
      <p className="mt-1 text-xs text-ink-soft">
        统一高度30，叠加观察腹径与口足的相对变化。
      </p>
      <svg
        viewBox="0 0 440 350"
        role="img"
        aria-label="左右器物的归一化截面轮廓叠加"
        className="mx-auto mt-4 w-full max-w-md"
      >
        {[0, 10, 20, 30].map((y) => (
          <g key={y}>
            <line
              x1="55"
              x2="405"
              y1={310 - (y / 30) * 280}
              y2={310 - (y / 30) * 280}
              stroke="#bcb7aa"
              opacity=".35"
            />
            <text x="22" y={315 - (y / 30) * 280} fontSize="12" fill="#676354">
              {y}
            </text>
          </g>
        ))}
        <line
          x1="220"
          x2="220"
          y1="30"
          y2="310"
          stroke="#bcb7aa"
          strokeDasharray="4 4"
        />
        <polygon
          points={points(left)}
          fill="#387087"
          fillOpacity=".08"
          stroke="#387087"
          strokeWidth="2"
        />
        <polygon
          points={points(right)}
          fill="#ac792d"
          fillOpacity=".06"
          stroke="#ac792d"
          strokeWidth="2"
          strokeDasharray="5 3"
        />
        <text x="95" y="340" fill="#387087" fontSize="13">
          实线：左侧
        </text>
        <text x="260" y="340" fill="#ac792d" fontSize="13">
          虚线：右侧
        </text>
      </svg>
    </div>
  );
}

function exportCsv(pair: ComparisonPair) {
  const cell = (value: string) =>
    '"' + (/^[=+@-]/.test(value) ? "'" : "") + value.replace(/"/g, '""') + '"';
  const rows = [
    [
      "参数（自动提取；归一化高度30）",
      pair.leftLabel ?? "",
      pair.rightLabel ?? "",
    ],
    ...[...pair.rows, ...(pair.cavityRows ?? [])].map((row) => [
      row.label,
      row.left,
      row.right,
    ]),
    ["厘米尺度", "", ""],
    ...(pair.physicalRows ?? []).map((row) => [row.label, row.left, row.right]),
    ["左侧标定来源", pair.leftMeasurement?.calibration?.source ?? "未标定", ""],
    [
      "右侧标定来源",
      pair.rightMeasurement?.calibration?.source ?? "未标定",
      "",
    ],
    ["差异洞察", pair.insight, ""],
    ...(pair.sources ?? []).map((s) => ["来源", s.title, s.url]),
  ];
  const url = URL.createObjectURL(
    new Blob(
      ["\uFEFF" + rows.map((row) => row.map(cell).join(",")).join("\r\n")],
      { type: "text/csv;charset=utf-8" },
    ),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "形态对比.csv";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function Comparison() {
  const { current } = usePorcelainModel();
  const { user } = useAuth();
  const [params] = useSearchParams();
  const [items, setItems] = useState<Porcelain[]>([]);
  const [leftId, setLeftId] = useState("");
  const [rightId, setRightId] = useState("");
  const [heights, setHeights] = useState({ left: "", right: "" });
  const [explanation, setExplanation] = useState<AIQueryAnswer | null>(null);
  const [explaining, setExplaining] = useState(false);
  const explanationRequest = useRef<AbortController | null>(null);
  const [pair, setPair] = useState<ComparisonPair | null>(null);
  const [loading, setLoading] = useState(false);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [uploading, setUploading] = useState<"left" | "right" | null>(null);
  const [axis, setAxis] = useState("y");
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const [ready, setReady] = useState(false);
  const activeRequest = useRef<AbortController | null>(null);
  const uploadRequest = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    activeRequest.current?.abort();
    setCatalogLoading(true);
    setLoading(false);
    setPair(null);
    setError("");
    fetchComparisonCatalog(controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;
        const shared =
          current?.source === "uploaded" &&
          current.modelUrl &&
          current.porcelain
            ? {
                ...current.porcelain,
                id: current.id,
                modelUrl: current.modelUrl,
                name: current.name || "我的瓷器",
                measurementSource: "mesh" as const,
              }
            : null;
        setItems(
          shared && !data.some((x) => x.id === shared.id)
            ? [...data, shared]
            : data,
        );
        setLeftId(params.get("left") ?? shared?.id ?? data[0]?.id ?? "");
        setRightId(params.get("right") ?? data[1]?.id ?? data[0]?.id ?? "");
        setReady(true);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setCatalogLoading(false);
      });
    return () => controller.abort();
  }, [
    reload,
    current?.id,
    current?.modelUrl,
    user?.id,
    params.get("left"),
    params.get("right"),
  ]);

  useEffect(
    () => () => {
      activeRequest.current?.abort();
      uploadRequest.current?.abort();
      explanationRequest.current?.abort();
    },
    [],
  );

  async function compare(left = leftId, right = rightId) {
    const a = items.find((x) => x.id === left),
      b = items.find((x) => x.id === right);
    if (!a || !b) return;
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    explanationRequest.current?.abort();
    setExplanation(null);
    setExplaining(false);
    setLoading(true);
    setError("");
    setPair(null);
    try {
      for (const height of Object.values(heights)) {
        if (
          height &&
          (!Number.isFinite(Number(height)) ||
            Number(height) <= 0 ||
            Number(height) > 1000)
        )
          throw new Error("实物高度需大于0且不超过1000厘米");
      }
      const result = await fetchComparisonPair(
        {
          leftId: a.id,
          rightId: b.id,
          leftHeightCm: heights.left ? Number(heights.left) : undefined,
          rightHeightCm: heights.right ? Number(heights.right) : undefined,
        },
        controller.signal,
      );
      if (!controller.signal.aborted) {
        setPair(result);
        if (user) {
          track(a.id, "compare").catch(() => {});
          track(b.id, "compare").catch(() => {});
        }
      }
    } catch (e) {
      if (!controller.signal.aborted)
        setError(e instanceof Error ? e.message : "对比失败");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  useEffect(() => {
    if (ready) {
      setReady(false);
      void compare();
    }
  }, [ready, items]);

  function choose(side: "left" | "right", value: string) {
    activeRequest.current?.abort();
    setLoading(false);
    setPair(null);
    setError("");
    explanationRequest.current?.abort();
    setExplanation(null);
    setExplaining(false);
    setHeights((old) => ({ ...old, [side]: "" }));
    if (side === "left") setLeftId(value);
    else setRightId(value);
  }

  async function upload(side: "left" | "right", file?: File) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".glb")) {
      setError("请上传GLB模型");
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setError("GLB不能超过20MB");
      return;
    }
    const controller = new AbortController();
    uploadRequest.current = controller;
    setUploading(side);
    setError("");
    try {
      const rawHeight = heights[side];
      const result = await importComparisonModel(
        file,
        axis,
        controller.signal,
        rawHeight ? Number(rawHeight) : undefined,
      );
      if (controller.signal.aborted) return;
      setItems((old) => [...old, result.artifact]);
      choose(side, result.artifact.id);
    } catch (e) {
      if (!controller.signal.aborted)
        setError(e instanceof Error ? e.message : "导入失败");
    } finally {
      if (!controller.signal.aborted) setUploading(null);
    }
  }

  const features: Array<[string, keyof Porcelain]> = [
    ["器型", "formFeatures"],
    ["纹饰", "decorationFeatures"],
    ["工艺", "craftFeatures"],
    ["材质", "material"],
    ["用途", "use"],
    ["历史背景", "history"],
  ];
  const describe = (item: Porcelain, key: keyof Porcelain) => {
    const value = item[key];
    return Array.isArray(value)
      ? value.join("；") || "未提供资料"
      : String(value || "未提供资料");
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="font-display text-3xl font-semibold">跨时期形态对比</h1>
      <p className="mt-2 text-sm text-ink-soft">
        选择两件器物或导入GLB，从三维截面测量形态，观察比例、纹饰与工艺的差异。
      </p>
      <div className="panel mt-6 space-y-5 p-5">
        <div className="grid gap-5 sm:grid-cols-2">
          {(["left", "right"] as const).map((side) => (
            <div key={side}>
              <label
                htmlFor={side + "-artifact"}
                className="mb-2 block text-sm"
              >
                {side === "left" ? "左侧器物" : "右侧器物"}
              </label>
              <select
                id={side + "-artifact"}
                value={side === "left" ? leftId : rightId}
                disabled={catalogLoading || !!uploading}
                onChange={(e) => choose(side, e.target.value)}
                className="w-full border border-ink/20 bg-paper p-2"
              >
                {items.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.dynastyName} · {item.name}
                  </option>
                ))}
              </select>
              <label className="mt-3 block text-xs text-ink-soft">
                实物高度（厘米，留空使用馆藏记录）
                <input
                  type="number"
                  min="0.001"
                  max="1000"
                  step="any"
                  aria-label={side === "left" ? "左侧实物高度" : "右侧实物高度"}
                  value={heights[side]}
                  placeholder="可选"
                  disabled={loading || !!uploading}
                  className="mt-1 w-full border border-ink/20 bg-paper p-2 text-sm"
                  onChange={(e) => {
                    activeRequest.current?.abort();
                    explanationRequest.current?.abort();
                    setLoading(false);
                    setExplaining(false);
                    setPair(null);
                    setExplanation(null);
                    setHeights((h) => ({ ...h, [side]: e.target.value }));
                  }}
                />
              </label>
              <label className="mt-3 inline-flex cursor-pointer items-center text-sm text-blue">
                {uploading === side ? "正在导入与测量…" : "导入GLB模型"}
                <input
                  aria-label={side === "left" ? "导入左侧GLB" : "导入右侧GLB"}
                  type="file"
                  accept=".glb"
                  disabled={catalogLoading || !!uploading || !user}
                  className="ml-3 max-w-[230px] text-xs"
                  onChange={(e) => {
                    void upload(side, e.target.files?.[0]);
                    e.target.value = "";
                  }}
                />
              </label>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <label className="text-sm text-ink-soft">
            导入模型的竖直轴
            <select
              aria-label="导入模型竖直轴"
              value={axis}
              disabled={!!uploading}
              onChange={(e) => setAxis(e.target.value)}
              className="ml-2 border border-ink/20 bg-paper p-1"
            >
              {["y", "z", "x", "-y", "-z", "-x"].map((a) => (
                <option key={a} value={a}>
                  {a.toUpperCase()}
                </option>
              ))}
            </select>
          </label>
          <button
            className="btn-gold"
            disabled={loading || catalogLoading || !!uploading || !items.length}
            onClick={() => void compare()}
          >
            {loading ? "正在计算…" : "开始对比"}
          </button>
        </div>
        <p className="text-xs text-ink-soft">
          馆藏照片模型从轮廓测量，扫描、导入及重建模型从网格截面测量。比例统一高度30；填写实物高度后换算厘米尺寸。
          {!user && "登录后可导入并保存自己的GLB。"}
        </p>
      </div>
      {error && (
        <div
          role="alert"
          className="panel mt-5 flex flex-wrap items-center justify-between gap-3 border-red-300 p-4"
        >
          <p>{error}</p>
          <button
            className="btn-ghost"
            onClick={() =>
              catalogLoading || !items.length
                ? setReload((x) => x + 1)
                : void compare()
            }
          >
            重试
          </button>
        </div>
      )}
      {(loading || catalogLoading) && (
        <p role="status" className="mt-8 text-center text-sm">
          正在加载与测量…
        </p>
      )}
      {!loading && !catalogLoading && !pair && !error && (
        <p className="panel mt-8 p-8 text-center text-ink-soft">
          已选择器物，点击“开始对比”查看测量结果。
        </p>
      )}
      {pair?.left && pair.right && (
        <div className="mt-8 space-y-6">
          <CompareViewer key={pair.id} left={pair.left} right={pair.right} />
          <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
            <div className="panel overflow-x-auto">
              <div className="flex items-center justify-between gap-3 border-b border-ink/10 p-5">
                <div>
                  <h2 className="font-display text-lg">形态参数 · 自动提取</h2>
                  <p className="mt-1 text-xs text-ink-soft">
                    归一化单位（高度=30）
                  </p>
                </div>
                <button
                  className="btn-ghost !px-3 !py-2 text-xs"
                  onClick={() => exportCsv(pair)}
                >
                  导出CSV
                </button>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-ink/10 text-left text-ink-soft">
                    <th className="p-4">参数</th>
                    <th className="p-4">{pair.leftLabel}</th>
                    <th className="p-4">{pair.rightLabel}</th>
                  </tr>
                </thead>
                <tbody>
                  {[...pair.rows, ...(pair.cavityRows ?? [])].map((row) => (
                    <tr key={row.label} className="border-b border-ink/5">
                      <td className="p-4">{row.label}</td>
                      <td className="p-4">{row.left}</td>
                      <td className="p-4">{row.right}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="p-4 text-xs text-ink-soft">
                左侧：{pair.leftMeasurement?.method} · 右侧：
                {pair.rightMeasurement?.method}。内口径与壁厚需要网格包含内壁。
              </p>
            </div>
            <ProfileChart left={pair.left.shape} right={pair.right.shape} />
          </div>
          <div className="panel overflow-x-auto p-5">
            <h2 className="font-display text-lg">厘米尺寸 · 按高度标定</h2>
            <p className="mt-2 text-xs text-ink-soft">
              左侧：{pair.leftMeasurement?.calibration?.source ?? "尚未标定"}
              ；右侧：{pair.rightMeasurement?.calibration?.source ?? "尚未标定"}
              。
            </p>
            <table className="mt-3 w-full text-sm">
              <tbody>
                {pair.physicalRows?.map((row) => (
                  <tr key={row.label} className="border-b border-ink/5">
                    <th className="p-3 text-left font-normal">{row.label}</th>
                    <td className="p-3">{row.left}</td>
                    <td className="p-3">{row.right}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="panel p-6">
            <h2 className="font-display text-xl">形态差异</h2>
            <p className="mt-3 text-sm leading-7">{pair.insight}</p>
          </div>
          <div className="panel overflow-x-auto">
            <h2 className="border-b border-ink/10 p-5 font-display text-lg">
              目录特征对照
            </h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ink/10 text-left">
                  <th className="p-4">特征</th>
                  <th className="p-4">{pair.leftLabel}</th>
                  <th className="p-4">{pair.rightLabel}</th>
                </tr>
              </thead>
              <tbody>
                {features.map(([label, key]) => (
                  <tr key={key} className="border-b border-ink/5">
                    <td className="p-4">{label}</td>
                    <td className="p-4 leading-7">
                      {describe(pair.left!, key)}
                    </td>
                    <td className="p-4 leading-7">
                      {describe(pair.right!, key)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Sources sources={pair.sources} />
          <div className="panel p-6">
            <button
              className="btn-gold"
              disabled={explaining}
              onClick={async () => {
                explanationRequest.current?.abort();
                const controller = new AbortController();
                explanationRequest.current = controller;
                setExplaining(true);
                try {
                  const answer = await request<AIQueryAnswer>(
                    "/compare/explain",
                    {
                      method: "POST",
                      signal: controller.signal,
                      body: JSON.stringify({
                        leftId: pair.leftId,
                        rightId: pair.rightId,
                        leftHeightCm: heights.left
                          ? Number(heights.left)
                          : undefined,
                        rightHeightCm: heights.right
                          ? Number(heights.right)
                          : undefined,
                      }),
                    },
                  );
                  if (!controller.signal.aborted) setExplanation(answer);
                } catch (e) {
                  if (!controller.signal.aborted)
                    setError((e as Error).message);
                } finally {
                  if (!controller.signal.aborted) setExplaining(false);
                }
              }}
            >
              {explaining ? "正在分析…" : "AI 分析形态、纹饰与工艺差异"}
            </button>
            {explanation && (
              <>
                <p className="mt-4 whitespace-pre-line text-sm leading-7">
                  {explanation.answer}
                </p>
                <Sources sources={explanation.sources} />
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
