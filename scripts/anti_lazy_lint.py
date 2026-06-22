"""anti_lazy_lint — 主报告深度检查 (skill v4.7)

机械化阻断"偷懒报告"的 7 条 hard-fail lint 规则 (v7.0: +Rule6 §七决策内核 +Rule7 无记忆性反例)。
LLM 自审看不见自己的懒,这里用确定性的 grep + 计数 + diff 替代。

调用:
  python3 -m scripts.anti_lazy_lint --md output/{company}/{company}-analysis-{date}.md

退出码:
  0 = 全部通过
  1 = 任一规则违规

集成点:
  Phase 6 Part A Step 0 — 23 项 LLM 审核之前
  scripts/build_html.py — 写 HTML 之前内置调用,fail 阻断
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SKELETON_PATH = SKILL_ROOT / "assets" / "templates" / "report-skeleton.md"

# ============================================================================
# Rule 1: 外链引用扫描
# ============================================================================
FORBIDDEN_LINK_PATTERNS = [
    (re.compile(r"详见\s*[^\s。,，)）]+\.md\b"), "详见 xxx.md"),
    (re.compile(r"参见\s*[^\s。,，)）]+\.md\b"), "参见 xxx.md"),
    (re.compile(r"\b见\s*phase\d[\w-]*\.md\b"), "见 phaseX.md"),
    (re.compile(r"详见\s*phase\d"), "详见 phaseX"),
    (re.compile(r"见附件"), "见附件"),
    (re.compile(r"\[[^\]]+\]\((?!#)[^)]*\.md\)"), "[xxx](xxx.md) 外链"),
]

# v7.0: 跨文件引用白名单 — §九 = 数据来源与信息缺口, 允许引用源文件名 (v6.0 的 §八)
SECTION_WHITELIST: dict[str, set[str]] = {
    "§九": {"audit_report.md", "metrics.json", "phase1-data.md", "phase2-documents.md"},
    "§六": {"audit_report.md"},   # 风险与红旗审计章节引用 audit_report 完整清单
}

# ============================================================================
# Rule 2: 各章节最低字符数 (中文+字母+数字, 排除标题行)
# v6.0: 8 章节合并后重新 calibrate. 合并章节的阈值 = 原合并各章之和略打折,
# 深度章节 (§二 基本面 / §四 评分维度证据 / §五 估值回报) 给高阈值,
# 摘要式 (§八 来源缺口) 给低阈值. 太严会卡合法摘要式章节.
# ============================================================================
MIN_SECTION_CHARS = {
    "§一":  600,   # 执行摘要 (含决策结论)
    "§二":  800,   # 公司基本面 (财务趋势 + 主力控盘 + 十大股东)
    "§三":  700,   # 行业与竞争对标 (行业格局 + peer)
    "§四": 1500,   # 评分与维度证据 (评分表 + 10 维度逐条 + 4.11 状态评估)
    "§五":  900,   # 估值、赔率与定价充分度 (P=F+N / 反向DCF / ΔP / SOTP / DCF / 回报路径)
    "§六":  500,   # 风险与红旗审计 (快筛 + audit 汇总 + 6.4 左尾防护)
    "§七":  800,   # 投资决策内核 (状态×赔率×路径 → 三分 + 行动档位)  v7.0 新增; 结构由 Rule6 兜底
    "§八":  600,   # 舆情 + 资金流 (v6.0 的 §七)
    "§九":  200,   # 数据来源 + 信息缺口 (v6.0 的 §八)
}

# ============================================================================
# Rule 3: artifact 关键短语覆盖率
# 实测阈值 — overall 40% + per-artifact 20% 才能区分"懒"(<20%) vs "正常摘要"(40-60%)
# vs "完整 inline"(>80%). 太严会卡 audit_report 这种"详细信号但主报告只引核心"的合理摘要.
# ============================================================================
ARTIFACTS = [
    "capital_flow.md",
    "peer_analysis.md",
    "technical_analysis.md",
    "audit_report.md",
    "data_snapshot.md",  # v4.8 新增 — 一劳永逸修复 Phase 3 漏读最新季度 / 十大股东省略
]
COVERAGE_OVERALL_MIN = 0.40
COVERAGE_PER_ARTIFACT_MIN = 0.20

# v4.8.2 新: data_snapshot.md 是百科全书式的全数据 dump (含 ~150-200 个独特数字短语,
# 含子公司股东持股 / 户数时序 / 质押日期 / 4 位小数等), 主报告不需要全部 inline。
# 给它设单独的宽松阈值 (5%, 即 ~10 个高优先级短语命中即可)。
PER_ARTIFACT_MIN_OVERRIDE = {
    "data_snapshot.md": 0.05,
}

# v4.8.2 新: 不计入 overall 覆盖率分母的 artifact (因短语集太大会稀释 overall)
EXCLUDE_FROM_OVERALL = {
    "data_snapshot.md",
}
KEY_PHRASE_PATTERN = re.compile(
    r"(?:\d+(?:[\.,]\d+)?\s*(?:%|亿元|亿|万元|万|元|x|倍|个|台|名|股|月|日|年|σ))"
)


@dataclass
class RuleResult:
    name: str
    passed: bool
    detail: str = ""
    findings: list[str] = field(default_factory=list)


@dataclass
class LintResult:
    md_path: Path
    rules: list[RuleResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.rules)

    @property
    def report(self) -> str:
        lines = [f"[anti_lazy_lint] 主报告: {self.md_path}"]
        for r in self.rules:
            mark = "✅ PASS" if r.passed else "❌ FAIL"
            lines.append(f"  {r.name}: {mark}{('  — ' + r.detail) if r.detail else ''}")
            for f in r.findings[:8]:
                lines.append(f"    {f}")
            if len(r.findings) > 8:
                lines.append(f"    … ({len(r.findings) - 8} more)")
        failed = [r.name for r in self.rules if not r.passed]
        lines.append("")
        if failed:
            lines.append(f"总结: {len(failed)} 项失败 ({', '.join(failed)}) → exit 1")
        else:
            lines.append(f"总结: 全部 {len(self.rules)} 项通过 → exit 0")
        return "\n".join(lines)


# ============================================================================
# 章节切分工具
# ============================================================================
def _split_sections(md_text: str) -> dict[str, str]:
    """按 ## §X 切分主报告 MD,返回 {section_id: body_text}.
    section_id 是 "§一" / "§二" 等 (不含正文化标题)。
    """
    out: dict[str, str] = {}
    current_id: str | None = None
    buf: list[str] = []
    for line in md_text.splitlines():
        m = re.match(r"^##\s+(§[\u4e00-\u9fa5]+)\b", line)
        if m:
            if current_id is not None:
                out[current_id] = "\n".join(buf)
            current_id = m.group(1)
            buf = [line]
        elif current_id is not None:
            buf.append(line)
    if current_id is not None:
        out[current_id] = "\n".join(buf)
    return out


def _normalize_title_core(line: str) -> str:
    """从 '## §X xxx (annotation)' 提取核心 'xxx',
    去掉所有半角/全角括号内容 + ## 前缀 + 反引号。
    """
    s = re.sub(r"[（(].*?[)）]", "", line)
    s = re.sub(r"^#+\s*", "", s).strip()
    s = re.sub(r"`[^`]*`", "", s).strip()
    return s


# ============================================================================
# Rule 1
# ============================================================================
def _line_is_whitelisted(line: str, sec_id: str) -> bool:
    """检查违规命中是否落在白名单内 (designed companion 引用 / 来源标注)."""
    allowed_files = SECTION_WHITELIST.get(sec_id, set())
    if not allowed_files:
        return False
    for fname in allowed_files:
        if fname in line:
            return True
    return False


def rule_1_forbidden_links(md_text: str) -> RuleResult:
    sections = _split_sections(md_text)
    findings: list[str] = []
    # 用全文 enumerate 拿全局行号
    md_lines = md_text.splitlines()
    line_to_sec: dict[int, str] = {}
    current_sec = "前置"
    for i, line in enumerate(md_lines):
        m = re.match(r"^##\s+(§[\u4e00-\u9fa5]+)", line)
        if m:
            current_sec = m.group(1)
        line_to_sec[i] = current_sec

    seen_lines: set[int] = set()
    for i, line in enumerate(md_lines):
        sec_id = line_to_sec.get(i, "前置")
        for pat, label in FORBIDDEN_LINK_PATTERNS:
            if not pat.search(line):
                continue
            if _line_is_whitelisted(line, sec_id):
                continue
            if i in seen_lines:
                continue
            seen_lines.add(i)
            findings.append(f"L{i+1} [{sec_id}/{label}]: {line.strip()[:90]}")
            break  # 该行已记一次, 不再重复匹配其他 pattern
    passed = len(findings) == 0
    detail = f"{len(findings)} 命中 (阈值 = 0)"
    return RuleResult(name="Rule 1 外链引用扫描", passed=passed, detail=detail, findings=findings)


# ============================================================================
# Rule 2
# ============================================================================
def _section_char_count(sec_body: str) -> int:
    """章节字符数 = 去掉 ## 标题行 / 空行 后,中文+字母+数字 字符数。
    保留表格行(它们也是密度证据)。
    """
    out_chars = 0
    for line in sec_body.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("## ") or s.startswith("### ") or s.startswith("#### "):
            continue
        # 计 中文 + 字母 + 数字
        out_chars += len(re.findall(r"[\w\u4e00-\u9fa5]", s))
    return out_chars


def rule_2_min_chars(md_text: str) -> RuleResult:
    sections = _split_sections(md_text)
    findings: list[str] = []
    for sec_id, threshold in MIN_SECTION_CHARS.items():
        body = sections.get(sec_id, "")
        actual = _section_char_count(body)
        if actual < threshold:
            findings.append(f"{sec_id} 字符数 {actual} < 阈值 {threshold}")
    passed = len(findings) == 0
    detail = f"{len(findings)} 章节不足"
    return RuleResult(name="Rule 2 章节最小字符数", passed=passed, detail=detail, findings=findings)


# ============================================================================
# Rule 3
# ============================================================================
def _extract_key_phrases(text: str) -> set[str]:
    """从 artifact 提取确定性 key phrase: '数字+单位'.
    例: '64.46%' / '5.31' / '2.19 亿' / '4.05 倍' / '27 台'
    最终归一化(去空格)再返回 set。
    """
    phrases = set()
    for m in KEY_PHRASE_PATTERN.finditer(text):
        s = m.group(0)
        s_norm = re.sub(r"\s+", "", s)
        if len(s_norm) >= 3:  # 过滤过短的(如 "0%")
            phrases.add(s_norm)
    return phrases


def rule_3_artifact_coverage(md_path: Path, md_text: str) -> RuleResult:
    findings: list[str] = []
    md_dir = md_path.parent
    md_norm = re.sub(r"\s+", "", md_text)

    artifact_total = 0
    artifact_hit = 0
    per_artifact: list[str] = []
    failing_artifacts: list[str] = []

    for art_name in ARTIFACTS:
        art_path = md_dir / art_name
        if not art_path.exists():
            continue
        try:
            art_text = art_path.read_text(encoding="utf-8")
        except Exception:
            continue
        phrases = _extract_key_phrases(art_text)
        if not phrases:
            continue
        hit = sum(1 for p in phrases if p in md_norm)
        # v4.8.2: data_snapshot.md 等百科 artifact 不计入 overall, 避免稀释
        if art_name not in EXCLUDE_FROM_OVERALL:
            artifact_total += len(phrases)
            artifact_hit += hit
        ratio = hit / len(phrases)
        # v4.8.2: 部分 artifact 用 override 阈值 (data_snapshot.md 5% 因短语过多)
        per_min = PER_ARTIFACT_MIN_OVERRIDE.get(art_name, COVERAGE_PER_ARTIFACT_MIN)
        if ratio < per_min:
            status = "❌"
            failing_artifacts.append(art_name)
        elif ratio < 0.5:
            status = "⚠️"
        else:
            status = "✅"
        excl_tag = " [不计 overall]" if art_name in EXCLUDE_FROM_OVERALL else ""
        per_artifact.append(
            f"{status} {art_name}: {hit}/{len(phrases)} = {ratio*100:.1f}% (阈值 {per_min*100:.0f}%){excl_tag}"
        )

    if artifact_total == 0:
        return RuleResult(
            name="Rule 3 Artifact 关键短语覆盖率",
            passed=True,
            detail="无 artifact 文件 (跳过, 适用于美股/港股)",
        )

    overall = artifact_hit / artifact_total
    findings.extend(per_artifact)
    overall_pass = overall >= COVERAGE_OVERALL_MIN
    per_pass = len(failing_artifacts) == 0
    passed = overall_pass and per_pass
    detail = (
        f"总体 {artifact_hit}/{artifact_total} = {overall*100:.1f}% "
        f"(阈值 overall ≥ {COVERAGE_OVERALL_MIN*100:.0f}%, 单 artifact ≥ {COVERAGE_PER_ARTIFACT_MIN*100:.0f}%)"
    )
    if not per_pass:
        detail += f" — 严重不足: {', '.join(failing_artifacts)}"
    return RuleResult(name="Rule 3 Artifact 关键短语覆盖率", passed=passed, detail=detail, findings=findings)


# ============================================================================
# Rule 4
# ============================================================================
def rule_4_title_byte_exact(md_text: str) -> RuleResult:
    findings: list[str] = []
    if not SKELETON_PATH.exists():
        return RuleResult(
            name="Rule 4 章节标题骨架一致",
            passed=True,
            detail=f"skeleton 不存在 ({SKELETON_PATH}),跳过",
        )
    skeleton_text = SKELETON_PATH.read_text(encoding="utf-8")

    skel_titles = [
        _normalize_title_core(l)
        for l in skeleton_text.splitlines()
        if re.match(r"^##\s+§", l)
    ]
    rep_titles = [
        _normalize_title_core(l)
        for l in md_text.splitlines()
        if re.match(r"^##\s+§", l)
    ]

    # 长度不等
    if len(rep_titles) != len(skel_titles):
        findings.append(
            f"章节数不匹配: report {len(rep_titles)} vs skeleton {len(skel_titles)}"
        )
    # 逐一比较
    for i, skel in enumerate(skel_titles):
        if i >= len(rep_titles):
            findings.append(f"缺章节 #{i+1}: skeleton='{skel}'")
            continue
        rep = rep_titles[i]
        if rep != skel:
            findings.append(f"#{i+1} 不匹配: report='{rep}' vs skeleton='{skel}'")

    passed = len(findings) == 0
    detail = (
        f"{len(findings)} 处不匹配"
        if not passed
        else f"{len(skel_titles)}/{len(skel_titles)} 章节标题与骨架字节一致 (去括号注释后)"
    )
    return RuleResult(name="Rule 4 章节标题骨架一致", passed=passed, detail=detail, findings=findings)


# ============================================================================
# Rule 5: §一 执行摘要禁止内联来源标签 (保持干净 TL;DR)
# 执行摘要是给人快读的决策仪表盘, 混入 [data_snapshot §2.1] / [§五] / [缺口#1] /
# [Tushare:..] 这类来源脚注会严重伤可读性。来源属于 §二-§八 正文。
# ============================================================================
EXEC_SUMMARY_SOURCE_TAG = re.compile(
    r"\[(?:data_snapshot|peer_analysis|metrics\.json|capital_flow|technical_analysis|"
    r"audit_report|audit|缺口|WebSearch|Tushare|PDF|yfinance|§[一二三四五六七八九十])"
)


def rule_5_exec_summary_clean(md_text: str) -> RuleResult:
    sections = _split_sections(md_text)
    body = sections.get("§一", "")
    findings: list[str] = []
    for line in body.splitlines():
        if line.lstrip().startswith("##"):
            continue
        m = EXEC_SUMMARY_SOURCE_TAG.search(line)
        if m:
            s = line.strip()
            findings.append(f"§一 内联来源标签: …{s[max(0, m.start() - 15):m.start() + 35]}…")
    passed = len(findings) == 0
    detail = f"{len(findings)} 处内联来源标签 (§一 应为干净叙述, 来源放 §二-§八; 阈值 = 0)"
    return RuleResult(name="Rule 5 §一 执行摘要无内联来源标签", passed=passed, detail=detail, findings=findings)


# ============================================================================
# Rule 6: §七 投资决策内核 完整性 (v7.0)
# §七 必含 决策三元组 / 行动档位 / 证伪, 且行动档位是六档之一 —— 防"合成章被略过/空话"
# ============================================================================
DECISION_CORE_REQUIRED = ("决策三元组", "行动档位", "证伪")
ACTION_TIERS = ("核心仓", "期权仓", "等证据临界", "不追高", "减仓", "回避")


def rule_6_decision_core(md_text: str) -> RuleResult:
    sections = _split_sections(md_text)
    body = sections.get("§七", "")
    findings: list[str] = []
    if not body.strip():
        findings.append("§七 投资决策内核 缺失或为空")
    else:
        for kw in DECISION_CORE_REQUIRED:
            if kw not in body:
                findings.append(f"§七 缺必填要素「{kw}」")
        if not any(t in body for t in ACTION_TIERS):
            findings.append(f"§七 行动档位未给出六档之一 {ACTION_TIERS}")
    passed = len(findings) == 0
    detail = f"{len(findings)} 项缺失 (§七 须含 决策三元组/行动档位/证伪 + 六档行动档位之一)"
    return RuleResult(name="Rule 6 §七 投资决策内核完整性", passed=passed, detail=detail, findings=findings)


# ============================================================================
# Rule 7: 无记忆性反例 — 禁止"等待时间幻觉"作买入理由 (v7.0, 泊松)
# 等久 ≠ 该涨; 买入理由必须是 λ↑ / 证据斜率变正。否定/元讨论语境豁免。
# ============================================================================
MEMORYLESS_FORBIDDEN = [
    "跌久了该涨", "跌多了该反弹", "超跌就该反弹", "沉寂这么久该涨",
    "沉寂久了该轮到", "估值压久了该修复", "压制这么久该修复",
    "横盘这么久该突破", "讲多年AI该兑现", "等这么久该涨",
]
MEMORYLESS_EXEMPT_CONTEXT = (
    "禁用", "禁止", "不得", "不能", "不应", "反例", "幻觉", "警惕", "避免", "并非", "而非", "无记忆性",
)


def rule_7_memorylessness(md_text: str) -> RuleResult:
    findings: list[str] = []
    for i, line in enumerate(md_text.splitlines()):
        if any(ctx in line for ctx in MEMORYLESS_EXEMPT_CONTEXT):
            continue   # 否定/元讨论语境 (报告解释"禁用这些") 豁免
        for phrase in MEMORYLESS_FORBIDDEN:
            if phrase in line:
                findings.append(f"L{i+1} 等待时间幻觉作买入理由: …{line.strip()[:60]}…")
                break
    passed = len(findings) == 0
    detail = f"{len(findings)} 处'等待时间幻觉' (泊松无记忆性: 等久≠该涨, 须 λ↑/证据斜率变正)"
    return RuleResult(name="Rule 7 无记忆性反例", passed=passed, detail=detail, findings=findings)


# ============================================================================
# 公共 API
# ============================================================================
def lint_md(md_path: Path) -> LintResult:
    md_path = Path(md_path)
    if not md_path.exists():
        result = LintResult(md_path=md_path)
        result.rules.append(
            RuleResult(name="文件存在", passed=False, detail=f"未找到 {md_path}")
        )
        return result

    md_text = md_path.read_text(encoding="utf-8")
    result = LintResult(md_path=md_path)
    result.rules.append(rule_1_forbidden_links(md_text))
    result.rules.append(rule_2_min_chars(md_text))
    result.rules.append(rule_3_artifact_coverage(md_path, md_text))
    result.rules.append(rule_4_title_byte_exact(md_text))
    result.rules.append(rule_5_exec_summary_clean(md_text))
    result.rules.append(rule_6_decision_core(md_text))
    result.rules.append(rule_7_memorylessness(md_text))
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--md", required=True, help="主报告 MD 路径")
    ap.add_argument("--quiet", action="store_true", help="仅退出码,不输出报告")
    args = ap.parse_args()

    md_path = Path(args.md).expanduser().resolve()
    result = lint_md(md_path)
    if not args.quiet:
        print(result.report)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
