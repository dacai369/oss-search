"""质量评级引擎（TASK-006）。

多维打分 + 加权汇总 + 评级 + 人话理由。
- 维度与权重见《技术规范》§6，MVP 初版可配置。
- relevance 用 BM25 降级（ADR-006），V2 上 embedding。
- 缺失字段降权而非报错。
"""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import Candidate, IntentSpec, ScoredCandidate

# ============ 权重配置（可按需调整）============

DEFAULT_WEIGHTS = {
    "relevance": 0.30,
    "activity": 0.20,
    "community": 0.15,
    "maturity": 0.15,
    "license_fit": 0.10,
    "security": 0.10,
}


def score(
    candidates: List[Candidate],
    spec: IntentSpec,
    weights: Optional[Dict[str, float]] = None,
) -> List[ScoredCandidate]:
    """主入口：批量打分排序。"""
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)

    # 收集所有文本用于 IDF
    all_texts = [(c.description or "") + " " + (c.readme_excerpt or "") for c in candidates]

    # 按能力 id 建立查询文本（per-capability relevance，避免全部合并稀释信号）
    cap_query_map: Dict[str, str] = {}
    candidate_pkg_set: set = set()
    for c in spec.capabilities:
        cap_query_map[c.id] = " ".join(
            [c.name, c.description or ""] + c.keywords_en + c.keywords_zh
        )
        for pkg in c.candidate_packages:
            candidate_pkg_set.add(pkg.lower().replace("-", "_").replace(".", "_"))

    fallback_query = " ".join(cap_query_map.values())

    scored = []
    for cand in candidates:
        dims = {}
        reasons = []

        cap_query = cap_query_map.get(cand.matched_capability or "", fallback_query)
        dims["relevance"], r_rel = _relevance(cand, cap_query, all_texts, candidates, candidate_pkg_set)
        reasons.append(r_rel)

        dims["activity"], r_act = _activity(cand)
        reasons.append(r_act)

        dims["community"], r_com = _community(cand)
        reasons.append(r_com)

        dims["maturity"], r_mat = _maturity(cand)
        reasons.append(r_mat)

        dims["license_fit"], r_lic = _license_fit(cand, spec)
        reasons.append(r_lic)

        dims["security"], r_sec = _security(cand)
        reasons.append(r_sec)

        total = sum(dims[k] * w.get(k, 0) for k in dims)
        grade = ScoredCandidate.compute_grade(total)

        scored.append(ScoredCandidate(
            candidate=cand,
            scores=dims,
            total_score=round(total, 4),
            grade=grade,
            reasons=reasons,
        ))

    scored.sort(key=lambda s: s.total_score, reverse=True)
    return scored


# ============ 维度计算 ============


def _relevance(
    cand: Candidate, query: str, all_texts: List[str], candidates: List[Candidate],
    candidate_pkg_set: Optional[set] = None,
) -> tuple:
    """BM25 简易实现（ADR-006：MVP 降级）。"""
    # candidate_packages 直接命中：用户明确指定的候选包，跳过 BM25 直接给高分
    if candidate_pkg_set:
        name_key = (cand.name or "").lower().replace("-", "_").replace(".", "_")
        for pkg in candidate_pkg_set:
            if pkg and (pkg in name_key or name_key in pkg):
                return 0.85, "明确指定的候选包，契合度极高"

    doc = (cand.description or "") + " " + (cand.readme_excerpt or "")
    if not doc.strip():
        return 0.0, "缺少项目描述，无法评估契合度"

    tokens = _tokenize(doc)
    query_tokens = _tokenize(query)

    if not query_tokens or not tokens:
        return 0.0, "文本不足，无法计算契合度"

    # IDF（简化：在所有候选文本中算）
    N = max(len(all_texts), 1)
    tokenized_all = [_tokenize(t) for t in all_texts]
    doc_freq = Counter()
    for tks in tokenized_all:
        doc_freq.update(set(tks))

    k1, b = 1.2, 0.75
    avg_dl = sum(len(tks) for tks in tokenized_all) / max(N, 1)
    dl = len(tokens)

    bm25 = 0.0
    tf = Counter(tokens)
    for qt in query_tokens:
        df = doc_freq.get(qt, 0)
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
        term_tf = tf.get(qt, 0)
        numerator = term_tf * (k1 + 1)
        denominator = term_tf + k1 * (1 - b + b * dl / max(avg_dl, 1))
        bm25 += idf * (numerator / max(denominator, 0.001))

    # 归一化到 [0,1]
    score = min(bm25 / 10.0, 1.0)

    # 人话理由
    if score >= 0.6:
        reason = "功能契合度高：项目描述与需求匹配良好"
    elif score >= 0.3:
        reason = "功能基本匹配：描述涉及相关领域，但未精确命中"
    else:
        reason = "契合度低：项目描述与需求关联弱"

    return round(score, 4), reason


def _activity(cand: Candidate) -> tuple:
    """活跃度：近90天提交越近分越高。拿不到数据给中性分。"""
    if not cand.last_commit_at:
        return 0.35, "无提交数据，活跃度未知"

    try:
        last = datetime.fromisoformat(cand.last_commit_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days = (now - last).days
    except (ValueError, AttributeError):
        return 0.35, "无法解析提交时间"

    if days <= 30:
        score = 0.9
        reason = f"近期活跃（{days}天内有提交）"
    elif days <= 90:
        score = 0.7
        reason = f"近{days}天内有提交，维护正常"
    elif days <= 180:
        score = 0.5
        reason = f"近{days}天内有提交，更新频率偏低"
    elif days <= 365:
        score = 0.3
        reason = f"距今{days}天，可能维护放缓"
    else:
        score = 0.1
        reason = f"距今{days}天，疑似停滞"

    # issue 响应速度作为补充信号
    if cand.open_issues is not None and cand.stars and cand.stars > 0:
        ratio = cand.open_issues / cand.stars
        if ratio < 0.01:
            score = min(score + 0.05, 1.0)
        elif ratio > 0.1:
            score = max(score - 0.05, 0.0)

    return round(score, 4), reason


def _community(cand: Candidate) -> tuple:
    """社区规模：stars/forks/contributors。"""
    stars = cand.stars
    forks = cand.forks or 0

    # npm/PyPI 包没有 star 数据，给中性分而非惩罚分
    if stars is None:
        return 0.5, "无 star 数据（npm/PyPI 包），社区规模未知"

    if stars == 0:
        return 0.1, "社区极小（0 star）"

    # 对数缩放
    star_score = min(math.log10(stars + 1) / math.log10(50001), 1.0)  # 5万星→1.0
    fork_score = min(math.log10(forks + 1) / math.log10(10001), 1.0)

    score = star_score * 0.6 + fork_score * 0.4

    # 被多源提及加权（来自归并的 raw.sources）
    extra_signals = cand.raw.get("source_count", 1)
    if extra_signals >= 3:
        score = min(score + 0.1, 1.0)
    elif extra_signals >= 2:
        score = min(score + 0.05, 1.0)

    if stars >= 10000:
        reason = f"社区活跃（{stars:,} ⭐）"
    elif stars >= 1000:
        reason = f"有一定社区基础（{stars:,} ⭐，{forks:,} fork）"
    elif stars >= 100:
        reason = f"社区规模中等（{stars:,} ⭐）"
    else:
        reason = f"社区较小（{stars:,} ⭐）"

    if extra_signals > 1:
        reason += f"，被{extra_signals}个源提及"

    return round(score, 4), reason


def _maturity(cand: Candidate) -> tuple:
    """成熟度：描述质量、license、stars 作为文档存在性的粗略代理。"""
    score = 0.3  # 基础分
    signals = []

    if cand.license:
        score += 0.15
        signals.append("有明确许可证")

    desc_len = len(cand.description or "")
    topics_count = len(cand.topics or [])
    if desc_len > 80:
        score += 0.15
        signals.append("描述详细")
    elif desc_len > 20:
        score += 0.08
    if topics_count >= 5:
        score += 0.10
        signals.append(f"标签齐全（{topics_count}个）")

    # README 有内容
    if cand.readme_excerpt and len(cand.readme_excerpt) > 50:
        score += 0.15
        signals.append("有README")

    # stars 作为"使用验证"代理
    if cand.stars and cand.stars >= 500:
        score += 0.10
    elif cand.stars and cand.stars >= 50:
        score += 0.05

    score = min(score, 1.0)

    if signals:
        reason = "项目成熟度较好：" + "，".join(signals)
    elif score > 0.3:
        reason = "有一定成熟度（有基础文档/许可证）"
    else:
        reason = "成熟度证据不足"

    return round(score, 4), reason


def _license_fit(cand: Candidate, spec: IntentSpec) -> tuple:
    """许可证适配。"""
    lic = (cand.license or "").strip()

    if not lic:
        return 0.5, "未声明许可证，需自行确认"

    constr = spec.constraints

    # deny 优先级最高
    for deny in constr.license_deny:
        if _license_matches(lic, deny):
            return 0.0, f"许可证 {lic} 在排除列表中（{deny}），不推荐"

    # allow 空 = 不限制
    if not constr.license_allow:
        return 1.0, f"许可证 {lic}，无约束冲突"
    for allow in constr.license_allow:
        if _license_matches(lic, allow):
            return 1.0, f"许可证 {lic} 符合要求"

    return 0.6, f"许可证 {lic} 不在首选列表中"


def _security(_cand: Candidate) -> tuple:
    """安全评分（MVP 占位，V2 接 OSV/CVE）。"""
    return 0.5, "安全评估待接入（MVP 无 CVE 扫描）"


def _license_matches(actual: str, target: str) -> bool:
    """宽松匹配：Apache-2.0 ≈ Apache 2.0。"""
    a = actual.lower().replace("-", " ").replace("_", " ").split()
    t = target.lower().replace("-", " ").replace("_", " ").split()
    return a == t or target.lower() in actual.lower() or actual.lower() in target.lower()


_tokenizer_re = re.compile(r"[a-zA-Z0-9\u4e00-\u9fff]+")


def _tokenize(text: str) -> List[str]:
    """简易分词：中英文混合，保留连续字母/数字/中文。"""
    return [t.lower() for t in _tokenizer_re.findall(text) if len(t) > 1]
