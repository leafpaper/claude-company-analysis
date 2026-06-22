"""单元测试: anti_lazy_lint v7.0 新增 Rule 6 (§七决策内核) + Rule 7 (无记忆性反例)。

运行:
    python3 -m scripts.tests.test_anti_lazy_lint_v7
"""
from __future__ import annotations

import sys
import unittest

from scripts import anti_lazy_lint as L


def _wrap_sec7(body: str) -> str:
    return f"## §一 执行摘要\n占位\n\n## §七 投资决策内核\n{body}\n"


class TestRule6DecisionCore(unittest.TestCase):
    def test_full_decision_core_passes(self):
        md = _wrap_sec7("决策三元组 [↑|price-in|高尾险]\n行动档位: 不追高（贵但优质）\n证伪: 中报分部不及预期")
        self.assertTrue(L.rule_6_decision_core(md).passed)

    def test_missing_action_tier_keyword_fails(self):
        md = _wrap_sec7("决策三元组 [↑|price-in|高尾险]\n行动方向: 观察\n证伪: 中报")
        self.assertFalse(L.rule_6_decision_core(md).passed)

    def test_missing_falsification_fails(self):
        md = _wrap_sec7("决策三元组 [↑|price-in|高尾险]\n行动档位: 回避")
        self.assertFalse(L.rule_6_decision_core(md).passed)

    def test_no_action_tier_value_fails(self):
        # 含"行动档位"字样但没给出六档之一
        md = _wrap_sec7("决策三元组 [↑|price-in|高尾险]\n行动档位: 待定\n证伪: 中报")
        self.assertFalse(L.rule_6_decision_core(md).passed)

    def test_missing_section7_fails(self):
        md = "## §一 执行摘要\n占位\n"
        self.assertFalse(L.rule_6_decision_core(md).passed)


class TestRule7Memorylessness(unittest.TestCase):
    def test_clean_text_passes(self):
        md = "## §四 评分\nλ 上升且证据斜率变正，买入逻辑成立。"
        self.assertTrue(L.rule_7_memorylessness(md).passed)

    def test_memoryless_assertion_fails(self):
        md = "## §四 评分\n本标的已经跌久了该涨，是入场良机。"
        self.assertFalse(L.rule_7_memorylessness(md).passed)

    def test_valuation_compressed_assertion_fails(self):
        md = "## §七 投资决策内核\n估值压久了该修复，给核心仓。"
        self.assertFalse(L.rule_7_memorylessness(md).passed)

    def test_exempt_context_passes(self):
        # 报告解释"禁用这些幻觉"——豁免语境，不应误判
        md = "## §四 评分\n禁止把'跌久了该涨/估值压久了该修复'当买入理由，须 λ↑。"
        self.assertTrue(L.rule_7_memorylessness(md).passed)


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (TestRule6DecisionCore, TestRule7Memorylessness):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
