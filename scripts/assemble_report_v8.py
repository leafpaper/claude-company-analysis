"""assemble_report_v8 — v8 报告装配 CLI: 首页 + 五章 + 附录A-E, 并落 assembly.json。

报告结构(spec §2 / research/06):
    报告头部 metadata(主页卡片: 行动档位人话 + 质地字段)
    首页 一眼结论   ← 机器装配: 决断卡五行 → 赚钱面板 → Top3 红旗 → 人工导读位 [→ 较上版变化]
    ① 质地 / ② 状态 / ③ 赔率 / ④ 路径 / ⑤ 怎么办   ← 五个节点 md 正文原样挂载
    附录A 财务与经营明细 / B 行业与对标明细 / C 舆情与资金底稿   ← 采集脚本产物挂载
    附录D 红旗总清单(机器合并产物: 脚本 audit ⊕ 写手提名)
    附录E 数据来源与信息缺口

数据只来自节点 md 顶部 YAML 块 + audit 红旗(装配零人工抄写, 见 assembly 模块)。

CLI:
    python -m scripts.assemble_report_v8 --run-dir output/东山精密/runs/2026-06-22 \\
        --company 东山精密 --date 2026-06-22 \\
        [--audit-json ...] [--artifacts-dir ...] [--prev-run-dir ...] [--out ...]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from . import assembly
from . import manifest as manifest_mod
from . import red_flags as rf

CHAPTERS = (
    ("quality", "① 质地——是不是好公司"),
    ("state", "② 状态——在变好吗"),
    ("odds", "③ 赔率——贵不贵"),
    ("path", "④ 路径——扛得住吗"),
    ("decision", "⑤ 怎么办——行动档位与证伪"),
)

# 附录 A/B/C/E 挂载采集脚本产物(零写手); D 由红旗清单机器生成
APPENDIX_SOURCES = (
    ("A", "财务与经营明细", ("data_snapshot.md",)),
    ("B", "行业与对标明细", ("peer_analysis.md",)),
    ("C", "舆情与资金底稿", ("capital_flow.md", "sentiment.md")),
    ("D", "红旗总清单", ()),
    ("E", "数据来源与信息缺口", ("data_sources.md",)),
)

AUDIT_JSON_CANDIDATES = ("audit_report.json", "raw_data/audit_report.json", "audit.json")

_HEADING = re.compile(r"^(#{1,6}) ", re.MULTILINE)


def _utf8_console() -> None:
    """Windows 控制台默认 GBK, 直接 print emoji/中文会 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):        # 非 TTY / 已重定向的老 Python
            pass


# ---------------------------------------------------------------- 工具

def _cell(text) -> str:
    """markdown 表格单元格: 竖线转义 + 换行压平。"""
    return re.sub(r"\s*\n\s*", " ", str(text if text is not None else "")).replace("|", "\\|")


def _demote(md_text: str, levels: int = 2) -> str:
    """挂载外部产物时下沉其标题层级, 使其嵌在 ## 附录X 之下。"""
    def repl(m: re.Match) -> str:
        return "#" * min(6, len(m.group(1)) + levels) + " "
    return _HEADING.sub(repl, md_text)


def find_artifact(dirs: list[Path], name: str) -> Path | None:
    for d in dirs:
        for candidate in (d / name, d / "raw_data" / name):
            if candidate.exists():
                return candidate
    return None


def load_audit_flags(path: Path | None, search_dirs: list[Path]) -> list[dict]:
    """读 audit JSON → 契约红旗条目; 找不到则返回空清单(附录D 只剩写手提名)。"""
    if path is None:
        for name in AUDIT_JSON_CANDIDATES:
            for d in search_dirs:
                if (d / name).exists():
                    path = d / name
                    break
            if path:
                break
    if path is None or not Path(path).exists():
        return []
    return rf.normalize_audit(json.loads(Path(path).read_text(encoding="utf-8")))


# ---------------------------------------------------------------- 首页

def render_verdict_card(card: list[dict]) -> str:
    lines = ["### 决断卡(机器装配自五个节点 verdict)", "", "| 问 | 判定 | 出处 |", "|---|---|---|"]
    marks = ("①", "②", "③", "④", "⑤")
    for mark, row in zip(marks, card):
        label = assembly.NODE_LABELS[row["source_node"]]
        lines.append(f"| {mark} {row['question']} | {_cell(row['verdict'])} | {label} |")
    return "\n".join(lines)


def render_panel(panel: dict, mark_map: dict) -> str:
    by_ind = mark_map.get("by_indicator", {})
    lines = [
        "### 赚不赚钱面板",
        "",
        f"**指标选择理由**:{panel['industry_reason']}",
        "",
        "| 指标 | 数值 | 趋势 | peer 分位 | 红标 |",
        "|---|---|---|---|---|",
    ]
    for ind in panel["indicators"]:
        entry = by_ind.get(ind["name"])
        if entry:
            flag = entry["flags"][0]
            badge = f"{flag['level']} {_cell(flag['title'])}([附录D](#{flag['anchor']}))"
        else:
            badge = "—"          # 无红旗命中 → 不标色(数值与分位自己说话)
        lines.append(
            f"| {_cell(ind['name'])} | {_cell(ind['value'])} | {_cell(ind['trend'])} "
            f"| {_cell(ind.get('peer_percentile') or '—')} | {badge} |"
        )
    conclusion = panel["conclusion"]
    lines += [
        "",
        f"**面板结论**(引用①质地子判定,面板不自产结论):{conclusion['biz_model']} · "
        f"{conclusion['quality_true']}",
    ]
    return "\n".join(lines)


def render_top3(top3: list[dict]) -> str:
    lines = ["### Top3 风险(机器从附录D 红旗清单带出)", ""]
    for item in top3:
        node = rf.NODE_LABELS.get(item.get("node"), item.get("node", ""))
        source = rf.SOURCE_LABELS.get(item.get("source"), item.get("source", ""))
        lines.append(
            f"{item['rank']}. **{item['level']} {item['title']}** — {item['evidence']} "
            f"〔{node} · 来源 {source} · [附录D](#{rf.anchor(item['red_flag_id'])})〕"
        )
    return "\n".join(lines)


def render_change_block(cb: dict) -> str:
    lines = ["### 较上版变化", "", f"**{cb['alpha_summary']}**", ""]
    tb, ta = cb["triad_before"], cb["triad_after"]
    lines += [
        "| 项 | 上版 | 本版 |",
        "|---|---|---|",
        f"| 行动档位 | {_cell(cb['gear_before'])} | {_cell(cb['gear_after'])} |",
        f"| 三元组 状态 | {_cell(tb['state'])} | {_cell(ta['state'])} |",
        f"| 三元组 赔率 | {_cell(tb['odds'])} | {_cell(ta['odds'])} |",
        f"| 三元组 路径 | {_cell(tb['path'])} | {_cell(ta['path'])} |",
    ]
    for delta in cb["metric_deltas"]:
        lines.append(f"| {_cell(delta['name'])} | {_cell(delta['before'])} | {_cell(delta['after'])} |")
    flipped = "、".join(assembly.NODE_LABELS[n] for n in cb["flipped_nodes"]) or "无"
    lines += ["", f"- **翻转节点**:{flipped}"]

    if cb["falsification_changes"]:
        for item in cb["falsification_changes"]:
            verb = "触发" if item["change"] == "triggered" else "解除"
            lines.append(f"- **证伪{verb}**:{item['condition']}")
    else:
        lines.append("- **证伪清单**:无触发/解除")
    if cb["red_flag_changes"]:
        for item in cb["red_flag_changes"]:
            verb = {"triggered": "新增", "resolved": "解除", "level_changed": "级别变化"}[item["change"]]
            lines.append(f"- **红旗{verb}**:{item.get('note') or item['id']}")
    else:
        lines.append("- **红旗清单**:无增减")
    if cb["full_rerun_advice"]["advised"]:
        lines += ["", f"> ⚠️ **建议全量重跑**:{cb['full_rerun_advice']['reason']}"]
    return "\n".join(lines)


def render_front_page(product: dict) -> str:
    parts = [
        "## 首页 一眼结论",
        "",
        render_verdict_card(product["verdict_card"]),
        "",
        render_panel(product["panel"], product.get("red_mark_map", {})),
        "",
        render_top3(product["top3"]),
        "",
        "### 导读",
        "",
        product.get("front_page_intro")
        or "<!-- 导读位:decision-writer 的 3-5 句人工导读(节点块 front_page_intro 字段) -->",
    ]
    if product.get("change_block"):
        parts += ["", render_change_block(product["change_block"])]
    return "\n".join(parts)


# ---------------------------------------------------------------- 附录

def render_appendix_d(flags: list[dict]) -> str:
    c = rf.counts(flags)
    level_line = " · ".join(f"{lvl} {n}" for lvl, n in c["by_level"].items() if n) or "无"
    source_line = " · ".join(
        f"{rf.SOURCE_LABELS[src]} {n}" for src, n in c["by_source"].items() if n
    ) or "无"
    lines = [
        "机器产物:脚本 audit 红旗 ⊕ 节点写手提名两源合并,是首页 Top3 与全报告红标的唯一数据源。",
        "",
        f"**合计 {c['total']} 条** — 级别:{level_line};来源:{source_line}",
        "",
        "| 级别 | 标题 | 证据 | 来源 | 归属节点 | 关联指标 | id |",
        "|---|---|---|---|---|---|---|",
    ]
    for flag in sorted(flags, key=lambda f: rf.LEVEL_ORDER[f["level"]]):
        metrics = "、".join(flag.get("metric_refs") or []) or "—"
        lines.append(
            f"| {flag['level']} | {_cell(flag['title'])} | {_cell(flag['evidence'])} "
            f"| {rf.SOURCE_LABELS[flag['source']]} | {rf.NODE_LABELS[flag['node']]} "
            f"| {_cell(metrics)} | <a id=\"{rf.anchor(flag['id'])}\"></a>`{flag['id']}` |"
        )
    return "\n".join(lines)


def build_appendices(
    flags: list[dict], search_dirs: list[Path]
) -> tuple[list[str], list[dict]]:
    """挂载附录A-E, 返回 (markdown 段落列表, 挂载记录)。缺产物不致命——记进 missing。"""
    sections, records = [], []
    for key, title, sources in APPENDIX_SOURCES:
        body_parts, mounted, missing = [], [], []
        if key == "D":
            body_parts.append(render_appendix_d(flags))
        for name in sources:
            path = find_artifact(search_dirs, name)
            if path is None:
                missing.append(name)
                continue
            mounted.append(str(path))
            body_parts.append(_demote(path.read_text(encoding="utf-8").strip("\n")))
        if missing and not body_parts:
            body_parts.append(f"> ⚠️ 未找到采集产物:{'、'.join(missing)}(本附录留空,请检查采集阶段)")
        elif missing:
            body_parts.append(f"> ⚠️ 未找到:{'、'.join(missing)}")
        sections.append(f"## 附录{key} {title}\n\n" + "\n\n".join(body_parts))
        records.append({"key": key, "title": title, "mounted": mounted, "missing": missing})
    return sections, records


# ---------------------------------------------------------------- 报告总装

def render_metadata_block(product: dict, ticker: str = "") -> str:
    meta = product["metadata"]
    lines = [
        "<!-- CARD_METADATA:",
        f"company: {meta['company']}",
        f"ticker: {ticker}" if ticker else None,
        f"date: {meta['date']}",
        "version: v8.0",
        f"action_gear: {meta['action_gear']}",
        f"verdict: {meta['verdict_plain']}",
        f"quality: {meta['quality_field']}",
        f"next_disclosure_date: {meta['next_disclosure_date']}" if meta.get("next_disclosure_date") else None,
        "-->",
    ]
    return "\n".join(l for l in lines if l)


def render_report(
    product: dict,
    bodies: dict[str, str],
    appendix_sections: list[str],
    ticker: str = "",
) -> str:
    meta = product["metadata"]
    title = f"# {meta['company']}({ticker})投资分析报告" if ticker else f"# {meta['company']}投资分析报告"
    header = [title, "", render_metadata_block(product, ticker), ""]
    stamp = f"**基准日**:{meta['date']} · **行动档位**:{meta['action_gear']} · **质地**:{meta['quality_field']}"
    if meta.get("next_disclosure_date"):
        stamp += f" · **下次预约披露日**:{meta['next_disclosure_date']}"
    header.append(stamp)

    parts = ["\n".join(header), render_front_page(product)]
    for node, heading in CHAPTERS:
        body = bodies.get(node, "").strip("\n")
        parts.append(f"## {heading}\n\n" + (body or "> ⚠️ 节点正文缺失"))
    parts.extend(appendix_sections)
    return "\n\n---\n\n".join(parts).rstrip() + "\n"


def assemble_run(
    run_dir: Path,
    company: str,
    date: str,
    out_path: Path | None = None,
    audit_json: Path | None = None,
    artifacts_dir: Path | None = None,
    prev_run_dir: Path | None = None,
    metric_deltas: list[dict] | None = None,
    ticker: str = "",
    next_disclosure_date: str | None = None,
) -> tuple[dict, Path]:
    """装配一次 run: 读 nodes/ 五块 + audit 红旗 → assembly.json + 主报告 md。"""
    run_dir = Path(run_dir)
    nodes_dir = run_dir / "nodes"
    search_dirs = [Path(artifacts_dir)] if artifacts_dir else []
    search_dirs.append(run_dir)

    nodes = assembly.load_nodes(nodes_dir)
    bodies = assembly.load_node_bodies(nodes_dir)
    script_flags = load_audit_flags(audit_json, search_dirs)

    prev_nodes = prev_script_flags = None
    if prev_run_dir:
        prev_run_dir = Path(prev_run_dir)
        prev_nodes = assembly.load_nodes(prev_run_dir / "nodes")
        prev_script_flags = load_audit_flags(None, [prev_run_dir])

    flags_preview = rf.merge(script_flags, rf.collect_nominations(nodes))
    appendix_sections, appendix_records = build_appendices(flags_preview, search_dirs)

    product = assembly.build_assembly(
        company=company,
        date=date,
        nodes=nodes,
        script_flags=script_flags,
        prev_nodes=prev_nodes,
        prev_script_flags=prev_script_flags,
        metric_deltas=metric_deltas,
        appendices=appendix_records,
        next_disclosure_date=next_disclosure_date,
    )

    assembly_dir = run_dir / "assembly"
    assembly_dir.mkdir(parents=True, exist_ok=True)
    (assembly_dir / "assembly.json").write_text(
        json.dumps(product, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    out_path = Path(out_path) if out_path else run_dir / f"{company}-analysis-{date}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_report(product, bodies, appendix_sections, ticker), encoding="utf-8")
    return product, out_path


def main() -> int:
    _utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-dir", required=True, help="runs/{date}/ 目录(含 nodes/)")
    ap.add_argument("--company", required=True)
    ap.add_argument("--date", required=True, help="报告基准日 YYYY-MM-DD")
    ap.add_argument("--ticker", default="")
    ap.add_argument("--out", default=None, help="主报告输出路径(默认 run 目录下)")
    ap.add_argument("--audit-json", default=None, help="financial_audit --json 产物(默认在 run 目录内找)")
    ap.add_argument("--artifacts-dir", default=None, help="附录A/B/C/E 采集产物目录(默认 run 目录)")
    ap.add_argument("--prev-run-dir", default=None, help="上版 run 目录, 传了则装配「较上版变化」区块")
    ap.add_argument("--metric-deltas", default=None, help="关键指标 delta 的 JSON 文件(分诊产物)")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not (run_dir / "nodes").is_dir():
        print(f"❌ run 目录缺 nodes/: {run_dir}", file=sys.stderr)
        return 2

    deltas = None
    if args.metric_deltas:
        deltas = json.loads(Path(args.metric_deltas).read_text(encoding="utf-8"))
        if isinstance(deltas, dict):
            deltas = deltas.get("metric_deltas", [])

    disclosure = None
    m = manifest_mod.load(run_dir.parent.parent)
    if m:
        disclosure = m.get("next_disclosure_date")

    try:
        product, out_path = assemble_run(
            run_dir=run_dir,
            company=args.company,
            date=args.date,
            out_path=Path(args.out) if args.out else None,
            audit_json=Path(args.audit_json) if args.audit_json else None,
            artifacts_dir=Path(args.artifacts_dir) if args.artifacts_dir else None,
            prev_run_dir=Path(args.prev_run_dir) if args.prev_run_dir else None,
            metric_deltas=deltas,
            ticker=args.ticker,
            next_disclosure_date=disclosure,
        )
    except (assembly.AssemblyError, rf.RedFlagError) as exc:
        print(f"❌ 装配失败:\n{exc}", file=sys.stderr)
        return 1

    missing = [a for a in product.get("appendices", []) if a["missing"]]
    print(f"✅ 主报告 → {out_path}")
    print(f"   装配产物 → {Path(args.run_dir) / 'assembly' / 'assembly.json'}")
    print(f"   红旗 {len(product['red_flags'])} 条 · Top3:"
          + " / ".join(f"{t['level']}{t['title']}" for t in product["top3"]))
    for a in missing:
        print(f"   ⚠️ 附录{a['key']} 缺产物:{'、'.join(a['missing'])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
