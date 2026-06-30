"""包仓库适配器：npm + PyPI。

按 candidate_packages / 关键词查包，从包元数据抽取仓库地址，输出统一 Candidate。
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from .models import Candidate, IntentSpec, Capability


# ============ npm 适配器 ============


class NpmAdapter:
    """npm registry 适配器。"""

    name = "npm"
    SEARCH_URL = "https://registry.npmjs.org/-/v1/search"
    SIZE = 10

    def __init__(self, record_path: Optional[str] = None):
        self._record_path = record_path
        self._recorded: List[Dict] = []

    def search(self, capability: Capability, spec: IntentSpec) -> List[Candidate]:
        """按 candidate_packages + keywords_en 搜索 npm。"""
        queries = self._build_queries(capability)
        seen: set = set()
        candidates: List[Candidate] = []

        for q in queries:
            try:
                results = self._search(q)
            except Exception:
                results = []
            for pkg in results:
                cand = self._to_candidate(pkg, capability.id)
                key = cand.id
                if key not in seen:
                    seen.add(key)
                    candidates.append(cand)
            time.sleep(0.3)

        return candidates

    def _build_queries(self, cap: Capability) -> List[str]:
        """优先 package 名，再回退关键词。"""
        queries = list(cap.candidate_packages)
        if not queries:
            queries = [kw.replace(" ", "+") for kw in cap.keywords_en[:3]]
        return queries or []

    def _search(self, query: str) -> List[Dict]:
        url = f"{self.SEARCH_URL}?text={urllib.parse.quote(query)}&size={self.SIZE}"
        return self._get_json(url) or []

    def _get_json(self, url: str) -> Optional[List[Dict]]:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                if self._record_path is not None:
                    self._recorded.append({"url": url, "body": data})
                return data.get("objects", [])
        except (urllib.error.URLError, json.JSONDecodeError, OSError):
            return None

    def _to_candidate(self, pkg: Dict, capability_id: str) -> Candidate:
        obj = pkg.get("package", pkg)
        name = obj.get("name", "")
        repo_url = _extract_repo_from_npm(obj)
        return Candidate(
            id=f"npm:{name}",
            source="npm",
            name=name,
            full_name=name,
            url=repo_url or obj.get("links", {}).get("npm", f"https://www.npmjs.com/package/{name}"),
            description=obj.get("description") or "",
            language="JavaScript",
            license=obj.get("license"),
            stars=None,
            forks=None,
            last_commit_at=None,
            open_issues=None,
            contributors=None,
            topics=obj.get("keywords") or [],
            readme_excerpt=obj.get("description") or "",
            matched_capability=capability_id,
            raw=obj,
        )

    def flush_recording(self):
        if self._record_path and self._recorded:
            import os
            os.makedirs(os.path.dirname(self._record_path), exist_ok=True)
            with open(self._record_path, "w", encoding="utf-8") as f:
                json.dump(self._recorded, f, ensure_ascii=False, indent=2)
            self._recorded.clear()


# ============ PyPI 适配器 ============


class PypiAdapter:
    """PyPI JSON API 适配器。"""

    name = "pypi"
    BASE = "https://pypi.org/pypi"

    def __init__(self):
        pass

    def search(self, capability: Capability, spec: IntentSpec) -> List[Candidate]:
        """按 candidate_packages 查 PyPI（不支持通用关键词搜索）。"""
        candidates: List[Candidate] = []
        packages = list(capability.candidate_packages)

        for pkg_name in packages:
            try:
                data = self._get_package(pkg_name.strip())
            except Exception:
                continue
            if not data:
                continue
            info = data.get("info", {})
            if not info.get("name"):
                continue
            candidates.append(self._to_candidate(info, capability.id))
            time.sleep(0.2)

        return candidates

    def _get_package(self, name: str) -> Optional[Dict]:
        url = f"{self.BASE}/{urllib.parse.quote(name, safe='')}/json"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, OSError):
            return None

    def _to_candidate(self, info: Dict, capability_id: str) -> Candidate:
        name = info.get("name", "")
        repo_url = _extract_repo_from_pypi(info)
        return Candidate(
            id=f"pypi:{name}",
            source="pypi",
            name=name,
            full_name=name,
            url=repo_url or info.get("home_page") or info.get("package_url", ""),
            description=info.get("summary") or "",
            language="Python",
            license=info.get("license"),
            stars=None,
            forks=None,
            last_commit_at=None,
            open_issues=None,
            contributors=None,
            topics=info.get("keywords") or [],
            readme_excerpt=info.get("summary") or "",
            matched_capability=capability_id,
            raw=info,
        )


# ============ 仓库 URL 提取 ============


def _extract_repo_from_npm(pkg: Dict) -> str:
    """从 npm 包对象提取 GitHub 仓库 URL。"""
    links = pkg.get("links", {})
    # repository link
    repo = links.get("repository") or ""
    if repo:
        return _normalize_github_url(repo)
    # 搜索 homepage
    for key in ("homepage", "bugs"):
        url = links.get(key, "")
        gh = _normalize_github_url(url)
        if gh:
            return gh
    return ""


def _extract_repo_from_pypi(info: Dict) -> str:
    """从 PyPI info 提取 GitHub 仓库 URL。"""
    # project_urls 字典
    urls = info.get("project_urls") or {}
    for key, val in urls.items():
        if val:
            gh = _normalize_github_url(val)
            if gh:
                return gh
    # home_page
    gh = _normalize_github_url(info.get("home_page") or "")
    if gh:
        return gh
    return ""


_GITHUB_RE = re.compile(r"(?:https?://)?github\.com/([^/]+/[^/?#]+)")


def _normalize_github_url(url: str) -> str:
    m = _GITHUB_RE.search(url)
    if not m:
        return ""
    path = m.group(1).rstrip("/").replace(".git", "")
    return f"https://github.com/{path}"
