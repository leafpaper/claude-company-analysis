"""node_graph — v8 判断链依赖图: 把任意节点子集排成执行波次(全量与增量共用一套调度)。

依赖边(链手册 §1.2「写作顺序 ≠ 章节顺序」+ spec §6):

    ①质地 quality ─────────────────────┐
                       ┌→ ②状态 state ─┼→ ⑤决策 decision
    ③赔率 odds  ───────┤               │
                       └→ ④路径 path ──┘

  · ②状态 ← ③赔率: 四层验证第④关(价格是否已买完完美未来)直接引用赔率 verdict;
  · ④路径 ← ③赔率: 左尾深度 `depth_pct` 是「跌回③锚要跌多少」, 分母是③的锚与现价(票 11)。

全量 run = 五节点全跑 → 第一波 质地∥赔率 → 第二波 状态∥路径 → 第三波 决策。

★ **④路径为什么从第一波挪到第二波**(票 11 裁决):票 09 验收暴露 ③④ 同波时,
④第一波只拿得到**上一版**的③锚, 终稿两套锚并存, 靠评审轮回填 —— 这在左尾还是散文时
只是措辞不齐, 票 11 把左尾深度变成**数值字段**之后就是硬错。两个候选解里选了挪波次:
装配期占位只能让④"拿到"数字, 不能让它**据此推理**(「回吐到 F 是 −64%」本身就是④的结论),
而挪波次的代价是零 —— 第二波原本只有②一个节点在跑, ④并进去, 总波次仍是 3。
反向的引用(③手册 §6「地板见④」)是**指路**不是取数, 不构成环。
增量复查(`--review`)= 只跑分诊标脏的子集; 子集外的依赖由上一版 YAML 块盖「复用」戳供给,
因此**不进波次**, 但会被列进 external_deps 供调度校验(缺了就是脏调度, 不许开跑)。

CLI(主 agent 在 Phase 3 开跑前调用, 照着波次派活):
    python -m scripts.node_graph --all
    python -m scripts.node_graph --nodes state,path,decision
    python -m scripts.node_graph --nodes state --json
"""
from __future__ import annotations

import argparse
import json
import sys

# 规范顺序: 按判断链序号排(质地/赔率/路径/状态/决策), 让波次输出稳定可比
NODES: tuple[str, ...] = ("quality", "odds", "path", "state", "decision")

DEPS: dict[str, tuple[str, ...]] = {
    "quality": (),
    "odds": (),
    "path": ("odds",),          # 左尾 depth_pct 的分母 = ③的锚与现价(票 11)
    "state": ("odds",),
    "decision": ("quality", "state", "odds", "path"),
}

LABELS = {
    "quality": "①质地",
    "odds": "③赔率",
    "path": "④路径",
    "state": "②状态",
    "decision": "⑤决策",
}

AGENTS = {
    "quality": "node-quality",
    "odds": "node-odds",
    "path": "node-path",
    "state": "node-state",
    "decision": "decision-writer",
}

# 增量复查里永远重跑的节点(spec §8: 状态/赔率必重评; 路径每次对照新数据核销
# 证伪/左尾清单=重跑; 决策层+首页永远重装配)。质地是唯一可复用节点, 标脏才进来。
# triage 用它兜底, 本模块只声明不强制——调度器把它并进标脏集合后再排波。
ALWAYS_RERUN: tuple[str, ...] = ("state", "odds", "path", "decision")


class UnknownNode(ValueError):
    """节点名不在判断链上(拼错 / 用了旧 part 名)。"""


def normalize(nodes) -> list[str]:
    """去重 + 按规范顺序排列 + 校验节点名。"""
    if isinstance(nodes, str):
        nodes = [n.strip() for n in nodes.split(",")]
    wanted = {n for n in nodes if n}
    unknown = sorted(wanted - set(NODES))
    if unknown:
        raise UnknownNode(f"未知节点: {'、'.join(unknown)}(合法值: {'/'.join(NODES)})")
    return [n for n in NODES if n in wanted]


def plan_waves(nodes) -> list[list[str]]:
    """把子集排成波次: 同一波内无依赖关系, 可并行启动。

    子集外的依赖视为「上一版复用块已就位」, 不参与排序(见 external_deps)。
    """
    remaining = set(normalize(nodes))
    waves: list[list[str]] = []
    while remaining:
        # 就绪 = 它依赖的节点没有一个还排在后面(本轮不跑的依赖 → 复用块供给, 不算阻塞)
        wave = [n for n in NODES if n in remaining and not (set(DEPS[n]) & remaining)]
        if not wave:                       # 依赖图是 DAG, 正常走不到
            raise RuntimeError(f"依赖成环, 排不出波次: {sorted(remaining)}")
        waves.append(wave)
        remaining -= set(wave)
    return waves


def external_deps(nodes) -> dict[str, list[str]]:
    """子集外的依赖: {节点: [它依赖但本轮不跑的节点]}——这些必须有上版复用块。"""
    subset = set(normalize(nodes))
    out = {}
    for node in normalize(nodes):
        missing = [d for d in DEPS[node] if d not in subset]
        if missing:
            out[node] = missing
    return out


def describe(waves: list[list[str]]) -> list[str]:
    """人话波次说明, 一波一行(主 agent 直接抄进 main-log.md)。"""
    lines = []
    for i, wave in enumerate(waves, 1):
        who = " ∥ ".join(f"{LABELS[n]}({AGENTS[n]})" for n in wave)
        mode = "并行" if len(wave) > 1 else "单个"
        lines.append(f"第{i}波({mode}): {who}")
    return lines


def plan(nodes) -> dict:
    """完整调度计划(CLI 与 09 增量调度共用的返回结构)。"""
    ordered = normalize(nodes)
    waves = plan_waves(ordered)
    return {
        "nodes": ordered,
        "waves": waves,
        "agents": [[AGENTS[n] for n in wave] for wave in waves],
        "external_deps": external_deps(ordered),
        "reused": [n for n in NODES if n not in ordered],
        "describe": describe(waves),
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--nodes", help="逗号分隔的节点子集, 如 state,path,decision")
    g.add_argument("--all", action="store_true", help="全量 run: 五节点")
    ap.add_argument("--json", action="store_true", help="只输出 JSON(供脚本消费)")
    args = ap.parse_args()

    try:
        result = plan(NODES if args.all else args.nodes)
    except UnknownNode as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    for line in result["describe"]:
        print(line)
    if result["reused"]:
        print("复用上版块(不重跑): " + "、".join(LABELS[n] for n in result["reused"]))
    for node, deps in result["external_deps"].items():
        print(f"  ⚠️ {LABELS[node]} 依赖本轮不跑的 {'、'.join(LABELS[d] for d in deps)}——"
              "开跑前确认上版 YAML 块已拷贝并盖「复用」戳")
    print(json.dumps({"waves": result["waves"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
