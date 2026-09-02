"""init_run — 跨平台初始化一次分析运行 (取代 bash 的 mkdir -p / test -f / printf)。

SKILL.md Step 2 调用: 建 output/{company}/ 目录树 + reviewer_responses/, 若 main-log.md
不存在则建并写表头, 然后追加一行"开始分析"分隔(yymmdd hhmm 双层日志)。

跨平台: 纯 pathlib, Mac/Linux/Windows 通用。

CLI:
  python -m scripts.init_run --company 东山精密 --ticker 002384.SZ
  python -m scripts.init_run --company 东山精密 --ticker 002384.SZ --run-type full
  python -m scripts.init_run --company 东山精密 --ticker 002384.SZ --run-type incremental
  (Windows 用 py -3 -m scripts.init_run ...)

v8: 传 --run-type full|incremental 时额外建 runs/{date}/ 目录树并登记 manifest.json
(契约见 scripts/manifest.py), stdout 第二行输出 run 目录; 不传则保持 v7 行为不变。

v8 增量复查(票 09): --run-type incremental 多做两件事——
  1. **硬规则 1**: 先验证存在可用的 v8 结构基线(manifest 有 runs 记录 + 上版 run 的
     五个节点 md 顶部 YAML 块全部过 schema)。不满足 → 抛 BaselineInvalid, CLI 退出码 3,
     主 agent 改跑全量(增量只服务 v8 结构基线)。
  2. **基线快照**: 采集产物落公司级、R1 刷新会原地覆盖, 所以在刷新**之前**把对比基线
     拷进 runs/{date}/baseline/(metrics.json / red_flags.json / audit_report.json /
     fina_mainbz.parquet / PDF 文件清单 pdfs_before.json / baseline.json 上版指针),
     供 R2 纯脚本分诊(scripts/triage.py)diff。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil
import sys
from pathlib import Path

from . import config
from . import manifest as manifest_mod

# 增量基线快照要拷的公司级证据文件(R1 刷新前的旧值 = 分诊 diff 的 before 侧)
BASELINE_FILES = ("metrics.json", "red_flags.json", "audit_report.json")
BASELINE_DIR = "baseline"


class BaselineInvalid(RuntimeError):
    """硬规则 1: 基线不是可用的 v8 结构(无 manifest / 无 run / 节点块不合契约)→ 直接全量。"""


def _validate_v8_baseline(company_dir: Path) -> dict:
    """校验最近一次 run 是可用的 v8 结构基线, 返回该 run 的 {date, type}。"""
    m = manifest_mod.load(company_dir)
    if not m or not m.get("runs"):
        raise BaselineInvalid(
            "无 v8 manifest/runs 记录(基线是 v8 之前的旧结构报告或从未分析过)"
        )
    prev = m["runs"][-1]
    nodes_dir = company_dir / "runs" / prev["date"] / "nodes"
    from . import assembly  # 延迟导入: v7 路径/全量路径不需要 yaml+jsonschema 之外的东西

    try:
        assembly.load_nodes(nodes_dir)
    except Exception as exc:  # noqa: BLE001 — 缺文件/缺块/不过 schema 都算基线不可用
        raise BaselineInvalid(
            f"上版 run {prev['date']} 不是可用的 v8 结构基线: {exc}"
        ) from exc
    return prev


def snapshot_baseline(company_dir: Path, run_dir: Path, prev: dict) -> Path:
    """把刷新前的公司级证据拷进 run_dir/baseline/, 返回 baseline 目录。"""
    bl = run_dir / BASELINE_DIR
    bl.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in BASELINE_FILES:
        src = company_dir / name
        if src.exists():
            shutil.copy2(src, bl / name)
            copied.append(name)
    mainbz = company_dir / "raw_data" / "fina_mainbz.parquet"
    if mainbz.exists():
        shutil.copy2(mainbz, bl / "fina_mainbz.parquet")
        copied.append("fina_mainbz.parquet")
    pdfs_dir = company_dir / "raw_data" / "pdfs"
    pdfs = sorted(p.name for p in pdfs_dir.glob("*.pdf")) if pdfs_dir.exists() else []
    (bl / "pdfs_before.json").write_text(
        json.dumps(pdfs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (bl / "baseline.json").write_text(
        json.dumps(
            {
                "prev_run_date": prev["date"],
                "prev_run_type": prev["type"],
                "files": copied,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return bl


def init_run(company: str, ticker: str = "", run_type: str | None = None) -> tuple[Path, Path | None]:
    """创建输出目录 + main-log.md; run_type 非空时再建 runs/{date}/ 并登记 manifest。

    run_type=incremental 时先做硬规则 1 校验(失败抛 BaselineInvalid, 不建目录不动 manifest),
    通过后建 run 目录并快照基线。返回 (公司输出目录, run 目录或 None)。
    """
    base = config.output_dir(company)                 # 已建 raw_data/ + raw_data/pdfs/
    (base / "reviewer_responses").mkdir(parents=True, exist_ok=True)

    prev: dict | None = None
    if run_type == "incremental":
        prev = _validate_v8_baseline(base)

    log = base / "main-log.md"
    if not log.exists():
        log.write_text(f"# {company} 分析日志\n\n", encoding="utf-8")

    stamp = _dt.datetime.now().strftime("%y%m%d %H%M")
    label = "开始增量复查" if run_type == "incremental" else "开始分析"
    with log.open("a", encoding="utf-8") as f:
        f.write(f"- {stamp} ━━━ {label} {company}({ticker}) ━━━\n")

    run_dir: Path | None = None
    if run_type:
        run_dir = manifest_mod.create_run(base, run_type, ticker=ticker)
        if prev is not None:
            snapshot_baseline(base, run_dir, prev)

    return base, run_dir


def main() -> int:
    for stream in (sys.stdout, sys.stderr):      # Windows 控制台 GBK 下 print emoji 会炸
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

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
    try:
        base, run_dir = init_run(args.company, args.ticker, args.run_type)
    except BaselineInvalid as exc:
        print(f"❌ 硬规则1: {exc}", file=sys.stderr)
        print("→ 增量只服务 v8 结构基线, 请改跑全量: init_run --run-type full", file=sys.stderr)
        return 3
    print(str(base))
    if run_dir is not None:
        print(str(run_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
