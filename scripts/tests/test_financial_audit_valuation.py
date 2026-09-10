"""financial_audit 估值红旗的证据句 —— 会原样上首页 Top3, 必须是人话。

华特 R1 交付 FIX: 「当前 PB=6.21 / 合理 PB (ROE/8%) ≈ 0.85 = 7.3x」这种公式串直接上了首页。
数字不变(③ 的 YAML 照引 6.21 / 0.85 / 7.3), 只换说法, 算法留在括注里。
"""
import unittest

import pandas as pd

from scripts import financial_audit as fa


def _bundle(pb: float, roe: float) -> dict:
    days = pd.date_range("2025-01-01", periods=5, freq="D").strftime("%Y%m%d")
    return {
        "daily_basic": pd.DataFrame({"trade_date": days, "pb": [pb] * 5, "pe_ttm": [40.0] * 5}),
        "fina_indicator": pd.DataFrame({"end_date": ["20241231"], "roe": [roe]}),
    }


class PbRoeEvidenceTest(unittest.TestCase):
    def _evidence(self, pb: float, roe: float, signal: str) -> str:
        flags = [f for f in fa._valuation(_bundle(pb, roe)) if f.signal == signal]
        self.assertEqual(len(flags), 1, f"应恰好一条「{signal}」")
        return flags[0].evidence

    def test_overvalued_evidence_is_plain_language(self):
        self.assertEqual(
            self._evidence(6.21, 6.8, "PB vs ROE 严重错配"),
            "市净率 6.21 倍;按净资产回报率 6.8% 应配约 0.85 倍(回报率÷8%),现价是它的 7.3 倍",
        )

    def test_negative_roe_does_not_claim_the_formula(self):
        # ROE ≤ 0 时合理 PB 是写死的 0.5 保守口径, 不是「回报率÷8%」算出来的 —— 不能套那句括注
        ev = self._evidence(3.0, -4.0, "PB vs ROE 严重错配")
        self.assertIn("为负", ev)
        self.assertNotIn("回报率÷8%", ev)

    def test_undervalued_evidence_is_plain_language(self):
        ev = self._evidence(0.5, 16.0, "PB vs ROE 低估机会")
        self.assertIn("现价不到它的一半", ev)
        self.assertNotIn("PB=", ev)


if __name__ == "__main__":
    unittest.main()
