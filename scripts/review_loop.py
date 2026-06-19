"""review_loop.py — v5.1.3 reviewer 修正循环辅助脚本

设计目标:
    替代 SKILL.md 里的伪代码 `apply_fix_to_parts()` / `wait_all_background_agents()`
    等不存在的"函数"。主 agent 用 Bash 工具调本脚本,脚本输出 JSON 结果给主 agent
    decide 下一步。

工作流(主 agent 视角):
    1. 主 agent 用 Agent 工具并行启动 3 个 reviewer (run_in_background=True)
       — reviewer-narrative / reviewer-valuation / reviewer-redflag
    2. 等 3 个完成,主 agent 把 3 份响应文本 Write 到:
         output/{company}/reviewer_responses/round_{N}_narrative.md
         output/{company}/reviewer_responses/round_{N}_valuation.md
         output/{company}/reviewer_responses/round_{N}_redflag.md
    3. 主 agent 用 Bash 跑:
         python3 -m scripts.review_loop \\
             --company {company} --date {date} \\
             --output-dir output/{company}/ --round N
    4. 脚本输出 JSON:
       {
         "overall_pass": false,
         "judgments": {"narrative": "FAIL", "valuation": "PASS", "redflag": "FAIL"},
         "fix_count": 5,
         "fix_list_path": "output/{company}/reviewer_responses/round_N_merged_fix.md",
         "diff_repeat": false,
         "fix_by_part": {"P1": 2, "P4": 3}
       }
    5. 主 agent 看 JSON 决定:
       - overall_pass=true → Part B
       - diff_repeat=true → 转人工
       - 否则: 主 agent Read fix_list_path,用 Edit 工具改 phase3-partN.md,
         重新 assemble + lint,Round+1 重新启动 3 reviewer

为什么主 agent 不直接读响应:
    - 主 agent context 应该保持干净,只看 JSON 决定决策
    - 详细 FIX 列表 LLM 不需要重复"读懂",只要 Edit 应用

为什么脚本不直接 Edit part 文件:
    - 应用 FIX 需要 LLM 理解"问题简述 → 建议"语义,然后到 part 里精准 Edit
      (位置、措辞、上下文都需判断),脚本无法干
    - 脚本只负责: 合并 FIX 列表 / 去重 / 算 diff signature

CLI:
    python3 -m scripts.review_loop \\
        --company 实丰文化 --date 2026-05-04 \\
        --output-dir output/实丰文化/ --round 1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# 章节 → Part 文件映射(与 assemble_report.py PART_EXPECTED_SECTIONS 一致, v6.0 — 4 part)
PART_SECTION_MAP = {
    "P1": ["§一"],
    "P2": ["§二", "§三"],
    "P3": ["§四", "§五"],
    "P4": ["§六", "§七", "§八"],
}
N_PARTS = len(PART_SECTION_MAP)

REVIEWER_NAMES = ("narrative", "valuation", "redflag")


def parse_reviewer_response(text: str) -> dict:
    """解析单个 reviewer 响应,提取判定 + FIX 列表。

    支持两种判定格式(reviewer-narrative/valuation/redflag 各自略不同):
    - `### 维度 N {名}: PASS/FAIL`
    - `### 总体: PASS/FAIL` (旧 reviewer 兼容)

    FIX 行格式:`- [FIX-P{1-4}-§{X}] {问题} → {建议}`
    """
    # 判定: 找第一个 PASS/FAIL
    judgment = "UNKNOWN"
    m = re.search(r"^###\s+(?:维度\s*\d+[^:]*|总体)[:：]\s*(PASS|FAIL|部分降级)",
                  text, re.MULTILINE)
    if m:
        judgment = m.group(1)

    # FIX 列表
    fix_lines = re.findall(r"^- \[FIX-P[1-4]-§[^\]]+\] .+ → .+$",
                           text, re.MULTILINE)

    return {"judgment": judgment, "fixes": fix_lines}


def merge_fix_lists(all_fixes_by_reviewer: dict[str, list[str]]) -> list[str]:
    """合并 3 reviewer 的 FIX 列表,去重(同一 FIX 行只保留一次)。
    保序: 按 reviewer 顺序(narrative → valuation → redflag),同 reviewer 内按出现顺序。
    """
    merged = []
    seen = set()
    for r in REVIEWER_NAMES:
        for fix in all_fixes_by_reviewer.get(r, []):
            if fix not in seen:
                merged.append(fix)
                seen.add(fix)
    return merged


def categorize_fixes_by_part(fixes: list[str]) -> dict[str, list[str]]:
    """把 FIX 行按 P1-P4 分组。"""
    by_part = {p: [] for p in PART_SECTION_MAP.keys()}
    for fix in fixes:
        m = re.match(r"^- \[FIX-(P[1-4])-", fix)
        if m:
            p = m.group(1)
            by_part[p].append(fix)
    return by_part


def compute_diff_signature(output_dir: Path) -> str:
    """计算 phase3-part{1-4}.md 4 个文件的 md5 拼接签名。
    用于检测 diff 对抗(连续 2 轮 signature 重复 = LLM 反复改回原状)。
    """
    h = hashlib.md5()
    for n in range(1, N_PARTS + 1):
        p = output_dir / f"phase3-part{n}.md"
        if p.exists():
            h.update(p.read_bytes())
        else:
            h.update(b"<MISSING>")
    return h.hexdigest()


def write_merged_fix_md(fix_list: list[str], by_part: dict, out_path: Path,
                       round_n: int) -> None:
    """把合并后的 FIX 列表写为 markdown 给主 agent 读。"""
    lines = [
        f"# Round {round_n} 合并后 FIX 列表 (v5.1.3)",
        "",
        f"**共 {len(fix_list)} 条** (3 reviewer 去重合并)",
        "",
        "## 按 Part 分组(主 agent Edit 时按此分组应用)",
        "",
    ]
    for part, fixes in by_part.items():
        if not fixes:
            continue
        part_file = f"phase3-part{part[-1]}.md"
        lines.append(f"### {part} → `{part_file}` ({len(fixes)} 条)")
        lines.append("")
        for fix in fixes:
            lines.append(fix)
        lines.append("")

    if not any(by_part.values()):
        lines.append("(无 FIX 条目)")

    lines.extend([
        "",
        "---",
        "",
        "## 主 agent 应用步骤",
        "",
        "1. 对每个非空 Part:",
        "   - Read 对应 `phase3-part{N}.md`",
        "   - 按 FIX 的 `问题 → 建议` 用 Edit 工具改文件",
        "2. 全部 FIX 应用后,运行 `python3 -m scripts.assemble_report ...` 重拼主报告",
        "3. 运行 `python3 -m scripts.anti_lazy_lint ...` 重跑机械检查",
        "4. Round+1: 重新并行启动 3 个 reviewer (fresh-restart, prompt 注入本 FIX 列表已应用)",
    ])

    out_path.write_text("\n".join(lines), encoding="utf-8")


def get_prev_round_signature(output_dir: Path, round_n: int) -> str | None:
    """读上一轮的 diff signature(从 .signature 文件)。"""
    if round_n <= 1:
        return None
    sig_file = output_dir / "reviewer_responses" / f"round_{round_n - 1}_signature.txt"
    if sig_file.exists():
        return sig_file.read_text(encoding="utf-8").strip()
    return None


def save_current_signature(output_dir: Path, round_n: int, sig: str) -> None:
    """保存本轮 signature 供下轮对比。"""
    sig_file = output_dir / "reviewer_responses" / f"round_{round_n}_signature.txt"
    sig_file.parent.mkdir(parents=True, exist_ok=True)
    sig_file.write_text(sig, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="reviewer 3 维度判定合并 + FIX 处理 + 对抗检测 (v5.1.3)"
    )
    ap.add_argument("--company", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--output-dir", required=True,
                    help="output/{company}/ 目录")
    ap.add_argument("--round", type=int, required=True,
                    help="本轮 round 编号 (1-3)")
    args = ap.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        print(json.dumps({"error": f"output-dir 不存在: {output_dir}"}))
        return 1

    resp_dir = output_dir / "reviewer_responses"
    if not resp_dir.exists():
        print(json.dumps({
            "error": f"reviewer_responses/ 目录不存在,主 agent 需先把 3 reviewer 响应 Write 到此目录"
        }))
        return 1

    # 读 3 份 reviewer 响应
    judgments = {}
    fixes_by_reviewer = {}
    missing = []
    for r in REVIEWER_NAMES:
        path = resp_dir / f"round_{args.round}_{r}.md"
        if not path.exists():
            missing.append(str(path))
            continue
        parsed = parse_reviewer_response(path.read_text(encoding="utf-8"))
        judgments[r] = parsed["judgment"]
        fixes_by_reviewer[r] = parsed["fixes"]

    if missing:
        print(json.dumps({
            "error": "缺少 reviewer 响应文件",
            "missing": missing,
        }, ensure_ascii=False))
        return 2

    # 综合判定
    overall_pass = all(j == "PASS" for j in judgments.values())

    # 合并 + 分组
    merged_fix = merge_fix_lists(fixes_by_reviewer)
    by_part = categorize_fixes_by_part(merged_fix)
    fix_by_part_count = {p: len(v) for p, v in by_part.items()}

    # diff signature 对抗检测
    current_sig = compute_diff_signature(output_dir)
    prev_sig = get_prev_round_signature(output_dir, args.round)
    diff_repeat = (prev_sig is not None and current_sig == prev_sig)
    save_current_signature(output_dir, args.round, current_sig)

    # 写合并后 FIX markdown
    fix_md_path = resp_dir / f"round_{args.round}_merged_fix.md"
    write_merged_fix_md(merged_fix, by_part, fix_md_path, args.round)

    # 输出 JSON
    result = {
        "overall_pass": overall_pass,
        "judgments": judgments,
        "fix_count": len(merged_fix),
        "fix_by_part": fix_by_part_count,
        "fix_list_path": str(fix_md_path),
        "diff_repeat": diff_repeat,
        "diff_signature": current_sig,
        "round": args.round,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
