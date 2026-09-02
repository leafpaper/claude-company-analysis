"""derivation — ③赔率估值推导的结构化数据: 算术闭合校验 + 三张表的机器渲染。

**起因**(票 11): 票 08 首份成品里「从 1,421 亿到 77.6 元/股」这一步全章没有交代 ——
要 ÷18.31 亿股, 而股本数字一次都没出现。三轮双 reviewer 没抓到, 是真人读者读出来的。
机器抓不到的原因很单纯: **这些数字只以散文形式存在, 没有可校验的结构**。

所以推导从「散文里的数字」升级成「契约里的数据」(`node-odds.schema.json#/properties/derivation`),
本模块是它的两个消费者:
  · `check()`      —— 十条算术闭合(lint_v8 R12 调用), 抓「每股换算整个丢失」与「合计加错」;
  · `expand_tables()` —— 把正文里的 `{{sotp}}` / `{{discount_rate}}` / `{{dcf}}` 占位
                        换成机器渲染的 markdown 表(写手只填数据, 不手搓表格)。

★ **容差按「写出来的精度」算, 不用相对百分比**。写手落盘的是四舍五入后的展示值
(20.9 亿 × 30x 写成 626 亿而不是 627 亿), 所以两边都只精确到各自最低位。
半 ulp 逐项累加得到的容差既容得下这种四舍五入, 又能抓住真错 ——
东山实测: 分部合计差 0.5(容差 2.55 → 过), 而漏掉一个 11 亿的分部差 11.5 → 判 fail。
一刀切的「1% 相对容差」两头都不对: 对分部合计太松(漏 11/1489 = 0.74% 会溜过去),
对每股换算又没有意义(丢失换算是 18 倍的差, 什么容差都能抓)。

★ **概率是声明值, 不是测量值**: `p: 0.3` 就是 30%, 不是 0.3±0.05。所以概率的 ulp 记 0,
否则 `Σ(p×pv)` 的容差会被 pv×0.05 撑到 247 亿, 等于没查。
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

# 概率和的容差: 半个百分点。用 ulp 会给出 ±0.15(0.3+0.5+0.3=1.1 也能过), 太松。
PROB_SUM_TOL = 0.005

# 正文里的表格占位 → 渲染函数名。写手在该出表的位置写占位, 装配替换。
TABLE_SLOTS = ("sotp", "discount_rate", "dcf")
_SLOT_RE = re.compile(r"\{\{\s*(" + "|".join(TABLE_SLOTS) + r")\s*\}\}")


class DerivationError(ValueError):
    """推导块结构不完整——schema 已经拦过一层, 走到这里说明是调用方给错了数据。"""


# ---------------------------------------------------------------- 数值与容差

def _half_ulp(value) -> float:
    """一个「写出来的数」的半个最低位。626 → 0.5 · 20.9 → 0.05 · 18.3161 → 0.00005。"""
    try:
        exp = Decimal(str(value)).as_tuple().exponent
    except (InvalidOperation, TypeError):
        return 0.0
    if not isinstance(exp, int):        # NaN / Infinity
        return 0.0
    return 0.5 * (10.0 ** exp)


def _fmt(value, unit: str = "") -> str:
    """按写出来的精度回显, 四位以上加千分位。1335 → 「1,335 亿」· 153.5 → 「153.5 亿」。"""
    if value is None:
        return "—"
    exp = Decimal(str(value)).as_tuple().exponent
    digits = max(-exp, 0) if isinstance(exp, int) else 0
    text = f"{float(value):,.{digits}f}"
    return f"{text} {unit}".strip() if unit else text


def _pct(value) -> str:
    """0.3 → 「30%」(概率)。走 Decimal 是为了不让 0.3×100 的浮点尾巴印成「30.0%」。"""
    if value is None:
        return "—"
    scaled = (Decimal(str(value)) * 100).normalize()
    if scaled == scaled.to_integral_value():
        scaled = scaled.quantize(Decimal(1))
    return f"{scaled:,f}%"


def _num_pct(value) -> str:
    """25 → 「25%」(已经是百分数的字段: CAGR / 利润率 / 折现率分项)。"""
    return "—" if value is None else _fmt(value) + "%"


def _mult(value) -> str:
    return "—" if value is None else _fmt(value) + "x"


def _close(lhs: float, rhs: float, tol: float) -> bool:
    return abs(lhs - rhs) <= tol + 1e-9


# ---------------------------------------------------------------- 闭合校验

def _seg_values(sotp: dict) -> list:
    """分部估值的**原值**, 不转 float —— `float(626)` 会变成 `626.0`, 半 ulp 从 0.5 掉到 0.05,
    容差凭空收紧 5 倍, 东山那张真表(分部逐个进位后合计再进一次)第一行就会被误判。"""
    return [s["value"] for s in sotp.get("segments") or [] if isinstance(s.get("value"), (int, float))]


def check(derivation: dict, current_price: dict | None = None,
          anchor_range: dict | None = None) -> list[str]:
    """十条算术闭合。返回违规说明(空 = 全闭合)。字段缺失交给 schema, 这里只算数。"""
    if not isinstance(derivation, dict):
        return ["derivation 不是映射(schema 应已拦下)"]

    out: list[str] = []
    unit = derivation.get("unit") or ""
    ps_unit = derivation.get("per_share_unit") or ""
    share = derivation.get("share_count") or {}
    shares = share.get("value")
    sotp = derivation.get("sotp") or {}
    dcf = derivation.get("dcf") or {}
    pfn = derivation.get("p_f_n") or {}

    # ① 分部乘法: 年化利润 × 倍数 = 分部估值
    for i, seg in enumerate(sotp.get("segments") or []):
        profit, mult, value = seg.get("profit"), seg.get("multiple"), seg.get("value")
        if not all(isinstance(v, (int, float)) for v in (profit, mult, value)):
            continue
        tol = (_half_ulp(value) + abs(mult) * _half_ulp(profit)
               + abs(profit) * _half_ulp(mult))
        if not _close(profit * mult, value, tol):
            out.append(
                f"sotp.segments[{i}]「{seg.get('name', '?')}」: "
                f"{_fmt(profit)} × {_mult(mult)} = {_fmt(profit * mult)} ≠ 落盘 {_fmt(value, unit)}"
                f"(容差 {tol:.3g})"
            )

    # ② 分部加总 = 企业价值(写手可显式落 enterprise_value, 缺省即分部和)
    seg_vals = _seg_values(sotp)
    ev_stated = sotp.get("enterprise_value")
    if seg_vals and isinstance(ev_stated, (int, float)):
        tol = sum(_half_ulp(v) for v in seg_vals) + _half_ulp(ev_stated)
        if not _close(sum(seg_vals), ev_stated, tol):
            out.append(
                f"sotp: 分部加总 {_fmt(sum(seg_vals), unit)} ≠ enterprise_value "
                f"{_fmt(ev_stated, unit)}(容差 {tol:.3g})"
            )
    ev = ev_stated if isinstance(ev_stated, (int, float)) else (sum(seg_vals) if seg_vals else None)

    # ③ ★ Σsegments − net_debt = equity_value
    net_debt, sotp_eq = sotp.get("net_debt"), sotp.get("equity_value")
    if all(isinstance(v, (int, float)) for v in (ev, net_debt, sotp_eq)):
        tol = (sum(_half_ulp(v) for v in seg_vals) + _half_ulp(ev_stated)
               + _half_ulp(net_debt) + _half_ulp(sotp_eq))
        if not _close(ev - net_debt, sotp_eq, tol):
            out.append(
                f"sotp: EV {_fmt(ev, unit)} − 净负债 {_fmt(net_debt, unit)} = "
                f"{_fmt(ev - net_debt, unit)} ≠ equity_value {_fmt(sotp_eq, unit)}"
                f"(容差 {tol:.3g})"
            )

    # ④ Σ概率 = 1
    scenarios = dcf.get("scenarios") or []
    probs = [s.get("p") for s in scenarios if isinstance(s.get("p"), (int, float))]
    if probs:
        if not _close(sum(probs), 1.0, PROB_SUM_TOL):
            out.append(
                f"dcf: 情景概率合计 {_pct(sum(probs))} ≠ 100%"
                f"({' + '.join(_pct(p) for p in probs)})"
            )

    # ⑤ ★ Σ(p × pv) = equity_value
    dcf_eq = dcf.get("equity_value")
    pairs = [(s.get("p"), s.get("pv")) for s in scenarios]
    pairs = [(p, v) for p, v in pairs if isinstance(p, (int, float)) and isinstance(v, (int, float))]
    if pairs and isinstance(dcf_eq, (int, float)):
        weighted = sum(p * v for p, v in pairs)
        tol = _half_ulp(dcf_eq) + sum(p * _half_ulp(v) for p, v in pairs)   # 概率 ulp = 0
        if not _close(weighted, dcf_eq, tol):
            out.append(
                f"dcf: 概率加权 {' + '.join(f'{_pct(p)}×{_fmt(v)}' for p, v in pairs)} = "
                f"{_fmt(weighted, unit)} ≠ equity_value {_fmt(dcf_eq, unit)}(容差 {tol:.3g})"
            )

    # ⑥ ★ Σ折现率分项 = 折现率
    rate = dcf.get("discount_rate") or {}
    comps = [c.get("value") for c in rate.get("components") or []
             if isinstance(c.get("value"), (int, float))]
    total = rate.get("total")
    if comps and isinstance(total, (int, float)):
        tol = sum(_half_ulp(v) for v in comps) + _half_ulp(total)
        if not _close(sum(comps), total, tol):
            out.append(
                f"dcf.discount_rate: 分项 {' + '.join(_num_pct(v) for v in comps)} = "
                f"{_num_pct(round(sum(comps), 9))} ≠ total {_num_pct(total)}(容差 {tol:.3g})"
            )

    # ⑦ ★ equity_value ÷ share_count = per_share —— 票 08 那个真人才读出来的缺口
    if isinstance(shares, (int, float)) and shares > 0:
        for name, block in (("sotp", sotp), ("dcf", dcf)):
            eq, per = block.get("equity_value"), block.get("per_share")
            if not all(isinstance(v, (int, float)) for v in (eq, per)):
                continue
            tol = _half_ulp(eq) + shares * _half_ulp(per) + abs(per) * _half_ulp(shares)
            if not _close(per * shares, eq, tol):
                out.append(
                    f"{name}: 每股 {_fmt(per, ps_unit)} × 股本 {_fmt(shares, share.get('unit'))} = "
                    f"{_fmt(per * shares, unit)} ≠ equity_value {_fmt(eq, unit)}(容差 {tol:.3g})"
                    " —— 每股换算对不上, 或者根本没换算"
                )

    # ⑧ 锚区间两端 = 两法各自的每股价 —— 锚不能是第三个数字
    if anchor_range:
        for end, block, label in (("low", sotp, "SOTP"), ("high", dcf, "DCF")):
            anchored = (anchor_range.get(end) or {}).get("value")
            per = block.get("per_share")
            if not all(isinstance(v, (int, float)) for v in (anchored, per)):
                continue
            tol = _half_ulp(anchored) + _half_ulp(per)
            if not _close(anchored, per, tol):
                out.append(
                    f"anchor_range.{end} {_fmt(anchored, ps_unit)} ≠ {label} 推导的每股 "
                    f"{_fmt(per, ps_unit)}(锚必须是推导出来的那个数, 不是另写一个)"
                )

    # ⑨ P = F + N, 且 N 占比与金额自洽
    cap, fact, narr = pfn.get("market_cap"), pfn.get("fact"), pfn.get("narrative")
    if all(isinstance(v, (int, float)) for v in (cap, fact, narr)):
        tol = _half_ulp(cap) + _half_ulp(fact) + _half_ulp(narr)
        if not _close(fact + narr, cap, tol):
            out.append(
                f"p_f_n: F {_fmt(fact, unit)} + N {_fmt(narr, unit)} = {_fmt(fact + narr, unit)} "
                f"≠ 市值 {_fmt(cap, unit)}(容差 {tol:.3g})"
            )
        n_share = pfn.get("narrative_share")
        if isinstance(n_share, (int, float)) and cap:
            tol = _half_ulp(narr) + abs(cap) * _half_ulp(n_share) + abs(n_share) * _half_ulp(cap)
            if not _close(n_share * cap, narr, tol):
                out.append(
                    f"p_f_n: 叙事占比 {_pct(n_share)} × 市值 {_fmt(cap, unit)} = "
                    f"{_fmt(n_share * cap, unit)} ≠ N {_fmt(narr, unit)}(容差 {tol:.3g})"
                )

    # ⑩ 市值 = 现价 × 股本 —— 把股本、现价、市值三个数字锁成一个三角
    price = (current_price or {}).get("value")
    if all(isinstance(v, (int, float)) for v in (price, shares, cap)):
        tol = _half_ulp(cap) + shares * _half_ulp(price) + abs(price) * _half_ulp(shares)
        if not _close(price * shares, cap, tol):
            out.append(
                f"p_f_n: 现价 {_fmt(price, ps_unit)} × 股本 {_fmt(shares, share.get('unit'))} = "
                f"{_fmt(price * shares, unit)} ≠ market_cap {_fmt(cap, unit)}(容差 {tol:.3g})"
            )
    return out


# ---------------------------------------------------------------- 表格渲染

def _total_row(cells: int, head: str, tail: str, note: str = "") -> str:
    """合计行: 首格粗体算式, 末格粗体结果, 中间留空(表宽由表头决定)。

    `note` 只在末列是文字列(SOTP 的「倍数理由」)时才单独占一格; 末列是数值列(DCF 的
    「折现值」)时它会把结果挤出末列, 所以并进首格的括注 —— 表的形状由表头定, 不由注定。
    """
    if note:
        middle = [""] * max(cells - 3, 0)
        return "| " + " | ".join([f"**{head}**", *middle, f"**{tail}**", note]) + " |"
    middle = [""] * max(cells - 2, 0)
    return "| " + " | ".join([f"**{head}**", *middle, f"**{tail}**"]) + " |"


def render_sotp(derivation: dict) -> str:
    """叙事分部 SOTP 表: 一行一分部, 合计行走完 EV → 净负债 → 股权 → ÷股本 → 每股。"""
    sotp = derivation.get("sotp") or {}
    unit, ps_unit = derivation.get("unit") or "", derivation.get("per_share_unit") or ""
    share = derivation.get("share_count") or {}
    segments = sotp.get("segments") or []
    if not segments:
        raise DerivationError("sotp.segments 为空, 渲染不出分部表")

    lines = [
        f"| 分部 | {sotp.get('profit_label') or '年化利润'} | 倍数 | 估值 | 倍数理由与证伪指标 |",
        "|---|---:|:---:|---:|---|",
    ]
    for seg in segments:
        basis = (seg.get("basis") or "").strip()
        falsify = (seg.get("falsify") or "").strip()
        note = f"{basis};证伪——{falsify}" if basis and falsify else (basis or (f"证伪——{falsify}" if falsify else ""))
        lines.append(
            f"| {seg.get('name', '')} | {_fmt(seg.get('profit'), unit)} | "
            f"{_mult(seg.get('multiple'))} | {_fmt(seg.get('value'), unit)} | {note} |"
        )

    seg_vals = _seg_values(sotp)
    ev = sotp.get("enterprise_value")
    ev = ev if isinstance(ev, (int, float)) else sum(seg_vals)
    head = (
        f"EV {_fmt(ev, unit)} − 净负债 {_fmt(sotp.get('net_debt'), unit)} = "
        f"股权 {_fmt(sotp.get('equity_value'), unit)} ÷ {_fmt(share.get('value'), share.get('unit'))}"
    )
    lines.append(_total_row(5, head, f"= {_fmt(sotp.get('per_share'), ps_unit)}/股", sotp.get("note") or ""))
    return "\n".join(lines)


def render_discount_rate(derivation: dict) -> str:
    """折现率加法栈: 一行一分项 + 合计行。散文里的括号串是 R11 眼里的「焊成段落的表」。"""
    rate = (derivation.get("dcf") or {}).get("discount_rate") or {}
    comps = rate.get("components") or []
    if not comps:
        raise DerivationError("dcf.discount_rate.components 为空, 渲染不出折现率栈")
    lines = ["| 折现率分项 | 值 | 依据 |", "|---|---:|---|"]
    for c in comps:
        lines.append(f"| {c.get('name', '')} | {_num_pct(c.get('value'))} | {c.get('basis') or ''} |")
    lines.append(
        f"| **合计折现率** | **{_num_pct(rate.get('total'))}** | {rate.get('note') or ''} |"
    )
    return "\n".join(lines)


def render_dcf(derivation: dict) -> str:
    """三情景概率加权表: 一行一情景 + 合计行(加权股权 ÷ 股本 = 每股)。"""
    dcf = derivation.get("dcf") or {}
    unit, ps_unit = derivation.get("unit") or "", derivation.get("per_share_unit") or ""
    share = derivation.get("share_count") or {}
    scenarios = dcf.get("scenarios") or []
    if not scenarios:
        raise DerivationError("dcf.scenarios 为空, 渲染不出情景表")

    lines = [
        "| 情景 | 概率 | 收入 5 年 CAGR | 成熟净利率 | 退出 PE | 折现值 |",
        "|---|:---:|:---:|:---:|:---:|---:|",
    ]
    for s in scenarios:
        lines.append(
            f"| {s.get('name', '')} | {_pct(s.get('p'))} | {_num_pct(s.get('cagr'))} | "
            f"{_num_pct(s.get('margin'))} | {_mult(s.get('exit_multiple'))} | {_fmt(s.get('pv'), unit)} |"
        )
    head = (
        f"概率加权 {_fmt(dcf.get('equity_value'), unit)} ÷ "
        f"{_fmt(share.get('value'), share.get('unit'))}"
    )
    if dcf.get("note"):                       # 末列是数值列, 注并进首格(见 _total_row)
        head += f"({dcf['note']})"
    lines.append(_total_row(6, head, f"= {_fmt(dcf.get('per_share'), ps_unit)}/股"))
    return "\n".join(lines)


RENDERERS = {"sotp": render_sotp, "discount_rate": render_discount_rate, "dcf": render_dcf}


def slots_in(body: str) -> set[str]:
    """正文里用到的占位名。"""
    return {m.group(1) for m in _SLOT_RE.finditer(body or "")}


def missing_slots(body: str) -> list[str]:
    """三张表里没被正文引用的那些——数据填了却没人渲染, 读者一格也看不到。"""
    return [s for s in TABLE_SLOTS if s not in slots_in(body)]


def expand_tables(body: str, odds_block: dict) -> str:
    """把 `{{sotp}}` / `{{discount_rate}}` / `{{dcf}}` 换成机器渲染的表。

    没有 derivation(旧 run / 半成品)就原样返回 —— 装配不因为缺推导块而炸,
    该报的是 lint R1(schema)与 R12(闭合), 不是这里。
    """
    derivation = (odds_block or {}).get("derivation")
    if not derivation or not _SLOT_RE.search(body or ""):
        return body
    return _SLOT_RE.sub(lambda m: RENDERERS[m.group(1)](derivation), body)
