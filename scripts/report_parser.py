"""Parse historical analysis reports to extract tagged metrics as baseline.

The analysis reports (v3+) have inline source tags like:
  - "营收 4.37 亿 [Tushare:income.revenue, end_date=20241231]"
  - "PB 7.26x [Tushare:daily_basic]"
  - "Q3 亏损 -5,879 万元 [PDF:q3_2025, P.2]"

This module extracts those anchor points so Phase 7 monitor can compare them
against fresh Tushare/PDF data.

Usage:
    from scripts.report_parser import parse_report
    baseline = parse_report(Path("output/实丰文化/实丰文化-analysis-2026-04-21.md"))
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


# ---------- Tag pattern ----------
# Matches [Tushare:income.revenue] / [Tushare:daily_basic] / [PDF:q3_2025, P.4] /
# [metrics.json:valuation.pb] etc.
TAG_PATTERN = re.compile(
    r"\[(?P<source>Tushare|PDF|metrics\.json|yfinance|WebSearch)"
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


# ---------- CLI ----------

if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Parse tagged metrics from an analysis report.")
    ap.add_argument("report_path", help="Path to {company}-analysis-*.md")
    ap.add_argument("--out", default=None, help="Output JSON path (default: stdout)")
    args = ap.parse_args()

    metrics = parse_report(Path(args.report_path))
    result = {
        "report": str(args.report_path),
        "metric_count": len(metrics),
        "metrics": [m.to_dict() for m in metrics],
    }

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(output)
