"""red_flags — v8 附录D 引擎: 红旗两源制(脚本 audit ⊕ 写手提名)合并 / 分组 / Top3 / 红标反查。

红旗清单是唯一判断权威(spec §3), 本模块只做**展示层映射**:零新增阈值、零新结论。

三件事:
  1. normalize_audit(): financial_audit 的 JSON(framework/signal/severity/...)→ 契约条目
     (common.schema.json#/$defs/red_flag_item: id/level/title/evidence/source/node/metric_refs)。
     id 稳定可复现(framework slug + signal 摘要哈希), 写手在 red_flags.json 里照抄 id 做
     panel 的 red_flag_ref, 增量复查(票 09)按 id diff 触发/解除。
  2. merge(): 脚本红旗 ⊕ 节点 YAML 的 red_flag_nominations, 同池一视同仁(05 决策)。
  3. top3() / red_mark_map(): Top3 机器带出 + 指标↔红旗反查数据(供 HTML 层渲染三通道与跳转)。

**分组**: 同一「首要关联指标」(metric_refs[0])的多条红旗视为一个风险, 合并成 Top3 的一条
(05 推演:脚本商誉规则 + 写手「对赌未披露」提名 = 一条商誉风险), 无 metric_refs 的条目自成一组。
**Top3 排序**: (级别 → 组内条数多者优先 → 归属节点 path>odds>quality>state → 清单出现序);
东山推演对照见 research/02 §6 与 research/05 §2(见 .scratch/v8-implementation/issues/04)。

CLI(P1 采集尾巴, 产 red_flags.json 供写手引用 id):
  python -m scripts.red_flags --audit-json output/{c}/audit_report.json --out output/{c}/red_flags.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from . import verdict_block

LEVELS = ("🔴", "🟠", "🟡", "🟢", "ℹ️")
LEVEL_ORDER = {lvl: i for i, lvl in enumerate(LEVELS)}
# 红标三通道的色档: 🔴/🟠 红、🟡 黄、🟢/ℹ️ 不标(05:无红旗命中的难看数字不标色)
MARK_BY_LEVEL = {"🔴": "red", "🟠": "red", "🟡": "yellow", "🟢": None, "ℹ️": None}
MARKED_LEVELS = tuple(lvl for lvl, mark in MARK_BY_LEVEL.items() if mark)

NODES = ("quality", "state", "odds", "path")
NODE_LABELS = {"quality": "①质地", "state": "②状态", "odds": "③赔率", "path": "④路径"}
# Top3 同级同条数时的杀伤力序:能让本金永久损失的(路径左尾)> 定价透支(赔率)> 经营质量 > 状态
NODE_ORDER = {"path": 0, "odds": 1, "quality": 2, "state": 3}
SOURCE_LABELS = {"script": "脚本", "nomination": "写手提名"}

# 脚本红旗归家(framework → 节点 + 默认关联指标), 覆盖 financial_audit 的 11 个框架
FRAMEWORK_MAP = {
    "Piotroski F-Score": ("quality", ["f_score"]),
    "Beneish M-Score": ("quality", ["m_score"]),
    "Altman Z-Score": ("quality", ["z_score"]),
    "DuPont": ("quality", ["roe"]),
    "Buffett Quality": ("quality", []),
    "Sloan Accrual": ("quality", ["accrual"]),
    "Governance": ("path", ["governance"]),
    "Shareholder Flow": ("path", ["holder_count"]),
    "Forecast Anomaly": ("state", ["forecast"]),
    "Valuation": ("odds", ["valuation"]),
    "Related-Party Exposure": ("quality", ["related_party"]),
}
# 信号级归家覆盖(前缀匹配, 因部分 signal 带动态数字): 决定节点 + 首要关联指标(=分组键)
SIGNAL_MAP = {
    "利润质量偏弱": ("quality", ["ocf_ni", "fcf"]),
    "应收账款增速远高于营收": ("quality", ["receivables"]),
    "存货增速远高于营收": ("quality", ["inventory"]),
    "商誉占净资产过高": ("path", ["goodwill"]),          # 商誉减值=左尾地板(research/02 §4)
    "非经常性损益占比过高": ("quality", ["non_operating"]),
    "高应计比例": ("quality", ["accrual"]),
    "ROE 急剧恶化": ("quality", ["roe"]),
    "高比例质押股东": ("path", ["pledge"]),
    "前十大股东减持": ("path", ["top10_change"]),
    "股东户数": ("path", ["holder_count"]),
    "长期户数": ("path", ["holder_count"]),
    "业绩预告": ("state", ["forecast"]),
    "预告区间过宽": ("state", ["forecast"]),
    "PB 历史分位": ("odds", ["pb"]),
    "PB vs ROE": ("odds", ["pb"]),
    "PS 历史分位": ("odds", ["ps"]),
    "股息率": ("odds", ["dividend_yield"]),
    "PE_TTM": ("odds", ["pe"]),
    "小盘亏损 + 高 PB 双杀": ("odds", ["pb"]),
}


class RedFlagError(ValueError):
    """红旗清单不合法(id 冲突 / 级别越界 / 归属节点未知)。"""


def _slug(text: str) -> str:
    """英文框架名 → ASCII slug; 非 ASCII 字符丢弃(id 需满足 ^[A-Za-z0-9_-]+$)。"""
    s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return s or "flag"


def flag_id(framework: str, signal: str) -> str:
    """脚本红旗的稳定 id: {framework-slug}-{signal 摘要 6 位}。

    只依赖 framework+signal 文本, 不依赖清单顺序——数值变化不改 id, 增量复查可按 id diff。
    """
    digest = hashlib.md5(f"{framework}|{signal}".encode("utf-8")).hexdigest()[:6]
    return f"{_slug(framework)}-{digest}"


def _level_of(severity: str) -> str:
    """'🟠 高' → '🟠'; 已是 emoji 的原样返回。"""
    head = (severity or "").strip().split()[0] if severity else ""
    if head in LEVEL_ORDER:
        return head
    for lvl in LEVELS:
        if lvl in (severity or ""):
            return lvl
    raise RedFlagError(f"无法识别红旗级别: {severity!r}")


def _home_of(framework: str, signal: str) -> tuple[str, list[str]]:
    """判定归属节点与首要关联指标: 信号级前缀优先, 退到框架级默认。"""
    for prefix, home in SIGNAL_MAP.items():
        if signal.startswith(prefix) or prefix in signal:
            return home[0], list(home[1])
    node, metrics = FRAMEWORK_MAP.get(framework, ("quality", []))
    return node, list(metrics)


def normalize_audit(audit: dict | list) -> list[dict]:
    """financial_audit 结果(dict 含 red_flags, 或裸 list)→ 契约红旗条目列表(source=script)。"""
    raw = audit.get("red_flags", []) if isinstance(audit, dict) else list(audit)
    items = []
    for entry in raw:
        framework = str(entry.get("framework", "")).strip() or "Audit"
        signal = str(entry.get("signal", "")).strip() or "未命名信号"
        node, metrics = _home_of(framework, signal)
        items.append({
            "id": flag_id(framework, signal),
            "level": _level_of(entry.get("severity", "")),
            "title": signal,
            "evidence": str(entry.get("evidence", "")).strip() or "(审计脚本未给证据)",
            "source": "script",
            "node": node,
            "metric_refs": metrics,
            # 附录D 展开用的脚本原始字段(非契约必需, schema 允许前向扩展)
            "framework": framework,
            "threshold": entry.get("threshold"),
            "implication": entry.get("implication"),
            "value": entry.get("value"),
        })
    return items


def collect_nominations(node_blocks: dict[str, dict]) -> list[dict]:
    """从四个节点 YAML 块收 red_flag_nominations, 补 source/node 缺省并按节点序稳定排列。"""
    out = []
    for node in NODES:
        block = node_blocks.get(node)
        if not block:
            continue
        for item in block.get("red_flag_nominations") or []:
            item = dict(item)
            item.setdefault("source", "nomination")
            item.setdefault("node", node)
            out.append(item)
    return out


def merge(script_flags: list[dict], nominations: list[dict]) -> list[dict]:
    """两源同池合并 → 附录D 清单。脚本在前、提名在后; id 冲突即报错(一条红旗一处归家)。"""
    merged: list[dict] = []
    seen: dict[str, dict] = {}
    for flag in list(script_flags) + list(nominations):
        fid = flag.get("id")
        if not fid:
            raise RedFlagError(f"红旗条目缺 id: {flag}")
        if fid in seen:
            raise RedFlagError(f"红旗 id 重复: {fid}(一条红旗只能归家一处)")
        if flag.get("level") not in LEVEL_ORDER:
            raise RedFlagError(f"红旗 {fid} 级别非法: {flag.get('level')!r}")
        if flag.get("node") not in NODES:
            raise RedFlagError(f"红旗 {fid} 归属节点非法: {flag.get('node')!r}")
        seen[fid] = flag
        merged.append(flag)
    return merged


def validate_flags(flags: list[dict]) -> list[str]:
    """附录D 合并产物过 schema(appendix-d.schema.json)。返回错误列表, 空=合法。"""
    return verdict_block.validate({"red_flags": flags}, "appendix-d")


def group_key(flag: dict) -> str:
    """分组键 = 首要关联指标; 无关联指标的条目自成一组(不与任何风险合并)。"""
    refs = flag.get("metric_refs") or []
    return refs[0] if refs else f"id:{flag['id']}"


def group_flags(flags: list[dict]) -> list[dict]:
    """按首要关联指标聚成风险组, 保持首次出现序。组级 level = 组内最严重。"""
    groups: dict[str, dict] = {}
    for idx, flag in enumerate(flags):
        key = group_key(flag)
        g = groups.get(key)
        if g is None:
            groups[key] = {"key": key, "flags": [flag], "first_index": idx}
        else:
            g["flags"].append(flag)
    out = []
    for g in groups.values():
        rep = min(g["flags"], key=lambda f: LEVEL_ORDER[f["level"]])
        out.append({
            "key": g["key"],
            "flags": g["flags"],
            "representative": rep,
            "level": rep["level"],
            "size": len(g["flags"]),
            "node": rep["node"],
            "first_index": g["first_index"],
        })
    return out


def _group_sort_key(g: dict) -> tuple:
    return (LEVEL_ORDER[g["level"]], -g["size"], NODE_ORDER[g["node"]], g["first_index"])


def top3(flags: list[dict]) -> list[dict]:
    """Top3 风险 = 红旗清单机器带出(零人工挑选)。同组多条红旗合并为一条。"""
    candidates = [g for g in group_flags(flags) if g["level"] in MARKED_LEVELS]
    if not candidates:
        candidates = group_flags(flags)
    if not candidates:
        raise RedFlagError("红旗清单为空, 无法带出 Top3")
    ranked = sorted(candidates, key=_group_sort_key)[:3]
    out = []
    for rank, g in enumerate(ranked, 1):
        rep = g["representative"]
        others = [f for f in g["flags"] if f["id"] != rep["id"]]
        evidence = rep["evidence"]
        for f in others:
            evidence += f" · {f['title']}({SOURCE_LABELS[f['source']]})"
        out.append({
            "rank": rank,
            "red_flag_id": rep["id"],
            "level": rep["level"],
            "title": rep["title"],
            "evidence": evidence,
            # 扩展字段: 供 lint 做红旗闭环机检 / HTML 层跳转
            "red_flag_ids": [f["id"] for f in g["flags"]],
            "node": rep["node"],
            "source": rep["source"],
        })
    return out


def _mark_entry(flags: list[dict]) -> dict | None:
    """一组命中同一指标的红旗 → 红标条目(级别/证据/来源/归属节点齐备)。无色档则返回 None。"""
    ranked = sorted(flags, key=lambda f: LEVEL_ORDER[f["level"]])
    mark = MARK_BY_LEVEL[ranked[0]["level"]]
    if not mark:
        return None
    return {
        "mark": mark,
        "level": ranked[0]["level"],
        "flags": [
            {
                "id": f["id"],
                "level": f["level"],
                "title": f["title"],
                "evidence": f["evidence"],
                "source": f["source"],
                "node": f["node"],
                "anchor": anchor(f["id"]),
            }
            for f in ranked
        ],
    }


def anchor(flag_id_: str) -> str:
    """附录D 条目锚点(HTML 层红标点击直达)。"""
    return f"flag-{flag_id_}"


def red_mark_map(flags: list[dict], indicators: list[dict] | None = None) -> dict:
    """红标反查映射数据。

    by_metric:    指标键 → 红标(正文/面板数字标色的数据源, 由红旗 metric_refs 反查)
    by_indicator: 面板指标名 → 红标(写手在面板块写的 red_flag_ref 解析结果)
    无红旗命中者不出现在映射里 = 不标色(05 推演点 1: ROE 难看但无规则命中 → 中性)。
    """
    by_id = {f["id"]: f for f in flags}
    per_metric: dict[str, list[dict]] = {}
    for flag in flags:
        for metric in flag.get("metric_refs") or []:
            per_metric.setdefault(metric, []).append(flag)

    by_metric = {}
    for metric, group in per_metric.items():
        entry = _mark_entry(group)
        if entry:
            by_metric[metric] = entry

    by_indicator = {}
    for ind in indicators or []:
        ref = ind.get("red_flag_ref")
        if not ref:
            continue
        flag = by_id.get(ref)
        if flag is None:
            raise RedFlagError(
                f"面板指标「{ind.get('name')}」的 red_flag_ref={ref!r} 在红旗清单里没有对应条目"
                "(红标只能反查红旗, 写手不得自行标红)"
            )
        entry = _mark_entry([flag])
        if entry:
            by_indicator[ind["name"]] = entry
    return {"by_metric": by_metric, "by_indicator": by_indicator}


def counts(flags: list[dict]) -> dict:
    """级别与来源统计(附录D 头部一行)。"""
    by_level = {lvl: sum(1 for f in flags if f["level"] == lvl) for lvl in LEVELS}
    by_source = {src: sum(1 for f in flags if f["source"] == src) for src in SOURCE_LABELS}
    return {"total": len(flags), "by_level": by_level, "by_source": by_source}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):      # Windows 控制台 GBK 下 print emoji 会炸
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--audit-json", required=True, help="financial_audit --json 产物")
    ap.add_argument("--out", required=True, help="输出 red_flags.json(写手引用 id 的来源)")
    args = ap.parse_args()

    audit_path = Path(args.audit_json)
    if not audit_path.exists():
        print(f"audit JSON 不存在: {audit_path}", file=sys.stderr)
        return 2
    flags = normalize_audit(json.loads(audit_path.read_text(encoding="utf-8")))
    errs = validate_flags(flags)
    if errs:
        for e in errs:
            print(f"✗ {e}", file=sys.stderr)
        return 1
    Path(args.out).write_text(
        json.dumps({"red_flags": flags}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    c = counts(flags)
    print(f"✓ {c['total']} 条脚本红旗 → {args.out}")
    print("  " + " · ".join(f"{lvl} {n}" for lvl, n in c["by_level"].items() if n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
