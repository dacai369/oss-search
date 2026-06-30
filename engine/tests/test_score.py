"""TASK-006 验收测试：质量评级引擎。

无 pytest 也可直接跑：python3 tests/test_score.py
"""

import sys
import os
import unittest
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from oss_search.models import (
    Candidate, IntentSpec, Constraints, Capability, ScoredCandidate,
)
from oss_search.score import (
    score, DEFAULT_WEIGHTS,
    _relevance, _activity, _community, _maturity, _license_fit, _security,
)


# ============ helpers ============


def _c(**kwargs) -> Candidate:
    """高星项目（默认优质样本）。"""
    defaults = dict(
        id="github:elastic/elasticsearch",
        source="github",
        name="elasticsearch",
        full_name="elastic/elasticsearch",
        url="https://github.com/elastic/elasticsearch",
        description="Free and Open Source, Distributed, RESTful Search Engine",
        language="Java",
        license="Apache-2.0",
        stars=75000,
        forks=25000,
        last_commit_at="2026-06-29T12:00:00Z",
        open_issues=300,
        contributors=2500,
        topics=["search", "elasticsearch", "full-text-search", "analytics", "distributed"],
        readme_excerpt="Elasticsearch is a distributed, RESTful search and analytics engine...",
        matched_capability="cap-1",
        raw={},
    )
    defaults.update(kwargs)
    return Candidate(**defaults)


def _low_c(**kwargs) -> Candidate:
    """低质量项目。"""
    defaults = dict(
        id="github:newbie/test",
        source="github",
        name="test",
        full_name="newbie/test",
        url="https://github.com/newbie/test",
        description="just a test",
        language=None,
        license=None,
        stars=0,
        forks=0,
        last_commit_at=None,
        open_issues=None,
        contributors=None,
        topics=[],
        readme_excerpt="",
        matched_capability="cap-1",
        raw={},
    )
    defaults.update(kwargs)
    return Candidate(**defaults)


def _spec(**kwargs) -> IntentSpec:
    """搜索需求 IntentSpec。"""
    caps = [
        Capability(
            id="cap-1", name="全文检索",
            description="分布式全文搜索引擎，支持 RESTful API",
            keywords_en=["full-text search", "search engine", "distributed search"],
            keywords_zh=["全文检索", "搜索引擎"],
            candidate_topics=["search", "elasticsearch"],
        ),
        Capability(
            id="cap-2", name="向量检索",
            description="向量相似度搜索",
            keywords_en=["vector search", "embedding search", "ANN"],
            keywords_zh=["向量检索"],
        ),
        Capability(
            id="cap-3", name="数据分析",
            description="数据聚合分析",
            keywords_en=["analytics", "aggregation", "data analysis"],
            keywords_zh=["数据分析"],
        ),
    ]
    return IntentSpec(
        original_request="需要一个开源的分布式搜索引擎",
        summary="分布式搜索引擎",
        constraints=Constraints(**kwargs),
        capabilities=caps,
    )


# ============ 1. 结构验证 ============


class TestScoredCandidateStructure(unittest.TestCase):
    def test_output_is_scored_candidate(self):
        result = score([_c()], _spec())
        self.assertEqual(len(result), 1)
        sc = result[0]
        self.assertIsInstance(sc, ScoredCandidate)
        self.assertIsInstance(sc.candidate, Candidate)

    def test_all_six_dimensions_present(self):
        result = score([_c()], _spec())
        dims = result[0].scores
        for key in DEFAULT_WEIGHTS:
            self.assertIn(key, dims, msg=f"缺少维度：{key}")
            self.assertIsInstance(dims[key], float)

    def test_total_score_in_range(self):
        result = score([_c()], _spec())
        for sc in result:
            self.assertGreaterEqual(sc.total_score, 0.0)
            self.assertLessEqual(sc.total_score, 1.0)

    def test_grade_mapping(self):
        tests = [
            (0.85, "A"), (0.80, "A"), (0.79, "B"),
            (0.65, "B"), (0.64, "C"), (0.50, "C"), (0.49, "D"), (0.0, "D"),
        ]
        for val, expected in tests:
            self.assertEqual(
                ScoredCandidate.compute_grade(val), expected,
                msg=f"总分 {val} 应对应 {expected}",
            )

    def test_at_least_three_reasons(self):
        candidates = [_c(), _low_c()]
        result = score(candidates, _spec())
        for sc in result:
            self.assertGreaterEqual(
                len(sc.reasons), 3,
                msg=f"{sc.candidate.name} 仅 {len(sc.reasons)} 条理由",
            )


# ============ 2. 排序 ============


class TestSorting(unittest.TestCase):
    def test_high_quality_ranks_above_low(self):
        """高分项目应排在低分项目前面。"""
        high = _c()
        low = _low_c()
        result = score([low, high], _spec())  # 故意乱序输入
        self.assertEqual(result[0].candidate.id, high.id, msg="高分项目应排第一")

    def test_sort_descending(self):
        result = score([_c(), _low_c()], _spec())
        for i in range(len(result) - 1):
            self.assertGreaterEqual(
                result[i].total_score, result[i + 1].total_score,
                msg=f"排序错误：{result[i].total_score} < {result[i+1].total_score}",
            )


# ============ 3. 可配置权重 ============


class TestCustomWeights(unittest.TestCase):
    def test_default_weights(self):
        result_default = score([_c()], _spec()).pop()
        self.assertEqual(sum(DEFAULT_WEIGHTS.values()), 1.0)  # 权重归一校验

    def test_custom_weights(self):
        """自定义权重应影响总分。"""
        # 只含 activity 的权重
        custom = {"activity": 1.0}
        result = score([_c(), _low_c()], _spec(), weights=custom)
        # activity 维度高的应排前面
        self.assertGreater(result[0].candidate.stars, 0, msg="active 项目应排前")

    def test_weight_affects_score(self):
        default = score([_c()], _spec())[0].total_score
        # 把所有权重都给 relevance，总分变化
        result = score([_c()], _spec(), weights={"relevance": 1.0})
        self.assertNotEqual(default, result[0].total_score, msg="权重变化应影响总分")


# ============ 4. 缺失字段降权（不崩溃）============


class TestNullSafety(unittest.TestCase):
    def test_all_null_fields(self):
        """全 null 项目不崩，给低分。"""
        empty = _low_c()
        result = score([empty], _spec())
        self.assertEqual(len(result), 1)
        self.assertLess(result[0].total_score, 0.5, msg="全 null 项目应低分")
        self.assertEqual(result[0].grade, "D")

    def test_empty_candidates_list(self):
        result = score([], _spec())
        self.assertEqual(result, [])


# ============ 5. 维度分测 ============


class TestRelevance(unittest.TestCase):
    def test_exact_match_high(self):
        """描述匹配度高→relevance 分高。"""
        cand = _c(description="Full-text search, distributed, RESTful search engine")
        spec = _spec()
        query = " ".join(
            f"{c.name} {c.description} " + " ".join(c.keywords_en)
            for c in spec.capabilities
        )
        texts = [cand.description]
        s, reason = _relevance(cand, query, texts, [cand])
        self.assertGreater(s, 0.3, msg=f"匹配度应较高，实际 {s}")

    def test_no_description_zero(self):
        cand = _c(description="", readme_excerpt="")
        spec = _spec()
        query = "search"
        s, _ = _relevance(cand, query, ["other"], [cand])
        self.assertEqual(s, 0.0)

    def test_irrelevant_low(self):
        cand = _c(description="A game engine written in C++", readme_excerpt="")
        spec = _spec()
        query = " ".join(
            f"{c.name} {c.description} " + " ".join(c.keywords_en)
            for c in spec.capabilities
        )
        texts = [cand.description]
        s, _ = _relevance(cand, query, texts, [cand])
        self.assertLess(s, 0.3, msg=f"不相关应低分，实际 {s}")


class TestActivity(unittest.TestCase):
    def test_recent_commit_high(self):
        cand = _c(last_commit_at="2026-06-28T00:00:00Z")
        s, reason = _activity(cand)
        self.assertGreater(s, 0.7, msg=f"近期提交应高分，实际 {s}")
        self.assertIn("活跃", reason)

    def test_old_commit_low(self):
        old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        cand = _c(last_commit_at=old)
        s, _ = _activity(cand)
        self.assertLess(s, 0.3, msg=f"旧提交应低分，实际 {s}")

    def test_no_commit_data_neutral(self):
        cand = _c(last_commit_at=None)
        s, _ = _activity(cand)
        self.assertEqual(s, 0.35, msg="无数据应给中性分 0.35")


class TestCommunity(unittest.TestCase):
    def test_high_stars_high(self):
        s, reason = _community(_c(stars=50000, forks=10000))
        self.assertGreater(s, 0.8, msg=f"高星应高分，实际 {s}")

    def test_zero_stars_low(self):
        s, reason = _community(_c(stars=0))
        self.assertEqual(s, 0.1)

    def test_multi_source_bonus(self):
        c = _c(stars=1000, raw={"source_count": 3})
        s, _ = _community(c)
        self.assertGreater(s, _community(_c(stars=1000))[0], msg="多源应有加分")


class TestMaturity(unittest.TestCase):
    def test_full_metadata_high(self):
        s, _ = _maturity(_c())
        self.assertGreater(s, 0.6, msg=f"完整元数据应高分，实际 {s}")

    def test_bare_project_low(self):
        s, _ = _maturity(_low_c())
        self.assertEqual(s, 0.3, msg="裸项目应仅基础分 0.3")


class TestLicenseFit(unittest.TestCase):
    def test_matches_allow(self):
        spec = _spec(license_allow=["Apache-2.0"])
        s, _ = _license_fit(_c(license="Apache-2.0"), spec)
        self.assertEqual(s, 1.0)

    def test_deny_blocks(self):
        spec = _spec(license_deny=["GPL-3.0"])
        s, _ = _license_fit(_c(license="GPL-3.0"), spec)
        self.assertEqual(s, 0.0, msg="GPL 应在 deny 列表里被阻")

    def test_no_license_neutral(self):
        s, _ = _license_fit(_c(license=None), _spec())
        self.assertEqual(s, 0.5)

    def test_no_constraints_full(self):
        s, _ = _license_fit(_c(license="MIT"), _spec())
        self.assertEqual(s, 1.0)


class TestSecurity(unittest.TestCase):
    def test_mvp_placeholder(self):
        s, _ = _security(_c())
        self.assertEqual(s, 0.5, msg="MVP 占位应固定 0.5")


# ============ runner ============


def _run_all():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in sorted(globals()):
        obj = globals()[name]
        if isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj is not unittest.TestCase:
            suite.addTests(loader.loadTestsFromTestCase(obj))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(_run_all())
