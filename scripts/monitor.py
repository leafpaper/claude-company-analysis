"""Quantitative monitor for Phase 7.

Compares a historical analysis report (baseline) against fresh Tushare/yfinance
data to identify material changes and trigger falsification checks on Phase 5
insights.

Usage:
    from scripts.monitor import Monitor
    m = Monitor(company="实丰文化", ticker="002862.SZ", market="a")
    result = m.run()
    print(result["summary"])  # markdown-ready brief

CLI:
    python3 -m scripts.monitor 实丰文化 --ticker 002862.SZ --market a
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config
from .report_parser import parse_report, extract_insights, MetricPoint, InsightPoint


# Material-change threshold
DEFAULT_CHANGE_THRESHOLD = 0.10   # ±10% triggers "重大变化"


@dataclass
class ChangeRecord:
    metric: str
    baseline_value: float | None
    fresh_value: float | None
    change_pct: float | None
    unit: str | None
    source: str
    source_detail: str | None
    baseline_context: str


@dataclass
class InsightCheck:
    insight_index: int
    title: str
    level: str
    falsification: str
    triggered: str  # "✅ 未触发" / "❌ 已触发" / "⚠️ 数据不足"
    evidence: str


@dataclass
class MonitorResult:
    company: str
    ticker: str
    market: str
    monitor_date: str
    baseline_report: str
    baseline_date: str | None
    days_since_baseline: int | None
    material_changes: list[ChangeRecord]
    stable_metrics_count: int
    insight_checks: list[InsightCheck]
    next_disclosure_date: str | None
    conclusion: str  # "维持" / "建议复评" / "重大修订"
    summary_markdown: str


# ---------- Utilities ----------

def _find_latest_report(company_dir: Path) -> Path | None:
    """Find the most recent {company}-analysis-*.md file."""
    candidates = sorted(company_dir.glob("*-analysis-*.md"), reverse=True)
    return candidates[0] if candidates else None


def _find_phase5_file(company_dir: Path) -> Path | None:
    """Find phase5-variant-perception.md or legacy phase2.5-alpha-insights.md."""
    for name in ["phase5-variant-perception.md", "phase2.5-alpha-insights.md"]:
        p = company_dir / name
        if p.exists():
            return p
    return None


def _extract_report_date(report_path: Path) -> str | None:
    """Extract YYYY-MM-DD from filename like {company}-analysis-2026-04-21.md"""
    import re
    m = re.search(r"(\d{4}-\d{2}-\d{2})", report_path.stem)
    return m.group(1) if m else None


def _days_between(date1: str, date2: str) -> int | None:
    try:
        d1 = dt.datetime.strptime(date1, "%Y-%m-%d").date()
        d2 = dt.datetime.strptime(date2, "%Y-%m-%d").date()
        return abs((d2 - d1).days)
    except Exception:
        return None


# ---------- Fresh data fetcher ----------

def _fetch_fresh_metrics(ticker: str, market: str) -> dict[str, Any]:
    """Re-run collector + derived_metrics, return merged dict of metric→value."""
    fresh: dict[str, Any] = {}

    if market.lower() in ("a", "a股"):
        from .tushare_collector import TushareCollector, normalize_a_code
        from .derived_metrics import compute_a_share
        c = TushareCollector()
        ts_code = normalize_a_code(ticker)
        bundle = c.collect_all(ts_code, start_year=2022)
        metrics = compute_a_share(bundle)
        fresh["bundle"] = bundle
        fresh["metrics"] = metrics
        fresh["ts_code"] = ts_code

        # next disclosure date from disclosure_date API
        try:
            disc = bundle.get("disclosure_date")
            if disc is not None and not disc.empty:
                # Get the nearest future ann_date or pre_ann_date
                fresh["next_disclosure"] = _nearest_future_disclosure(disc)
        except Exception:
            fresh["next_disclosure"] = None

    elif market.lower() in ("us", "美股"):
        from .us_collector import USCollector
        from .derived_metrics import compute_us
        c = USCollector()
        bundle = c.collect_all(ticker)
        metrics = compute_us(bundle)
        fresh["bundle"] = bundle
        fresh["metrics"] = metrics
        fresh["ts_code"] = ticker
        fresh["next_disclosure"] = None

    elif market.lower() in ("hk", "港股"):
        from .hk_collector import HKCollector
        c = HKCollector()
        bundle = c.collect_all(ticker)
        fresh["bundle"] = bundle
        fresh["metrics"] = {}  # hk metrics TBD
        fresh["ts_code"] = ticker
        fresh["next_disclosure"] = None

    else:
        raise ValueError(f"Unknown market: {market}")

    return fresh


def _nearest_future_disclosure(df) -> str | None:
    """From disclosure_date DataFrame, pick the nearest future date."""
    import pandas as pd
    today = dt.date.today().strftime("%Y%m%d")
    for col in ("pre_ann_date", "ann_date", "modify_date"):
        if col in df.columns:
            future = df[df[col] > today].sort_values(col)
            if not future.empty:
                raw = str(future.iloc[0][col])
                if len(raw) == 8:
                    return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return None


# ---------- Baseline vs fresh comparison ----------

def _value_from_fresh(metric_point: MetricPoint, fresh: dict[str, Any]) -> float | None:
    """Given a baseline MetricPoint with source tag like 'Tushare:income.revenue' or
    'metrics.json:valuation.pb', try to fetch the corresponding fresh value.
    """
    source = metric_point.source.lower()
    detail = (metric_point.source_detail or "").strip()
    metrics = fresh.get("metrics") or {}

    # metrics.json path: e.g. 'valuation.pb' → fresh['metrics']['valuation']['pb']
    if "metrics.json" in source or detail.startswith(("valuation.", "profitability.", "growth.", "cashflow.", "latest_vitals.")):
        if "=" in detail:
            detail = detail.split("=", 1)[0].strip()
        path = detail.split(".") if "." in detail else detail.split(":")
        if path:
            val: Any = metrics
            try:
                for key in path:
                    key = key.strip()
                    if isinstance(val, dict):
                        val = val.get(key)
                    else:
                        val = None
                        break
                if isinstance(val, (int, float)):
                    return float(val)
            except Exception:
                return None

    # Tushare bundle: try common mappings
    if "tushare" in source:
        bundle = fresh.get("bundle", {})
        # detail like 'income.revenue, end_date=20240101'
        if "." in detail:
            table, rest = detail.split(".", 1)
            field_name = rest.split(",")[0].strip()
            df = bundle.get(table)
            if df is not None and not df.empty and field_name in df.columns:
                # use latest row (sorted by end_date or ann_date desc)
                if "end_date" in df.columns:
                    df_sorted = df.sort_values("end_date", ascending=False)
                else:
                    df_sorted = df
                try:
                    v = df_sorted.iloc[0][field_name]
                    return float(v) if v is not None and str(v) != "nan" else None
                except Exception:
                    return None
        # common shortcuts
        if "daily_basic" in detail or detail == "daily_basic":
            df = bundle.get("daily_basic")
            if df is not None and not df.empty and "pb" in df.columns:
                return float(df.sort_values("trade_date", ascending=False).iloc[0]["pb"])

    # No mapping found
    return None


def _compute_changes(
    baseline: list[MetricPoint],
    fresh: dict[str, Any],
    threshold: float = DEFAULT_CHANGE_THRESHOLD,
) -> tuple[list[ChangeRecord], int]:
    """Compare each baseline metric against fresh data. Return (material_changes, stable_count)."""
    material: list[ChangeRecord] = []
    stable_count = 0

    for mp in baseline:
        if mp.value is None:
            continue  # can't compare without baseline value
        fresh_v = _value_from_fresh(mp, fresh)
        if fresh_v is None:
            continue  # no corresponding fresh data
        base_v = mp.value
        if base_v == 0:
            change = None if fresh_v == 0 else float("inf")
        else:
            change = (fresh_v - base_v) / abs(base_v)

        record = ChangeRecord(
            metric=(mp.source_detail or mp.source),
            baseline_value=base_v,
            fresh_value=fresh_v,
            change_pct=change,
            unit=mp.unit,
            source=mp.source,
            source_detail=mp.source_detail,
            baseline_context=mp.context[:150],
        )

        if change is not None and abs(change) >= threshold:
            material.append(record)
        else:
            stable_count += 1

    return material, stable_count


# ---------- Insight falsification checker ----------

def _check_insights(
    insights: list[InsightPoint],
    fresh: dict[str, Any],
) -> list[InsightCheck]:
    """For each insight, inspect the falsification condition against fresh data.

    NOTE: We can't fully automate all falsification checks (they're natural language),
    but we can flag ones where the condition contains specific numeric thresholds.
    """
    import re
    checks: list[InsightCheck] = []

    for ins in insights:
        fal = ins.falsification or ""
        if not fal:
            continue

        # Try to find numeric thresholds like "< 2000 万" or "> 55%"
        threshold_match = re.search(r"([<>≥≤]=?)\s*([-+]?\d[\d,.]*)\s*(万|亿|%|元|x|倍)?", fal)

        triggered = "⚠️ 数据不足"
        evidence = "（自动化检查仅能识别简单数值阈值；需人工复核）"

        if threshold_match:
            op = threshold_match.group(1)
            thr = float(threshold_match.group(2).replace(",", ""))
            unit = threshold_match.group(3)
            # Try to find a related metric in fresh data by keyword from insight title/hypothesis
            # This is heuristic — flags "potentially relevant" rather than conclusive
            evidence = f"数值阈值: {op} {thr} {unit or ''}（需对照最新 {ins.title} 相关数据人工确认）"

        checks.append(InsightCheck(
            insight_index=ins.index,
            title=ins.title[:80],
            level=ins.level,
            falsification=fal[:200],
            triggered=triggered,
            evidence=evidence,
        ))

    return checks


# ---------- Summary generation ----------

def _format_summary(result: MonitorResult) -> str:
    """Generate the markdown brief."""
    lines = [
        f"# 量化监控简报：{result.company}",
        "",
        f"**监控日期**: {result.monitor_date}",
        f"**基线报告**: {Path(result.baseline_report).name}"
        + (f"（基线日期 {result.baseline_date}，{result.days_since_baseline} 天前）" if result.baseline_date else ""),
        f"**股票代码**: {result.ticker}",
        f"**市场**: {result.market}",
        "",
        "---",
        "",
        f"## §1 重大变化（变化 ≥ {int(DEFAULT_CHANGE_THRESHOLD * 100)}% 的指标，共 {len(result.material_changes)} 项）",
        "",
    ]
    if result.material_changes:
        lines.append("| 指标 | 基线值 | 最新值 | 变化 | 单位 | 基线上下文 |")
        lines.append("|------|-------:|-------:|:----:|------|-----------|")
        for c in result.material_changes[:30]:
            bv = f"{c.baseline_value:,.2f}" if c.baseline_value is not None else "—"
            fv = f"{c.fresh_value:,.2f}" if c.fresh_value is not None else "—"
            ch = f"{c.change_pct:+.1%}" if c.change_pct is not None else "—"
            lines.append(f"| {c.metric} | {bv} | {fv} | {ch} | {c.unit or ''} | {c.baseline_context[:80]} |")
    else:
        lines.append("*（无重大变化）*")
    lines += [
        "",
        f"**稳定指标数**（变化 < {int(DEFAULT_CHANGE_THRESHOLD * 100)}%）: {result.stable_metrics_count}",
        "",
        "---",
        "",
        "## §2 Phase 5 洞察证伪检查",
        "",
    ]
    if result.insight_checks:
        lines.append("| # | 洞察标题 | Level | 证伪条件 | 状态 | 证据 |")
        lines.append("|---|---------|:---:|---------|:---:|------|")
        for ic in result.insight_checks:
            lines.append(f"| #{ic.insight_index} | {ic.title} | {ic.level} | {ic.falsification[:100]} | {ic.triggered} | {ic.evidence[:100]} |")
    else:
        lines.append("*（未找到 Phase 5 洞察文件或无可解析洞察）*")

    lines += [
        "",
        "---",
        "",
        "## §3 下次监控触发",
        "",
    ]
    if result.next_disclosure_date:
        days = _days_between(result.monitor_date, result.next_disclosure_date)
        lines.append(f"- **预约披露日**: {result.next_disclosure_date}（{days or '?'} 天后）")
    else:
        lines.append("- **预约披露日**: 未知（`disclosure_date` API 未返回有效日期）")
    lines.append("- 建议手动触发: `/company-analysis-monitor " + result.company + "`")

    lines += [
        "",
        "---",
        "",
        f"## §4 综合结论: **{result.conclusion}**",
        "",
    ]
    if result.conclusion == "重大修订":
        lines.append("⚠️ 多项关键指标变化幅度超过 10%，或 ≥2 条 Phase 5 洞察触发证伪。**建议立即重跑完整分析**。")
    elif result.conclusion == "建议复评":
        lines.append("🟡 检测到部分重大变化或 1 条洞察触发证伪。**建议人工复核相关章节**。")
    else:
        lines.append("✅ 所有指标稳定，无洞察证伪触发。**维持现有投资结论**。")

    return "\n".join(lines)


# ---------- Orchestrator ----------

class Monitor:
    def __init__(self, company: str, ticker: str, market: str,
                 change_threshold: float = DEFAULT_CHANGE_THRESHOLD):
        self.company = company
        self.ticker = ticker
        self.market = market
        self.change_threshold = change_threshold

    def run(self, baseline_report: Path | None = None) -> MonitorResult:
        """Run the full monitor pipeline. Returns MonitorResult."""
        company_dir = config.output_dir(self.company)

        # 1. Find baseline report
        if baseline_report is None:
            baseline_report = _find_latest_report(company_dir)
        if baseline_report is None:
            raise FileNotFoundError(
                f"No analysis report found in {company_dir}. "
                f"Run /company-analysis {self.company} first."
            )
        baseline_date = _extract_report_date(baseline_report)
        today = dt.date.today().strftime("%Y-%m-%d")
        days_since = _days_between(baseline_date, today) if baseline_date else None

        # 2. Parse baseline metrics
        baseline_metrics = parse_report(baseline_report)

        # 3. Parse Phase 5 insights (falsification conditions)
        phase5_file = _find_phase5_file(company_dir)
        insights = extract_insights(phase5_file) if phase5_file else []

        # 4. Fetch fresh data
        fresh = _fetch_fresh_metrics(self.ticker, self.market)

        # 5. Compare
        material_changes, stable_count = _compute_changes(
            baseline_metrics, fresh, self.change_threshold
        )

        # 6. Check insights
        insight_checks = _check_insights(insights, fresh)

        # 7. Determine conclusion
        triggered_count = sum(1 for ic in insight_checks if ic.triggered == "❌ 已触发")
        if len(material_changes) >= 5 or triggered_count >= 2:
            conclusion = "重大修订"
        elif len(material_changes) >= 1 or triggered_count >= 1:
            conclusion = "建议复评"
        else:
            conclusion = "维持"

        result = MonitorResult(
            company=self.company,
            ticker=self.ticker,
            market=self.market,
            monitor_date=today,
            baseline_report=str(baseline_report),
            baseline_date=baseline_date,
            days_since_baseline=days_since,
            material_changes=material_changes,
            stable_metrics_count=stable_count,
            insight_checks=insight_checks,
            next_disclosure_date=fresh.get("next_disclosure"),
            conclusion=conclusion,
            summary_markdown="",  # filled below
        )
        result.summary_markdown = _format_summary(result)

        # 8. Save to output/{company}/monitor_{date}.md
        out_path = company_dir / f"monitor_{self.company}_{today}.md"
        out_path.write_text(result.summary_markdown, encoding="utf-8")

        return result


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="Run quantitative monitor for a company.")
    ap.add_argument("company", help="Company name (Chinese or English, matches output/ folder)")
    ap.add_argument("--ticker", required=True, help="Stock code (e.g. 002862.SZ, AAPL, 0700.HK)")
    ap.add_argument("--market", default="a", choices=["a", "us", "hk"], help="Market code")
    ap.add_argument("--threshold", type=float, default=DEFAULT_CHANGE_THRESHOLD,
                    help=f"Material change threshold (default {DEFAULT_CHANGE_THRESHOLD})")
    ap.add_argument("--baseline", default=None, help="Explicit baseline report path (default: latest)")
    args = ap.parse_args()

    m = Monitor(args.company, args.ticker, args.market, change_threshold=args.threshold)
    baseline = Path(args.baseline) if args.baseline else None
    result = m.run(baseline_report=baseline)

    print(result.summary_markdown)
    print(f"\n(Saved to: output/{args.company}/monitor_{args.company}_{result.monitor_date}.md)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
