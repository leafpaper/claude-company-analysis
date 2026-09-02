"""单元测试: v8 估值推导结构化 — 算术闭合(lint_v8 R12)+ 三张表的机器渲染。

实现票 11(.scratch/v8-implementation/issues/11-valuation-derivation-schema.md)。

票 11 的起因是票 08 首份成品的一处真缺陷:「从 1,421 亿到 77.6 元/股」这一步全章没有交代
——要 ÷18.31 亿股, 而股本数字一次都没出现, 三轮双 reviewer 全没抓到, 是真人读者读出来的。
所以本模块的两个头等用例就是那两类错:

    TestPerShareConversion  —— 每股换算整个丢失(把股权总额当成每股价)
    TestSumErrors           —— 合计加错(漏一个分部 / 情景概率不足 / 折现率分项对不上)

★ 容差是「写出来的精度」逐项半 ulp 累加, 不是相对百分比 —— 见 derivation 模块头注。
  下面每个负例都同时断言「真错被抓住」与「四舍五入不被误伤」, 两头都要成立才算这条规则可用。

运行:
    python -m unittest scripts.tests.test_derivation_v8
"""
from __future__ import annotations

import copy
import unittest

from scripts import derivation as d
from scripts.tests import dongshan_fixture as fx


def golden() -> dict:
    return copy.deepcopy(fx.odds_block())


def check(block: dict) -> list[str]:
    return d.check(block["derivation"], block.get("current_price"), block.get("anchor_range"))


class TestGoldenCloses(unittest.TestCase):
    def test_dongshan_golden_is_fully_closed(self):
        """golden 推导十条闭合全过 —— 基线不闭合的话下面所有负例都没意义。"""
        self.assertEqual(check(golden()), [])

    def test_rounding_is_not_a_violation(self):
        """写手落的是四舍五入后的展示值: 20.9 × 30 = 627 写成 626, 不该判错。

        这条是容差设计的正面证明 —— 真实东山 SOTP 就长这样(分部乘积逐个进位、
        合计再进一次), 容差如果按「两边必须完全相等」算, golden 第一行就红。
        """
        b = golden()
        segs = b["derivation"]["sotp"]["segments"]
        segs[0].update({"profit": 20.9, "multiple": 30, "value": 626})   # 实际 627
        segs[1].update({"profit": 18.6, "multiple": 40, "value": 746})   # 实际 744
        segs[2].update({"profit": 7.1, "multiple": 15, "value": 106})    # 实际 106.5
        segs[3].update({"profit": 1.4, "multiple": 8, "value": 11})      # 实际 11.2
        b["derivation"]["sotp"].update(
            {"enterprise_value": 1488, "net_debt": 153.5, "equity_value": 1335, "per_share": 73}
        )
        b["derivation"]["share_count"]["value"] = 18.3161
        b["anchor_range"]["low"]["value"] = 73
        self.assertEqual(
            [f for f in check(b) if "sotp" in f or "anchor_range.low" in f], []
        )


class TestPerShareConversion(unittest.TestCase):
    """★ 票 11 的头号用例: 每股换算整个丢失。"""

    def test_missing_conversion_is_caught(self):
        """把股权总额直接当每股价写(1,050 亿 → 「1050 元/股」)—— 必须抓住。"""
        b = golden()
        b["derivation"]["sotp"]["per_share"] = 1050
        b["anchor_range"]["low"]["value"] = 1050
        findings = check(b)
        self.assertTrue(any("每股换算对不上" in f for f in findings), findings)

    def test_wrong_share_count_is_caught(self):
        """股本写错一个量级(18.3161 → 1.83161 亿股): 每股与市值两条同时红。"""
        b = golden()
        b["derivation"]["share_count"]["value"] = 1.83161
        findings = check(b)
        self.assertTrue(any("每股换算对不上" in f for f in findings), findings)
        self.assertTrue(any("market_cap" in f for f in findings), findings)

    def test_anchor_must_equal_the_derived_per_share(self):
        """锚不能是第三个数字 —— 推导出 57, 锚却写 60。"""
        b = golden()
        b["anchor_range"]["low"]["value"] = 60
        findings = check(b)
        self.assertTrue(any("anchor_range.low" in f for f in findings), findings)

    def test_both_ends_are_checked(self):
        b = golden()
        b["anchor_range"]["high"]["value"] = 95
        findings = check(b)
        self.assertTrue(any("anchor_range.high" in f for f in findings), findings)


class TestSumErrors(unittest.TestCase):
    """★ 票 11 的二号用例: 合计加错。"""

    def test_dropped_segment_is_caught(self):
        """漏掉一个 20 亿的分部 —— 占 EV 的 1.7%, 一刀切的 1% 相对容差会放它过去。"""
        b = golden()
        b["derivation"]["sotp"]["segments"].pop()          # 光电显示模组 20 亿
        findings = check(b)
        self.assertTrue(any("分部加总" in f for f in findings), findings)

    def test_segment_product_error_is_caught(self):
        b = golden()
        b["derivation"]["sotp"]["segments"][0]["value"] = 750    # 22 × 25 = 550
        findings = check(b)
        self.assertTrue(any("segments[0]" in f for f in findings), findings)

    def test_net_debt_forgotten_is_caught(self):
        """EV 直接当股权用(忘了减净负债)。"""
        b = golden()
        b["derivation"]["sotp"]["equity_value"] = 1170
        findings = check(b)
        self.assertTrue(any("净负债" in f for f in findings), findings)

    def test_probabilities_must_sum_to_one(self):
        b = golden()
        b["derivation"]["dcf"]["scenarios"][1]["p"] = 0.6        # 0.3 + 0.6 + 0.2
        findings = check(b)
        self.assertTrue(any("情景概率合计" in f for f in findings), findings)

    def test_probability_sum_tolerance_is_tight(self):
        """0.3+0.5+0.3 = 1.1: 按半 ulp 算容差是 ±0.15, 会放它过去 —— 所以概率单独定死 ±0.5pp。"""
        b = golden()
        b["derivation"]["dcf"]["scenarios"][2]["p"] = 0.3
        b["derivation"]["dcf"]["equity_value"] = 1678            # 让加权和自洽, 只留概率这一条错
        findings = check(b)
        self.assertTrue(any("情景概率合计" in f for f in findings), findings)

    def test_weighted_sum_error_is_caught(self):
        b = golden()
        b["derivation"]["dcf"]["scenarios"][0]["pv"] = 4000      # 加权后 1,842 ≠ 1,632
        findings = check(b)
        self.assertTrue(any("概率加权" in f for f in findings), findings)

    def test_discount_rate_stack_must_add_up(self):
        b = golden()
        b["derivation"]["dcf"]["discount_rate"]["components"].pop()   # 少一项 1.6%
        findings = check(b)
        self.assertTrue(any("discount_rate" in f for f in findings), findings)

    def test_p_f_n_must_add_up(self):
        b = golden()
        b["derivation"]["p_f_n"]["narrative"] = 3500              # 1,000 + 3,500 ≠ 5,000
        findings = check(b)
        self.assertTrue(any("p_f_n" in f for f in findings), findings)

    def test_narrative_share_must_match_the_amounts(self):
        """占比和金额讲两个故事 —— 图上画的是占比, 正文引的是金额, 必须一致。"""
        b = golden()
        b["derivation"]["p_f_n"]["narrative_share"] = 0.5
        findings = check(b)
        self.assertTrue(any("叙事占比" in f for f in findings), findings)

    def test_market_cap_locks_price_and_share_count(self):
        """市值 = 现价 × 股本: 把股本、现价、市值三个数字锁成一个三角。"""
        b = golden()
        b["current_price"] = {"value": 150, "unit": "元"}
        findings = check(b)
        self.assertTrue(any("market_cap" in f for f in findings), findings)


class TestTableSlots(unittest.TestCase):
    def test_missing_slots_are_reported(self):
        self.assertEqual(d.missing_slots("正文里一个占位也没有"), list(d.TABLE_SLOTS))

    def test_golden_body_uses_all_three(self):
        self.assertEqual(d.missing_slots(fx.NODE_BODIES["odds"]), [])

    def test_expand_replaces_every_slot(self):
        out = d.expand_tables(fx.NODE_BODIES["odds"], golden())
        self.assertNotIn("{{", out)
        self.assertIn("| 分部 | 年化利润 | 倍数 | 估值 |", out)
        self.assertIn("| 折现率分项 |", out)
        self.assertIn("| 情景 | 概率 |", out)

    def test_expand_is_a_noop_without_derivation(self):
        """旧 run / 半成品没有推导块时装配不炸 —— 该报的是 lint, 不是渲染。"""
        body = "### 低端\n\n{{sotp}}\n"
        self.assertEqual(d.expand_tables(body, {"node": "odds"}), body)


class TestTableRendering(unittest.TestCase):
    def test_sotp_total_row_walks_the_whole_chain(self):
        """合计行必须把 EV → 净负债 → 股权 → ÷股本 → 每股 五步全走完 —— 就是票 08 丢掉的那步。"""
        row = d.render_sotp(golden()["derivation"]).splitlines()[-1]
        for piece in ("EV 1,170 亿", "净负债 120 亿", "股权 1,050 亿", "18.3161 亿股", "57 元/股"):
            self.assertIn(piece, row)

    def test_segment_row_carries_basis_and_falsifier(self):
        table = d.render_sotp(golden()["derivation"])
        self.assertIn("40x 已含 AI 溢价;证伪——毛利率跌破 30%", table)

    def test_probability_renders_without_a_float_tail(self):
        """0.3 × 100 的浮点尾巴不许印成「30.0%」。"""
        self.assertIn("| 30% |", d.render_dcf(golden()["derivation"]))

    def test_thousands_separator_and_written_precision(self):
        self.assertEqual(d._fmt(1335, "亿"), "1,335 亿")
        self.assertEqual(d._fmt(153.5, "亿"), "153.5 亿")
        self.assertEqual(d._fmt(18.3161, "亿股"), "18.3161 亿股")

    def test_dcf_note_goes_into_the_head_cell(self):
        """末列是数值列, 注只能并进首格 —— 否则会把每股结果挤出末列。"""
        row = d.render_dcf(golden()["derivation"]).splitlines()[-1]
        self.assertTrue(row.rstrip().endswith("**= 89 元/股** |"), row)
        self.assertIn("终值用退出倍数法", row)

    def test_empty_segments_refuses_to_render(self):
        b = golden()
        b["derivation"]["sotp"]["segments"] = []
        with self.assertRaises(d.DerivationError):
            d.render_sotp(b["derivation"])


if __name__ == "__main__":
    unittest.main()
