"""compare — v8 产业链同行对比 `--compare`: 成组 / 并排装配 / 组内裁决校验(票 10)。

答的问题只有一个:**同行组里钱该放哪家**。

一页上下两半, 两半的性质完全不同 ——
  · 上半 = 各家决断卡并排。每一格都搬自那家最新 run 的装配产物(assembly.json)与节点
    YAML 块, **这里不产生任何新判断**;本模块做的是搬运、对齐、算基准日新鲜度。
  · 下半 = 「组内裁决」。全链唯一被允许说「谁比谁好」的地方, 由 compare-judge 写成
    `compare-judge.md` 顶部 YAML 块, 过 compare-judge.schema.json + 本模块四条机检。

**全报告制**: 只在有完整 v8 报告的成员间对比。缺报告的成员成组时就列出来(missing_members),
由用户决定先补跑哪几家 —— 不为对比另建一条 peer-lite 轻判断管线(两套判断口径必打架)。

目录(对比组不属于任何一家公司, 落 output 根下):
    output/_compare/{slug}/
    ├── group.json                    组定义(锚 + 成员 + 来源, 过 compare-group.schema.json)
    ├── compare-judge.md              组内裁决(compare-judge 写, 顶部 YAML 块)
    ├── compare.json                  装配产物(过 compare.schema.json)= 出片与站点的唯一输入
    └── {slug}-compare-{date}.md      本地 md 底稿

CLI(主 agent 按 phases/compare-pipeline.md 调用):
    python -m scripts.compare candidates --anchor 东山精密
    python -m scripts.compare init --anchor 东山精密 --slug pcb-optics --name "PCB-光模块产业链" \
        --member "中际旭创:300308.SZ:longbridge" --member "沪电股份:002463.SZ:library"
    python -m scripts.compare assemble --slug pcb-optics [--require-judge]
    python -m scripts.compare status --slug pcb-optics [--json]
退出码: 0 = 成功 · 2 = 输入不完整(组不存在 / 有报告成员不足 2 家 / 缺裁决且要求了 --require-judge)。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

from . import assembly
from . import config
from . import manifest as manifest_mod
from . import verdict_block

GROUP_NAME = "group.json"
PRODUCT_NAME = "compare.json"
JUDGE_NAME = "compare-judge.md"

# 基准日超过这个天数标「陈旧」并提示先 --review(spec §9: 90 天 ≈ 一个披露季)
STALE_THRESHOLD_DAYS = 90

MEMBER_SOURCES = ("anchor", "longbridge", "library", "model")

# 并排表的行序 —— 五问顺序与单报告决断卡一致(assembly.CARD_ROWS)
CARD_QUESTIONS = tuple(question for question, _ in assembly.CARD_ROWS)

# 行动档位的进攻度(并排列序用;与 assembly.GEAR_BANDS 同一份六档词表)
GEAR_ORDER = {gear: i for i, gear in enumerate(
    ("核心仓", "期权仓", "等证据临界", "不追高", "减仓", "回避"))}


class CompareError(ValueError):
    """成组 / 装配 / 裁决校验的输入错误 —— 一律拒绝产半成品对比页。"""


class MissingReport(CompareError):
    """这家成员没有可用的 v8 报告(全报告制下不进上半, 进 missing_members)。"""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


# ---------------------------------------------------------------- slug / 目录

_SLUG_CLEAN = re.compile(r"[^a-z0-9]+")
_TICKER_SUFFIX = re.compile(r"\.(SH|SZ|BJ|HK|US)$", re.I)


def slugify(text: str) -> str:
    """英文短名 → kebab-case slug;中文/符号会被清成空, 由调用方兜底。"""
    return _SLUG_CLEAN.sub("-", (text or "").strip().lower()).strip("-")


def default_slug(ticker: str, company: str = "") -> str:
    """兜底组名 `{锚ticker}-peers`(spec §9);ticker 也不可用时退回公司名 slug。"""
    base = slugify(_TICKER_SUFFIX.sub("", ticker or ""))
    return f"{base}-peers" if base else (slugify(company) or "peers")


# 对比组不属于任何一家公司, 落 output 根下的 _compare/
COMPARE_DIRNAME = "_compare"


def find_company_dir(company: str) -> Path | None:
    """找已存在的公司目录(**不创建**), 顺序同 config.output_dir 的解析规则。

    消费侧(对比装配)必须和产出侧问同一个人, 否则装好的 skill 从别处跑就找不到刚写的报告
    (票 08 发布时踩过一次)。找不到返回 None —— 由调用方决定这算不算错。
    这两个 helper 长在这里而不是 config.py: 那个文件是 skip-worktree 的(护着本地 token,
    HEAD 里没有), 放进去等于写了一段永远进不了库的代码。
    """
    for root in (config.PLUGIN_ROOT / "output", config.SKILL_ROOT / "output", Path("output")):
        candidate = root / company
        if candidate.exists():
            return candidate
    return None


def compare_root(root: Path | None = None) -> Path:
    """对比组的根目录 output/_compare/(与公司目录同一个 output 根)。"""
    return Path(root) if root else config.OUTPUT_ROOT / COMPARE_DIRNAME


def group_dir(slug: str, root: Path | None = None) -> Path:
    return compare_root(root) / slug


def list_groups(root: Path | None = None) -> list[str]:
    base = compare_root(root)
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if (p / GROUP_NAME).exists())


# ---------------------------------------------------------------- 组定义 CRUD

def load_group(slug: str, root: Path | None = None) -> dict:
    path = group_dir(slug, root) / GROUP_NAME
    if not path.exists():
        raise CompareError(f"对比组不存在: {path}(先跑 compare init)")
    group = json.loads(path.read_text(encoding="utf-8"))
    errs = verdict_block.validate(group, "compare-group")
    if errs:
        raise CompareError(f"{path} 不合契约:\n  - " + "\n  - ".join(errs))
    return group


def save_group(group: dict, root: Path | None = None) -> Path:
    errs = verdict_block.validate(group, "compare-group")
    if errs:
        raise CompareError("组定义不合契约, 拒绝写入:\n  - " + "\n  - ".join(errs))
    if group["anchor"] not in [m["company"] for m in group["members"]]:
        raise CompareError(f"锚公司 {group['anchor']} 不在成员名单里(锚必须自己也在组内)")
    gdir = group_dir(group["slug"], root)
    gdir.mkdir(parents=True, exist_ok=True)
    path = gdir / GROUP_NAME
    path.write_text(json.dumps(group, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def parse_member(spec: str) -> dict:
    """`公司:ticker[:source[:备注]]` → 成员 dict(CLI 用;source 缺省 model)。"""
    parts = [p.strip() for p in str(spec).split(":")]
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise CompareError(f"成员写法应为 `公司:ticker[:source[:备注]]`, 收到: {spec}")
    member = {"company": parts[0], "ticker": parts[1], "source": "model"}
    if len(parts) >= 3 and parts[2]:
        if parts[2] not in MEMBER_SOURCES:
            raise CompareError(f"source 只能是 {'/'.join(MEMBER_SOURCES)}, 收到: {parts[2]}")
        member["source"] = parts[2]
    if len(parts) >= 4 and parts[3]:
        member["note"] = parts[3]
    return member


def create_group(
    anchor: str,
    anchor_ticker: str = "",
    members: list[dict] | None = None,
    slug: str | None = None,
    name: str | None = None,
    chain_note: str | None = None,
    created: str | None = None,
    root: Path | None = None,
) -> dict:
    """建组并把 slug 登记进每个成员的 manifest.compare_groups(有 manifest 的才登记)。

    候选是怎么查出来的(Longbridge / 库内 peer / 模型兜底)记在 member.source 里 ——
    验收「三路优先级」时可回查, 也让下次成组知道哪几家是模型猜的。
    """
    members = [dict(m) for m in (members or [])]
    if not any(m["company"] == anchor for m in members):
        members.insert(0, {"company": anchor, "ticker": anchor_ticker, "source": "anchor"})
    for m in members:
        m.setdefault("source", "model")
        if not m.get("ticker"):
            company_dir = find_company_dir(m["company"])
            existing = manifest_mod.load(company_dir) if company_dir else None
            m["ticker"] = (existing or {}).get("ticker") or m["company"]

    anchor_member = next(m for m in members if m["company"] == anchor)
    group = {
        "slug": slug or default_slug(anchor_member["ticker"], anchor),
        "name": name or f"{anchor} 产业链同行对比",
        "anchor": anchor,
        "created": created or _dt.date.today().isoformat(),
        "members": members,
    }
    if chain_note:
        group["chain_note"] = chain_note
    save_group(group, root)
    for m in members:
        company_dir = find_company_dir(m["company"])
        if company_dir:
            manifest_mod.add_compare_group(company_dir, group["slug"])
    return group


# ---------------------------------------------------------------- 候选:库内 peer(优先级②)

def library_candidates(anchor: str) -> list[dict]:
    """报告库内已有 manifest 的其他公司 = 候选优先级②(脚本能查的那一路)。

    ① Longbridge 产业链/成分股 与 ③ 模型按业务描述兜底都要工具或模型, 归主 agent
    (见 phases/compare-pipeline.md);本函数只回答「库里还有谁, 各自有没有可用报告」。
    """
    out: list[dict] = []
    seen: set[str] = set()
    for candidate_root in (config.PLUGIN_ROOT / "output", config.SKILL_ROOT / "output", Path("output")):
        if not candidate_root.is_dir():
            continue
        for company_dir in sorted(candidate_root.iterdir()):
            name = company_dir.name
            if not company_dir.is_dir() or name == anchor or name.startswith("_") or name in seen:
                continue
            seen.add(name)
            m = manifest_mod.load(company_dir)
            try:
                if not m:
                    # 库里有这个名字但没有 v8 manifest(多半是 v8 之前的旧版报告)——
                    # 照样列出来: 它是合法候选, 只是要先补跑一次全量才能进对比
                    raise MissingReport("没有 v8 manifest(旧版报告不进对比, 需先跑一次全量)")
                snapshot = member_snapshot(name, company_dir)
                ready, detail = True, f"最新报告 {snapshot['report_date']}({snapshot['run_type']})"
            except MissingReport as exc:
                ready, detail = False, exc.reason
            out.append({
                "company": name, "ticker": (m or {}).get("ticker") or "", "market": (m or {}).get("market"),
                "source": "library", "report_ready": ready, "detail": detail,
            })
    return out


# ---------------------------------------------------------------- 成员快照(上半的每一格)

def _load_product_json(run_dir: Path) -> dict:
    for candidate in (run_dir / "assembly" / "assembly.json", run_dir / "assembly.json"):
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    raise MissingReport(f"最新 run {run_dir.name} 没有装配产物 assembly/assembly.json(报告没跑完)")


def _read_odds_fields(run_dir: Path) -> dict:
    """从③赔率节点块里只取区间锚与现价(读不出来返回空 dict, 由调用方降级标注)。"""
    path = Path(run_dir) / "nodes" / assembly.NODE_FILES["odds"]
    if not path.exists():
        return {}
    try:
        block = verdict_block.extract_yaml_block(path.read_text(encoding="utf-8"))
    except (verdict_block.BlockNotFound, OSError, ValueError):
        return {}
    return {k: block[k] for k in ("anchor_range", "current_price") if block.get(k)}


def _age_days(report_date: str, today: str) -> int:
    delta = _dt.date.fromisoformat(today) - _dt.date.fromisoformat(report_date)
    return max(delta.days, 0)


def _site_slug(company: str, ticker: str) -> str:
    """站点报告目录名 —— 与 update_index 同一套命名, 否则对比页点回去是死链。"""
    from .update_index import _slug_from_company

    return _slug_from_company(company, ticker)


def member_snapshot(
    company: str,
    company_dir: Path,
    today: str | None = None,
    stale_days: int = STALE_THRESHOLD_DAYS,
) -> dict:
    """一家成员的并排卡片数据 —— 全部搬自它自己的最新 run, 一个字都不新判断。

    拿不到可用报告就抛 MissingReport(带原因), 由 assemble 收进 missing_members。
    """
    today = today or _dt.date.today().isoformat()
    company_dir = Path(company_dir)
    m = manifest_mod.load(company_dir)
    if not m:
        raise MissingReport("没有 manifest.json(这家还没跑过 v8 分析)")
    if not m.get("runs"):
        raise MissingReport("manifest 里没有 run 记录")

    latest = m["runs"][-1]
    run_dir = company_dir / "runs" / latest["date"]
    if not run_dir.is_dir():
        raise MissingReport(f"manifest 记的最新 run {latest['date']} 目录不存在")
    product = _load_product_json(run_dir)
    # 只校验对比页真正消费的三处(compare-member-source), 不拿整份 assembly.schema 去卡 ——
    # 成员报告是不同时间产出的, 用今天的完整契约去判昨天的完整报告, 会把它误判成「缺报告」。
    core = {k: product[k] for k in ("verdict_card", "top3", "metadata") if k in product}
    errs = verdict_block.validate(core, "compare-member-source")
    if errs:
        raise MissingReport(f"最新 run {latest['date']} 的装配产物缺对比页要用的字段: {errs[0]}")

    meta = product["metadata"]
    age = _age_days(latest["date"], today)
    snapshot = {
        "company": company,
        "ticker": m.get("ticker") or "",
        "market": m.get("market"),
        "report_date": latest["date"],
        "run_type": latest["type"],
        "age_days": age,
        "stale": age > stale_days,
        "action_gear": meta["action_gear"],
        "quality_field": meta["quality_field"],
        "verdict_plain": meta["verdict_plain"],
        "verdict_card": [dict(row) for row in product["verdict_card"]],
        "top3": [dict(item) for item in product["top3"]],
    }
    next_disclosure = meta.get("next_disclosure_date") or m.get("next_disclosure_date")
    if next_disclosure:
        snapshot["next_disclosure_date"] = next_disclosure
    flags = product.get("red_flags") or []
    if flags:
        snapshot["red_flag_counts"] = dict(Counter(f["level"] for f in flags))

    # ③赔率的区间锚要结构化 —— 并排表按数字对齐, 不能只有决断卡里那句话。
    # 同样**只读这两个字段**: 整块过 node-odds.schema 会因为无关的契约演进(如票 11 加的
    # derivation 必填)读不出一份完好旧报告的锚, 而对比页压根不消费 derivation。
    odds = _read_odds_fields(run_dir)
    if odds:
        errs = verdict_block.validate({**core, **odds}, "compare-member-source")
        if errs:
            snapshot["degraded"] = [f"③赔率的区间锚不合契约, 本页留空({errs[0]})"]
            odds = {}
    else:
        snapshot["degraded"] = ["③赔率节点块读不出区间锚, 本页留空"]
    snapshot.update(odds)

    md = run_dir / f"{company}-analysis-{latest['date']}.md"
    if md.exists():
        snapshot["report_md"] = str(md)
    snapshot["report_href"] = f"../../reports/{_site_slug(company, snapshot['ticker'])}/分析报告_dashboard.html"
    return snapshot


# ---------------------------------------------------------------- 组内裁决:载入 + 四条机检

_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _numbers(text: str) -> set[str]:
    """文本里的数字 token(小数去掉尾零, 让 57 与 57.0 算同一个数)。"""
    out = set()
    for raw in _NUMBER.findall(str(text or "")):
        out.add(raw.rstrip("0").rstrip(".") if "." in raw else raw)
    return out


def _sourced_numbers(members: list[dict]) -> set[str]:
    """全组卡片上出现过的数字池 —— 裁决只能引用池里的数。"""
    texts: list[str] = []
    for m in members:
        texts += [row["verdict"] for row in m["verdict_card"]]
        texts += [item["title"] for item in m["top3"]]
        texts += [item["evidence"] for item in m["top3"]]
        texts += [m["quality_field"], m["action_gear"], m.get("verdict_plain") or "", m["report_date"]]
        anchor = m.get("anchor_range") or {}
        for end in ("low", "high"):
            if anchor.get(end):
                texts.append(assembly._fmt_number(anchor[end]["value"]))
        if m.get("current_price"):
            texts.append(assembly._fmt_number(m["current_price"]["value"]))
        texts += [str(count) for count in (m.get("red_flag_counts") or {}).values()]
    pool: set[str] = set()
    for t in texts:
        pool |= _numbers(t)
    return pool


def unsourced_numbers(text: str, pool: set[str]) -> list[str]:
    """裁决句里回不到组内卡片的数字。

    只查「像证据的数」——带小数点的, 或两位以上的整数。个位裸数字(排名第 1、3 家、5/5)
    放过: 它们是行文, 不是新证据, 卡这种数只会逼出「第一名」这类更难读的写法。
    """
    return sorted(n for n in _numbers(text) if ("." in n or len(n) >= 2) and n not in pool)


def check_judge(judge: dict, members: list[dict]) -> list[str]:
    """裁决四条机检(schema 之外):具名成员 / 排名连号 / 全组覆盖 / 数字回得了源。"""
    problems: list[str] = []
    names = [m["company"] for m in members]
    ranked = [r["company"] for r in judge["ranking"]]

    for company in ranked:
        if company not in names:
            problems.append(
                f"裁决排了「{company}」, 但它不是本组有报告的成员(全报告制: 只在有报告的成员间排序)"
            )
    absent = [n for n in names if n not in ranked]
    if absent:
        problems.append(f"裁决漏了成员: {'、'.join(absent)}(有报告的成员一个都不能不排)")
    if len(set(ranked)) != len(ranked):
        problems.append("裁决里有重复公司")

    ranks = sorted(r["rank"] for r in judge["ranking"])
    if ranks != list(range(1, len(ranks) + 1)):
        problems.append(f"rank 必须从 1 连号, 收到: {ranks}")

    pool = _sourced_numbers(members)
    by_company = {m["company"]: m for m in members}
    checks = [("verdict", judge["verdict"]), ("common_risk", judge.get("common_risk") or "")]
    checks += [(f"ranking[{r['rank']}] {r['company']}", r["one_liner"]) for r in judge["ranking"]]
    checks.append(("not_comparable", "；".join(judge.get("not_comparable") or [])))
    for where, text in checks:
        bad = unsourced_numbers(text, pool)
        if bad:
            problems.append(
                f"{where}: 数字 {'、'.join(bad)} 在全组决断卡上找不到出处"
                "(裁决只引用不自产证据 —— 要用新数字, 先让它进那家的报告)"
            )
    for item in judge["ranking"]:
        member = by_company.get(item["company"])
        if member and "decision" in item["basis"] and not member.get("verdict_plain"):
            problems.append(f"{item['company']}: basis 引用了 decision, 但这家没有决策层结论")
    return problems


def load_judge(slug: str, members: list[dict], root: Path | None = None) -> dict | None:
    """读组内裁决 md 顶部 YAML 块, 过 schema + 四条机检;文件不存在返回 None。"""
    path = group_dir(slug, root) / JUDGE_NAME
    if not path.exists():
        return None
    try:
        judge, errs = verdict_block.load_and_validate(path, "compare-judge")
    except verdict_block.BlockNotFound as exc:
        raise CompareError(f"{path}: {exc}") from exc
    if errs:
        raise CompareError(f"{JUDGE_NAME} 不过 schema:\n  - " + "\n  - ".join(errs))
    if judge["group"] != slug:
        raise CompareError(f"{JUDGE_NAME} 的 group={judge['group']} 与本组 {slug} 对不上")
    problems = check_judge(judge, members)
    if problems:
        raise CompareError(f"{JUDGE_NAME} 未过组内裁决机检:\n  - " + "\n  - ".join(problems))
    return judge


# ---------------------------------------------------------------- 装配

def build_notes(members: list[dict], missing: list[dict], judge: dict | None,
                stale_days: int = STALE_THRESHOLD_DAYS) -> list[str]:
    """页面顶部的机器提示 —— 陈旧成员 / 缺报告 / 裁决未产出, 一句话一条。"""
    notes = []
    stale = [m for m in members if m["stale"]]
    if stale:
        notes.append(
            f"⚠️ 基准日超 {stale_days} 天(陈旧): "
            + "、".join(f"{m['company']} {m['report_date']}({m['age_days']} 天前)" for m in stale)
            + " —— 先跑 `--review` 复查再比, 别拿三个月前的判断跟昨天的判断硬比"
        )
    if missing:
        notes.append(
            "🕳️ 缺完整报告、未进对比: "
            + "、".join(f"{m['company']}({m['reason']})" for m in missing)
            + " —— 全报告制不给它们凑数, 补跑后重装配即可并入"
        )
    degraded = [m for m in members if m.get("degraded")]
    if degraded:
        notes.append(
            "ℹ️ 有格子读不出来、页面留空: "
            + "；".join(f"{m['company']}({'；'.join(m['degraded'])})" for m in degraded)
        )
    if judge is None:
        notes.append("⏳ 组内裁决尚未产出(上半并排卡片已就绪, 跑 compare-judge 后重装配)")
    return notes


def assemble(
    slug: str,
    today: str | None = None,
    stale_days: int = STALE_THRESHOLD_DAYS,
    require_judge: bool = False,
    root: Path | None = None,
) -> dict:
    """组定义 + 各家最新 run → compare.json(过 compare.schema.json)+ 本地 md 底稿。"""
    today = today or _dt.date.today().isoformat()
    group = load_group(slug, root)

    members: list[dict] = []
    missing: list[dict] = []
    for entry in group["members"]:
        company = entry["company"]
        company_dir = find_company_dir(company)
        try:
            if company_dir is None:
                raise MissingReport("output/ 下没有这家的目录(从没分析过)")
            snapshot = member_snapshot(company, company_dir, today=today, stale_days=stale_days)
        except MissingReport as exc:
            missing.append({
                "company": company,
                "ticker": entry.get("ticker", ""),
                "source": entry["source"],
                "reason": exc.reason,
                "command": f"/company-analysis {company} {entry.get('ticker', '')}".strip(),
            })
            continue
        snapshot["is_anchor"] = company == group["anchor"]
        if entry.get("market") and not snapshot.get("market"):
            snapshot["market"] = entry["market"]
        members.append(snapshot)

    if len(members) < 2:
        have = "、".join(m["company"] for m in members) or "无"
        lack = "、".join(m["company"] for m in missing) or "无"
        raise CompareError(
            f"有完整报告的成员只有 {len(members)} 家({have}), 对比至少要 2 家。"
            f"缺报告的: {lack} —— 全报告制: 先补跑再回来"
        )

    # 锚排头, 其余按行动档位的进攻度排(同档按公司名), 让读者的眼睛有落点
    members.sort(key=lambda m: (not m["is_anchor"], GEAR_ORDER.get(m["action_gear"], 9), m["company"]))

    judge = load_judge(slug, members, root)
    if judge is None and require_judge:
        raise CompareError(
            "组内裁决未产出: 先让 compare-judge 读 compare.json 写 "
            f"{group_dir(slug, root) / JUDGE_NAME}, 再重跑装配"
        )

    product = {
        "group": {k: group[k] for k in ("slug", "name", "anchor")},
        "generated": today,
        "stale_threshold_days": stale_days,
        "members": members,
        "missing_members": missing,
        "notes": build_notes(members, missing, judge, stale_days),
    }
    if group.get("chain_note"):
        product["group"]["chain_note"] = group["chain_note"]
    if judge:
        product["judge"] = judge

    errs = verdict_block.validate(product, "compare")
    if errs:
        raise CompareError("对比装配产物不过 schema:\n  - " + "\n  - ".join(errs))

    gdir = group_dir(slug, root)
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / PRODUCT_NAME).write_text(
        json.dumps(product, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (gdir / md_name(slug, today)).write_text(render_md(product), encoding="utf-8")
    return product


def md_name(slug: str, date: str) -> str:
    return f"{slug}-compare-{date}.md"


def load_product(slug: str, root: Path | None = None) -> dict:
    path = group_dir(slug, root) / PRODUCT_NAME
    if not path.exists():
        raise CompareError(f"还没装配过这个组: {path}(先跑 compare assemble)")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- md 底稿

def anchor_text(member: dict) -> str:
    """区间锚一格: 两端 + 单位 (+ 现价 / 不同向标记), 与单报告决断卡同一套措辞。"""
    anchor = member.get("anchor_range")
    if not anchor:
        return "–"
    low, high = anchor["low"], anchor["high"]
    unit = low.get("unit") or high.get("unit") or ""
    text = f"{assembly._fmt_number(low['value'])}-{assembly._fmt_number(high['value'])}"
    if unit:
        text += f" {unit}"
    if not anchor.get("same_direction", True):
        text += "(两端不同向)"
    price = member.get("current_price")
    if price:
        price_unit = price.get("unit") or unit
        text += f" vs 现价 {assembly._fmt_number(price['value'])}"
        if price_unit:
            text += f" {price_unit}"
    return text


def date_text(member: dict) -> str:
    kind = "全量" if member["run_type"] == "full" else "增量"
    text = f"{member['report_date']}({kind}, {member['age_days']} 天前)"
    return text + " ⚠️陈旧" if member["stale"] else text


def flags_text(member: dict) -> str:
    counts = member.get("red_flag_counts") or {}
    if not counts:
        return "–"
    return " ".join(f"{level}{counts[level]}" for level in ("🔴", "🟠", "🟡", "🟢", "ℹ️") if counts.get(level))


def top3_text(member: dict, sep: str = "<br>") -> str:
    return sep.join(f"{item['rank']}. {item['level']} {item['title']}" for item in member["top3"])


def _row(label: str, cells: list[str]) -> str:
    return f"| {label} | " + " | ".join(c or "–" for c in cells) + " |"


def render_md(product: dict) -> str:
    """compare.json → 本地 md 底稿(= HTML 与站点的正文源, 机器渲染, 无人工位)。"""
    members = product["members"]
    group = product["group"]
    lines = [
        f"# {group['name']} — 产业链同行对比",
        "",
        f"> 组 `{group['slug']}` · 锚定 **{group['anchor']}** · 生成于 {product['generated']} · "
        f"{len(members)} 家有完整报告"
        + (f" · {len(product['missing_members'])} 家缺报告" if product["missing_members"] else ""),
    ]
    if group.get("chain_note"):
        lines += ["", f"**同行口径**:{group['chain_note']}"]
    if product.get("notes"):
        lines += [""] + [f"- {n}" for n in product["notes"]]

    heads = [
        f"**{m['company']}**<br>{m['ticker']}" + ("(锚)" if m["is_anchor"] else "")
        for m in members
    ]
    lines += [
        "",
        "## 一、各家决断卡并排",
        "",
        "> 每一格都搬自那家最新 run 的装配产物与节点 YAML 块,**本页不产生新判断**;"
        "点公司名回到那份完整报告。",
        "",
        "| | " + " | ".join(heads) + " |",
        "|---|" + "---|" * len(members),
        _row("基准日", [date_text(m) for m in members]),
        _row("行动档位", [f"**{m['action_gear']}**" for m in members]),
    ]
    for i, question in enumerate(CARD_QUESTIONS):
        lines.append(_row(question, [m["verdict_card"][i]["verdict"] for m in members]))
    lines += [
        _row("区间锚", [anchor_text(m) for m in members]),
        _row("红旗", [flags_text(m) for m in members]),
        _row("Top3 风险", [top3_text(m) for m in members]),
        _row("下次披露", [m.get("next_disclosure_date") or "–" for m in members]),
    ]

    lines += ["", "## 二、组内裁决"]
    judge = product.get("judge")
    if not judge:
        lines += ["", "⏳ 裁决尚未产出 —— compare-judge 读 `compare.json` 写 `compare-judge.md` 后重跑装配。"]
    else:
        lines += [
            "",
            f"> **{judge['verdict']}**",
            "",
            "| 排序 | 公司 | 一句话原因 | 依据 |",
            "|:--:|---|---|---|",
        ]
        for item in sorted(judge["ranking"], key=lambda r: r["rank"]):
            basis = "、".join(assembly.NODE_LABELS.get(b, b) for b in item["basis"])
            lines.append(f"| {item['rank']} | {item['company']} | {item['one_liner']} | {basis} |")
        if judge.get("common_risk"):
            lines += ["", f"**全组共担**:{judge['common_risk']}"]
        if judge.get("not_comparable"):
            lines += ["", "**这次不可比的维度**:"] + [f"- {x}" for x in judge["not_comparable"]]

    if product["missing_members"]:
        lines += [
            "",
            "## 三、缺报告成员(未进对比)",
            "",
            "| 公司 | ticker | 候选来源 | 原因 | 补跑 |",
            "|---|---|---|---|---|",
        ]
        for m in product["missing_members"]:
            lines.append(
                f"| {m['company']} | {m.get('ticker') or '–'} | {m.get('source') or '–'} | "
                f"{m['reason']} | `{m.get('command') or '–'}` |"
            )

    lines += [
        "",
        "---",
        "",
        "由 company-analysis v8 `--compare` 机器装配 · 上半零新判断 · "
        f"下半唯一判断节点 = compare-judge · 基准日超 {product['stale_threshold_days']} 天标陈旧",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- 状态(--review 收尾联动)

def status(slug: str, today: str | None = None, root: Path | None = None) -> dict:
    """对比页跟成员报告同不同步 —— `--review` 收尾靠它决定要不要提示重装配。"""
    today = today or _dt.date.today().isoformat()
    group = load_group(slug, root)
    try:
        product = load_product(slug, root)
    except CompareError:
        product = None

    known = {m["company"]: m["report_date"] for m in (product or {}).get("members", [])}
    outdated: list[dict] = []
    unchanged: list[dict] = []
    still_missing: list[dict] = []
    for entry in group["members"]:
        company = entry["company"]
        company_dir = find_company_dir(company)
        try:
            if company_dir is None:
                raise MissingReport("output/ 下没有这家的目录")
            snapshot = member_snapshot(company, company_dir, today=today)
        except MissingReport as exc:
            still_missing.append({"company": company, "reason": exc.reason})
            continue
        if company not in known:
            outdated.append({"company": company, "was": None, "now": snapshot["report_date"]})
        elif known[company] != snapshot["report_date"]:
            outdated.append({"company": company, "was": known[company], "now": snapshot["report_date"]})
        else:
            unchanged.append({"company": company, "report_date": snapshot["report_date"]})

    reasons = []
    if product is None:
        reasons.append("这个组还没装配过")
    if outdated:
        reasons.append("成员报告已更新: " + "、".join(
            f"{o['company']} {o['was'] or '(新入组)'}→{o['now']}" for o in outdated))
    if product is not None and "judge" not in product:
        reasons.append("组内裁决尚未产出")

    return {
        "slug": slug,
        "generated": (product or {}).get("generated"),
        "needs_rebuild": bool(reasons),
        "reasons": reasons,
        "outdated_members": outdated,
        "unchanged_members": unchanged,
        "missing_members": still_missing,
        "stale_members": [m["company"] for m in (product or {}).get("members", []) if m.get("stale")],
    }


def groups_of(company: str) -> list[str]:
    """这家公司在哪些对比组里(manifest.compare_groups)—— `--review` 收尾第一问。"""
    company_dir = find_company_dir(company)
    m = manifest_mod.load(company_dir) if company_dir else None
    return list((m or {}).get("compare_groups") or [])


# ---------------------------------------------------------------- CLI

def _print_group(group: dict) -> None:
    print(f"组 {group['slug']} · {group['name']} · 锚 {group['anchor']} · 建于 {group['created']}")
    for m in group["members"]:
        mark = "⚓" if m["company"] == group["anchor"] else " "
        print(f"  {mark} {m['company']} {m['ticker']}  [{m['source']}]"
              + (f"  {m['note']}" if m.get("note") else ""))


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_cand = sub.add_parser("candidates", help="库内 peer 候选(优先级②;①Longbridge 与③模型兜底归主 agent)")
    p_cand.add_argument("--anchor", required=True)
    p_cand.add_argument("--json", action="store_true")

    p_init = sub.add_parser("init", help="建组(用户确认成员之后)")
    p_init.add_argument("--anchor", required=True)
    p_init.add_argument("--anchor-ticker", default="")
    p_init.add_argument("--slug", help="组 slug(缺省 {锚ticker}-peers)")
    p_init.add_argument("--name", help="组的人话名字")
    p_init.add_argument("--chain-note", help="这组凭什么算同行, 一句话")
    p_init.add_argument("--member", action="append", default=[],
                        metavar="公司:ticker[:source[:备注]]",
                        help="可重复; source=longbridge|library|model")
    p_init.add_argument("--date", help="建组日期(默认今天)")

    p_asm = sub.add_parser("assemble", help="装配对比页(compare.json + md 底稿)")
    p_asm.add_argument("--slug", required=True)
    p_asm.add_argument("--date", help="生成日(默认今天, 决定陈旧判定的基准)")
    p_asm.add_argument("--require-judge", action="store_true", help="没有组内裁决就报错(发布前用)")
    p_asm.add_argument("--json", action="store_true")

    p_st = sub.add_parser("status", help="对比页与成员报告同不同步(--review 收尾联动)")
    p_st.add_argument("--slug")
    p_st.add_argument("--company", help="查这家在哪些组里, 逐组报状态")
    p_st.add_argument("--json", action="store_true")

    sub.add_parser("list", help="列出所有对比组")
    args = ap.parse_args()

    try:
        if args.cmd == "list":
            slugs = list_groups()
            if not slugs:
                print("还没有对比组(compare init 建一个)")
            for slug in slugs:
                _print_group(load_group(slug))
            return 0

        if args.cmd == "candidates":
            cands = library_candidates(args.anchor)
            if args.json:
                print(json.dumps(cands, ensure_ascii=False, indent=2))
                return 0
            print(f"库内候选(优先级②)· 锚 {args.anchor} · {len(cands)} 家")
            for c in cands:
                mark = "✅" if c["report_ready"] else "🕳️"
                print(f"  {mark} {c['company']} {c['ticker']} — {c['detail']}")
            print("\n① Longbridge 产业链/成分股 与 ③ 模型按业务描述兜底由主 agent 补齐;"
                  "候选**必经用户确认/增删**才能成组。")
            return 0

        if args.cmd == "init":
            group = create_group(
                anchor=args.anchor, anchor_ticker=args.anchor_ticker,
                members=[parse_member(s) for s in args.member],
                slug=args.slug, name=args.name, chain_note=args.chain_note, created=args.date,
            )
            print(f"✅ 建组: {group_dir(group['slug']) / GROUP_NAME}")
            _print_group(group)
            print(f"\n下一步: python -m scripts.compare assemble --slug {group['slug']}")
            return 0

        if args.cmd == "assemble":
            product = assemble(args.slug, today=args.date, require_judge=args.require_judge)
            if args.json:
                print(json.dumps(product, ensure_ascii=False, indent=2))
                return 0
            gdir = group_dir(args.slug)
            print(f"✅ 装配 {args.slug}: {len(product['members'])} 家并排"
                  + (f", {len(product['missing_members'])} 家缺报告" if product["missing_members"] else "")
                  + (", 含组内裁决" if product.get("judge") else ", 裁决未产出"))
            for note in product["notes"]:
                print(f"   {note}")
            print(f"   {gdir / PRODUCT_NAME}")
            print(f"   {gdir / md_name(args.slug, product['generated'])}")
            return 0

        if args.cmd == "status":
            slugs = [args.slug] if args.slug else groups_of(args.company or "")
            if not slugs:
                print("没有对应的对比组")
                return 0
            results = [status(slug) for slug in slugs]
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
                return 0
            for r in results:
                head = "需要重装配" if r["needs_rebuild"] else "已是最新"
                print(f"{r['slug']}: {head}(上次装配 {r['generated'] or '从未'})")
                for reason in r["reasons"]:
                    print(f"   - {reason}")
                if r["stale_members"]:
                    print(f"   - 陈旧成员(超 {STALE_THRESHOLD_DAYS} 天): "
                          f"{'、'.join(r['stale_members'])} → 建议先 --review")
                if r["missing_members"]:
                    print("   - 缺报告: " + "、".join(
                        f"{m['company']}({m['reason']})" for m in r["missing_members"]))
            return 0
    except CompareError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
