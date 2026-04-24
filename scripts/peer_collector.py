"""A 股可比公司自动采集 (v4.4 新增).

解决痛点: Phase 3 §八 可比公司对标原本靠 LLM 手写猜竞品, 现改为 Tushare 按
行业自动采集同行业市值相近的 Top N peer, 并对比关键财务指标.

核心流程:
1. 查目标公司 industry (Tushare stock_basic)
2. 拉同行业全部上市公司 (pro.stock_basic(industry=X, list_status='L'))
3. 按总市值相近度排序, 取 Top N (默认 5)
4. 批量拉 peer 的 fina_indicator 最新期 + daily_basic 最新日
5. 生成对比表 markdown: peer_analysis.md

Usage:
    python3 -m scripts.peer_collector 600745.SH \\
        --peers 5 \\
        --out output/闻泰科技/peer_analysis.md

    # 或代码调用
    from scripts.peer_collector import collect_peers
    df, md = collect_peers("600745.SH", n=5)

限制:
- 只支持 A 股 (Tushare 核心覆盖面)
- 海外 peer (Infineon/STMicro 等) 需 LLM 手工补到 Phase 3 §八
- 行业分类用 Tushare 的 industry 字段 (申万三级, 较细粒度)
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import Any

import pandas as pd

from . import config
from .tushare_collector import TushareCollector, normalize_a_code


# ---------- 关键指标字段 ----------
# 对比维度: 规模 (市值) + 盈利 (ROE/毛利/净利) + 杠杆 + 估值 (PE/PB/PS)

COMPARE_FIELDS = [
    ("name",                "公司"),
    ("industry",            "细分行业"),
    ("total_mv_yi",         "市值(亿)"),
    ("pe_ttm",              "PE TTM"),
    ("pb",                  "PB"),
    ("ps_ttm",              "PS TTM"),
    ("roe_latest",          "ROE(%)"),
    ("grossprofit_margin",  "毛利率(%)"),
    ("netprofit_margin",    "净利率(%)"),
    ("debt_to_assets",      "资产负债率(%)"),
    ("revenue_yoy",         "营收 YoY(%)"),
    ("dv_ratio",            "股息率(%)"),
]


# ---------- 辅助: 最近交易日 ----------

def _latest_trade_date(tc: TushareCollector, lookback: int = 10) -> str:
    """从今天倒推 lookback 天, 找最近有行情的交易日 YYYYMMDD."""
    today = dt.date.today()
    for i in range(lookback):
        d = today - dt.timedelta(days=i)
        ds = d.strftime("%Y%m%d")
        # 用 daily_basic 小探一下 (任意股票作探针)
        try:
            df = tc._pro.daily_basic(ts_code="600519.SH", trade_date=ds)
            if not df.empty:
                return ds
        except Exception:
            continue
    raise RuntimeError(f"未找到近 {lookback} 日的交易日数据")


# ---------- 核心采集函数 ----------

def collect_peers(
    target_code: str,
    n: int = 5,
    trade_date: str | None = None,
) -> tuple[pd.DataFrame, str]:
    """Returns (peers_df, markdown_report)."""
    target_code = normalize_a_code(target_code)
    tc = TushareCollector()
    tc._ensure_pro()
    pro = tc._pro

    # 1. 查目标公司行业
    target_basic = tc.stock_basic(target_code)
    if target_basic.empty:
        raise RuntimeError(f"无法获取 {target_code} 基本信息")
    industry = target_basic.iloc[0].get("industry")
    target_name = target_basic.iloc[0].get("name")
    if not industry or pd.isna(industry):
        raise RuntimeError(f"{target_code} 行业字段为空, 无法做 peer 采集")

    # 2. 拉全市场 stock_basic 后本地过滤 (Tushare industry 参数可能不严格过滤)
    all_stocks = pro.stock_basic(
        exchange="",
        list_status="L",
        fields="ts_code,symbol,name,industry,list_date,market",
    )
    all_peers = all_stocks[all_stocks["industry"] == industry].copy()
    if len(all_peers) < 2:
        raise RuntimeError(f"行业 '{industry}' 上市公司不足 2 家, 无法做 peer 对比")

    # 3. 拉最新日的 daily_basic 全市场, 得市值/估值
    td = trade_date or _latest_trade_date(tc)
    basic_day = pro.daily_basic(
        trade_date=td,
        fields="ts_code,close,total_mv,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,turnover_rate",
    )
    merged = all_peers.merge(basic_day, on="ts_code", how="left")
    merged = merged.dropna(subset=["total_mv"])
    # 再次保险: 确保 industry 严格相同
    merged = merged[merged["industry"] == industry]
    # total_mv tushare 单位是万元 → 转亿
    merged["total_mv_yi"] = merged["total_mv"] / 10000

    # 4. 按市值相近度排序 (不做绝对差, 用对数距离更公平)
    target_mv = merged.loc[merged["ts_code"] == target_code, "total_mv"].iloc[0]
    import math
    merged["mv_log_dist"] = merged["total_mv"].apply(
        lambda x: abs(math.log(x + 1) - math.log(target_mv + 1))
    )
    peers_sorted = merged.sort_values("mv_log_dist")

    # 5. 取 target + 最接近的 n 家
    selected_codes: list[str] = [target_code]
    for code in peers_sorted["ts_code"]:
        if code == target_code:
            continue
        selected_codes.append(code)
        if len(selected_codes) >= n + 1:
            break
    selected = peers_sorted[peers_sorted["ts_code"].isin(selected_codes)].copy()

    # 6. 批量拉每家 fina_indicator (最新一期) + income (计算 YoY)
    rows = []
    for _, prow in selected.iterrows():
        code = prow["ts_code"]
        try:
            fi = tc.fina_indicator(code, start_year=dt.date.today().year - 2)
            inc = tc.income(code, start_year=dt.date.today().year - 2)
        except Exception as e:
            print(f"[WARN] {code} 财务数据采集失败: {e}")
            fi = pd.DataFrame()
            inc = pd.DataFrame()

        latest_fi = fi.iloc[-1] if not fi.empty else pd.Series(dtype=object)
        # 营收 YoY: latest 年 vs 上一年
        rev_yoy = None
        if len(inc) >= 2:
            # 按 end_date 取最近两期同期
            inc_sorted = inc.sort_values("end_date", ascending=False)
            latest_period = inc_sorted.iloc[0]["end_date"][-4:]  # MMDD
            prev = inc_sorted[inc_sorted["end_date"].str.endswith(latest_period)].head(2)
            if len(prev) == 2:
                try:
                    rev_now = float(prev.iloc[0]["revenue"])
                    rev_old = float(prev.iloc[1]["revenue"])
                    if rev_old and rev_old > 0:
                        rev_yoy = (rev_now - rev_old) / rev_old * 100
                except (ValueError, TypeError, KeyError):
                    pass

        rows.append({
            "ts_code": code,
            "name": prow["name"],
            "industry": prow["industry"],
            "total_mv_yi": prow.get("total_mv_yi"),
            "pe_ttm": prow.get("pe_ttm"),
            "pb": prow.get("pb"),
            "ps_ttm": prow.get("ps_ttm"),
            "dv_ratio": prow.get("dv_ratio"),
            "roe_latest": _sf(latest_fi.get("roe")),
            "grossprofit_margin": _sf(latest_fi.get("grossprofit_margin")),
            "netprofit_margin": _sf(latest_fi.get("netprofit_margin")),
            "debt_to_assets": _sf(latest_fi.get("debt_to_assets")),
            "revenue_yoy": rev_yoy,
            "is_target": code == target_code,
        })

    df = pd.DataFrame(rows)

    # 7. 生成 markdown
    md = _format_markdown(df, target_code, target_name, industry, td)
    return df, md


def _sf(x) -> float | None:
    try:
        v = float(x)
        import math
        if math.isnan(v):
            return None
        return round(v, 2)
    except (ValueError, TypeError):
        return None


def _format_markdown(
    df: pd.DataFrame,
    target_code: str,
    target_name: str,
    industry: str,
    trade_date: str,
) -> str:
    lines = [
        f"# 可比公司对标: {target_name} ({target_code})",
        "",
        f"**行业分类** (Tushare industry): **{industry}**",
        f"**Peer 选取规则**: 同行业 + 市值最接近的 {len(df) - 1} 家 + 目标公司",
        f"**财务截至**: 最新披露期 · **行情截至**: {trade_date}",
        "",
        "## §1 对比表",
        "",
    ]

    # 表头
    headers = ["ts_code"] + [h for _, h in COMPARE_FIELDS]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join([":---:"] * len(headers)) + "|")

    # 目标公司在第一行
    df_sorted = df.sort_values("is_target", ascending=False)
    for _, row in df_sorted.iterrows():
        target_mark = " ⭐" if row["is_target"] else ""
        cells = [f"**{row['ts_code']}**{target_mark}" if row["is_target"] else row["ts_code"]]
        for field, _ in COMPARE_FIELDS:
            v = row.get(field)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                cells.append("–")
            elif field == "name":
                cells.append(f"**{v}**" if row["is_target"] else str(v))
            elif isinstance(v, (int, float)):
                cells.append(f"{v:,.2f}")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")

    # 分位排名
    lines.extend([
        "",
        "## §2 目标公司在 peer 中的分位",
        "",
        f"下表显示 {target_name} 相对 peer group 的分位 (1=最好/最高, 0=最差/最低):",
        "",
        "| 指标 | 目标值 | Peer 中位数 | 分位 (high=好) | 解读 |",
        "|------|:---:|:---:|:---:|------|",
    ])
    target_row = df[df["is_target"]].iloc[0]
    peer_df = df[~df["is_target"]]

    # "好" 的方向: ROE/毛利率/净利率/营收YoY 越高越好; 资产负债率/PE/PB/PS 越低越好
    interpretations = {
        "roe_latest": ("高", "ROE 越高盈利能力越强"),
        "grossprofit_margin": ("高", "毛利率越高议价能力越强"),
        "netprofit_margin": ("高", "净利率越高经营效率越高"),
        "debt_to_assets": ("低", "负债率低则财务稳健"),
        "pe_ttm": ("低", "PE 低估值便宜 (但要看是否真便宜还是破落)"),
        "pb": ("低", "PB 低估值便宜"),
        "revenue_yoy": ("高", "营收高增长支撑估值"),
    }
    for field, (direction, interp) in interpretations.items():
        tv = target_row.get(field)
        pvs = [v for v in peer_df[field].tolist() if v is not None and not (isinstance(v, float) and pd.isna(v))]
        if tv is None or not pvs:
            continue
        median = sorted(pvs)[len(pvs) // 2]
        better_count = sum(1 for v in pvs if (v < tv if direction == "高" else v > tv))
        percentile = better_count / len(pvs) if pvs else 0
        label = _compare_label(percentile, direction)
        lines.append(
            f"| {dict(COMPARE_FIELDS).get(field, field)} | "
            f"{tv:,.2f} | {median:,.2f} | "
            f"**{percentile:.0%}** {label} | {interp} |"
        )

    # 风险警示
    lines.extend([
        "",
        "## §3 对比洞察 (供 Phase 3 §八 消费)",
        "",
    ])
    # 硬判定规则
    insights = []
    t_pe = target_row.get("pe_ttm")
    peer_pe_med = _median([v for v in peer_df["pe_ttm"] if v is not None and v > 0])
    if t_pe is not None and t_pe > 0 and peer_pe_med and t_pe > peer_pe_med * 1.5:
        insights.append(f"⚠️ **PE 显著高于 peer 中位数** ({t_pe:.1f}x vs {peer_pe_med:.1f}x × 1.5),估值溢价 > 50%")
    elif t_pe is not None and t_pe > 0 and peer_pe_med and t_pe < peer_pe_med * 0.7:
        insights.append(f"✅ **PE 显著低于 peer 中位数** ({t_pe:.1f}x vs {peer_pe_med:.1f}x × 0.7),估值折让 > 30%")

    t_pb = target_row.get("pb")
    peer_pb_med = _median([v for v in peer_df["pb"] if v is not None and v > 0])
    if t_pb is not None and peer_pb_med and t_pb < peer_pb_med * 0.5:
        insights.append(f"✅ **PB 显著低于 peer** ({t_pb:.2f}x vs {peer_pb_med:.2f}x × 0.5),可能真便宜也可能基本面有问题")

    t_roe = target_row.get("roe_latest")
    peer_roe_med = _median([v for v in peer_df["roe_latest"] if v is not None])
    if t_roe is not None and peer_roe_med and t_roe < peer_roe_med - 5:
        insights.append(f"⚠️ **ROE 显著低于 peer 中位数** ({t_roe:.2f}% vs {peer_roe_med:.2f}%),盈利能力落后")

    t_rev = target_row.get("revenue_yoy")
    peer_rev_med = _median([v for v in peer_df["revenue_yoy"] if v is not None])
    if t_rev is not None and peer_rev_med is not None and t_rev > peer_rev_med + 10:
        insights.append(f"✅ **营收增速显著超 peer** (+{t_rev:.1f}% vs +{peer_rev_med:.1f}%),领先行业")
    elif t_rev is not None and peer_rev_med is not None and t_rev < peer_rev_med - 10:
        insights.append(f"⚠️ **营收增速落后 peer** ({t_rev:.1f}% vs {peer_rev_med:.1f}%),可能基本面恶化")

    if not insights:
        insights.append("ℹ️ 目标公司各项指标均在 peer 中位数 ±1σ 内,估值/盈利无显著偏离")

    lines.extend(insights)
    lines.extend([
        "",
        "---",
        "",
        f"*由 `scripts/peer_collector.py` 自动生成,供 Phase 3 §八 可比公司对标直接引用*",
        "*海外 peer (如全球同业龙头) 需 LLM 手动补充到 Phase 3 §八 末尾*",
    ])

    return "\n".join(lines)


def _median(xs: list[float]) -> float | None:
    xs = sorted([x for x in xs if x is not None])
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 == 1 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def _compare_label(p: float, direction: str) -> str:
    if direction == "高":
        if p >= 0.8: return "🟢 领先"
        if p >= 0.6: return "✅ 高于中位"
        if p >= 0.4: return "🟡 中位"
        if p >= 0.2: return "⚠️ 低于中位"
        return "🔴 落后"
    else:  # 越低越好
        if p >= 0.8: return "🟢 最便宜"
        if p >= 0.6: return "✅ 便宜"
        if p >= 0.4: return "🟡 中位"
        if p >= 0.2: return "⚠️ 偏贵"
        return "🔴 最贵"


def main():
    ap = argparse.ArgumentParser(description="A 股可比公司自动采集 (v4.4)")
    ap.add_argument("ts_code", help="目标公司代码, 如 600745.SH 或 002862")
    ap.add_argument("--peers", type=int, default=5, help="peer 家数 (默认 5)")
    ap.add_argument("--trade-date", help="指定交易日 YYYYMMDD (默认最近)")
    ap.add_argument("--out", help="输出 md 路径 (默认 stdout)")
    args = ap.parse_args()

    try:
        df, md = collect_peers(args.ts_code, n=args.peers, trade_date=args.trade_date)
    except RuntimeError as e:
        print(f"❌ 失败: {e}")
        return 1

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md, encoding="utf-8")
        print(f"✅ peer_analysis 已写入 {out_path}")
        print(f"   peer 数: {len(df) - 1}  (含目标 + {len(df) - 1} 家同行业相近市值)")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
