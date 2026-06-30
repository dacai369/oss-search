"""命令行入口：`python -m oss_search` / 安装后 `oss-search`。

完整端到端链路：parse_intent → collect → dedup → score → report。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from .intent import load_intent_spec, parse_intent
from .collect import GitHubAdapter, SourceAdapter
from .adapters import NpmAdapter, PypiAdapter
from .merge import dedup
from .score import score, DEFAULT_WEIGHTS
from .report import build_report, build_html
from .models import Candidate, IntentSpec, ScoredCandidate

# 统一输出到 stderr，不污染 stdout（stdout 留给 --stdout 报告内容）
console = Console(stderr=True, highlight=False)


def _get_adapters() -> list:
    """返回所有可用的采集适配器。"""
    adapters: list = [GitHubAdapter()]
    try:
        adapters.append(NpmAdapter())
    except Exception:
        pass
    try:
        adapters.append(PypiAdapter())
    except Exception:
        pass
    return adapters


def _cmd_intent(args: argparse.Namespace) -> int:
    if args.json:
        with open(args.json, encoding="utf-8") as f:
            data = json.load(f)
        spec = load_intent_spec(data, original_request=args.request or "")
    elif args.request:
        spec = parse_intent(args.request)
    else:
        console.print("[red]错误：需要提供 request 或 --json 之一[/red]")
        return 2
    print(json.dumps(spec.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    """端到端搜索：意图拆解 → 采集 → 归并 → 评级 → 报告。"""
    t0 = time.time()

    # ---- 1. 意图拆解 ----
    console.rule("[bold cyan]意图拆解[/bold cyan]")
    if args.json:
        with open(args.json, encoding="utf-8") as f:
            spec = load_intent_spec(json.load(f), original_request=args.request or "")
    elif args.request:
        spec = parse_intent(args.request)
    else:
        console.print("[red]错误：需要提供 request 或 --json[/red]")
        return 2

    cap_names = [c.name for c in spec.capabilities]
    console.print(f"  [green]✓[/green] 拆出 [bold]{len(cap_names)}[/bold] 个能力：{cap_names}")

    # ---- 2. 采集（多个适配器并行）----
    console.rule("[bold cyan]多源采集[/bold cyan]")
    all_candidates: List[Candidate] = []
    sources_used: List[str] = []
    adapters = _get_adapters()
    for adapter in adapters:
        name = getattr(adapter, "name", type(adapter).__name__)
        for cap in spec.capabilities:
            try:
                results = adapter.search(cap, spec)
                console.print(
                    f"  [[cyan]{name}[/cyan]] {cap.name} "
                    f"[dim]→[/dim] [yellow]{len(results)}[/yellow] 个候选"
                )
                all_candidates.extend(results)
                if name not in sources_used:
                    sources_used.append(name)
            except Exception as e:
                console.print(f"  [red]⚠ [{name}] {cap.name} 失败：{e}[/red]")

    if getattr(args, "source", None):
        for s in args.source:
            sources_used.append(f"custom:{s}")
            console.print(f"  [dim]📎 自定义信源已登记：{s}[/dim]")

    console.print(
        f"\n  共计 [bold]{len(all_candidates)}[/bold] 个候选"
        f"（[dim]{len(sources_used)} 个源[/dim]）"
    )

    grades: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0}
    if not all_candidates:
        console.print("[yellow]⚠️ 未找到任何候选项目。生成空报告。[/yellow]")
        scored: list = []
    else:
        # ---- 3. 归并 ----
        console.rule("[bold cyan]归并去重[/bold cyan]")
        merged = dedup(all_candidates)
        console.print(
            f"  [green]✓[/green] {len(all_candidates)} → [bold]{len(merged)}[/bold] 个"
        )

        # ---- 4. 评级 ----
        console.rule("[bold cyan]质量评级[/bold cyan]")
        weights = {}
        if args.weights:
            with open(args.weights, encoding="utf-8") as f:
                weights = json.load(f)
        scored = score(merged, spec, weights=weights or None)

        for s in scored:
            grades[s.grade] = grades.get(s.grade, 0) + 1

        grade_table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        grade_table.add_column("评级", style="bold", justify="center")
        grade_table.add_column("数量", justify="right")
        grade_table.add_column("含义", style="dim")
        grade_table.add_row("[green]A[/green]", str(grades["A"]), "综合评分 ≥ 0.80")
        grade_table.add_row("[blue]B[/blue]",  str(grades["B"]), "综合评分 ≥ 0.65")
        grade_table.add_row("[yellow]C[/yellow]", str(grades["C"]), "综合评分 ≥ 0.50")
        grade_table.add_row("[red]D[/red]",   str(grades["D"]), "综合评分 < 0.50")
        console.print(grade_table)

    # ---- 5. 报告 ----
    console.rule("[bold cyan]生成报告[/bold cyan]")
    top_n = args.top_n or 5
    md = build_report(scored, spec, top_n=top_n, sources=sources_used)

    out_base = args.out or "report"
    if args.html:
        html = build_html(md)
        html_path = f"{out_base}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        console.print(f"  [green]✓[/green] HTML: [link]{os.path.abspath(html_path)}[/link]")

    if args.md or (not args.html):
        md_path = f"{out_base}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        console.print(f"  [green]✓[/green] Markdown: [link]{os.path.abspath(md_path)}[/link]")

    if args.stdout:
        print(md)

    elapsed = time.time() - t0
    console.print(
        Panel(
            f"[bold green]完成！[/bold green]  耗时 {elapsed:.1f}s  |  "
            f"A=[green]{grades.get('A',0)}[/green]  "
            f"B=[blue]{grades.get('B',0)}[/blue]  "
            f"C=[yellow]{grades.get('C',0)}[/yellow]  "
            f"D=[red]{grades.get('D',0)}[/red]",
            border_style="green",
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="oss-search", description="开源意图搜索器引擎")

    sub = p.add_subparsers(dest="cmd")

    # ---- intent ----
    pi = sub.add_parser("intent", help="意图拆解：校验已有 JSON（--json）或兜底自己拆（request）")
    pi.add_argument("request", nargs="?", help="自然语言需求（兜底路径，需配 LLM_* 环境变量）")
    pi.add_argument("--json", help="一个已有的 IntentSpec JSON 文件路径（skill 主路径，无需 LLM）")
    pi.set_defaults(func=_cmd_intent)

    # ---- search ----
    ps = sub.add_parser("search", help="端到端搜索：意图→采集→评级→报告")
    ps.add_argument("request", nargs="?", help="自然语言需求")
    ps.add_argument("--json", help="IntentSpec JSON 文件路径（跳过意图拆解）")
    ps.add_argument("--out", "-o", default="report", help="输出文件名前缀（默认 report）")
    ps.add_argument("--top-n", type=int, default=5, help="每组 Top-N（默认 5）")
    ps.add_argument("--md", action="store_true", help="输出 Markdown")
    ps.add_argument("--html", action="store_true", help="输出自包含 HTML")
    ps.add_argument("--stdout", action="store_true", help="同时打印 Markdown 到 stdout")
    ps.add_argument("--weights", help="自定义权重 JSON 文件路径")
    ps.add_argument("--source", action="append", default=[], help="运行时自定义信源 URL（可多次指定）")
    ps.set_defaults(func=_cmd_search)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 1
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        console.print(f"[red]错误：{e}[/red]")
        return 1
    except KeyboardInterrupt:
        console.print("\n[dim]中断。[/dim]")
        return 130


if __name__ == "__main__":
    sys.exit(main())
