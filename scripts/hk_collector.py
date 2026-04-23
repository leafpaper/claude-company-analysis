"""Hong Kong equity collector — hybrid of Tushare HK endpoints + yfinance fallback.

Strategy:
- Tushare Pro has hk_basic, hk_daily — use these for metadata + price history.
- Tushare's HK financial statement coverage is sparse → use yfinance for financials.
- Dividends, institutional holders → yfinance.

Usage:
    from scripts.hk_collector import HKCollector
    c = HKCollector()
    bundle = c.collect_all("0700.HK")  # Tencent
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import pandas as pd

from . import config, data_cache
from .tushare_collector import TushareCollector, normalize_hk_code
from .us_collector import USCollector


class HKCollector:
    """Hybrid collector: Tushare for metadata/prices, yfinance for financials."""

    def __init__(self):
        self._ts: TushareCollector | None = None
        self._yf = USCollector()

    def _tushare(self) -> TushareCollector:
        if self._ts is None:
            self._ts = TushareCollector()
        return self._ts

    def hk_basic(self, hk_code: str) -> pd.DataFrame:
        """Tushare hk_basic — company profile."""
        ts = self._tushare()
        ts._ensure_pro()
        key = f"tushare_hk_basic_{hk_code}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        df = ts._call(ts._pro.hk_basic, ts_code=hk_code)
        data_cache.put(key, df)
        return df

    def hk_daily(self, hk_code: str, years: int = 3) -> pd.DataFrame:
        """Tushare hk_daily — price history."""
        ts = self._tushare()
        ts._ensure_pro()
        key = f"tushare_hk_daily_{hk_code}_y{years}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        end = dt.date.today()
        start = end - dt.timedelta(days=years * 365)
        df = ts._call(
            ts._pro.hk_daily,
            ts_code=hk_code,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
        )
        data_cache.put(key, df)
        return df

    def collect_all(self, hk_code: str) -> dict[str, pd.DataFrame]:
        hk_code = normalize_hk_code(hk_code)
        bundle: dict[str, pd.DataFrame] = {}

        # --- Tushare for HK metadata + prices (optional, graceful degrade) ---
        try:
            bundle["hk_basic"] = self.hk_basic(hk_code)
        except Exception as e:  # noqa: BLE001
            print(f"[HK] hk_basic failed: {e}", file=__import__("sys").stderr)
            bundle["hk_basic"] = pd.DataFrame()
        try:
            bundle["hk_daily"] = self.hk_daily(hk_code)
        except Exception as e:  # noqa: BLE001
            print(f"[HK] hk_daily failed: {e}", file=__import__("sys").stderr)
            bundle["hk_daily"] = pd.DataFrame()

        # --- yfinance for financials + holders + dividends ---
        yf_bundle = self._yf.collect_all(hk_code)
        bundle.update({f"yf_{k}": v for k, v in yf_bundle.items()})

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
    ap = argparse.ArgumentParser(description="Collect hybrid bundle for a HK equity.")
    ap.add_argument("code", help="HK ticker (e.g. 0700 or 0700.HK)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--name", default=None)
    args = ap.parse_args()

    hk_code = normalize_hk_code(args.code)
    c = HKCollector()
    print(f"Fetching HK bundle for {hk_code}...")
    bundle = c.collect_all(hk_code)

    if args.out:
        out_dir = Path(args.out)
    else:
        name = args.name
        if not name and not bundle.get("hk_basic", pd.DataFrame()).empty:
            name = bundle["hk_basic"]["name"].iloc[0] if "name" in bundle["hk_basic"].columns else hk_code
        if not name:
            name = hk_code.replace(".", "_")
        out_dir = config.output_dir(name) / "raw_data"

    save_bundle(bundle, out_dir)

    print(f"\nSaved to: {out_dir}")
    for key, df in bundle.items():
        print(f"  {key}: {len(df)} rows × {len(df.columns)} cols")


if __name__ == "__main__":
    main()
