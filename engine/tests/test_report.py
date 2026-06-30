"""TASK-007 验收测试：排序与报告。

无 pytest 也可直接跑：python3 tests/test_report.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from oss_search.models import Candidate, IntentSpec, Constraints, Capability, ScoredCandidate
from oss_search.report import build_report, build_html, _group_by_capability


def _c(**kwargs) -> Candidate:
    defaults = {
        "id": "github:test/x",
        "source": "github",
        "name": "x",
        "url": "https://github.com/test/x",
        "full_name": "test/x",
        "description": "Search engine",
        "license": "MIT",
        "stars": 5000,
    }
    defaults.update(kwargs)
    return Candidate(**defaults)


def _sc(cand=None, total=0.85, grade="B", reasons=None, scores=None, cap_id="cap-1") -> ScoredCandidate:
    c = cand or _c()
    c.matched_capability = cap_id
    if reasons is None:
        reasons = ["项目活跃，社区庞大", "许可证 MIT 兼容", "文档齐全"]
    if scores is None:
        scores = {"relevance": 0.8, "activity": 0.9, "community": 0.9,
                   "maturity": 0.7, "license_fit": 1.0, "security": 0.5}
    return ScoredCandidate(candidate=c, scores=scores, total_score=total,
                           grade=grade, reasons=reasons)


def _spec() -> IntentSpec:
    return IntentSpec(
        original_request="做一个文档问答知识库，要自部署",
        summary="自托管文档问答(RAG)知识库",
        constraints=Constraints(
            self_host_required=True,
            license_deny=["GPL-3.0"],
            deployment="本地/私有部署",
        ),
        capabilities=[
            Capability(id="cap-1", name="文档解析与切分", required=True,
                       keywords_en=["document parser"], keywords_zh=["文档解析"]),
            Capability(id="cap-2", name="向量检索", required=True,
                       keywords_en=["vector search"], keywords_zh=["向量检索"]),
        ],
    )


# ============ 1. 报告生成 ============


class TestBuildReport(unittest.TestCase):
    def test_report_contains_key_sections(self):
        scored = [_sc(_c(id="g:a/1", full_name="a/1", stars=5000, description="doc parser"), grade="A"),
                   _sc(_c(id="g:b/2", full_name="b/2", stars=3000, description="vector db"), grade="B", cap_id="cap-2")]
        spec = _spec()
        md = build_report(scored, spec)
        self.assertIn("开源选型报告", md)
        self.assertIn("自托管", md)
        self.assertIn("doc parser", md)
        self.assertIn("候选评估", md)
        self.assertIn("整体组合建议", md)
        self.assertIn("风险提示", md)

    def test_groups_by_capability(self):
        scored = [
            _sc(_c(id="g:a", full_name="a"), cap_id="cap-1", grade="B"),
            _sc(_c(id="g:b", full_name="b"), cap_id="cap-2", grade="A"),
            _sc(_c(id="g:c", full_name="c"), cap_id="cap-1", grade="B"),
        ]
        spec = _spec()
        md = build_report(scored, spec)
        # cap-1 应出现在 cap-2 前面（按 spec 排序）
        idx1 = md.index("文档解析")
        idx2 = md.index("向量检索")
        self.assertLess(idx1, idx2, msg="capabilities 应按 spec 顺序排列")

    def test_shows_grade_and_license(self):
        scored = [_sc(_c(license="Apache-2.0", stars=10000), grade="A")]
        md = build_report(scored, _spec())
        self.assertIn("Apache-2.0", md)
        self.assertIn("**A**", md)

    def test_top_n_limit(self):
        scored = [_sc(_c(id=f"g:x{i}", full_name=f"x{i}"), grade="B") for i in range(8)]
        spec = _spec()
        md = build_report(scored, spec, top_n=3)
        # 详细条目 ### 有 1(cap标题)+3(items)=4 个
        h3_count = md.count("### ")
        self.assertEqual(h3_count, 4, msg=f"Top-3 应产生 4 个 H3 (1组标题+3条目)，实际：{h3_count}")

    def test_empty_scored(self):
        md = build_report([], _spec())
        self.assertIn("无候选项目", md)

    def test_risk_warnings(self):
        scored = [
            _sc(_c(id="g:bad", full_name="bad/repo", stars=3, license=None,
                   last_commit_at="2024-01-01T00:00:00Z"), grade="D",
                scores={"relevance": 0.2, "activity": 0.1, "community": 0.05,
                        "maturity": 0.1, "license_fit": 0.5, "security": 0.5}),
        ]
        md = build_report(scored, _spec())
        self.assertIn("未声明许可证", md)
        self.assertIn("D", md)


# ============ 2. HTML 渲染 ============


class TestBuildHtml(unittest.TestCase):
    def test_html_self_contained(self):
        scored = [_sc(grade="B")]
        md = build_report(scored, _spec())
        html = build_html(md)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("<style>", html)
        self.assertIn("</html>", html)
        # 无外链
        self.assertNotIn("http://", html.split("<style>")[0].split("</style>")[0] if "<style>" in html else html[:200])

    def test_html_renders_table(self):
        scored = [_sc(_c(full_name="a/b"), grade="B")]
        md = build_report(scored, _spec())
        html = build_html(md)
        self.assertIn("<table>", html)
        self.assertIn("<td>", html)

    def test_html_renders_header(self):
        scored = [_sc(grade="B")]
        md = build_report(scored, _spec())
        html = build_html(md)
        self.assertIn("<h1>", html)
        self.assertIn("<h2>", html)


# ============ 3. 分组逻辑 ============


class TestGrouping(unittest.TestCase):
    def test_groups_maintain_spec_order(self):
        spec = _spec()
        scored = [
            _sc(cap_id="cap-2", grade="B"),
            _sc(cap_id="cap-1", grade="A"),
            _sc(cap_id="cap-2", grade="B"),
        ]
        groups = _group_by_capability(scored, spec)
        self.assertEqual(groups[0][0], "cap-1")
        self.assertEqual(groups[1][0], "cap-2")
        self.assertEqual(len(groups[0][2]), 1)  # cap-1: 1 item
        self.assertEqual(len(groups[1][2]), 2)  # cap-2: 2 items


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
