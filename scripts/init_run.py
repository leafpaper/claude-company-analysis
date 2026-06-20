"""init_run — 跨平台初始化一次分析运行 (取代 bash 的 mkdir -p / test -f / printf)。

SKILL.md Step 2 调用: 建 output/{company}/ 目录树 + reviewer_responses/, 若 main-log.md
不存在则建并写表头, 然后追加一行"开始分析"分隔(yymmdd hhmm 双层日志)。

跨平台: 纯 pathlib, Mac/Linux/Windows 通用。

CLI:
  python -m scripts.init_run --company 东山精密 --ticker 002384.SZ
  (Windows 用 py -3 -m scripts.init_run ...)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

from . import config


def init_run(company: str, ticker: str = "") -> Path:
    """创建输出目录 + main-log.md, 返回公司输出目录路径。"""
    base = config.output_dir(company)                 # 已建 raw_data/ + raw_data/pdfs/
    (base / "reviewer_responses").mkdir(parents=True, exist_ok=True)

    log = base / "main-log.md"
    if not log.exists():
        log.write_text(f"# {company} 分析日志\n\n", encoding="utf-8")

    stamp = _dt.datetime.now().strftime("%y%m%d %H%M")
    with log.open("a", encoding="utf-8") as f:
        f.write(f"- {stamp} ━━━ 开始分析 {company}({ticker}) ━━━\n")

    return base


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--company", required=True)
    ap.add_argument("--ticker", default="")
    args = ap.parse_args()
    base = init_run(args.company, args.ticker)
    print(str(base))
    return 0


if __name__ == "__main__":
    sys.exit(main())
