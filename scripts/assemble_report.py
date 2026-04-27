"""assemble_report.py — Phase 3c 拼接器, 把 5 个 part 文件合并为最终主报告.

设计目标:
    Phase 3 重构后, 主报告分 5 个 part 由 LLM 分次写入 (避免单次 context 压力下省略中间章节)。
    本脚本把 phase3-part1.md ~ phase3-part5.md 顺序拼接为 {company}-analysis-{date}.md,
    同时验证章节齐全 / 提取 metadata 注释块到顶部。

Part 章节边界 (固定):
    part1: §一 §二 §三                  (执行摘要 / 评分 / 快筛, 含报告头部 + RATING/METRICS/CARD metadata)
    part2: §四 §五                       (公司基本面 / 行业)  ★ 财务趋势 + 十大股东
    part3: §六 §七 §八                   (10 维度 / 舆情 / Peer)
    part4: §九 §十 §十一                 (估值 / 回报 / 定性)
    part5: §十二 §十三 §十四 §十五       (洞察 / 角色 / 缺口 / 来源)

CLI:
    python3 -m scripts.assemble_report \\
        --company {company} \\
        --date {YYYY-MM-DD} \\
        --parts-dir output/{company}/ \\
        --out output/{company}/{company}-analysis-{date}.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# part 名 → 期望含的章节号 (Rule 4 anti_lazy_lint 已强制章节标题与 skeleton 字节一致)
# v4.8.1: 用正则边界匹配 (\s|$) 取代字符串 startswith,
# 修 Bug 3 — §十 vs §十一/§十二 等的脆弱区分(原版用尾部空格硬编码,
# 容错性差: 任何 tab / 多空格都会误报缺章节)
PART_EXPECTED_SECTIONS = {
    1: ["§一", "§二", "§三"],
    2: ["§四", "§五"],
    3: ["§六", "§七", "§八"],
    4: ["§九", "§十", "§十一"],
    5: ["§十二", "§十三", "§十四", "§十五"],
}


def _has_section(content: str, section: str) -> bool:
    """检查 markdown content 是否含 ## {section} 章节标题, 用正则保证 §十 不被 §十一/§十二 假阳性命中.

    匹配规则: 行首 ## (允许前后任意空白), 然后 {section}, 后面必须是空白或行尾.
    例如 _has_section(text, '§十') 不会匹配 '## §十一 投资回报'.
    """
    pattern = rf"^\s*##\s+{re.escape(section)}(?=\s|$)"
    return bool(re.search(pattern, content, re.MULTILINE))


def validate_part(idx: int, content: str) -> list[str]:
    """验证 part 含其预期章节标题, 返回问题列表 (空表示通过)."""
    issues = []
    expected = PART_EXPECTED_SECTIONS.get(idx, [])
    for sec in expected:
        if not _has_section(content, sec):
            issues.append(f"part{idx}: 缺章节标题 '## {sec}'")
    return issues


def extract_metadata_blocks(part1_content: str) -> str:
    """从 part1 抽取 RATING_TRIO_DATA / KEY_METRICS_SIDEBAR / CARD_METADATA 三个注释块.

    若 part1 未含 metadata 注释块, 返回空字符串 (Phase 3b-1 写作时未按 schema 输出).
    """
    blocks = []
    for marker in ("RATING_TRIO_DATA", "KEY_METRICS_SIDEBAR", "CARD_METADATA"):
        pattern = rf"<!--\s*{marker}:.*?-->"
        m = re.search(pattern, part1_content, re.DOTALL)
        if m:
            blocks.append(m.group(0))
        else:
            sys.stderr.write(f"⚠️  part1 未含 {marker} 注释块 (Phase 6 update_index.py 可能解析降级)\n")
    return "\n\n".join(blocks)


def assemble(company: str, date: str, parts_dir: Path, out_path: Path) -> int:
    """读 5 个 part, 拼接, 写 out_path. 返回 0 成功 / 1 失败."""

    # 1. 读 5 个 part
    parts = {}
    for i in range(1, 6):
        p = parts_dir / f"phase3-part{i}.md"
        if not p.exists():
            sys.stderr.write(f"❌ 缺 part {i}: {p}\n")
            return 1
        parts[i] = p.read_text(encoding="utf-8")
        sys.stderr.write(f"  读取 part{i}: {len(parts[i]):,} chars\n")

    # 2. 验证每个 part 含其预期章节
    all_issues = []
    for i, content in parts.items():
        issues = validate_part(i, content)
        all_issues.extend(issues)
    if all_issues:
        sys.stderr.write("❌ 章节验证失败:\n")
        for issue in all_issues:
            sys.stderr.write(f"   - {issue}\n")
        sys.stderr.write("\n请回到对应 part 修复后重新拼接.\n")
        return 1

    # 3. 拼接: part1 已含报告头部和 metadata; part2-5 直接追加
    pieces = [parts[1].rstrip()]
    for i in range(2, 6):
        # 追加前确保有空行分隔
        pieces.append("\n\n" + parts[i].lstrip())

    final_content = "\n".join(pieces)

    # 4. 末尾 footer (生成时间戳 + skill 版本)
    if not final_content.rstrip().endswith("*"):  # 简单判断: 如果 part5 没 footer 就加
        final_content = final_content.rstrip() + "\n"

    # 5. 写最终文件
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(final_content, encoding="utf-8")

    # 6. 自检
    section_count = final_content.count("\n## §")
    sys.stderr.write(f"\n✅ 主报告已拼接到 {out_path}\n")
    sys.stderr.write(f"   总字符数: {len(final_content):,}\n")
    sys.stderr.write(f"   章节数 (## §): {section_count}\n")

    if section_count < 15:
        sys.stderr.write(f"⚠️  章节数 {section_count} < 15 (skeleton 期望 15 章)\n")

    return 0


def main():
    ap = argparse.ArgumentParser(description="拼接 5 个 phase3-part .md 为最终主报告")
    ap.add_argument("--company", required=True, help="公司名称, 用于头部展示")
    ap.add_argument("--date", required=True, help="报告日期 YYYY-MM-DD")
    ap.add_argument("--parts-dir", required=True, help="包含 phase3-part1.md ~ phase3-part5.md 的目录")
    ap.add_argument("--out", required=True, help="输出主报告路径, 如 output/{company}/{company}-analysis-{date}.md")
    args = ap.parse_args()

    parts_dir = Path(args.parts_dir)
    out_path = Path(args.out)

    if not parts_dir.exists() or not parts_dir.is_dir():
        print(f"❌ parts-dir 不存在: {parts_dir}", file=sys.stderr)
        return 1

    return assemble(args.company, args.date, parts_dir, out_path)


if __name__ == "__main__":
    sys.exit(main())
