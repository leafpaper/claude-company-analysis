"""lint_v8 — v8 质量环的机器门控:判断链节点块 + 装配后的报告。

取代 v7 的 `anti_lazy_lint`(章节字数下限 / artifact 关键短语覆盖率 / 9 章节骨架比对)——
那三条与 v8 的「章预算是上限 + 全表下沉附录 + 章节=判断链」正面冲突,随判断链收敛删除。
留下来改写的三条:外链引用、决策字段齐全(改查 YAML 块)、无记忆性反例。

判定对象 = 一个 run 目录:
    runs/{date}/nodes/node-{quality,state,odds,path,decision}.md   五块 YAML verdict + 正文(=五章)
    runs/{date}/assembly/assembly.json                             装配产物(决断卡/面板/Top3/红标)
    runs/{date}/{company}-analysis-{date}.md                       主报告(首页 + 五章 + 附录A-E)

规则(fail 阻断 / warn 提示):

| # | 规则 | 级别 | 判什么 |
|---|---|---|---|
| R1 | 五块 schema 校验 | fail | 五个节点 md 顶部 YAML 块逐块过 `scripts/schemas/` |
| R2 | 红旗闭环 | fail + warn | Top3/清单与节点块重算一致;🔴 未在归属节点叙述 = fail,🟠 = warn |
| R3 | 数字唯一 home | fail | 同一数字跨章出现时, 异地那处必须带出处引用(①-⑤ / 附录A-E) |
| R4 | 章预算 | warn | 链手册 §1.3 的行数上限(70/60/70/60/50)与主体合计上限 |
| R5 | 区间锚 | fail | 同向标记必填、不同向必写分歧原因、两端不倒置、verdict 与现价方向自洽 |
| R6 | 外链引用 | fail | 正文禁「详见 xxx.md」「[x](x.md)」这类把内容推给附件的写法 |
| R7 | 决策字段 + 封顶 | fail | 决策块字段齐全;有 🔴 致命红旗 → 档位必须封顶「回避」且 gear_cap 已触发 |
| R8 | 越权发声 | fail | 仓位 / 行动档位 / 买卖建议只能出现在⑤决策(链手册 §2.8) |
| R9 | 无记忆性反例 | fail | 禁「跌久了该涨 / 估值压久了该修复」当买入理由 |
| R10 | 报告与节点同步 | fail | 主报告五章正文 = 节点 md 正文(改完正文没重跑装配, 在这里现形) |

CLI:
    python -m scripts.lint_v8 --run-dir output/{company}/runs/{date}
    python -m scripts.lint_v8 --run-dir ... --md ... --artifacts-dir output/{company}

退出码:0 = 无 fail(warn 不阻断) · 1 = 有 fail · 2 = run 目录不完整(没法判)

集成点:Phase 6 Step 0(两个 reviewer 之前的机器门控)· `scripts/build_html.py` v8 通道写 HTML 前。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import assemble_report_v8 as render
from . import assembly
from . import red_flags as rf
from . import verdict_block

CHAPTER_ORDER = ("quality", "state", "odds", "path", "decision")
LABELS = assembly.NODE_LABELS                       # quality→①质地 … decision→⑤怎么办

# 章预算(references/judgment-chain.md §1.3;软目标,超了先想「能不能下沉附录」)
CHAPTER_BUDGET = {"quality": 70, "state": 60, "odds": 70, "path": 60, "decision": 50}
BODY_TOTAL_MAX = 400                                # 主体合计软上限(下限规则已随 v8 删除)

FAIL, WARN = "fail", "warn"


@dataclass
class RuleResult:
    name: str
    severity: str = FAIL
    passed: bool = True
    detail: str = ""
    findings: list[str] = field(default_factory=list)
    skipped: bool = False


@dataclass
class LintResult:
    run_dir: Path
    rules: list[RuleResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.rules if r.severity == FAIL)

    @property
    def warnings(self) -> list[RuleResult]:
        return [r for r in self.rules if r.severity == WARN and not r.passed]

    @property
    def report(self) -> str:
        lines = [f"[lint_v8] run 目录: {self.run_dir}"]
        for r in self.rules:
            if r.skipped:
                mark = "⏭️ SKIP"
            elif r.passed:
                mark = "✅ PASS"
            else:
                mark = "❌ FAIL" if r.severity == FAIL else "⚠️ WARN"
            lines.append(f"  {r.name}: {mark}{('  — ' + r.detail) if r.detail else ''}")
            for f in r.findings[:8]:
                lines.append(f"    {f}")
            if len(r.findings) > 8:
                lines.append(f"    … (还有 {len(r.findings) - 8} 条)")
        failed = [r.name for r in self.rules if r.severity == FAIL and not r.passed]
        warned = [r.name for r in self.warnings]
        lines.append("")
        if failed:
            lines.append(f"总结: {len(failed)} 项 fail ({', '.join(failed)}) → exit 1")
        else:
            lines.append("总结: fail 项全过 → exit 0")
        if warned:
            lines.append(f"      {len(warned)} 项 warn ({', '.join(warned)}) — 不阻断, 但请自检")
        return "\n".join(lines)


# ============================================================================
# 通用工具
# ============================================================================
def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _body_lines(body: str) -> list[str]:
    return [l for l in body.splitlines() if l.strip()]


# 数字短语 = 数字 + 单位(年/月/日不算——那是时间不是事实数字)
NUMBER_PHRASE = re.compile(
    r"\d[\d,]*(?:\.\d+)?\s*(?:%|亿元|亿美元|亿|万元|万手|万|元|美元|港元|倍|pp|个百分点|bp|x|户|股|名|次)"
)
# 「带出处的引用」= 指向别的章或附录(链手册 §4.5 允许的异地写法)
CITATION = re.compile(r"[①②③④⑤]|附录[A-E]")

# 两位整数百分比(30% / 16% / 46%…)撞车率极高、信息量极低:R3 按数字串比对、不认指标,
# 东山实测「光模块毛利率跌破 30%」(②状态)与「DCF 情景概率 / 收入 CAGR 30%」(③赔率)
# 被判成同一个数字 —— 照它的要求加出处会写出假话(等于说 DCF 概率来自一个毛利率阈值)。
# 所以整百分点的两位数不进 home 追踪;带小数或带量纲的(30.5% / 3,306 亿)照常判。
_COLLIDING_PCT = re.compile(r"\d{1,2}%")


def split_report(md_text: str) -> dict[str, str]:
    """把装配后的主报告按 `## ` 切成 {标题: 正文};段间分隔线 `---` 不计入正文。"""
    out: dict[str, str] = {}
    heads = list(re.finditer(r"^## (.+)$", md_text, re.MULTILINE))
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(md_text)
        body = md_text[m.end():end]
        body = re.sub(r"\n+-{3,}\s*$", "\n", body)
        out[m.group(1).strip()] = body.strip("\n")
    return out


def report_chapters(md_text: str) -> dict[str, str]:
    """主报告里的五章正文(按 assemble_report_v8.CHAPTERS 的标题定位)。"""
    sections = split_report(md_text)
    return {node: sections[title] for node, title in render.CHAPTERS if title in sections}


# ============================================================================
# R1 五块 schema
# ============================================================================
def rule_schema(nodes_dir: Path) -> tuple[RuleResult, dict | None]:
    try:
        nodes = assembly.load_nodes(nodes_dir)
    except assembly.AssemblyError as exc:
        findings = [l.strip().lstrip("- ") for l in str(exc).splitlines()[1:]]
        return RuleResult(
            name="R1 五块 schema 校验", passed=False,
            detail=f"{len(findings)} 处不合契约(判断类问题 fresh-restart 写手, 不许手改 YAML 块)",
            findings=findings,
        ), None
    return RuleResult(
        name="R1 五块 schema 校验", detail="五个节点 YAML 块全部合契约"
    ), nodes


# ============================================================================
# R2 红旗闭环(归家 + Top3 一致)
# ============================================================================
_TOKEN_SPLIT = re.compile(r"[^\w一-龥]+")


def flag_tokens(flag: dict) -> list[str]:
    """红旗的「叙述指纹」= 标题里的词 + 证据里的前两个数字短语(命中任一即算讲过)。"""
    tokens = [t for t in _TOKEN_SPLIT.split(flag.get("title", "")) if len(t) >= 2]
    tokens += [m.group(0) for m in NUMBER_PHRASE.finditer(_squash(flag.get("evidence", "")))][:2]
    return tokens


def _mentions(body: str, tokens: list[str]) -> bool:
    squashed = _squash(body)
    return any(_squash(t) in squashed for t in tokens)


def rule_red_flag_closure(
    bodies: dict[str, str], flags: list[dict], product: dict | None
) -> tuple[RuleResult, RuleResult]:
    """fail:Top3/清单与节点块重算不一致、🔴 未归家;warn:🟠 未归家。"""
    fails: list[str] = []
    warns: list[str] = []

    # 清单为空 = 没跑 audit 也没人提名(装配本身也过不去), 交给 R2s warn 说话, 别在这里炸
    expected_top3 = rf.top3(flags) if flags else []
    if product is not None and flags:
        got_ids = {f["id"] for f in product.get("red_flags") or []}
        want_ids = {f["id"] for f in flags}
        if got_ids != want_ids:
            missing = "、".join(sorted(want_ids - got_ids)) or "无"
            extra = "、".join(sorted(got_ids - want_ids)) or "无"
            fails.append(
                f"assembly.json 的红旗清单与节点块重算不一致(缺 {missing};多 {extra})"
                " → 节点改过但没重跑 assemble_report_v8"
            )
        got = [(t["rank"], t["red_flag_id"]) for t in product.get("top3") or []]
        want = [(t["rank"], t["red_flag_id"]) for t in expected_top3]
        if got != want:
            fails.append(f"Top3 漂移:装配产物 {got} vs 重算 {want}(Top3 由机器带出, 不许人工挑)")

    for flag in flags:
        if flag["level"] not in ("🔴", "🟠"):
            continue
        home = flag["node"]
        tokens = flag_tokens(flag)
        if _mentions(bodies.get(home, ""), tokens):
            continue
        elsewhere = [n for n in CHAPTER_ORDER if n != home and _mentions(bodies.get(n, ""), tokens)]
        where = f",却出现在 {'、'.join(LABELS[n] for n in elsewhere)}" if elsewhere else ""
        msg = (
            f"{flag['level']}「{flag['title']}」未在归属节点 {LABELS[home]} 叙述{where}"
            f"(找过:{'、'.join(tokens[:4])})"
        )
        (fails if flag["level"] == "🔴" else warns).append(msg)

    fatal_n = sum(1 for f in flags if f["level"] == "🔴")
    high_n = sum(1 for f in flags if f["level"] == "🟠")
    return (
        RuleResult(
            name="R2 红旗闭环", passed=not fails,
            detail=f"清单 {len(flags)} 条(🔴{fatal_n} 🟠{high_n})· Top3 与重算一致 + 🔴 归家",
            findings=fails,
        ),
        RuleResult(
            name="R2w 🟠 高级红旗归家", severity=WARN, passed=not warns,
            detail=f"{len(warns)} 条 🟠 未在归属节点叙述(附录D 有条目, 但正文没讲)",
            findings=warns,
        ),
    )


# ============================================================================
# R3 数字唯一 home
# ============================================================================
def rule_number_home(bodies: dict[str, str]) -> RuleResult:
    """跨章重复的数字:第一个**不带出处**地写出它的章是 home,之后每处都要带出处引用。

    只在五章之间判——首页是机器装配(链手册 §4.5 明文豁免),附录本就是全表下沉的家。

    ★ 带出处的引用既不认领 home 也不算违规。判 home 时必须跳过它们,否则章序在前的
    「借用方」会抢走 home,把真正的主人反判成异地裸引 —— 现价与区间锚归③赔率,但②状态
    按规矩带出处引用了它们,章序②在③前,老写法就会去告③赔率的状。
    """
    home_of: dict[str, str] = {}
    findings: list[str] = []
    for node in CHAPTER_ORDER:
        per_phrase: dict[str, list[str]] = {}
        for line in bodies.get(node, "").splitlines():
            for m in NUMBER_PHRASE.finditer(_squash(line)):
                per_phrase.setdefault(m.group(0), []).append(line)
        for phrase, lines in per_phrase.items():
            if len(phrase) < 3 or _COLLIDING_PCT.fullmatch(phrase):
                continue
            if any(CITATION.search(l) for l in lines):
                continue
            home = home_of.get(phrase)
            if home is None:
                home_of[phrase] = node
                continue
            findings.append(
                f"{LABELS[node]} 裸引「{phrase}」(home 在 {LABELS[home]}):{lines[0].strip()[:60]}"
            )
    return RuleResult(
        name="R3 数字唯一 home", passed=not findings,
        detail=f"{len(findings)} 处异地裸数字(异地出现要带出处:①-⑤ / 附录A-E)",
        findings=findings,
    )


# ============================================================================
# R4 章预算
# ============================================================================
def rule_budget(bodies: dict[str, str]) -> RuleResult:
    findings, total = [], 0
    for node in CHAPTER_ORDER:
        n = len(_body_lines(bodies.get(node, "")))
        total += n
        budget = CHAPTER_BUDGET[node]
        if n > budget:
            findings.append(f"{LABELS[node]} {n} 行 > 预算 {budget} 行(先看能不能下沉附录)")
    if total > BODY_TOTAL_MAX:
        findings.append(f"主体合计 {total} 行 > {BODY_TOTAL_MAX} 行")
    return RuleResult(
        name="R4 章预算", severity=WARN, passed=not findings,
        detail=f"主体合计 {total} 行(上限软目标 {BODY_TOTAL_MAX};字数下限规则已随 v8 删除)",
        findings=findings,
    )


# ============================================================================
# R11 散文密度
# ============================================================================
# R4 数的是**行数**, 于是写手把该说的塞进更少的行里 —— 行写长就行。列表形状的内容
# (四个分部 / 五项折现率 / 三个情景 / 七条传导)因此被焊成一个段落, 读者得在脑子里重建表。
# 东山首份 v8 报告实测: 五章 17 行, 最密的一行 844 字。
#
# ★ 判据是「形状」不是「数字个数」(票 08 第 4 轮交付评审校准):
#   数数字两头都误判 —— ③赔率结尾 140 字几乎没数字, 是全报告最好读的一段;
#   ②有一段 185 字塞 7 个数字却完全好读, 因为那是四句**平行、互不比较**的自问自答。
#   真正读不下去的是「读者必须同时在脑子里持有几个数字才能跟上这一句」, 而那种句子的
#   外形特征是**列表被焊成了段落**: 逐条 / 逐期 / 逐分部 / 逐情景 / 逐科目。
#   所以主判据 = 列表形状检测, 长度只作兜底提示。
#
# ★★ 但这条规则**只是定位器, 不是判官**(第 5 轮评审的结论, 比上面那层更要紧):
#   真正决定「该不该是表」的不是有没有并列项, 而是**这些并列项之间有没有共同的列**——
#   分部 / 净利 / 倍数 / 估值 有共同列, 天生是表;
#   「给光模块 40x 是因为索尔思单体没披露、1.6T 只到小批量试产」没有共同列, 它是**理由**,
#   而理由的正确形状就是散文。**有没有共同列这件事机器数不出来, LLM 才数得出来。**
#   所以本规则永远 warn、只报「可疑段落在哪」, 结论交给 reviewer;
#   阈值也别拿单份报告标定(那会把「中文散文本来就用顿号」学成特征)——待多公司样本单独切票。
PROSE_MAX_CHARS = 200       # 兜底: 一行散文的字数(中文按字符算), 提示而非定罪

# 列表形状的三种外形: 编号项 / 期间对比(A → B) / 并列项(顿号或分号串)
_ENUM = re.compile(r"[1-9][)）]|[①-⑨](?=[^质状赔路决])")
_ARROW = re.compile(r"(?:→|->|—>)")
_PARALLEL = re.compile(r"[、;;]")
SHAPE_MIN_HITS = 3          # 同一类标记出现 ≥3 次 = 一张没写成表的表


def _list_shape(line: str, after_table: bool = False) -> str | None:
    """这一行是不是「被焊成段落的表」? 返回命中的形状名, 否则 None。

    两处校准(票 08 第 4 轮实测, 都是为了压误报):
    · **并列项要同时数数字**。中文散文本来就大量用顿号 —— 只数标点会把出处引用行
      (「贵不贵见③赔率;客户集中见④路径」)和引号串反例判成表。要求 ≥4 个数字短语,
      才像「逐分部 / 逐科目」那种真正该进表的东西。
    · **紧跟表格的一行豁免**。那是链手册认可的「表下注」形态 —— reviewer 明确要求把
      倍数理由、证伪指标从列里下沉成注, 这条规则不能反过来又把它推回表里。
    """
    if after_table:
        return None
    n_nums = len(NUMBER_PHRASE.findall(_squash(line)))
    for name, pat, need_nums in (
        ("编号项", _ENUM, 0),
        ("期间对比(A → B)", _ARROW, 0),
        ("并列项", _PARALLEL, 4),
    ):
        if len(pat.findall(line)) >= SHAPE_MIN_HITS and n_nums >= need_nums:
            return name
    return None


def rule_prose_density(bodies: dict[str, str]) -> RuleResult:
    """列表形状的内容被焊成散文 → 该改成表。warn, 不阻断出片。

    另加一条**正向**断言防矫枉过正: 每章至少要有一段像样的纯判断散文,
    否则报告会被优化成一摞没有观点的表(票 08 第 4 轮①质地表格化后已逼近这条线)。
    """
    findings = []
    for node in CHAPTER_ORDER:
        prose, after_table = [], set()
        prev_was_table = False
        for raw in bodies.get(node, "").splitlines():
            s = raw.strip()
            if not s:
                continue
            if s.startswith("|"):
                prev_was_table = True
                continue
            if not s.startswith("#"):
                if prev_was_table:
                    after_table.add(len(prose))     # 紧跟表格 = 表下注, 形状判据豁免
                prose.append(s)
            prev_was_table = False
        for i, s in enumerate(prose):
            shape = _list_shape(s, after_table=i in after_table)
            if shape:
                findings.append(
                    f"{LABELS[node]} 第 {i + 1} 段命中「{shape}」(≥{SHAPE_MIN_HITS} 处)"
                    f"—— 请人判它该不该是表:{s[:42]}…"
                )
            elif len(s) > PROSE_MAX_CHARS:
                findings.append(
                    f"{LABELS[node]} 第 {i + 1} 段 {len(s)} 字(>{PROSE_MAX_CHARS})"
                    f"—— 判断/推理可以长, 数据罗列不该长:{s[:42]}…"
                )
        # 正向断言: 至少一段有分量的纯判断。只对**写满了的章**判 ——
        # 桩章节 / 刚起头的草稿没必要被念叨(fixture 的四行桩就属这类)。
        body_lines = [l for l in bodies.get(node, "").splitlines() if l.strip()]
        if len(body_lines) >= 10 and not any(
            len(s) >= 80 and len(NUMBER_PHRASE.findall(_squash(s))) <= 2 for s in prose
        ):
            findings.append(
                f"{LABELS[node]} 没有一段「≥80 字且数字 ≤2」的纯判断散文 —— "
                "数字归表之后, 观点也要有地方说, 别把章写成一摞表"
            )
    return RuleResult(
        name="R11 散文密度", severity=WARN, passed=not findings,
        detail=f"{len(findings)} 处可疑段落(定位器, 不是判官 —— 该不该改成表由 reviewer 判)",
        findings=findings,
    )


# ============================================================================
# R5 区间锚
# ============================================================================
def rule_anchor(nodes: dict) -> tuple[RuleResult, RuleResult]:
    odds = nodes["odds"]
    anchor = odds.get("anchor_range") or {}
    fails, warns = [], []

    if "same_direction" not in anchor:
        fails.append("anchor_range 缺 same_direction 标记(两端同向与否是赔率判定成立的前提)")
    same = anchor.get("same_direction", True)
    if not same and not (anchor.get("divergence_note") or "").strip():
        fails.append("两端不同向却没写 divergence_note(分歧是信息, 要写明两把尺子量的是什么)")
    if not same and "口径" not in odds.get("verdict", ""):
        warns.append("两端不同向时 verdict 建议标注「取决于口径」(链手册 §2.4)")

    low, high = anchor.get("low") or {}, anchor.get("high") or {}
    lo, hi = low.get("value"), high.get("value")
    if isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
        if lo > hi:
            fails.append(f"区间锚倒置:low {lo} > high {hi}(低端=SOTP, 高端=DCF)")
        price = (odds.get("current_price") or {}).get("value")
        verdict = odds.get("verdict", "")
        if isinstance(price, (int, float)):
            if price > hi and verdict.startswith("便宜"):
                fails.append(f"现价 {price} 高于锚区间高端 {hi} 却判「{verdict}」(自相矛盾)")
            if price < lo and "买完完美未来" in verdict:
                fails.append(f"现价 {price} 低于锚区间低端 {lo} 却判「{verdict}」(自相矛盾)")
    return (
        RuleResult(
            name="R5 区间锚", passed=not fails,
            detail="同向标记 / 分歧说明 / 两端不倒置 / verdict 与现价方向自洽",
            findings=fails,
        ),
        RuleResult(name="R5w 不同向标注", severity=WARN, passed=not warns, findings=warns),
    )


# ============================================================================
# R6 外链引用
# ============================================================================
FORBIDDEN_LINKS = [
    (re.compile(r"详见\s*[^\s。,,))]+\.md\b"), "详见 xxx.md"),
    (re.compile(r"参见\s*[^\s。,,))]+\.md\b"), "参见 xxx.md"),
    (re.compile(r"见\s*phase\d[\w-]*\.md\b"), "见 phaseX.md"),
    (re.compile(r"见附件"), "见附件"),
    (re.compile(r"\[[^\]]+\]\((?!#)[^)]*\.md\)"), "[xxx](xxx.md) 外链"),
]


def rule_links(bodies: dict[str, str]) -> RuleResult:
    findings = []
    for node in CHAPTER_ORDER:
        for i, line in enumerate(bodies.get(node, "").splitlines(), 1):
            for pat, label in FORBIDDEN_LINKS:
                if pat.search(line):
                    findings.append(f"{LABELS[node]} L{i} [{label}]: {line.strip()[:70]}")
                    break
    return RuleResult(
        name="R6 外链引用", passed=not findings,
        detail=f"{len(findings)} 处外链(内容要么 inline, 要么下沉本报告附录; 阈值 = 0)",
        findings=findings,
    )


# ============================================================================
# R7 决策字段齐全 + 致命红旗封顶
# ============================================================================
DECISION_REQUIRED = (
    "triad", "action_gear", "action_detail", "position", "three_part",
    "good_company_ref", "what_to_wait", "falsification_exit", "gear_cap",
)


def rule_decision(nodes: dict, flags: list[dict]) -> tuple[RuleResult, RuleResult]:
    decision = nodes["decision"]
    fails, warns = [], []
    for key in DECISION_REQUIRED:
        if not decision.get(key):
            fails.append(f"决策块缺「{key}」(链手册 §2:三元组/档位/仓位/三分/该等什么/证伪/封顶)")

    fatal = [f for f in flags if f["level"] == "🔴"]
    cap = decision.get("gear_cap") or {}
    if fatal:
        names = "、".join(f["title"] for f in fatal)
        if decision.get("action_gear") != "回避":
            fails.append(
                f"有 {len(fatal)} 条 🔴 致命红旗({names})却判「{decision.get('action_gear')}」"
                " —— 封顶是硬规则:必须「回避」(链手册 §2.3)"
            )
        if not cap.get("triggered"):
            fails.append(f"有 🔴 致命红旗({names})但 gear_cap.triggered = false")
    elif cap.get("triggered"):
        warns.append("清单里没有 🔴 致命红旗, gear_cap 却标 triggered=true(封顶理由要对得上清单)")
    return (
        RuleResult(
            name="R7 决策字段 + 封顶", passed=not fails,
            detail=f"决策块 {len(DECISION_REQUIRED)} 个必填字段 + 致命红旗封顶检查",
            findings=fails,
        ),
        RuleResult(name="R7w 封顶理由", severity=WARN, passed=not warns, findings=warns),
    )


# ============================================================================
# R8 越权发声(仓位 / 行动档位 / 买卖建议只在⑤)
# ============================================================================
OVERREACH = [
    (re.compile(r"建议\s*(买入|卖出|加仓|减仓|回避|持有|清仓|仓位)"), "买卖/仓位建议"),
    (re.compile(r"仓位建议|建议仓位"), "仓位建议"),
    (re.compile(r"(可以|应该|应当|值得)\s*(买入|加仓|建仓|入场)"), "买入建议"),
    (re.compile(r"仓位\s*[≤<≥>=]"), "仓位数字"),
    (re.compile(r"总资金\s*的?\s*[≤<]?\s*\d"), "仓位数字"),
    (re.compile(r"核心仓|期权仓|等证据临界|不追高"), "行动档位词"),
]
OVERREACH_EXEMPT = ("⑤", "决策层", "由决策", "唯一出处", "越权", "不判", "不给")


def rule_overreach(bodies: dict[str, str]) -> RuleResult:
    findings = []
    for node in CHAPTER_ORDER:
        if node == "decision":
            continue
        for i, line in enumerate(bodies.get(node, "").splitlines(), 1):
            if any(ctx in line for ctx in OVERREACH_EXEMPT):
                continue                     # 明确写「归⑤ / 见⑤ / 不判」的引用行豁免
            for pat, label in OVERREACH:
                if pat.search(line):
                    findings.append(f"{LABELS[node]} L{i} [{label}]: {line.strip()[:70]}")
                    break
    return RuleResult(
        name="R8 越权发声", passed=not findings,
        detail=f"{len(findings)} 处越权(仓位/行动档位/买卖建议的唯一出处是⑤决策)",
        findings=findings,
    )


# ============================================================================
# R9 无记忆性反例
# ============================================================================
MEMORYLESS_FORBIDDEN = [
    "跌久了该涨", "跌多了该反弹", "超跌就该反弹", "沉寂这么久该涨",
    "沉寂久了该轮到", "估值压久了该修复", "压制这么久该修复",
    "横盘这么久该突破", "讲多年AI该兑现", "等这么久该涨",
]
MEMORYLESS_EXEMPT = (
    "禁用", "禁止", "不得", "不能", "不应", "反例", "幻觉", "警惕", "避免", "并非", "而非", "无记忆",
)


def rule_memoryless(bodies: dict[str, str]) -> RuleResult:
    findings = []
    for node in CHAPTER_ORDER:
        for i, line in enumerate(bodies.get(node, "").splitlines(), 1):
            if any(ctx in line for ctx in MEMORYLESS_EXEMPT):
                continue
            for phrase in MEMORYLESS_FORBIDDEN:
                if phrase in line:
                    findings.append(f"{LABELS[node]} L{i} 等待时间幻觉: {line.strip()[:60]}")
                    break
    return RuleResult(
        name="R9 无记忆性反例", passed=not findings,
        detail=f"{len(findings)} 处「等久了该涨」(买入理由必须是 λ↑ / 证据斜率变正)",
        findings=findings,
    )


# ============================================================================
# R10 报告与节点同步(装配是最后一步, 改完正文必须重跑)
# ============================================================================
def rule_report_sync(md_path: Path | None, bodies: dict[str, str]) -> RuleResult:
    if md_path is None or not Path(md_path).exists():
        return RuleResult(
            name="R10 报告与节点同步", skipped=True,
            detail="未找到装配后的主报告(本次只判节点块与五章正文)",
        )
    md_path = Path(md_path)
    chapters = report_chapters(md_path.read_text(encoding="utf-8"))
    findings = []
    for node in CHAPTER_ORDER:
        if node not in chapters:
            findings.append(f"主报告缺 {LABELS[node]} 章")
        elif _squash(chapters[node]) != _squash(bodies.get(node, "")):
            findings.append(
                f"{LABELS[node]} 章正文 ≠ nodes/node-{node}.md → 重跑 assemble_report_v8"
            )
    return RuleResult(
        name="R10 报告与节点同步", passed=not findings,
        detail=f"{md_path.name}:五章正文 = 节点 md 正文(报告零人工抄写)",
        findings=findings,
    )


# ============================================================================
# 公共 API
# ============================================================================
def find_report_md(run_dir: Path) -> Path | None:
    mds = sorted(Path(run_dir).glob("*-analysis-*.md"), reverse=True)
    return mds[0] if mds else None


def load_assembly(run_dir: Path) -> dict | None:
    for candidate in (run_dir / "assembly" / "assembly.json", run_dir / "assembly.json"):
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    return None


def lint_run(run_dir, md_path=None, artifacts_dir=None, audit_json=None) -> LintResult:
    """判一个 run 目录。缺 nodes/ 抛 FileNotFoundError(调用方转 exit 2)。"""
    run_dir = Path(run_dir)
    nodes_dir = run_dir / "nodes"
    if not nodes_dir.is_dir():
        raise FileNotFoundError(f"run 目录缺 nodes/: {run_dir}")

    result = LintResult(run_dir=run_dir)
    schema_rule, nodes = rule_schema(nodes_dir)
    result.rules.append(schema_rule)
    if nodes is None:                # 块都不合契约, 后面的规则判不了(判了也是噪音)
        for name in ("R2 红旗闭环", "R3 数字唯一 home", "R5 区间锚",
                     "R7 决策字段 + 封顶", "R10 报告与节点同步"):
            result.rules.append(RuleResult(name=name, skipped=True, detail="R1 未过, 跳过"))
        return result

    bodies = assembly.load_node_bodies(nodes_dir)
    search_dirs = [Path(artifacts_dir)] if artifacts_dir else []
    search_dirs += [run_dir, run_dir.parent.parent]      # runs/{date} → output/{company}
    script_flags = render.load_audit_flags(Path(audit_json) if audit_json else None, search_dirs)
    product = load_assembly(run_dir)

    try:
        flags = rf.merge(script_flags, rf.collect_nominations(nodes))
        closure_fail, closure_warn = rule_red_flag_closure(bodies, flags, product)
    except rf.RedFlagError as exc:
        # id 撞车 / 级别或归属非法 —— 写手提名的问题, 按 fail 报出来(装配同样会拒绝产出)
        flags = []
        closure_fail = RuleResult(
            name="R2 红旗闭环", passed=False,
            detail="红旗清单合并失败(写手提名与脚本红旗冲突)", findings=[str(exc)],
        )
        closure_warn = RuleResult(name="R2w 🟠 高级红旗归家", severity=WARN, skipped=True)
    anchor_fail, anchor_warn = rule_anchor(nodes)
    decision_fail, decision_warn = rule_decision(nodes, flags)
    result.rules += [
        closure_fail,
        rule_number_home(bodies),
        anchor_fail,
        rule_links(bodies),
        decision_fail,
        rule_overreach(bodies),
        rule_memoryless(bodies),
        rule_report_sync(Path(md_path) if md_path else find_report_md(run_dir), bodies),
        rule_budget(bodies),
        rule_prose_density(bodies),
        closure_warn,
        anchor_warn,
        decision_warn,
    ]
    if not script_flags:
        result.rules.append(RuleResult(
            name="R2s audit 产物", severity=WARN, passed=False,
            detail="没找到 audit_report.json,红旗闭环只判了写手提名",
        ))
    return result


def main() -> int:
    for stream in (sys.stdout, sys.stderr):      # Windows 控制台 GBK 下 print emoji 会炸
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-dir", required=True, help="runs/{date}/ 目录(含 nodes/)")
    ap.add_argument("--md", default=None, help="装配后的主报告(默认在 run 目录内找)")
    ap.add_argument("--artifacts-dir", default=None, help="采集产物目录(找 audit_report.json)")
    ap.add_argument("--audit-json", default=None, help="显式指定 audit JSON")
    ap.add_argument("--quiet", action="store_true", help="只给退出码")
    args = ap.parse_args()

    try:
        result = lint_run(
            args.run_dir, md_path=args.md,
            artifacts_dir=args.artifacts_dir, audit_json=args.audit_json,
        )
    except FileNotFoundError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2
    except (rf.RedFlagError, verdict_block.BlockNotFound) as exc:
        print(f"❌ 红旗清单 / 节点块读不了:{exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        print(result.report)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
