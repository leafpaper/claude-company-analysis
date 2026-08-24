"""assembly — v8 摘要层装配: 决断卡 / 赚钱面板 / Top3 / 主页 metadata / 变化区块。

**零人工抄写**: 唯一输入是五个节点 md 顶部的 fenced YAML verdict 块(契约见 verdict_block)
与 audit 红旗产物; 装配只搬运与合并, 不产任何新结论——
  · 决断卡五行 = 五个节点的 verdict 原文(赔率行机器拼上区间锚与现价);
  · 面板 = 质地节点自选指标 + 红标反查(red_flags), 结论行引用质地子判定①②;
  · Top3 = 红旗清单两源同池机器带出(red_flags.top3);
  · 主页 metadata = 行动档位人话(决策 verdict)+ 质地字段;
  · 变化区块 = 新旧 YAML 块 diff(增量复查票 09 直接复用)。

产物过 assembly.schema.json; 渲染(首页/五章/附录A-E)在 assemble_report_v8。
"""
from __future__ import annotations

import re
from pathlib import Path

from . import derivation
from . import red_flags as rf
from . import verdict_block

NODE_SCHEMAS = {
    "quality": "node-quality",
    "state": "node-state",
    "odds": "node-odds",
    "path": "node-path",
    "decision": "node-decision",
}
NODE_FILES = {node: f"node-{node}.md" for node in NODE_SCHEMAS}
NODE_LABELS = dict(rf.NODE_LABELS, decision="⑤怎么办")

# 决断卡五行: (问题, 出处节点) —— 问题名由 assembly.schema.json 锁定
CARD_ROWS = (
    ("是不是好公司", "quality"),
    ("在变好吗", "state"),
    ("贵不贵", "odds"),
    ("扛得住吗", "path"),
    ("怎么办", "decision"),
)

# 面板结论行引用的两个质地子判定(05: 面板不下新结论)
PANEL_CONCLUSION_QUESTIONS = {"biz_model": "生意模式赚钱吗", "quality_true": "赚钱质量真吗"}

# 行动档位的三档态度带(进攻/观望/撤退)。「跨两档」= 跨越两个带(如 核心仓→回避),
# 增量复查硬规则 2 用它判「建议全量重跑」; 东山中报场景 A(等证据临界→回避)= 跨一档, 不触发。
GEAR_BANDS = {"核心仓": 0, "期权仓": 0, "等证据临界": 1, "不追高": 1, "减仓": 2, "回避": 2}

# 质地字段(主页卡片)= verdict 的第一个短语
_QUALITY_FIELD_SPLIT = re.compile(r"[———,,;;((\(]")


class AssemblyError(ValueError):
    """节点块缺失 / 不过 schema / 引用不到红旗——装配拒绝产出半成品。"""


# ---------------------------------------------------------------- 输入

def load_nodes(nodes_dir) -> dict[str, dict]:
    """读 nodes/ 下五个节点 md 的顶部 YAML 块并逐个过 schema。任一不合法即抛错。"""
    nodes_dir = Path(nodes_dir)
    blocks, problems = {}, []
    for node, fname in NODE_FILES.items():
        path = nodes_dir / fname
        if not path.exists():
            problems.append(f"{fname}: 文件不存在")
            continue
        try:
            data, errs = verdict_block.load_and_validate(path, NODE_SCHEMAS[node])
        except verdict_block.BlockNotFound as exc:
            problems.append(f"{fname}: {exc}")
            continue
        problems.extend(f"{fname} → {e}" for e in errs)
        blocks[node] = data
    if problems:
        raise AssemblyError("节点 YAML 块不合契约:\n  - " + "\n  - ".join(problems))
    return blocks


def load_node_bodies(nodes_dir, nodes: dict[str, dict] | None = None) -> dict[str, str]:
    """读五个节点 md 的正文(剥掉顶部 YAML 块与写手自带的章节标题行)。

    给了 `nodes`(已过 schema 的五块)就顺手把③赔率正文里的
    `{{sotp}}` / `{{discount_rate}}` / `{{dcf}}` 占位换成机器渲染的表(票 11)——
    **装配与 lint 必须传同一个 nodes**, 否则 R10「报告与节点同步」会拿展开前的正文
    去比展开后的报告, 每次都判不同步。
    """
    nodes_dir = Path(nodes_dir)
    bodies = {}
    for node, fname in NODE_FILES.items():
        path = nodes_dir / fname
        if not path.exists():
            continue
        body = strip_yaml_block(path.read_text(encoding="utf-8"), node)
        if node == "odds" and nodes:
            body = derivation.expand_tables(body, nodes.get("odds") or {})
        bodies[node] = body
    return bodies


_TOP_BLOCK = re.compile(r"\A\s*```yaml[ \t]*\n.*?\n[ \t]*```[ \t]*\n?", re.DOTALL)
_LEADING_HEADING = re.compile(r"\A\s*(#{1,2} [^\n]*)\n")
# 章节标题的识别词(只有这类标题才由装配统一发, 正文内的小标题一概保留)
CHAPTER_KEYWORDS = {
    "quality": ("①", "质地"), "state": ("②", "状态"), "odds": ("③", "赔率"),
    "path": ("④", "路径"), "decision": ("⑤", "怎么办"),
}


def strip_yaml_block(md_text: str, node: str | None = None) -> str:
    """去掉顶部 YAML 块; 正文若自带本章的章节标题(# / ##)一并去掉——章标题由装配统一发。"""
    body = _TOP_BLOCK.sub("", md_text, count=1)
    m = _LEADING_HEADING.match(body)
    if m and node and any(kw in m.group(1) for kw in CHAPTER_KEYWORDS[node]):
        body = body[m.end():]
    return body.strip("\n")


# ---------------------------------------------------------------- 决断卡 / 面板 / metadata

def _fmt_number(value) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def odds_card_text(odds: dict) -> str:
    """赔率行 = verdict + 区间锚两端 (+ 现价对比 / 不同向标记), 机器拼装。"""
    anchor = odds["anchor_range"]
    low, high = anchor["low"], anchor["high"]
    unit = low.get("unit") or high.get("unit") or ""
    text = f"{odds['verdict']};锚区间 {_fmt_number(low['value'])}-{_fmt_number(high['value'])}"
    if unit:
        text += f" {unit}"
    if not anchor.get("same_direction", True):
        text += "(两端不同向:取决于口径)"
    price = odds.get("current_price")
    if price:
        text += f" vs 现价 {_fmt_number(price['value'])}"
        p_unit = price.get("unit") or unit
        if p_unit:
            text += f" {p_unit}"
    return text


def build_verdict_card(nodes: dict[str, dict]) -> list[dict]:
    """决断卡五行 = 五个节点 verdict 原文(赔率行拼锚区间), 一行一处权威。"""
    card = []
    for question, node in CARD_ROWS:
        block = nodes.get(node)
        if not block:
            raise AssemblyError(f"决断卡缺 {node} 节点块")
        text = odds_card_text(block) if node == "odds" else block["verdict"]
        card.append({"question": question, "verdict": text, "source_node": node})
    return card


def quality_field(quality_verdict: str) -> str:
    """主页质地字段 = 质地 verdict 的第一个短语(如「部分好——真卡位+平庸财务」→「部分好」)。"""
    return _QUALITY_FIELD_SPLIT.split(quality_verdict, 1)[0].strip() or quality_verdict.strip()


def _sub_verdict(block: dict, question: str) -> dict:
    for sub in block.get("sub_verdicts") or []:
        if sub.get("question") == question:
            return sub
    raise AssemblyError(f"质地节点缺子判定「{question}」(面板结论行的引用来源)")


def build_panel(nodes: dict[str, dict], flags: list[dict]) -> dict:
    """赚钱面板 = 质地节点自选 3-5 指标(原样搬运)+ 结论行引用质地子判定①②。

    面板零新结论:结论行是引用, 红标由 red_flags 反查(见 build_assembly 的 red_mark_map)。
    """
    quality = nodes["quality"]
    panel_src = quality["panel"]
    conclusion = {}
    for key, question in PANEL_CONCLUSION_QUESTIONS.items():
        sub = _sub_verdict(quality, question)
        conclusion[key] = f"{sub['judgment']} {sub['question']}"
    return {
        "industry_reason": panel_src["industry_reason"],
        "conclusion": conclusion,
        "indicators": [dict(i) for i in panel_src["indicators"]],
    }


def build_metadata(
    company: str, date: str, nodes: dict[str, dict], next_disclosure_date: str | None = None
) -> dict:
    """主页 metadata: verdict = 行动档位人话(决策 verdict), 另带质地字段与预约披露日。"""
    decision = nodes["decision"]
    meta = {
        "company": company,
        "date": date,
        "action_gear": decision["action_gear"],
        "verdict_plain": decision["verdict"],
        "quality_field": quality_field(nodes["quality"]["verdict"]),
    }
    if next_disclosure_date:
        meta["next_disclosure_date"] = next_disclosure_date
    return meta


# ---------------------------------------------------------------- 变化区块(增量复查)

def _norm(text: str) -> str:
    return re.sub(r"\s+", "", str(text or ""))


# 翻转比对只看 verdict 首短语(判定态度), 破折号/顿号后的论据措辞不算——
# 重评写手必然重写论据, 全文比对会把「买完完美未来(数字更新)」也判成翻转(research/03 场景 A 反例)。
_VERDICT_PHRASE_SPLIT = re.compile(r"[———,,;;::((\(·、]")


def _verdict_phrase(verdict: str) -> str:
    return _norm(_VERDICT_PHRASE_SPLIT.split(str(verdict or ""), 1)[0]) or _norm(verdict)


# 子判定比对只认判定符号(质地的 ✓/⚠️/✗ 可机检); 状态/赔率/路径的子判定是自由文本,
# 重评必然重写措辞, 拿文本比对等于把「数字更新」也判成翻转。
_JUDGMENT_SYMBOLS = {"✓", "⚠️", "✗"}


def _sub_symbol_changes(before: dict, after: dict) -> list[str]:
    old = {s["question"]: s["judgment"] for s in before.get("sub_verdicts") or []}
    new = {s["question"]: s["judgment"] for s in after.get("sub_verdicts") or []}
    return [
        f"{q} {old[q]}→{j}"
        for q, j in new.items()
        if q in old and old[q] != j
        and old[q] in _JUDGMENT_SYMBOLS and j in _JUDGMENT_SYMBOLS
    ]


def _flip_kind(before: dict | None, after: dict | None) -> str | None:
    """翻转种类: "verdict"=判定语(首短语)真变了 / "sub"=判定语没变但子判定符变了 / None=没翻。

    两种都算翻转(进 flipped_nodes、可触发硬规则 2), 但对读者的措辞不同——
    「部分好→部分好」喊"翻转"是自相矛盾(delivery 评审票 09 Round 2), 子判定级的要说"子判定变化"。
    """
    if not before or not after:
        return None
    if _verdict_phrase(before.get("verdict")) != _verdict_phrase(after.get("verdict")):
        return "verdict"
    if _sub_symbol_changes(before, after):
        return "sub"
    return None


def _node_flipped(before: dict | None, after: dict | None) -> bool:
    """判定翻转 = verdict 首短语变化, 或任一子判定的判定符变化(质地 ✓/⚠️/✗ 可机检)。"""
    return _flip_kind(before, after) is not None


def gear_distance(before: str, after: str) -> int:
    """行动档位跨了几档(按进攻/观望/撤退三带算; 未知档位按 0 处理)。"""
    return abs(GEAR_BANDS.get(after, 0) - GEAR_BANDS.get(before, 0))


# 🟢/ℹ️ 是绿灯与信息更新, 不许借「红旗」名头(计数与条目都要分组, 文案与统计必须同源)
SOFT_FLAG_LEVELS = ("🟢", "ℹ️")


def flag_change_is_soft(item: dict) -> bool:
    level = item.get("level") or ""
    if level:
        return level in SOFT_FLAG_LEVELS
    return any(lv in (item.get("note") or "") for lv in SOFT_FLAG_LEVELS)


def _flag_changes(before: list[dict], after: list[dict]) -> list[dict]:
    old = {f["id"]: f for f in before}
    new = {f["id"]: f for f in after}
    changes = []
    for fid, flag in new.items():
        if fid not in old:
            changes.append({"id": fid, "change": "triggered", "level": flag["level"],
                            "note": f"{flag['level']} {flag['title']}"})
        elif old[fid]["level"] != flag["level"]:
            changes.append({
                "id": fid,
                "change": "level_changed",
                "level": flag["level"],
                "note": f"{flag['title']}:{old[fid]['level']}→{flag['level']}",
            })
    for fid, flag in old.items():
        if fid not in new:
            changes.append({"id": fid, "change": "resolved", "level": flag["level"],
                            "note": f"{flag['level']} {flag['title']}"})
    return changes


def _falsification_changes(before: dict | None, after: dict | None) -> list[dict]:
    if not before or not after:
        return []
    old = {f["condition"]: bool(f.get("triggered")) for f in before.get("falsifications") or []}
    out = []
    for item in after.get("falsifications") or []:
        cond, now = item["condition"], bool(item.get("triggered"))
        was = old.get(cond)
        if now and not was:
            out.append({"condition": cond, "change": "triggered"})
        elif was and not now:
            out.append({"condition": cond, "change": "cleared"})
    return out


def build_change_block(
    prev_nodes: dict[str, dict],
    nodes: dict[str, dict],
    prev_flags: list[dict],
    flags: list[dict],
    metric_deltas: list[dict] | None = None,
) -> dict:
    """「较上版变化」区块:新旧 YAML 块 diff, 首句人话答「阿尔法变了没」。

    硬规则 2(票 03/09):质地判定翻转 或 档位跨两档 → advised=True(照常产出, 首页明示建议全量)。
    """
    gear_before = prev_nodes["decision"]["action_gear"]
    gear_after = nodes["decision"]["action_gear"]
    flip_kinds = {
        n: kind for n in rf.NODES
        if (kind := _flip_kind(prev_nodes.get(n), nodes.get(n)))
    }
    flipped = [n for n in rf.NODES if n in flip_kinds]
    flag_changes = _flag_changes(prev_flags, flags)
    fals_changes = _falsification_changes(prev_nodes.get("path"), nodes.get("path"))

    reasons = []
    if flip_kinds.get("quality") == "verdict":
        reasons.append(
            f"质地判定翻转({prev_nodes['quality']['verdict']} → {nodes['quality']['verdict']})"
        )
    elif flip_kinds.get("quality") == "sub":
        details = "、".join(_sub_symbol_changes(prev_nodes["quality"], nodes["quality"]))
        reasons.append(f"质地子判定变化(判定语未变:{details})")
    distance = gear_distance(gear_before, gear_after)
    if distance >= 2:
        reasons.append(f"行动档位跨两档({gear_before} → {gear_after})")
    advice = {
        "advised": bool(reasons),
        "reason": ";".join(reasons) + ",建议全量重跑重锚" if reasons else None,
    }

    return {
        "alpha_summary": _alpha_summary(
            gear_before, gear_after, flip_kinds, flag_changes, fals_changes, nodes
        ),
        "gear_before": gear_before,
        "gear_after": gear_after,
        "triad_before": dict(prev_nodes["decision"]["triad"]),
        "triad_after": dict(nodes["decision"]["triad"]),
        "flipped_nodes": flipped,
        "flip_kinds": flip_kinds,
        "red_flag_changes": flag_changes,
        "falsification_changes": fals_changes,
        "metric_deltas": list(metric_deltas or []),
        "full_rerun_advice": advice,
    }


def _alpha_summary(gear_before, gear_after, flip_kinds, flag_changes, fals_changes, nodes) -> str:
    """首句人话答「阿尔法变了没」——只陈述机器测得的变化, 不自产解释。

    措辞纪律: 「翻转」只留给判定语真变的节点; 判定语未变、子判定符变的说「子判定变化」;
    🟢/ℹ️ 不借「红旗」名头(文案与折叠组计数同源, 见 flag_change_is_soft)。
    """
    triggered = [c for c in fals_changes if c["change"] == "triggered"]
    hard = [c for c in flag_changes if not flag_change_is_soft(c)]
    soft = [c for c in flag_changes if flag_change_is_soft(c)]
    new_flags = [c for c in hard if c["change"] == "triggered"]
    resolved = [c for c in hard if c["change"] == "resolved"]
    level_changed = [c for c in hard if c["change"] == "level_changed"]
    verdict_flips = [n for n, k in flip_kinds.items() if k == "verdict"]
    sub_flips = [n for n, k in flip_kinds.items() if k == "sub"]
    parts = []
    if triggered:
        parts.append(f"证伪触发 {len(triggered)} 条({triggered[0]['condition']})")
    if verdict_flips:
        parts.append("、".join(NODE_LABELS[n] for n in rf.NODES if n in verdict_flips) + "判定翻转")
    if sub_flips:
        parts.append("、".join(NODE_LABELS[n] for n in rf.NODES if n in sub_flips) + "子判定变化(判定语未变)")
    if gear_before != gear_after:
        parts.append(f"档位 {gear_before}→{gear_after}")
    if new_flags:
        parts.append(f"新增红旗 {len(new_flags)} 条")
    if resolved:
        parts.append(f"解除红旗 {len(resolved)} 条")
    if level_changed:
        parts.append(f"红旗级别变化 {len(level_changed)} 条")
    if soft:
        parts.append(f"绿灯/信息更新 {len(soft)} 条")
    if not parts:
        return (
            f"阿尔法没变:三元组与档位维持「{gear_after}」,无节点翻转、无证伪触发、无红旗增减"
            f"(判定:{nodes['decision']['verdict']})"
        )
    return "阿尔法变了:" + ";".join(parts)


# ---------------------------------------------------------------- 总装

def build_assembly(
    company: str,
    date: str,
    nodes: dict[str, dict],
    script_flags: list[dict],
    prev_nodes: dict[str, dict] | None = None,
    prev_script_flags: list[dict] | None = None,
    metric_deltas: list[dict] | None = None,
    appendices: list[dict] | None = None,
    next_disclosure_date: str | None = None,
) -> dict:
    """五个节点块 + 脚本红旗 → 装配产物(过 assembly.schema.json)。"""
    flags = rf.merge(script_flags, rf.collect_nominations(nodes))
    flag_errs = rf.validate_flags(flags)
    if flag_errs:
        raise AssemblyError("附录D 红旗清单不合契约:\n  - " + "\n  - ".join(flag_errs))

    panel = build_panel(nodes, flags)
    product = {
        "verdict_card": build_verdict_card(nodes),
        "panel": panel,
        "top3": rf.top3(flags),
        "metadata": build_metadata(company, date, nodes, next_disclosure_date),
        "red_flags": flags,
        "red_mark_map": rf.red_mark_map(flags, panel["indicators"]),
    }
    intro = nodes["decision"].get("front_page_intro")
    if intro:
        product["front_page_intro"] = intro          # 首页唯一人工位: decision-writer 的 3-5 句导读
    if appendices is not None:
        product["appendices"] = appendices
    if prev_nodes:
        prev_flags = rf.merge(list(prev_script_flags or []), rf.collect_nominations(prev_nodes))
        product["change_block"] = build_change_block(
            prev_nodes, nodes, prev_flags, flags, metric_deltas
        )

    errs = verdict_block.validate(product, "assembly")
    if errs:
        raise AssemblyError("装配产物不过 schema:\n  - " + "\n  - ".join(errs))
    return product
