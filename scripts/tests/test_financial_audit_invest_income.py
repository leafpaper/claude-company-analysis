"""financial_audit: 投资收益撑起来的利润要报红旗。

金山办公 688111 2026H1 实测:投资收益 19.14 亿 / 营业利润 27.45 亿 = 70%(上年同期 17%),
净利润同比 +237%。脚本一条红旗都没报 —— 因为原有的「非经常性损益占比过高」是拿
`利润总额 − 营业利润` 估的, 只抓得到**营业外**收支(金山这项只有 0.21 亿),
而投资收益与公允价值变动**计在营业利润里面**, 整块从缝里漏过去。
后果:ROE、净利率、同行分位全被一次性收益顶高, 判质地的人看不到这层。

运行:
    python -m unittest scripts.tests.test_financial_audit_invest_income
"""
from __future__ import annotations

import unittest

import pandas as pd

from scripts import financial_audit as fa


def _income(rows: list[dict]) -> dict:
    return {"income": pd.DataFrame(rows)}


YI = 1e8


def _row(end_date: str, op: float, invest: float, fv: float = 0.0, non_oper: float = 0.0) -> dict:
    """单位:亿元。`total_profit` 按营业利润 + 营业外收支 给, 好验证老规则抓不到。"""
    return {
        "end_date": end_date,
        "operate_profit": op * YI,
        "invest_income": invest * YI,
        "fv_value_chg_gain": fv * YI,
        "total_profit": (op + non_oper) * YI,
    }


class InvestIncomeShareTest(unittest.TestCase):

    def _flags(self, rows: list[dict]):
        return fa._invest_income_in_operating_profit(_income(rows))

    def test_kingsoft_h1_is_flagged(self):
        flags = self._flags([
            _row("20250630", op=7.76, invest=1.33, non_oper=0.04),
            _row("20260630", op=27.45, invest=19.14, non_oper=0.20),
        ])
        self.assertEqual(len(flags), 1)
        f = flags[0]
        self.assertEqual(f.signal, "投资收益占营业利润过高")
        self.assertAlmostEqual(f.value, 0.697, places=2)
        self.assertIn("高", f.severity)                 # 70% > 50% → 🟠 高
        self.assertIn("19.14亿", f.evidence)
        self.assertIn("上年同期 17%", f.evidence)       # 「今年突然」和「一直这样」要分得开

    def test_old_non_operating_rule_misses_it(self):
        """同一份数据走老规则(营业外口径)一声不吭 —— 这条测试守住「为什么要新加一条」。"""
        rows = [_row("20260630", op=27.45, invest=19.14, non_oper=0.20)]
        y = pd.DataFrame(rows).iloc[-1]
        non_op_ratio = abs(y["total_profit"] - y["operate_profit"]) / abs(y["total_profit"])
        self.assertLess(non_op_ratio, 0.30)

    def test_fair_value_change_counts_too(self):
        """公允价值变动和投资收益一起算 —— 拆成两栏放同样躲不过去。"""
        flags = self._flags([_row("20251231", op=10.0, invest=2.0, fv=2.5)])
        self.assertEqual(len(flags), 1)
        self.assertAlmostEqual(flags[0].value, 0.45, places=2)
        self.assertIn("中", flags[0].severity)          # 45% ≤ 50% → 🟡 中

    def test_normal_company_is_quiet(self):
        self.assertEqual(self._flags([_row("20251231", op=19.47, invest=4.65)]), [])

    def test_operating_loss_does_not_divide(self):
        """营业利润为负时比值没意义(会算出负数或爆表), 不报旗、不崩。"""
        self.assertEqual(self._flags([_row("20251231", op=-3.0, invest=2.0)]), [])

    def test_missing_columns_degrade_quietly(self):
        self.assertEqual(fa._invest_income_in_operating_profit({}), [])
        self.assertEqual(fa._invest_income_in_operating_profit({"income": pd.DataFrame()}), [])

    def test_flag_has_a_home_node(self):
        """红旗必须能归家, 否则 assemble 阶段 RedFlagError。"""
        from scripts import red_flags

        node, metrics = red_flags._home_of("Buffett Quality", "投资收益占营业利润过高")
        self.assertEqual(node, "quality")
        self.assertIn("non_operating", metrics)


if __name__ == "__main__":
    unittest.main()
