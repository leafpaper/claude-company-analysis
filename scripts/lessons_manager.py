"""lessons_manager.py — v5.1.1 全局经验库管理脚本

功能:
    - append: 把 sub-agent 自检报告里提取的 lessons 行追加到全局 lessons-learned.md
    - recent: 抽取近 N 天某类别 lessons,供主 agent 注入下一次 sub-agent prompt

设计:
    - 文件: output/_global/lessons-learned.md (跨公司共享)
    - 类别: 用 ## 类别: {sub_agent_name} 二级标题分组
    - 条目格式: - [{yymmdd} {company}] {内容}
    - 每类别上限 100 条,超过最老 5 条归档到 lessons-archive-{YYYY-MM}.md
    - 单条上限 200 字符,超过自动截断

CLI:
    python3 -m scripts.lessons_manager append \\
        --category phase3-part4 \\
        --company 盛美上海 \\
        --date 260429 \\
        --lines "DCF 假设需基于历史外推, +30% 但历史下滑会被 reviewer FAIL"

    python3 -m scripts.lessons_manager recent \\
        --category phase3-part4 \\
        --days 30
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 全局经验库位置(相对 skill 根目录)
GLOBAL_DIR = Path(__file__).resolve().parent.parent / "output" / "_global"
LESSONS_FILE = GLOBAL_DIR / "lessons-learned.md"

MAX_PER_CATEGORY = 100
MAX_LINE_CHARS = 200
SIMILARITY_THRESHOLD = 0.6  # 简单 substring 包含,不上 cosine

HEADER_TEMPLATE = """# Company Analysis 全局经验库 (lessons-learned, v5.1.1)

> 由 sub-agent 自检报告的 `**lessons**` 字段自动汇集,主 agent 启动新 sub-agent 时注入近 30 天条目。
> 详见 `references/agent-protocol.md` §6。

"""


def _ensure_file() -> None:
    GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
    if not LESSONS_FILE.exists():
        LESSONS_FILE.write_text(HEADER_TEMPLATE, encoding="utf-8")


def _read_categories() -> dict[str, list[str]]:
    """读全文,按 ## 类别: 分组返回 {category: [lines]}."""
    if not LESSONS_FILE.exists():
        return {}

    content = LESSONS_FILE.read_text(encoding="utf-8")
    cats: dict[str, list[str]] = {}
    current = None
    for line in content.splitlines():
        m = re.match(r"^##\s+类别:\s*(.+?)\s*$", line)
        if m:
            current = m.group(1).strip()
            cats.setdefault(current, [])
        elif current and line.startswith("- ["):
            cats[current].append(line)
    return cats


def _write_categories(cats: dict[str, list[str]]) -> None:
    out = [HEADER_TEMPLATE.rstrip(), ""]
    for cat in sorted(cats.keys()):
        out.append(f"## 类别: {cat}")
        out.append("")
        out.extend(cats[cat])
        out.append("")
    LESSONS_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")


def _is_duplicate(new_text: str, existing: list[str]) -> bool:
    """简单去重: 新内容是否被任何已有条目以 substring 形式覆盖 ≥ SIMILARITY_THRESHOLD."""
    new_clean = re.sub(r"\[\d+\s+[^\]]+\]\s*", "", new_text).strip()
    if not new_clean:
        return False
    for ex in existing:
        ex_clean = re.sub(r"\[\d+\s+[^\]]+\]\s*", "", ex).strip()
        if not ex_clean:
            continue
        # 双向 substring 测试
        if new_clean in ex_clean or ex_clean in new_clean:
            return True
        # 简单 token Jaccard
        new_tokens = set(new_clean[:50])  # 字符级粗估
        ex_tokens = set(ex_clean[:50])
        if not new_tokens or not ex_tokens:
            continue
        jaccard = len(new_tokens & ex_tokens) / max(len(new_tokens | ex_tokens), 1)
        if jaccard > SIMILARITY_THRESHOLD:
            return True
    return False


def _archive_oldest(category: str, lines: list[str]) -> tuple[list[str], list[str]]:
    """超过 MAX_PER_CATEGORY 时把最老的 5 条归档,返回 (保留, 归档)."""
    if len(lines) <= MAX_PER_CATEGORY:
        return lines, []
    archive_n = 5
    return lines[archive_n:], lines[:archive_n]


def _write_archive(category: str, archived: list[str]) -> Path:
    """归档到 lessons-archive-{YYYY-MM}.md."""
    ym = datetime.now().strftime("%Y-%m")
    archive_path = GLOBAL_DIR / f"lessons-archive-{ym}.md"
    header = f"## {category} (归档于 {datetime.now():%Y-%m-%d %H:%M})\n\n"
    existing = archive_path.read_text(encoding="utf-8") if archive_path.exists() else ""
    archive_path.write_text(existing + header + "\n".join(archived) + "\n\n", encoding="utf-8")
    return archive_path


def cmd_append(args: argparse.Namespace) -> int:
    _ensure_file()
    cats = _read_categories()
    cats.setdefault(args.category, [])

    added = 0
    skipped = 0
    truncated = 0
    archived_count = 0

    # lines 参数允许多行,用 \n 或多个 --lines
    raw_lines = args.lines or []
    if isinstance(raw_lines, str):
        raw_lines = raw_lines.splitlines()
    raw_lines = [ln.strip(" -") for ln in raw_lines if ln.strip(" -")]

    for raw in raw_lines:
        text = raw.strip()
        if len(text) > MAX_LINE_CHARS:
            text = text[:MAX_LINE_CHARS - 3] + "..."
            truncated += 1
        entry = f"- [{args.date} {args.company}] {text}"
        if _is_duplicate(entry, cats[args.category]):
            skipped += 1
            continue
        cats[args.category].append(entry)
        added += 1

    # 超限归档
    cats[args.category], archived = _archive_oldest(args.category, cats[args.category])
    if archived:
        _write_archive(args.category, archived)
        archived_count = len(archived)

    _write_categories(cats)

    print(
        f"[lessons_append] category={args.category} added={added} "
        f"skipped_dup={skipped} truncated={truncated} archived={archived_count}",
        file=sys.stderr,
    )
    return 0


def cmd_recent(args: argparse.Namespace) -> int:
    if not LESSONS_FILE.exists():
        return 0  # 无文件 = 无经验,silent OK

    cats = _read_categories()
    lines = cats.get(args.category, [])
    if not lines:
        return 0

    # 解析每行的日期 [yymmdd ...] 过滤近 N 天
    cutoff = datetime.now() - timedelta(days=args.days)
    recent = []
    for ln in lines:
        m = re.match(r"^- \[(\d{6})\s", ln)
        if not m:
            continue
        try:
            d = datetime.strptime(m.group(1), "%y%m%d")
            if d >= cutoff:
                recent.append(ln)
        except ValueError:
            continue

    if recent:
        # 输出到 stdout 供主 agent 拼到 prompt
        print(f"### 近 {args.days} 天 {args.category} 经验提示\n")
        for ln in recent[-args.limit:]:  # 最多 limit 条,默认 20
            print(ln)
        print()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="lessons-learned 全局经验库管理 (v5.1.1)"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_a = sub.add_parser("append", help="追加 lessons 到全局文件")
    p_a.add_argument("--category", required=True, help="sub-agent 名,如 phase3-part4")
    p_a.add_argument("--company", required=True, help="公司名")
    p_a.add_argument("--date", required=True, help="yymmdd,如 260429")
    p_a.add_argument(
        "--lines",
        action="append",
        required=True,
        help="经验内容 (- 前缀可省略),可多次 --lines 或单次传 \\n 分隔",
    )
    p_a.set_defaults(func=cmd_append)

    p_r = sub.add_parser("recent", help="提取近 N 天某类别 lessons")
    p_r.add_argument("--category", required=True)
    p_r.add_argument("--days", type=int, default=30)
    p_r.add_argument("--limit", type=int, default=20)
    p_r.set_defaults(func=cmd_recent)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
