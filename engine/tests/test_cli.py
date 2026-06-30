"""TASK-008 验收测试：CLI 端到端串联。

无 pytest 也可直接跑：python3 tests/test_cli.py
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from oss_search.__main__ import build_parser, main
from oss_search.collect import GitHubAdapter
from oss_search.models import Candidate


def _load_fixture():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "github_search.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    all_items = []
    for rec in data:
        body = rec.get("body", {})
        if isinstance(body, dict):
            all_items.extend(body.get("items", []))
    return all_items


class _FakeGitHubAdapter(GitHubAdapter):
    """用 fixture 数据替代真实 API 调用。"""

    def __init__(self):
        super().__init__()
        self._all_items = _load_fixture()

    def _search_repos(self, query: str, per_page: int = None) -> list:
        return self._all_items


class _FakeEmptyAdapter:
    """空适配器：无网络调用，返回空列表。"""
    name = "fake"

    def search(self, capability, spec):
        return []


# ============ 1. CLI 参数解析 ============


class TestCLIParsing(unittest.TestCase):
    def test_search_with_request(self):
        parser = build_parser()
        args = parser.parse_args(["search", "test query"])
        self.assertEqual(args.cmd, "search")
        self.assertEqual(args.request, "test query")
        self.assertEqual(args.top_n, 5)
        self.assertEqual(args.out, "report")

    def test_search_with_all_flags(self):
        parser = build_parser()
        args = parser.parse_args([
            "search", "test query", "--json", "spec.json",
            "--out", "myreport", "--top-n", "3",
            "--md", "--html", "--stdout",
            "--weights", "w.json",
        ])
        self.assertEqual(args.out, "myreport")
        self.assertEqual(args.top_n, 3)
        self.assertTrue(args.md)
        self.assertTrue(args.html)
        self.assertTrue(args.stdout)
        self.assertEqual(args.weights, "w.json")

    def test_intent_command(self):
        parser = build_parser()
        args = parser.parse_args(["intent", "--json", "spec.json"])
        self.assertEqual(args.cmd, "intent")

    def test_no_subcommand_shows_help(self):
        ret = main([])
        self.assertEqual(ret, 1)  # prints help, exits non-zero


# ============ 2. 端到端（利用 fixture 离线跑）============


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        if not _load_fixture():
            raise unittest.SkipTest("fixture 不存在，需先录制")
        self.tmpdir = tempfile.mkdtemp()
        self.spec_path = os.path.join(os.path.dirname(__file__), "fixtures", "test_spec.json")
        # 离线 mock 所有适配器
        self._patches = [
            patch("oss_search.__main__.GitHubAdapter", new=_FakeGitHubAdapter),
            patch("oss_search.__main__.NpmAdapter", new=_FakeEmptyAdapter),
            patch("oss_search.__main__.PypiAdapter", new=_FakeEmptyAdapter),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def test_full_pipeline_produces_markdown(self):
        """端到端：意图 JSON → GitHub → 归并 → 评级 → Markdown 报告。"""
        out_base = os.path.join(self.tmpdir, "report")
        ret = main([
            "search",
            "--json", self.spec_path,
            "--out", out_base,
            "--md",
            "--top-n", "3",
        ])
        self.assertEqual(ret, 0, msg="CLI 应正常退出")

        md_path = out_base + ".md"
        self.assertTrue(os.path.exists(md_path), msg=f"应生成 {md_path}")
        with open(md_path, encoding="utf-8") as f:
            content = f.read()

        # 报告核心结构
        self.assertIn("开源选型报告", content)
        self.assertIn("📋 需求", content)
        self.assertIn("📊 候选评估", content)
        self.assertIn("💡 整体组合建议", content)
        self.assertIn("⚠️ 风险提示", content)

    def test_full_pipeline_produces_html(self):
        """端到端：同样链路产出 HTML。"""
        out_base = os.path.join(self.tmpdir, "report2")
        ret = main([
            "search",
            "--json", self.spec_path,
            "--out", out_base,
            "--html",
            "--top-n", "3",
        ])
        self.assertEqual(ret, 0)

        html_path = out_base + ".html"
        self.assertTrue(os.path.exists(html_path))
        with open(html_path, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("<style>", content, msg="HTML 应样式内联")
        self.assertIn("</html>", content)


# ============ 3. 错误降级 ============


class TestErrorHandling(unittest.TestCase):
    def test_missing_request_and_json(self):
        """无 request 且无 --json 时应报错。"""
        ret = main(["search"])
        self.assertEqual(ret, 2)

    def test_nonexistent_json(self):
        ret = main(["search", "--json", "/nonexistent/path.json"])
        self.assertEqual(ret, 1)  # FileNotFound

    def test_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            path = f.name
        try:
            ret = main(["search", "--json", path])
            self.assertEqual(ret, 1)
        finally:
            os.unlink(path)


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
