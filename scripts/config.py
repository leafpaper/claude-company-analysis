"""Central configuration: token, cache paths, rate limits, output layout."""
from __future__ import annotations

import os
from pathlib import Path

# ---------- Tushare ----------
TUSHARE_TOKEN: str | None = os.environ.get("TUSHARE_TOKEN")

# Token 不在环境里不立即抛错 —— us_collector / pdf_reader / derived_metrics 不需要 token
# 调用 A 股/港股 collector 时才显式检查（见 tushare_collector.require_token()）

# ---------- 缓存 ----------
_DEFAULT_CACHE = Path.home() / ".claude" / "plugins" / "company-analysis" / ".cache"
CACHE_DIR: Path = Path(os.environ.get("COMPANY_ANALYSIS_CACHE", _DEFAULT_CACHE)).expanduser()
CACHE_TTL_DAYS: int = int(os.environ.get("COMPANY_ANALYSIS_CACHE_TTL", "7"))

# ---------- 速率限制 ----------
# Tushare 免费账号默认 500 次/分钟，VIP 2000+；统一保守 120/分钟（每 500ms 一次）
TUSHARE_RATE_LIMIT_SEC: float = 0.5
TUSHARE_MAX_RETRIES: int = 5
TUSHARE_RETRY_BACKOFF: float = 1.5  # 指数退避倍数

# yfinance 没有官方速率限制，但按经验 300ms 一次较安全
YFINANCE_RATE_LIMIT_SEC: float = 0.3

# ---------- 输出目录 ----------
SKILL_ROOT: Path = Path(__file__).resolve().parent.parent  # skills/company-analysis/
PLUGIN_ROOT: Path = SKILL_ROOT.parent.parent               # plugins/company-analysis/

# v4: 历史 output 在 plugin 根目录下（因为 SKILL.md 曾说"不保存到 skill 目录"），
# 所以 OUTPUT_ROOT 优先用 plugin 根的 output，若不存在则用 skill 根的 output（新安装场景）
if (PLUGIN_ROOT / "output").exists():
    OUTPUT_ROOT: Path = PLUGIN_ROOT / "output"
else:
    OUTPUT_ROOT = SKILL_ROOT / "output"


def output_dir(company: str) -> Path:
    """Get (and create) the output dir for a given company.

    智能选择：若已存在于 plugin 根的 output/ 下则用那个；否则在 SKILL_ROOT/output/ 下创建。
    """
    for root in (PLUGIN_ROOT / "output", SKILL_ROOT / "output"):
        candidate = root / company
        if candidate.exists():
            (candidate / "raw_data").mkdir(exist_ok=True)
            (candidate / "raw_data" / "pdfs").mkdir(exist_ok=True)
            return candidate
    # 新公司：默认建在 plugin 根（与历史一致）
    p = PLUGIN_ROOT / "output" / company
    p.mkdir(parents=True, exist_ok=True)
    (p / "raw_data").mkdir(exist_ok=True)
    (p / "raw_data" / "pdfs").mkdir(exist_ok=True)
    return p


def cache_path(key: str) -> Path:
    """Namespaced cache path for a given logical key (e.g. 'tushare_income_600519.SH_2024')."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = key.replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"{safe}.parquet"
