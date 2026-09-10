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
    "verdict": "买完完美未来(无 slack)——现价是高端 49.6 元的 2.61 倍、低端 35.3 元的 3.66 倍",
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
            "quality": "", "state": "区间锚 35.3~49.6 元对现价 129.30 元(③赔率)",
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
        r = self.rule(position="三季报过线且价格回落进 42.2~49.6 元锚区间再重估")
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
        self.assertFalse(self.rule("锚区间 42.2-49.6 元").passed)
        self.assertTrue(self.rule("2026-04-17 收盘价 90.86 元").passed)

    def test_odds_own_text_is_not_judged_here(self):
        """③自己的锚归 R5 管;这条只查别的节点抄得对不对。"""
        n = nodes()
        bodies = {"quality": "", "state": "", "odds": "旧锚 42.2~49.6 元", "path": "", "decision": ""}
        self.assertTrue(lint_v8.rule_anchor_citation(n, bodies).passed)


if __name__ == "__main__":
    unittest.main()
