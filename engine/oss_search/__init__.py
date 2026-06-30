"""开源意图搜索器 · 核心引擎

意图拆解 → 采集 → 归并 → 评级 → 报告。
本包不依赖任何 Skill / Claude 运行环境，可单独 `python -m` 运行（见 ADR-007）。
"""

__version__ = "0.1.0"

from .models import IntentSpec, Capability, Constraints, Candidate
from .intent import load_intent_spec, parse_intent
from .collect import SourceAdapter, GitHubAdapter, expand_queries
from .merge import dedup, normalize_repo_url
