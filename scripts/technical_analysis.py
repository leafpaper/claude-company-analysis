"""A 股技术分析模块 (v4.4 新增).

用 `daily.parquet` 里已采集的近 3 年日线数据算经典 TA 指标, 让 Phase 3 §九
估值章节除了基本面锚外还有"技术面位置"参考.

指标覆盖:
- 移动均线 MA5/20/60/120 + 多头/空头排列判定
- MACD (EMA12/26/9 经典参数) + 金叉死叉
- RSI (14 日) + 超买(>70) / 超卖(<30) 区域
- 布林带 BOLL (20 日, 2σ) + 价格位置 (上/中/下轨)
- 成交量异常 (相对 60 日均量的倍数)
- 支撑/阻力 (近 60/120 日最低价/最高价 + 密集成交区)

Usage:
    python3 -m scripts.technical_analysis 600745.SH \\
        --out output/闻泰科技/technical_analysis.md

前置: Phase 1 Step 1 tushare_collector 已跑过, daily.parquet 存在.
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .tushare_collector import normalize_a_code


# ---------- 基础指标计算 ----------

def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(window=n, min_periods=1).mean()


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def _rsi(s: pd.Series, n: int = 14) -> pd.Series:
    delta = s.diff()
    gain = delta.where(delta > 0, 0).rolling(window=n, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=n, min_periods=1).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    return rsi


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns (DIFF, DEA, MACD_histogram)."""
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    diff = ema_fast - ema_slow
    dea = _ema(diff, signal)
    macd_hist = (diff - dea) * 2
    return diff, dea, macd_hist


def _bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    """Returns (middle, upper, lower)."""
    middle = _sma(close, n)
    std = close.rolling(window=n, min_periods=1).std()
    upper = middle + k * std
    lower = middle - k * std
    return middle, upper, lower


# ---------- 主分析函数 ----------

def analyze(daily_path: Path | str, ticker: str) -> tuple[pd.DataFrame, dict, str]:
    """Returns (df_with_indicators, signal_summary_dict, markdown_report)."""
    df = pd.read_parquet(daily_path)
    if df.empty:
        raise RuntimeError(f"daily.parquet 为空: {daily_path}")

    # 按日期升序 (Tushare daily 默认是降序, 需要反转)
    df = df.sort_values("trade_date").reset_index(drop=True)
    df["trade_date"] = df["trade_date"].astype(str)

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["vol"].astype(float)

    # 1. MA
    df["ma5"] = _sma(close, 5)
    df["ma20"] = _sma(close, 20)
    df["ma60"] = _sma(close, 60)
    df["ma120"] = _sma(close, 120)

    # 2. MACD
    df["macd_diff"], df["macd_dea"], df["macd_hist"] = _macd(close)

    # 3. RSI
    df["rsi14"] = _rsi(close, 14)

    # 4. Bollinger
    df["boll_mid"], df["boll_up"], df["boll_dn"] = _bollinger(close, 20, 2)

    # 5. Volume 相对 60 日均量
    df["vol_ma60"] = _sma(vol, 60)
    df["vol_ratio"] = vol / df["vol_ma60"]

    # ---- 信号汇总 (最新一日) ----
    last = df.iloc[-1]
    signals: dict[str, Any] = {
        "trade_date": last["trade_date"],
        "close": float(last["close"]),
        "ticker": ticker,
    }

    # 1. MA 排列
    mas = [last["ma5"], last["ma20"], last["ma60"], last["ma120"]]
    if all(np.isnan(v) == False for v in mas):
        is_bull = mas[0] > mas[1] > mas[2] > mas[3]
        is_bear = mas[0] < mas[1] < mas[2] < mas[3]
        signals["ma_pattern"] = "多头排列 🟢" if is_bull else ("空头排列 🔴" if is_bear else "均线纠缠 🟡")
        signals["ma_values"] = {"ma5": round(mas[0], 2), "ma20": round(mas[1], 2),
                                "ma60": round(mas[2], 2), "ma120": round(mas[3], 2)}
        # 是否破 MA60/120 (中长期趋势线)
        if last["close"] < last["ma120"]:
            signals["below_ma120"] = True
            signals["trend"] = "长期弱势 🔴"
        elif last["close"] > last["ma60"]:
            signals["trend"] = "中期强势 🟢"
        else:
            signals["trend"] = "中期震荡 🟡"

    # 2. MACD 最近 10 日金叉/死叉
    recent = df.tail(10)
    golden = ((recent["macd_diff"].shift(1) < recent["macd_dea"].shift(1)) &
              (recent["macd_diff"] >= recent["macd_dea"])).any()
    death = ((recent["macd_diff"].shift(1) > recent["macd_dea"].shift(1)) &
             (recent["macd_diff"] <= recent["macd_dea"])).any()
    signals["macd_status"] = "近 10 日金叉 🟢" if golden else ("近 10 日死叉 🔴" if death else "无交叉 ⚪")
    signals["macd_diff"] = round(float(last["macd_diff"]), 3)
    signals["macd_dea"] = round(float(last["macd_dea"]), 3)
    signals["macd_above_zero"] = bool(last["macd_diff"] > 0)

    # 3. RSI
    rsi_now = float(last["rsi14"])
    signals["rsi14"] = round(rsi_now, 2)
    if rsi_now > 70:
        signals["rsi_status"] = "超买 🔴"
    elif rsi_now < 30:
        signals["rsi_status"] = "超卖 🟢"
    else:
        signals["rsi_status"] = "中性 ⚪"

    # 4. Bollinger 位置
    if last["close"] > last["boll_up"]:
        signals["boll_position"] = "上轨之上 (短期超买) 🔴"
    elif last["close"] < last["boll_dn"]:
        signals["boll_position"] = "下轨之下 (短期超卖) 🟢"
    elif last["close"] > last["boll_mid"]:
        signals["boll_position"] = "中轨之上 (偏强)"
    else:
        signals["boll_position"] = "中轨之下 (偏弱)"
    signals["boll_upper"] = round(float(last["boll_up"]), 2)
    signals["boll_lower"] = round(float(last["boll_dn"]), 2)
    signals["boll_mid"] = round(float(last["boll_mid"]), 2)

    # 5. Volume 异常
    vol_ratio = float(last["vol_ratio"])
    signals["vol_ratio"] = round(vol_ratio, 2)
    if vol_ratio > 3:
        signals["vol_status"] = f"放巨量 (>{vol_ratio:.1f}x 60 日均量) 🔴"
    elif vol_ratio > 1.5:
        signals["vol_status"] = f"放量 ({vol_ratio:.1f}x) ⚠️"
    elif vol_ratio < 0.5:
        signals["vol_status"] = f"缩量 ({vol_ratio:.1f}x) 🟡"
    else:
        signals["vol_status"] = f"正常 ({vol_ratio:.1f}x)"

    # 6. 支撑阻力 (近 60/120 日)
    last60 = df.tail(60)
    last120 = df.tail(120)
    signals["support_60d"] = round(float(last60["low"].min()), 2)
    signals["resist_60d"] = round(float(last60["high"].max()), 2)
    signals["support_120d"] = round(float(last120["low"].min()), 2)
    signals["resist_120d"] = round(float(last120["high"].max()), 2)
    signals["dist_to_support_60"] = round((signals["close"] - signals["support_60d"]) / signals["close"] * 100, 2)
    signals["dist_to_resist_60"] = round((signals["resist_60d"] - signals["close"]) / signals["close"] * 100, 2)

    # 7. 近期表现
    if len(df) >= 21:
        p20 = float(df.iloc[-21]["close"])
        signals["ret_20d"] = round((signals["close"] - p20) / p20 * 100, 2)
    if len(df) >= 61:
        p60 = float(df.iloc[-61]["close"])
        signals["ret_60d"] = round((signals["close"] - p60) / p60 * 100, 2)
    if len(df) >= 251:
        p252 = float(df.iloc[-251]["close"])
        signals["ret_252d"] = round((signals["close"] - p252) / p252 * 100, 2)

    # ---- 综合技术面结论 ----
    red_flags, green_flags = [], []
    if signals.get("ma_pattern", "").startswith("空头排列"):
        red_flags.append("均线空头排列")
    if signals.get("ma_pattern", "").startswith("多头排列"):
        green_flags.append("均线多头排列")
    if signals.get("below_ma120"):
        red_flags.append("收盘价跌破 MA120 长期均线")
    if signals.get("macd_status", "").startswith("近 10 日死叉"):
        red_flags.append("MACD 近 10 日死叉")
    if signals.get("macd_status", "").startswith("近 10 日金叉"):
        green_flags.append("MACD 近 10 日金叉")
    if signals.get("rsi_status", "").startswith("超买"):
        red_flags.append(f"RSI={rsi_now:.1f} 超买 (>70)")
    if signals.get("rsi_status", "").startswith("超卖"):
        green_flags.append(f"RSI={rsi_now:.1f} 超卖 (<30)")
    if signals.get("vol_ratio", 1) > 3:
        red_flags.append(f"放巨量 ({signals['vol_ratio']}x 60日均量)")

    if len(red_flags) >= 2:
        signals["tech_verdict"] = "🔴 技术面偏空 (多重卖出信号)"
    elif len(green_flags) >= 2:
        signals["tech_verdict"] = "🟢 技术面偏多 (多重买入信号)"
    else:
        signals["tech_verdict"] = "🟡 技术面中性 (无明确方向)"

    signals["red_flags"] = red_flags
    signals["green_flags"] = green_flags

    # ---- Markdown 报告 ----
    md = _format_markdown(df, signals)
    return df, signals, md


def _format_markdown(df: pd.DataFrame, s: dict) -> str:
    lines = [
        f"# 技术分析: {s['ticker']}",
        "",
        f"**收盘日期**: {s['trade_date']} · **收盘价**: {s['close']:.2f} 元",
        "",
        f"## §1 技术面综合判定",
        "",
        f"**结论**: {s.get('tech_verdict', '-')}",
        "",
        "| 维度 | 信号 | 数值 |",
        "|------|------|------|",
        f"| 均线排列 | {s.get('ma_pattern', '-')} | MA5/20/60/120 = {s['ma_values']['ma5']}/{s['ma_values']['ma20']}/{s['ma_values']['ma60']}/{s['ma_values']['ma120']} |",
        f"| 中长期趋势 | {s.get('trend', '-')} | 收盘 vs MA60/MA120 |",
        f"| MACD | {s.get('macd_status', '-')} | DIFF={s.get('macd_diff')} / DEA={s.get('macd_dea')} / 零轴上方={s.get('macd_above_zero')} |",
        f"| RSI(14) | {s.get('rsi_status', '-')} | {s.get('rsi14')} |",
        f"| 布林带位置 | {s.get('boll_position', '-')} | 上轨 {s.get('boll_upper')} / 中 {s.get('boll_mid')} / 下 {s.get('boll_lower')} |",
        f"| 成交量 | {s.get('vol_status', '-')} | 当日/60日均量 = {s.get('vol_ratio')}x |",
    ]

    lines.extend([
        "",
        "## §2 价格位置 (近期表现 + 支撑阻力)",
        "",
        "| 指标 | 数值 | 当前价距离 |",
        "|------|:---:|:---:|",
        f"| 近 20 日涨跌 | {s.get('ret_20d', 'N/A')}% | – |",
        f"| 近 60 日涨跌 | {s.get('ret_60d', 'N/A')}% | – |",
        f"| 近 1 年涨跌 | {s.get('ret_252d', 'N/A')}% | – |",
        f"| 近 60 日最低 (支撑) | {s['support_60d']} 元 | 上方 {s['dist_to_support_60']}% |",
        f"| 近 60 日最高 (阻力) | {s['resist_60d']} 元 | 下方 {s['dist_to_resist_60']}% |",
        f"| 近 120 日最低 | {s['support_120d']} 元 | – |",
        f"| 近 120 日最高 | {s['resist_120d']} 元 | – |",
    ])

    # §3 Red/Green flags
    lines.extend([
        "",
        "## §3 技术面警示 (供 Phase 3 §九 消费)",
        "",
    ])
    if s["red_flags"]:
        lines.append("### 🔴 看空信号")
        for f in s["red_flags"]:
            lines.append(f"- {f}")
    if s["green_flags"]:
        lines.append("")
        lines.append("### 🟢 看多信号")
        for f in s["green_flags"]:
            lines.append(f"- {f}")
    if not s["red_flags"] and not s["green_flags"]:
        lines.append("- ⚪ 当前技术面无显著信号,处于震荡中性区间")

    # §4 解读指引
    lines.extend([
        "",
        "## §4 技术面与基本面的配合 (Phase 3 §九 应用指南)",
        "",
        "**DCF 估值锚是基本面锚,技术面给执行时点提示**:",
        "- 若 DCF 基准情景看涨 + **技术面偏空** → 好公司但时点不对,建议等 MA60 金叉或 RSI 从超卖反弹后再入场",
        "- 若 DCF 基准情景看涨 + **技术面偏多** → 基本面+技术面共振,是加仓时机",
        "- 若 DCF 悲观情景 + **技术面偏空** → 下行风险放大,应减仓或止损",
        "- 若 DCF 悲观情景 + **技术面偏多** → 可能是情绪性反弹,不要追",
        "",
        "**支撑阻力位用途**:",
        f"- 当前价 {s['close']} 元 距离近 60 日支撑 {s['support_60d']} 元仅 {s['dist_to_support_60']}%,**可作为止损参考**",
        f"- 近 60 日阻力 {s['resist_60d']} 元 上方 {s['dist_to_resist_60']}%,**若向上突破为技术面买点信号**",
        "",
        "---",
        "",
        f"*由 `scripts/technical_analysis.py` 自动生成*",
        f"*数据源: Phase 1 `daily.parquet` (Tushare 日线, 近 3 年)*",
        f"*供 Phase 3 §九 估值与回报模拟的 `### 技术面位置` 子节消费*",
    ])

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="A 股技术分析 (v4.4)")
    ap.add_argument("ts_code", help="A 股代码, 如 600745.SH")
    ap.add_argument("--daily", help="daily.parquet 路径 (默认 output/{name}/raw_data/daily.parquet)")
    ap.add_argument("--name", help="公司名 (用于定位 output 目录)")
    ap.add_argument("--out", help="输出 md 路径")
    args = ap.parse_args()

    target_code = normalize_a_code(args.ts_code)
    if args.daily:
        daily_path = Path(args.daily)
    elif args.name:
        daily_path = Path(f"output/{args.name}/raw_data/daily.parquet")
    else:
        # 在 output/ 下搜
        import glob
        candidates = glob.glob(f"output/*/raw_data/daily.parquet")
        if not candidates:
            print("❌ 未找到 daily.parquet, 请用 --daily 指定路径或先跑 Phase 1")
            return 1
        # 按 mtime 选最近的
        daily_path = Path(max(candidates, key=lambda p: Path(p).stat().st_mtime))
        print(f"ℹ️ 自动选取 {daily_path}")

    if not daily_path.exists():
        print(f"❌ daily.parquet 不存在: {daily_path}")
        return 1

    try:
        df, signals, md = analyze(daily_path, target_code)
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback; traceback.print_exc()
        return 1

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"✅ technical_analysis 已写入 {out}")
        print(f"   综合判定: {signals.get('tech_verdict', '-')}")
        print(f"   红旗 {len(signals['red_flags'])} / 绿旗 {len(signals['green_flags'])}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
