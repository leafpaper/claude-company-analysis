"""A 股主力控盘与资金流向分析 (v4.4 新增).

解决痛点: A 股投资者最关心"流动盘有没有问题 / 机构主力是不是在控盘",
但之前 skill 只粗用了 top10_holders + stk_holdernumber 两个信号,
完全没消费陆股通 / 两融 / 龙虎榜 / 大单资金流等控盘证据.

本模块拉 6 个 Tushare 接口 (2000+ 积分门槛, 用户 5000 积分完全够) 并推导
6 个综合控盘指标, 生成 capital_flow.md.

数据接口:
1. moneyflow         - 个股每日资金流向 (超大单/大单/中单/小单)
2. moneyflow_hsgt    - 陆股通/沪深股通整体 (大盘层面)
3. hk_hold           - 陆股通个股持股每日明细
4. margin_detail     - 个股两融每日明细
5. top_list          - 龙虎榜上榜记录
6. top_inst          - 龙虎榜机构席位买卖明细

推导指标:
1. 主力控盘度    - 前十大流通股东占流通股本比例
2. 筹码集中度   - 户数 × 户均持股 2×2 矩阵变化
3. 北向资金趋势 - 陆股通持股比例 60/20 日变化
4. 两融杠杆方向 - 融资余额占流通市值分位
5. 主力资金流  - 近 20 日超大单+大单净流入天数占比
6. 机构席位活跃 - 近 30 日龙虎榜机构上榜次数

Usage:
    python3 -m scripts.capital_flow 600745.SH --days 60 \\
        --out output/闻泰科技/capital_flow.md
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import Any

import pandas as pd

from . import config
from .tushare_collector import TushareCollector, normalize_a_code


def _latest_n_trade_dates(tc: TushareCollector, n: int = 60) -> list[str]:
    """从今天倒推找最近 n 个交易日 (用 trade_cal 接口)."""
    today = dt.date.today()
    start = today - dt.timedelta(days=int(n * 1.7))  # 有周末需要放宽
    try:
        cal = tc._pro.trade_cal(
            exchange="SSE",
            start_date=start.strftime("%Y%m%d"),
            end_date=today.strftime("%Y%m%d"),
            is_open="1",
        )
        dates = sorted(cal["cal_date"].tolist(), reverse=True)
        return dates[:n]
    except Exception:
        # fallback: 简单按 ±2 填充
        return [(today - dt.timedelta(days=i)).strftime("%Y%m%d") for i in range(n)]


def _safe_call(fn, **kwargs) -> pd.DataFrame:
    """接口失败 / 无权限时返回空 df 而非抛异常."""
    try:
        df = fn(**kwargs)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        print(f"[WARN] {fn.__name__} 失败: {e}")
        return pd.DataFrame()


def collect_capital_flow(
    target_code: str,
    days: int = 60,
) -> tuple[dict[str, pd.DataFrame], str]:
    """Returns (raw_data_dict, markdown_report)."""
    target_code = normalize_a_code(target_code)
    tc = TushareCollector()
    tc._ensure_pro()
    pro = tc._pro

    # 日期范围
    end_date = dt.date.today().strftime("%Y%m%d")
    start_date = (dt.date.today() - dt.timedelta(days=int(days * 1.5))).strftime("%Y%m%d")

    raw: dict[str, pd.DataFrame] = {}

    # ---------- 1. 个股主力资金流 ----------
    raw["moneyflow"] = _safe_call(
        pro.moneyflow,
        ts_code=target_code,
        start_date=start_date,
        end_date=end_date,
    )

    # ---------- 2. 陆股通整体 (参考背景) ----------
    raw["moneyflow_hsgt"] = _safe_call(
        pro.moneyflow_hsgt,
        start_date=start_date,
        end_date=end_date,
    )

    # ---------- 3. 陆股通个股持股每日 ----------
    raw["hk_hold"] = _safe_call(
        pro.hk_hold,
        ts_code=target_code,
        start_date=start_date,
        end_date=end_date,
    )

    # ---------- 4. 两融明细 ----------
    raw["margin_detail"] = _safe_call(
        pro.margin_detail,
        ts_code=target_code,
        start_date=start_date,
        end_date=end_date,
    )

    # ---------- 5. 龙虎榜上榜 ----------
    # top_list 需按日期迭代 (每天一调用, 所以只取近 30 日的)
    top_dates = _latest_n_trade_dates(tc, n=30)
    tl_dfs = []
    for d in top_dates:
        df = _safe_call(pro.top_list, trade_date=d, ts_code=target_code)
        if not df.empty:
            tl_dfs.append(df)
    raw["top_list"] = pd.concat(tl_dfs, ignore_index=True) if tl_dfs else pd.DataFrame()

    # ---------- 6. 龙虎榜机构席位 ----------
    ti_dfs = []
    if not raw["top_list"].empty:
        for d in raw["top_list"]["trade_date"].unique():
            df = _safe_call(pro.top_inst, trade_date=d, ts_code=target_code)
            if not df.empty:
                ti_dfs.append(df)
    raw["top_inst"] = pd.concat(ti_dfs, ignore_index=True) if ti_dfs else pd.DataFrame()

    # ---------- 辅助: 拉 top10_floatholders + stk_holdernumber + daily_basic ----------
    raw["top10_float"] = tc.top10_floatholders(target_code, start_year=dt.date.today().year - 1)
    raw["holder_num"] = tc.stk_holdernumber(target_code, start_year=dt.date.today().year - 1)
    raw["daily_basic"] = tc.daily_basic(target_code)
    raw["stock_basic"] = tc.stock_basic(target_code)

    # ---------- 推导指标 ----------
    metrics = _derive_metrics(target_code, raw)

    # ---------- 生成 markdown ----------
    md = _format_markdown(target_code, raw, metrics)

    return raw, md


def _derive_metrics(target_code: str, raw: dict) -> dict[str, Any]:
    m: dict[str, Any] = {}

    # 1. 主力控盘度: 最近期前 10 大流通股东合计占流通股本
    top10f = raw["top10_float"]
    if not top10f.empty:
        latest_ed = top10f["end_date"].max()
        latest = top10f[top10f["end_date"] == latest_ed]
        if "hold_ratio" in latest.columns:
            total_ratio = latest["hold_ratio"].sum()
            m["control_ratio_top10"] = round(total_ratio, 2)
            m["control_period"] = latest_ed

            # 控盘档位
            if total_ratio >= 50:
                m["control_level"] = "🔴 高度控盘"
            elif total_ratio >= 30:
                m["control_level"] = "🟡 中度控盘"
            else:
                m["control_level"] = "🟢 分散"

    # 2. 筹码集中度 2×2 矩阵 (户数变化 × 户均持股变化)
    hn = raw["holder_num"]
    if len(hn) >= 2:
        hn_sorted = hn.sort_values("end_date", ascending=False)
        now = hn_sorted.iloc[0]
        prev = hn_sorted.iloc[1]
        holder_chg = (now["holder_num"] - prev["holder_num"]) / prev["holder_num"]
        m["holder_num_change"] = round(holder_chg * 100, 2)
        m["holder_num_latest"] = int(now["holder_num"])
        m["holder_num_period_current"] = now["end_date"]
        m["holder_num_period_prev"] = prev["end_date"]
        # 户均 = 流通股本 / 户数, 但 stk_holdernumber 不含股本, 用 daily_basic 的 free_share
        db = raw["daily_basic"]
        if not db.empty and "free_share" in db.columns:
            db_latest = db.sort_values("trade_date", ascending=False).iloc[0]
            free_share = db_latest.get("free_share")
            if free_share and now["holder_num"] > 0:
                avg_now = free_share * 10000 / now["holder_num"]  # free_share 单位万股
                avg_prev = free_share * 10000 / prev["holder_num"]  # 近似,用当前流通股反推
                m["avg_holding_now"] = round(avg_now, 0)
                m["avg_holding_change"] = round((avg_now - avg_prev) / avg_prev * 100, 2)

        # 2×2 矩阵判定
        if holder_chg < -0.03:  # 户数 -3%+
            if m.get("avg_holding_change", 0) > 3:
                m["chip_concentration"] = "🟢 筹码集中 (主力吸筹)"
            else:
                m["chip_concentration"] = "🟡 户数减少但户均未升 (待观察)"
        elif holder_chg > 0.05:  # 户数 +5%+
            m["chip_concentration"] = "🔴 筹码分散 (散户涌入, 机构退出)"
        else:
            m["chip_concentration"] = "⚪ 筹码平稳"

    # 3. 陆股通持仓趋势
    hkh = raw["hk_hold"]
    if not hkh.empty and "hold_ratio" in hkh.columns:
        hkh_sorted = hkh.sort_values("trade_date", ascending=False)
        latest_hk_ratio = hkh_sorted.iloc[0]["hold_ratio"]
        m["hsgt_ratio_latest"] = round(float(latest_hk_ratio), 3)
        m["hsgt_date_latest"] = hkh_sorted.iloc[0]["trade_date"]
        # 20 日和 60 日变化
        if len(hkh_sorted) >= 20:
            hk_20 = hkh_sorted.iloc[19]["hold_ratio"]
            m["hsgt_ratio_change_20d"] = round(float(latest_hk_ratio) - float(hk_20), 3)
        if len(hkh_sorted) >= 60:
            hk_60 = hkh_sorted.iloc[59]["hold_ratio"]
            m["hsgt_ratio_change_60d"] = round(float(latest_hk_ratio) - float(hk_60), 3)
        # 方向判定
        chg_20 = m.get("hsgt_ratio_change_20d", 0)
        if chg_20 > 0.3:
            m["hsgt_direction"] = "🟢 外资近 20 日加仓"
        elif chg_20 < -0.3:
            m["hsgt_direction"] = "🔴 外资近 20 日减仓"
        else:
            m["hsgt_direction"] = "⚪ 外资近 20 日平稳"

    # 4. 两融杠杆方向: 融资余额占流通市值分位
    md = raw["margin_detail"]
    if not md.empty and "rzye" in md.columns:
        md_sorted = md.sort_values("trade_date", ascending=False).head(60)
        m["margin_rzye_latest_wan"] = round(float(md_sorted.iloc[0]["rzye"]) / 10000, 2)
        # 相对 60 日中位数
        rzye_values = md_sorted["rzye"].astype(float).tolist()
        if len(rzye_values) >= 20:
            median = sorted(rzye_values)[len(rzye_values) // 2]
            m["margin_vs_median"] = round(
                (rzye_values[0] - median) / median * 100, 2
            ) if median else 0
            if m["margin_vs_median"] > 20:
                m["margin_signal"] = "🔴 两融余额显著高于近 60 日中位数 (杠杆多头拥挤)"
            elif m["margin_vs_median"] < -20:
                m["margin_signal"] = "🟢 两融余额显著低于中位数 (杠杆撤退)"
            else:
                m["margin_signal"] = "⚪ 两融余额平稳"

    # 5. 主力资金流: 近 20 日超大单+大单净流入天数
    mf = raw["moneyflow"]
    if not mf.empty:
        mf_sorted = mf.sort_values("trade_date", ascending=False).head(20)
        # buy_elg_amount 超大单买入, buy_lg_amount 大单买入, 卖出类似
        # 净流入 = (buy_elg + buy_lg) - (sell_elg + sell_lg) - 单位千元
        net_inflow_days = 0
        total_net_inflow = 0
        for _, row in mf_sorted.iterrows():
            try:
                buy_big = float(row.get("buy_elg_amount", 0)) + float(row.get("buy_lg_amount", 0))
                sell_big = float(row.get("sell_elg_amount", 0)) + float(row.get("sell_lg_amount", 0))
                net = buy_big - sell_big
                if net > 0:
                    net_inflow_days += 1
                total_net_inflow += net
            except (ValueError, TypeError):
                continue
        m["main_capital_inflow_days_20"] = net_inflow_days
        m["main_capital_net_20d_wan"] = round(total_net_inflow / 10, 2)  # 千元 → 万元
        m["main_capital_ratio"] = round(net_inflow_days / 20 * 100, 1)
        if net_inflow_days >= 14:
            m["main_capital_signal"] = "🟢 主力资金近 20 日持续净流入"
        elif net_inflow_days <= 6:
            m["main_capital_signal"] = "🔴 主力资金近 20 日持续净流出"
        else:
            m["main_capital_signal"] = "⚪ 主力资金近 20 日拉锯"

    # 6. 龙虎榜机构席位活跃度
    tl = raw["top_list"]
    ti = raw["top_inst"]
    if not tl.empty:
        m["top_list_count_30d"] = len(tl)
        m["top_list_reasons"] = ", ".join(tl["reason"].dropna().astype(str).tolist()[:3])
    else:
        m["top_list_count_30d"] = 0
    if not ti.empty:
        # 计算机构净买入
        if "net_buy" in ti.columns:
            total_inst_net = ti["net_buy"].astype(float).sum()
            m["inst_net_buy_30d_wan"] = round(total_inst_net / 10000, 2)
            if total_inst_net > 0:
                m["inst_signal"] = f"🟢 近 30 日龙虎榜机构净买入 {total_inst_net / 10000:.0f} 万元"
            else:
                m["inst_signal"] = f"🔴 近 30 日龙虎榜机构净卖出 {abs(total_inst_net) / 10000:.0f} 万元"
    else:
        m["inst_signal"] = "⚪ 近 30 日无龙虎榜机构席位上榜"

    return m


def _format_markdown(target_code: str, raw: dict, m: dict) -> str:
    sb = raw["stock_basic"]
    name = sb.iloc[0]["name"] if not sb.empty else target_code

    lines = [
        f"# 主力控盘与资金流向分析: {name} ({target_code})",
        "",
        f"**生成日期**: {dt.date.today().isoformat()}",
        f"**数据窗口**: 近 60 日 (两融/陆股通/主力资金) / 近 30 日 (龙虎榜)",
        "",
        "## §1 控盘综合判定 (Top 一眼可见)",
        "",
        "| 维度 | 信号 | 解读 |",
        "|------|------|------|",
    ]

    # 一键汇总 6 维度
    dims = [
        ("主力控盘度", m.get("control_level"), f"前 10 大流通股东合计 {m.get('control_ratio_top10', 'N/A')}%"),
        ("筹码集中度", m.get("chip_concentration"), f"户数变化 {m.get('holder_num_change', 'N/A')}%"),
        ("陆股通(北向)", m.get("hsgt_direction"), f"持仓 {m.get('hsgt_ratio_latest', 'N/A')}% / 20 日变化 {m.get('hsgt_ratio_change_20d', 'N/A')}pp"),
        ("两融杠杆", m.get("margin_signal"), f"融资余额 {m.get('margin_rzye_latest_wan', 'N/A')} 万元, 相对近 60 日中位 {m.get('margin_vs_median', 'N/A')}%"),
        ("主力资金流", m.get("main_capital_signal"), f"近 20 日净流入天数 {m.get('main_capital_inflow_days_20', 'N/A')} / 20"),
        ("龙虎榜机构", m.get("inst_signal"), f"近 30 日上榜 {m.get('top_list_count_30d', 0)} 次"),
    ]
    for dim, signal, detail in dims:
        lines.append(f"| {dim} | {signal or '数据不足'} | {detail} |")

    # §2 详细: 前十大流通股东
    lines.extend([
        "",
        "## §2 前十大流通股东 (最近期)",
        "",
    ])
    top10f = raw["top10_float"]
    if not top10f.empty:
        latest_ed = top10f["end_date"].max()
        latest = top10f[top10f["end_date"] == latest_ed].copy()
        cols = ["holder_name", "hold_amount", "hold_ratio"]
        available = [c for c in cols if c in latest.columns]
        if available:
            lines.append(f"**披露期**: {latest_ed}")
            lines.append(f"**合计持股比例**: **{m.get('control_ratio_top10', 'N/A')}%**  ({m.get('control_level', '')})")
            lines.append("")
            lines.append("| 股东 | 持股数(万股) | 比例(%) |")
            lines.append("|------|:---:|:---:|")
            for _, row in latest.iterrows():
                name = row.get("holder_name", "-")
                amount = row.get("hold_amount")
                ratio = row.get("hold_ratio")
                try:
                    amount_wan = f"{float(amount) / 10000:,.0f}" if amount else "-"
                except (ValueError, TypeError):
                    amount_wan = "-"
                try:
                    ratio_pct = f"{float(ratio):.2f}" if ratio is not None else "-"
                except (ValueError, TypeError):
                    ratio_pct = "-"
                lines.append(f"| {name} | {amount_wan} | {ratio_pct} |")
    else:
        lines.append("*数据不足*")

    # §3 筹码集中度 2×2
    lines.extend([
        "",
        "## §3 筹码集中度 2×2 矩阵",
        "",
    ])
    if "holder_num_change" in m:
        hn_latest = m.get("holder_num_latest", 0)
        lines.append(f"**当前期**: {m.get('holder_num_period_current')} · 户数 **{hn_latest:,}**")
        lines.append(f"**环比**: {m['holder_num_change']:+.2f}%")
        if "avg_holding_change" in m:
            lines.append(f"**户均持股**: {m['avg_holding_now']:,.0f} 股 · 环比 {m['avg_holding_change']:+.2f}%")
        lines.append("")
        lines.append(f"**判定**: {m.get('chip_concentration', '数据不足')}")
        lines.append("")
        lines.append("> 经典 2×2 矩阵: 户数↓ + 户均↑ = 筹码集中(机构吸筹);  户数↑ + 户均↓ = 筹码分散(机构退出)")
    else:
        lines.append("*户数数据不足 2 期*")

    # §4 陆股通
    lines.extend([
        "",
        "## §4 陆股通(北向)持仓趋势",
        "",
    ])
    hkh = raw["hk_hold"]
    if not hkh.empty:
        lines.append(f"**最新持仓比例**: {m.get('hsgt_ratio_latest', 'N/A')}% ({m.get('hsgt_date_latest', 'N/A')})")
        ch20 = m.get("hsgt_ratio_change_20d")
        ch60 = m.get("hsgt_ratio_change_60d")
        ch20_s = f"{ch20:+.3f}" if isinstance(ch20, (int, float)) else "N/A"
        ch60_s = f"{ch60:+.3f}" if isinstance(ch60, (int, float)) else "N/A"
        lines.append(f"**20 日变化**: {ch20_s} pp · **60 日变化**: {ch60_s} pp")
        lines.append(f"**判定**: {m.get('hsgt_direction', '数据不足')}")
    else:
        lines.append("*陆股通数据不足*")

    # §5 两融
    lines.extend([
        "",
        "## §5 两融杠杆 (融资余额)",
        "",
    ])
    md = raw["margin_detail"]
    if not md.empty:
        rzye = m.get("margin_rzye_latest_wan")
        vs_med = m.get("margin_vs_median")
        rzye_s = f"{rzye:,.0f}" if isinstance(rzye, (int, float)) else "N/A"
        vs_med_s = f"{vs_med:+.1f}" if isinstance(vs_med, (int, float)) else "N/A"
        lines.append(f"**最新融资余额**: {rzye_s} 万元")
        lines.append(f"**相对近 60 日中位数**: {vs_med_s}%")
        lines.append(f"**判定**: {m.get('margin_signal', '数据不足')}")
    else:
        lines.append("*两融数据不足*")

    # §6 主力资金
    lines.extend([
        "",
        "## §6 主力资金流向 (近 20 日)",
        "",
    ])
    mf = raw["moneyflow"]
    if not mf.empty:
        net_wan = m.get("main_capital_net_20d_wan")
        net_wan_s = f"{net_wan:+,.0f}" if isinstance(net_wan, (int, float)) else "N/A"
        lines.append(f"**近 20 日主力净流入天数**: {m.get('main_capital_inflow_days_20', 'N/A')} / 20 ({m.get('main_capital_ratio', 'N/A')}%)")
        lines.append(f"**净流入累计**: {net_wan_s} 万元")
        lines.append(f"**判定**: {m.get('main_capital_signal', '数据不足')}")
        lines.append("")
        lines.append("> 口径: 主力 = 超大单 + 大单 (`buy_elg_amount + buy_lg_amount`)  ·  散户 = 中小单  ·  净流入 > 0 表示主力净买入")
    else:
        lines.append("*主力资金流数据不足*")

    # §7 龙虎榜
    lines.extend([
        "",
        "## §7 龙虎榜与机构席位 (近 30 日)",
        "",
    ])
    tl = raw["top_list"]
    if not tl.empty:
        lines.append(f"**上榜次数**: {len(tl)} 次")
        if "reason" in tl.columns:
            reasons = tl["reason"].dropna().astype(str).tolist()[:5]
            lines.append(f"**上榜原因** (Top 5): {'; '.join(reasons)}")
        lines.append("")
        lines.append(f"**机构席位**: {m.get('inst_signal', '数据不足')}")
    else:
        lines.append("*近 30 日未上榜龙虎榜*")

    # §8 综合控盘警示
    lines.extend([
        "",
        "## §8 综合控盘警示 (供 Phase 3 §四 / §七 消费)",
        "",
    ])
    warnings = []

    # 规则触发
    if m.get("control_ratio_top10", 0) >= 50:
        warnings.append("🔴 **高度控盘** — 前十大流通股东 ≥50%,股价易被大股东影响,流动性风险需评估")
    if "筹码分散" in str(m.get("chip_concentration", "")):
        warnings.append("🔴 **筹码分散** — 户数增加 >5%,散户涌入,机构可能正在退出")
    if "筹码集中" in str(m.get("chip_concentration", "")):
        warnings.append("🟢 **筹码集中** — 户数减少 + 户均持股上升,机构可能在吸筹")
    if m.get("hsgt_ratio_change_20d", 0) < -0.5:
        warnings.append(f"🔴 **外资撤离** — 陆股通 20 日减仓 {m['hsgt_ratio_change_20d']:.2f}pp")
    if m.get("hsgt_ratio_change_20d", 0) > 0.5:
        warnings.append(f"🟢 **外资加仓** — 陆股通 20 日加仓 +{m['hsgt_ratio_change_20d']:.2f}pp")
    if m.get("main_capital_inflow_days_20", 10) <= 6:
        warnings.append("🔴 **主力资金撤退** — 近 20 日超大单+大单净流入天数 ≤6 日")
    if m.get("main_capital_inflow_days_20", 10) >= 14:
        warnings.append("🟢 **主力资金吸筹** — 近 20 日超大单+大单净流入天数 ≥14 日")
    if m.get("margin_vs_median", 0) > 30:
        warnings.append(f"⚠️ **两融杠杆拥挤** — 融资余额较近 60 日中位数高 {m['margin_vs_median']:.0f}%,若股价回调可能连锁平仓")

    if warnings:
        for w in warnings:
            lines.append(f"- {w}")
    else:
        lines.append("- ℹ️ 无显著控盘/资金异常信号 (6 维度均在中性区间)")

    lines.extend([
        "",
        "---",
        "",
        f"*由 `scripts/capital_flow.py` 自动生成*",
        f"*数据源: Tushare (moneyflow / hk_hold / margin_detail / top_list / top_inst / top10_floatholders / stk_holdernumber)*",
        f"*供 Phase 3 §四 公司基本面的 `### 主力控盘与筹码分析` 子节 + §七 网络舆情的 `### 资金流向信号` 子节消费*",
    ])

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="A 股主力控盘与资金流向分析 (v4.4)")
    ap.add_argument("ts_code", help="A 股代码")
    ap.add_argument("--days", type=int, default=60, help="数据窗口 (默认 60 日)")
    ap.add_argument("--out", help="输出 md 路径")
    args = ap.parse_args()

    try:
        raw, md = collect_capital_flow(args.ts_code, days=args.days)
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback; traceback.print_exc()
        return 1

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"✅ capital_flow 已写入 {out}")
        # 统计
        non_empty = [k for k, df in raw.items() if not df.empty]
        print(f"   接口命中: {len(non_empty)} / {len(raw)}")
        for k in raw:
            status = "✓" if not raw[k].empty else "✗"
            print(f"   [{status}] {k}: {len(raw[k])} 行")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
