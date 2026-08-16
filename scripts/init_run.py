"""init_run — 跨平台初始化一次分析运行 (取代 bash 的 mkdir -p / test -f / printf)。

SKILL.md Step 2 调用: 建 output/{company}/ 目录树 + reviewer_responses/, 若 main-log.md
不存在则建并写表头, 然后追加一行"开始分析"分隔(yymmdd hhmm 双层日志)。

跨平台: 纯 pathlib, Mac/Linux/Windows 通用。

CLI:
  python -m scripts.init_run --company 东山精密 --ticker 002384.SZ
  python -m scripts.init_run --company 东山精密 --ticker 002384.SZ --run-type full
  (Windows 用 py -3 -m scripts.init_run ...)

v8: 传 --run-type full|incremental 时额外建 runs/{date}/ 目录树并登记 manifest.json
(契约见 scripts/manifest.py), stdout 第二行输出 run 目录; 不传则保持 v7 行为不变。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

from . import config
from . import manifest as manifest_mod


def init_run(company: str, ticker: str = "", run_type: str | None = None) -> tuple[Path, Path | None]:
    """创建输出目录 + main-log.md; run_type 非空时再建 runs/{date}/ 并登记 manifest。

    返回 (公司输出目录, run 目录或 None)。
    """
    base = config.output_dir(company)                 # 已建 raw_data/ + raw_data/pdfs/
    (base / "reviewer_responses").mkdir(parents=True, exist_ok=True)

    log = base / "main-log.md"
    if not log.exists():
        log.write_text(f"# {company} 分析日志\n\n", encoding="utf-8")

    stamp = _dt.datetime.now().strftime("%y%m%d %H%M")
    with log.open("a", encoding="utf-8") as f:
        f.write(f"- {stamp} ━━━ 开始分析 {company}({ticker}) ━━━\n")

    run_dir: Path | None = None
    if run_type:
        run_dir = manifest_mod.create_run(base, run_type, ticker=ticker)

    return base, run_dir


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--company", required=True)
    ap.add_argument("--ticker", default="")
    ap.add_argument(
        "--run-type",
        choices=manifest_mod.RUN_TYPES,
        default=None,
        help="v8: 建 runs/{date}/ 目录并登记 manifest; 不传保持 v7 行为",
    )
    args = ap.parse_args()
    base, run_dir = init_run(args.company, args.ticker, args.run_type)
    print(str(base))
    if run_dir is not None:
        print(str(run_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
