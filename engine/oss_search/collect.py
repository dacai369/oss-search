"""采集框架 + GitHub 适配器（TASK-002）。

定义可插拔 SourceAdapter 协议 + GitHubAdapter 实现：
- 查询扩展：每个 capability 的关键词 + topic 组合成多条去重查询
- 同步串行，限流退避重试
- 输出统一 Candidate（字段缺失填 null，不伪造）
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple

from .models import Candidate, IntentSpec, Capability

# ============ 协议 ============


class SourceAdapter(Protocol):
    """可插拔采集适配器（《技术规范》§5）。"""
    name: str  # 源标识，如 "github" / "npm" / "pypi"

    def search(self, capability: Capability, spec: IntentSpec) -> list[Candidate]:
        """按单个能力搜索，返回候选项目列表。"""
        ...


# ============ 查询扩展 ============


def expand_queries(cap: Capability) -> List[str]:
    """将一个能力的 keywords_en + candidate_topics 去重组合成查询列表。

    策略：
    1. 每个 topic 生成一条 topic: 限定查询（组合所有关键词）
    2. 无边 topic 时，用关键词直接查询
    返回去重后的查询字符串列表。
    """
    queries: List[str] = []
    seen: Set[str] = set()
    keywords = [k.strip().lower() for k in cap.keywords_en if k.strip()]

    if not keywords:
        return queries

    kw_joined = "+".join(keywords)

    # topic + 关键词组合查询
    for topic in cap.candidate_topics:
        t = topic.strip().lower()
        if not t:
            continue
        q = f"topic:{t}+{kw_joined}"
        if q not in seen:
            seen.add(q)
            queries.append(q)

    # 纯关键词查询
    if kw_joined not in seen:
        seen.add(kw_joined)
        queries.append(kw_joined)

    return queries


# ============ GitHub 适配器 ============


class GitHubAdapter:
    """GitHub 仓库搜索适配器。

    环境变量 GITHUB_TOKEN（可选）提升限流（60→5000 req/h）。
    限流: 读 X-RateLimit-* 头，429/403 时退避重试。
    """

    name = "github"
    BASE = "https://api.github.com"
    PER_PAGE = 30

    def __init__(
        self,
        token: str = "",
        max_retries: int = 2,
        record_path: Optional[str] = None,
    ):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.max_retries = max_retries
        # 录制模式：存响应到文件供离线测试
        self._record_path = record_path
        self._recorded: List[Dict] = []

    # ---------- 公开接口 ----------

    def search(self, capability: Capability, spec: IntentSpec) -> List[Candidate]:
        """对单个能力做查询扩展 → 逐条搜 GitHub → 汇总去重 Candidate。"""
        queries = expand_queries(capability)
        if not queries:
            return []

        seen_ids: Set[str] = set()
        candidates: List[Candidate] = []

        for q in queries:
            try:
                results = self._search_repos(q)
            except Exception:
                # 单次查询失败降级跳过，不崩
                results = []
            for item in results:
                cand = self._to_candidate(item, capability.id)
                if cand.id not in seen_ids:
                    seen_ids.add(cand.id)
                    candidates.append(cand)
            time.sleep(0.7)  # 请求间隔，降低限流压力

        return candidates

    # ---------- API ----------

    def _search_repos(self, query: str, per_page: int = None) -> List[Dict]:
        """GET /search/repositories，返回 items 列表。"""
        params = {"q": query, "sort": "stars", "order": "desc", "per_page": per_page or self.PER_PAGE}
        url = f"{self.BASE}/search/repositories?{urllib.parse.urlencode(params)}"
        return self._get_json(url)

    # ---------- HTTP ----------

    def _get_json(self, url: str, retry: int = 0) -> List[Dict]:
        """GET 一个 GitHub API URL，返回 JSON 主体。限流/网络错误时退避重试。"""
        req = urllib.request.Request(url, headers=self._headers())

        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    self._check_rate_limit(resp)
                    raw = resp.read().decode("utf-8")
                    data = json.loads(raw)

                    # 录制
                    if self._record_path is not None:
                        self._recorded.append({"url": url, "status": resp.status, "body": data})

                    # GitHub search 返回 {total_count, items, ...}
                    return data.get("items", []) if isinstance(data, dict) else []

            except urllib.error.HTTPError as e:
                if e.code in (403, 429):
                    if attempt < self.max_retries:
                        wait = self._retry_after(e) or (2 ** attempt * 2)
                        time.sleep(wait)
                        continue
                    # 最后一次也失败则降级返回空列表，不崩
                return []
            except (urllib.error.URLError, json.JSONDecodeError, OSError):
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt * 2)
                    continue
                return []

        return []

    def _headers(self) -> Dict[str, str]:
        h = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "oss-search/0.1",
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _check_rate_limit(self, resp) -> None:
        """检查 X-RateLimit-Remaining，接近 0 时休眠等待。"""
        remaining = resp.headers.get("X-RateLimit-Remaining")
        if remaining is not None and int(remaining) < 5:
            reset = int(resp.headers.get("X-RateLimit-Reset", 0))
            now = int(time.time())
            wait = max(reset - now, 0) + 2
            if wait > 0:
                time.sleep(wait)

    def _retry_after(self, err: urllib.error.HTTPError) -> Optional[float]:
        """从 Retry-After 头读取等待秒数。"""
        raw = err.headers.get("Retry-After", "")
        if raw.isdigit():
            return float(raw) + 1
        return None

    # ---------- 映射 ----------

    def _to_candidate(self, item: Dict[str, Any], capability_id: str) -> Candidate:
        """将 GitHub API 返回的一项映射为统一 Candidate。缺失字段填 null，不伪造。"""
        lic = item.get("license") or {}
        return Candidate(
            id=f"github:{item.get('full_name', '')}",
            source="github",
            name=item.get("name", ""),
            full_name=item.get("full_name", ""),
            url=item.get("html_url", ""),
            description=item.get("description") or "",
            language=item.get("language"),
            license=lic.get("spdx_id"),
            stars=item.get("stargazers_count"),
            forks=item.get("forks_count"),
            last_commit_at=item.get("pushed_at"),
            open_issues=item.get("open_issues_count"),
            contributors=None,  # search API 不含，需另调 repo 接口
            topics=item.get("topics") or [],
            readme_excerpt=item.get("description") or "",
            matched_capability=capability_id,
            raw=item,
        )

    def flush_recording(self):
        """保存录制数据到文件。"""
        if self._record_path and self._recorded:
            os.makedirs(os.path.dirname(self._record_path), exist_ok=True)
            with open(self._record_path, "w", encoding="utf-8") as f:
                json.dump(self._recorded, f, ensure_ascii=False, indent=2)
            self._recorded.clear()
