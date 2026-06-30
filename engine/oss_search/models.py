"""核心数据结构。

对应《技术规范》§4 与《意图拆解Schema》。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ============ 意图拆解相关 ============

@dataclass
class Constraints:
    """需求约束。用户没明说的字段一律留空，不臆造。"""
    languages: List[str] = field(default_factory=list)
    license_allow: List[str] = field(default_factory=list)
    license_deny: List[str] = field(default_factory=list)
    self_host_required: bool = False
    deployment: str = ""

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "Constraints":
        d = d or {}
        return cls(
            languages=list(d.get("languages") or []),
            license_allow=list(d.get("license_allow") or []),
            license_deny=list(d.get("license_deny") or []),
            self_host_required=bool(d.get("self_host_required", False)),
            deployment=str(d.get("deployment") or ""),
        )


@dataclass
class Capability:
    """一个原子能力：可以独立去开源世界找方案的功能点。"""
    id: str
    name: str
    description: str = ""
    required: bool = True
    keywords_en: List[str] = field(default_factory=list)
    keywords_zh: List[str] = field(default_factory=list)
    candidate_topics: List[str] = field(default_factory=list)
    candidate_packages: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Capability":
        return cls(
            id=str(d.get("id") or "").strip(),
            name=str(d.get("name") or "").strip(),
            description=str(d.get("description") or ""),
            required=bool(d.get("required", True)),
            keywords_en=list(d.get("keywords_en") or []),
            keywords_zh=list(d.get("keywords_zh") or []),
            candidate_topics=list(d.get("candidate_topics") or []),
            candidate_packages=list(d.get("candidate_packages") or []),
        )

    def validate(self) -> List[str]:
        """返回错误列表，空列表表示合法（对应《意图拆解Schema》字段规则）。"""
        errs = []
        if not self.id:
            errs.append("capability.id 不能为空")
        if not self.name:
            errs.append(f"capability[{self.id}].name 不能为空")
        # 关键词数量：中/英各至少 2 个，供查询扩展层使用
        if len(self.keywords_en) < 2:
            errs.append(f"capability[{self.id or self.name}].keywords_en 至少 2 个（当前 {len(self.keywords_en)}）")
        if len(self.keywords_zh) < 2:
            errs.append(f"capability[{self.id or self.name}].keywords_zh 至少 2 个（当前 {len(self.keywords_zh)}）")
        return errs


@dataclass
class IntentSpec:
    """意图拆解的最终产物。"""
    original_request: str
    summary: str
    constraints: Constraints = field(default_factory=Constraints)
    capabilities: List[Capability] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict[str, Any], original_request: str = "") -> "IntentSpec":
        caps = [Capability.from_dict(c) for c in (d.get("capabilities") or [])]
        return cls(
            original_request=original_request or str(d.get("original_request") or ""),
            summary=str(d.get("summary") or ""),
            constraints=Constraints.from_dict(d.get("constraints")),
            capabilities=caps,
        )

    # 能力数量边界（对应《意图拆解Schema》：3-8 个原子能力）
    MIN_CAPABILITIES = 3
    MAX_CAPABILITIES = 8

    def validate(self) -> List[str]:
        """返回错误列表，空列表表示合法（对应 Schema §4 验收）。"""
        errs = []
        if not self.summary:
            errs.append("summary 不能为空")
        n = len(self.capabilities)
        if n < self.MIN_CAPABILITIES or n > self.MAX_CAPABILITIES:
            errs.append(
                f"capabilities 数量应为 {self.MIN_CAPABILITIES}-{self.MAX_CAPABILITIES} 项（当前 {n}）"
            )
        seen = set()
        seen_optional = False  # 一旦出现 required:false，后面不允许再出现 required:true
        for cap in self.capabilities:
            errs.extend(cap.validate())
            if cap.id in seen:
                errs.append(f"capability.id 重复：{cap.id}")
            seen.add(cap.id)
            if cap.required and seen_optional:
                errs.append(
                    f"capabilities 排序错误：必需能力 {cap.id} 出现在可选能力之后（required:true 须在前）"
                )
            if not cap.required:
                seen_optional = True
        return errs

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============ 采集 / 评级相关 ============

@dataclass
class Candidate:
    """采集层统一输出（《技术规范》§4.2）。"""
    id: str
    source: str
    name: str
    url: str
    full_name: str = ""
    description: str = ""
    language: Optional[str] = None
    license: Optional[str] = None
    stars: Optional[int] = None
    forks: Optional[int] = None
    last_commit_at: Optional[str] = None
    open_issues: Optional[int] = None
    contributors: Optional[int] = None
    topics: List[str] = field(default_factory=list)
    readme_excerpt: str = ""
    matched_capability: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


# ============ 评级相关 ============

@dataclass
class ScoredCandidate:
    """评级层输出（《技术规范》§4.3）。在 Candidate 基础上加评分。"""
    candidate: Candidate
    scores: Dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0
    grade: str = "D"
    reasons: List[str] = field(default_factory=list)

    # 评级阈值
    GRADES = {"A": 0.80, "B": 0.65, "C": 0.50}

    @classmethod
    def compute_grade(cls, total: float) -> str:
        for g, threshold in cls.GRADES.items():
            if total >= threshold:
                return g
        return "D"
