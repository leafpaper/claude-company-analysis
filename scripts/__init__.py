"""company-analysis data layer — structured financial data collection & computation.

Modules:
    config            配置（token 路径、缓存 TTL、速率限制）
    data_cache        7 天 TTL 的 Parquet 缓存
    check_env         环境检查（pip 包 + TUSHARE_TOKEN）
    tushare_collector A 股 Tushare Pro 接口封装
    us_collector      美股 yfinance 接口封装
    hk_collector      港股 混合（Tushare 港股 + yfinance fallback）
    pdf_reader        财报 PDF 原文解析（pypdf + 正则段落提取）
    derived_metrics   CAGR / FCF / ROIC / WACC / Owner Earnings 计算

CLI 入口见 README.md。数据输出到 output/{company}/raw_data/ 下。
"""

__version__ = "3.0.0"
