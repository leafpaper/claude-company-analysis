"""data_snapshot.py — 确定性产出 data_snapshot.md, 一劳永逸修复 Phase 3 数据漏读 / 章节省略.

设计目标:
    Phase 3 写主报告时反复出现"漏掉最新季度数据 / 用业绩预告替代实际年报 / 十大股东表
    简化省略"等问题, 根因是 Phase 3 LLM 只读 phase1-data.md (LLM 摘要), 不读 raw_data
    源头 parquet。本脚本绕开 LLM, 用纯 Python 从 parquet 读取并拼装一个完整的中间
    artifact `data_snapshot.md`, 让 Phase 3 每次写报告前都能 Read 到确定性完整数据.

设计原则:
    - 完全 Python 拼装, 无 LLM 参与 → 数据完整性 100% 确定
    - 字段 / 表格 / 行数全部固定, LLM 看到的是结构化的 markdown table
    - 头部插入 "★ Phase 3 必读规则" 强约束, 同时在 anti_lazy_lint Rule 3 加入此 artifact 的
      关键短语检查作为 safety net

输出 8 节:
    §1 数据完整度 — 每张表行数 / end_date 区间 / 最新期
    §2 最新期完整快照 — income / balance / cashflow / fina_indicator 最新行关键字段
    §3 多年趋势完整表 — 每个 distinct end_date 一行 (LLM 写主报告 §四 财务趋势表的源头)
    §4 业绩预告 vs 实际兑现 — forecast_vip 每条 vs 同期 income (强制 LLM 用 actual)
    §5 完整十大股东表 — 最近 4 期 × 10 行 (主报告 §四 十大股东章节源头)
    §6 完整十大流通股东表 — 最近 4 期 × 10 行
    §7 质押 / 冻结明细 — pledge_detail (active 状态)
    §8 股东户数变化时序 — stk_holdernumber 完整历史

CLI:
    python3 -m scripts.data_snapshot \\
        --bundle output/{company}/raw_data \\
        --out output/{company}/data_snapshot.md
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from io import StringIO
from pathlib import Path
from typing import Optional

import pandas as pd


# ---------- 常量 ----------

# §3 多年趋势表的核心字段 (从 income + fina_indicator join)
TREND_FIELDS = [
    ("end_date", "期末"),
    ("revenue_yi", "营收(亿)"),
    ("revenue_yoy", "营收 YoY"),
    ("gross_margin", "毛利率%"),
    ("net_margin", "净利率%"),
    ("n_income_yi", "归母净利(亿)"),
    ("net_income_yoy", "净利 YoY"),
    ("roe", "加权 ROE"),
    ("debt_to_assets", "资产负债率%"),
    ("ocf_yi", "OCF(亿)"),
]

# §2.1 利润表关键字段 (中文标签, 单位)
INCOME_KEY_FIELDS = [
    ("revenue", "营业收入", "yi"),
    ("oper_cost", "营业成本", "yi"),
    ("sell_exp", "销售费用", "yi"),
    ("admin_exp", "管理费用", "yi"),
    ("rd_exp", "研发费用", "yi"),
    ("fin_exp", "财务费用", "wan"),
    ("biz_tax_surchg", "税金及附加", "wan"),
    ("assets_impair_loss", "资产减值损失", "wan"),
    ("credit_impa_loss", "信用减值损失", "wan"),
    ("fv_value_chg_gain", "公允价值变动", "wan"),
    ("invest_income", "投资收益", "wan"),
    ("operate_profit", "营业利润", "yi"),
    ("non_oper_income", "营业外收入", "wan"),
    ("non_oper_exp", "营业外支出", "wan"),
    ("total_profit", "利润总额", "yi"),
    ("income_tax", "所得税", "wan"),
    ("n_income", "净利润", "yi"),
    ("n_income_attr_p", "归母净利润", "yi"),
    ("basic_eps", "基本 EPS(元)", "raw"),
]

# §2.2 资产负债表关键字段
BALANCE_KEY_FIELDS = [
    ("total_assets", "总资产", "yi"),
    ("total_liab", "总负债", "yi"),
    ("total_hldr_eqy_inc_min_int", "所有者权益合计", "yi"),
    ("money_cap", "货币资金", "yi"),
    ("accounts_receiv", "应收账款", "yi"),
    ("inventories", "存货", "yi"),
    ("fix_assets", "固定资产", "yi"),
    ("cip", "在建工程", "yi"),
    ("intan_assets", "无形资产", "yi"),
    ("goodwill", "商誉", "yi"),
    ("st_borr", "短期借款", "yi"),
    ("notes_payable", "应付票据", "yi"),
    ("acct_payable", "应付账款", "yi"),
    ("lt_borr", "长期借款", "yi"),
    ("total_share", "总股本(万股)", "wanshares"),
]

# §2.3 现金流量表关键字段
CASHFLOW_KEY_FIELDS = [
    ("net_profit", "净利润(对账)", "yi"),
    ("c_fr_sale_sg", "销售商品收到现金", "yi"),
    ("c_paid_goods_s", "购买商品支付现金", "yi"),
    ("c_paid_for_taxes", "支付税费", "yi"),
    ("n_cashflow_act", "经营活动现金流净额", "yi"),
    ("c_pay_acq_const_fiolta", "购建固定资产支付现金", "yi"),
    ("c_paid_invest", "投资支付现金", "yi"),
    ("n_cashflow_inv_act", "投资活动现金流净额", "yi"),
    ("c_recp_borrow", "借款收到现金", "yi"),
    ("c_prepay_amt_borr", "偿还债务支付现金", "yi"),
    ("c_pay_dist_dpcp_int_exp", "分配股利偿付利息现金", "yi"),
    ("n_cash_flows_fnc_act", "筹资活动现金流净额", "yi"),
    ("free_cashflow", "自由现金流", "yi"),
    ("depr_fa_coga_dpba", "固定资产折旧", "yi"),
    ("amort_intang_assets", "无形资产摊销", "wan"),
]

# §2.4 fina_indicator 关键字段
FINA_KEY_FIELDS = [
    ("eps", "EPS(元/股)"),
    ("revenue_ps", "营收 / 股(元)"),
    ("ocfps", "经营现金流 / 股(元)"),
    ("gross_margin", "毛利率(%)"),
    ("netprofit_margin", "净利率(%)"),
    ("netprofit_yoy", "净利 YoY(%)"),
    ("tr_yoy", "营收 YoY(%)"),
    ("roe", "加权 ROE(%)"),
    ("roe_dt", "加权 ROE(扣非, %)"),
    ("roa", "ROA(%)"),
    ("roic", "投入资本回报率(%)"),
    ("debt_to_assets", "资产负债率(%)"),
    ("current_ratio", "流动比率"),
    ("quick_ratio", "速动比率"),
    ("assets_turn", "总资产周转率"),
    ("ar_turn", "应收账款周转率"),
    ("inv_turn", "存货周转率"),
    ("interestdebt", "有息负债(元)"),
    ("netdebt", "净负债(元)"),
    ("ocf_to_or", "经营性现金流 / 营业收入"),
    ("debt_to_eqt", "产权比率"),
    ("dt_eps", "稀释 EPS(元/股)"),
    ("bps", "每股净资产"),
    ("q_roe", "本季度 ROE(%)"),
    ("q_netprofit_margin", "本季度净利率(%)"),
    ("q_gsprofit_margin", "本季度毛利率(%)"),
    ("q_op_qoq", "本季度营业利润环比(%)"),
    ("q_netprofit_yoy", "本季度净利 YoY(%)"),
]


# ---------- 工具函数 ----------

def _fmt_value(v, unit: str = "yi") -> str:
    """统一格式化数值。yi=亿元 / wan=万元 / wanshares=万股 / raw=原值"""
    if v is None or pd.isna(v):
        return "–"
    if unit == "yi":
        return f"{v / 1e8:.4f} 亿"
    if unit == "wan":
        return f"{v / 1e4:,.2f} 万"
    if unit == "wanshares":
        return f"{v / 1e4:,.2f} 万股"
    if unit == "pct":
        return f"{v:.2f}%"
    if unit == "raw":
        if isinstance(v, float):
            return f"{v:.4f}".rstrip("0").rstrip(".")
        return str(v)
    return str(v)


def _fmt_pct(v) -> str:
    if v is None or pd.isna(v):
        return "–"
    return f"{v:+.2f}%"


def _fmt_yoy(curr: float, prev: float) -> str:
    if curr is None or prev is None or pd.isna(curr) or pd.isna(prev) or prev == 0:
        return "–"
    return f"{(curr / prev - 1) * 100:+.2f}%"


def _read_parquet_safe(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_parquet(path)
    except Exception as e:
        sys.stderr.write(f"[data_snapshot] 读取 {path.name} 失败: {e}\n")
        return pd.DataFrame()


def _latest_row(df: pd.DataFrame, date_col: str = "end_date") -> Optional[pd.Series]:
    if df.empty or date_col not in df.columns:
        return None
    df_sorted = df.dropna(subset=[date_col]).sort_values(date_col, ascending=False)
    if df_sorted.empty:
        return None
    return df_sorted.iloc[0]


def _all_periods(df: pd.DataFrame, date_col: str = "end_date") -> list[str]:
    if df.empty or date_col not in df.columns:
        return []
    return sorted(df[date_col].dropna().unique().tolist(), reverse=True)


# ---------- 各 section 渲染 ----------

def _render_section_1(bundle_dir: Path, out: StringIO):
    """§1 数据完整度 + 各表最新期"""
    out.write("## §1 数据完整度 (Phase 3 必读: 验证最新数据已采集)\n\n")
    out.write("| 表 | 行数 | end_date 区间 | **最新期(★ Phase 3 必含)** |\n")
    out.write("|---|---:|:---:|:---:|\n")

    tables = [
        "income", "balancesheet", "cashflow", "fina_indicator",
        "daily", "daily_basic",
        "top10_holders", "top10_floatholders", "pledge_detail",
        "forecast_vip", "express_vip", "stk_holdernumber",
        "fina_mainbz", "dividend", "repurchase",
    ]
    latest_periods = {}
    for tbl in tables:
        df = _read_parquet_safe(bundle_dir / f"{tbl}.parquet")
        if df.empty:
            out.write(f"| {tbl} | 0 | – | – |\n")
            continue
        date_col = "end_date" if "end_date" in df.columns else (
            "trade_date" if "trade_date" in df.columns else "ann_date" if "ann_date" in df.columns else None
        )
        if date_col is None:
            out.write(f"| {tbl} | {len(df)} | (无日期列) | – |\n")
            continue
        periods = sorted(df[date_col].dropna().unique().tolist(), reverse=True)
        if not periods:
            out.write(f"| {tbl} | {len(df)} | – | – |\n")
            continue
        latest = periods[0]
        latest_periods[tbl] = latest
        period_range = f"{periods[-1]} ~ {periods[0]}" if len(periods) > 1 else str(periods[0])
        out.write(f"| {tbl} | {len(df)} | {period_range} | **{latest}** |\n")

    out.write("\n")
    return latest_periods


def _render_section_2(bundle_dir: Path, latest_periods: dict, out: StringIO):
    """§2 最新期完整快照"""
    out.write("## §2 最新期完整快照\n\n")

    income = _read_parquet_safe(bundle_dir / "income.parquet")
    bs = _read_parquet_safe(bundle_dir / "balancesheet.parquet")
    cf = _read_parquet_safe(bundle_dir / "cashflow.parquet")
    fi = _read_parquet_safe(bundle_dir / "fina_indicator.parquet")

    # 2.1 利润表
    out.write(f"### 2.1 利润表关键科目 (来自 income.parquet 最新行 end_date={latest_periods.get('income','?')})\n\n")
    if not income.empty:
        latest = _latest_row(income)
        prev = None
        # 找上年同期(YoY)
        if latest is not None and "end_date" in income.columns:
            curr_date = str(latest["end_date"])
            try:
                prev_date = str(int(curr_date[:4]) - 1) + curr_date[4:]
                prev_rows = income[income["end_date"] == prev_date]
                prev = prev_rows.iloc[0] if len(prev_rows) else None
            except (ValueError, TypeError):
                prev = None
        out.write("| 科目 | 最新期数值 | 上年同期 | YoY |\n|---|---:|---:|:---:|\n")
        for col, label, unit in INCOME_KEY_FIELDS:
            if latest is None or col not in latest.index:
                continue
            curr_v = latest[col]
            prev_v = prev[col] if (prev is not None and col in prev.index) else None
            yoy = _fmt_yoy(curr_v, prev_v) if (curr_v is not None and prev_v is not None) else "–"
            out.write(f"| {label} | {_fmt_value(curr_v, unit)} | {_fmt_value(prev_v, unit)} | {yoy} |\n")
    out.write("\n")

    # 2.2 资产负债表
    out.write(f"### 2.2 资产负债表关键科目 (来自 balancesheet.parquet 最新行 end_date={latest_periods.get('balancesheet','?')})\n\n")
    if not bs.empty:
        latest = _latest_row(bs)
        prev = None
        if latest is not None and "end_date" in bs.columns:
            curr_date = str(latest["end_date"])
            # 上年同期
            try:
                prev_date = str(int(curr_date[:4]) - 1) + curr_date[4:]
                prev_rows = bs[bs["end_date"] == prev_date]
                prev = prev_rows.iloc[0] if len(prev_rows) else None
            except (ValueError, TypeError):
                pass
        out.write("| 科目 | 最新期数值 | 上年同期 | YoY |\n|---|---:|---:|:---:|\n")
        for col, label, unit in BALANCE_KEY_FIELDS:
            if latest is None or col not in latest.index:
                continue
            curr_v = latest[col]
            prev_v = prev[col] if (prev is not None and col in prev.index) else None
            yoy = _fmt_yoy(curr_v, prev_v) if (curr_v is not None and prev_v is not None) else "–"
            out.write(f"| {label} | {_fmt_value(curr_v, unit)} | {_fmt_value(prev_v, unit)} | {yoy} |\n")
    out.write("\n")

    # 2.3 现金流
    out.write(f"### 2.3 现金流量表 (来自 cashflow.parquet 最新行 end_date={latest_periods.get('cashflow','?')})\n\n")
    if not cf.empty:
        latest = _latest_row(cf)
        prev = None
        if latest is not None and "end_date" in cf.columns:
            curr_date = str(latest["end_date"])
            try:
                prev_date = str(int(curr_date[:4]) - 1) + curr_date[4:]
                prev_rows = cf[cf["end_date"] == prev_date]
                prev = prev_rows.iloc[0] if len(prev_rows) else None
            except (ValueError, TypeError):
                pass
        out.write("| 科目 | 最新期数值 | 上年同期 | YoY |\n|---|---:|---:|:---:|\n")
        for col, label, unit in CASHFLOW_KEY_FIELDS:
            if latest is None or col not in latest.index:
                continue
            curr_v = latest[col]
            prev_v = prev[col] if (prev is not None and col in prev.index) else None
            yoy = _fmt_yoy(curr_v, prev_v) if (curr_v is not None and prev_v is not None) else "–"
            out.write(f"| {label} | {_fmt_value(curr_v, unit)} | {_fmt_value(prev_v, unit)} | {yoy} |\n")
    out.write("\n")

    # 2.4 fina_indicator
    out.write(f"### 2.4 财务指标 (来自 fina_indicator.parquet 最新行 end_date={latest_periods.get('fina_indicator','?')})\n\n")
    if not fi.empty:
        latest = _latest_row(fi)
        out.write("| 指标 | 数值 |\n|---|---:|\n")
        for col, label in FINA_KEY_FIELDS:
            if latest is not None and col in latest.index and pd.notna(latest[col]):
                v = latest[col]
                out.write(f"| {label} | {v:.4f} |\n" if isinstance(v, float) else f"| {label} | {v} |\n")
    out.write("\n")


def _render_section_3(bundle_dir: Path, out: StringIO):
    """§3 多年趋势完整表"""
    out.write("## §3 多年趋势完整表 (★ 主报告 §四 财务趋势表必须 inline 全部行)\n\n")

    income = _read_parquet_safe(bundle_dir / "income.parquet")
    fi = _read_parquet_safe(bundle_dir / "fina_indicator.parquet")
    cf = _read_parquet_safe(bundle_dir / "cashflow.parquet")
    bs = _read_parquet_safe(bundle_dir / "balancesheet.parquet")

    if income.empty:
        out.write("(income.parquet 为空, 跳过)\n\n")
        return

    # 取所有 distinct end_date
    periods = sorted(income["end_date"].dropna().unique().tolist(), reverse=True)
    if not periods:
        out.write("(无可用 end_date)\n\n")
        return

    out.write("| 期末 | 营收(亿) | 营收 YoY | 毛利率% | 净利率% | 归母净利(亿) | 净利 YoY | 加权 ROE% | 资产负债率% | OCF(亿) |\n")
    out.write("|:---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|\n")

    # 去重: 重复 end_date 取第一个 (通常 ann_date 最新或 report_type 标准的)
    income_idx = income.drop_duplicates(subset="end_date").set_index("end_date") if "end_date" in income.columns else pd.DataFrame()
    fi_idx = fi.drop_duplicates(subset="end_date").set_index("end_date") if (not fi.empty and "end_date" in fi.columns) else pd.DataFrame()
    cf_idx = cf.drop_duplicates(subset="end_date").set_index("end_date") if (not cf.empty and "end_date" in cf.columns) else pd.DataFrame()
    bs_idx = bs.drop_duplicates(subset="end_date").set_index("end_date") if (not bs.empty and "end_date" in bs.columns) else pd.DataFrame()

    for i, period in enumerate(periods):
        # 当期
        rev = income_idx.loc[period, "revenue"] if period in income_idx.index else None
        ni = income_idx.loc[period, "n_income_attr_p"] if period in income_idx.index else None
        # 上年同期 YoY
        try:
            prev_p = str(int(period[:4]) - 1) + period[4:]
        except (ValueError, TypeError):
            prev_p = None
        prev_rev = income_idx.loc[prev_p, "revenue"] if (prev_p and prev_p in income_idx.index) else None
        prev_ni = income_idx.loc[prev_p, "n_income_attr_p"] if (prev_p and prev_p in income_idx.index) else None
        # fina_indicator
        fi_row = fi_idx.loc[period] if period in fi_idx.index else None
        gross = fi_row["grossprofit_margin"] if fi_row is not None and "grossprofit_margin" in fi_row else None
        netm = fi_row["netprofit_margin"] if fi_row is not None and "netprofit_margin" in fi_row else None
        roe = fi_row["roe"] if fi_row is not None and "roe" in fi_row else None
        d2a = fi_row["debt_to_assets"] if fi_row is not None and "debt_to_assets" in fi_row else None
        # 现金流
        ocf = cf_idx.loc[period, "n_cashflow_act"] if period in cf_idx.index else None

        row = [
            period,
            f"{rev/1e8:.2f}" if rev is not None and pd.notna(rev) else "–",
            _fmt_yoy(rev, prev_rev),
            f"{gross:.2f}" if gross is not None and pd.notna(gross) else "–",
            f"{netm:.2f}" if netm is not None and pd.notna(netm) else "–",
            f"{ni/1e8:.4f}" if ni is not None and pd.notna(ni) else "–",
            _fmt_yoy(ni, prev_ni),
            f"{roe:.2f}" if roe is not None and pd.notna(roe) else "–",
            f"{d2a:.2f}" if d2a is not None and pd.notna(d2a) else "–",
            f"{ocf/1e8:.4f}" if ocf is not None and pd.notna(ocf) else "–",
        ]
        out.write("| " + " | ".join(row) + " |\n")
    out.write(f"\n*共 {len(periods)} 期, 主报告 §四 财务趋势表必须 inline 全部行 (尤其最新期 {periods[0]}); 严禁省略最新季度。*\n\n")


def _render_section_4(bundle_dir: Path, out: StringIO):
    """§4 业绩预告 vs 实际兑现对比"""
    out.write("## §4 业绩预告 vs 实际兑现对比 (★ 若 actual 已存在, 主报告必须用 actual, 禁止用预告口径)\n\n")

    forecast = _read_parquet_safe(bundle_dir / "forecast_vip.parquet")
    income = _read_parquet_safe(bundle_dir / "income.parquet")

    if forecast.empty:
        out.write("(无业绩预告数据)\n\n")
        return

    forecast = forecast.drop_duplicates(subset=["ann_date", "end_date"]).sort_values("ann_date", ascending=False).head(15)

    if not income.empty and "end_date" in income.columns:
        income_idx = income.set_index("end_date")
    else:
        income_idx = pd.DataFrame()

    out.write("| 公告日 | 报告期 | 类型 | 预告净利区间(万) | **实际归母净利(★ income)** | 兑现状态 |\n")
    out.write("|:---:|:---:|:---:|---:|---:|:---:|\n")

    for _, row in forecast.iterrows():
        ann = row.get("ann_date", "?")
        end = str(row.get("end_date", "?"))
        ftype = row.get("type", "?")
        npmin = row.get("net_profit_min")
        npmax = row.get("net_profit_max")
        forecast_range = f"{npmin:,.0f} ~ {npmax:,.0f}" if pd.notna(npmin) and pd.notna(npmax) else "–"
        # 查 income 同 end_date 的 actual
        actual = None
        if end in income_idx.index:
            try:
                actual = income_idx.loc[end, "n_income_attr_p"]
                if hasattr(actual, "iloc"):  # 防止重复 end_date 返回 Series
                    actual = actual.iloc[0]
            except (KeyError, IndexError):
                actual = None
        actual_str = f"**{actual/1e4:,.2f} 万**" if (actual is not None and pd.notna(actual)) else "未发布 / 待披露"
        # 兑现状态
        status = "未发布"
        if actual is not None and pd.notna(actual) and pd.notna(npmin) and pd.notna(npmax):
            actual_wan = actual / 1e4
            if actual_wan < npmin:
                status = f"⬇️ 低于预告下沿 ({(actual_wan/npmin-1)*100:+.1f}%)"
            elif actual_wan > npmax:
                status = f"⬆️ 高于预告上沿 ({(actual_wan/npmax-1)*100:+.1f}%)"
            else:
                status = "✅ 落入区间"
        out.write(f"| {ann} | {end} | {ftype} | {forecast_range} | {actual_str} | {status} |\n")
    out.write('\n*★ 强制规则: 若某期 income.parquet 已有 actual 数据(上表实际栏非 "待披露"), 主报告 §四 财务趋势表 + §一 执行摘要 必须用 actual 而非预告区间。*\n\n')


def _render_section_5_or_6(bundle_dir: Path, out: StringIO, parquet_name: str, title: str, n_periods: int = 4):
    """§5 / §6 完整十大股东表 (最近 N 期, 各 10 行)"""
    out.write(f"## {title}\n\n")
    df = _read_parquet_safe(bundle_dir / f"{parquet_name}.parquet")
    if df.empty:
        out.write("(无数据)\n\n")
        return

    periods = sorted(df["end_date"].dropna().unique().tolist(), reverse=True)[:n_periods]
    if not periods:
        out.write("(无可用 end_date)\n\n")
        return

    for period in periods:
        out.write(f"### 报告期: {period}\n\n")
        sub = df[df["end_date"] == period].sort_values("hold_ratio", ascending=False).head(10)
        if sub.empty:
            out.write("(本期无数据)\n\n")
            continue
        out.write("| # | 股东 | 持股数(万股) | 持股比例(%) | 占流通比例(%) | 期间变动(万股) | 股东类型 |\n")
        out.write("|---|---|---:|---:|---:|---:|:---:|\n")
        for i, (_, r) in enumerate(sub.iterrows(), 1):
            name = str(r.get("holder_name", "–"))
            amt = r.get("hold_amount")
            ratio = r.get("hold_ratio")
            float_ratio = r.get("hold_float_ratio")
            chg = r.get("hold_change")
            htype = r.get("holder_type", "–")
            out.write(
                f"| {i} | {name} | "
                f"{amt/1e4:,.2f} | " if pd.notna(amt) else f"| {i} | {name} | – | "
            )
            out.write(
                f"{ratio:.2f} | " if pd.notna(ratio) else "– | "
            )
            out.write(
                f"{float_ratio:.2f} | " if pd.notna(float_ratio) else "– | "
            )
            out.write(
                f"{chg/1e4:+,.2f} | " if pd.notna(chg) else "– | "
            )
            out.write(f"{htype} |\n")
        out.write("\n")
    out.write(f"*共 {len(periods)} 期 × ≤10 行/期。主报告 §四 主力控盘 / 十大股东子节必须 inline ≥ 1 期 ≥ 9 行 (推荐至少 2 期对比展示变动)。*\n\n")


def _render_section_7(bundle_dir: Path, out: StringIO):
    """§7 质押 / 冻结明细"""
    out.write("## §7 质押 / 冻结明细 (active 状态)\n\n")
    df = _read_parquet_safe(bundle_dir / "pledge_detail.parquet")
    if df.empty:
        out.write("(无质押数据)\n\n")
        return

    # 优先 active(未释放), 否则全部
    if "is_release" in df.columns:
        active = df[df["is_release"].isin(["N", "0", 0, False, "否", "未解除"])]
        if active.empty:
            active = df.copy()
    else:
        active = df.copy()

    active = active.sort_values("start_date", ascending=False).head(30)
    out.write(f"**总记录: {len(df)} 条; 显示 active / 最近 {len(active)} 条**\n\n")
    out.write("| 公告日 | 股东 | 质押方 | 起始日 | 期末日 | 质押数(万股) | 占持股% | 占总股本% | 状态 |\n")
    out.write("|:---:|---|---|:---:|:---:|---:|---:|---:|:---:|\n")
    for _, r in active.iterrows():
        ann = r.get("ann_date", "–")
        name = r.get("holder_name", "–")
        pledgor = r.get("pledgor", "–")
        start = r.get("start_date", "–")
        end = r.get("end_date", "–")
        amt = r.get("pledge_amount")
        ptotal = r.get("p_total_ratio")
        htotal = r.get("h_total_ratio")
        is_rel = r.get("is_release", "–")
        status = "已解除" if is_rel in ("Y", "1", 1, True, "是") else "active"
        out.write(
            f"| {ann} | {name} | {pledgor} | {start} | {end} | "
            f"{amt/1e4:,.2f} | " if pd.notna(amt) else f"| {ann} | {name} | {pledgor} | {start} | {end} | – | "
        )
        out.write(f"{ptotal:.2f} | " if pd.notna(ptotal) else "– | ")
        out.write(f"{htotal:.2f} | " if pd.notna(htotal) else "– | ")
        out.write(f"{status} |\n")
    out.write("\n*★ 主报告 §四 主力控盘子节必须引用此表 (若 active 记录非空); §三 致命看空快筛 #3 大股东累计质押 > 50% 检查源头。*\n\n")


def _render_section_8(bundle_dir: Path, out: StringIO):
    """§8 股东户数变化时序"""
    out.write("## §8 股东户数变化时序\n\n")
    df = _read_parquet_safe(bundle_dir / "stk_holdernumber.parquet")
    if df.empty:
        out.write("(无户数数据)\n\n")
        return

    df = df.sort_values("end_date", ascending=False)
    out.write("| 报告期 | 户数 | 环比 |\n|:---:|---:|:---:|\n")
    prev = None
    rows_buf = []
    for _, r in df.iterrows():
        ed = r.get("end_date", "–")
        n = r.get("holder_num")
        rows_buf.append((ed, n))

    # 按降序展示, 但环比要按时间正序计算
    for i, (ed, n) in enumerate(rows_buf):
        if i + 1 < len(rows_buf):
            prev_n = rows_buf[i + 1][1]
            chg = f"{(n / prev_n - 1) * 100:+.2f}%" if (pd.notna(n) and pd.notna(prev_n) and prev_n != 0) else "–"
        else:
            chg = "–"
        out.write(f"| {ed} | {n:,.0f} | {chg} |\n" if pd.notna(n) else f"| {ed} | – | {chg} |\n")
    out.write("\n*★ 户数变化是主力吸筹/出货的核心信号: 户数↓ + 户均↑ = 机构吸筹; 户数↑ + 户均↓ = 机构退出 (capital_flow.md §3 已自动判定)。*\n\n")


# ---------- 主入口 ----------

def build_snapshot(bundle_dir: Path, ts_code: str = "", company: str = "") -> str:
    """从 raw_data parquet 拼装 data_snapshot.md 全文"""
    out = StringIO()

    # 文件头 + Phase 3 强制规则
    today = dt.date.today().strftime("%Y-%m-%d")
    out.write(f"# 数据快照: {company or 'company'} ({ts_code or 'ticker'})\n\n")
    out.write(f"**生成日期**: {today}\n")
    out.write(f"**数据源**: `{bundle_dir}` (Tushare parquet)\n\n")
    out.write("> ★ **Phase 3 必读规则**: 本 artifact 为主报告 §四 公司基本面 / §九 估值 / "
              "§十一 治理 等章节的**唯一**财务和股东数据源。Phase 3 LLM 必须把 §3 多年趋势完整表、"
              "§5/§6 十大股东表 inline 完整搬入主报告对应章节, **严禁** \"同上\"/\"余略\"/"
              "\"详见附件\" 等省略性写法。**若 §4 forecast vs actual 表显示 actual 已存在, "
              "主报告必须用 actual 数据, 禁止用预告区间口径。**\n\n")
    out.write("---\n\n")

    # §1
    latest_periods = _render_section_1(bundle_dir, out)
    out.write("---\n\n")

    # §2
    _render_section_2(bundle_dir, latest_periods, out)
    out.write("---\n\n")

    # §3
    _render_section_3(bundle_dir, out)
    out.write("---\n\n")

    # §4
    _render_section_4(bundle_dir, out)
    out.write("---\n\n")

    # §5
    _render_section_5_or_6(bundle_dir, out, "top10_holders", "§5 完整十大股东表 (最近 4 期)")
    out.write("---\n\n")

    # §6
    _render_section_5_or_6(bundle_dir, out, "top10_floatholders", "§6 完整十大流通股东表 (最近 4 期)")
    out.write("---\n\n")

    # §7
    _render_section_7(bundle_dir, out)
    out.write("---\n\n")

    # §8
    _render_section_8(bundle_dir, out)

    out.write(
        "\n---\n\n"
        "*由 `scripts/data_snapshot.py` 自动生成 (确定性 Python 拼装, LLM 不参与)。"
        "供 Phase 3a 全量预加载 + Phase 3b 分章按需写入直接消费, "
        "解决了反复出现的 \"漏读最新季度数据 / 用预告替代实际 / 十大股东章节简化省略\" 问题。*\n"
    )

    return out.getvalue()


def main():
    ap = argparse.ArgumentParser(description="确定性产出 data_snapshot.md, 修复 Phase 3 数据漏读")
    ap.add_argument("--bundle", required=True, help="raw_data 目录路径")
    ap.add_argument("--out", required=True, help="输出 data_snapshot.md 路径")
    ap.add_argument("--ts-code", default="", help="ts_code (可选, 仅用于头部展示)")
    ap.add_argument("--company", default="", help="公司名 (可选, 仅用于头部展示)")
    args = ap.parse_args()

    bundle = Path(args.bundle)
    if not bundle.exists() or not bundle.is_dir():
        print(f"❌ bundle 目录不存在: {bundle}", file=sys.stderr)
        return 1

    # 尝试从 stock_basic.parquet 读 ts_code / name (若 CLI 未提供)
    ts_code = args.ts_code
    company = args.company
    if not ts_code or not company:
        sb = _read_parquet_safe(bundle / "stock_basic.parquet")
        if not sb.empty:
            if not ts_code:
                ts_code = str(sb.iloc[0].get("ts_code", "")) if "ts_code" in sb.columns else ""
            if not company:
                company = str(sb.iloc[0].get("name", "")) if "name" in sb.columns else ""

    md = build_snapshot(bundle, ts_code=ts_code, company=company)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")

    print(f"✅ data_snapshot.md 已写入 {out_path}")
    print(f"   字符数: {len(md):,}")
    # 自检: 关键章节是否都生成
    sections = ["§1 数据完整度", "§2 最新期完整快照", "§3 多年趋势完整表",
                "§4 业绩预告 vs 实际兑现", "§5 完整十大股东表", "§6 完整十大流通股东表",
                "§7 质押", "§8 股东户数变化"]
    missing = [s for s in sections if s not in md]
    if missing:
        print(f"   ⚠️  缺失章节: {missing}")
        return 2
    print(f"   ✅ 8 个核心章节齐全")
    return 0


if __name__ == "__main__":
    sys.exit(main())
