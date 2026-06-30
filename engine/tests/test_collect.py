"""SourceAdapter 协议 + GitHubAdapter + 查询扩展。

用录制的 GitHub API 响应离线跑（不连网）。
无 pytest 也可直接跑：python3 tests/test_collect.py
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from oss_search.models import IntentSpec, Constraints, Capability
from oss_search.collect import (
    SourceAdapter,
    GitHubAdapter,
    expand_queries,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _make_cap(index: int = 1, **kwargs) -> Capability:
    """快速构造一个合规 Capability。"""
    defaults = dict(
        id=f"cap-{index}",
        name=f"测试能力{index}",
        description="用于测试的能力",
        required=True,
        keywords_en=["full-text search", "vector search", "text search"],
        keywords_zh=["全文检索", "向量检索"],
        candidate_topics=["search", "elasticsearch"],
        candidate_packages=["meilisearch", "typesense"],
    )
    defaults.update(kwargs)
    return Capability(**defaults)


def _make_spec(caps: list = None) -> IntentSpec:
    return IntentSpec(
        original_request="测试需求",
        summary="测试用意图",
        constraints=Constraints(),
        capabilities=caps or [_make_cap(1), _make_cap(2, id="cap-2", name="测试2"), _make_cap(3, id="cap-3", name="测试3")],
    )


# ============ 1. 查询扩展 ============


class TestQueryExpansion(unittest.TestCase):
    def test_expands_keywords_and_topics(self):
        cap = _make_cap(1, keywords_en=["full-text search", "vector search"])
        queries = expand_queries(cap)
        # 应该有 topic:search + topic:elasticsearch + 纯关键词
        self.assertGreaterEqual(len(queries), 2, msg=f"一个能力应生成≥2条查询，实际：{len(queries)}")
        # 检查去重
        self.assertEqual(len(queries), len(set(queries)), msg="查询应去重")

    def test_no_query_sources_returns_empty(self):
        """keywords/topics/packages 全空才返回空列表。"""
        cap = _make_cap(1, keywords_en=[], keywords_zh=[], candidate_topics=[], candidate_packages=[])
        self.assertEqual(expand_queries(cap), [])

    def test_keywords_deduplicated(self):
        cap = _make_cap(1, keywords_en=["search", "SEARCH", "  search  "])
        queries = expand_queries(cap)
        # 去重后：1 条 keyword + topics 条数 + packages 条数
        expected = 1 + len(cap.candidate_topics) + len(cap.candidate_packages)
        self.assertEqual(len(queries), expected, msg=f"期望 {expected} 条，实际 {len(queries)}：{queries}")


# ============ 2. Candidate 契约 ============


class TestCandidateContract(unittest.TestCase):
    """验证 Candidate 结构完整性（不连网）。"""

    FULL_FIELDS = [
        "id", "source", "name", "full_name", "url", "description",
        "language", "license", "stars", "forks", "last_commit_at",
        "open_issues", "contributors", "topics", "readme_excerpt",
        "matched_capability", "raw",
    ]

    def test_all_fields_present_or_null(self):
        """用假数据构造 Candidate，验证字段齐全。"""
        from oss_search.models import Candidate
        adapter = GitHubAdapter()
        fake_item = {
            "full_name": "test/repo",
            "name": "repo",
            "html_url": "https://github.com/test/repo",
            "description": "A test repo",
            "language": "Python",
            "license": {"spdx_id": "MIT"},
            "stargazers_count": 100,
            "forks_count": 20,
            "pushed_at": "2026-06-01T00:00:00Z",
            "open_issues_count": 5,
            "topics": ["search"],
        }
        cand = adapter._to_candidate(fake_item, "cap-1")
        for field in self.FULL_FIELDS:
            self.assertTrue(
                hasattr(cand, field),
                msg=f"Candidate 缺少字段：{field}",
            )

    def test_missing_fields_are_null(self):
        """拿不到的数据填 null，不伪造。"""
        from oss_search.models import Candidate
        adapter = GitHubAdapter()
        fake_item = {
            "full_name": "bare/repo",
            "name": "repo",
            "html_url": "https://github.com/bare/repo",
            "description": None,
            "language": None,
            "license": None,
        }
        cand = adapter._to_candidate(fake_item, "cap-1")
        self.assertIsNone(cand.language)
        self.assertIsNone(cand.license)
        self.assertIsNone(cand.stars)
        self.assertIsNone(cand.contributors)  # search API 总是取不到


# ============ 3. SourceAdapter 协议 ============


class TestSourceAdapterProtocol(unittest.TestCase):
    def test_github_adapter_implements_protocol(self):
        """GitHubAdapter 满足 SourceAdapter 的结构要求。"""
        adapter = GitHubAdapter()
        self.assertEqual(adapter.name, "github")
        self.assertTrue(hasattr(adapter, "search"))
        self.assertTrue(callable(adapter.search))


# ============ 4. 集成测试（录制的响应） ============


class TestGitHubAdapterWithFixtures(unittest.TestCase):
    """用录制的 GitHub API 响应跑集成测试。"""

    @classmethod
    def setUpClass(cls):
        fixture_path = os.path.join(FIXTURES_DIR, "github_search.json")
        if not os.path.exists(fixture_path):
            raise unittest.SkipTest(f"fixture 不存在，先运行录制：{fixture_path}")
        with open(fixture_path, encoding="utf-8") as f:
            cls.fixture = json.load(f)

    def setUp(self):
        """构造一个注入假响应的适配器。"""
        self.adapter = _FakeGitHubAdapter(self.fixture)

    def test_search_returns_candidates(self):
        cap = _make_cap(1)
        spec = _make_spec()
        candidates = self.adapter.search(cap, spec)
        self.assertIsInstance(candidates, list)
        self.assertGreaterEqual(len(candidates), 10, msg="一个 capability 应返回 ≥10 条 Candidate")
        # 每条都符合结构
        for c in candidates:
            self.assertEqual(c.source, "github")
            self.assertTrue(c.id.startswith("github:"), msg=f"id 格式不对：{c.id}")
            self.assertEqual(c.matched_capability, "cap-1")

    def test_search_dedup_across_queries(self):
        """多条查询结果重复时去重。"""
        cap = _make_cap(1)
        spec = _make_spec()
        candidates = self.adapter.search(cap, spec)
        ids = [c.id for c in candidates]
        self.assertEqual(len(ids), len(set(ids)), msg="候选 ID 应唯一")


# ============ 5. 错误降级 ============


class TestErrorHandling(unittest.TestCase):
    def test_http_error_not_crashing(self):
        """单次 API 失败不崩，降级返回空列表。"""
        adapter = _BrokenAdapter()
        cap = _make_cap(1)
        spec = _make_spec()
        candidates = adapter.search(cap, spec)
        self.assertIsInstance(candidates, list)


# ============ 假适配器 ============


class _FakeGitHubAdapter(GitHubAdapter):
    """用录制的 fixture 替代真实 API 调用。返回所有 fixture items（不 exact-match URL）。"""

    def __init__(self, fixture: list):
        super().__init__()
        all_items = []
        for rec in fixture:
            body = rec.get("body", {})
            if isinstance(body, dict):
                all_items.extend(body.get("items", []))
        self._all_items = all_items

    def _search_repos(self, query: str, per_page: int = None) -> list:
        """返回 fixture 中所有 items（模拟多条查询的汇总）。"""
        return self._all_items


class _BrokenAdapter(GitHubAdapter):
    """模拟所有 API 调用失败。"""

    def _search_repos(self, query: str, per_page: int = None) -> list:
        raise OSError("模拟网络错误")


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
