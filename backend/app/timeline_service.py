"""历史演化数据访问与匹配逻辑。

当前使用本地 JSON 文件，接口层不依赖数据库。后续迁移到 SQLite 时，
只需要替换本模块的读取实现，保持 API 响应结构不变。
"""

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "timeline.json"


@lru_cache(maxsize=1)
def _load_data() -> dict[str, Any]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"历史演化数据文件不存在：{DATA_PATH}")
    with DATA_PATH.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, dict):
        raise ValueError("历史演化数据文件的根节点必须是对象")
    return data


def reload_data() -> None:
    """清除内存缓存，供开发调试或数据更新后调用。"""
    _load_data.cache_clear()


def list_dynasties() -> list[dict[str, Any]]:
    return copy.deepcopy(_load_data().get("dynasties", []))


def get_porcelain(porcelain_id: str) -> dict[str, Any] | None:
    for item in _load_data().get("porcelains", []):
        if item.get("id") == porcelain_id:
            return copy.deepcopy(item)
    return None


def get_dynasty_porcelain(dynasty: str) -> dict[str, Any] | None:
    dynasty_info = next(
        (item for item in _load_data().get("dynasties", []) if item.get("id") == dynasty),
        None,
    )
    if dynasty_info is None:
        return None
    return get_porcelain(str(dynasty_info["porcelainId"]))


def get_personalized_matches(category: str) -> list[dict[str, Any]]:
    normalized = category.strip()
    if not normalized:
        return []

    data = _load_data()
    configured = data.get("matches", {})
    matches = configured.get(normalized)
    if matches is not None:
        return copy.deepcopy(matches)

    # 未收录的器型也返回完整朝代序列，让前端能明确展示“暂无匹配”状态。
    return [
        {
            "dynasty": dynasty["id"],
            "porcelainId": None,
            "difference": "",
            "emptyReason": f"暂未找到“{normalized}”的可靠同类参考案例。",
        }
        for dynasty in data.get("dynasties", [])
    ]
