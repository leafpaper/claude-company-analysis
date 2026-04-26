"""免费 K 线 fallback (新浪 K 线 JSON,无需 Tushare token).

设计目标:当 Tushare Pro `daily` 接口因积分不足或代码异常返回空 DataFrame 时,
作为兜底自动降级到本模块的免费数据源,把字段名 / 单位适配到 Pro 风格,
让上层(`tushare_collector.daily` / `derived_metrics` / `technical_analysis`)无感知。

核心来源:
- 新浪历史 K 线 JSON
  https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData
  支持北交所 (bj 前缀) / 沪市 (sh) / 深市 (sz),无需 token,实测 datalen 最高 3000 (12+ 年历史)。

字段 / 单位差异(已在适配层处理):
  - 新浪 `volume` 单位:股 → Pro `vol` 单位:手 (÷ 100)
  - 新浪 不返还 amount → 用 close × volume / 1000 估算 (千元)
  - 新浪 不返还 pre_close / change / pct_chg → 用 shift(1) 计算
"""
from __future__ import annotations

import json
import sys
from typing import Optional

import pandas as pd
import requests


_SINA_KLINE_URL = (
    "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "CN_MarketData.getKLineData"
)
_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://finance.sina.com.cn/",
}
_TIMEOUT_SEC = 10


def _ts_code_to_sina_symbol(ts_code: str) -> str:
    """`920522.BJ` → `bj920522`; `600519.SH` → `sh600519`; `000001.SZ` → `sz000001`."""
    if "." not in ts_code:
        raise ValueError(f"ts_code missing exchange suffix: {ts_code!r}")
    code, suf = ts_code.split(".", 1)
    suf = suf.upper()
    prefix = {"SH": "sh", "SZ": "sz", "BJ": "bj"}.get(suf)
    if not prefix:
        raise ValueError(f"unsupported exchange in ts_code: {ts_code!r}")
    return f"{prefix}{code}"


def get_daily_history_legacy(
    ts_code: str,
    datalen: int = 1500,
) -> pd.DataFrame:
    """从新浪免费 K 线 API 拉历史日线,适配到 Tushare Pro `daily` 字段名 / 单位.

    Args:
        ts_code: Pro 风格代码,如 `920522.BJ` / `600519.SH` / `000001.SZ`
        datalen: 拉取最近 N 个交易日 (实测最高 3000 ≈ 12 年). 默认 1500 ≈ 6 年,够 Phase 1 使用.

    Returns:
        DataFrame with columns matching Pro `daily`:
          ts_code, trade_date (YYYYMMDD str), open, high, low, close,
          pre_close, change, pct_chg, vol, amount
        若 API 失败 / 返回空,返回空 DataFrame.
    """
    try:
        sym = _ts_code_to_sina_symbol(ts_code)
    except ValueError as e:
        sys.stderr.write(f"[legacy_quote] {e}\n")
        return pd.DataFrame()

    url = f"{_SINA_KLINE_URL}?symbol={sym}&scale=240&ma=no&datalen={datalen}"
    try:
        r = requests.get(url, timeout=_TIMEOUT_SEC, headers=_HEADERS)
        r.raise_for_status()
        rows = json.loads(r.text)
    except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
        sys.stderr.write(f"[legacy_quote] sina K-line fetch failed for {ts_code}: {e}\n")
        return pd.DataFrame()

    if not rows or not isinstance(rows, list):
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    expected = {"day", "open", "high", "low", "close", "volume"}
    if not expected.issubset(df.columns):
        sys.stderr.write(
            f"[legacy_quote] sina kline schema mismatch for {ts_code}: got {list(df.columns)}\n"
        )
        return pd.DataFrame()

    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"]).copy()
    df = df.sort_values("day").reset_index(drop=True)

    df["ts_code"] = ts_code
    df["trade_date"] = df["day"].str.replace("-", "", regex=False)
    df["pre_close"] = df["close"].shift(1)
    df["change"] = (df["close"] - df["pre_close"]).round(4)
    df["pct_chg"] = ((df["change"] / df["pre_close"]) * 100).round(4)
    df["vol"] = (df["volume"] / 100).round(2)
    df["amount"] = (df["volume"] * df["close"] / 1000).round(3)

    return df[
        [
            "ts_code", "trade_date",
            "open", "high", "low", "close",
            "pre_close", "change", "pct_chg",
            "vol", "amount",
        ]
    ].reset_index(drop=True)


def filter_by_date_range(
    df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
) -> pd.DataFrame:
    """按 YYYYMMDD 字符串区间过滤 Sina kline DataFrame (供 tushare_collector.daily 复用)."""
    if df.empty:
        return df
    out = df
    if start_date:
        out = out[out["trade_date"] >= str(start_date).replace("-", "")]
    if end_date:
        out = out[out["trade_date"] <= str(end_date).replace("-", "")]
    return out.reset_index(drop=True)


if __name__ == "__main__":
    # CLI smoke test
    import argparse
    ap = argparse.ArgumentParser(description="Sina K 线 legacy fallback smoke test")
    ap.add_argument("ts_code", help="如 920522.BJ / 600519.SH / 000001.SZ")
    ap.add_argument("--datalen", type=int, default=300)
    args = ap.parse_args()
    out = get_daily_history_legacy(args.ts_code, datalen=args.datalen)
    print(f"rows: {len(out)}")
    if len(out) > 0:
        print(f"columns: {list(out.columns)}")
        print(out.tail(5).to_string())
