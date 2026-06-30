"""TASK-003 验收测试：npm + PyPI 适配器。

用录制的 API 响应离线跑。
无 pytest 也可直接跑：python3 tests/test_adapters.py
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from oss_search.models import Capability, IntentSpec, Constraints
from oss_search.adapters import (
    NpmAdapter, PypiAdapter,
    _extract_repo_from_npm, _extract_repo_from_pypi, _normalize_github_url,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture():
    path = os.path.join(FIXTURES_DIR, "npm_pypi_fixtures.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _search_cap(**kwargs) -> Capability:
    defaults = dict(
        id="cap-1", name="全文检索",
        description="搜索引擎",
        keywords_en=["full-text search", "search engine"],
        keywords_zh=["全文检索"],
        candidate_packages=["elasticsearch", "meilisearch", "typesense"],
    )
    defaults.update(kwargs)
    return Capability(**defaults)


def _spec() -> IntentSpec:
    return IntentSpec(
        original_request="搜索",
        summary="搜索",
        constraints=Constraints(),
        capabilities=[_search_cap()],
    )


# ============ URL 提取 ============


class TestRepoExtraction(unittest.TestCase):
    def test_github_url_normalization(self):
        cases = [
            ("https://github.com/org/repo", "https://github.com/org/repo"),
            ("https://github.com/org/repo.git", "https://github.com/org/repo"),
            ("https://github.com/ORG/Repo/", "https://github.com/ORG/Repo"),
            ("http://github.com/a/b", "https://github.com/a/b"),
            ("git+https://github.com/a/b.git", "https://github.com/a/b"),
            ("not a github url", ""),
            ("", ""),
        ]
        for inp, expected in cases:
            self.assertEqual(
                _normalize_github_url(inp), expected,
                msg=f"input={inp!r}",
            )

    def test_extract_from_npm_package(self):
        """用真实录制的 npm 包验证仓库提取。"""
        fixture = _load_fixture()
        if not fixture:
            raise unittest.SkipTest("fixture 不存在")
        # 应该至少有一个包能提取出 GitHub URL
        found = 0
        for qr in fixture.get("npm_search", []):
            for obj in qr.get("objects", []):
                url = _extract_repo_from_npm(obj.get("package", obj))
                if url:
                    found += 1
        self.assertGreater(found, 0, msg="npm 搜索结果中应至少有一个提取出 GitHub URL")

    def test_extract_from_pypi_package(self):
        fixture = _load_fixture()
        if not fixture:
            raise unittest.SkipTest("fixture 不存在")
        found = 0
        for name, info in fixture.get("pypi_packages", {}).items():
            url = _extract_repo_from_pypi(info)
            if url:
                found += 1
        self.assertGreater(found, 0, msg="PyPI 包中应至少有一个提取出 GitHub URL")


# ============ npm 适配器（用 fixture）============


class TestNpmAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = _load_fixture()
        if not fixture:
            raise unittest.SkipTest("fixture 不存在")
        cls.fixture = fixture

    def test_implements_protocol(self):
        adapter = NpmAdapter()
        self.assertEqual(adapter.name, "npm")
        self.assertTrue(callable(adapter.search))

    def test_search_returns_candidates(self):
        adapter = _FakeNpmAdapter(self.fixture)
        cap = _search_cap()
        results = adapter.search(cap, _spec())
        self.assertIsInstance(results, list)
        for c in results:
            self.assertEqual(c.source, "npm")
            self.assertTrue(c.id.startswith("npm:"), msg=f"id 格式不对：{c.id}")

    def test_no_packages_returns_empty(self):
        adapter = _FakeNpmAdapter(self.fixture)
        cap = _search_cap(candidate_packages=[], keywords_en=[])
        results = adapter.search(cap, _spec())
        self.assertEqual(results, [])


# ============ PyPI 适配器（用 fixture）============


class TestPypiAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = _load_fixture()
        if not fixture:
            raise unittest.SkipTest("fixture 不存在")
        cls.fixture = fixture

    def test_implements_protocol(self):
        adapter = PypiAdapter()
        self.assertEqual(adapter.name, "pypi")
        self.assertTrue(callable(adapter.search))

    def test_search_returns_candidates(self):
        adapter = _FakePypiAdapter(self.fixture)
        cap = _search_cap()
        results = adapter.search(cap, _spec())
        self.assertIsInstance(results, list)
        for c in results:
            self.assertEqual(c.source, "pypi")
            self.assertTrue(c.id.startswith("pypi:"))

    def test_nonexistent_package_skipped(self):
        adapter = _FakePypiAdapter(self.fixture)
        cap = _search_cap(candidate_packages=["this-pkg-does-not-exist-xyz"])
        results = adapter.search(cap, _spec())
        self.assertEqual(results, [])


# ============ 假适配器 ============


class _FakeNpmAdapter(NpmAdapter):
    def __init__(self, fixture: dict):
        super().__init__()
        all_objects = []
        for qr in fixture.get("npm_search", []):
            all_objects.extend(qr.get("objects", []))
        self._all_objects = all_objects

    def _search(self, query: str) -> list:
        return self._all_objects


class _FakePypiAdapter(PypiAdapter):
    def __init__(self, fixture: dict):
        super().__init__()
        self._pkgs = fixture.get("pypi_packages", {})

    def _get_package(self, name: str) -> dict:
        info = self._pkgs.get(name)
        if not info:
            return None
        return {"info": info}


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
