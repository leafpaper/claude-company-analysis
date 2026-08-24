"""triage — v8 增量复查(--review)R2 纯脚本分诊: 指标 diff + 质地标脏机检 + 重评波次。

四段链里的位置(spec §8 / research/03):
    R1 证据刷新(data-collector/doc-analyst 增量模式)
  → R2 本脚本(**零 LLM**): 基线快照 vs 刷新后证据 diff, 产结构化分诊单 triage.json
  → R3 依赖图跑标脏子集(node_graph 同一套调度), 未重评节点拷上版 YAML 块盖「复用」戳
  → R4 决策层 + 首页必重装配(assemble_report_v8 --prev-run-dir ... --metric-deltas triage.json)

分层重评规则(机器执行, 不留判断给人):
  · 状态/赔率/路径/决策 = 每次必重评(node_graph.ALWAYS_RERUN);
  · 质地默认复用, 四条标脏机检——
      (a) annual_report      新增年报 PDF(排除半年报/中报的 annual 误匹配)
      (b) segment_band       关键分部收入占比跨档(档位 10% / 25% / 50%, fina_mainbz 两版对比)
      (c) new_quality_flag   新增红旗归家质地节点且 🔴/🟠/🟡(red_flags.json 按 id diff)
      (d) evidence_sign_flip 质地关键指标变号(经营现金流 / FCF / 归母净利 / ROE / 净利同比过零)
    「跨阈值」的具名阈值等票 11 估值推导 schema 落地后并入; 当前机检口径 = 过零变号。
  · **拿不准一律标脏**(铁律): 某条规则的 diff 数据**单侧缺失**(基线有新版没有, 或反之)
    → 无法判断变化 → 该规则记 triggered=null 且整体标脏。两侧都没有(该市场从来不产这份
    数据, 如港股无 fina_mainbz)→ 无变化信号, 不触发, evidence 里写明。

硬规则 1(旧结构基线→直接全量)在 init_run --run-type incremental 已拦截, 本脚本不重复;
硬规则 2(质地翻转/档位跨两档→首页明示建议全量)由装配层 change_block 在 R4 判(assembly.py);
建议档(距上次全量 >12 个月 或 累计 ≥4 次增量 → 建议全量重锚)由本脚本从 manifest 算出。

产物: {run_dir}/triage.json(过 scripts/schemas/triage.schema.json)。
`--apply-reuse` 额外把未重评节点的 md 从上版 run 拷来, YAML 块盖 reused_from 戳 +
正文插一行复用说明(装配后读者可见, 复用不藏着)。

CLI(主 agent 在 R1 刷新完成后调用):
    python -m scripts.triage --company-dir output/{company} --run-dir output/{company}/runs/{date} --apply-reuse
    python -m scripts.triage --company-dir ... --run-dir ... --json
退出码: 0 = 分诊完成(脏不脏都算完成) · 2 = 输入不完整(没跑 init_run incremental / 缺基线)。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

from . import assembly
from . import manifest as manifest_mod
from . import node_graph
from . import verdict_block

TRIAGE_NAME = "triage.json"
BASELINE_DIR = "baseline"

# 质地标脏四条的机检名(分诊单 rules[].rule 的枚举, schema 锁定)
RULE_ANNUAL = "annual_report"
RULE_SEGMENT = "segment_band"
RULE_FLAG = "new_quality_flag"
RULE_SIGN = "evidence_sign_flip"

# 分部占比档位边界(research/03 场景 A 3.58%→7% 未跨档 / 场景 B →12% 跨档 ⇒ 首档线 10%)
SEGMENT_BANDS = (0.10, 0.25, 0.50)

# 指标 diff 的重大变化阈值(沿用旧 monitor 内核的 ±10%)
DELTA_THRESHOLD = 0.10
MAX_DELTAS = 12

# metrics.json 里参与 diff 的指标: 点路径 → (人话名, 格式)
# 格式: yi=换算亿元 / pct=小数→百分比 / raw2=原值两位小数(估值倍数与已是百分数的比率)
METRIC_WATCH: dict[str, tuple[str, str]] = {
    "valuation.latest_close": ("收盘价", "raw2"),
    "valuation.pe_ttm": ("PE(TTM)", "raw2"),
    "valuation.pb": ("PB", "raw2"),
    "valuation.ps_ttm": ("PS(TTM)", "raw2"),
    "valuation.market_cap_wanyuan": ("总市值", "wanyuan_yi"),
    "profitability.roe_latest": ("ROE", "raw2"),
    "profitability.gross_margin_latest": ("毛利率", "raw2"),
    "profitability.net_margin_latest": ("净利率", "raw2"),
    "profitability.debt_to_assets": ("资产负债率", "raw2"),
    "growth.revenue_yoy_latest": ("营收同比", "pct"),
    "growth.net_income_yoy_latest": ("归母净利同比", "pct"),
    "cashflow.operating_cashflow_latest": ("经营现金流", "yi"),
    "cashflow.free_cashflow_latest": ("自由现金流", "yi"),
    "latest_vitals.latest_revenue": ("最新期营收", "yi"),
    "latest_vitals.latest_net_income": ("最新期归母净利", "yi"),
}

# 规则 (d) 监测变号的质地关键指标(经营质量的「最硬证据」常引用处)
SIGN_WATCH = (
    "cashflow.operating_cashflow_latest",
    "cashflow.free_cashflow_latest",
    "latest_vitals.latest_net_income",
    "profitability.roe_latest",
    "growth.net_income_yoy_latest",
)

# 规则 (c) 只看会上红/黄标的新红旗(🟢/ℹ️ 不构成质地重评理由)
FLAG_LEVELS = ("🔴", "🟠", "🟡")

# 半年报/中报先排除, 再匹配年报(避免 semiannual 里的 annual 误命中)
_INTERIM_RE = re.compile(r"semi|half|interim|中报|半年", re.IGNORECASE)
_ANNUAL_RE = re.compile(r"annual|年度报告|年报", re.IGNORECASE)

# 复用说明行(插进复用节点正文顶部, 装配后读者可见; 重复复用时先剥旧行再插新行)
_REUSE_NOTE_RE = re.compile(r"^> ♻️ .*\n?", re.MULTILINE)


class TriageInputError(RuntimeError):
    """缺基线快照 / 缺上版节点——没法分诊(先跑 init_run --run-type incremental + R1 刷新)。"""


# ---------------------------------------------------------------- 工具

def _read_json(path: Path):
    if not path.exists():
        return None
    raw = path.read_bytes()
    # 容错读取: 历史 collector 在 Windows ANSI 控制台下写过 GBK 的 metrics.json
    # (根因已修 derived_metrics encoding="utf-8", 但存量文件与旧机器仍可能撞上)
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise TriageInputError(f"{path.name}: 不是可解析的 JSON(utf-8/gbk 都读不动)")


def _flag_list(data) -> list | None:
    """red_flags.json 两种形态都认: 裸列表 或 red_flags.py CLI 的 {"red_flags": [...]}。"""
    if data is None:
        return None
    if isinstance(data, dict):
        return list(data.get("red_flags") or [])
    return list(data)


def _metric_get(metrics: dict | None, dotted: str):
    val = metrics or {}
    for key in dotted.split("."):
        if not isinstance(val, dict):
            return None
        val = val.get(key)
    return val if isinstance(val, (int, float)) else None


def _fmt(value: float, fmt: str) -> str:
    if fmt == "yi":
        return f"{value / 1e8:,.2f} 亿"
    if fmt == "wanyuan_yi":
        return f"{value / 1e4:,.0f} 亿"
    if fmt == "pct":
        return f"{value * 100:+.1f}%"
    return f"{value:,.2f}"


def _is_interim(name: str) -> bool:
    return bool(_INTERIM_RE.search(name))


def is_annual_pdf(name: str) -> bool:
    """年报判定: 先排除半年报/中报/interim, 再看 annual/年报/年度报告。"""
    return not _is_interim(name) and bool(_ANNUAL_RE.search(name))


# ---------------------------------------------------------------- 各项 diff

def metric_deltas(before: dict | None, after: dict | None) -> list[dict]:
    """两版 metrics.json → 重大变化清单(±10% 或变号), 形状与 assembly change_block 对齐。"""
    if before is None or after is None:
        return []
    out = []
    for dotted, (label, fmt) in METRIC_WATCH.items():
        b, a = _metric_get(before, dotted), _metric_get(after, dotted)
        if b is None or a is None:
            continue
        flipped = (b > 0 > a) or (b < 0 < a)
        rel = abs(a - b) / abs(b) if b else (float("inf") if a else 0.0)
        if not flipped and rel < DELTA_THRESHOLD:
            continue
        out.append({
            "name": label,
            "before": _fmt(b, fmt),
            "after": _fmt(a, fmt),
            "_rank": rel if rel != float("inf") else 9e9,
        })
    out.sort(key=lambda d: d["_rank"], reverse=True)
    for d in out:
        d.pop("_rank")
    return out[:MAX_DELTAS]


def segment_shares(parquet_path: Path) -> dict[str, float] | None:
    """fina_mainbz 最新期各分部收入占比(优先产品口径 P); 文件缺失返回 None。"""
    if not parquet_path.exists():
        return None
    import pandas as pd  # 延迟导入, 非 A 股路径不强依赖

    df = pd.read_parquet(parquet_path)
    if df.empty or "bz_sales" not in df.columns:
        return {}
    for code in ("P", "I", "D"):
        sub = df[df["bz_code"] == code] if "bz_code" in df.columns else df
        if not sub.empty:
            break
    date_col = "end_date" if "end_date" in sub.columns else None
    if date_col:
        sub = sub[sub[date_col] == sub[date_col].max()]
    sub = sub[~sub["bz_item"].astype(str).str.contains("合计|小计|总计", na=False)]
    vals = {str(r.bz_item): float(r.bz_sales or 0) for r in sub.itertuples()}
    # 名字抓不住的聚合行按数值剔除(Tushare P 口径常有一行「产品」= 全部之和):
    # 某行 ≈ 其余行之和(±2%)即视为合计行, 只剔最大的一行
    grand = sum(vals.values())
    for name, v in sorted(vals.items(), key=lambda kv: -kv[1]):
        rest = grand - v
        if rest > 0 and abs(v - rest) / rest < 0.02:
            del vals[name]
            break
    total = sum(vals.values())
    if total <= 0:
        return {}
    return {name: v / total for name, v in vals.items()}


def _band(share: float) -> int:
    return sum(share >= b for b in SEGMENT_BANDS)


def segment_band_crossings(
    before: dict[str, float] | None, after: dict[str, float] | None
) -> list[str] | None:
    """跨档分部清单; 任一侧数据缺失(None)返回 None = 拿不准。"""
    if before is None or after is None:
        return None
    crossings = []
    for name in sorted(set(before) | set(after)):
        b, a = before.get(name, 0.0), after.get(name, 0.0)
        if _band(b) != _band(a):
            crossings.append(f"{name} {b:.1%}→{a:.1%}")
    return crossings


def new_quality_flags(before: list | None, after: list | None) -> list[dict] | None:
    """新增且归家质地、级别 🔴/🟠/🟡 的红旗; 任一侧清单缺失返回 None = 拿不准。"""
    if before is None or after is None:
        return None
    old_ids = {f["id"] for f in before}
    return [
        f for f in after
        if f["id"] not in old_ids and f.get("node") == "quality" and f.get("level") in FLAG_LEVELS
    ]


def sign_flips(before: dict | None, after: dict | None) -> list[str] | None:
    """SIGN_WATCH 指标里的过零变号; 任一侧 metrics.json 缺失返回 None = 拿不准。"""
    if before is None or after is None:
        return None
    flips = []
    for dotted in SIGN_WATCH:
        b, a = _metric_get(before, dotted), _metric_get(after, dotted)
        if b is None or a is None:
            continue
        if (b > 0 > a) or (b < 0 < a):
            label, fmt = METRIC_WATCH.get(dotted, (dotted, "raw2"))
            flips.append(f"{label} {_fmt(b, fmt)}→{_fmt(a, fmt)}")
    return flips


# ---------------------------------------------------------------- 质地标脏

def _rule(rule: str, triggered: bool | None, evidence: str) -> dict:
    return {"rule": rule, "triggered": triggered, "evidence": evidence}


def quality_rules(
    new_pdfs: list[str],
    seg_before: dict | None,
    seg_after: dict | None,
    flags_before: list | None,
    flags_after: list | None,
    m_before: dict | None,
    m_after: dict | None,
) -> list[dict]:
    """四条标脏机检; triggered=None 表示单侧数据缺失拿不准(整体按脏处理)。"""
    rules = []

    annual = [n for n in new_pdfs if is_annual_pdf(n)]
    rules.append(_rule(
        RULE_ANNUAL, bool(annual),
        f"新增年报 PDF: {', '.join(annual)}" if annual else "无新增年报 PDF",
    ))

    if seg_before is None and seg_after is None:
        rules.append(_rule(RULE_SEGMENT, False, "两版均无分部数据(该市场不产 fina_mainbz), 无变化信号"))
    else:
        crossings = segment_band_crossings(seg_before, seg_after)
        if crossings is None:
            rules.append(_rule(RULE_SEGMENT, None, "分部数据单侧缺失, 拿不准 → 标脏"))
        else:
            bands = "/".join(f"{int(b * 100)}%" for b in SEGMENT_BANDS)
            rules.append(_rule(
                RULE_SEGMENT, bool(crossings),
                f"跨档({bands} 档线): {'; '.join(crossings)}" if crossings
                else f"各分部占比均未跨档({bands} 档线)",
            ))

    if flags_before is None and flags_after is None:
        rules.append(_rule(RULE_FLAG, False, "两版均无 red_flags.json, 无变化信号"))
    else:
        fresh = new_quality_flags(flags_before, flags_after)
        if fresh is None:
            rules.append(_rule(RULE_FLAG, None, "红旗清单单侧缺失, 拿不准 → 标脏"))
        else:
            rules.append(_rule(
                RULE_FLAG, bool(fresh),
                "新增质地红旗: " + "; ".join(f"{f['level']} {f['title']}" for f in fresh)
                if fresh else "无新增 🔴/🟠/🟡 质地红旗",
            ))

    if m_before is None and m_after is None:
        rules.append(_rule(RULE_SIGN, False, "两版均无 metrics.json, 无变化信号"))
    else:
        flips = sign_flips(m_before, m_after)
        if flips is None:
            rules.append(_rule(RULE_SIGN, None, "metrics.json 单侧缺失, 拿不准 → 标脏"))
        else:
            rules.append(_rule(
                RULE_SIGN, bool(flips),
                "关键指标变号: " + "; ".join(flips) if flips else "监测指标(现金流/净利/ROE/净利同比)均未变号",
            ))

    return rules


# ---------------------------------------------------------------- 建议档

def full_rerun_advice(m: dict | None, today: str) -> dict:
    """建议档: 距上次全量 >12 个月 或 累计 ≥4 次增量 → 建议全量重锚(不阻断本次增量)。"""
    reasons = []
    if not m or not m.get("last_full_date"):
        reasons.append("manifest 无全量基线日期")
    else:
        import datetime as dt

        days = (dt.date.fromisoformat(today) - dt.date.fromisoformat(m["last_full_date"])).days
        if days > 365:
            reasons.append(f"距上次全量 {days} 天(>12 个月)")
    if m and m.get("incremental_count", 0) >= 4:
        reasons.append(f"累计增量 {m['incremental_count']} 次(≥4)")
    return {"advised": bool(reasons), "reasons": reasons}


# ---------------------------------------------------------------- 复用戳

def stamp_reused_copy(prev_md: Path, dest_md: Path, prev_date: str, reason: str) -> None:
    """把上版节点 md 拷到本版, YAML 块盖 reused_from 戳 + 正文插复用说明行。

    上版本身已是复用块时保留其原始 reused_from(指向最后一次真实重评的日期)。
    拷完按该节点 schema 复检, 不合法直接抛错。
    """
    text = prev_md.read_text(encoding="utf-8")
    m = verdict_block._TOP_BLOCK_RE.match(text)
    if not m:
        raise TriageInputError(f"{prev_md.name}: 上版 md 顶部无 YAML 块, 不能复用")
    data = yaml.safe_load(m.group(1))
    data["reused_from"] = data.get("reused_from") or prev_date
    dumped = yaml.safe_dump(data, allow_unicode=True, sort_keys=False).rstrip("\n")
    body = _REUSE_NOTE_RE.sub("", text[m.end():]).lstrip("\n")
    note = (
        f"> ♻️ 本章判断复用 {data['reused_from']} 版({reason});"
        "证据数字以本版附录为准。\n\n"
    )
    dest_md.write_text(f"```yaml\n{dumped}\n```\n\n{note}{body}", encoding="utf-8")

    node = data.get("node")
    schema = assembly.NODE_SCHEMAS.get(node)
    if schema:
        errs = verdict_block.validate(data, schema)
        if errs:
            raise TriageInputError(f"{dest_md.name}: 复用块不过 schema: {errs}")


# ---------------------------------------------------------------- 主流程

def run_triage(company_dir: Path, run_dir: Path, apply_reuse: bool = False) -> dict:
    company_dir, run_dir = Path(company_dir), Path(run_dir)
    bl = run_dir / BASELINE_DIR
    baseline_meta = _read_json(bl / "baseline.json")
    if baseline_meta is None:
        raise TriageInputError(
            f"缺 {bl / 'baseline.json'} —— 先跑 init_run --run-type incremental(它做硬规则1校验并快照基线)"
        )
    prev_date = baseline_meta["prev_run_date"]
    prev_run_dir = company_dir / "runs" / prev_date
    prev_nodes_dir = prev_run_dir / "nodes"
    if not prev_nodes_dir.exists():
        raise TriageInputError(f"上版 run 目录缺失: {prev_nodes_dir}")
    prev_nodes = assembly.load_nodes(prev_nodes_dir)

    # 证据 diff: 基线快照(before) vs 公司级刷新后(after)
    m_before = _read_json(bl / "metrics.json")
    m_after = _read_json(company_dir / "metrics.json")
    flags_before = _flag_list(_read_json(bl / "red_flags.json"))
    flags_after = _flag_list(_read_json(company_dir / "red_flags.json"))
    seg_before = segment_shares(bl / "fina_mainbz.parquet")
    seg_after = segment_shares(company_dir / "raw_data" / "fina_mainbz.parquet")
    pdfs_before = set(_read_json(bl / "pdfs_before.json") or [])
    pdfs_dir = company_dir / "raw_data" / "pdfs"
    pdfs_now = sorted(p.name for p in pdfs_dir.glob("*.pdf")) if pdfs_dir.exists() else []
    new_pdfs = [n for n in pdfs_now if n not in pdfs_before]

    rules = quality_rules(new_pdfs, seg_before, seg_after, flags_before, flags_after, m_before, m_after)
    quality_dirty = any(r["triggered"] is None or r["triggered"] for r in rules)

    rerun = set(node_graph.ALWAYS_RERUN) | ({"quality"} if quality_dirty else set())
    plan = node_graph.plan(sorted(rerun))

    # 红旗 diff(脚本源两版): 触发/解除/升降级, 变化区块与首页装配同一口径
    red_flag_diff = assembly._flag_changes(flags_before or [], flags_after or [])

    path_block = prev_nodes["path"]
    falsification_checklist = [
        {"condition": f["condition"], "prev_triggered": f.get("triggered")}
        for f in path_block.get("falsifications") or []
    ]
    critical_points = list((prev_nodes["state"].get("critical_point") or {}).get("items") or [])

    manifest = manifest_mod.load(company_dir)
    date = run_dir.name
    advice = full_rerun_advice(manifest, date)

    deltas = metric_deltas(m_before, m_after)
    dirty_note = "质地标脏 → 五节点全部重评" if quality_dirty else "质地复用, 重评 状态/赔率/路径/决策"
    summary = (
        f"分诊: {dirty_note};新增 PDF {len(new_pdfs)} 份, 重大指标变化 {len(deltas)} 项, "
        f"红旗变化 {len(red_flag_diff)} 条;证伪清单 {len(falsification_checklist)} 条待④路径核销"
        + ("; ⚠️ 建议全量重锚(" + "; ".join(advice["reasons"]) + ")" if advice["advised"] else "")
    )

    result = {
        "company": manifest["company"] if manifest else company_dir.name,
        "date": date,
        "prev_run_date": prev_date,
        "prev_run_type": baseline_meta.get("prev_run_type", "full"),
        "quality": {"dirty": quality_dirty, "rules": rules},
        "rerun_nodes": plan["nodes"],
        "reused_nodes": plan["reused"],
        "waves": plan["waves"],
        "agents": plan["agents"],
        "new_pdfs": new_pdfs,
        "annual_disclosed": any(is_annual_pdf(n) for n in new_pdfs),
        "metric_deltas": deltas,
        "red_flag_diff": red_flag_diff,
        "falsification_checklist": falsification_checklist,
        "critical_points": critical_points,
        "full_rerun_advice": advice,
        "summary": summary,
    }
    errs = verdict_block.validate(result, "triage")
    if errs:
        raise RuntimeError(f"分诊单不过 schema(triage.py 自身 bug): {errs}")

    (run_dir / TRIAGE_NAME).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if apply_reuse:
        reason = "增量复查分诊: 质地四条标脏规则均未触发"
        for node in plan["reused"]:
            fname = assembly.NODE_FILES[node]
            stamp_reused_copy(prev_nodes_dir / fname, run_dir / "nodes" / fname, prev_date, reason)
        # 重跑分诊后判定可能从「复用」翻成「重评」(证据修正后常见): 清掉早前盖过戳的
        # 旧复用拷贝, 免得写手失败时留下一份假装是新判断的旧文件
        for node in plan["nodes"]:
            dest = run_dir / "nodes" / assembly.NODE_FILES[node]
            if dest.exists() and "♻️ 本章判断复用" in dest.read_text(encoding="utf-8"):
                dest.unlink()

    return result


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--company-dir", required=True, help="output/{company}/ 目录")
    ap.add_argument("--run-dir", required=True, help="本次增量 runs/{date}/ 目录(含 baseline/)")
    ap.add_argument("--apply-reuse", action="store_true",
                    help="把未重评节点从上版拷来盖「复用」戳(R3 开跑前执行)")
    ap.add_argument("--json", action="store_true", help="只输出 JSON(供脚本消费)")
    args = ap.parse_args()

    try:
        result = run_triage(Path(args.company_dir), Path(args.run_dir), apply_reuse=args.apply_reuse)
    except (TriageInputError, assembly.AssemblyError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(result["summary"])
    print()
    print("质地标脏机检:")
    for r in result["quality"]["rules"]:
        mark = "❓拿不准→脏" if r["triggered"] is None else ("❌触发" if r["triggered"] else "✅未触发")
        print(f"  {mark} {r['rule']}: {r['evidence']}")
    print()
    for line in node_graph.describe(result["waves"]):
        print(line)
    if result["reused_nodes"]:
        labels = "、".join(node_graph.LABELS[n] for n in result["reused_nodes"])
        stamped = "(已拷上版块盖复用戳)" if args.apply_reuse else "(跑 --apply-reuse 拷块)"
        print(f"复用上版: {labels} {stamped}")
    if result["full_rerun_advice"]["advised"]:
        print("⚠️ 建议档: " + "; ".join(result["full_rerun_advice"]["reasons"]) + " → 建议全量重锚")
    print(f"\n分诊单: {Path(args.run_dir) / TRIAGE_NAME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
