"""Tushare Pro collector for A-shares (and a subset of HK).

Design:
- One class `TushareCollector`, methods grouped by domain.
- Each public method:
    1. Checks cache (via data_cache)
    2. Calls tushare API with rate-limiting + exponential backoff
    3. Stores result in cache
    4. Returns a pandas DataFrame
- Token is loaded lazily — first use of any A-share method triggers init.

Usage:
    from scripts.tushare_collector import TushareCollector
    c = TushareCollector()
    df_income = c.income("002862.SZ", start_year=2022)
    df_bs = c.balancesheet("002862.SZ", start_year=2022)
    bundle = c.collect_all("002862.SZ")  # one-shot, returns dict of DataFrames

CLI:
    python3 -m scripts.tushare_collector 002862.SZ [--out output/实丰文化/raw_data/]
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from . import config, data_cache


# ---------- Code normalization ----------

_A_SHARE_PATTERN = re.compile(r"^(\d{6})(?:\.(SH|SZ|BJ))?$", re.IGNORECASE)
_HK_PATTERN = re.compile(r"^(\d{1,5})(?:\.HK)?$", re.IGNORECASE)


def normalize_a_code(code: str) -> str:
    """'002862' → '002862.SZ'; '600519' → '600519.SH'; '832522' → '832522.BJ'; '920522' → '920522.BJ'.

    Rules without explicit suffix:
      6xx → .SH (主板/科创板)
      0xx/3xx → .SZ (主板/创业板)
      4xx/8xx/9xx → .BJ (北交所；含 2025 年 8XXXXX→9XXXXX 迁移代码)

    若需访问 SH 900XXX B 股(罕见,且大多已退市), 必须显式指定 ".SH" 后缀。
    """
    code = code.strip().upper()
    m = _A_SHARE_PATTERN.match(code)
    if not m:
        raise ValueError(f"Not a valid A-share code: {code!r}")
    num, suffix = m.group(1), m.group(2)
    if suffix:
        return f"{num}.{suffix}"
    first = num[0]
    if first == "6":
        return f"{num}.SH"
    if first in "03":
        return f"{num}.SZ"
    if first in "489":
        return f"{num}.BJ"
    raise ValueError(f"Unknown market prefix for {code!r}")


def normalize_hk_code(code: str) -> str:
    """'700' → '0700.HK'; '0700.HK' → '0700.HK'. Pads to 4+ digits."""
    code = code.strip().upper()
    m = _HK_PATTERN.match(code)
    if not m:
        raise ValueError(f"Not a valid HK code: {code!r}")
    num = m.group(1).zfill(4)
    return f"{num}.HK"


# ---------- Collector ----------

class TushareCollector:
    """Thin wrapper around tushare.pro_api() with caching + rate limiting."""

    def __init__(self, token: str | None = None, rate_limit_sec: float | None = None):
        self._token = token or config.TUSHARE_TOKEN
        self._rate = rate_limit_sec or config.TUSHARE_RATE_LIMIT_SEC
        self._last_call: float = 0.0
        self._pro: Any | None = None  # lazy init

    # ---- infra ----

    def _ensure_pro(self):
        if self._pro is not None:
            return
        if not self._token:
            raise RuntimeError(
                "TUSHARE_TOKEN 未设置。请在 ~/.zshrc 添加：\n"
                "  export TUSHARE_TOKEN='your_token_here'\n"
                "然后新开终端或 source ~/.zshrc"
            )
        import tushare as ts  # deferred import
        ts.set_token(self._token)
        self._pro = ts.pro_api()

    def _throttle(self):
        elapsed = time.time() - self._last_call
        if elapsed < self._rate:
            time.sleep(self._rate - elapsed)
        self._last_call = time.time()

    def _call(self, fn: Callable, **kwargs) -> pd.DataFrame:
        """Invoke a tushare pro_api method with retry + rate-limit."""
        self._ensure_pro()
        last_err: Exception | None = None
        for attempt in range(config.TUSHARE_MAX_RETRIES):
            try:
                self._throttle()
                df = fn(**kwargs)
                if df is None:
                    return pd.DataFrame()
                return df
            except Exception as e:  # noqa: BLE001 — tushare throws vague errors
                last_err = e
                wait = config.TUSHARE_RETRY_BACKOFF ** attempt
                sys.stderr.write(
                    f"[tushare retry {attempt + 1}/{config.TUSHARE_MAX_RETRIES}] "
                    f"{fn.__name__}({kwargs}) failed: {e}. Sleeping {wait:.1f}s.\n"
                )
                time.sleep(wait)
        raise RuntimeError(f"tushare {fn.__name__} failed after retries: {last_err}")

    def _cached(self, key: str, fn: Callable, **kwargs) -> pd.DataFrame:
        """Run a tushare call with caching."""
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        method = getattr(self._pro, fn.__name__) if hasattr(fn, "__name__") else fn
        df = self._call(method, **kwargs)
        data_cache.put(key, df, extra={"api": fn.__name__ if hasattr(fn, "__name__") else "unknown"})
        return df

    # ---- metadata ----

    def stock_basic(self, ts_code: str) -> pd.DataFrame:
        """Stock metadata: name, industry, list_date, exchange, etc."""
        key = f"tushare_stock_basic_{ts_code}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        df = self._call(
            self._pro.stock_basic,
            ts_code=ts_code,
            fields="ts_code,symbol,name,area,industry,fullname,market,exchange,list_status,list_date,delist_date,is_hs",
        )
        data_cache.put(key, df, extra={"api": "stock_basic"})
        return df

    def resolve_ticker(
        self,
        code_or_name: str,
        name_hint: str | None = None,
    ) -> tuple[str, pd.DataFrame]:
        """Resolve a possibly-wrong / legacy / ambiguous ticker.

        Tries (in order):
          1. The provided code as-is (after normalize_a_code if it parses)
          2. If a name_hint is given OR the input is non-numeric: search stock_basic
             by name field (含模糊匹配; 单一命中即返回, 多命中报错列出 5 条候选)
             — 这是北交所 2025 年 8XXXXX→9XXXXX 代码迁移的主 fallback 路径,
               因 BSE 迁移并非简单字符替换 (832522 → 920522 而非 932522), 必须靠名称匹配

        Returns: (resolved_code, basic_df)
        Raises: RuntimeError with helpful suggestions if all fallbacks fail.
        """
        self._ensure_pro()

        # Step 1: Try as-is (if it parses as a code)
        try:
            code = normalize_a_code(code_or_name)
        except ValueError:
            code = None

        if code:
            df = self.stock_basic(code)
            if not df.empty:
                return code, df

        # Step 2: Search by name (when name_hint OR input looks like name not code)
        name = name_hint if name_hint else (code_or_name if not code else None)
        if name:
            all_basic = self._call(
                self._pro.stock_basic,
                list_status="L",
                fields="ts_code,name,industry,market,exchange",
            )
            match = all_basic[all_basic["name"].str.contains(name, na=False, regex=False)]
            if len(match) == 1:
                found_code = match.iloc[0]["ts_code"]
                sys.stderr.write(
                    f"⚠️  '{code_or_name}' 未直接命中, 按名称匹配到 "
                    f"{found_code} ({match.iloc[0]['name']})\n"
                )
                return found_code, self.stock_basic(found_code)
            elif len(match) > 1:
                hits = match[["ts_code", "name"]].head(5).to_dict("records")
                raise RuntimeError(
                    f"按名称 '{name}' 找到 {len(match)} 个匹配 (前 5):\n"
                    f"  {hits}\n"
                    "请显式指定 ts_code"
                )

        # All fallbacks exhausted
        attempted = [f"stock_basic(ts_code={code or code_or_name})"]
        if name:
            attempted.append(f"按名称 '{name}' 搜索 stock_basic")
        raise RuntimeError(
            f"无法解析 ticker '{code_or_name}'。已尝试:\n"
            + "\n".join(f"  - {a}" for a in attempted)
            + "\n建议: (a) 检查代码拼写; "
            "(b) 北交所 2025 部分股票从 8XXXXX 迁至 9XXXXX, 建议输入最新 9XXXXX 代码; "
            "(c) 添加 --name 公司名 以启用名称 fallback"
        )

    # ---- 3 大报表 ----

    # ---- 字段精简说明（v4） ----
    # v3 曾拉取全部字段（income 85 / balance 152 / cashflow 97 / fina_indicator 108），
    # 但报告实际只用 <10% 字段。v4 精简到"核心字段集"（涵盖 95% 用例），
    # Parquet 体积减少 ~70%。如需完整字段，调用时传 fields='full'.

    _INCOME_CORE_FIELDS = (
        "ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,"
        "basic_eps,diluted_eps,total_revenue,revenue,"
        "total_cogs,oper_cost,sell_exp,admin_exp,fin_exp,rd_exp,"
        "biz_tax_surchg,assets_impair_loss,credit_impa_loss,"
        "fv_value_chg_gain,invest_income,ass_invest_income,"
        "operate_profit,non_oper_income,non_oper_exp,total_profit,"
        "income_tax,n_income,n_income_attr_p,minority_gain,"
        "ebit,ebitda"
    )

    def income(self, ts_code: str, start_year: int = 2020, report_type: int = 1,
               fields: str = "core") -> pd.DataFrame:
        """利润表（合并报表）。

        fields='core' (默认，~32 列) 或 'full' (全量 85 列)。
        report_type: 1=合并, 2=单季, 4=单季调整
        """
        key = f"tushare_income_{ts_code}_rt{report_type}_from{start_year}_{fields}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        if fields == "core":
            fields_param = self._INCOME_CORE_FIELDS
        elif fields == "full":
            fields_param = (
                "ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,"
                "basic_eps,diluted_eps,total_revenue,revenue,int_income,prem_earned,"
                "comm_income,n_commis_income,n_oth_income,n_oth_b_income,prem_income,"
                "out_prem,une_prem_reser,reins_income,n_sec_tb_income,n_sec_uw_income,"
                "n_asset_mg_income,oth_b_income,fv_value_chg_gain,invest_income,"
                "ass_invest_income,forex_gain,total_cogs,oper_cost,int_exp,comm_exp,"
                "biz_tax_surchg,sell_exp,admin_exp,fin_exp,assets_impair_loss,"
                "prem_refund,compens_payout,reser_insur_liab,div_payt,reins_exp,"
                "oper_exp,compens_payout_refu,insur_reser_refu,reins_cost_refund,"
                "other_bus_cost,operate_profit,non_oper_income,non_oper_exp,nca_disploss,"
                "total_profit,income_tax,n_income,n_income_attr_p,minority_gain,"
                "oth_compr_income,t_compr_income,compr_inc_attr_p,compr_inc_attr_m_s,"
                "ebit,ebitda,insurance_exp,undist_profit,distable_profit,rd_exp,"
                "fin_exp_int_exp,fin_exp_int_inc,credit_impa_loss"
            )
        else:
            fields_param = fields  # 用户自定义
        df = self._call(
            self._pro.income,
            ts_code=ts_code,
            start_date=f"{start_year}0101",
            end_date=dt.date.today().strftime("%Y%m%d"),
            report_type=report_type,
            fields=fields_param,
        )
        data_cache.put(key, df, extra={"api": "income", "fields": fields})
        return df

    _BALANCE_CORE_FIELDS = (
        "ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,"
        "total_share,money_cap,accounts_receiv,prepayment,inventories,"
        "oth_cur_assets,total_cur_assets,"
        "lt_eqt_invest,fix_assets,cip,intan_assets,goodwill,"
        "defer_tax_assets,total_nca,total_assets,"
        "st_borr,notes_payable,acct_payable,adv_receipts,"
        "payroll_payable,taxes_payable,oth_payable,"
        "non_cur_liab_due_1y,total_cur_liab,"
        "lt_borr,bond_payable,lt_payable,defer_tax_liab,total_ncl,"
        "total_liab,cap_rese,surplus_rese,undistr_porfit,"
        "total_hldr_eqy_exc_min_int,total_hldr_eqy_inc_min_int,minority_int,"
        "oth_receiv,contract_assets"
    )

    def balancesheet(self, ts_code: str, start_year: int = 2020, report_type: int = 1,
                     fields: str = "core") -> pd.DataFrame:
        """资产负债表。fields='core' (默认 ~42 列) 或 'full' (全量 152 列)."""
        key = f"tushare_balance_{ts_code}_rt{report_type}_from{start_year}_{fields}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        if fields == "core":
            fields_param = self._BALANCE_CORE_FIELDS
        elif fields == "full":
            fields_param = None  # 让 Tushare 返回全部
        else:
            fields_param = fields
        kwargs = dict(
            ts_code=ts_code,
            start_date=f"{start_year}0101",
            end_date=dt.date.today().strftime("%Y%m%d"),
            report_type=report_type,
        )
        if fields_param:
            kwargs["fields"] = fields_param
        df = self._call(self._pro.balancesheet, **kwargs)
        data_cache.put(key, df, extra={"api": "balancesheet", "fields": fields})
        return df

    _CASHFLOW_CORE_FIELDS = (
        "ts_code,ann_date,f_ann_date,end_date,comp_type,report_type,"
        "net_profit,finan_exp,free_cashflow,"
        "c_fr_sale_sg,c_paid_goods_s,c_paid_to_for_empl,c_paid_for_taxes,"
        "n_cashflow_act,"
        "c_disp_withdrwl_invest,c_recp_return_invest,c_pay_acq_const_fiolta,c_paid_invest,"
        "n_cashflow_inv_act,"
        "c_recp_borrow,proc_issue_bonds,c_prepay_amt_borr,c_pay_dist_dpcp_int_exp,"
        "n_cash_flows_fnc_act,"
        "prov_depr_assets,depr_fa_coga_dpba,amort_intang_assets,"
        "decr_inventories,decr_oper_payable,incr_oper_payable,"
        "n_incr_cash_cash_equ,c_cash_equ_beg_period,c_cash_equ_end_period,"
        "credit_impa_loss"
    )

    def cashflow(self, ts_code: str, start_year: int = 2020, report_type: int = 1,
                 fields: str = "core") -> pd.DataFrame:
        """现金流量表。fields='core' (默认 ~33 列) 或 'full' (全量 97 列)."""
        key = f"tushare_cashflow_{ts_code}_rt{report_type}_from{start_year}_{fields}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        if fields == "core":
            fields_param = self._CASHFLOW_CORE_FIELDS
        elif fields == "full":
            fields_param = None
        else:
            fields_param = fields
        kwargs = dict(
            ts_code=ts_code,
            start_date=f"{start_year}0101",
            end_date=dt.date.today().strftime("%Y%m%d"),
            report_type=report_type,
        )
        if fields_param:
            kwargs["fields"] = fields_param
        df = self._call(self._pro.cashflow, **kwargs)
        data_cache.put(key, df, extra={"api": "cashflow", "fields": fields})
        return df

    _FINA_INDICATOR_CORE_FIELDS = (
        "ts_code,ann_date,end_date,"
        "eps,dt_eps,total_revenue_ps,revenue_ps,capital_rese_ps,surplus_rese_ps,undist_profit_ps,"
        "extra_item,profit_dedt,gross_margin,current_ratio,quick_ratio,cash_ratio,"
        "ar_turn,ca_turn,fa_turn,assets_turn,"
        "op_income,ebit,ebitda,fcff,fcfe,current_exint,noncurrent_exint,interestdebt,"
        "netdebt,tangible_asset,working_capital,networking_capital,invest_capital,"
        "retained_earnings,diluted2_eps,bps,ocfps,retainedps,cfps,ebit_ps,fcff_ps,fcfe_ps,"
        "netprofit_margin,grossprofit_margin,cogs_of_sales,expense_of_sales,"
        "profit_to_gr,saleexp_to_gr,adminexp_of_gr,finaexp_of_gr,"
        "impai_ttm,gc_of_gr,op_of_gr,ebit_of_gr,roe,roe_waa,roe_dt,roa,npta,roic,roe_yearly,"
        "roa2_yearly,debt_to_assets,assets_to_eqt,dp_assets_to_eqt,ca_to_assets,"
        "nca_to_assets,tbassets_to_totalassets,int_to_talcap,eqt_to_talcapital,"
        "currentdebt_to_debt,longdeb_to_debt,ocf_to_shortdebt,debt_to_eqt,eqt_to_debt,"
        "eqt_to_interestdebt,tangibleasset_to_debt,tangasset_to_intdebt,"
        "tangibleasset_to_netdebt,ocf_to_debt,ocf_to_interestdebt,ocf_to_netdebt,"
        "ebit_to_interest,longdebt_to_workingcapital,ebitda_to_debt,turn_days,"
        "roa_yearly,roa_dp,fixed_assets,profit_prefin_exp,non_op_profit,op_to_ebt,"
        "nop_to_ebt,ocf_to_profit,cash_to_liqdebt,cash_to_liqdebt_withinterest,"
        "op_to_liqdebt,op_to_debt,roic_yearly,total_fa_trun,profit_to_op,q_opincome,"
        "q_investincome,q_dtprofit,q_eps,q_netprofit_margin,q_gsprofit_margin,"
        "q_exp_to_sales,q_profit_to_gr,q_saleexp_to_gr,q_adminexp_to_gr,q_finaexp_to_gr,"
        "q_impair_to_gr_ttm,q_gc_to_gr,q_op_to_gr,q_roe,q_dt_roe,q_npta"
    )

    def fina_indicator(self, ts_code: str, start_year: int = 2020,
                       fields: str = "core") -> pd.DataFrame:
        """财务指标（ROE/ROA/毛利率等）。fields='core' (默认 ~110 列) 或 'full' (全量 108 列，差异在 ttm 指标).

        注：fina_indicator 本身字段已经比较精简，core 与 full 差异不大，但保留接口形式一致。
        """
        key = f"tushare_fina_indicator_{ts_code}_from{start_year}_{fields}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        kwargs = dict(
            ts_code=ts_code,
            start_date=f"{start_year}0101",
            end_date=dt.date.today().strftime("%Y%m%d"),
        )
        if fields == "core":
            kwargs["fields"] = self._FINA_INDICATOR_CORE_FIELDS
        elif fields == "full":
            pass  # 不传 fields 返回默认全部
        else:
            kwargs["fields"] = fields
        df = self._call(self._pro.fina_indicator, **kwargs)
        data_cache.put(key, df, extra={"api": "fina_indicator", "fields": fields})
        return df

    # ---- 股权 / 治理 ----

    def top10_holders(self, ts_code: str, start_year: int = 2023) -> pd.DataFrame:
        """前十大股东。"""
        key = f"tushare_top10_holders_{ts_code}_from{start_year}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        df = self._call(
            self._pro.top10_holders,
            ts_code=ts_code,
            start_date=f"{start_year}0101",
            end_date=dt.date.today().strftime("%Y%m%d"),
        )
        data_cache.put(key, df, extra={"api": "top10_holders"})
        return df

    def top10_floatholders(self, ts_code: str, start_year: int = 2023) -> pd.DataFrame:
        """前十大流通股东。"""
        key = f"tushare_top10_float_{ts_code}_from{start_year}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        df = self._call(
            self._pro.top10_floatholders,
            ts_code=ts_code,
            start_date=f"{start_year}0101",
            end_date=dt.date.today().strftime("%Y%m%d"),
        )
        data_cache.put(key, df, extra={"api": "top10_floatholders"})
        return df

    def pledge_detail(self, ts_code: str) -> pd.DataFrame:
        """股权质押明细。"""
        key = f"tushare_pledge_{ts_code}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        df = self._call(self._pro.pledge_detail, ts_code=ts_code)
        data_cache.put(key, df, extra={"api": "pledge_detail"})
        return df

    def stk_managers(self, ts_code: str) -> pd.DataFrame:
        """公司高管信息（董监高名单、任职、学历）。"""
        key = f"tushare_stk_managers_{ts_code}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        df = self._call(self._pro.stk_managers, ts_code=ts_code)
        data_cache.put(key, df, extra={"api": "stk_managers"})
        return df

    def stk_rewards(self, ts_code: str) -> pd.DataFrame:
        """管理层薪酬与持股（报酬明细）。"""
        key = f"tushare_stk_rewards_{ts_code}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        df = self._call(self._pro.stk_rewards, ts_code=ts_code)
        data_cache.put(key, df, extra={"api": "stk_rewards"})
        return df

    def stk_holdernumber(self, ts_code: str, start_year: int = 2023) -> pd.DataFrame:
        """股东户数变化（反映散户/机构流向）。"""
        key = f"tushare_holdernumber_{ts_code}_from{start_year}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        df = self._call(
            self._pro.stk_holdernumber,
            ts_code=ts_code,
            start_date=f"{start_year}0101",
            end_date=dt.date.today().strftime("%Y%m%d"),
        )
        data_cache.put(key, df, extra={"api": "stk_holdernumber"})
        return df

    def repurchase(self, ts_code: str) -> pd.DataFrame:
        """股票回购明细。"""
        key = f"tushare_repurchase_{ts_code}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        df = self._call(self._pro.repurchase, ts_code=ts_code)
        data_cache.put(key, df, extra={"api": "repurchase"})
        return df

    # ---- 业绩预告与快报（v3 新增） ----

    def forecast_vip(self, ts_code: str) -> pd.DataFrame:
        """业绩预告（全量，含预增/预减/扭亏/首亏等说明）。"""
        key = f"tushare_forecast_vip_{ts_code}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        df = self._call(self._pro.forecast_vip, ts_code=ts_code)
        data_cache.put(key, df, extra={"api": "forecast_vip"})
        return df

    def express_vip(self, ts_code: str) -> pd.DataFrame:
        """业绩快报（年报前的快速披露）。"""
        key = f"tushare_express_vip_{ts_code}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        df = self._call(self._pro.express_vip, ts_code=ts_code)
        data_cache.put(key, df, extra={"api": "express_vip"})
        return df

    # ---- 市场数据 ----

    def daily_basic(self, ts_code: str, trade_date: str | None = None) -> pd.DataFrame:
        """每日基本面（含 PE/PB/PS/股息率）。trade_date=YYYYMMDD；默认最近 250 个交易日。"""
        key = f"tushare_daily_basic_{ts_code}_{trade_date or 'recent'}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        kwargs = {"ts_code": ts_code}
        if trade_date:
            kwargs["trade_date"] = trade_date
        else:
            # 最近 ~1 年数据
            end = dt.date.today().strftime("%Y%m%d")
            start = (dt.date.today() - dt.timedelta(days=400)).strftime("%Y%m%d")
            kwargs["start_date"] = start
            kwargs["end_date"] = end
        df = self._call(self._pro.daily_basic, **kwargs)
        data_cache.put(key, df, extra={"api": "daily_basic"})
        return df

    def daily(self, ts_code: str, years: int = 3) -> pd.DataFrame:
        """日线行情（不复权）。

        若 Tushare Pro 返回空(常见于北交所低积分账户), 自动 fallback 到新浪
        免费 K 线 JSON, 字段名/单位适配到 Pro 风格。fallback 标志写入 cache extra
        以便排查。
        """
        key = f"tushare_daily_{ts_code}_y{years}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        end = dt.date.today()
        start = end - dt.timedelta(days=years * 365)
        df = self._call(
            self._pro.daily,
            ts_code=ts_code,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
        )

        source = "tushare_pro"
        if df.empty:
            sys.stderr.write(
                f"⚠️  Tushare Pro daily 返回空 for {ts_code} (可能积分不足或代码异常), "
                "尝试新浪免费 K 线 fallback...\n"
            )
            from . import legacy_quote
            datalen = max(years * 250, 250)  # 250 交易日/年
            legacy_df = legacy_quote.get_daily_history_legacy(ts_code, datalen=datalen)
            if not legacy_df.empty:
                df = legacy_quote.filter_by_date_range(
                    legacy_df,
                    start_date=start.strftime("%Y%m%d"),
                    end_date=end.strftime("%Y%m%d"),
                )
                source = "sina_legacy"
                sys.stderr.write(
                    f"✅ 新浪免费 K 线 fallback 命中 for {ts_code}: {len(df)} 行 "
                    "(注: amount 字段为 close × volume 估算值, "
                    "vs Pro 的真实成交额可能有 ±5% 偏差)\n"
                )

        data_cache.put(key, df, extra={"api": "daily", "source": source})
        return df

    # ---- 分业务 / 行业 ----

    def fina_mainbz(self, ts_code: str, start_year: int = 2023) -> pd.DataFrame:
        """主营业务构成（分行业/产品/地区）。若披露过则有数据。"""
        key = f"tushare_mainbz_{ts_code}_from{start_year}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        df = self._call(
            self._pro.fina_mainbz,
            ts_code=ts_code,
            start_date=f"{start_year}0101",
            end_date=dt.date.today().strftime("%Y%m%d"),
        )
        data_cache.put(key, df, extra={"api": "fina_mainbz"})
        return df

    def dividend(self, ts_code: str) -> pd.DataFrame:
        """分红送股明细。"""
        key = f"tushare_dividend_{ts_code}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        df = self._call(self._pro.dividend, ts_code=ts_code)
        data_cache.put(key, df, extra={"api": "dividend"})
        return df

    # ---- 公告 ----

    def disclosure_date(self, ts_code: str) -> pd.DataFrame:
        """披露日历（年报/季报/业绩预告等预告日期）。"""
        key = f"tushare_disclosure_{ts_code}"
        cached = data_cache.get(key)
        if cached is not None:
            return cached
        self._ensure_pro()
        df = self._call(self._pro.disclosure_date, ts_code=ts_code)
        data_cache.put(key, df, extra={"api": "disclosure_date"})
        return df

    # ---- 一键采集 ----

    def collect_all(self, ts_code: str, start_year: int = 2022) -> dict[str, pd.DataFrame]:
        """Collect the full financial + governance bundle for a company.

        Returns a dict keyed by data domain. Each value is a pandas DataFrame
        (possibly empty if the API has no data or failed).
        """
        bundle: dict[str, pd.DataFrame] = {}
        bundle["stock_basic"] = self.stock_basic(ts_code)
        bundle["income"] = self.income(ts_code, start_year=start_year)
        bundle["balancesheet"] = self.balancesheet(ts_code, start_year=start_year)
        bundle["cashflow"] = self.cashflow(ts_code, start_year=start_year)
        bundle["fina_indicator"] = self.fina_indicator(ts_code, start_year=start_year)
        bundle["top10_holders"] = self.top10_holders(ts_code, start_year=start_year)
        bundle["top10_floatholders"] = self.top10_floatholders(ts_code, start_year=start_year)
        bundle["pledge_detail"] = self.pledge_detail(ts_code)
        bundle["daily_basic"] = self.daily_basic(ts_code)
        bundle["daily"] = self.daily(ts_code)
        # 业绩预告/快报
        try:
            bundle["forecast_vip"] = self.forecast_vip(ts_code)
        except Exception:  # noqa: BLE001
            bundle["forecast_vip"] = pd.DataFrame()
        try:
            bundle["express_vip"] = self.express_vip(ts_code)
        except Exception:  # noqa: BLE001
            bundle["express_vip"] = pd.DataFrame()
        # 高管 / 股东户数 / 回购
        try:
            bundle["stk_managers"] = self.stk_managers(ts_code)
        except Exception:  # noqa: BLE001
            bundle["stk_managers"] = pd.DataFrame()
        try:
            bundle["stk_rewards"] = self.stk_rewards(ts_code)
        except Exception:  # noqa: BLE001
            bundle["stk_rewards"] = pd.DataFrame()
        try:
            bundle["stk_holdernumber"] = self.stk_holdernumber(ts_code, start_year=start_year)
        except Exception:  # noqa: BLE001
            bundle["stk_holdernumber"] = pd.DataFrame()
        try:
            bundle["repurchase"] = self.repurchase(ts_code)
        except Exception:  # noqa: BLE001
            bundle["repurchase"] = pd.DataFrame()
        # 以下两个对部分公司为空
        try:
            bundle["fina_mainbz"] = self.fina_mainbz(ts_code, start_year=start_year)
        except Exception:  # noqa: BLE001 — mainbz 可能无权限
            bundle["fina_mainbz"] = pd.DataFrame()
        try:
            bundle["dividend"] = self.dividend(ts_code)
        except Exception:  # noqa: BLE001
            bundle["dividend"] = pd.DataFrame()
        # 披露日历
        try:
            bundle["disclosure_date"] = self.disclosure_date(ts_code)
        except Exception:  # noqa: BLE001
            bundle["disclosure_date"] = pd.DataFrame()
        return bundle


# ---------- Output helpers ----------

def save_bundle(bundle: dict[str, pd.DataFrame], out_dir: Path) -> None:
    """Save each DataFrame as a Parquet file under out_dir/raw_data/."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for key, df in bundle.items():
        path = out_dir / f"{key}.parquet"
        df.to_parquet(path, index=False)
        summary[key] = {"rows": len(df), "cols": len(df.columns), "path": str(path.name)}
    # Save a summary index
    import json
    (out_dir / "_manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
    )


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="Collect Tushare financial bundle for an A-share.")
    ap.add_argument("code", help="Stock code (e.g. 002862 or 002862.SZ)")
    ap.add_argument("--out", default=None, help="Output dir (default: output/{code}/raw_data/)")
    ap.add_argument("--start-year", type=int, default=2022, help="Earliest year of financials to fetch")
    ap.add_argument("--name", default=None, help="Chinese/common name for output dir (default from stock_basic)")
    args = ap.parse_args()

    c = TushareCollector()
    ts_code, target_basic = c.resolve_ticker(args.code, name_hint=args.name)
    print(f"Resolved code: {ts_code}")

    print(f"Fetching bundle for {ts_code}...")
    bundle = c.collect_all(ts_code, start_year=args.start_year)

    # Decide output directory
    if args.out:
        out_dir = Path(args.out)
    else:
        name = args.name
        if not name and len(bundle["stock_basic"]) > 0:
            name = bundle["stock_basic"]["name"].iloc[0]
        if not name:
            name = ts_code.replace(".", "_")
        out_dir = config.output_dir(name) / "raw_data"

    save_bundle(bundle, out_dir)

    print(f"\nSaved to: {out_dir}")
    for key, df in bundle.items():
        print(f"  {key}: {len(df)} rows × {len(df.columns)} cols")


if __name__ == "__main__":
    main()
