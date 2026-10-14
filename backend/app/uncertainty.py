"""可观测性 / 不确定性分析与可视化。

说明：这里计算的是"基于可观测性的启发式不确定度"，而非真实概率置信度。
没有真实三维扫描数据校准时，不把启发式评分称作置信度，也不把生成的背面
当作真实文物数据。
"""
import time

import numpy as np
import trimesh

from . import config

VIEW_DIR = np.array([0.0, 0.0, 1.0], dtype=np.float32)  # 假设相机朝向 +z（启发式）


def orient_upright(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """把"最长轴"旋转到 Y 轴，让瓶/罐类器物竖起来（绕坐标轴 90° 旋转，保持朝向不变）。"""
    ext = np.asarray(mesh.extents, dtype=np.float32)  # (x, y, z)
    axis = int(np.argmax(ext))
    if axis == 1:
        return mesh

    v = np.asarray(mesh.vertices, dtype=np.float32).copy()
    if axis == 0:
        # x 最长：绕 Z 轴旋转，使 x -> y
        v = np.stack([-v[:, 1], v[:, 0], v[:, 2]], axis=1)
    else:  # axis == 2
        # TripoSR 的 Z 轴向上，绕 X 轴 -90°，保持顶部朝上。
        v = np.stack([v[:, 0], v[:, 2], -v[:, 1]], axis=1)

    mesh = mesh.copy()
    mesh.vertices = v
    return mesh


def normalize_mesh(mesh: trimesh.Trimesh, height: float = config.DISPLAY_HEIGHT) -> trimesh.Trimesh:
    """居中并归一化：水平居中，底部置于 y=0，高度缩放到给定值。"""
    mesh = mesh.copy()
    bounds = mesh.bounds
    center_xz = (bounds[0] + bounds[1]) / 2.0
    mesh.vertices[:, 0] -= center_xz[0]
    mesh.vertices[:, 2] -= center_xz[2]
    ymin = mesh.vertices[:, 1].min()
    mesh.vertices[:, 1] -= ymin

    h = mesh.vertices[:, 1].max() - mesh.vertices[:, 1].min()
    if h > 1e-6:
        scale = height / h
        mesh.vertices *= scale
    return mesh


def vertex_uncertainty(mesh: trimesh.Trimesh) -> np.ndarray:
    """逐顶点不确定度 [0,1]。0 = 可观测（正对相机），1 = 推断（背面/遮挡）。"""
    normals = np.asarray(mesh.vertex_normals, dtype=np.float32)
    norm = np.linalg.norm(normals, axis=1, keepdims=True)
    norm[norm < 1e-8] = 1.0
    n = normals / norm
    vis = np.clip(n @ VIEW_DIR, 0.0, 1.0)
    return (1.0 - vis).astype(np.float32)


def _colormap(u: np.ndarray) -> np.ndarray:
    """u∈[0,1] -> RGB。蓝(低) → 青 → 黄 → 红(高)。"""
    stops = np.array(
        [
            [0.0, 0.23, 0.30, 0.75],
            [0.33, 0.15, 0.62, 0.56],
            [0.66, 0.95, 0.80, 0.20],
            [1.0, 0.85, 0.18, 0.15],
        ],
        dtype=np.float32,
    )
    u = np.clip(u, 0.0, 1.0).reshape(-1, 1)
    idx = np.searchsorted(stops[:, 0], u[:, 0], side="right") - 1
    idx = np.clip(idx, 0, len(stops) - 2)
    c0, c1 = stops[idx], stops[idx + 1]
    t = ((u[:, 0] - c0[:, 0]) / np.maximum(c1[:, 0] - c0[:, 0], 1e-8)).reshape(-1, 1)
    rgb = c0[:, 1:] * (1 - t) + c1[:, 1:] * t
    return np.clip(rgb, 0.0, 1.0)


def make_heatmap_mesh(mesh: trimesh.Trimesh, uncertainty: np.ndarray) -> trimesh.Trimesh:
    """把逐顶点不确定度映射为顶点色，生成热力图网格（独立副本，不影响原始网格）。"""
    hm = mesh.copy()
    rgb = _colormap(uncertainty)
    rgba = np.concatenate([rgb, np.ones((rgb.shape[0], 1), dtype=np.float32)], axis=1)
    rgba_uint8 = (rgba * 255.0).astype(np.uint8)
    try:
        hm.visual = trimesh.visual.ColorVisuals(mesh=hm, vertex_colors=rgba_uint8)
    except TypeError:
        hm.visual = trimesh.visual.ColorVisuals(vertex_colors=rgba_uint8)
    return hm


def enhance_colors(
    mesh: trimesh.Trimesh,
    uncertainty: np.ndarray,
    view_dir: np.ndarray = VIEW_DIR,
    brightness: float = 1.2,
) -> trimesh.Trimesh:
    """增强效果：整体提亮 + 轴对称补色（把正面颜色铺到背面，消除背面发黑）。

    适用于瓶/罐等近似旋转对称的瓷器；对称性补色是后处理先验，非真实重建。
    """
    visual = mesh.visual
    if visual is None or visual.vertex_colors is None:
        return mesh

    colors = np.asarray(visual.vertex_colors, dtype=np.float32) / 255.0
    verts = np.asarray(mesh.vertices, dtype=np.float32)
    normals = np.asarray(mesh.vertex_normals, dtype=np.float32)
    n = normals / (np.linalg.norm(normals, axis=1, keepdims=True) + 1e-8)
    front = (n @ view_dir) > 0.1

    y = verts[:, 1]
    r = np.sqrt(verts[:, 0] ** 2 + verts[:, 2] ** 2)
    y_bins = np.linspace(y.min(), y.max(), 64)
    r_bins = np.linspace(0.0, r.max() + 1e-6, 32)
    yi = np.clip(np.digitize(y, y_bins) - 1, 0, len(y_bins) - 2)
    ri = np.clip(np.digitize(r, r_bins) - 1, 0, len(r_bins) - 2)

    acc = np.zeros((len(y_bins) - 1, len(r_bins) - 1, 3), dtype=np.float64)
    cnt = np.zeros((len(y_bins) - 1, len(r_bins) - 1), dtype=np.float64)
    if front.any():
        np.add.at(acc, (yi[front], ri[front]), colors[front, :3])
        np.add.at(cnt, (yi[front], ri[front]), 1.0)
    avg = np.zeros_like(acc)
    mask = cnt > 0
    avg[mask] = acc[mask] / cnt[mask][..., None]

    new_colors = colors.copy()
    back = ~front
    if back.any():
        fill = avg[yi[back], ri[back]]
        blend = np.clip(uncertainty[back, None], 0.0, 1.0)
        new_colors[back, :3] = blend * fill + (1.0 - blend) * colors[back, :3]

    # 整体提亮
    new_colors[:, :3] = np.clip(new_colors[:, :3] * brightness, 0.0, 1.0)

    rgba = (new_colors * 255.0).astype(np.uint8)
    try:
        mesh.visual = trimesh.visual.ColorVisuals(mesh=mesh, vertex_colors=rgba)
    except TypeError:
        mesh.visual = trimesh.visual.ColorVisuals(vertex_colors=rgba)
    return mesh


def compute_coarse_shape(mesh: trimesh.Trimesh, n: int = 32) -> list[list[float]]:
    """从网格提取粗略侧面轮廓 [半径, 高度]，用于前端取景/程序化兜底。"""
    verts = np.asarray(mesh.vertices, dtype=np.float32)
    ymin, ymax = verts[:, 1].min(), verts[:, 1].max()
    ys = np.linspace(ymin, ymax, n)
    edges = np.concatenate([[ymin], (ys[:-1] + ys[1:]) / 2.0, [ymax]])
    shape: list[list[float]] = []
    for i in range(n):
        y0, y1 = edges[i], edges[i + 1]
        mask = (verts[:, 1] >= y0) & (verts[:, 1] < y1)
        if mask.sum() == 0:
            r = 0.0
        else:
            r = float(np.sqrt((verts[mask, 0] ** 2 + verts[mask, 2] ** 2)).max())
        shape.append([r, float(ys[i])])
    return shape


def build_report(
    mesh: trimesh.Trimesh,
    uncertainty: np.ndarray,
    elapsed_ms: float,
) -> dict:
    """生成质量报告（明确标注局限）。"""
    observed = float((uncertainty < 0.33).mean())
    inferred = float((uncertainty > 0.66).mean())
    bbox = mesh.extents
    return {
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "bbox": [round(float(v), 3) for v in bbox],
        "observedRatio": round(observed, 3),
        "inferredRatio": round(inferred, 3),
        "elapsedMs": int(elapsed_ms),
        "note": (
            "不确定度为基于可观测性（法线朝向）的启发式估计，非真实概率置信度；"
            "背面/底部为模型推断区域。正面纹饰由上传照片投影，背面采用正面镜像纹理。"
        ),
    }
