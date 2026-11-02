import type {
  ComparisonPair,
  ComparisonRequest,
  MorphologyMeasurement,
  Porcelain,
} from "../types/porcelain";

const BASE = (import.meta.env.VITE_COMPARISON_BASE ?? "").replace(/\/$/, "");
async function call<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(BASE + "/api" + path, {
    ...options,
    credentials: "include",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(
      typeof error?.detail === "string"
        ? error.detail
        : "形态服务请求失败（" + response.status + "）",
    );
  }
  return response.json();
}
export function fetchComparisonCatalog(
  signal?: AbortSignal,
): Promise<Porcelain[]> {
  return call("/comparison/artifacts", { signal });
}
export function fetchComparisonPair(
  selection: ComparisonRequest,
  signal?: AbortSignal,
): Promise<ComparisonPair> {
  return call("/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(selection),
    signal,
  });
}
export function measureModel(
  modelUrl: string,
  signal?: AbortSignal,
): Promise<MorphologyMeasurement> {
  return call("/measure", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ modelUrl }),
    signal,
  });
}
export function importComparisonModel(
  file: File,
  upAxis: string,
  signal?: AbortSignal,
  heightCm?: number,
): Promise<{ artifact: Porcelain; measurement: MorphologyMeasurement }> {
  const form = new FormData();
  form.set("file", file);
  form.set("upAxis", upAxis);
  if (heightCm !== undefined) form.set("heightCm", String(heightCm));
  return call("/measure/upload", { method: "POST", body: form, signal });
}
