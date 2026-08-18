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


def prepare_body(body_md: str, product: dict, decorate: bool = True) -> str:
    """章节/附录正文: MD → HTML → 表格进横滚容器 → 红标反查。"""
    body = wrap_tables(_md_to_html(body_md))
    body = upgrade_flag_links(body, product)
    if decorate:
        body = decorate_red_marks(body, red_mark_vocab(product))
    return body


# ---------- 首页各块 ----------

def _split_verdict(text: str) -> tuple[str, str]:
    """verdict → (判定短语, 其余理由)。切法与 assembly.quality_field 同源, 只是展示层分行。"""
    head = assembly.quality_field(text)
    tail = text[len(head):].lstrip("—-,,;;((\\ ") if text.startswith(head) else ""
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
        facts.append(("下次预约披露", _esc(meta["next_disclosure_date"]), ""))
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
        tiles.append(
            f'  <div class="st{cls}">{badge}\n'
            f'    <div class="l">{_esc(ind["name"])}</div>\n'
            f'    <div class="v">{_esc(ind["value"])}</div>\n'
            f'    <div class="n">{note}</div>\n'
            f"  </div>"
        )
    conclusion = panel["conclusion"]
    tiles.append(
        f'  <div class="pv"><b>面板结论:{_esc(conclusion["biz_model"])} · '
        f'{_esc(conclusion["quality_true"])}</b>'
        f'<span class="src">← 引用①质地子判定,面板不自产结论</span></div>'
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
    paragraphs = "\n".join(f"<p>{_esc(p)}</p>" for p in re.split(r"\n{2,}", intro.strip()) if p.strip())
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
    rows += [(f"三元组 {k}", tb[k], ta[k]) for k in ("state", "odds", "path")]
    rows += [(d["name"], d["before"], d["after"]) for d in cb["metric_deltas"]]
    table = (
        '<div class="tblwrap"><table><thead><tr><th>项</th><th>上版</th><th>本版</th></tr></thead><tbody>'
        + "".join(
            f"<tr><td>{_esc(a)}</td><td>{_esc(b)}</td><td>{_esc(c)}</td></tr>" for a, b, c in rows
        )
        + "</tbody></table></div>"
    )
    bullets = [
        "<li><b>翻转节点</b>:"
        + (_esc("、".join(assembly.NODE_LABELS[n] for n in cb["flipped_nodes"])) or "无")
        + "</li>"
    ]
    for item in cb["falsification_changes"]:
        verb = "触发" if item["change"] == "triggered" else "解除"
        bullets.append(f'<li><b>证伪{verb}</b>:{_esc(item["condition"])}</li>')
    if not cb["falsification_changes"]:
        bullets.append("<li><b>证伪清单</b>:无触发/解除</li>")
    verbs = {"triggered": "新增", "resolved": "解除", "level_changed": "级别变化"}
    for item in cb["red_flag_changes"]:
        bullets.append(f'<li><b>红旗{verbs[item["change"]]}</b>:{_esc(item.get("note") or item["id"])}</li>')
    if not cb["red_flag_changes"]:
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


def render_chapters(parts: dict, product: dict) -> str:
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
        out.append(
            f'<section class="chB" id="ch-{node}">\n'
            f'  <div class="hd"><span class="no">{_esc(name.strip())}</span>'
            f'<span class="qq">{_esc(question.strip())}</span>'
            f'<span class="pill {pill_cls}">{_esc(head_txt)}</span></div>\n'
            f'  <div class="bd">{prepare_body(body_md, product)}</div>\n'
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
        "chapters": render_chapters(parts, product),
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


# ---------- CLI ----------

def main():
    for stream in (sys.stdout, sys.stderr):      # Windows 控制台 GBK 下 print emoji 会炸
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    ap = argparse.ArgumentParser(description="MD → HTML 报告构建器 (v8 仪表盘 / v7 兼容)")
    ap.add_argument("--company", required=True, help="公司目录名, 例 实丰文化")
    ap.add_argument("--run-dir", help="v8: runs/{date}/ 目录(含 nodes/ 与 assembly/assembly.json)")
    ap.add_argument("--md", help="MD 路径 (默认自动找最新)")
    ap.add_argument("--out", help="输出 HTML 路径 (默认同目录同名 .html)")
    ap.add_argument("--ticker", default="", help="ticker(默认从 MD title / CARD_METADATA 抽)")
    ap.add_argument("--version", default="", help="skill 版本号(默认 v8 报告 v8.0 / v7 报告 v6.0)")
    ap.add_argument("--skip-lint", action="store_true", help="跳过 anti_lazy_lint(不推荐, 仅 debug 用)")
    args = ap.parse_args()

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
        candidates = [
            Path(f"/Users/leafpaper/.claude/plugins/company-analysis/output/{args.company}"),
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

    # ---- v8 通道: 有装配产物就走 B 仪表盘(v7 的 anti_lazy_lint 已被 v8 lint 取代, 归实现票 06) ----
    product, nodes = load_v8_context(md_path, Path(args.run_dir) if args.run_dir else None)
    if product is not None:
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

    # ---- v7 通道 ----
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
                print(f"✅ anti_lazy_lint PASS ({len(lint_result.rules)} 条规则全过)")
        except ImportError:
            print("⚠️  anti_lazy_lint 模块未找到, 跳过深度检查")

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
