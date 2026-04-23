"""Parse historical analysis reports to extract tagged metrics as baseline.

The analysis reports (v3+) have inline source tags like:
  - "营收 4.37 亿 [Tushare:income.revenue, end_date=20241231]"
  - "PB 7.26x [Tushare:daily_basic]"
  - "Q3 亏损 -5,879 万元 [PDF:q3_2025, P.2]"

This module extracts those anchor points so Phase 7 monitor can compare them
against fresh Tushare/PDF data.

Also extracts Phase 5 insight falsification conditions.

Usage:
    from scripts.report_parser import parse_report, extract_insights
    baseline = parse_report(Path("output/实丰文化/实丰文化-analysis-2026-04-21.md"))
    insights = extract_insights(Path("output/实丰文化/phase5-variant-perception.md"))
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


# ---------- Tag pattern ----------
# Matches [Tushare:income.revenue] / [Tushare:daily_basic] / [PDF:q3_2025, P.4] /
# [metrics.json:valuation.pb] etc.
TAG_PATTERN = re.compile(
    r"\[(?P<source>Tushare|PDF|metrics\.json|yfinance|WebSearch|Phase\s*5\s*补查)"
    r"(?::\s*(?P<detail>[^\]]*?))?\]",
    re.IGNORECASE,
)

# Number + unit pattern (Chinese units support): 4.37 亿 / -5,879 万元 / 7.26x / 38.27% / 17.27 元
# Captures sign, magnitude, and unit
NUMBER_WITH_UNIT = re.compile(
    r"(?P<value>[-+]?\d[\d,]*\.?\d*)"
    r"\s*"
    r"(?P<unit>亿元?|万元?|千元?|元|%|x|倍|pp|bp|美元|港元|港币)?"
)


@dataclass
class MetricPoint:
    """A single extracted metric with its source tag."""
    raw_text: str
    value: float | None
    unit: str | None
    source: str  # Tushare / PDF / metrics.json / ...
    source_detail: str | None
    context: str  # surrounding text (200 chars)
    line_number: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InsightPoint:
    """A Phase 5 insight with its falsification condition."""
    index: int  # "#1", "#2" ...
    title: str
    hypothesis: str
    level: str  # A / B / C
    falsification: str  # 证伪条件
    time_window: str  # 6M / 1Y / 3Y
    confidence: str  # 高 / 中 / 低
    math_derivation: str  # the 数学推导 section raw text

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------- Number parsing helpers ----------

_UNIT_SCALE = {
    "亿": 1e8, "亿元": 1e8,
    "万": 1e4, "万元": 1e4,
    "千": 1e3, "千元": 1e3,
    "元": 1.0,
    "美元": 1.0, "港元": 1.0, "港币": 1.0,
    "%": 0.01,
    "x": 1.0, "倍": 1.0,
    "pp": 0.01, "bp": 0.0001,
}


def _parse_value(value_str: str, unit: str | None) -> float | None:
    """Parse '4.37 亿' → 437_000_000.0 ; '7.26x' → 7.26 ; '38.27%' → 0.3827"""
    if not value_str:
        return None
    clean = value_str.replace(",", "")
    try:
        v = float(clean)
    except ValueError:
        return None
    if unit and unit in _UNIT_SCALE:
        v *= _UNIT_SCALE[unit]
    return v


# ---------- Main parser ----------

def parse_report(report_path: Path, context_chars: int = 100) -> list[MetricPoint]:
    """Scan a markdown report for tagged metric points.

    Strategy:
    1. Split text by lines
    2. For each line, find all [Source:detail] tags
    3. For each tag, look backwards in the same line for the nearest number+unit
       (e.g. "营收 4.37 亿 [Tushare:income.revenue]" → extract (4.37, "亿"))
    4. Build MetricPoint

    Returns a list of MetricPoints in document order.
    """
    text = Path(report_path).read_text(encoding="utf-8")
    lines = text.splitlines()

    points: list[MetricPoint] = []
    for line_no, line in enumerate(lines, 1):
        for tag_match in TAG_PATTERN.finditer(line):
            source = tag_match.group("source")
            detail = (tag_match.group("detail") or "").strip() or None

            # Look backwards from tag position for the nearest number+unit
            prefix = line[: tag_match.start()]
            # Find the last number+unit occurrence in prefix
            best = None
            for m in NUMBER_WITH_UNIT.finditer(prefix):
                best = m
            if best:
                value_str = best.group("value")
                unit = best.group("unit")
                value = _parse_value(value_str, unit)
            else:
                value_str = unit = None
                value = None

            # Build context
            start_ctx = max(0, tag_match.start() - context_chars)
            end_ctx = min(len(line), tag_match.end() + context_chars)
            context = line[start_ctx:end_ctx].strip()

            points.append(MetricPoint(
                raw_text=line[best.start():tag_match.end()] if best else line[:tag_match.end()],
                value=value,
                unit=unit,
                source=source,
                source_detail=detail,
                context=context,
                line_number=line_no,
            ))

    return points


# ---------- Phase 5 insight extractor ----------

# Phase 5 insight card structure — supports BOTH v3 (13 字段) and v4.1 (9 字段)
#
# v3/v4:
#   ### 洞察 #N: {title}
#   **假设**: ...
#   **数学推导**: ...（多行）
#   **证据等级**: A/B/C
#   **证伪条件**: ...
#   **置信度**: 高/中/低
#   **时间窗**: 6M/1Y/3Y
#
# v4.1 合并字段: **信号强度**: `Level A / 高置信 / 1Y`
#   or: **信号强度**: Level A | 高 | 6M

INSIGHT_HEADER = re.compile(r"^#{2,4}\s+洞察\s*#?(\d+)[:：]?\s*(.+?)\s*(?:【.*?】)?\s*$")
# These field regexes are robust to bold/italic/space variations
FIELD_HYPOTHESIS = re.compile(r"\*\*(?:1\.\s*)?假设\*\*[:：]?\s*(.+?)$")
FIELD_LEVEL = re.compile(r"\*\*证据等级\*\*[^A-Ca-c]*[:：]?[^A-Ca-c]*([A-Ca-c])")
FIELD_FALSIFICATION = re.compile(r"\*\*(?:\d\.\s*)?证伪条件\*\*[:：]?\s*(.+?)$")
FIELD_CONFIDENCE = re.compile(r"\*\*置信度\*\*[:：]?\s*([^\s|\n]+)")
FIELD_TIME_WINDOW = re.compile(r"\*\*时间窗(?:口)?\*\*[:：]?\s*([^\s|\n]+)")

# v4.1 merged field: 信号强度 — parse Level + confidence + time window from single line
# Matches: "**信号强度**: Level A / 高 / 1Y" or "**9. 信号强度**: `Level B / 中置信 / 6M`"
FIELD_SIGNAL_STRENGTH = re.compile(r"\*\*(?:\d\.\s*)?信号强度\*\*[:：]?\s*`?([^`\n]+)`?")
# Subpattern: inside the 信号强度 value, extract Level (A/B/C), confidence (高/中/低), window (6M/1Y/3Y)
_SIG_LEVEL = re.compile(r"Level\s*([ABCabc])", re.IGNORECASE)
_SIG_CONFIDENCE = re.compile(r"(高|中|低)\s*置信|置信度?\s*[:：]?\s*(高|中|低)|(?:^|[/\s|])(高|中|低)(?:[/\s|]|$)")
_SIG_WINDOW = re.compile(r"\b(\d+[MmYy])\b|\b(\d+\s*个?\s*月)\b|\b(\d+\s*年)\b")


def extract_insights(phase5_path: Path) -> list[InsightPoint]:
    """Extract Phase 5 insight cards with falsification conditions.

    Returns empty list if file doesn't exist.
    """
    if not phase5_path.exists():
        return []
    text = phase5_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    insights: list[InsightPoint] = []
    current: dict[str, Any] | None = None
    in_math_block = False
    math_buffer: list[str] = []

    def flush():
        nonlocal current, math_buffer
        if current and current.get("title"):
            if math_buffer:
                current["math_derivation"] = "\n".join(math_buffer).strip()
            insights.append(InsightPoint(
                index=current.get("index", 0),
                title=current.get("title", ""),
                hypothesis=current.get("hypothesis", ""),
                level=current.get("level", "?"),
                falsification=current.get("falsification", ""),
                time_window=current.get("time_window", ""),
                confidence=current.get("confidence", ""),
                math_derivation=current.get("math_derivation", ""),
            ))
        current = None
        math_buffer = []

    for line in lines:
        header = INSIGHT_HEADER.match(line)
        if header:
            flush()
            current = {"index": int(header.group(1)), "title": header.group(2).strip()}
            in_math_block = False
            math_buffer = []
            continue

        if current is None:
            continue

        # Check for math_derivation start (flexible naming)
        if re.search(r"\*\*数学推导\*\*", line):
            in_math_block = True
            math_buffer.append(line)
            continue

        # End math block when we hit another bold field or blank + next field
        if in_math_block:
            if re.search(r"\*\*(证据等级|信号强度|市场共识|变异认知|证伪条件|置信度|支撑证据|信息不对称|验证路径|类型|量化影响)\*\*", line):
                in_math_block = False
                # fall through to other field checks below
            else:
                math_buffer.append(line)
                continue

        # v4.1 merged "信号强度" field: parse Level + confidence + time_window from single line
        m_sig = FIELD_SIGNAL_STRENGTH.search(line)
        if m_sig:
            sig_value = m_sig.group(1).strip()
            m_l = _SIG_LEVEL.search(sig_value)
            if m_l and not current.get("level"):
                current["level"] = m_l.group(1).upper()
            m_c = _SIG_CONFIDENCE.search(sig_value)
            if m_c and not current.get("confidence"):
                current["confidence"] = next(g for g in m_c.groups() if g)
            m_w = _SIG_WINDOW.search(sig_value)
            if m_w and not current.get("time_window"):
                current["time_window"] = next(g for g in m_w.groups() if g)
            continue

        # legacy v3/v4 separate fields (also still supported)
        for fname, regex in [
            ("hypothesis", FIELD_HYPOTHESIS),
            ("falsification", FIELD_FALSIFICATION),
            ("confidence", FIELD_CONFIDENCE),
            ("time_window", FIELD_TIME_WINDOW),
        ]:
            m = regex.search(line)
            if m:
                current[fname] = m.group(1).strip()
                break
        m = FIELD_LEVEL.search(line)
        if m:
            current["level"] = m.group(1).upper()

    flush()
    return insights


# ---------- CLI ----------

if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Parse tagged metrics from an analysis report.")
    ap.add_argument("report_path", help="Path to {company}-analysis-*.md")
    ap.add_argument("--insights", default=None, help="Optional path to phase5-variant-perception.md")
    ap.add_argument("--out", default=None, help="Output JSON path (default: stdout)")
    args = ap.parse_args()

    metrics = parse_report(Path(args.report_path))
    result = {
        "report": str(args.report_path),
        "metric_count": len(metrics),
        "metrics": [m.to_dict() for m in metrics],
    }

    if args.insights:
        insights = extract_insights(Path(args.insights))
        result["insight_count"] = len(insights)
        result["insights"] = [i.to_dict() for i in insights]

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(output)
