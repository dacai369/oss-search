"""归并去重 · 实体对齐（TASK-005）。

把指向同一真实项目的多来源结果合并成一条。
- 归一化键：仓库 URL（host+owner+repo 规范化）
- 合并策略：保留信息最全的一条，来源记入 raw.sources
- 跨源加权信号（同一项目被 github+npm+content 都提到 → 评分加权）
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from .models import Candidate


def dedup(candidates: List[Candidate]) -> List[Candidate]:
    """归并去重：多来源 Candidate 按归一化仓库 URL 合并。

    同项目可来自 github、npm、pypi、content（内容提及），
    合并后保留信息最全的一条，并在 raw.sources 记录所有来源。
    """
    groups: Dict[str, List[Candidate]] = {}
    order: List[str] = []

    for c in candidates:
        key = normalize_repo_url(c.url)
        if not key and c.full_name:
            # fallback: 从 full_name 构造 key
            key = f"github.com/{c.full_name.lower()}"
        if not key:
            # 无仓库 URL 的候选单独成组
            key = f"__nogroup__{c.id}"

        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(c)

    merged: List[Candidate] = []
    for key in order:
        group = groups[key]
        if len(group) == 1:
            c = group[0]
            c.raw["sources"] = [c.source]
            merged.append(c)
        else:
            merged.append(_merge_group(key, group))

    return merged


def normalize_repo_url(url: str) -> str:
    """规范化仓库 URL 为统一键。

    处理：大小写、末尾斜杠、.git 后缀、www 前缀。
    >>> normalize_repo_url("https://github.com/Owner/Repo.git")
    'github.com/owner/repo'
    >>> normalize_repo_url("https://www.github.com/owner/repo/")
    'github.com/owner/repo'
    """
    if not url:
        return ""
    url = url.strip().lower()
    # 去协议
    url = re.sub(r"^https?://", "", url)
    # 去 www
    url = re.sub(r"^www\.", "", url)
    # 去尾部斜杠
    url = url.rstrip("/")
    # 去 .git 后缀
    url = re.sub(r"\.git$", "", url)
    # 去掉非 repo 路径部分（如 /issues, /tree/...）
    # 只保留 host/owner/repo 三级
    parts = url.split("/")
    if len(parts) >= 3:
        url = "/".join(parts[:3])
    return url


def _merge_group(key: str, group: List[Candidate]) -> Candidate:
    """合并一组指向同一项目的 Candidate，保留信息最全的一条。"""
    # 选信息最全的作为基底（非空字段最多）
    def _score(c: Candidate) -> int:
        s = 0
        for attr in ["description", "language", "license", "stars", "forks",
                      "last_commit_at", "open_issues", "contributors",
                      "readme_excerpt"]:
            v = getattr(c, attr, None)
            if v is not None and v != "":
                s += 1
        return s

    best = max(group, key=_score)

    # 收集所有来源
    sources = list(dict.fromkeys(c.source for c in group))  # 去重保序
    source_count = len(sources)

    # 合并 raw 数据
    merged_raw: Dict[str, Any] = dict(best.raw)
    merged_raw["sources"] = sources
    merged_raw["source_count"] = source_count
    merged_raw["merged_from"] = len(group)
    # 保留各源的 url
    merged_raw["source_urls"] = {c.source: c.url for c in group}

    # 用非空值填补基底缺失的字段
    for c in group:
        if c is best:
            continue
        for attr in ["description", "language", "license", "readme_excerpt"]:
            best_val = getattr(best, attr, None)
            other_val = getattr(c, attr, None)
            if (best_val is None or best_val == "") and (other_val is not None and other_val != ""):
                setattr(best, attr, other_val)

        # numeric: 取 max
        for attr in ["stars", "forks", "open_issues", "contributors"]:
            best_val = getattr(best, attr) or 0
            other_val = getattr(c, attr) or 0
            if other_val > best_val:
                setattr(best, attr, other_val)

        # last_commit_at: 取最近
        if best.last_commit_at is None and c.last_commit_at is not None:
            best.last_commit_at = c.last_commit_at

    best.raw = merged_raw
    return best
