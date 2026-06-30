"""排序与选型报告（TASK-007）。

按能力分组，每组 Top-N 候选 + 评级 + 理由 + 风险。
输出 Markdown（机器/CLI 友好）+ 自包含 HTML（样式内联，可直接给人类看/存档）。
"""

from __future__ import annotations

from typing import List

from .models import IntentSpec, ScoredCandidate

TOP_N = 5


def build_report(
    scored: List[ScoredCandidate],
    spec: IntentSpec,
    top_n: int = TOP_N,
    sources: list = None,
) -> str:
    """生成 Markdown 选型报告。

    Args:
        scored: 已排序的 ScoredCandidate 列表。
        spec: 原始意图。
        top_n: 每组能力 Top-N 候选（默认 5）。
        sources: 本次使用的信源列表。
    """
    lines: List[str] = []
    _h(lines, f"开源选型报告：{spec.summary}", 1)
    lines.append("")

    # 需求回显
    _h(lines, "📋 需求", 2)
    lines.append(f"> **原始需求**：{spec.original_request}")
    lines.append(f"> **概括**：{spec.summary}")
    if spec.constraints.languages:
        lines.append(f"> **语言**：{', '.join(spec.constraints.languages)}")
    if spec.constraints.license_allow:
        lines.append(f"> **首选许可证**：{', '.join(spec.constraints.license_allow)}")
    if spec.constraints.license_deny:
        lines.append(f"> **排除许可证**：{', '.join(spec.constraints.license_deny)}")
    if spec.constraints.self_host_required:
        lines.append("> **必须自托管**")
    if spec.constraints.deployment:
        lines.append(f"> **部署**：{spec.constraints.deployment}")
    lines.append("")

    # 信源
    if sources:
        _h(lines, "📡 本次使用信源", 2)
        for s in sources:
            if s.startswith("custom:"):
                lines.append(f"- {s}（已记录·采集待 V2）")
            else:
                lines.append(f"- {s}")
        lines.append("")

    # 按能力分组
    groups = _group_by_capability(scored, spec)

    _h(lines, "📊 候选评估", 2)

    for cap_id, cap_name, items in groups:
        _h(lines, f"▸ {cap_name} (`{cap_id}`)", 3)
        lines.append(f"**候选数**：{len(items)} | **展示 Top-{min(top_n, len(items))}**")
        lines.append("")

        # 表格
        _table_header(lines)
        for i, sc in enumerate(items[:top_n]):
            _table_row(lines, i + 1, sc)
        lines.append("")

        # 每条的理由
        for i, sc in enumerate(items[:top_n]):
            c = sc.candidate
            lines.append(f"### {i+1}. [{c.full_name or c.name}]({c.url})")
            if c.description:
                lines.append(f">{c.description[:200]}")
            lines.append(f"- **综合评分**：`{sc.total_score}` / **{sc.grade}**")
            for r in sc.reasons:
                lines.append(f"  - {r}")
            lines.append(f"- **链接**：[{c.url}]({c.url})")
            lines.append("")

    # 整体建议
    _h(lines, "💡 整体组合建议", 2)
    lines.append(all_combo_advice(scored, spec))
    lines.append("")

    _h(lines, "⚠️ 风险提示", 2)
    risks = _risk_warnings(scored)
    if risks:
        for r in risks:
            lines.append(f"- {r}")
    else:
        lines.append("- 未检测到明显风险")
    lines.append("")

    lines.append(f"---")
    lines.append(f"*报告由 开源意图搜索器 (oss-search) 生成 · {len(scored)} 个候选评估*")

    return "\n".join(lines)


def build_html(md: str) -> str:
    """将 Markdown 报告渲染为自包含 HTML。样式内联，无外链，可独立打开。"""
    css = _minimal_css()
    # 简易 markdown→HTML（不用额外依赖）
    body = _md_to_html(md)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>开源选型报告</title>
<style>
{css}
</style>
</head>
<body>
{body}
</body>
</html>"""


def all_combo_advice(scored: List[ScoredCandidate], spec: IntentSpec) -> str:
    """生成整体组合建议。"""
    if not scored:
        return "无候选项目，无法给出建议。"

    a_count = sum(1 for s in scored if s.grade == "A")
    b_count = sum(1 for s in scored if s.grade == "B")

    lines = []
    top = scored[0]
    lines.append(f"**首选推荐**：[{top.candidate.full_name}]({top.candidate.url})（{top.grade} 级，{top.total_score} 分）")

    if a_count >= 2:
        lines.append(f"\n发现 {a_count} 个 A 级和 {b_count} 个 B 级项目，生态选择丰富。")
    elif a_count == 1:
        lines.append(f"\n仅 1 个 A 级项目，{b_count} 个 B 级备选。建议重点评估 A 级项目。")
    else:
        lines.append(f"\n无 A 级项目，{b_count} 个 B 级可选。建议放宽搜索条件或关注新兴项目。")

    # 许可证检查
    licenses = set(s.candidate.license for s in scored if s.candidate.license)
    if len(licenses) <= 2:
        lines.append(f"\n候选项目许可证统一：{', '.join(sorted(filter(None, licenses)))}，组合使用兼容性好。")

    return "\n".join(lines)


def _risk_warnings(scored: List[ScoredCandidate]) -> List[str]:
    """识别风险信号。"""
    risks = []
    for sc in scored:
        c = sc.candidate
        if sc.grade == "D":
            risks.append(f"{c.full_name}: 综合评级为 D，建议谨慎使用")
        if c.license and "GPL" in c.license.upper():
            risks.append(f"{c.full_name}: 使用 {c.license} 许可证，注意合规风险")
        if not c.license:
            risks.append(f"{c.full_name}: 未声明许可证，存在法律风险")
        if c.stars and c.stars < 10:
            risks.append(f"{c.full_name}: 社区极小（{c.stars} ⭐），可能缺乏长期维护")
        if sc.scores.get("activity", 1) < 0.3:
            risks.append(f"{c.full_name}: 活跃度低，项目可能已停滞")
    return risks


# ============ 内部工具 ============


def _group_by_capability(
    scored: List[ScoredCandidate], spec: IntentSpec
) -> List[tuple]:
    """按 capability 分组，保持 spec 里的顺序。"""
    cap_order = {c.id: i for i, c in enumerate(spec.capabilities)}
    cap_names = {c.id: c.name or c.id for c in spec.capabilities}

    groups: dict = {}
    for sc in scored:
        cap_id = sc.candidate.matched_capability or "__unmatched__"
        if cap_id not in groups:
            groups[cap_id] = []
        groups[cap_id].append(sc)

    # 按 spec 里的能力顺序排
    result = []
    for c in spec.capabilities:
        if c.id in groups:
            result.append((c.id, cap_names.get(c.id, c.id), groups[c.id]))
    # 未匹配的放最后
    if "__unmatched__" in groups:
        result.append(("__unmatched__", "未匹配", groups["__unmatched__"]))

    return result


def _h(lines: List[str], text: str, level: int):
    lines.append("#" * level + " " + text)


def _table_header(lines: List[str]):
    lines.append("| # | 项目 | 评分 | 评级 | ⭐ | License | 理由 |")
    lines.append("|---|------|------|------|----|---------|------|")


def _table_row(lines: List[str], idx: int, sc: ScoredCandidate):
    c = sc.candidate
    name = f"[{c.full_name or c.name}]({c.url})"
    stars = f"{c.stars:,}" if c.stars else "-"
    lic = c.license or "-"
    # 取最相关的一条理由
    top_reason = sc.reasons[0] if sc.reasons else "-"
    if len(top_reason) > 50:
        top_reason = top_reason[:47] + "..."

    lines.append(
        f"| {idx} | {name} | {sc.total_score} | **{sc.grade}** | {stars} | {lic} | {top_reason} |"
    )


# ============ 简易 Markdown → HTML（无依赖）============


def _md_to_html(md: str) -> str:
    """极简转换：标题、表格、链接、列表、引用。"""
    import re

    lines = md.strip().split("\n")
    out: List[str] = []
    in_table = False

    for line in lines:
        # 标题
        m = re.match(r"^(#{1,6})\s+(.+)", line)
        if m:
            if in_table:
                out.append("</tbody></table>")
                in_table = False
            level = len(m.group(1))
            out.append(f"<h{level}>{m.group(2)}</h{level}>")
            continue

        # 表格分隔线
        if re.match(r"^\|[-| :]+\|$", line) and in_table:
            continue

        # 表格行
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line[1:-1].split("|")]
            html_cells = "".join(f"<td>{_inline_html(c)}</td>" for c in cells)
            if not in_table:
                out.append("<table><thead>")
                in_table = "hdr"
            if in_table == "hdr":
                out.append(f"<tr>{html_cells}</tr></thead><tbody>")
                in_table = "body"
            else:
                out.append(f"<tr>{html_cells}</tr>")
            continue

        if in_table:
            out.append("</tbody></table>")
            in_table = False

        # 引用
        if line.startswith("> "):
            out.append(f"<blockquote>{_inline_html(line[2:])}</blockquote>")
            continue

        # 无序列表
        m = re.match(r"^(\s*)-\s+(.+)", line)
        if m:
            indent = len(m.group(1))
            margin = f"margin-left:{indent * 20}px;" if indent else ""
            out.append(f'<li style="{margin}">{_inline_html(m.group(2))}</li>')
            continue

        # 分隔线
        if line.strip() == "---":
            out.append("<hr>")
            continue

        # 空行
        if not line.strip():
            out.append("<br>")
            continue

        # 普通段落
        out.append(f"<p>{_inline_html(line)}</p>")

    if in_table:
        out.append("</tbody></table>")
    return "\n".join(out)


def _inline_html(text: str) -> str:
    """处理内联 markdown：**粗体**、`代码`、[链接]()。"""
    import re
    # 先处理粗体
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # 代码
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # 链接 [text](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def _minimal_css() -> str:
    return """
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    max-width: 900px;
    margin: 40px auto;
    padding: 0 20px;
    line-height: 1.6;
    color: #1a1a1a;
    background: #fff;
}
h1 { font-size: 1.8em; border-bottom: 2px solid #e0e0e0; padding-bottom: 8px; }
h2 { font-size: 1.4em; margin-top: 32px; }
h3 { font-size: 1.1em; color: #555; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; }
th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }
th { background: #f5f5f5; font-weight: 600; }
tr:hover { background: #fafafa; }
blockquote { border-left: 4px solid #e0e0e0; margin: 8px 0; padding: 4px 16px; color: #666; }
a { color: #0366d6; text-decoration: none; }
a:hover { text-decoration: underline; }
code { background: #f0f0f0; padding: 1px 5px; border-radius: 3px; font-size: 0.9em; }
strong { color: #222; }
hr { border: none; border-top: 1px solid #eee; margin: 24px 0; }
li { margin: 3px 0; }
"""
