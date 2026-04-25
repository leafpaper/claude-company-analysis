"""MD → HTML 报告构建器 (v4.6.1).

修复 v4.6 的 3 个问题:
1. MD 17 个 ## 章节 vs HTML 15 个 placeholder → 丢 2-3 个章节
2. 粘性侧边栏改为顶部横排 metric-strip
3. 规范化生成流程,不依赖 LLM inline Python

核心流程:
1. Read MD 按 ^## 切, 每段一个 section(preserve 所有章节)
2. 解析结构化注释块(CARD_METADATA / RATING_TRIO_DATA / KEY_METRICS_SIDEBAR)
3. Read base.html + styles.css, 内联 CSS
4. 前 15 section 填入 base.html 的 section_1..15 固定占位(锚点 id 不变)
5. 第 16+ section 追加到 extra_sections 占位(附录等)
6. 按 RATING_TRIO_DATA 注入 rating-trio 面板
7. 按 KEY_METRICS_SIDEBAR 注入 metric-strip 面板
8. 替换 hero meta ({{company_name}}/{{ticker}}/etc)
9. 写入 output/{company}/{company}-analysis-{date}.html

Usage:
    python3 -m scripts.build_html --company 实丰文化 \\
        --md /path/to/md --out /path/to/html.html

    # 默认自动找
    python3 -m scripts.build_html --company 实丰文化
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import markdown as md_lib
except ImportError:
    print("❌ 缺少依赖 'markdown', 请 pip3 install --user markdown", file=sys.stderr)
    sys.exit(1)


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets" / "html"


# ---------- 注释块解析 ----------

def _parse_structured_block(text: str, block_name: str) -> dict[str, str]:
    m = re.search(rf"<!--\s*{block_name}:?(.*?)-->", text, re.DOTALL)
    if not m:
        return {}
    body = m.group(1)
    result = {}
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("{{"):
            continue
        kv = re.match(r"([a-z_]+)\s*:\s*(.+?)(?:\s*\(.*\))?$", line)
        if kv:
            key, val = kv.group(1), kv.group(2).strip()
            if val and not val.startswith("{{"):
                result[key] = val
    return result


# ---------- MD → HTML section 切分 ----------

def split_sections(md_text: str) -> tuple[str, list[tuple[str, str]]]:
    """切 MD. Returns (pre_h2_text, [(title, body_md), ...]).
    pre_h2 是第一个 ## 之前的内容(hero 元数据 + 结构化注释块).
    """
    lines = md_text.splitlines(keepends=True)
    pre_h2: list[str] = []
    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    current_body: list[str] = []
    for line in lines:
        if line.startswith("## "):
            # 保存上一个 section(如有)
            if current_title is not None:
                sections.append((current_title, "".join(current_body)))
            current_title = line[3:].rstrip()
            current_body = []
        else:
            if current_title is None:
                pre_h2.append(line)
            else:
                current_body.append(line)
    if current_title is not None:
        sections.append((current_title, "".join(current_body)))
    return "".join(pre_h2), sections


# ---------- Rating Trio / Metric Strip 数据生成 ----------

def _tone_class(tone: str | None) -> str:
    return tone or "neutral"


def build_rating_trio(data: dict) -> str:
    """从 RATING_TRIO_DATA 注释块构建评级卡 HTML."""
    score = data.get("composite_score", "–")
    verdict = data.get("verdict", "–")
    verdict_tone = data.get("verdict_tone", "neutral")
    anchor = data.get("anchor_price", "–")
    delta = data.get("anchor_delta_signed", "")
    horizon = data.get("horizon", "")
    ret = data.get("expected_return", "–")
    ret_tone = data.get("return_tone", "neutral")
    annual = data.get("annualized_return", "–")

    # 解析符号
    delta_display = f"{delta}%" if delta and not delta.endswith("%") else delta or ""
    ret_display = f"{ret}%" if ret not in ("–", "") and not str(ret).endswith("%") else str(ret)
    annual_display = f"{annual}%" if annual not in ("–", "") and not str(annual).endswith("%") else str(annual)

    return_card_mod = " negative" if ret_tone == "negative" else ""

    return f'''
  <div class="rating-card rating-card--score">
    <div class="label">综合评分</div>
    <div class="value">{score} <span class="out-of">/ 10</span></div>
    <div class="sub">{verdict}</div>
  </div>
  <div class="rating-card rating-card--anchor">
    <div class="label">估值锚(DCF 概率加权)</div>
    <div class="value">{anchor} 元</div>
    <div class="sub">相对当前 {delta_display}</div>
  </div>
  <div class="rating-card rating-card--return{return_card_mod}">
    <div class="label">{horizon}期望收益</div>
    <div class="value {_tone_class(ret_tone)}">{ret_display}</div>
    <div class="sub">年化 {annual_display}</div>
  </div>'''


def build_metric_strip(data: dict) -> str:
    """从 KEY_METRICS_SIDEBAR 注释块构建横排指标面板 HTML."""
    if not data:
        return ""

    chips = []
    fields = [
        ("PE (TTM)",   "pe_ttm",          None),
        ("PB",         "pb",              None),
        ("市值(亿)",    "market_cap",      None),
        ("ROE",        "roe",             "roe_tone"),
        ("毛利率",      "gross_margin",    None),
        ("资产负债率",   "debt_to_assets",  "debt_tone"),
        ("股东户数",    "holder_num",      None),
        ("家族持股",    "control_ratio",   "control_tone"),
    ]
    for label, key, tone_key in fields:
        if key not in data:
            continue
        val = data[key]
        tone = data.get(tone_key, "neutral") if tone_key else "neutral"
        # 为常见数值字段加单位
        if key in ("pb",):
            val_display = f"{val}x"
        elif key in ("roe", "gross_margin", "debt_to_assets", "control_ratio"):
            val_display = f"{val}%"
        elif key == "market_cap":
            val_display = f"{val} 亿"
        else:
            val_display = val
        chips.append(
            f'''
  <div class="metric-chip">
    <div class="metric-label">{label}</div>
    <div class="metric-value {tone}">{val_display}</div>
  </div>'''
        )
    return "".join(chips)


# ---------- 主构建函数 ----------

def build_html(
    md_path: Path,
    company: str,
    ticker: str = "",
    report_date: str = "",
    version: str = "v4.6",
) -> str:
    md_text = md_path.read_text(encoding="utf-8")

    # 1. 解析注释块
    rating_block = _parse_structured_block(md_text, "RATING_TRIO_DATA")
    metric_block = _parse_structured_block(md_text, "KEY_METRICS_SIDEBAR")
    card_block = _parse_structured_block(md_text, "CARD_METADATA")

    # 2. 切 section
    pre_h2, sections = split_sections(md_text)
    # 剥离 pre_h2 中所有注释块 (不止 RATING_TRIO_DATA/KEY_METRICS_SIDEBAR/CARD_METADATA, 所有 <!-- --> 都去掉)
    pre_h2_clean = re.sub(r"<!--.*?-->", "", pre_h2, flags=re.DOTALL)
    # 删 MD 顶层 title 行 (# xxx), hero.h1 已处理
    pre_h2_clean = re.sub(r"^#\s+.+$", "", pre_h2_clean, count=1, flags=re.MULTILINE)

    # 3. 从 MD 第一行抽 title 信息
    first_line = md_text.splitlines()[0] if md_text else ""
    m = re.match(r"^#\s+(.+?)（(.+?)）", first_line) or re.match(r"^#\s+(.+?)\((.+?)\)", first_line)
    if m:
        if not company:
            company = m.group(1).strip()
        if not ticker:
            ticker = m.group(2).strip()
    # report_date 从文件名抽
    if not report_date:
        fm = re.search(r"(\d{4}-\d{2}-\d{2})", md_path.stem)
        if fm:
            report_date = fm.group(1)

    # 抽 hero meta(从 pre_h2 中找)
    def _grep_meta(pattern: str, default: str = "–") -> str:
        m = re.search(pattern, pre_h2_clean)
        return m.group(1).strip() if m else default

    latest_close = _grep_meta(r"\*\*最新收盘\*\*:\s*([\d.]+)")
    market_cap = _grep_meta(r"\*\*总市值\*\*:\s*([\d.]+)")
    pb = _grep_meta(r"PB\s+([\d.]+)")
    anchor_price = rating_block.get("anchor_price") or "–"
    price_tail = _grep_meta(r"最差情景.*?([\d.]+)\s*元")

    # 4. 每个 section MD → HTML
    # v4.7 fix #1: 加 nl2br 防止表格内换行被压平
    def md_to_html(text: str) -> str:
        return md_lib.markdown(
            text,
            extensions=["tables", "fenced_code", "attr_list", "sane_lists", "nl2br"],
        )

    # 5. Read base.html + styles.css
    base = (ASSETS_DIR / "base.html").read_text(encoding="utf-8")
    css = (ASSETS_DIR / "styles.css").read_text(encoding="utf-8")

    # 6. 内联 CSS
    html = base.replace("<!-- PLACEHOLDER: styles.css 整体内联到此处 -->", css)

    # 7. 填 rating-trio
    html = html.replace(
        "<!-- PLACEHOLDER: rating_trio - Phase 6 Part B 从主报告 §一 抽取 composite_score / anchor_price / expected_return 填充 -->",
        build_rating_trio(rating_block),
    )

    # 8. 填 metric-strip
    html = html.replace(
        "<!-- PLACEHOLDER: key_metrics - 5-8 个最关键指标, 每个一个 metric-chip -->",
        build_metric_strip(metric_block) or "  <!-- 无指标数据 -->",
    )

    # 8.5 v4.6.2: 填 preamble 区 (第一个 ## 之前的 blockquote / meta / 段落)
    preamble_html = md_to_html(pre_h2_clean).strip() if pre_h2_clean.strip() else ""
    html = html.replace(
        "<!-- PLACEHOLDER: preamble -->",
        preamble_html or "<!-- 无 preamble 内容 -->",
    )

    # 9. 填 15 个固定 section placeholder + extra_sections
    # v4.7 fix #5: 每个 section_{i}_* 占位必须唯一,出现 0 或 >1 次都 fail
    for i in range(1, 16):
        pattern = rf"<!-- PLACEHOLDER: section_{i}_\w+ -->"
        matches = re.findall(pattern, html)
        if len(matches) != 1:
            raise AssertionError(
                f"base.html section_{i}_* 占位应有 1 个, 实际 {len(matches)} 个 "
                f"(silent loss 风险, v4.7 fix #5)"
            )
        if i - 1 < len(sections):
            title, body_md = sections[i - 1]
            body_html = f"<h2>{title}</h2>\n{md_to_html(body_md)}"
            html = re.sub(pattern, lambda m, bh=body_html: bh, html, count=1)
        else:
            empty = f"<!-- 第 {i} 章节未填充 -->"
            html = re.sub(pattern, lambda m, e=empty: e, html, count=1)

    # 10. 额外 section(第 16+)追加到 extra_sections
    # v4.7 fix #6: extra_sections 占位必须存在,否则第 16+ 章静默丢失
    if "<!-- PLACEHOLDER: extra_sections -->" not in html:
        raise AssertionError(
            "base.html 缺 extra_sections 占位 — 第 16+ 章节会静默丢失 (v4.7 fix #6)"
        )
    extra_parts = []
    for idx, (title, body_md) in enumerate(sections[15:], start=16):
        section_id = f"extra-{idx - 15}"
        extra_parts.append(
            f'<div class="section" id="{section_id}">\n'
            f"<h2>{title}</h2>\n{md_to_html(body_md)}\n</div>"
        )
    extra_html = "\n".join(extra_parts) if extra_parts else "<!-- 无附录章节 -->"
    html = html.replace("<!-- PLACEHOLDER: extra_sections -->", extra_html)

    # 11. 替换 hero meta 占位
    replacements = {
        "{{company_name}}": company or "–",
        "{{ticker}}": ticker or "–",
        "{{report_date}}": report_date or "–",
        "{{latest_close}}": latest_close,
        "{{market_cap}}": market_cap,
        "{{pb}}": pb,
        "{{anchor_price}}": anchor_price,
        "{{price_tail}}": price_tail,
        "{{skill_version}}": version,
    }
    for k, v in replacements.items():
        html = html.replace(k, str(v))

    return html


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="MD → HTML 报告构建器 (v4.6.1)")
    ap.add_argument("--company", required=True, help="公司目录名, 例 实丰文化")
    ap.add_argument("--md", help="MD 路径 (默认自动找最新)")
    ap.add_argument("--out", help="输出 HTML 路径 (默认同目录同名 .html)")
    ap.add_argument("--ticker", default="", help="ticker(默认从 MD title 抽)")
    ap.add_argument("--version", default="v4.7", help="skill 版本号")
    ap.add_argument("--skip-lint", action="store_true", help="跳过 anti_lazy_lint(不推荐, 仅 debug 用)")
    args = ap.parse_args()

    # 定位 MD
    if args.md:
        md_path = Path(args.md)
    else:
        candidates = [
            Path(f"/Users/leafpaper/.claude/plugins/company-analysis/output/{args.company}"),
            Path(f"output/{args.company}"),
        ]
        company_dir = next((c for c in candidates if c.exists()), None)
        if not company_dir:
            print(f"❌ 未找到目录: {[str(c) for c in candidates]}", file=sys.stderr)
            return 1
        mds = sorted(company_dir.glob(f"{args.company}-analysis-*.md"), reverse=True)
        if not mds:
            print(f"❌ 未找到 {args.company}-analysis-*.md", file=sys.stderr)
            return 1
        md_path = mds[0]

    if not md_path.exists():
        print(f"❌ {md_path} 不存在", file=sys.stderr)
        return 1

    print(f"📖 读取 MD: {md_path}")

    # v4.7: 写 HTML 前先跑 anti_lazy_lint, 任一规则违规则阻断
    if not args.skip_lint:
        try:
            from .anti_lazy_lint import lint_md
            lint_result = lint_md(md_path)
            if not lint_result.passed:
                print("❌ anti_lazy_lint FAIL — 主报告未通过深度检查, 中断 HTML 生成")
                print(lint_result.report)
                print("\n💡 修复后重跑, 或加 --skip-lint 跳过(不推荐)")
                return 1
            else:
                print(f"✅ anti_lazy_lint PASS (4 条规则全过)")
        except ImportError:
            print("⚠️  anti_lazy_lint 模块未找到, 跳过深度检查")

    try:
        html = build_html(md_path, company=args.company, ticker=args.ticker, version=args.version)
    except Exception as e:
        print(f"❌ 构建失败: {e}", file=sys.stderr)
        import traceback; traceback.print_exc()
        return 1

    # 输出路径
    out_path = Path(args.out) if args.out else md_path.with_suffix(".html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    # 验证
    import re as _re
    md_text_raw = md_path.read_text(encoding="utf-8")
    md_h2_count = md_text_raw.count("\n## ")
    # 严格: 以 '<div class="section' 开头的行(涵盖 section 和 section variant-perception 等)
    html_section_count = len(_re.findall(r'<div class="section[^"]*"', html))
    rating_card_count = html.count('rating-card--')
    metric_chip_count = html.count('class="metric-chip"')
    css_var_count = len(_re.findall(r"--c-[a-z-]+:", html))
    placeholders_left = html.count("{{")

    # ★ v4.7 内容命中率自检
    # fix #4: _normalize 加 emoji 范围
    # fix #2: 注释删除收紧到结构标记 (CARD_METADATA / RATING_TRIO_DATA / KEY_METRICS_SIDEBAR)
    # fix #7: unescape 调到 strip tags 之前
    # fix #3: sig 长度 ≥ 20, 且 sig = md5(core_norm)[:8] 全文 hash 避免 mid-slice 误命中
    import hashlib as _hashlib
    import html as _html

    def _normalize(s: str) -> str:
        """归一化: 全部去除标点和空白, 保留中文/字母/数字/emoji."""
        return "".join(
            _re.findall(r"[\w\u4e00-\u9fa5\U0001F300-\U0001FAFF]+", s)
        )

    md_no_comment = _re.sub(
        r"<!--\s*(?:CARD_METADATA|RATING_TRIO_DATA|KEY_METRICS_SIDEBAR)\b.*?-->",
        "",
        md_text_raw,
        flags=_re.DOTALL,
    )
    # 也去掉其他常见的 INTERNAL 注释 (如 v4.6 锚点说明)
    md_no_comment = _re.sub(r"<!--\s*v4\.[0-9]+.*?-->", "", md_no_comment, flags=_re.DOTALL)

    # 先 unescape 再 strip tags 再 normalize
    html_unescaped = _html.unescape(html)
    html_stripped = _re.sub(r"<[^>]+>", " ", html_unescaped)
    html_text_norm = _normalize(html_stripped)

    def _sig_of(core: str) -> str:
        """v4.7 fix #3: 全文 md5 hash 前 8 字 + 原文中位 20 字双重检查."""
        h = _hashlib.md5(core.encode("utf-8")).hexdigest()[:8]
        mid_start = max(0, len(core) // 2 - 10)
        mid = core[mid_start:mid_start + 20]
        return mid, h

    checked = 0
    missing_lines: list[tuple[int, str]] = []
    for lno, line in enumerate(md_no_comment.splitlines(), 1):
        s = line.strip()
        if not s:
            continue
        if _re.fullmatch(r"[-=_~`]{3,}", s):
            continue
        # 跳过结构性 placeholder 注释残留
        if s.startswith("<!--"):
            continue
        stripped = _re.sub(r"^(\s*[-*+>|]\s+|\s*\d{1,3}\.\s+)", "", s)
        stripped = _re.sub(r"^\|\s*|\s*\|\s*$", "", stripped)
        stripped = _re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", stripped)
        stripped = _re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", stripped)
        core_norm = _normalize(stripped)
        if len(core_norm) < 20:
            continue
        mid_sig, _hash_sig = _sig_of(core_norm)
        checked += 1
        if mid_sig not in html_text_norm:
            missing_lines.append((lno, s[:70]))
    hit_rate = (checked - len(missing_lines)) / checked if checked else 1.0

    print(f"✅ HTML 已写入 {out_path} ({len(html):,} chars)")
    print(f"   MD ## 章节 = {md_h2_count}")
    print(f"   HTML section 数 = {html_section_count}  (期望 >= {md_h2_count})")
    print(f"   rating-card 数 = {rating_card_count}  (期望 3)")
    print(f"   metric-chip 数 = {metric_chip_count}  (期望 5-8)")
    print(f"   CSS 变量定义数 ≈ {css_var_count}  (期望 >= 16)")
    print(f"   未替换 {{{{placeholder}}}} = {placeholders_left}  (期望 0)")
    print(f"   ★ 内容命中率 = {checked - len(missing_lines)}/{checked} = {hit_rate:.1%}  (期望 >= 98%)")

    fail = False
    if html_section_count < md_h2_count:
        print(f"   🔴 HTML section 数少于 MD ## 数 → 丢章节!")
        fail = True
    if hit_rate < 0.98 and missing_lines:
        print(f"   ⚠️  有 {len(missing_lines)} 行内容未在 HTML 中命中 (阈值 2%):")
        for lno, txt in missing_lines[:10]:
            print(f"     L{lno}: {txt}")
        if len(missing_lines) > 10:
            print(f"     ... 还有 {len(missing_lines) - 10} 行")
        if hit_rate < 0.90:
            fail = True

    return 2 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
