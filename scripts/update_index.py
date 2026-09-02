"""Inves-Report 主页联动 (v4.6).

解决 Phase 6 Part C 痛点: 每份新报告都要手工编辑 index.html 加卡片。
v4.6 改为自动:
1. 从主报告 MD 抽取卡片元数据(ticker / 评分 / 结论 / 收益 / 日期 等)
2. 写到 output/{company}/card-metadata.json
3. 若指定 --repo, 自动合并到 Inves-Report/data/reports.json (upsert by ticker)

Usage:
    # 只生成 card-metadata.json (不改 Inves-Report)
    python3 -m scripts.update_index --company 实丰文化

    # 生成并 upsert 到 Inves-Report
    python3 -m scripts.update_index --company 实丰文化 \\
        --repo /tmp/Inves-Report-v2

    # 强制覆盖现有报告 (by ticker match)
    python3 -m scripts.update_index --company 实丰文化 \\
        --repo /tmp/Inves-Report-v2 --force
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


# ---------- 解析工具 ----------

def _find_latest_md(company_dir: Path) -> Path:
    """找 output/{company}/ 下最新的 {company}-analysis-{date}.md"""
    candidates = sorted(company_dir.glob(f"{company_dir.name}-analysis-*.md"), reverse=True)
    if not candidates:
        raise FileNotFoundError(f"未找到 {company_dir}/*-analysis-*.md")
    return candidates[0]


def _grep(text: str, pattern: str, group: int = 1, default: str = "") -> str:
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(group).strip() if m else default


def _grep_float(text: str, pattern: str, default: float | None = None) -> float | None:
    s = _grep(text, pattern)
    if not s:
        return default
    # 去掉 % 或其他单位
    s = re.sub(r"[^\d.\-+]", "", s)
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


# ---------- 语气推断 ----------

# v8: 行动档位(六档)→ 卡片语气; v8 报告无综合评分, tone 直接由档位决定
GEAR_TONE = {
    "核心仓": "bullish", "期权仓": "neutral", "等证据临界": "neutral",
    "不追高": "neutral", "减仓": "bearish", "回避": "bearish",
}


def _infer_tone(verdict: str, score: float | None) -> str:
    """根据 verdict 文本 + 评分推断 tone(bullish/neutral/bearish)."""
    v = (verdict or "").lower()
    if any(k in v for k in ["强烈看好", "推荐买入", "买入"]):
        return "bullish"
    if any(k in v for k in ["看空", "回避", "减仓"]):
        return "bearish"
    if "中性-分歧偏空" in verdict or "偏空" in v:
        return "bearish"
    if "有条件看好" in v or "看多" in v:
        return "bullish"
    # 退化到评分判断
    if score is not None:
        if score >= 6.0:
            return "bullish"
        if score < 4.0:
            return "bearish"
    return "neutral"


def _detect_market(ticker: str, company_name: str) -> str:
    t = (ticker or "").upper()
    if ".SH" in t or ".SZ" in t or ".BJ" in t or re.match(r"^\d{6}", t):
        return "a"
    if ".HK" in t or re.match(r"^0\d{3,4}\.HK", t, re.I):
        return "hk"
    if ".US" in t or re.match(r"^[A-Z]{1,5}$", t):
        return "us"
    # 一级市场(非上市公司名)
    return "pe"


# ---------- 元数据提取 ----------

@dataclass
class CardMetadata:
    slug: str = ""
    ticker: str = ""
    name: str = ""
    name_cn: str = ""
    sector: str = ""
    market: str = ""
    report_date: str = ""
    version: str = "v1"
    composite_score: float | None = None
    verdict: str = ""
    verdict_tone: str = "neutral"
    quality_field: str = ""            # v8: 质地字段(是不是好公司), 与 verdict 并列上卡片
    action_gear: str = ""              # v8: 行动档位(六档原词, 供站点按档位分组/配色)
    next_disclosure_date: str = ""     # v8: 下次预约披露日(站点超龄/陈旧警示的基准)
    review_hint: str = ""              # v8 票09: manifest 建议档(>12月未全量/≥4次增量 → 建议全量重锚)
    valuation_tag: str = ""
    one_liner: str = ""
    metrics: list[dict] = None
    expected_return_short: str = ""
    badges: list[dict] = None

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = []
        if self.badges is None:
            self.badges = []


def _slug_from_company(company_name: str, ticker: str) -> str:
    """根据 Inves-Report 现有命名惯例: EnglishName_中文名."""
    # 已有映射表(历史兼容)
    known = {
        "闻泰科技": "Wingtech_闻泰科技",
        "实丰文化": "ShifengCulture_实丰文化",
        "震安科技": "ZhenAn_震安科技",
        "西藏矿业": "TibetMining_西藏矿业",
        "纽瑞芯": "NewRadioTech_纽瑞芯",
        "程星通信": "Starway_程星通信",
        "同泰怡": "Tongtaiyi_同泰怡",
    }
    if company_name in known:
        return known[company_name]
    # fallback: ticker_company
    clean_ticker = re.sub(r"\.(SH|SZ|BJ|HK|US)$", "", ticker or "X", flags=re.I)
    return f"{clean_ticker}_{company_name}"


def _parse_structured_block(text: str, block_name: str) -> dict[str, str]:
    """解析 report-skeleton v4.6 的 HTML 注释块,如 <!-- CARD_METADATA: key: val\n ... -->"""
    m = re.search(rf"<!--\s*{block_name}:?(.*?)-->", text, re.DOTALL)
    if not m:
        return {}
    body = m.group(1)
    result = {}
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("{{"):  # 跳过未填充的 placeholder 行
            continue
        kv = re.match(r"([a-z_]+)\s*:\s*(.+?)(?:\s*\(.*\))?$", line)
        if kv:
            key, val = kv.group(1), kv.group(2).strip()
            if val and not val.startswith("{{"):
                result[key] = val
    return result


def _load_assembly(md_path: Path) -> dict | None:
    """v8 卡片优先读装配产物(唯一契约), 找不到再退回解析主报告正文。"""
    for candidate in (md_path.parent / "assembly" / "assembly.json", md_path.parent / "assembly.json"):
        if candidate.exists():
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return None
    return None


def _v8_anchor_tag(md_path: Path) -> str:
    """v8 估值标签 = ③赔率 `anchor_range` 的两端(**结构化字段**, 不是散文正则)。

    v7 的做法是拿 `估值锚…([\\d.]+)\\s*元` 去 grep 整份报告 —— 在 v8 上会扫进**附录D 的红旗行**:
    中际旭创实测命中「估值锚的外部交叉验证…一致预期目标价 1,245.60 元」, 而千分位逗号截断了数字串,
    抓出来的是 `245.6`, 首页卡片于是印了一个不存在的锚(真值 482.4–535.3)。
    v8 的锚有唯一真相源, 不该再靠正则从散文里刨。
    """
    node = Path(md_path).parent / "nodes" / "node-odds.md"
    if not node.exists():
        return ""
    try:
        from . import verdict_block

        block = verdict_block.extract_yaml_block(node.read_text(encoding="utf-8"))
    except Exception:                                  # noqa: BLE001 — 读不到就退回上层兜底
        return ""
    anchor = block.get("anchor_range") or {}
    low, high = anchor.get("low") or {}, anchor.get("high") or {}
    if not (isinstance(low.get("value"), (int, float)) and isinstance(high.get("value"), (int, float))):
        return ""
    unit = low.get("unit") or high.get("unit") or ""
    fmt = lambda v: str(int(v)) if float(v).is_integer() else str(v)   # noqa: E731
    return f"估值锚 {fmt(low['value'])}-{fmt(high['value'])} {unit}".strip()


def _verdict_card_rows(text: str, product: dict | None) -> dict[str, str]:
    """决断卡「问题 → 判定」。有 assembly.json 用它, 否则解析首页决断卡表格。"""
    if product:
        return {row["question"]: row["verdict"] for row in product.get("verdict_card", [])}
    rows = {}
    for m in re.finditer(r"^\|\s*[①②③④⑤]\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", text, re.MULTILINE):
        rows[m.group(1).strip()] = m.group(2).strip()
    return rows


def _v8_card_layout(meta: CardMetadata, text: str, product: dict | None,
                    md_path: Path | None = None) -> None:
    """v8 卡片版式(实现票 07):verdict = 行动档位人话, 质地字段并列, 三块 metrics 换成判断链口径。

    v8 报告没有综合评分/期望收益, 卡片改陈述判断链结论:行动档位 / 质地 / 贵不贵。
    """
    rows = _verdict_card_rows(text, product)
    odds = (rows.get("贵不贵") or "").split(";")[0].split("；")[0].strip()

    if not meta.one_liner:
        intro = (product or {}).get("front_page_intro") or _grep(
            text, r"### 导读\s*\n+([^\n<][^\n]*)"
        )
        meta.one_liner = re.sub(r"\s+", " ", re.sub(r"\*\*([^*]+)\*\*", r"\1", intro)).strip()[:300]

    tone_variant = {"bullish": "green", "bearish": "red"}.get(meta.verdict_tone, "amber")
    meta.metrics = [{"label": "行动档位", "value": meta.action_gear or meta.verdict,
                     "tone": {"bullish": "positive", "bearish": "negative"}.get(meta.verdict_tone, "neutral")}]
    if meta.quality_field:
        meta.metrics.append({"label": "质地", "value": meta.quality_field, "tone": "neutral"})
    if odds:
        meta.metrics.append({"label": "贵不贵", "value": odds, "tone": "neutral"})
    # 估值标签以③的结构化锚为准, **覆盖** v7 那条散文正则的结果(它会扫进附录D 的红旗行)
    meta.valuation_tag = (
        (_v8_anchor_tag(md_path) if md_path else "") or meta.valuation_tag or odds
    )

    meta.badges = [{"label": meta.verdict, "variant": tone_variant}]
    if meta.quality_field:
        meta.badges.append({"label": f"质地 {meta.quality_field}", "variant": "amber"})
    if odds:
        meta.badges.append({"label": f"赔率 {odds}", "variant": "amber"})


def extract_metadata(md_path: Path, company_name: str) -> CardMetadata:
    text = md_path.read_text(encoding="utf-8")

    meta = CardMetadata()
    meta.name = company_name  # default, 英文名稍后尝试抽
    meta.name_cn = company_name

    # v4.6: 优先解析 HTML 注释中的结构化 metadata 块(Phase 3 写报告时填入)
    card_block = _parse_structured_block(text, "CARD_METADATA")
    rating_block = _parse_structured_block(text, "RATING_TRIO_DATA")

    # 文件名推 ticker + date
    fname = md_path.stem  # 如 "实丰文化-analysis-2026-04-24"
    date_m = re.search(r"(\d{4}-\d{2}-\d{2})", fname)
    if date_m:
        meta.report_date = date_m.group(1)

    # Title 抽 ticker: # xxx(002862.SZ)投资分析报告
    title = _grep(text, r"^#\s+(.+)$")
    ticker_m = re.search(r"\(([^)]*\.(SH|SZ|BJ|HK|US)[^)]*)\)", title)
    if ticker_m:
        meta.ticker = ticker_m.group(1).strip()
    else:
        # fallback: 找任何 "XXXXXX.SZ" 或纯 ticker
        tm = re.search(r"\b(\d{6}\.(SH|SZ|BJ)|[A-Z]{1,5}\.US|\d{1,5}\.HK|\d{6})\b", title)
        if tm:
            meta.ticker = tm.group(1)

    meta.market = _detect_market(meta.ticker, company_name)
    meta.slug = _slug_from_company(company_name, meta.ticker)

    # 版本号: v8 由装配写进 CARD_METADATA; 否则从 title 的 v4.1 等或正文末尾找
    vm = re.search(r"\bv(\d+\.\d+)\b", title) or re.search(r"附录.*v(\d+\.\d+)", text)
    if card_block.get("version"):
        meta.version = card_block["version"]
    elif vm:
        meta.version = f"v{vm.group(1)}"

    # 综合评分
    score = _grep_float(text, r"综合评分\*?\*?:?\s*\*?\*?([\d.]+)\s*/\s*10")
    if score is None:
        score = _grep_float(text, r"综合评分\*?\*?:?\s*\*?\*?([\d.]+)")
    meta.composite_score = score

    # 投资方向(verdict) — v7.1: 优先 RATING_TRIO_DATA.verdict (part1 权威填写的行动档位, 如"等证据临界(不追高)");
    #   再退到 §一 决断卡"本案落「X」"; 兼容旧"投资方向综合判定"; 最后用一句话结论前缀。
    #   ★ 不再用裸"行动档位"正则匹配正文——会误抓"行动档位六档：核心仓/期权仓/…"菜单行。
    #   ★ v8: 装配脚本把行动档位人话写进 CARD_METADATA.verdict(RATING_TRIO_DATA 已随判断链收敛删除)。
    verdict = (rating_block.get("verdict") or card_block.get("verdict") or "").strip()
    if not verdict:
        verdict = _grep(text, r"本案落[「『\"]?\s*([^」』\"\n（(]+)")
    if not verdict:
        verdict = _grep(text, r"投资方向综合判定\*?\*?:?\s*\*?\*?([^\n*]+)")
    if not verdict:
        verdict = _grep(text, r"\*\*一句话结论\*\*:\s*\*\*([^*]+)\*\*")
    meta.verdict = verdict or "–"
    meta.quality_field = (card_block.get("quality") or "").strip()
    meta.action_gear = (card_block.get("action_gear") or "").strip()
    meta.next_disclosure_date = (card_block.get("next_disclosure_date") or "").strip()
    meta.verdict_tone = (
        (rating_block.get("verdict_tone") or "").strip()
        or GEAR_TONE.get((card_block.get("action_gear") or "").strip(), "")
        or _infer_tone(verdict, score)
    )

    # 估值锚 / 期望收益
    anchor_price = rating_block.get("anchor_price") or _grep(text, r"估值锚\*?\*?:?\s*\*?\*?[^\n元]*?([\d.]+)\s*元")
    if anchor_price:
        try:
            ap = float(re.sub(r"[^\d.]", "", anchor_price))
            meta.valuation_tag = f"估值锚 {ap} 元"
        except ValueError:
            pass

    # 期望收益: 优先从 rating block, 其次从 §十 投资回报表格
    ret_raw = rating_block.get("expected_return") or _grep(
        text, r"\*\*概率加权\s*\d*\s*年?\s*收益率\*\*\s*\|[^\|]+\|[^\|]+\|\s*\*\*([+\-−]?[\d.]+)%?\*\*"
    )
    if not ret_raw:
        # fallback: 查找 "年化 ≈ X%" 或 "期望收益 -X%" 格式
        ret_raw = _grep(text, r"2\s*年\s*期望收益率?\*?\*?\s*\|[^\n]*?([+\-−]?[\d.]+)%")
    if ret_raw:
        clean = re.sub(r"[^\d.+\-]", "", ret_raw)
        if clean:
            meta.expected_return_short = f"{clean}%"

    # 一句话结论
    one_liner = _grep(text, r"\*\*一句话结论\*\*:\s*(.+?)(?=\n\n|\n\*\*|$)", 1, "")
    # 清理 markdown 加粗
    one_liner = re.sub(r"\*\*([^*]+)\*\*", r"\1", one_liner)
    one_liner = re.sub(r"\s+", " ", one_liner).strip()
    meta.one_liner = one_liner[:300]  # 截断

    # 业务领域(sector) — 优先 CARD_METADATA 块, 其次从正文推断
    sector = card_block.get("sector")
    if not sector:
        # 从 title 或 副标题括号里找业务关键词
        # 优先: 主报告 §四 业务板块表或 §一"一句话结论"开头"XX 是..." / title 注释括号
        sector_patterns = [
            # title 行: "(002862.SZ · 玩具 + 游戏 + 光伏参股)" 等
            r"[•·]\s*([^\|\n•·]{2,40}?)(?:\s*\(|$|\n)",
            # §一: "一句话结论: 看空 — 某某业务..."
            r"\*\*行业\*\*:\s*([^\n|]+)",
            r"\*\*主营业务[^\*]*\*\*:\s*([^\n|]+)",
        ]
        for pat in sector_patterns:
            s = _grep(text, pat)
            s = s.strip(" |*·—").strip()
            # 过滤掉明显不是行业的(包含 "市场共识"/"评分" 等)
            if s and len(s) > 2 and not any(kw in s for kw in ["市场共识", "评分", "元", "亿", "%", "**"]):
                sector = s
                break
    meta.sector = (sector or "–")[:80]

    # 3 个 metrics 卡片(复用 §二 评分总览或§九估值锚)
    metrics = []
    if score is not None:
        metrics.append({"label": "综合评分", "value": f"{score}/10", "tone": "neutral"})
    if meta.expected_return_short:
        try:
            val = float(meta.expected_return_short.strip("%").replace("+", ""))
            tone = "positive" if val > 0 else "negative" if val < -10 else "neutral"
        except (ValueError, TypeError):
            tone = "neutral"
        metrics.append({"label": "期望收益", "value": meta.expected_return_short, "tone": tone})
    if meta.valuation_tag:
        # 从 valuation_tag 抽纯数字
        num = re.search(r"([\d.]+)\s*元", meta.valuation_tag)
        if num:
            metrics.append({"label": "估值锚", "value": f"{num.group(1)}元", "tone": "neutral"})
    # PB 补充(如能找到) — 限定在 header 的"总市值: X 亿 · PB Y.ZZ" 行,避开 "2024 年" 这种年份
    # 用更严格正则:PB 后跟空格再数字(小数点 1-3 位),避免匹配到 "PB 2024"
    pb_m = re.search(r"\bPB\s+([0-9]{1,3}\.[0-9]{1,3})(?:\s|x|$)", text)
    if pb_m and len(metrics) < 3:
        metrics.append({"label": "PB", "value": f"{pb_m.group(1)}x", "tone": "neutral"})
    meta.metrics = metrics[:3]

    # badges
    meta.badges = [
        {"label": f"{meta.verdict} {score}/10" if score else meta.verdict, "variant": "amber"},
    ]
    if meta.quality_field:      # v8: 质地字段与行动档位并列(卡片版式改造归实现票 07)
        meta.badges.append({"label": f"质地 {meta.quality_field}", "variant": "amber"})
    if meta.valuation_tag:
        meta.badges.append({"label": meta.valuation_tag, "variant": "amber"})

    # v8 卡片版式(实现票 07): 判断链口径覆盖 v7 的评分/期望收益口径
    if meta.version.startswith("v8") or meta.action_gear:
        _v8_card_layout(meta, text, _load_assembly(md_path), md_path=md_path)

    return meta


# ---------- reports.json upsert ----------

def upsert_reports_json(repo_data_json: Path, card: CardMetadata, force: bool = False) -> bool:
    """合并 card 到 reports.json. 返回是否新增(True)或更新(False)."""
    if repo_data_json.exists():
        data = json.loads(repo_data_json.read_text(encoding="utf-8"))
    else:
        data = {"schema_version": "v1", "reports": []}

    reports = data.setdefault("reports", [])
    card_dict = asdict(card)

    existing_idx = None
    for i, r in enumerate(reports):
        if r.get("ticker") == card.ticker and r.get("slug") == card.slug:
            existing_idx = i
            break

    if existing_idx is not None:
        if force or r.get("report_date", "") <= card.report_date:
            reports[existing_idx] = card_dict
            is_new = False
        else:
            print(f"[WARN] 已存在更新版本 {r.get('report_date')} >= {card.report_date},跳过(用 --force 强制覆盖)")
            return False
    else:
        reports.append(card_dict)
        is_new = True

    # 按 report_date 降序
    reports.sort(key=lambda r: r.get("report_date", ""), reverse=True)

    data["last_updated"] = card.report_date
    repo_data_json.parent.mkdir(parents=True, exist_ok=True)
    repo_data_json.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return is_new


PREVIEW_DATA_HEADER = (
    "// 本地预览兜底数据 (内容 = data/reports.json 快照)。线上以实时 fetch data/reports.json 为准。"
)


def refresh_preview_data(repo: Path, create: bool = False) -> bool:
    """把 data/reports.json 快照写回 reports.data.js(file:// 本地预览的兜底数据源)。

    线上 index.html 实时 fetch data/reports.json, 但 file:// 打开时 fetch 被 CORS 挡住,
    页面退回读 `window.REPORTS_RAW` —— 不同步这个文件, 本地预览看到的就是上一版报告。
    默认只在文件已存在时刷新(它是派生产物, 留旧的永远是错的); create=True 则不存在也建。
    """
    target = repo / "reports.data.js"
    source = repo / "data" / "reports.json"
    if not source.exists() or (not target.exists() and not create):
        return False
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    body = json.dumps(data, ensure_ascii=False, indent=2)
    # utf-8-sig: 站点历史上带 BOM, 去掉会让某些浏览器按 ANSI 解码中文
    target.write_text(f"{PREVIEW_DATA_HEADER}\nwindow.REPORTS_RAW = {body};\n", encoding="utf-8-sig")
    return True


# ---------- 对比页发布(票 10): compare/{slug}/ + data/compare.json ----------

COMPARE_PREVIEW_HEADER = (
    "// 本地预览兜底数据 (内容 = data/compare.json 快照)。线上以实时 fetch data/compare.json 为准。"
)


def compare_card(product: dict) -> dict:
    """对比组 → 首页卡片条目(与单报告卡片并列, 互相可点)。

    卡片上不放新结论: verdict 直接引裁决那一句, 成员各自的档位引各自报告 —— 同「上半零新判断」。
    """
    judge = product.get("judge") or {}
    winner = min(judge["ranking"], key=lambda r: r["rank"])["company"] if judge.get("ranking") else ""
    group = product["group"]
    markets = []
    for m in product["members"]:
        mk = m.get("market") or _detect_market(m.get("ticker") or "", m["company"])
        if mk and mk not in markets:
            markets.append(mk)
    return {
        "kind": "compare",
        "slug": group["slug"],
        "name": group["name"],
        "anchor": group["anchor"],
        "chain_note": group.get("chain_note", ""),
        "href": f"compare/{group['slug']}/index.html",
        "generated": product["generated"],
        "verdict": judge.get("verdict", ""),
        "winner": winner,
        "markets": markets,
        "member_count": len(product["members"]),
        "missing_count": len(product["missing_members"]),
        "stale_count": sum(1 for m in product["members"] if m["stale"]),
        "members": [
            {
                "company": m["company"],
                "ticker": m["ticker"],
                "market": m.get("market") or _detect_market(m.get("ticker") or "", m["company"]),
                "action_gear": m["action_gear"],
                "quality_field": m["quality_field"],
                "report_date": m["report_date"],
                "stale": m["stale"],
                # 站点视角的相对路径(compare.json 里存的是对比页自己的 ../../ 相对链接)
                "href": (m.get("report_href") or "").replace("../../", ""),
            }
            for m in product["members"]
        ],
    }


def upsert_compare_json(repo_data_json: Path, card: dict, force: bool = False) -> bool:
    """合并对比卡到 data/compare.json(按 slug upsert)。返回是否新增。

    语义合并, 不整文件覆盖 —— 这个仓库有别的会话与 cron 在写, 覆盖会毁掉别人的条目。
    """
    if repo_data_json.exists():
        data = json.loads(repo_data_json.read_text(encoding="utf-8-sig"))
    else:
        data = {"schema_version": "v1", "groups": []}
    groups = data.setdefault("groups", [])

    existing = next((i for i, g in enumerate(groups) if g.get("slug") == card["slug"]), None)
    if existing is None:
        groups.append(card)
        is_new = True
    else:
        old_date = groups[existing].get("generated", "")
        if not force and old_date > card["generated"]:
            print(f"[WARN] compare.json 里已有更新版本 {old_date} > {card['generated']},"
                  "跳过(用 --force 强制覆盖)")
            return False
        groups[existing] = card
        is_new = False

    groups.sort(key=lambda g: g.get("generated", ""), reverse=True)
    data["last_updated"] = card["generated"]
    repo_data_json.parent.mkdir(parents=True, exist_ok=True)
    repo_data_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return is_new


def refresh_compare_preview(repo: Path, create: bool = False) -> bool:
    """compare.data.js = data/compare.json 的快照(file:// 本地预览读它, 同 reports.data.js)。"""
    target = repo / "compare.data.js"
    source = repo / "data" / "compare.json"
    if not source.exists() or (not target.exists() and not create):
        return False
    body = json.dumps(json.loads(source.read_text(encoding="utf-8-sig")), ensure_ascii=False, indent=2)
    target.write_text(f"{COMPARE_PREVIEW_HEADER}\nwindow.COMPARE_RAW = {body};\n", encoding="utf-8-sig")
    return True


def publish_compare(slug: str, repo: Path | None, force: bool = False,
                    create_preview: bool = False, version: str = "v8.0") -> int:
    """装配产物 → 对比页 HTML + 站点条目。HTML 当场从 compare.json 渲染, 不捡旧文件。"""
    from . import build_html as bh
    from . import compare as cmp_mod

    try:
        product = cmp_mod.load_product(slug)
    except cmp_mod.CompareError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    if not product.get("judge"):
        print("⚠️ 这个组还没有组内裁决 —— 页面下半会明写「待产出」;发布前请先跑 compare-judge")

    html = bh.build_compare_html(product, version=version)
    gaps = bh.check_compare_coverage(html, product)
    if gaps:
        print("❌ 对比页成品自检未过:", file=sys.stderr)
        for gap in gaps:
            print(f"   - {gap}", file=sys.stderr)
        return 2

    card = compare_card(product)
    local_html = cmp_mod.group_dir(slug) / f"{slug}-compare-{product['generated']}.html"
    local_html.write_text(html, encoding="utf-8")
    card_path = cmp_mod.group_dir(slug) / "card-metadata.json"
    card_path.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 对比页 {local_html}")

    if not repo:
        return 0
    if not repo.exists():
        print(f"⚠️  {repo} 不存在,跳过发布")
        return 0
    page = repo / "compare" / slug / "index.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(html, encoding="utf-8")
    (page.parent / "card-metadata.json").write_text(
        json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 复制到 {page}")

    is_new = upsert_compare_json(repo / "data" / "compare.json", card, force=force)
    print(f"✅ {'新增' if is_new else '更新'} data/compare.json 条目 (slug={slug})")
    if refresh_compare_preview(repo, create=create_preview):
        print(f"✅ 同步 {repo / 'compare.data.js'}(本地预览兜底; 记得一起 git add)")
    print(f"\n下一步: cd {repo} && git add compare/{slug}/ data/compare.json && git commit && git push")
    return 0


# ---------- 主入口 ----------

def main():
    for stream in (sys.stdout, sys.stderr):      # Windows 控制台 GBK 下 print emoji 会炸
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    ap = argparse.ArgumentParser(description="Inves-Report 主页卡片元数据自动化 (v4.6)")
    ap.add_argument("--company", help="公司目录名, 例 实丰文化(发布对比页时不需要)")
    ap.add_argument("--compare-slug", help="v8 票10: 发布产业链对比页(compare/{slug}/ + data/compare.json)")
    ap.add_argument("--output-dir", help="output 根目录 (默认 output/)")
    ap.add_argument("--repo", help="Inves-Report 仓库路径 (例 /tmp/Inves-Report-v2). 若指定则自动 upsert reports.json")
    ap.add_argument("--force", action="store_true", help="强制覆盖 reports.json 中的现有条目")
    ap.add_argument(
        "--refresh-preview-data",
        action="store_true",
        help="reports.data.js 不存在时也生成(已存在的话 upsert 后总会自动刷新)",
    )
    args = ap.parse_args()

    # ---- 对比页通道: 输入是组的 compare.json, 与单报告卡片各走各的 ----
    if args.compare_slug:
        return publish_compare(
            args.compare_slug, Path(args.repo) if args.repo else None,
            force=args.force, create_preview=args.refresh_preview_data,
        )
    if not args.company:
        ap.error("--company 必填(或用 --compare-slug 发布对比页)")

    output_root = Path(args.output_dir) if args.output_dir else None
    # 搜索 output 目录 — 优先选含主报告 md 的,而非仅 exists 的
    candidates = []
    if output_root:
        candidates.append(output_root / args.company)
    # config 的解析规则(PLUGIN_ROOT/output 优先, 否则 SKILL_ROOT/output)是产出侧的真相源,
    # 消费侧必须问同一个人 —— 否则装好的 skill 从别处跑就找不到自己刚写的报告(票 08 发布时踩到)。
    from . import config
    candidates.extend([
        config.PLUGIN_ROOT / "output" / args.company,
        config.SKILL_ROOT / "output" / args.company,
        Path(f"output/{args.company}"),
    ])
    company_dir = None
    md_path = None
    for c in candidates:
        if c.exists():
            # v7 报告在公司目录根; v8 报告落 runs/{date}/ —— 两处一起找, 按文件名(含日期)取最新
            mds = sorted(
                list(c.glob(f"{c.name}-analysis-*.md")) + list(c.glob(f"runs/*/{c.name}-analysis-*.md")),
                key=lambda p: p.name,
                reverse=True,
            )
            if mds:
                company_dir = c
                md_path = mds[0]
                break
    if md_path is None:
        print(
            f"❌ 未找到主报告 {args.company}-analysis-*.md, 已尝试: "
            f"{[str(c) for c in candidates]}",
            file=sys.stderr,
        )
        return 1

    print(f"📖 解析: {md_path}")
    try:
        card = extract_metadata(md_path, args.company)
    except Exception as e:
        print(f"❌ 解析失败: {e}", file=sys.stderr)
        import traceback; traceback.print_exc()
        return 1

    # v8 票09 建议档: manifest 状态机(距上次全量 >12 个月 / 累计 ≥4 次增量)→ 卡片超龄警示升级
    from . import manifest as manifest_mod
    from .triage import full_rerun_advice
    m = manifest_mod.load(company_dir)
    if m and m.get("last_full_date") and card.report_date:
        advice = full_rerun_advice(m, card.report_date)
        if advice["advised"]:
            card.review_hint = "建议全量重锚: " + "; ".join(advice["reasons"])

    # 写 card-metadata.json
    card_json = company_dir / "card-metadata.json"
    card_json.write_text(
        json.dumps(asdict(card), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ 写入 {card_json}")
    print(f"   ticker={card.ticker} · score={card.composite_score} · verdict={card.verdict} · tone={card.verdict_tone}")

    # 若指定 --repo,合并到 reports.json
    if args.repo:
        repo = Path(args.repo)
        if not repo.exists():
            print(f"⚠️  {repo} 不存在,跳过 upsert")
            return 0
        data_json = repo / "data" / "reports.json"
        # 同时复制 card-metadata.json 到 repo/reports/{slug}/
        target_card = repo / "reports" / card.slug / "card-metadata.json"
        target_card.parent.mkdir(parents=True, exist_ok=True)
        target_card.write_text(card_json.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"✅ 复制到 {target_card}")

        is_new = upsert_reports_json(data_json, card, force=args.force)
        action = "新增" if is_new else "更新"
        print(f"✅ {action} reports.json 条目 (ticker={card.ticker})")

        # 本地预览兜底数据是派生产物 —— 跟着 reports.json 一起走, 否则 file:// 预览停在上一版
        if refresh_preview_data(repo, create=args.refresh_preview_data):
            print(f"✅ 同步 {repo / 'reports.data.js'}(本地预览兜底; 记得一起 git add)")
        else:
            print("· 跳过 reports.data.js(仓库里没有这个文件; 需要就加 --refresh-preview-data)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
