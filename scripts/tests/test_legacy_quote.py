"""单元测试: scripts.legacy_quote 模块.

运行:
    cd skills/company-analysis
    python3 -m pytest scripts/tests/test_legacy_quote.py -v

或不依赖 pytest:
    python3 -m scripts.tests.test_legacy_quote
"""
from __future__ import annotations

import sys
import unittest

import pandas as pd

from scripts import legacy_quote


PRO_DAILY_SCHEMA = {
    "ts_code", "trade_date",
    "open", "high", "low", "close",
    "pre_close", "change", "pct_chg",
    "vol", "amount",
}


class TestSinaSymbolMapping(unittest.TestCase):
    def test_bj_prefix(self):
        self.assertEqual(legacy_quote._ts_code_to_sina_symbol("920522.BJ"), "bj920522")
        self.assertEqual(legacy_quote._ts_code_to_sina_symbol("832522.BJ"), "bj832522")

    def test_sh_prefix(self):
        self.assertEqual(legacy_quote._ts_code_to_sina_symbol("600519.SH"), "sh600519")
        self.assertEqual(legacy_quote._ts_code_to_sina_symbol("688114.SH"), "sh688114")

    def test_sz_prefix(self):
        self.assertEqual(legacy_quote._ts_code_to_sina_symbol("000001.SZ"), "sz000001")
        self.assertEqual(legacy_quote._ts_code_to_sina_symbol("300451.SZ"), "sz300451")

    def test_lowercase_suffix_normalized(self):
        self.assertEqual(legacy_quote._ts_code_to_sina_symbol("920522.bj"), "bj920522")

    def test_missing_suffix_raises(self):
        with self.assertRaises(ValueError):
            legacy_quote._ts_code_to_sina_symbol("920522")

    def test_unknown_suffix_raises(self):
        with self.assertRaises(ValueError):
            legacy_quote._ts_code_to_sina_symbol("0700.HK")


class TestDailyHistorySchema(unittest.TestCase):
    """端到端:实际请求新浪,验证 schema 与 Pro 一致 (网络敏感测试)."""

    def test_bj_schema_matches_pro(self):
        df = legacy_quote.get_daily_history_legacy("920522.BJ", datalen=30)
        self.assertGreater(len(df), 0, "BJ 应能取到数据")
        self.assertEqual(set(df.columns), PRO_DAILY_SCHEMA)
        self.assertEqual(df["ts_code"].iloc[0], "920522.BJ")
        # trade_date 是 YYYYMMDD 字符串
        self.assertTrue(df["trade_date"].str.match(r"^\d{8}$").all())
        # 单位检查: vol 是手 (不是股),应是 volume / 100
        # close × vol × 100 / 1000 = amount (估算逻辑)
        latest = df.iloc[-1]
        expected_amount_estimate = latest["close"] * latest["vol"] * 100 / 1000
        self.assertAlmostEqual(
            latest["amount"], expected_amount_estimate, places=2,
            msg="amount 应等于 close × vol × 100 / 1000 (估算公式)"
        )

    def test_sh_schema_matches_pro(self):
        df = legacy_quote.get_daily_history_legacy("600519.SH", datalen=10)
        self.assertGreater(len(df), 0)
        self.assertEqual(set(df.columns), PRO_DAILY_SCHEMA)

    def test_sz_schema_matches_pro(self):
        df = legacy_quote.get_daily_history_legacy("000001.SZ", datalen=10)
        self.assertGreater(len(df), 0)
        self.assertEqual(set(df.columns), PRO_DAILY_SCHEMA)

    def test_pct_chg_computed_correctly(self):
        df = legacy_quote.get_daily_history_legacy("920522.BJ", datalen=30)
        # 第一行 pre_close 是 NaN (shift 后),pct_chg 也应是 NaN
        self.assertTrue(pd.isna(df["pre_close"].iloc[0]))
        # 后续行应该有: change = close - pre_close
        for i in range(1, min(5, len(df))):
            row = df.iloc[i]
            expected_change = round(row["close"] - row["pre_close"], 4)
            self.assertAlmostEqual(row["change"], expected_change, places=2)

    def test_invalid_code_returns_empty(self):
        # 不带后缀 → 内部捕获 ValueError 返回 空
        df = legacy_quote.get_daily_history_legacy("920522")
        self.assertTrue(df.empty)


class TestDateRangeFilter(unittest.TestCase):
    def test_filter_inclusive(self):
        df = pd.DataFrame({
            "ts_code": ["X.SH"] * 5,
            "trade_date": ["20260101", "20260102", "20260103", "20260104", "20260105"],
            "close": [10, 11, 12, 13, 14],
        })
        # 补齐 schema 占位
        for col in PRO_DAILY_SCHEMA - set(df.columns):
            df[col] = 0
        out = legacy_quote.filter_by_date_range(df, "20260102", "20260104")
        self.assertEqual(len(out), 3)
        self.assertEqual(out["trade_date"].tolist(), ["20260102", "20260103", "20260104"])

    def test_filter_handles_dashed_dates(self):
        df = pd.DataFrame({"trade_date": ["20260101", "20260105"]})
        for col in PRO_DAILY_SCHEMA - {"trade_date"}:
            df[col] = 0
        out = legacy_quote.filter_by_date_range(df, "2026-01-01", "2026-01-03")
        self.assertEqual(len(out), 1)

    def test_filter_empty_passthrough(self):
        df = pd.DataFrame()
        out = legacy_quote.filter_by_date_range(df, "20260101", "20260105")
        self.assertTrue(out.empty)


def main():
    """命令行运行 (无需 pytest)."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (TestSinaSymbolMapping, TestDailyHistorySchema, TestDateRangeFilter):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
