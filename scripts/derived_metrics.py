"""Compute derived financial metrics from raw Tushare/yfinance bundles.

Produces a JSON-serializable dict with:
  - growth:       CAGR (revenue, net profit, FCF) over 3/5 years
  - profitability: ROE (5y trend), ROA, gross margin, net margin
  - valuation:   PE, PB, PS, EV/EBITDA, FCF yield, dividend yield
  - capital:     asset-liability ratio, current ratio, quick ratio
  - cashflow:    FCF, Owner Earnings (Buffett), 穿透回报率 (Turtle)
  - segments:    分业务收入/毛利（若 fina_mainbz 有数据）

Usage:
    from scripts.derived_metrics import compute_a_share, compute_us
    metrics = compute_a_share(bundle)  # bundle = TushareCollector.collect_all()
    json.dump(metrics, file)

CLI:
    python3 -m scripts.derived_metrics output/实丰文化/raw_data/
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

# ============================================================================
# Helpers
# ============================================================================


def _safe_float(x) -> float | None:
    """Convert to float, return None on NaN/None/Error."""
    try:
        if x is None:
            return None
        if isinstance(x, float) and math.isnan(x):
            return None
        v = float(x)
        if math.isnan(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def _cagr(start: float | None, end: float | None, years: int) -> float | None:
    """Compound Annual Growth Rate. Returns None if inputs invalid."""
    start = _safe_float(start)
    end = _safe_float(end)
    if start is None or end is None or years <= 0:
        return None
    if start <= 0 or end <= 0:
        # CAGR undefined for negative/zero values
        return None
    try:
        return (end / start) ** (1 / years) - 1
    except (ValueError, ZeroDivisionError):
        return None


def _pct_change(start: float | None, end: float | None) -> float | None:
    start = _safe_float(start)
    end = _safe_float(end)
    if start is None or end is None or start == 0:
        return None
    return (end - start) / abs(start)


def _latest_annual(df: pd.DataFrame, end_date_col: str = "end_date") -> pd.DataFrame:
    """Filter income/balance/cashflow to annual (end_date ending 1231), sorted asc by year."""
    if df is None or df.empty or end_date_col not in df.columns:
        return pd.DataFrame()
    # end_date like '20241231'
    mask = df[end_date_col].astype(str).str.endswith("1231")
    annual = df.loc[mask].copy()
    annual["_year"] = annual[end_date_col].astype(str).str[:4].astype(int)
    annual = annual.sort_values("_year").drop_duplicates(subset="_year", keep="last")
    return annual


def _latest_quarter(df: pd.DataFrame, end_date_col: str = "end_date") -> pd.DataFrame | None:
    """Return the single row for the most recent reporting period."""
    if df is None or df.empty or end_date_col not in df.columns:
        return None
    df = df.copy()
    df["_sort"] = df[end_date_col].astype(str)
    return df.sort_values("_sort", ascending=False).iloc[:1]


# ============================================================================
# A-share metrics (Tushare)
# ============================================================================


def compute_a_share(bundle: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Compute metrics for an A-share given a Tushare bundle."""
    inc = _latest_annual(bundle.get("income", pd.DataFrame()))
    bs = _latest_annual(bundle.get("balancesheet", pd.DataFrame()))
    cf = _latest_annual(bundle.get("cashflow", pd.DataFrame()))
    fi = _latest_annual(bundle.get("fina_indicator", pd.DataFrame()))
    daily_basic = bundle.get("daily_basic", pd.DataFrame())
    daily = bundle.get("daily", pd.DataFrame())
    mainbz = bundle.get("fina_mainbz", pd.DataFrame())
    latest_q_inc = _latest_quarter(bundle.get("income", pd.DataFrame()))
    latest_q_cf = _latest_quarter(bundle.get("cashflow", pd.DataFrame()))

    out: dict[str, Any] = {}

    # ---- growth (CAGR from oldest annual to latest annual) ----
    growth = {}
    if not inc.empty:
        years_span = len(inc)
        for n in (3, 5):
            if years_span > n:
                old = inc.iloc[-(n + 1)]  # n+1 years ago
                new = inc.iloc[-1]
                growth[f"revenue_cagr_{n}y"] = _cagr(
                    old.get("revenue"), new.get("revenue"), n
                )
                growth[f"net_income_cagr_{n}y"] = _cagr(
                    old.get("n_income_attr_p"), new.get("n_income_attr_p"), n
                )
        # latest YoY
        if years_span >= 2:
            growth["revenue_yoy_latest"] = _pct_change(
                inc.iloc[-2].get("revenue"), inc.iloc[-1].get("revenue")
            )
            growth["net_income_yoy_latest"] = _pct_change(
                inc.iloc[-2].get("n_income_attr_p"), inc.iloc[-1].get("n_income_attr_p")
            )
    out["growth"] = growth

    # ---- profitability (from fina_indicator where available) ----
    prof = {}
    if not fi.empty:
        latest_fi = fi.iloc[-1]
        for field, key in [
            ("roe", "roe_latest"),
            ("roa", "roa_latest"),
            ("grossprofit_margin", "gross_margin_latest"),
            ("netprofit_margin", "net_margin_latest"),
            ("debt_to_assets", "debt_to_assets"),
            ("current_ratio", "current_ratio"),
            ("quick_ratio", "quick_ratio"),
            ("eps", "eps_latest"),
        ]:
            v = _safe_float(latest_fi.get(field))
            if v is not None:
                prof[key] = v
        # 5-year ROE trend
        if "roe" in fi.columns and len(fi) >= 3:
            prof["roe_trend"] = {
                int(row["_year"]): _safe_float(row["roe"])
                for _, row in fi.iterrows()
            }
    # fallback: compute from income if fina_indicator empty
    if not prof and not inc.empty:
        latest_inc = inc.iloc[-1]
        rev = _safe_float(latest_inc.get("revenue"))
        ni = _safe_float(latest_inc.get("n_income_attr_p"))
        oper_cost = _safe_float(latest_inc.get("oper_cost"))
        if rev and rev > 0:
            if ni is not None:
                prof["net_margin_latest"] = ni / rev
            if oper_cost is not None:
                prof["gross_margin_latest"] = (rev - oper_cost) / rev
    out["profitability"] = prof

    # ---- valuation (from daily_basic snapshot) ----
    val = {}
    if not daily_basic.empty:
        latest = daily_basic.sort_values("trade_date", ascending=False).iloc[0]
        for field, key in [
            ("pe", "pe"), ("pe_ttm", "pe_ttm"),
            ("pb", "pb"), ("ps", "ps"), ("ps_ttm", "ps_ttm"),
            ("dv_ratio", "dividend_yield"),
            ("total_mv", "market_cap_wanyuan"),  # 万元
            ("circ_mv", "circ_market_cap_wanyuan"),
            ("total_share", "total_share_wanshou"),  # 万股
        ]:
            v = _safe_float(latest.get(field))
            if v is not None:
                val[key] = v
        val["snapshot_date"] = str(latest.get("trade_date"))
    # latest close price
    if not daily.empty:
        latest_day = daily.sort_values("trade_date", ascending=False).iloc[0]
        val["latest_close"] = _safe_float(latest_day.get("close"))
        val["latest_date"] = str(latest_day.get("trade_date"))
    out["valuation"] = val

    # ---- cashflow / Owner Earnings ----
    cashflow = {}
    if not cf.empty:
        latest_cf = cf.iloc[-1]
        ocf = _safe_float(latest_cf.get("n_cashflow_act"))  # 经营现金流净额
        capex = _safe_float(latest_cf.get("c_pay_acq_const_fiolta"))  # 购建固定资产、无形资产和其他长期资产支付
        dep = _safe_float(latest_cf.get("depr_fa_coga_dpba"))  # 折旧
        amort = _safe_float(latest_cf.get("amort_intang_assets"))  # 摊销
        ni_cf = _safe_float(latest_cf.get("net_profit"))

        cashflow["operating_cashflow_latest"] = ocf
        cashflow["capex_latest"] = capex
        cashflow["depreciation_latest"] = dep
        cashflow["amortization_latest"] = amort

        # FCF = OCF - Capex
        if ocf is not None and capex is not None:
            fcf = ocf - capex
            cashflow["free_cashflow_latest"] = fcf
            mc = val.get("market_cap_wanyuan")
            if mc and mc > 0:
                # daily_basic total_mv is in 万元; cashflow values are in 元
                cashflow["fcf_yield"] = fcf / (mc * 10000)

        # Owner Earnings = NI + D&A - Maintenance Capex (G=0.8)
        if ni_cf is not None and dep is not None and capex is not None:
            da = dep + (amort or 0.0)
            maint_capex = capex * 0.8
            cashflow["owner_earnings_latest"] = ni_cf + da - maint_capex

    out["cashflow"] = cashflow

    # ---- Q3 / latest-quarter vitals (if tracking a plunge) ----
    vitals = {}
    if latest_q_inc is not None and len(latest_q_inc):
        row = latest_q_inc.iloc[0]
        vitals["latest_period"] = str(row.get("end_date"))
        vitals["latest_revenue"] = _safe_float(row.get("revenue"))
        vitals["latest_net_income"] = _safe_float(row.get("n_income_attr_p"))
        vitals["latest_operating_profit"] = _safe_float(row.get("operate_profit"))
        vitals["latest_fv_chg_gain"] = _safe_float(row.get("fv_value_chg_gain"))
        vitals["latest_invest_income"] = _safe_float(row.get("invest_income"))
        vitals["latest_credit_impa_loss"] = _safe_float(row.get("credit_impa_loss"))
        vitals["latest_assets_impair_loss"] = _safe_float(row.get("assets_impair_loss"))
    out["latest_vitals"] = vitals

    # ---- segments (主营业务构成) ----
    segments = {}
    if not mainbz.empty and "end_date" in mainbz.columns:
        latest_period = mainbz["end_date"].max()
        latest = mainbz[mainbz["end_date"] == latest_period]
        seg_list = []
        for _, row in latest.iterrows():
            seg_list.append({
                "type": row.get("bz_item"),
                "item": row.get("bz_item"),
                "revenue": _safe_float(row.get("bz_sales")),
                "cost": _safe_float(row.get("bz_cost")),
                "profit": _safe_float(row.get("bz_profit")),
                "classification": row.get("curr_type") or row.get("bz_code"),
            })
        segments["latest_period"] = str(latest_period)
        segments["segments"] = seg_list
    out["segments"] = segments

    # ---- capital structure ----
    capital = {}
    if not bs.empty:
        latest_bs = bs.iloc[-1]
        total_liab = _safe_float(latest_bs.get("total_liab"))
        total_assets = _safe_float(latest_bs.get("total_assets"))
        total_cur_assets = _safe_float(latest_bs.get("total_cur_assets"))
        total_cur_liab = _safe_float(latest_bs.get("total_cur_liab"))
        inventory = _safe_float(latest_bs.get("inventories"))
        money = _safe_float(latest_bs.get("money_cap"))
        lt_borr = _safe_float(latest_bs.get("lt_borr"))
        st_borr = _safe_float(latest_bs.get("st_borr"))

        if total_liab is not None and total_assets and total_assets > 0:
            capital["debt_to_assets"] = total_liab / total_assets
        if total_cur_liab and total_cur_liab > 0 and total_cur_assets is not None:
            capital["current_ratio"] = total_cur_assets / total_cur_liab
            if inventory is not None:
                capital["quick_ratio"] = (total_cur_assets - inventory) / total_cur_liab
        capital["cash_latest"] = money
        capital["debt_latest"] = (lt_borr or 0.0) + (st_borr or 0.0)
        if money is not None:
            capital["net_cash_latest"] = money - capital["debt_latest"]
    out["capital"] = capital

    return out


# ============================================================================
# US metrics (yfinance)
# ============================================================================


def compute_us(bundle: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Lightweight metrics for US equity (yfinance bundle)."""
    info = bundle.get("info", pd.DataFrame())
    inc = bundle.get("income_annual", pd.DataFrame())
    cf = bundle.get("cashflow_annual", pd.DataFrame())
    hist = bundle.get("history_5y", pd.DataFrame())

    out: dict[str, Any] = {}

    # ---- valuation (from info) ----
    val = {}
    if not info.empty:
        row = info.iloc[0]
        for key in [
            "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months",
            "enterpriseToEbitda", "dividendYield", "marketCap", "enterpriseValue",
            "profitMargins", "operatingMargins", "grossMargins",
            "returnOnEquity", "returnOnAssets",
            "revenueGrowth", "earningsGrowth",
            "debtToEquity", "currentRatio", "quickRatio",
            "freeCashflow", "operatingCashflow",
            "currentPrice", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
            "beta", "sharesOutstanding",
            "sector", "industry", "longName", "shortName",
        ]:
            v = row.get(key)
            if v is not None and not (isinstance(v, float) and math.isnan(v)):
                val[key] = v
    out["valuation"] = val

    # ---- growth (from annual income) ----
    growth = {}
    if not inc.empty and "period" in inc.columns:
        inc = inc.sort_values("period").reset_index(drop=True)
        # Revenue column name is "Total Revenue" in yfinance
        if "Total Revenue" in inc.columns and len(inc) >= 3:
            growth["revenue_cagr_3y"] = _cagr(
                _safe_float(inc.iloc[-3]["Total Revenue"]),
                _safe_float(inc.iloc[-1]["Total Revenue"]),
                2,
            )
        if "Net Income" in inc.columns and len(inc) >= 2:
            growth["net_income_yoy_latest"] = _pct_change(
                _safe_float(inc.iloc[-2]["Net Income"]),
                _safe_float(inc.iloc[-1]["Net Income"]),
            )
    out["growth"] = growth

    # ---- price snapshot ----
    price = {}
    if not hist.empty:
        hist_sorted = hist.sort_values("Date") if "Date" in hist.columns else hist
        last = hist_sorted.iloc[-1]
        price["latest_close"] = _safe_float(last.get("Close"))
        price["latest_date"] = str(last.get("Date"))
        price["52w_high"] = _safe_float(hist_sorted["High"].max()) if "High" in hist_sorted else None
        price["52w_low"] = _safe_float(hist_sorted["Low"].min()) if "Low" in hist_sorted else None
    out["price"] = price

    return out


# ============================================================================
# CLI
# ============================================================================


def _load_bundle_from_dir(d: Path) -> dict[str, pd.DataFrame]:
    """Load all *.parquet from a directory into a bundle dict keyed by stem."""
    bundle = {}
    for p in d.glob("*.parquet"):
        try:
            bundle[p.stem] = pd.read_parquet(p)
        except Exception:
            pass
    return bundle


def main():
    ap = argparse.ArgumentParser(description="Compute derived metrics from a raw_data bundle dir.")
    ap.add_argument("bundle_dir", help="Path to output/{company}/raw_data/")
    ap.add_argument("--market", choices=["a", "us", "hk"], default="a", help="Which schema")
    ap.add_argument("--out", default=None, help="Output JSON path (default: {bundle_dir}/../metrics.json)")
    args = ap.parse_args()

    d = Path(args.bundle_dir)
    bundle = _load_bundle_from_dir(d)
    print(f"Loaded {len(bundle)} dataframes from {d}")

    if args.market == "a":
        metrics = compute_a_share(bundle)
    elif args.market == "us":
        metrics = compute_us(bundle)
    else:
        # HK is hybrid — try both
        metrics = compute_us({k.removeprefix("yf_"): v for k, v in bundle.items() if k.startswith("yf_")})

    out_path = Path(args.out) if args.out else d.parent / "metrics.json"
    out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2, default=str))
    print(f"Wrote metrics to {out_path}")
    print(json.dumps(metrics, ensure_ascii=False, indent=2, default=str)[:2000])


if __name__ == "__main__":
    main()
