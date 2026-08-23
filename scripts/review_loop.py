"""review_loop.py — v8 质量环:两个 reviewer 的判定合并 + FIX 分诊 + 对抗检测。

主 agent 视角的工作流(细节见 `phases/phase6-review-publish.md`):

    1. 机器门控先过:`{PYBIN} -m scripts.lint_v8 --run-dir {run_dir}` 退出码 0
    2. 并行启动两个 reviewer(`run_in_background=True`):reviewer-logic ∥ reviewer-delivery
    3. 两份响应 Write 到:
         {run_dir}/reviewer_responses/round_{N}_logic.md
         {run_dir}/reviewer_responses/round_{N}_delivery.md
    4. 跑本脚本:
         {PYBIN} -m scripts.review_loop --run-dir {run_dir} --round N
    5. 读它的 JSON 决定下一步:
         overall_pass=true  → Part B 出片发布
         diff_repeat=true   → 转人工(两轮改回原状 = 对抗)
         否则               → 按 restart_writers / edit_targets 应用 FIX,重跑装配 + lint,Round+1

**FIX 行格式**(reviewer 必须照写,本脚本按它分诊):

    - [FIX-{node}-{kind}] {问题≤30 字} → {建议≤60 字}

    node ∈ quality | state | odds | path | decision | front(首页导读)| delivery(HTML 交付)
    kind ∈ 判断 | 表述

**分诊规则**(v8 修正循环的落点,agent-protocol §4.2):

| kind | 落点 | 谁动手 |
|---|---|---|
| 判断 | 该节点的 YAML 块与正文 | **fresh-restart 对应写手**(主 agent 不许手改 YAML 块) |
| 表述 | 该节点 md 的正文 | 主 agent 用 Edit 改措辞 |
| node=front | 决策块的 `front_page_intro` | fresh-restart decision-writer(那是 YAML 字段) |
| node=delivery | HTML 模板 / 渲染 | 主 agent 改 `assets/html/` 或重跑 build_html,不惊动写手 |

两类 FIX 应用完都必须**重跑 `assemble_report_v8` + `lint_v8`**——报告是装配产物,改了节点不重装
= 报告与节点脱节(lint R10 会当场抓到)。

为什么脚本不直接改文件:应用 FIX 要理解「问题 → 建议」的语义再定位落点,那是 LLM 的活;
脚本只做确定性的部分:解析、合并去重、分诊、算 diff signature。

CLI:
    python -m scripts.review_loop --run-dir output/东山精密/runs/2026-06-22 --round 1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REVIEWERS = ("logic", "delivery")
REVIEWER_LABELS = {"logic": "reviewer-logic(判断链逻辑)", "delivery": "reviewer-delivery(可读性与交付)"}

# FIX 的落点 → 该由哪个 sub-agent fresh-restart(delivery 无写手, 归主 agent)
NODE_AGENTS = {
    "quality": "node-quality",
    "state": "node-state",
    "odds": "node-odds",
    "path": "node-path",
    "decision": "decision-writer",
    "front": "decision-writer",          # 首页导读 = 决策块的 front_page_intro 字段
}
NODE_LABELS = {
    "quality": "①质地", "state": "②状态", "odds": "③赔率", "path": "④路径",
    "decision": "⑤怎么办", "front": "首页导读", "delivery": "HTML 交付",
}
NODES = tuple(NODE_LABELS)
KINDS = ("判断", "表述")

FIX_RE = re.compile(
    r"^- \[FIX-(?P<node>" + "|".join(NODES) + r")-(?P<kind>判断|表述)\][^\n]*→[^\n]*$",
    re.MULTILINE,
)
JUDGMENT_RE = re.compile(
    r"^#{2,4}\s+(?:维度\s*\d*[^:：]*|总体)[:：]\s*(PASS|FAIL|部分降级)", re.MULTILINE
)


def parse_reviewer_response(text: str) -> dict:
    """解析单个 reviewer 响应:判定 + FIX 行。

    判定行两种写法都认(`### 维度 1 …: PASS` / `### 总体: FAIL`), 标题层级 `##`-`####` 都收——
    reviewer 用 `##` 还是 `###` 起头纯属笔头习惯, 不该让整份判定丢成 UNKNOWN(票 08 实测踩到)。
    找不到判定 → UNKNOWN(fail-closed: overall_pass 要求全 PASS, 主 agent 按 FAIL 处理)。
    """
    m = JUDGMENT_RE.search(text)
    return {
        "judgment": m.group(1) if m else "UNKNOWN",
        "fixes": [m.group(0) for m in FIX_RE.finditer(text)],
    }


def merge_fix_lists(fixes_by_reviewer: dict[str, list[str]]) -> list[str]:
    """合并两个 reviewer 的 FIX,逐行去重;保序(logic → delivery, 各自内部按出现序)。"""
    merged, seen = [], set()
    for reviewer in REVIEWERS:
        for fix in fixes_by_reviewer.get(reviewer, []):
            if fix not in seen:
                merged.append(fix)
                seen.add(fix)
    return merged


def triage(fixes: list[str]) -> dict:
    """把 FIX 按 (落点, 类型) 分诊 → 谁 fresh-restart、谁 Edit。"""
    by_node = {n: [] for n in NODES}
    by_kind = {k: [] for k in KINDS}
    for fix in fixes:
        m = FIX_RE.match(fix)
        if not m:
            continue
        by_node[m.group("node")].append(fix)
        by_kind[m.group("kind")].append(fix)

    restart, edits = [], []
    for fix in fixes:
        m = FIX_RE.match(fix)
        if not m:
            continue
        node, kind = m.group("node"), m.group("kind")
        if node == "delivery":
            continue                          # 交付类不惊动写手: 主 agent 改模板 / 重跑 build_html
        if kind == "判断" or node == "front":  # front_page_intro 在 YAML 块里, 只能写手改
            agent = NODE_AGENTS[node]
            if agent not in restart:
                restart.append(agent)
        else:
            target = f"nodes/node-{node}.md"
            if target not in edits:
                edits.append(target)
    return {
        "by_node": by_node,
        "by_kind": by_kind,
        "restart_writers": restart,
        "edit_targets": edits,
    }


def compute_diff_signature(run_dir: Path) -> str:
    """五个节点 md 的 md5 拼接签名(连续两轮相同 = LLM 把改动又改回去了)。"""
    h = hashlib.md5()
    for node in ("quality", "state", "odds", "path", "decision"):
        p = Path(run_dir) / "nodes" / f"node-{node}.md"
        h.update(p.read_bytes() if p.exists() else b"<MISSING>")
    return h.hexdigest()


def get_prev_round_signature(run_dir: Path, round_n: int) -> str | None:
    if round_n <= 1:
        return None
    sig_file = Path(run_dir) / "reviewer_responses" / f"round_{round_n - 1}_signature.txt"
    return sig_file.read_text(encoding="utf-8").strip() if sig_file.exists() else None


def save_current_signature(run_dir: Path, round_n: int, sig: str) -> None:
    sig_file = Path(run_dir) / "reviewer_responses" / f"round_{round_n}_signature.txt"
    sig_file.parent.mkdir(parents=True, exist_ok=True)
    sig_file.write_text(sig, encoding="utf-8")


def write_merged_fix_md(fixes: list[str], plan: dict, out_path: Path, round_n: int) -> None:
    """合并后的 FIX 列表 + 应用步骤,写成 markdown 给主 agent 读。"""
    lines = [
        f"# Round {round_n} 合并 FIX 列表 (v8 质量环)",
        "",
        f"**共 {len(fixes)} 条**(reviewer-logic + reviewer-delivery 去重合并)",
        "",
    ]
    for node in NODES:
        node_fixes = plan["by_node"][node]
        if not node_fixes:
            continue
        if node == "delivery":
            where = "HTML 模板 / 渲染(assets/html/ 或 build_html)"
        else:
            where = f"nodes/node-{node}.md"
        lines += [f"## {NODE_LABELS[node]} → `{where}`({len(node_fixes)} 条)", ""]
        lines += node_fixes
        lines.append("")
    if not fixes:
        lines.append("(无 FIX 条目)")

    lines += [
        "---",
        "",
        "## 应用步骤",
        "",
        "1. **判断类 FIX**(改 verdict / 子判定 / 提名 / 首页导读)→ fresh-restart 对应写手,"
        "prompt 注入本轮 FIX 原文 + 「只看当前文件状态」;主 agent **不手改 YAML 块**。",
    ]
    if plan["restart_writers"]:
        lines.append(f"   - 本轮要重启:{', '.join(plan['restart_writers'])}")
    lines.append(
        "2. **表述类 FIX**(措辞 / 结论先行 / 人话)→ 主 agent 用 Edit 改对应节点 md 的**正文**。"
    )
    if plan["edit_targets"]:
        lines.append(f"   - 本轮要改:{', '.join(plan['edit_targets'])}")
    if plan["by_node"]["delivery"]:
        lines.append(
            "3. **交付类 FIX**(版式 / 移动端 / 主题)→ 改 `assets/html/report-v8.{html,css}` "
            "或 build_html 渲染,不惊动写手。"
        )
    lines += [
        "",
        "4. 全部 FIX 应用后按顺序重跑(缺一不可):",
        "",
        "   ```",
        "   {PYBIN} -m scripts.assemble_report_v8 --run-dir {run_dir} --company {company} --date {date} …",
        "   {PYBIN} -m scripts.lint_v8 --run-dir {run_dir}",
        "   ```",
        "",
        "5. Round+1:重新并行启动两个 reviewer(fresh-restart,prompt 注明本轮 FIX 已应用)。",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(run_dir: Path, round_n: int) -> dict:
    """读两份 reviewer 响应 → 判定 / FIX 分诊 / 对抗检测。返回给主 agent 的 JSON 结构。"""
    run_dir = Path(run_dir)
    resp_dir = run_dir / "reviewer_responses"
    if not resp_dir.is_dir():
        return {"error": f"reviewer_responses/ 不存在, 先把两份响应写进去: {resp_dir}"}

    judgments, fixes_by_reviewer, missing = {}, {}, []
    for reviewer in REVIEWERS:
        path = resp_dir / f"round_{round_n}_{reviewer}.md"
        if not path.exists():
            missing.append(str(path))
            continue
        parsed = parse_reviewer_response(path.read_text(encoding="utf-8"))
        judgments[reviewer] = parsed["judgment"]
        fixes_by_reviewer[reviewer] = parsed["fixes"]
    if missing:
        return {"error": "缺少 reviewer 响应文件", "missing": missing}

    merged = merge_fix_lists(fixes_by_reviewer)
    plan = triage(merged)

    current_sig = compute_diff_signature(run_dir)
    prev_sig = get_prev_round_signature(run_dir, round_n)
    save_current_signature(run_dir, round_n, current_sig)

    fix_md_path = resp_dir / f"round_{round_n}_merged_fix.md"
    write_merged_fix_md(merged, plan, fix_md_path, round_n)

    return {
        "overall_pass": all(j == "PASS" for j in judgments.values()),
        "judgments": judgments,
        "fix_count": len(merged),
        "fix_by_node": {n: len(v) for n, v in plan["by_node"].items() if v},
        "fix_by_kind": {k: len(v) for k, v in plan["by_kind"].items()},
        "restart_writers": plan["restart_writers"],
        "edit_targets": plan["edit_targets"],
        "delivery_fixes": len(plan["by_node"]["delivery"]),
        "fix_list_path": str(fix_md_path),
        "diff_repeat": prev_sig is not None and current_sig == prev_sig,
        "diff_signature": current_sig,
        "round": round_n,
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):      # Windows 控制台 GBK 下 print 中文/emoji 会炸
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    ap = argparse.ArgumentParser(description="v8 质量环: 两 reviewer 判定合并 + FIX 分诊")
    ap.add_argument("--run-dir", required=True, help="runs/{date}/ 目录(含 reviewer_responses/)")
    ap.add_argument("--round", type=int, required=True, help="本轮 round 编号 (1-3)")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(json.dumps({"error": f"run-dir 不存在: {run_dir}"}, ensure_ascii=False))
        return 1

    result = run(run_dir, args.round)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result.get("error") else 0


if __name__ == "__main__":
    sys.exit(main())
