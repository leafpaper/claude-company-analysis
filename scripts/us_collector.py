"""US equity collector using yfinance.

Usage:
    from scripts.us_collector import USCollector
    c = USCollector()
    bundle = c.collect_all("AAPL")

CLI:
    python3 -m scripts.us_collector AAPL [--out output/Apple/raw_data/]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from . import config, data_cache


def _normalize_us(code: str) -> str:
    return code.strip().upper()


class USCollector:
    """yfinance-based collector for NYSE/NASDAQ tickers."""

    def __init__(self, rate_limit_sec: float | None = None):
        self._rate = rate_limit_sec or config.YFINANCE_RATE_LIMIT_SEC
        self._last_call = 0.0
        self._tickers: dict[str, Any] = {}

    def _throttle(self):
        elapsed = time.time() - self._last_call
        if elapsed < self._rate:
            time.sleep(self._rate - elapsed)
        self._last_call = time.time()

    def _ticker(self, code: str):
        import yfinance as yf
        code = _normalize_us(code)
        if code not in self._tickers:
            self._tickers[code] = yf.Ticker(code)
        return self._tickers[code]

    def _cached_df(self, key: str, loader) -> pd.DataFrame:
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._throttle()
        df = loader()
        if isinstance(df, pd.DataFrame) and not df.empty:
            df = df.T.reset_index()
            df.rename(columns={"index": "period"}, inplace=True)
        elif df is None:
            df = pd.DataFrame()
        data_cache.put(key, df)
        return df

    # ---- financials ----

    def income_annual(self, code: str) -> pd.DataFrame:
        code = _normalize_us(code)
        return self._cached_df(f"yf_income_ann_{code}", lambda: self._ticker(code).financials)

    def income_quarterly(self, code: str) -> pd.DataFrame:
        code = _normalize_us(code)
        return self._cached_df(f"yf_income_q_{code}", lambda: self._ticker(code).quarterly_financials)

    def balance_annual(self, code: str) -> pd.DataFrame:
        code = _normalize_us(code)
        return self._cached_df(f"yf_balance_ann_{code}", lambda: self._ticker(code).balance_sheet)

    def balance_quarterly(self, code: str) -> pd.DataFrame:
        code = _normalize_us(code)
        return self._cached_df(f"yf_balance_q_{code}", lambda: self._ticker(code).quarterly_balance_sheet)

    def cashflow_annual(self, code: str) -> pd.DataFrame:
        code = _normalize_us(code)
        return self._cached_df(f"yf_cashflow_ann_{code}", lambda: self._ticker(code).cashflow)

    def cashflow_quarterly(self, code: str) -> pd.DataFrame:
        code = _normalize_us(code)
        return self._cached_df(f"yf_cashflow_q_{code}", lambda: self._ticker(code).quarterly_cashflow)

    # ---- metadata ----

    def info(self, code: str) -> pd.DataFrame:
        """Single-row DataFrame with price, market cap, PE, PB, industry, etc."""
        code = _normalize_us(code)
        key = f"yf_info_{code}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._throttle()
        info = self._ticker(code).info or {}
        flat = {}
        for k, v in info.items():
            if isinstance(v, (dict, list, tuple)):
                try:
                    flat[k] = json.dumps(v, ensure_ascii=False)
                except Exception:  # noqa: BLE001
                    flat[k] = str(v)
            else:
                flat[k] = v
        df = pd.DataFrame([flat])
        data_cache.put(key, df)
        return df

    def major_holders(self, code: str) -> pd.DataFrame:
        code = _normalize_us(code)
        key = f"yf_major_holders_{code}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._throttle()
        df = self._ticker(code).major_holders
        if df is None:
            df = pd.DataFrame()
        elif not df.empty:
            df = df.reset_index()
        data_cache.put(key, df)
        return df

    def institutional_holders(self, code: str) -> pd.DataFrame:
        code = _normalize_us(code)
        key = f"yf_inst_holders_{code}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._throttle()
        df = self._ticker(code).institutional_holders
        if df is None:
            df = pd.DataFrame()
        data_cache.put(key, df)
        return df

    def history(self, code: str, period: str = "5y") -> pd.DataFrame:
        code = _normalize_us(code)
        key = f"yf_history_{code}_{period}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._throttle()
        df = self._ticker(code).history(period=period, auto_adjust=False)
        if df is None:
            df = pd.DataFrame()
        elif not df.empty:
            df = df.reset_index()
        data_cache.put(key, df)
        return df

    def dividends(self, code: str) -> pd.DataFrame:
        code = _normalize_us(code)
        key = f"yf_dividends_{code}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._throttle()
        s = self._ticker(code).dividends
        if s is None or s.empty:
            df = pd.DataFrame()
        else:
            df = s.reset_index()
            df.columns = ["date", "dividend"]
        data_cache.put(key, df)
        return df

    def collect_all(self, code: str) -> dict[str, pd.DataFrame]:
        bundle: dict[str, pd.DataFrame] = {}
        bundle["info"] = self.info(code)
        bundle["income_annual"] = self.income_annual(code)
        bundle["income_quarterly"] = self.income_quarterly(code)
        bundle["balance_annual"] = self.balance_annual(code)
        bundle["balance_quarterly"] = self.balance_quarterly(code)
        bundle["cashflow_annual"] = self.cashflow_annual(code)
        bundle["cashflow_quarterly"] = self.cashflow_quarterly(code)
        bundle["major_holders"] = self.major_holders(code)
        bundle["institutional_holders"] = self.institutional_holders(code)
        bundle["history_5y"] = self.history(code, period="5y")
        bundle["dividends"] = self.dividends(code)
        return bundle


def save_bundle(bundle: dict[str, pd.DataFrame], out_dir: Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for key, df in bundle.items():
        path = out_dir / f"{key}.parquet"
        df.to_parquet(path, index=False)
        summary[key] = {"rows": len(df), "cols": len(df.columns), "path": path.name}
    (out_dir / "_manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
    )


def main():
    ap = argparse.ArgumentParser(description="Collect yfinance bundle for a US equity.")
    ap.add_argument("code", help="US ticker (e.g. AAPL)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--name", default=None, help="Display name for output dir")
    args = ap.parse_args()

    code = _normalize_us(args.code)
    c = USCollector()
    print(f"Fetching yfinance bundle for {code}...")
    bundle = c.collect_all(code)

    if args.out:
        out_dir = Path(args.out)
    else:
        name = args.name or code
        out_dir = config.output_dir(name) / "raw_data"

    save_bundle(bundle, out_dir)

    print(f"\nSaved to: {out_dir}")
    for key, df in bundle.items():
        print(f"  {key}: {len(df)} rows × {len(df.columns)} cols")


if __name__ == "__main__":
    main()
