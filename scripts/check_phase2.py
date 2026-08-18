"""check_phase2 — Phase 2 文档精析机器门控 (v7.2)

Phase 2 产出 phase2-documents.md。此前它是全流程唯一"无机器门控"的阶段(质量要求
只写在 phases/phase2-document-analysis.md 文件内, 全靠自觉)。本脚本把那几条硬要求
变成确定性的退出码检查, 与 check_env / lint_v8 同构。

调用(v7.2 起双跑: doc-analyst 写完自跑自补 ≤3 轮, 主 agent 收到响应后复核一次):
  python3 -m scripts.check_phase2 --md output/{company}/phase2-documents.md

退出码:
  0 = 全部硬规则通过
  1 = 任一硬规则违规(doc-analyst 据此回去补 phase2-documents.md 再跑;
      主 agent 复核红了则 fresh-restart doc-analyst, 不自己补写)

硬规则:
  R1  §1-§8 八个章节标题齐全
  R2  §2 利润表变动 ≥ 3 行带 [PDF:...] 原文引用(反"只写结论不引原文")
  R3  §8 高价值事实锚点表 ≥ 5 行带来源标签([PDF:/[Tushare: 等)
软提示(不阻断): §3 子公司表行数(单主体公司可能为 0)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 章节标题: ## §1 ... ## §8 (Phase 2 用阿拉伯数字, 与主报告的 §一-§八 区分)
SECTION_RE = re.compile(r"^##\s+§\s*(\d)\b", re.MULTILINE)
PDF_TAG = re.compile(r"[\[【]\s*PDF\s*[:：]", re.IGNORECASE)
SOURCE_TAG = re.compile(r"[\[【]\s*(?:PDF|Tushare|metrics\.json|yfinance|WebSearch)\s*[:：]", re.IGNORECASE)

REQUIRED_SECTIONS = [str(i) for i in range(1, 9)]   # §1..§8
MIN_PDF_QUOTES_S2 = 3
MIN_ANCHORS_S8 = 5


def split_sections(md: str) -> dict[str, str]:
    """按 ## §N 切分, 返回 {N: body}."""
    out: dict[str, str] = {}
    matches = list(SECTION_RE.finditer(md))
    for i, m in enumerate(matches):
        num = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        out[num] = md[start:end]
    return out


def _table_rows(body: str) -> list[str]:
    """章节里的表格数据行(以 | 开头, 排除分隔行 |---| 与纯表头)."""
    rows = []
    for line in body.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        if re.fullmatch(r"\|[\s:|-]+\|?", s):   # 分隔行
            continue
        rows.append(s)
    return rows


def lint_phase2(md_path: Path) -> tuple[bool, str]:
    if not md_path.exists():
        return False, f"❌ 未找到 {md_path}"

    md = md_path.read_text(encoding="utf-8")
    sections = split_sections(md)
    findings: list[str] = []

    # R1 章节齐全
    missing = [f"§{n}" for n in REQUIRED_SECTIONS if n not in sections]
    r1 = not missing
    if not r1:
        findings.append(f"R1 章节缺失: {', '.join(missing)}(需 §1-§8 齐全)")

    # R2 §2 PDF 原文引用 ≥ 3
    s2 = sections.get("2", "")
    s2_quotes = sum(1 for line in s2.splitlines() if PDF_TAG.search(line))
    r2 = s2_quotes >= MIN_PDF_QUOTES_S2
    if not r2:
        findings.append(f"R2 §2 带 [PDF:] 原文引用仅 {s2_quotes} 行 < {MIN_PDF_QUOTES_S2}(疑似只写结论未引原文)")

    # R3 §8 锚点表 ≥ 5 行带来源
    s8 = sections.get("8", "")
    s8_anchors = sum(1 for row in _table_rows(s8) if SOURCE_TAG.search(row))
    r3 = s8_anchors >= MIN_ANCHORS_S8
    if not r3:
        findings.append(f"R3 §8 带来源标签的锚点行仅 {s8_anchors} 行 < {MIN_ANCHORS_S8}")

    # 软提示: §3 子公司表
    s3_rows = len(_table_rows(sections.get("3", "")))
    soft = f"(软提示) §3 子公司表数据行 = {s3_rows}" + (" — 注意是否漏列" if s3_rows == 0 else "")

    passed = r1 and r2 and r3
    lines = [f"[check_phase2] {md_path}"]
    lines.append(f"  R1 §1-§8 齐全: {'✅' if r1 else '❌'}")
    lines.append(f"  R2 §2 PDF 原文引用 ≥{MIN_PDF_QUOTES_S2}: {'✅' if r2 else '❌'} ({s2_quotes} 行)")
    lines.append(f"  R3 §8 锚点 ≥{MIN_ANCHORS_S8}: {'✅' if r3 else '❌'} ({s8_anchors} 行)")
    lines.append(f"  {soft}")
    if findings:
        lines.append("")
        lines.append("总结: " + "; ".join(findings) + " → exit 1")
    else:
        lines.append("")
        lines.append("总结: 全部 3 项硬规则通过 → exit 0")
    return passed, "\n".join(lines)


def main() -> int:
    # 报告含 ✅/❌ 等非 ASCII;Windows 控制台默认 GBK 会 UnicodeEncodeError 崩在 print 上,
    # 被 doc-analyst 误读成"门控红了"并空转 3 轮补写。强制 UTF-8 输出。
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):     # 非 TextIOWrapper(被重定向/包装)时跳过
        pass

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--md", required=True, help="phase2-documents.md 路径")
    ap.add_argument("--quiet", action="store_true", help="仅退出码, 不打印报告")
    args = ap.parse_args()

    passed, report = lint_phase2(Path(args.md).expanduser())
    if not args.quiet:
        print(report)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
