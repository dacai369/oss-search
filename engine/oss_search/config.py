"""配置加载：信源清单.yaml → 启用的源列表（TASK-002+）。"""

from __future__ import annotations

import os
import yaml
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_SOURCES_PATH = os.path.join(ROOT, "规范", "信源清单.yaml")


def load_sources(path: Optional[str] = None) -> Dict[str, Any]:
    """加载信源清单 YAML。"""
    with open(path or DEFAULT_SOURCES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def enabled_sources(data: Dict[str, Any], group: str) -> List[Dict[str, Any]]:
    """返回某个 group 下 enabled:true 的源，按 priority 升序排列。"""
    items = []
    for src in data.get(group, []):
        if src.get("enabled") is True:
            items.append(src)
    items.sort(key=lambda s: s.get("priority", 99))
    return items


def source_by_id(data: Dict[str, Any], src_id: str) -> Optional[Dict[str, Any]]:
    """在所有 group 里找一个源。"""
    for group in ("code_platforms", "package_registries", "content_sources"):
        for src in data.get(group, []):
            if src.get("id") == src_id:
                return src
    return None
