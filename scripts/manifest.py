"""manifest — v8 契约层: runs/{date}/ 目录制 + 公司级状态唯一源 manifest.json。

每次分析 run 落在 output/{company}/runs/{YYYY-MM-DD}/ 独立目录(旧 run 整目录即留档);
manifest.json 挂在公司目录根, 是 runs 列表(full/incremental)、增量计数、上次全量日期、
下次预约披露日、所属对比组的唯一真相源(schema: scripts/schemas/manifest.schema.json)。

run 目录内固定子目录:
  raw_data/pdfs/   采集产物(data-collector)
  nodes/           五个节点 md(顶部 YAML verdict 块, 见 verdict_block)
  assembly/        装配产物(首页/附录/metadata)
  reviewer_responses/  质量环往返
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from . import verdict_block

MANIFEST_NAME = "manifest.json"
RUN_SUBDIRS = ("raw_data/pdfs", "nodes", "assembly", "reviewer_responses")
RUN_TYPES = ("full", "incremental")


class RunExists(FileExistsError):
    """同日期 run 目录已存在(一天最多一个 run, 重跑先手动清理)。"""


def manifest_path(company_dir: Path) -> Path:
    return Path(company_dir) / MANIFEST_NAME


def load(company_dir: Path) -> dict | None:
    """读公司 manifest; 不存在返回 None。"""
    p = manifest_path(company_dir)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save(company_dir: Path, data: dict) -> None:
    """校验后写 manifest(不合法直接抛错, 不落盘脏状态)。"""
    errs = verdict_block.validate(data, "manifest")
    if errs:
        raise ValueError(f"manifest 不合法, 拒绝写入: {errs}")
    manifest_path(company_dir).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _new_manifest(company: str, ticker: str) -> dict:
    return {
        "company": company,
        "ticker": ticker,
        "market": None,
        "runs": [],
        "incremental_count": 0,
        "last_full_date": None,
        "next_disclosure_date": None,
        "compare_groups": [],
    }


def create_run(
    company_dir: Path,
    run_type: str,
    date: str | None = None,
    ticker: str = "",
) -> Path:
    """建 runs/{date}/ 目录树并把本次 run 记入 manifest, 返回 run 目录。

    full run 重置增量计数并更新 last_full_date; incremental 计数 +1。
    旧 run 目录不触碰(整目录留档)。
    """
    if run_type not in RUN_TYPES:
        raise ValueError(f"run_type 必须是 {'|'.join(RUN_TYPES)}, 收到: {run_type}")
    company_dir = Path(company_dir)
    date = date or _dt.date.today().isoformat()

    run_dir = company_dir / "runs" / date
    if run_dir.exists():
        raise RunExists(f"run 目录已存在: {run_dir}")
    for sub in RUN_SUBDIRS:
        (run_dir / sub).mkdir(parents=True)

    m = load(company_dir) or _new_manifest(company_dir.name, ticker)
    if ticker and not m.get("ticker"):
        m["ticker"] = ticker
    m["runs"].append({"date": date, "type": run_type})
    if run_type == "full":
        m["last_full_date"] = date
        m["incremental_count"] = 0
    else:
        m["incremental_count"] += 1
    save(company_dir, m)
    return run_dir


def latest_run(company_dir: Path) -> dict | None:
    """最近一次 run 的 {date, type}; 无 manifest 或无 run 返回 None。"""
    m = load(company_dir)
    if not m or not m["runs"]:
        return None
    return m["runs"][-1]
