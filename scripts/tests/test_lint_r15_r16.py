"""单元测试: lint_v8 R15 三元组同源 / R16 ③锚引用过期(v8.5 华特实战)。

两条都是「跨节点抄本过期」:上游节点在修正循环里改了, 下游抄本没跟上, 而 R1-R14 全绿。
华特 R1:④改了判定句, ⑤ triad 仍是旧句;③锚低端 42.2→35.3 后, ⑤ 正文与 YAML 里
仍有 8 处「42.2~49.6 元」—— 装配 + lint 一次过, 靠人工 grep 才发现。

运行:
    python -m unittest scripts.tests.test_lint_r15_r16
"""
from __future__ import annotations

import unittest

from scripts import lint_v8

ODDS = {
    "node": "odds",
    "verdict": "买完完美未来——现价是高端 49.6 元的 2.61 倍、低端 35.3 元的 3.66 倍",
    "anchor_range": {
        "low": {"method": "只认已兑现利润的两段加总", "value": 35.3, "unit": "元"},
        "high": {"method": "三情景概率加权折现", "value": 49.6, "unit": "元"},
        "same_direction": True,
    },
}
STATE = {"node": "state", "verdict": "↑未确认——一半增长来自氦气涨价,另一半是走量换价"}
PATH = {"node": "path", "verdict": "高尾险·不可承受——七项炒作拥挤特征中了六项(高信仰体检)"}


def decision(triad: dict | None = None, **extra) -> dict:
    d = {
        "node": "decision",
        "verdict": "回避",
        "triad": triad if triad is not None else {
            "state": STATE["verdict"], "odds": ODDS["verdict"], "path": PATH["verdict"],
        },
    }
    d.update(extra)
    return d


def nodes(dec: dict | None = None) -> dict:
    return {"state": STATE, "odds": ODDS, "path": PATH, "decision": dec if dec is not None else decision()}


class TestR15TriadSource(unittest.TestCase):

    def test_verbatim_triad_passes(self):
        r = lint_v8.rule_triad_source(nodes())
        self.assertTrue(r.passed, r.findings)

    def test_stale_sentence_is_caught_even_when_tier_matches(self):
        """判定档没变、只改了破折号后半句 —— 华特 R1 的实际形态, 首页卡片取的正是这半句。"""
        stale = {
            "state": STATE["verdict"], "odds": ODDS["verdict"],
            "path": "高尾险·不可承受——③三情景无一高于现价,高信仰体检 6/7",
        }
        r = lint_v8.rule_triad_source(nodes(decision(stale)))
        self.assertFalse(r.passed)
        self.assertEqual(len(r.findings), 1)
        self.assertIn("triad.path", r.findings[0])

    def test_missing_triad_is_skipped_not_failed(self):
        d = decision()
        del d["triad"]
        self.assertTrue(lint_v8.rule_triad_source(nodes(d)).skipped)


class TestR16AnchorCitation(unittest.TestCase):

    def rule(self, decision_body: str = "", **dec_extra):
        bodies = {
            "quality": "", "state": "合理价区间 35.3~49.6 元对现价 129.30 元(③赔率)",
            "odds": "", "path": "", "decision": decision_body,
        }
        return lint_v8.rule_anchor_citation(nodes(decision(**dec_extra)), bodies)

    def test_current_anchor_passes(self):
        r = self.rule("回落进 35.3~49.6 元才有安全垫(③)")
        self.assertTrue(r.passed, r.findings)

    def test_range_with_one_stale_end_is_caught(self):
        r = self.rule("回落进 42.2~49.6 元才有安全垫(③)")
        self.assertFalse(r.passed)
        self.assertIn("42.2", r.findings[0])

    def test_stale_copy_inside_yaml_is_caught(self):
        r = self.rule(position="三季报过线且价格回落进 42.2~49.6 元合理价区间再重估")
        self.assertFalse(r.passed)
        self.assertIn("YAML position", r.findings[0])

    def test_unrelated_ranges_are_left_alone(self):
        """两端都不是锚 = 别的区间(历史价、情景价), 不归这条管。"""
        r = self.rule("盘中区间 90.86~290.0 元;乐观情景每股 107.8 元")
        self.assertTrue(r.passed, r.findings)

    def test_named_anchor_end_must_match(self):
        self.assertFalse(self.rule("③锚低端 SOTP 42.2 元只认已兑现").passed)
        self.assertTrue(self.rule("③锚低端 SOTP 35.3 元只认已兑现").passed)

    def test_hyphen_range_counts_but_dates_do_not(self):
        self.assertFalse(self.rule("合理价区间 42.2-49.6 元").passed)
        self.assertTrue(self.rule("2026-04-17 收盘价 90.86 元").passed)

    def test_odds_own_text_is_not_judged_here(self):
        """③自己的锚归 R5 管;这条只查别的节点抄得对不对。"""
        n = nodes()
        bodies = {"quality": "", "state": "", "odds": "旧锚 42.2~49.6 元", "path": "", "decision": ""}
        self.assertTrue(lint_v8.rule_anchor_citation(n, bodies).passed)



# ---------------------------------------------------------------- R17 已兑现倍数(v8.9)

def _odds_with(segments: list[dict], scenarios: list[dict]) -> dict:
    return {"odds": {"node": "odds", "derivation": {"sotp": {"segments": segments},
                                                    "dcf": {"scenarios": scenarios}}}}


HUATE_SCENARIOS = [
    {"name": "乐观前景(高端放量 + 氦价高位)", "p": 0.2, "exit_multiple": 45},
    {"name": "基准前景(行业增速 + 氦价回落)", "p": 0.5, "exit_multiple": 35},
    {"name": "最差那条前景(价格内卷延续)", "p": 0.3, "exit_multiple": 25},
]


class TestR17RealizedMultiple(unittest.TestCase):
    """按**自身历史倍数**给已兑现利润定价时, 不得高于基准情景的退出倍数。

    华特 R1 实测:低端「只认已兑现」给 40x, 而基准情景五年增长之后才给 35x ——
    等于给不增长的利润付了比增长还贵的价, F 里含了增长、N 被低估(改 32.8x 后低端 42.2 → 35.3 元)。
    R5 只查两端不倒置, 这种「同向但内部不自洽」它看不见。
    """

    def test_self_history_multiple_above_base_exit_fails(self):
        r = lint_v8.rule_realized_multiple(_odds_with(
            [{"name": "基本盘(2025 全年扣非)", "multiple": 40,
              "basis": "行情前滚动市盈率 25 分位"}], HUATE_SCENARIOS))
        self.assertFalse(r.passed)
        self.assertIn("40x", r.findings[0])
        self.assertIn("35x", r.findings[0])

    def test_lowered_multiple_passes(self):
        """华特修完之后的形态(32.8x < 35x)不该再报。"""
        r = lint_v8.rule_realized_multiple(_odds_with(
            [{"name": "基本盘(2025 全年扣非)", "multiple": 32.8,
              "basis": "行情前滚动市盈率 25 分位, 低于基准前景退出 35x"}], HUATE_SCENARIOS))
        self.assertTrue(r.passed, r.findings)

    def test_peer_priced_segment_is_not_judged(self):
        """按**同业倍数**给分部定价是另一回事, 不能拿去和终值倍数比大小。

        东山实测:电子电路 30x、光模块 40x 都高于基准情景退出 20x —— 那是「当期同业倍数」
        对「五年后的终值倍数」, 两者本就不可比。误判它会把两份已发布的报告判红。
        """
        r = lint_v8.rule_realized_multiple(_odds_with(
            [{"name": "电子电路", "multiple": 30, "basis": "给 5 家 peer 中位"},
             {"name": "光模块(索尔思)", "multiple": 40, "basis": "H1 收入为 2025 全年的 3.7 倍, 40x 已含 AI 溢价"}],
            [{"name": "基准(光模块降速)", "p": 0.5, "exit_multiple": 20}]))
        self.assertTrue(r.passed, r.findings)

    def test_base_scenario_falls_back_to_highest_probability(self):
        """情景没叫「基准」时取概率最大的那条。"""
        r = lint_v8.rule_realized_multiple(_odds_with(
            [{"name": "已兑现", "multiple": 30, "basis": "自身历史倍数中位"}],
            [{"name": "乐观", "p": 0.2, "exit_multiple": 40},
             {"name": "中性", "p": 0.5, "exit_multiple": 25},
             {"name": "悲观", "p": 0.3, "exit_multiple": 15}]))
        self.assertFalse(r.passed)
        self.assertIn("中性", r.findings[0])

    def test_missing_scenarios_is_skipped_not_failed(self):
        r = lint_v8.rule_realized_multiple(_odds_with(
            [{"name": "已兑现", "multiple": 30, "basis": "自身历史分位"}], []))
        self.assertTrue(r.skipped)


if __name__ == "__main__":
    unittest.main()
