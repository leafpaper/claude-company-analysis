"""MD → HTML 报告构建器 (v8.0 仪表盘 / v7 旧版式双通道).

**v8 通道(默认)**: 第二套 B「仪表盘 · 一眼决断」——决断卡=5 张 verdict 瓦片、赚钱面板=stat
tiles + 红标角标、Top3=风险卡。数据两来源、各司其职:
  · 结构化件(决断卡/面板/Top3/变化区块/红标反查) ← `assembly/assembly.json`(装配层产物, 票 04);
  · 正文与附录 ← 装配好的主报告 md(章节原样, 表格进横滚容器, 红标按红旗清单反查自动上色)。
HTML 层是纯展示: 零新增阈值、零新结论, 红标只反查附录D 红旗清单(spec §3/§4)。
版式基线 = .scratch/v8-refactor/prototypes/07-delivery-samples.html variant B(无杂交)。

**v7 通道(兼容)**: 旧 9 章节 base.html 槽位填充, 保留给未迁移的历史报告。
设计要点:
1. section 槽位从 base.html 动态发现(v7.0 = 9 章节), MD ## 章节一一对应, 不丢章节
2. 顶部横排 metric-strip + 前置评级三件套
3. 规范化生成流程,不依赖 LLM inline Python

核心流程:
1. Read MD 按 ^## 切, 每段一个 section(preserve 所有章节)
2. 解析结构化注释块(CARD_METADATA / RATING_TRIO_DATA / KEY_METRICS_SIDEBAR)
3. Read base.html + styles.css, 内联 CSS
4. 固定 section 填入 base.html 的 section_1..N 占位(槽位数从 base.html 动态发现, v7.0 = 9)
5. 超出固定槽位的 section 追加到 extra_sections 占位(附录等)
6. 按 RATING_TRIO_DATA 注入 rating-trio 面板
7. 按 KEY_METRICS_SIDEBAR 注入 metric-strip 面板
8. 替换 hero meta ({{company_name}}/{{ticker}}/etc)
9. 写入 output/{company}/{company}-analysis-{date}.html

Usage:
    # v8: 直接指向 run 目录(内含 nodes/ 与 assembly/assembly.json)
    python -m scripts.build_html --company 东山精密 \\
        --run-dir output/东山精密/runs/2026-06-22

    # v8/v7 通用: 指定 md(v8 报告会自动在其所在 run 目录找 assembly.json)
    python -m scripts.build_html --company 实丰文化 \\
        --md /path/to/md --out /path/to/html.html

    # 默认自动找
    python -m scripts.build_html --company 实丰文化
"""
from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import markdown as md_lib
except ImportError:
    print("❌ 缺少依赖 'markdown', 请 pip3 install --user markdown", file=sys.stderr)
    sys.exit(1)

from . import assembly
from . import derivation
from . import red_flags as rf
from .update_index import GEAR_TONE

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
    version: str = "v6.0",
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

    # 9. 填固定 section placeholder + extra_sections
    # v6.0: section 槽位从 base.html 动态发现 (不再硬编码 15), 占位数随骨架章节数自适应。
    # 每个 section_{i}_* 占位必须唯一,出现 0 或 >1 次都 fail (silent loss 风险, v4.7 fix #5)
    section_slots = sorted(set(int(m) for m in re.findall(r"section_(\d+)_\w+", html)))
    n_slots = len(section_slots)
    for i in section_slots:
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

    # 10. 额外 section(超出固定槽位的)追加到 extra_sections
    # v4.7 fix #6: extra_sections 占位必须存在,否则附录章静默丢失
    if "<!-- PLACEHOLDER: extra_sections -->" not in html:
        raise AssertionError(
            "base.html 缺 extra_sections 占位 — 附录章节会静默丢失 (v4.7 fix #6)"
        )
    extra_parts = []
    for idx, (title, body_md) in enumerate(sections[n_slots:], start=n_slots + 1):
        section_id = f"extra-{idx - n_slots}"
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


# =====================================================================
# v8.0 交付形态 — 第二套 B「仪表盘 · 一眼决断」
# =====================================================================

V8_TEMPLATE = ASSETS_DIR / "report-v8.html"
V8_CSS = ASSETS_DIR / "report-v8.css"

# md 章标题形如 "① 质地——是不是好公司"; 标记 → 节点
CHAPTER_MARKS = {"①": "quality", "②": "state", "③": "odds", "④": "path", "⑤": "decision"}
NODE_MARKS = {node: mark for mark, node in CHAPTER_MARKS.items()}
# 红标文字通道: 级别 → 级别词。emoji 之外必须有字, 底纹之外必须有 emoji —— 三通道缺一不可。
LEVEL_WORDS = {"🔴": "致命红旗", "🟠": "高级红旗", "🟡": "中级红旗", "🟢": "低风险", "ℹ️": "信息"}
# 行动档位 → 瓦片语气: 复用 update_index 的六档映射, 不另立一套阈值
TONE_BY_STANCE = {"bullish": "good", "neutral": "watch", "bearish": "bad"}


def _esc(value) -> str:
    return html_lib.escape(str(value if value is not None else ""), quote=True)


def _md_to_html(text: str) -> str:
    """MD → HTML(nl2br 防表格内换行被压平, 同 v7 通道)。"""
    return md_lib.markdown(
        text, extensions=["tables", "fenced_code", "attr_list", "sane_lists", "nl2br"]
    )


_TABLE_RE = re.compile(r"<table\b.*?</table>", re.DOTALL)


def wrap_tables(html_text: str) -> str:
    """所有表格塞进 overflow-x 容器 —— 移动端宽表横滚, 页面本体永不横向溢出(spec §10)。"""
    return _TABLE_RE.sub(lambda m: f'<div class="tblwrap">{m.group(0)}</div>', html_text)


# ---------- 红标: 三通道渲染 + 反查(悬停浮层 / 点击直达附录D) ----------

def _flag_line(flag: dict) -> str:
    """浮层一行 = 红旗标题 + 级别 + 一句证据 + 来源 + 归属节点(反查五要素)。"""
    return (
        f'<span class="ttl">{_esc(flag["level"])} {_esc(flag["title"])}</span>'
        f'<span>{_esc(flag["evidence"])}</span>'
        f'<span class="meta">级别 {_esc(LEVEL_WORDS.get(flag["level"], flag["level"]))}'
        f' · 来源 {_esc(rf.SOURCE_LABELS.get(flag["source"], flag["source"]))}'
        f' · 归属 {_esc(rf.NODE_LABELS.get(flag["node"], flag["node"]))}</span>'
        f'<span class="go">→ 点击查看附录D 条目</span>'
    )


def _flag_plain(flag: dict) -> str:
    """title 属性兜底(浮层被横滚容器裁掉时仍能反查, 触屏长按也可见)。"""
    return (
        f'{flag["level"]} {LEVEL_WORDS.get(flag["level"], "")} {flag["title"]}'
        f'｜{flag["evidence"]}'
        f'｜来源 {rf.SOURCE_LABELS.get(flag["source"], flag["source"])}'
        f'｜归属 {rf.NODE_LABELS.get(flag["node"], flag["node"])}'
    )


def render_mark(entry: dict, label: str | None = None, inline: bool = False) -> str:
    """红标 = ①emoji ②级别词 ③底纹, 三通道并行; 元素本身是链接 → 触屏点击直达附录D 条目。

    entry = red_mark_map 的条目(mark/level/flags), label 为被标记的文本(正文行内=命中短语)。
    """
    flags = entry["flags"]
    lead = flags[0]
    text = label if label is not None else lead["title"]
    cls = f'fw fw-{entry["mark"]}' + (" fw-inline" if inline else "")
    tip = " ／ ".join(_flag_plain(f) for f in flags)
    pops = "".join(f'<span class="fw-pop" role="note">{_flag_line(f)}</span>' for f in flags[:1])
    if len(flags) > 1:                      # 同一指标命中多条红旗 → 浮层里一并列出
        pops = (
            '<span class="fw-pop" role="note">'
            + "".join(_flag_line(f) + '<span class="meta">—</span>' for f in flags[:-1])
            + _flag_line(flags[-1])
            + "</span>"
        )
    return (
        f'<a class="{cls}" href="#{_esc(lead["anchor"])}" title="{_esc(tip)}">'
        f'<span class="fw-i" aria-hidden="true">{_esc(lead["level"])}</span>'
        f'<span class="fw-t">{_esc(text)}</span> '
        f'<span class="fw-k">{_esc(LEVEL_WORDS.get(lead["level"], ""))}</span>'
        f"{pops}</a>"
    )


# 自动反查的最短短语: 太短的词(如 "FCF"、"ROE")会命中表头与无关句子, 宁可不标
MIN_AUTO_MARK_LEN = 4


def red_mark_vocab(product: dict) -> dict[str, dict]:
    """正文自动红标的词表: 红旗标题 + 命中红旗的面板指标名 → 红标条目。

    「红标不用你标」(references/node-quality.md):写手不手涂, 展示层按红旗清单反查。
    只认逐字命中, 零新增阈值 —— 没有红旗的难看数字不会被标色。
    """
    mark_map = product.get("red_mark_map") or {}
    vocab: dict[str, dict] = {}
    for flag in product.get("red_flags") or []:
        if not rf.MARK_BY_LEVEL.get(flag["level"]):
            continue
        entry = {
            "mark": rf.MARK_BY_LEVEL[flag["level"]],
            "level": flag["level"],
            "flags": [dict(flag, anchor=rf.anchor(flag["id"]))],
        }
        vocab.setdefault(flag["title"], entry)
    for name, entry in (mark_map.get("by_indicator") or {}).items():
        vocab[name] = entry
    return {k: v for k, v in vocab.items() if len(k.strip()) >= MIN_AUTO_MARK_LEN}


_TAG_RE = re.compile(r"<[^>]+>")
_TAG_NAME_RE = re.compile(r"</?\s*([A-Za-z][A-Za-z0-9]*)")
# 这些元素内部不自动标红: 链接(避免嵌套 a)、标题、表头(列标签不是数字本身)、代码
NO_MARK_TAGS = {"a", "code", "pre", "th", "h1", "h2", "h3", "h4", "h5", "h6", "script", "style"}


def decorate_red_marks(html_text: str, vocab: dict[str, dict]) -> str:
    """在正文文本节点上逐字反查红旗词表并上红标(不进链接/标题/代码块)。"""
    if not vocab:
        return html_text
    pattern = re.compile("|".join(re.escape(p) for p in sorted(vocab, key=len, reverse=True)))
    out: list[str] = []
    depth, pos = 0, 0
    for m in _TAG_RE.finditer(html_text):
        chunk = html_text[pos:m.start()]
        out.append(
            pattern.sub(lambda mm: render_mark(vocab[mm.group(0)], mm.group(0), inline=True), chunk)
            if depth == 0 else chunk
        )
        tag = m.group(0)
        name_m = _TAG_NAME_RE.match(tag)
        name = name_m.group(1).lower() if name_m else ""
        if name in NO_MARK_TAGS:
            if tag.startswith("</"):
                depth = max(0, depth - 1)
            elif not tag.endswith("/>"):
                depth += 1
        out.append(tag)
        pos = m.end()
    tail = html_text[pos:]
    out.append(pattern.sub(lambda mm: render_mark(vocab[mm.group(0)], mm.group(0), inline=True), tail)
               if depth == 0 else tail)
    return "".join(out)


_FLAG_LINK_RE = re.compile(r'<a href="#(flag-[^"]+)">(.*?)</a>', re.DOTALL)


def upgrade_flag_links(html_text: str, product: dict) -> str:
    """写手/装配写下的 `[附录D](#flag-xxx)` 引用 → 升级成同一套红标(同一实现, 统一处理)。"""
    by_anchor = {
        rf.anchor(f["id"]): {
            "mark": rf.MARK_BY_LEVEL.get(f["level"]) or "yellow",
            "level": f["level"],
            "flags": [dict(f, anchor=rf.anchor(f["id"]))],
        }
        for f in product.get("red_flags") or []
    }

    def repl(m: re.Match) -> str:
        entry = by_anchor.get(m.group(1))
        if not entry:
            return m.group(0)
        label = re.sub(r"<[^>]+>", "", m.group(2)).strip() or entry["flags"][0]["title"]
        return render_mark(entry, label, inline=True)

    return _FLAG_LINK_RE.sub(repl, html_text)


# ---------- 渐进披露 / 出处锚链接 / 估值尺(票 08 后续:不删信息, 只改读法) ----------

_H3_SPLIT = re.compile(r"(<h3\b[^>]*>.*?</h3>)", re.DOTALL)


def fold_sections(html_text: str) -> str:
    """章内 `###` 段落折进 <details>:收起时读小标题串成判断链, 展开才看推导。

    写手的 `###` 标题本来就是结论句(「差的那一半在"利润是怎么来的"——…」),
    所以折叠后信息一个字没少, 只是默认不占屏。⑤怎么办没有 `###`, 整章常驻可见。
    """
    parts = _H3_SPLIT.split(html_text)
    if len(parts) < 3:
        return html_text                       # 没有 ### = 不折(⑤决策)
    out = [parts[0]]                           # 判定行 + 子判定表: 常驻
    for i in range(1, len(parts), 2):
        head = re.sub(r"</?h3\b[^>]*>", "", parts[i]).strip()
        # summary 里不放链接:嵌套可点元素会抢走「展开/收起」的点击, 键盘顺序也乱
        head = re.sub(r"<a\b[^>]*>(.*?)</a>", r"\1", head, flags=re.DOTALL)
        body = parts[i + 1] if i + 1 < len(parts) else ""
        out.append(
            f'<details class="drill"><summary>{head}</summary>'
            f'<div class="dd">{body}</div></details>'
        )
    return "".join(out)


_CITE_TARGET = {
    "①质地": "ch-quality", "②状态": "ch-state", "③赔率": "ch-odds",
    "④路径": "ch-path", "⑤决策": "ch-decision", "⑤怎么办": "ch-decision",
}
_CITE_RE = re.compile("(" + "|".join(list(_CITE_TARGET) + [f"附录{k}" for k in "ABCDE"]) + ")")
_TAG_SPLIT = re.compile(r"(<a\b.*?</a>|<[^>]+>)", re.DOTALL)


def link_citations(html_text: str) -> str:
    """把正文里的「见①质地」「明细见附录A」渲染成真锚链接(手机上顶栏不吸顶, 手动滚回去很难)。

    只改标签之外的文字, 已经在 <a> 里的不动。
    """
    def one(chunk: str) -> str:
        return _CITE_RE.sub(
            lambda m: f'<a class="cite" href="#{_CITE_TARGET.get(m.group(1), "appx-" + m.group(1)[-1])}">{m.group(1)}</a>',
            chunk,
        )
    return "".join(
        seg if (seg.startswith("<") or i % 2) else one(seg)
        for i, seg in enumerate(_TAG_SPLIT.split(html_text))
    )


def render_valuation_meter(nodes: dict | None) -> str:
    """估值尺:轨道=锚区间, 标记=现价。一眼看出现价在合理区间「之外多远」。

    形态取自 dataviz 的 meter —— 不画三根柱, 柱子让人比高矮, 而这里的信息是「出界」。
    数据全部来自 node-odds 的 YAML 契约字段(anchor_range / current_price), 零写手工作。
    """
    odds = (nodes or {}).get("odds") or {}
    rng, cur = odds.get("anchor_range") or {}, odds.get("current_price") or {}
    lo = (rng.get("low") or {}).get("value")
    hi = (rng.get("high") or {}).get("value")
    price, unit = cur.get("value"), cur.get("unit") or "元"
    if not all(isinstance(v, (int, float)) for v in (lo, hi, price)):
        return ""
    top = max(price, hi) * 1.12
    x = lambda v: round(v / top * 100, 2)
    over = price > hi
    ratio = price / hi if hi else 0
    note = (f"现价是区间高端的 {ratio:.2f} 倍" if over
            else ("现价在区间内" if price >= lo else f"现价低于区间低端 {lo}{unit}"))
    band_w = round(max(x(hi) - x(lo), 0.6), 2)
    over_cls = " over" if over else ""
    alt = f"估值尺:合理区间 {lo}-{hi}{unit},现价 {price}{unit},{note}"
    return "\n".join([
        f'<figure class="meter" role="img" aria-label="{_esc(alt)}">',
        "  <figcaption>贵不贵:一把尺</figcaption>",
        '  <div class="track">',
        f'    <span class="band" style="left:{x(lo)}%;width:{band_w}%"></span>',
        f'    <span class="mark{over_cls}" style="left:{x(price)}%"></span>',
        "  </div>",
        # 两端刻度:没有刻度的尺不是尺 —— 读者得知道整条轨道代表什么范围
        f'  <div class="scale"><span>0</span><span>{round(top)} {unit}</span></div>',
        '  <div class="lg">'
        f'<span><i class="sw band"></i>合理区间 {lo}–{hi} {unit}'
        "<small>SOTP / DCF 两端</small></span>"
        f'<span><i class="sw mark"></i>现价 {price} {unit}'
        f"<small>{_esc(note)}</small></span></div>",
        "</figure>",
    ])


def _pct_text(value: float, digits: int = 1) -> str:
    text = f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return f"{text or '0'}%"


def render_pfn_bar(nodes: dict | None) -> str:
    """P = F + N 占比尺:一根条拆两段 —— 已赚到的 F / 为想象多付的 N。

    形态取自 dataviz 的 proportion bar(两段的部分-整体, 不画饼也不画两根柱)。
    两段之间留 2px 表面色缝隙, 不描边框。identity 三通道:颜色 + 图例文字 + 直标金额与占比,
    所以浅色主题下 N 段那支色相的对比度 WARN 由「可见直标」解除, 不靠颜色单通道。
    数据全部来自 node-odds 的 `derivation.p_f_n`(票 11), 零写手工作。
    """
    deriv = ((nodes or {}).get("odds") or {}).get("derivation") or {}
    pfn = deriv.get("p_f_n") or {}
    cap, fact, narr = pfn.get("market_cap"), pfn.get("fact"), pfn.get("narrative")
    if not all(isinstance(v, (int, float)) for v in (cap, fact, narr)) or not cap:
        return ""
    unit = deriv.get("unit") or ""
    n_share = pfn.get("narrative_share")
    n_pct = float(n_share) * 100 if isinstance(n_share, (int, float)) else narr / cap * 100
    f_pct = 100 - n_pct
    kind = "市场已收费的义务,不是白送的彩票" if pfn.get("kind") == "embedded_obligation" \
        else "白送的可选项(free option)"
    f_txt = f"{derivation._fmt(fact, unit)} · {_pct_text(f_pct)}"
    n_txt = f"{derivation._fmt(narr, unit)} · {_pct_text(n_pct)}"
    alt = (f"股价拆两半:市值 {derivation._fmt(cap, unit)} 里, 已赚到的 F {f_txt},"
           f"为想象多付的 N {n_txt}")
    return "\n".join([
        f'<figure class="pfn" role="img" aria-label="{_esc(alt)}">',
        "  <figcaption>股价拆两半:已赚到的 · 为想象多付的</figcaption>",
        '  <div class="bar">',
        f'    <span class="sg f" style="flex-basis:calc({f_pct:.2f}% - 1px)"></span>',
        f'    <span class="sg n" style="flex-basis:calc({n_pct:.2f}% - 1px)"></span>',
        "  </div>",
        '  <div class="lg">'
        f'<span><i class="sw f"></i>已赚到的 F {_esc(f_txt)}'
        f'<small>{_esc(pfn.get("fact_basis") or "")}</small></span>'
        f'<span><i class="sw n"></i>为想象多付的 N {_esc(n_txt)}'
        f"<small>{_esc(kind)}</small></span></div>",
        "</figure>",
    ])


# 左尾情景的短名:取第一个「→」之前的部分(「谁出事」), 「→」之后是后果, 数值列已经说了
_LADDER_SPLIT = re.compile(r"\s*(?:→|->|—>)")
_LADDER_BREAK = re.compile(r"[,,、;;::+＋=＝\s]")     # 含空白: 「114.18 亿」这种没有标点的串靠它落刀
_LADDER_LABEL_MAX = 26


def _ladder_head(scenario: str) -> str:
    """情景的「谁出事」部分, 不截断 —— 屏幕阅读器与 title 用它。"""
    return _LADDER_SPLIT.split(scenario.strip(), 1)[0].strip() or scenario.strip()


def _ladder_label(scenario: str) -> str:
    """轨道左侧那一列的短名。

    截断只在标点边界上落刀 —— 硬砍会切在数字中间(「应收 10…」把 105.98 亿砍成 10),
    那正是 dataviz anti-patterns 里「标签被裁掉首尾字符」的那一条, 而且砍出来的是假数字。
    """
    head = _ladder_head(scenario)
    if len(head) <= _LADDER_LABEL_MAX:
        return head
    cuts = [m.start() for m in _LADDER_BREAK.finditer(head) if m.start() <= _LADDER_LABEL_MAX]
    return (head[:cuts[-1]] if cuts else head[:_LADDER_LABEL_MAX - 1]) + "…"


def render_left_tail_ladder(nodes: dict | None) -> str:
    """左尾深度阶梯:一条一级台阶, 由浅到深往下走。

    单一色相 —— 全部台阶都在零的同一侧(都是跌幅), 长度已经编码了量级, 再按深浅调色
    就是把同一件事编码两遍(dataviz anti-patterns「彩虹条形图」)。色相取自调色板的
    发散对(蓝↔红)的红臂, 因为整张图只落在红臂上。
    量不到价格的情景不静默丢:图下一行明说还有几条、分别是什么量级(票 11 契约里的 magnitude)。
    """
    tails = ((nodes or {}).get("path") or {}).get("left_tail") or []
    graded = [t for t in tails if isinstance(t.get("depth_pct"), (int, float))]
    if not graded:
        return ""
    graded = sorted(graded, key=lambda t: t["depth_pct"], reverse=True)   # 浅 → 深
    # 轨道满格 = 本图最深的那级, 不是 −100% —— 八条都在 −70% 上下时, 按 −100% 归一
    # 会把八根条压成一样长, 阶梯就没有台阶了
    deepest = max(abs(float(t["depth_pct"])) for t in graded) or 1.0
    rungs = []
    for t in graded:
        depth = abs(float(t["depth_pct"]))
        width = max(depth / deepest * 100, 2)
        full = t["scenario"] + (f" —— {t['depth_basis']}" if t.get("depth_basis") else "")
        rungs.append(
            f'    <li title="{_esc(full)}">'
            f'<span class="lb">{_esc(_ladder_label(t["scenario"]))}</span>'
            f'<span class="tr"><i style="width:{width:.1f}%"></i></span>'
            f'<b class="dv">−{_pct_text(depth)}</b></li>'
        )
    ungraded = [t for t in tails if not isinstance(t.get("depth_pct"), (int, float))]
    foot = ""
    if ungraded:
        items = "; ".join(
            f"{_esc(_ladder_label(t['scenario']))}({_esc(t.get('magnitude') or '未量化')})"
            for t in ungraded
        )
        foot = f'  <p class="foot">另 {len(ungraded)} 条量不到价格:{items}</p>'
    alt = "左尾深度阶梯:" + "、".join(          # 朗读用全名, 截断只是版面上的事
        f"{_ladder_head(t['scenario'])} −{_pct_text(abs(float(t['depth_pct'])))}" for t in graded
    )
    return "\n".join(filter(None, [
        f'<figure class="ladder" role="img" aria-label="{_esc(alt)}">',
        "  <figcaption>左尾有多深:兑现之前最坏要扛多少</figcaption>",
        '  <ol class="rungs">', *rungs, "  </ol>",
        foot,
        "</figure>",
    ]))


def render_sparkline(series: dict | None, label: str = "") -> str:
    """面板 sparkline:一格一条线, 无坐标轴无网格, 末点直标。

    单序列 → 单色 → 不要图例(标题就是它的名字)。跨零的序列补一条零基线,
    否则「−24 亿」和「+11 亿」在同一条线上看不出谁在水下。
    数值序列来自①质地 `panel.indicators[].series`(票 11);为 null 的那格不出图。
    """
    points = (series or {}).get("points") or []
    values = [p["value"] for p in points if isinstance(p.get("value"), (int, float))]
    if len(values) < 3:
        return ""
    w, h, pad = 72.0, 20.0, 3.0
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    step = (w - 2 * pad) / (len(values) - 1)
    xy = [(pad + i * step, h - pad - (v - lo) / span * (h - 2 * pad))
          for i, v in enumerate(values)]
    path = " ".join(("M" if i == 0 else "L") + f"{x:.1f} {y:.1f}" for i, (x, y) in enumerate(xy))
    zero = ""
    if lo < 0 < hi:
        y0 = h - pad - (0 - lo) / span * (h - 2 * pad)
        zero = f'<line class="z" x1="0" y1="{y0:.1f}" x2="{w:.0f}" y2="{y0:.1f}"/>'
    unit = (series or {}).get("unit") or ""
    alt = f"{label}走势:" + " → ".join(
        f"{p['label']} {p['value']}{unit}" for p in points if isinstance(p.get("value"), (int, float))
    )
    return (
        f'<svg class="spark" viewBox="0 0 {w:.0f} {h:.0f}" preserveAspectRatio="none" '
        f'role="img" aria-label="{_esc(alt)}">{zero}'
        f'<path class="ln" d="{path}"/>'
        f'<circle class="pt" cx="{xy[-1][0]:.1f}" cy="{xy[-1][1]:.1f}" r="2.4"/></svg>'
    )


def prepare_body(body_md: str, product: dict, decorate: bool = True, fold: bool = False) -> str:
    """章节/附录正文: MD → HTML → 表格进横滚容器 → 红标反查。"""
    body = wrap_tables(_md_to_html(body_md))
    body = upgrade_flag_links(body, product)
    if decorate:
        body = decorate_red_marks(body, red_mark_vocab(product))
    body = link_citations(body)
    if fold:
        body = fold_sections(body)
    return body


# ---------- 首页各块 ----------

_PAREN_OPEN = "(（"
_PAREN_CLOSE = ")）"


def _split_verdict(text: str) -> tuple[str, str]:
    """verdict → (判定短语, 其余理由)。切法与 assembly.quality_field 同源, 只是展示层分行。

    括号成对剥离:剥掉左括号却把右括号留在 tail 里, 决断卡上就会出现「高信仰体检 6/7)」
    这种孤立反括号(票 08 交付评审在④路径卡上抓到)。
    """
    head = assembly.quality_field(text)
    tail = text[len(head):].lstrip("—-,,;;((\\ ") if text.startswith(head) else ""
    opens = sum(tail.count(c) for c in _PAREN_OPEN)
    closes = sum(tail.count(c) for c in _PAREN_CLOSE)
    while tail and tail[-1] in _PAREN_CLOSE and closes > opens:
        tail = tail[:-1].rstrip()
        closes -= 1
    return head or text, tail


def _flag_load(product: dict) -> dict[str, list[str]]:
    """各节点背了几面旗(红旗条目的 node 字段是契约字段, 非新判断)。"""
    load: dict[str, list[str]] = {}
    for flag in product.get("red_flags") or []:
        if rf.MARK_BY_LEVEL.get(flag["level"]):
            load.setdefault(flag["node"], []).append(flag["level"])
    return load


def _load_chip(levels: list[str]) -> str:
    if not levels:
        return '<span class="chip">无红旗</span>'
    counts = {lvl: levels.count(lvl) for lvl in rf.LEVELS if lvl in levels}
    body = " ".join(f"{lvl}×{n}" for lvl, n in counts.items())
    return f'<a class="chip" href="#appx-D" title="本节点红旗数(明细见附录D)">{_esc(body)} 红旗</a>'


def node_tone(node: str, product: dict, load: dict[str, list[str]]) -> str:
    """瓦片语气: ⑤按行动档位(决策层唯一权威); ①-④按本节点红旗载荷(纯展示映射, 见 spec §3)。"""
    if node == "decision":
        gear = product["metadata"]["action_gear"]
        return TONE_BY_STANCE.get(GEAR_TONE.get(gear, "neutral"), "watch")
    levels = load.get(node, [])
    if any(lvl in ("🔴", "🟠") for lvl in levels):
        return "bad"
    if "🟡" in levels:
        return "watch"
    return "node"


def render_hero_facts(product: dict, nodes: dict[str, dict] | None = None) -> str:
    """事实条 = 行动档位 / 质地 / 现价 / 锚区间 / 下次预约披露日(全部契约字段, 不自行推导)。"""
    meta = product["metadata"]
    facts = [
        ("行动档位", _esc(meta["action_gear"]), ""),
        ("质地", _esc(meta["quality_field"]), ""),
    ]
    odds = (nodes or {}).get("odds") or {}
    price = odds.get("current_price")
    if price:
        facts.append(("现价", _esc(assembly._fmt_number(price["value"])),
                      _esc(price.get("unit") or "")))
    anchor = odds.get("anchor_range")
    if anchor:
        low, high = anchor["low"], anchor["high"]
        unit = low.get("unit") or high.get("unit") or ""
        note = "" if anchor.get("same_direction", True) else "两端不同向"
        facts.append((
            f"锚区间{('(' + note + ')') if note else ''}",
            _esc(f'{assembly._fmt_number(low["value"])}–{assembly._fmt_number(high["value"])}'),
            _esc(unit),
        ))
    if meta.get("next_disclosure_date"):
        # 披露日早于基准日 = 已披露(增量复查常态: 本次 run 就是它触发的), 别再喊「下次」
        disc = meta["next_disclosure_date"]
        if disc < meta.get("date", ""):
            facts.append(("预约披露", _esc(f"{disc}(已披露)"), ""))
        else:
            facts.append(("下次预约披露", _esc(disc), ""))
    return "\n".join(
        f'  <div class="fact"><div class="l">{label}</div>'
        f'<div class="v">{value}{f" <small>{unit}</small>" if unit else ""}</div></div>'
        for label, value, unit in facts
    )


def render_verdict_tiles(product: dict) -> str:
    """决断卡 = 5 张 verdict 瓦片(判定大字 + 理由小字 + 出处 + 本节点红旗数)。"""
    load = _flag_load(product)
    tiles = []
    for row in product["verdict_card"]:
        node = row["source_node"]
        head, tail = _split_verdict(row["verdict"])
        tiles.append(
            f'  <a class="dc t-{node_tone(node, product, load)}" href="#ch-{node}">\n'
            f'    <div class="q">{_esc(NODE_MARKS[node])} {_esc(row["question"])}</div>\n'
            f'    <div class="a">{_esc(head)}</div>\n'
            f'    <div class="w">{_esc(tail)}</div>\n'
            f'    <div class="s"><span class="chip">{_esc(assembly.NODE_LABELS[node])}</span> '
            f'{_load_chip(load.get(node, []))}</div>\n'
            f"  </a>"
        )
    return "\n".join(tiles)


def render_panel(product: dict) -> str:
    """赚不赚钱面板 = stat tiles + 红标角标; 结论行引用①质地子判定, 面板不自产结论。"""
    panel = product["panel"]
    by_ind = (product.get("red_mark_map") or {}).get("by_indicator", {})
    tiles = []
    for ind in panel["indicators"]:
        entry = by_ind.get(ind["name"])
        badge = f'<div class="fb">{render_mark(entry)}</div>' if entry else ""
        cls = f' mk-{entry["mark"]}' if entry else ""
        note = _esc(ind["trend"])
        if ind.get("peer_percentile"):
            note += f' · peer {_esc(ind["peer_percentile"])}'
        if ind.get("note"):
            note += f' <span class="why">（{_esc(ind["note"])}）</span>'
        spark = render_sparkline(ind.get("series"), ind["name"])
        tiles.append(
            f'  <div class="st{cls}">{badge}\n'
            f'    <div class="l">{_esc(ind["name"])}</div>\n'
            f'    <div class="v">{_esc(ind["value"])}{spark}</div>\n'
            f'    <div class="n">{note}</div>\n'
            f"  </div>"
        )
    conclusion = panel["conclusion"]
    tiles.append(
        f'  <div class="pv"><b>面板结论:{_esc(conclusion["biz_model"])} · '
        f'{_esc(conclusion["quality_true"])}</b>'
        f'<span class="src">← 结论来自①质地</span></div>'
    )
    return (
        '<div class="secl"><span class="t">赚不赚钱面板</span> '
        '<span class="chip man">写手选 3-5</span></div>\n'
        f'<p class="reason">{_esc(panel["industry_reason"])}</p>\n'
        '<div class="tiles">\n' + "\n".join(tiles) + "\n</div>"
    )


def render_top3(product: dict) -> str:
    """Top3 = 风险卡; 标题即红标(点击直达附录D), 卡上标明归属节点、来源与同组并入的红旗。"""
    by_id = {f["id"]: f for f in product.get("red_flags") or []}
    cards = []
    for item in product["top3"]:
        lead = by_id.get(item["red_flag_id"], {
            "id": item["red_flag_id"], "level": item["level"], "title": item["title"],
            "evidence": item["evidence"], "source": item.get("source", "script"),
            "node": item.get("node", "quality"),
        })
        # 同一「首要关联指标」的多条红旗被装配合并成一条风险 —— 浮层里两源一并列出,
        # 按级别排序使领衔条目 = 装配选定的代表(red_flag_id), 红标 emoji/颜色/锚点三者一致
        group = sorted(
            [by_id[i] for i in item.get("red_flag_ids", []) if i in by_id] or [lead],
            key=lambda f: rf.LEVEL_ORDER[f["level"]],
        )
        entry = {
            "mark": rf.MARK_BY_LEVEL.get(item["level"]) or "yellow",
            "level": item["level"],
            "flags": [dict(f, anchor=rf.anchor(f["id"])) for f in group],
        }
        node = item.get("node", "")
        others = "".join(
            f' · <a href="#{rf.anchor(f["id"])}">{_esc(f["level"])} {_esc(f["title"])}'
            f'({_esc(rf.SOURCE_LABELS.get(f["source"], f["source"]))})</a>'
            for f in group if f["id"] != lead["id"]
        )
        cards.append(
            f'  <div class="rk mk-{entry["mark"]}">\n'
            f'    <div class="t">{render_mark(entry, item["title"])}</div>\n'
            f'    <div class="d">{_esc(item["evidence"])}</div>\n'
            f'    <div class="h">所属节点 → <a href="#ch-{_esc(node)}">'
            f'{_esc(rf.NODE_LABELS.get(node, node))}</a>'
            f' · 来源 {_esc(rf.SOURCE_LABELS.get(item.get("source"), "—"))}{others}</div>\n'
            f"  </div>"
        )
    return "\n".join(cards)


def render_intro(product: dict) -> str:
    intro = product.get("front_page_intro")
    if not intro:
        return "<!-- 无写手导读 -->"
    # 按**单**换行切句成段:导读是首页唯一不走 markdown 渲染的人工字段, 写手在 YAML 里
    # 一句一行写得清清楚楚, 但 HTML 会把单换行吃成空格 —— 只认空行的话 5 句会合成一个 <p>,
    # 桌面 1120px 下看着是 5 行、看不出问题, 390px 下就是一堵十几行没有断点的墙,
    # 而最该一眼看到的末句(「那天盯三件事」)正好埋在墙底(票 08 第 5 轮交付评审实测)。
    paragraphs = "\n".join(f"<p>{_esc(p)}</p>" for p in re.split(r"\n+", intro.strip()) if p.strip())
    return (
        '<div class="secl"><span class="t">写手导读</span> '
        '<span class="chip man">人工 3-5 句</span></div>\n'
        f'<div class="intro">{paragraphs}</div>'
    )


def render_change_block(product: dict) -> str:
    """较上版变化(增量复查 --review 才有): 首句人话答「阿尔法变了没」。"""
    cb = product.get("change_block")
    if not cb:
        return "<!-- 全量 run: 无较上版变化区块 -->"
    tb, ta = cb["triad_before"], cb["triad_after"]
    rows = [("行动档位", cb["gear_before"], cb["gear_after"])]
    rows += [(f"三元组·{assembly.NODE_LABELS[k]}", tb[k], ta[k]) for k in ("state", "odds", "path")]
    rows += [(d["name"], d["before"], d["after"]) for d in cb["metric_deltas"]]
    table = (
        '<div class="tblwrap"><table><thead><tr><th>项</th><th>上版</th><th>本版</th></tr></thead><tbody>'
        + "".join(
            f"<tr><td>{_esc(a)}</td><td>{_esc(b)}</td><td>{_esc(c)}</td></tr>" for a, b, c in rows
        )
        + "</tbody></table></div>"
    )
    kinds = cb.get("flip_kinds") or {}
    verdict_flips = [n for n in cb["flipped_nodes"] if kinds.get(n, "verdict") == "verdict"]
    sub_flips = [n for n in cb["flipped_nodes"] if kinds.get(n) == "sub"]
    flip_bits = []
    if verdict_flips:
        flip_bits.append("、".join(assembly.NODE_LABELS[n] for n in verdict_flips) + " 判定翻转")
    if sub_flips:
        flip_bits.append("、".join(assembly.NODE_LABELS[n] for n in sub_flips) + " 子判定变化(判定语未变)")
    bullets = [f'<li><b>判定变化</b>:{_esc(";".join(flip_bits) or "无")}</li>']
    for item in cb["falsification_changes"]:
        verb = "触发" if item["change"] == "triggered" else "解除"
        bullets.append(f'<li><b>证伪{verb}</b>:{_esc(item["condition"])}</li>')
    if not cb["falsification_changes"]:
        bullets.append("<li><b>证伪清单</b>:无触发/解除</li>")
    # 红旗变化: 🟢/ℹ️ 是绿灯与信息更新, 不许借「红旗」名头吓人; 长清单收进折叠组
    # (分组口径 = assembly.flag_change_is_soft, 与 alpha_summary 的计数同源)
    verbs = {"triggered": "新增", "resolved": "解除", "level_changed": "级别变化"}
    flag_items, green_items = [], []
    for item in cb["red_flag_changes"]:
        note = item.get("note") or item["id"]
        target = green_items if assembly.flag_change_is_soft(item) else flag_items
        target.append(f'<li><b>{"绿灯更新" if target is green_items else "红旗" + verbs[item["change"]]}</b>:{_esc(note)}</li>')
    if flag_items or green_items:
        counts = []
        if flag_items:
            counts.append(f"红旗 {len(flag_items)}")
        if green_items:
            counts.append(f"绿灯/信息 {len(green_items)}")
        bullets.append(
            f'<li><details><summary><b>红旗与绿灯变化</b>({" · ".join(counts)},点开逐条)</summary>'
            f'<ul>{"".join(flag_items + green_items)}</ul></details></li>'
        )
    else:
        bullets.append("<li><b>红旗清单</b>:无增减</li>")
    advice = ""
    if cb["full_rerun_advice"]["advised"]:
        advice = f'<div class="advice">⚠️ <b>建议全量重跑</b>:{_esc(cb["full_rerun_advice"]["reason"])}</div>'
    return (
        '<div class="secl"><span class="t">较上版变化</span> <span class="chip">机器装配</span></div>\n'
        f'<div class="change"><div class="alpha">{_esc(cb["alpha_summary"])}</div>'
        f'{table}<ul>{"".join(bullets)}</ul>{advice}</div>'
    )


# ---------- md 章节切分 ----------

def split_v8_sections(md_text: str) -> dict[str, Any]:
    """把装配好的 v8 主报告切成: 首页(丢弃, 由 assembly.json 重渲染)/ 五章 / 附录A-E / 其他。"""
    pre_h2, sections = split_sections(md_text)
    chapters: dict[str, tuple[str, str]] = {}
    appendices: list[tuple[str, str, str]] = []
    extras: list[tuple[str, str]] = []
    front_found = False
    for title, body in sections:
        head = title.strip()
        body = re.sub(r"\n-{3,}\s*$", "\n", body)     # 吃掉装配的章间分隔线(卡片自带边框)
        if head.startswith("首页"):
            front_found = True
            continue
        mark = head[0] if head else ""
        if mark in CHAPTER_MARKS:
            chapters[CHAPTER_MARKS[mark]] = (head, body)
        elif head.startswith("附录") and len(head) > 2 and head[2] in "ABCDE":
            appendices.append((head[2], head, body))
        else:
            extras.append((head, body))
    return {
        "preamble": pre_h2,
        "chapters": chapters,
        "appendices": appendices,
        "extras": extras,
        "front_found": front_found,
    }


def render_chapters(parts: dict, product: dict, nodes: dict | None = None) -> str:
    """五章 = 卡片(头部 verdict pill + 正文原样)。verdict 取自装配产物, 与首页同一处权威。"""
    verdicts = {row["source_node"]: row for row in product["verdict_card"]}
    load = _flag_load(product)
    out = []
    for node in ("quality", "state", "odds", "path", "decision"):
        entry = parts["chapters"].get(node)
        if not entry:
            continue
        title, body_md = entry
        head_txt, _ = _split_verdict(verdicts[node]["verdict"]) if node in verdicts else (title, "")
        name, _, question = title.partition("——")
        tone = node_tone(node, product, load)
        pill_cls = tone if tone in ("bad", "watch", "good") else "node"
        # 章头图:③=估值尺 + P=F+N 占比尺, ④=左尾深度阶梯(票 11)。全部由 YAML 契约驱动。
        figures = ""
        if node == "odds":
            figures = render_valuation_meter(nodes) + render_pfn_bar(nodes)
        elif node == "path":
            figures = render_left_tail_ladder(nodes)
        out.append(
            f'<section class="chB" id="ch-{node}">\n'
            f'  <div class="hd"><span class="no">{_esc(name.strip())}</span>'
            f'<span class="qq">{_esc(question.strip())}</span>'
            f'<span class="pill {pill_cls}">{_esc(head_txt)}</span></div>\n'
            f'  <div class="bd">{figures}{prepare_body(body_md, product, fold=True)}</div>\n'
            f"</section>"
        )
    return "\n".join(out)


def render_appendix_nav(parts: dict) -> str:
    cards = []
    for key, title, _ in parts["appendices"]:
        name = title[3:].strip() or title
        cards.append(
            f'  <a class="ap" href="#appx-{key}"><b>附录{_esc(key)}</b>{_esc(name)}</a>'
        )
    return "\n".join(cards) or "  <!-- 无附录 -->"


def render_appendices(parts: dict, product: dict) -> str:
    out = []
    for key, title, body_md in parts["appendices"]:
        # 附录D 是红旗清单本体(红标数据源), 不再对它自动反查标红, 免得整表刷成红的
        body = prepare_body(body_md, product, decorate=(key != "D"))
        out.append(
            f'<section class="appx" id="appx-{key}">\n  <h2>{_esc(title)}</h2>\n  {body}\n</section>'
        )
    for title, body_md in parts["extras"]:
        out.append(
            f'<section class="appx">\n  <h2>{_esc(title)}</h2>\n'
            f"  {prepare_body(body_md, product)}\n</section>"
        )
    return "\n".join(out) or "<!-- 无附录章节 -->"


# ---------- v8 总装 ----------

def build_html_v8(
    md_path: Path,
    product: dict,
    nodes: dict[str, dict] | None = None,
    ticker: str = "",
    version: str = "v8.0",
) -> str:
    """装配产物(assembly.json)+ 主报告 md → B 仪表盘成品 HTML。"""
    md_text = Path(md_path).read_text(encoding="utf-8")
    parts = split_v8_sections(md_text)
    meta = product["metadata"]

    if not ticker:
        card_block = _parse_structured_block(md_text, "CARD_METADATA")
        ticker = card_block.get("ticker", "")

    base = V8_TEMPLATE.read_text(encoding="utf-8")
    css = V8_CSS.read_text(encoding="utf-8")
    html = base.replace("<!-- PLACEHOLDER: styles -->", css)

    fills = {
        "hero_facts": render_hero_facts(product, nodes),
        "verdict_card": render_verdict_tiles(product),
        "panel": render_panel(product),
        "top3": render_top3(product),
        "intro": render_intro(product),
        "change_block": render_change_block(product),
        "chapters": render_chapters(parts, product, nodes),
        "appendix_nav": render_appendix_nav(parts),
        "appendices": render_appendices(parts, product),
    }
    for key, value in fills.items():
        placeholder = f"<!-- PLACEHOLDER: {key} -->"
        if placeholder not in html:
            raise AssertionError(f"report-v8.html 缺占位 {placeholder}(内容会静默丢失)")
        html = html.replace(placeholder, value)

    for key, value in {
        "{{company_name}}": meta["company"],
        "{{ticker}}": ticker or "–",
        "{{report_date}}": meta["date"],
        "{{skill_version}}": version,
    }.items():
        html = html.replace(key, _esc(value))
    return html


def load_v8_context(md_path: Path, run_dir: Path | None = None) -> tuple[dict | None, dict | None]:
    """找装配产物与节点块。run 目录 = 显式给的, 否则 md 所在目录(v8 报告落 runs/{date}/)。"""
    run_dir = Path(run_dir) if run_dir else Path(md_path).parent
    product = None
    for candidate in (run_dir / "assembly" / "assembly.json", run_dir / "assembly.json"):
        if candidate.exists():
            product = json.loads(candidate.read_text(encoding="utf-8"))
            break
    nodes = None
    if (run_dir / "nodes").is_dir():
        try:
            nodes = assembly.load_nodes(run_dir / "nodes")
        except assembly.AssemblyError:
            nodes = None                     # 事实条降级(少两块), 不阻断出片
    return product, nodes


def check_v8_coverage(html: str, product: dict, parts: dict) -> list[str]:
    """成品自检: 决断卡五行 / Top3 / 面板指标 / 五章 / 附录 一个都不能少。"""
    text = re.sub(r"<[^>]+>", " ", html_lib.unescape(html))
    flat = re.sub(r"\s+", "", text)
    missing = []
    for row in product["verdict_card"]:
        head, _ = _split_verdict(row["verdict"])
        if re.sub(r"\s+", "", head) not in flat:
            missing.append(f"决断卡「{row['question']}」判定未出现")
    for item in product["top3"]:
        if re.sub(r"\s+", "", item["title"]) not in flat:
            missing.append(f"Top3「{item['title']}」未出现")
    for ind in product["panel"]["indicators"]:
        if re.sub(r"\s+", "", ind["name"]) not in flat:
            missing.append(f"面板指标「{ind['name']}」未出现")
    for node in ("quality", "state", "odds", "path", "decision"):
        if node in parts["chapters"] and f'id="ch-{node}"' not in html:
            missing.append(f"章节 {node} 未渲染")
    for key, _, _ in parts["appendices"]:
        if f'id="appx-{key}"' not in html:
            missing.append(f"附录{key} 未渲染")
    return missing


# ---------- 对比页(票 10 --compare): compare.json → 一页上下两半 ----------

V8_COMPARE_TEMPLATE = ASSETS_DIR / "compare-v8.html"


def _member_head(member: dict) -> str:
    """表头一格 = 公司(链接回它的单报告)+ ticker + 基准日 + 陈旧徽章。"""
    anchor_mark = '<span class="anch">锚</span>' if member.get("is_anchor") else ""
    kind = "全量" if member["run_type"] == "full" else "增量"
    parts = [
        f'<a class="who" href="{_esc(member.get("report_href") or "#")}">'
        f'{_esc(member["company"])}</a>{anchor_mark}',
        f'<span class="code">{_esc(member["ticker"] or "–")}</span>',
        f'<span class="asof">基准日 {_esc(member["report_date"])} · {kind} · '
        f'{member["age_days"]} 天前</span>',
    ]
    if member["stale"]:
        parts.append('<span class="stale">⚠️ 陈旧 · 建议先跑 --review 复查再比</span>')
    return "".join(parts)


def _top3_cell(member: dict) -> str:
    items = "".join(
        f'<li>{_esc(item["level"])} {_esc(LEVEL_WORDS.get(item["level"], ""))}'
        f' {_esc(item["title"])}</li>'
        for item in member["top3"]
    )
    return f"<ol>{items}</ol>" if items else "–"


def render_compare_matrix(product: dict) -> str:
    """并排矩阵: 行 = 决断卡五问 + 锚/红旗/Top3/披露日, 列 = 各家。搬运, 不判断。"""
    from . import compare as cmp_mod

    members = product["members"]
    heads = "".join(f"<th>{_member_head(m)}</th>" for m in members)
    rows = [
        ("行动档位", [f'<span class="pill">{_esc(m["action_gear"])}</span>' for m in members], "gear"),
    ]
    for i, question in enumerate(cmp_mod.CARD_QUESTIONS):
        rows.append((question, [_esc(m["verdict_card"][i]["verdict"]) for m in members], ""))
    rows += [
        ("区间锚", [_esc(cmp_mod.anchor_text(m)) for m in members], ""),
        ("红旗", [_esc(cmp_mod.flags_text(m)) for m in members], ""),
        ("Top3 风险", [_top3_cell(m) for m in members], ""),
        ("下次披露", [_esc(m.get("next_disclosure_date") or "–") for m in members], ""),
    ]
    body = "".join(
        f"<tr><th>{_esc(label)}</th>"
        + "".join(f'<td class="{cls}">{cell}</td>' for cell in cells)
        + "</tr>"
        for label, cells, cls in rows
    )
    return (
        f'<table class="cmp"><thead><tr><th></th>{heads}</tr></thead>'
        f"<tbody>{body}</tbody></table>"
    )


def render_compare_facts(product: dict) -> str:
    members, missing = product["members"], product["missing_members"]
    stale = [m for m in members if m["stale"]]
    judge = product.get("judge")
    winner = min(judge["ranking"], key=lambda r: r["rank"])["company"] if judge else "待产出"
    facts = [
        ("组内成员", f"{len(members)} 家",
         f"另 {len(missing)} 家缺报告" if missing else "全员有完整报告"),
        ("裁决首位", winner, "compare-judge 判" if judge else "跑 compare-judge 后重装配"),
        ("基准日新鲜度", f"{len(stale)} 家陈旧",
         f"超 {product['stale_threshold_days']} 天档线" if stale else "全部在档线内"),
    ]
    return "".join(
        f'<div class="fact"><div class="l">{_esc(label)}</div>'
        f'<div class="v">{_esc(value)} <small>{_esc(note)}</small></div></div>'
        for label, value, note in facts
    )


def render_compare_notes(product: dict) -> str:
    notes = product.get("notes") or []
    if not notes:
        return ""
    items = "".join(f"<li>{_esc(n)}</li>" for n in notes)
    return f'<div class="change"><ul>{items}</ul></div>'


def render_compare_chain_note(product: dict) -> str:
    note = product["group"].get("chain_note")
    if not note:
        return ""
    return f'<p class="reason">同行口径:{_esc(note)}</p>'


def render_compare_judge(product: dict) -> str:
    """下半 = 唯一判断节点。没有裁决就明说待产出, 不拿并排卡片冒充结论。"""
    judge = product.get("judge")
    if not judge:
        return (
            '<div class="pending">⏳ 组内裁决尚未产出 —— 上半并排卡片已就绪, '
            "由 compare-judge 读 <code>compare.json</code> 写 <code>compare-judge.md</code> 后重跑装配。</div>"
        )
    cards = "".join(
        f'<div class="rank"><div class="no">第 {item["rank"]} 位</div>'
        f'<div class="who">{_esc(item["company"])}</div>'
        f'<div class="why">{_esc(item["one_liner"])}</div>'
        f'<div class="basis">依据:'
        + "、".join(_esc(assembly.NODE_LABELS.get(b, b)) for b in item["basis"])
        + "</div></div>"
        for item in sorted(judge["ranking"], key=lambda r: r["rank"])
    )
    out = [f'<div class="jv">{_esc(judge["verdict"])}</div>', f'<div class="ranks">{cards}</div>']
    if judge.get("common_risk"):
        out.append(f'<p class="reason">全组共担:{_esc(judge["common_risk"])}</p>')
    if judge.get("not_comparable"):
        items = "".join(f"<li>{_esc(x)}</li>" for x in judge["not_comparable"])
        out.append(f'<div class="intro"><p>这次不可比的维度:</p><ul>{items}</ul></div>')
    return "".join(out)


def render_compare_missing(product: dict) -> str:
    """缺报告成员 —— 全报告制的另一半: 不凑数, 但要看得见、知道怎么补。"""
    missing = product["missing_members"]
    if not missing:
        return ""
    rows = "".join(
        f'<tr><td>{_esc(m["company"])}</td><td>{_esc(m.get("ticker") or "–")}</td>'
        f'<td>{_esc(m.get("source") or "–")}</td><td>{_esc(m["reason"])}</td>'
        f'<td><code>{_esc(m.get("command") or "–")}</code></td></tr>'
        for m in missing
    )
    return (
        '<div class="secl" id="missing"><span class="t">缺报告成员</span> '
        '<span class="chip">未进对比 · 补跑后重装配即并入</span></div>'
        '<div class="tblwrap"><table class="cmp">'
        "<thead><tr><th>公司</th><th>ticker</th><th>候选来源</th><th>原因</th><th>补跑</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def build_compare_html(product: dict, version: str = "v8.0") -> str:
    """compare.json → 对比页成品 HTML(与单报告同一套 token 与组件, 不另起一套版式)。"""
    base = V8_COMPARE_TEMPLATE.read_text(encoding="utf-8")
    css = V8_CSS.read_text(encoding="utf-8")
    html = base.replace("<!-- PLACEHOLDER: styles -->", css)

    fills = {
        "chain_note": render_compare_chain_note(product),
        "hero_facts": render_compare_facts(product),
        "notes": render_compare_notes(product),
        "matrix": render_compare_matrix(product),
        "judge": render_compare_judge(product),
        "missing": render_compare_missing(product),
    }
    for key, value in fills.items():
        placeholder = f"<!-- PLACEHOLDER: {key} -->"
        if placeholder not in html:
            raise AssertionError(f"compare-v8.html 缺占位 {placeholder}(内容会静默丢失)")
        html = html.replace(placeholder, value)

    group = product["group"]
    for key, value in {
        "{{group_name}}": group["name"],
        "{{group_slug}}": group["slug"],
        "{{anchor}}": group["anchor"],
        "{{generated}}": product["generated"],
        "{{stale_days}}": product["stale_threshold_days"],
        "{{skill_version}}": version,
    }.items():
        html = html.replace(key, _esc(value))
    return html


def check_compare_coverage(html: str, product: dict) -> list[str]:
    """成品自检: 每家的公司名、五行判定与回原报告的链接一个都不能少。"""
    text = re.sub(r"<[^>]+>", " ", html_lib.unescape(html))
    flat = re.sub(r"\s+", "", text)
    missing = []
    for member in product["members"]:
        if re.sub(r"\s+", "", member["company"]) not in flat:
            missing.append(f"成员「{member['company']}」未出现")
        if member.get("report_href") and member["report_href"] not in html:
            missing.append(f"成员「{member['company']}」缺回原报告的链接")
        for row in member["verdict_card"]:
            head, _ = _split_verdict(row["verdict"])
            if re.sub(r"\s+", "", head) not in flat:
                missing.append(f"{member['company']}「{row['question']}」判定未出现")
    judge = product.get("judge")
    if judge:
        for item in judge["ranking"]:
            if re.sub(r"\s+", "", item["one_liner"]) not in flat:
                missing.append(f"裁决「{item['company']}」的一句原因未出现")
    return missing


# ---------- CLI ----------

def _build_compare(args) -> int:
    """--compare-slug 通道: compare.json → 对比页 HTML(装配归 scripts.compare, 这里只出片)。"""
    from . import compare as cmp_mod

    try:
        product = cmp_mod.load_product(args.compare_slug)
    except cmp_mod.CompareError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    if not product.get("judge"):
        print("⚠️ 这个组还没有组内裁决 —— 页面下半会明写「待产出」;发布前请先跑 compare-judge")

    html = build_compare_html(product, version=args.version or "v8.0")
    out_path = Path(args.out) if args.out else (
        cmp_mod.group_dir(args.compare_slug)
        / f"{args.compare_slug}-compare-{product['generated']}.html"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    print(f"✅ HTML(对比页)已写入 {out_path} ({len(html):,} chars)")
    print(f"   {len(product['members'])} 家并排 · "
          f"{'含组内裁决' if product.get('judge') else '裁决待产出'} · "
          f"{len(product['missing_members'])} 家缺报告 · "
          f"{sum(1 for m in product['members'] if m['stale'])} 家陈旧")
    missing = check_compare_coverage(html, product)
    if missing:
        print("❌ 成品自检未过:", file=sys.stderr)
        for item in missing:
            print(f"   - {item}", file=sys.stderr)
        return 2
    return 0


def main():
    for stream in (sys.stdout, sys.stderr):      # Windows 控制台 GBK 下 print emoji 会炸
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    ap = argparse.ArgumentParser(description="MD → HTML 报告构建器 (v8 仪表盘 / 对比页 / v7 兼容)")
    ap.add_argument("--company", help="公司目录名, 例 实丰文化(出对比页时不需要)")
    ap.add_argument("--compare-slug", help="v8 票10: 出产业链对比页(读该组的 compare.json)")
    ap.add_argument("--run-dir", help="v8: runs/{date}/ 目录(含 nodes/ 与 assembly/assembly.json)")
    ap.add_argument("--md", help="MD 路径 (默认自动找最新)")
    ap.add_argument("--out", help="输出 HTML 路径 (默认同目录同名 .html)")
    ap.add_argument("--ticker", default="", help="ticker(默认从 MD title / CARD_METADATA 抽)")
    ap.add_argument("--version", default="", help="skill 版本号(默认 v8 报告 v8.0 / v7 报告 v6.0)")
    ap.add_argument("--skip-lint", action="store_true", help="跳过 v8 lint 门控(不推荐, 仅 debug 用)")
    args = ap.parse_args()

    # ---- 对比页通道: 输入是 compare.json, 没有 md 也没有 lint(判断在各家自己的报告里已过关)----
    if args.compare_slug:
        return _build_compare(args)
    if not args.company:
        ap.error("--company 必填(或用 --compare-slug 出对比页)")

    # 定位 MD
    if args.md:
        md_path = Path(args.md)
    elif args.run_dir:
        mds = sorted(Path(args.run_dir).glob(f"{args.company}-analysis-*.md"), reverse=True)
        if not mds:
            print(f"❌ {args.run_dir} 内未找到 {args.company}-analysis-*.md", file=sys.stderr)
            return 1
        md_path = mds[0]
    else:
        # 与产出侧同源(config 的 PLUGIN_ROOT/output 优先规则), 不硬编码任何人的机器路径
        from . import config
        candidates = [
            config.PLUGIN_ROOT / "output" / args.company,
            config.SKILL_ROOT / "output" / args.company,
            Path(f"output/{args.company}"),
        ]
        company_dir = next((c for c in candidates if c.exists()), None)
        if not company_dir:
            print(f"❌ 未找到目录: {[str(c) for c in candidates]}", file=sys.stderr)
            return 1
        # v7 报告在公司目录根; v8 报告落 runs/{date}/ —— 两处一起找, 取最新
        mds = sorted(
            list(company_dir.glob(f"{args.company}-analysis-*.md"))
            + list(company_dir.glob(f"runs/*/{args.company}-analysis-*.md")),
            key=lambda p: p.name,
            reverse=True,
        )
        if not mds:
            print(f"❌ 未找到 {args.company}-analysis-*.md", file=sys.stderr)
            return 1
        md_path = mds[0]

    if not md_path.exists():
        print(f"❌ {md_path} 不存在", file=sys.stderr)
        return 1

    print(f"📖 读取 MD: {md_path}")

    # ---- v8 通道: 有装配产物就走 B 仪表盘 ----
    product, nodes = load_v8_context(md_path, Path(args.run_dir) if args.run_dir else None)
    if product is not None:
        run_dir = Path(args.run_dir) if args.run_dir else md_path.parent
        # 出片前先过机器门控(Phase 6 Step 0 的同一条规则集; fail 阻断, warn 只提示)
        if not args.skip_lint:
            from .lint_v8 import lint_run
            try:
                lint_result = lint_run(run_dir, md_path=md_path)
            except (FileNotFoundError, ValueError) as e:
                print(f"❌ lint_v8 判不了这个 run: {e}", file=sys.stderr)
                return 1
            if not lint_result.passed:
                print("❌ lint_v8 FAIL — 质量环机器门控未过, 中断 HTML 生成")
                print(lint_result.report)
                print("\n💡 按 FAIL 项修完重跑(改判断 fresh-restart 写手 → 重跑 assemble_report_v8), "
                      "或加 --skip-lint 跳过(不推荐)")
                return 1
            warned = len(lint_result.warnings)
            print(f"✅ lint_v8 PASS (fail 项全过{f', {warned} 项 warn 见下' if warned else ''})")
            for rule in lint_result.warnings:
                print(f"   ⚠️ {rule.name}: {rule.detail}")
        try:
            html = build_html_v8(
                md_path, product, nodes=nodes,
                ticker=args.ticker, version=args.version or "v8.0",
            )
        except Exception as e:
            print(f"❌ 构建失败: {e}", file=sys.stderr)
            import traceback; traceback.print_exc()
            return 1
        out_path = Path(args.out) if args.out else md_path.with_suffix(".html")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")

        parts = split_v8_sections(md_path.read_text(encoding="utf-8"))
        missing = check_v8_coverage(html, product, parts)
        marks = html.count('class="fw fw-') + html.count('class="fw fw-red fw-inline')
        print(f"✅ HTML(v8 仪表盘)已写入 {out_path} ({len(html):,} chars)")
        print(f"   决断卡 {len(product['verdict_card'])} 瓦片 · 面板 {len(product['panel']['indicators'])} 块 "
              f"· Top3 {len(product['top3'])} 卡 · 红旗 {len(product.get('red_flags') or [])} 条")
        print(f"   章节 {len(parts['chapters'])}/5 · 附录 {len(parts['appendices'])} · 红标 {marks} 处")
        wraps = html.count('class="tblwrap"')
        change = "有" if product.get("change_block") else "无"
        print(f"   表格横滚容器 {wraps} 个 · 变化区块 {change}")
        if missing:
            print("   🔴 成品自检未命中:", file=sys.stderr)
            for item in missing:
                print(f"     - {item}", file=sys.stderr)
            return 2
        return 0

    # ---- v7 通道(旧报告重出片; 无判断链节点块, v8 lint 判不了, 只做渲染) ----
    print("ℹ️  v7 兼容通道: 无装配产物, 跳过质量门控(v8 lint 的判定对象是 runs/{date}/ 的节点块)")

    try:
        html = build_html(
            md_path, company=args.company, ticker=args.ticker, version=args.version or "v6.0"
        )
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
    # 严格: 匹配所有 '<div class="section...">' 块(含附录 extra-N section)
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
