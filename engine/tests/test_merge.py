"""归并去重 · 实体对齐。

无 pytest 也可直接跑：python3 tests/test_merge.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from oss_search.models import Candidate
from oss_search.merge import dedup, normalize_repo_url


def _c(**kwargs) -> Candidate:
    """快速构造 Candidate。"""
    defaults = dict(
        id="github:test/repo",
        source="github",
        name="repo",
        full_name="test/repo",
        url="https://github.com/test/repo",
        description="",
        language=None,
        license=None,
        stars=None,
        forks=None,
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


# ============ 1. URL 规范化 ============


class TestNormalizeRepoUrl(unittest.TestCase):
    def test_strips_protocol(self):
        self.assertEqual(
            normalize_repo_url("https://github.com/a/b"),
            "github.com/a/b",
        )

    def test_strips_www(self):
        self.assertEqual(
            normalize_repo_url("https://www.github.com/a/b"),
            "github.com/a/b",
        )

    def test_strips_trailing_slash(self):
        self.assertEqual(
            normalize_repo_url("https://github.com/a/b/"),
            "github.com/a/b",
        )

    def test_strips_dot_git(self):
        self.assertEqual(
            normalize_repo_url("https://github.com/a/b.git"),
            "github.com/a/b",
        )

    def test_case_insensitive(self):
        self.assertEqual(
            normalize_repo_url("https://GITHUB.COM/Owner/Repo"),
            "github.com/owner/repo",
        )

    def test_strips_extra_path(self):
        """/issues, /tree/main 等非 repo 路径应被去除。"""
        self.assertEqual(
            normalize_repo_url("https://github.com/a/b/issues"),
            "github.com/a/b",
        )
        self.assertEqual(
            normalize_repo_url("https://github.com/a/b/tree/main/src"),
            "github.com/a/b",
        )

    def test_empty_url(self):
        self.assertEqual(normalize_repo_url(""), "")

    def test_non_github_url(self):
        self.assertEqual(
            normalize_repo_url("https://gitlab.com/org/proj"),
            "gitlab.com/org/proj",
        )


# ============ 2. 去重与合并 ============


class TestDedup(unittest.TestCase):
    def test_single_candidate_untouched(self):
        c = _c(id="github:a/b", stars=100)
        result = dedup([c])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].stars, 100)
        self.assertEqual(result[0].raw.get("sources"), ["github"])

    def test_same_url_merged(self):
        """同 URL 的两条 Candidate 应合并为 1 条。"""
        c1 = _c(id="github:a/b", url="https://github.com/a/b", stars=100, language="Python")
        c2 = _c(id="github:a/b", url="https://github.com/a/b", stars=200, license="MIT")
        result = dedup([c1, c2])
        self.assertEqual(len(result), 1, msg="同 URL 应合并为 1 条")
        merged = result[0]
        # 取 max stars
        self.assertEqual(merged.stars, 200)
        # 保留 language
        self.assertEqual(merged.language, "Python")
        # 填补 license
        self.assertEqual(merged.license, "MIT")
        # sources 记录两个来源（此时都是 github）
        self.assertIn("github", merged.raw["sources"])

    def test_url_variants_merged(self):
        """不同写法但同一仓库的 URL 应合并。"""
        c1 = _c(id="github:a/b", url="https://github.com/a/b.git", stars=100)
        c2 = _c(id="github:a/b", url="https://github.com/a/b/", forks=20)
        result = dedup([c1, c2])
        self.assertEqual(len(result), 1, msg="URL 变体应合并")

    def test_different_repos_not_merged(self):
        """不同仓库不应合并。"""
        c1 = _c(id="github:a/b", url="https://github.com/a/b", stars=100)
        c2 = _c(id="github:c/d", url="https://github.com/c/d", stars=50)
        result = dedup([c1, c2])
        self.assertEqual(len(result), 2)

    def test_no_url_fallback_to_fullname(self):
        """无有效 URL 时回退到 full_name。"""
        c1 = _c(id="github:X/Y", url="", full_name="X/Y", stars=100)
        c2 = _c(id="github:X/Y", url="", full_name="X/Y", forks=5)
        result = dedup([c1, c2])
        self.assertEqual(len(result), 1, msg="同 full_name 应合并")

    def test_cross_source_merge(self):
        """跨源（github + npm）指向同一仓库应合并。"""
        c1 = _c(id="github:a/b", source="github", url="https://github.com/a/b", stars=300)
        c2 = _c(id="npm:pkg-x", source="npm", url="https://github.com/a/b", stars=500)
        result = dedup([c1, c2])
        self.assertEqual(len(result), 1, msg="跨源同仓库应合并")
        merged = result[0]
        # sources 包含两个源
        self.assertEqual(set(merged.raw["sources"]), {"github", "npm"})
        # source_count
        self.assertEqual(merged.raw.get("source_count"), 2)
        # merged_from
        self.assertEqual(merged.raw.get("merged_from"), 2)

    def test_non_repo_candidates_kept_separate(self):
        """无仓库 URL 且 full_name 不同的候选各自保留。"""
        c1 = _c(id="a:1", url="", full_name="")
        c2 = _c(id="b:2", url="", full_name="")
        result = dedup([c1, c2])
        self.assertEqual(len(result), 2, msg="无 key 候选应各自独立")

    def test_source_count(self):
        """验证 source_count 正确记录。"""
        c1 = _c(id="github:a/b", source="github", url="https://github.com/a/b")
        c2 = _c(id="npm:a/b", source="npm", url="https://github.com/a/b")
        c3 = _c(id="content:1", source="content", url="https://github.com/a/b")
        result = dedup([c1, c2, c3])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].raw["source_count"], 3)
        self.assertEqual(result[0].raw["merged_from"], 3)


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
