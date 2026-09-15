"""票 12 — 逐条判据算真阳率 / 误报率, 并试改良版。

现行三条形状判据是「命中任一即返回」, 统计不出各自的误报率;票 12 要的正是
「误报率压不下去的判据删掉, 不是调参」。这里把每条单独跑, 再试两个候选改良:

  · 编号项':只认**句首**的编号 —— 现行正则把「③赔率」「(5.4)」「🟠③④」这类
    引用标记和小节号也数成编号项。
  · 并列项':数**自带数字的并列段** ≥4 —— 现行是「顿号 ≥3 且全段数字 ≥4」,
    数字挤在一句里也算, 于是判定句和权重理由全中。

用法: python .scratch/v8-implementation/r11-calibration/evaluate.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2]))

from labels import LABELS, key_of  # noqa: E402
from scripts import lint_v8  # noqa: E402

# 句首编号:行首, 或紧跟在分句标点 / 空白之后;且不能是「🟠③」这种红旗引用、
# 也不能是「(5.4)」这种小节号(数字前面还有数字或点)
_ENUM_AT_CLAUSE_START = re.compile(
    r"(?:^|(?<=[;;。:：])|(?<=[;;。:：]\s))\s*(?:[①-⑨]|[1-9][)）])"
)
_SEG_SPLIT = re.compile(r"[、;;]")


def enum_strict(line: str) -> int:
    return len(_ENUM_AT_CLAUSE_START.findall(line))


def numbered_segments(line: str) -> int:
    """被顿号 / 分号切开后, 自带数字短语的段有几个。"""
    segs = [s for s in _SEG_SPLIT.split(line) if s.strip()]
    return sum(1 for s in segs if lint_v8.NUMBER_PHRASE.search(lint_v8._squash(s)))


def variants(row: dict) -> dict[str, bool]:
    line, after_table = row["text"], row["紧跟表格"]
    if after_table:
        return {}
    n_nums = row["数字短语"]
    return {
        "编号项(现行)": row["编号项"] >= lint_v8.SHAPE_MIN_HITS,
        "编号项'(句首)": enum_strict(line) >= lint_v8.SHAPE_MIN_HITS,
        "期间对比(现行)": row["期间对比"] >= lint_v8.SHAPE_MIN_HITS,
        "并列项(现行)": row["并列项"] >= lint_v8.SHAPE_MIN_HITS and n_nums >= 4,
        "并列项'(带数字的段≥4)": numbered_segments(line) >= 4,
        "超长(>200字)": row["字数"] > lint_v8.PROSE_MAX_CHARS,
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = json.loads((HERE / "paragraphs.json").read_text(encoding="utf-8"))

    names = list(variants(rows[0]) or {
        "编号项(现行)": 0, "编号项'(句首)": 0, "期间对比(现行)": 0,
        "并列项(现行)": 0, "并列项'(带数字的段≥4)": 0, "超长(>200字)": 0})
    stats = {n: {"命中": 0, "T": 0, "F": 0, "未标注": []} for n in names}

    for row in rows:
        v = variants(row)
        if not v:
            continue
        label = LABELS.get(key_of(row))
        for name, hit in v.items():
            if not hit:
                continue
            stats[name]["命中"] += 1
            if label is None:
                stats[name]["未标注"].append(row)
            else:
                stats[name][label] += 1

    print(f"语料: {len(rows)} 段(东山 / 旭创 / 华特 三份 v8 + 景嘉微 v7 负样本)")
    print(f"{'判据':24} {'命中':>4} {'真阳':>4} {'误报':>4} {'未标':>4} {'精确率':>7}")
    for name in names:
        s = stats[name]
        judged = s["T"] + s["F"]
        prec = f"{s['T'] / judged * 100:.0f}%" if judged else "—"
        print(f"{name:24} {s['命中']:>4} {s['T']:>4} {s['F']:>4} {len(s['未标注']):>4} {prec:>7}")

    # 改良版新抓到、原来没命中的段 —— 这些没有标注, 要人工看
    for name in ("编号项'(句首)", "并列项'(带数字的段≥4)"):
        new = [r for r in stats[name]["未标注"]]
        if new:
            print(f"\n【{name}】新抓到 {len(new)} 段(原判据未命中, 需人工判):")
            for r in new[:12]:
                print(f"  - {r['来源']} {r['章']} 第{r['段']}段(带数字段 {numbered_segments(r['text'])}"
                      f" / 顿号 {r['并列项']} / 数字 {r['数字短语']}): {r['text'][:80]}")

    # 漏掉的真阳(原判据抓到、改良版没抓到)
    print("\n【改良版是否漏掉真阳】")
    for row in rows:
        v = variants(row)
        if not v:
            continue
        label = LABELS.get(key_of(row))
        if label != "T":
            continue
        if v["编号项(现行)"] and not v["编号项'(句首)"]:
            print(f"  编号项' 漏: {row['来源']} {row['章']} 第{row['段']}段")
        if v["并列项(现行)"] and not v["并列项'(带数字的段≥4)"]:
            print(f"  并列项' 漏: {row['来源']} {row['章']} 第{row['段']}段")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
