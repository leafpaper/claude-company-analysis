"""票 12 — R11 散文密度的多样本标定:把每条形状判据**单独**跑一遍, 产标注工作表。

为什么要单独跑:现在 `_list_shape` 是「命中任一即返回」,统计不出**每条判据各自的**误报率;
而票 12 要的正是「误报率高的判据删掉, 不是调参」。

语料:
  · 三份 v8 报告的五章正文(东山精密 / 中际旭创 / 华特气体)
  · 景嘉微 v7 报告全文 —— **人工认可过的负样本**:它被人读过并发布, 上面的命中多半是误报

用法:
    python .scratch/v8-implementation/r11-calibration/collect.py            # 统计
    python .scratch/v8-implementation/r11-calibration/collect.py --sheet    # 产标注工作表
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts import lint_v8  # noqa: E402

OUTPUT = Path("C:/Users/tinyb/.claude/output")
HERE = Path(__file__).resolve().parent

V8_RUNS = [
    ("东山精密", OUTPUT / "东山精密/runs/2026-08-24/nodes"),
    ("中际旭创", OUTPUT / "中际旭创/runs/2026-09-01/nodes"),
    ("华特气体", OUTPUT / "华特气体/runs/2026-09-10/nodes"),
]
NEGATIVE = ("景嘉微(v7 人工认可)", OUTPUT / "景嘉微/景嘉微-analysis-2026-06-22.md")


def paragraphs(md: str) -> list[tuple[str, bool]]:
    """(段落, 是否紧跟表格) —— 与 R11 的切分保持一致:跳过表格行与标题行。"""
    out: list[tuple[str, bool]] = []
    prev_was_table = False
    for raw in md.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("|"):
            prev_was_table = True
            continue
        if s.startswith("#"):
            prev_was_table = False
            continue
        out.append((s, prev_was_table))
        prev_was_table = False
    return out


def body_of(node_md: Path) -> str:
    """节点 md 去掉顶部 YAML 块后的正文。"""
    t = node_md.read_text(encoding="utf-8")
    m = re.match(r"\A\s*```yaml.*?\n```\n", t, re.DOTALL)
    return t[m.end():] if m else t


def criteria_hits(line: str) -> dict[str, int]:
    """每条判据**各自**的命中次数(不短路), 外加数字短语数与字数。"""
    squashed = lint_v8._squash(line)
    return {
        "编号项": len(lint_v8._ENUM.findall(line)),
        "期间对比": len(lint_v8._ARROW.findall(line)),
        "并列项": len(lint_v8._PARALLEL.findall(line)),
        "数字短语": len(lint_v8.NUMBER_PHRASE.findall(squashed)),
        "字数": len(line),
    }


def flagged(hits: dict[str, int], after_table: bool) -> list[str]:
    """按现行阈值, 这一段会被哪几条判据报出来(现行实现是短路的, 这里全列)。"""
    if after_table:
        return []
    names = []
    if hits["编号项"] >= lint_v8.SHAPE_MIN_HITS:
        names.append("编号项")
    if hits["期间对比"] >= lint_v8.SHAPE_MIN_HITS:
        names.append("期间对比")
    if hits["并列项"] >= lint_v8.SHAPE_MIN_HITS and hits["数字短语"] >= 4:
        names.append("并列项")
    if not names and hits["字数"] > lint_v8.PROSE_MAX_CHARS:
        names.append("超长")
    return names


def collect() -> list[dict]:
    rows: list[dict] = []
    for company, nodes_dir in V8_RUNS:
        for node in lint_v8.CHAPTER_ORDER:
            f = nodes_dir / f"node-{node}.md"
            if not f.exists():
                continue
            for i, (text, after_table) in enumerate(paragraphs(body_of(f)), 1):
                h = criteria_hits(text)
                rows.append({
                    "来源": company, "章": lint_v8.LABELS[node], "段": i,
                    "紧跟表格": after_table, "命中": flagged(h, after_table),
                    "text": text, **h,
                })
    name, path = NEGATIVE
    if path.exists():
        for i, (text, after_table) in enumerate(paragraphs(path.read_text(encoding="utf-8")), 1):
            h = criteria_hits(text)
            rows.append({
                "来源": name, "章": "v7 全文", "段": i,
                "紧跟表格": after_table, "命中": flagged(h, after_table),
                "text": text, **h,
            })
    return rows


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", action="store_true", help="产标注工作表 sheet.md")
    args = ap.parse_args()

    rows = collect()
    (HERE / "paragraphs.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    by_source: dict[str, dict] = {}
    for r in rows:
        acc = by_source.setdefault(r["来源"], {"段落": 0, "命中段": 0})
        acc["段落"] += 1
        if r["命中"]:
            acc["命中段"] += 1
        for c in r["命中"]:
            acc[c] = acc.get(c, 0) + 1
    print(f"{'来源':22} {'段落':>5} {'命中段':>5}  明细")
    for src, acc in by_source.items():
        detail = " ".join(f"{k}={v}" for k, v in acc.items() if k not in ("段落", "命中段"))
        print(f"{src:22} {acc['段落']:>5} {acc['命中段']:>5}  {detail}")
    print(f"\n总段落 {len(rows)}, 命中 {sum(1 for r in rows if r['命中'])} 段")
    print(f"明细已写入 {HERE / 'paragraphs.json'}")

    if args.sheet:
        lines = ["# R11 标定工作表", "",
                 "逐段标注:`表` = 该改成表(真阳) / `文` = 本来就该是散文(误报)。",
                 "判据的目标形状是「并列项之间有共同的列」——分部/倍数/科目有共同列;",
                 "「给光模块 40x 是因为索尔思单体没披露」没有共同列, 它是理由, 理由的形状就是散文。", ""]
        for r in rows:
            if not r["命中"]:
                continue
            lines.append(
                f"- [ ] **{r['来源']} {r['章']} 第{r['段']}段** 命中 {'+'.join(r['命中'])} "
                f"(编号{r['编号项']} 箭头{r['期间对比']} 并列{r['并列项']} 数字{r['数字短语']} {r['字数']}字)\n"
                f"  > {r['text'][:200]}"
            )
        (HERE / "sheet.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"工作表已写入 {HERE / 'sheet.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
