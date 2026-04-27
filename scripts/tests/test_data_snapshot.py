"""单元测试: scripts.data_snapshot

运行:
    python3 -m scripts.tests.test_data_snapshot
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

from scripts import data_snapshot


SAMPLE_BUNDLE = Path("/Users/leafpaper/.claude/plugins/company-analysis/output/华凯易佰/raw_data")


class TestUtilities(unittest.TestCase):
    def test_fmt_value_yi(self):
        self.assertEqual(data_snapshot._fmt_value(1e8, "yi"), "1.0000 亿")
        self.assertEqual(data_snapshot._fmt_value(2.34e8, "yi"), "2.3400 亿")

    def test_fmt_value_wan(self):
        self.assertEqual(data_snapshot._fmt_value(1e4, "wan"), "1.00 万")
        self.assertEqual(data_snapshot._fmt_value(1234567, "wan"), "123.46 万")

    def test_fmt_value_nan_returns_dash(self):
        self.assertEqual(data_snapshot._fmt_value(None, "yi"), "–")
        self.assertEqual(data_snapshot._fmt_value(float("nan"), "yi"), "–")

    def test_fmt_yoy_normal(self):
        self.assertEqual(data_snapshot._fmt_yoy(120, 100), "+20.00%")
        self.assertEqual(data_snapshot._fmt_yoy(80, 100), "-20.00%")

    def test_fmt_yoy_zero_or_nan(self):
        self.assertEqual(data_snapshot._fmt_yoy(100, 0), "–")
        self.assertEqual(data_snapshot._fmt_yoy(100, None), "–")
        self.assertEqual(data_snapshot._fmt_yoy(None, 100), "–")

    def test_latest_row(self):
        df = pd.DataFrame({"end_date": ["20240101", "20260331", "20250630"], "v": [1, 2, 3]})
        latest = data_snapshot._latest_row(df)
        self.assertEqual(latest["end_date"], "20260331")
        self.assertEqual(latest["v"], 2)

    def test_latest_row_empty(self):
        self.assertIsNone(data_snapshot._latest_row(pd.DataFrame()))

    def test_all_periods_descending(self):
        df = pd.DataFrame({"end_date": ["20240101", "20260331", "20250630"]})
        periods = data_snapshot._all_periods(df)
        self.assertEqual(periods, ["20260331", "20250630", "20240101"])


@unittest.skipUnless(SAMPLE_BUNDLE.exists(), "华凯易佰 raw_data 不存在, 跳过 e2e 测试")
class TestEndToEnd(unittest.TestCase):
    """端到端: 用 华凯易佰 真实 raw_data 跑一遍 build_snapshot, 验证关键内容."""

    @classmethod
    def setUpClass(cls):
        cls.md = data_snapshot.build_snapshot(
            SAMPLE_BUNDLE, ts_code="300592.SZ", company="华凯易佰"
        )

    def test_8_sections_present(self):
        for sec in ("§1 数据完整度", "§2 最新期完整快照", "§3 多年趋势完整表",
                    "§4 业绩预告 vs 实际兑现", "§5 完整十大股东表",
                    "§6 完整十大流通股东表", "§7 质押", "§8 股东户数变化"):
            self.assertIn(sec, self.md, f"缺 {sec}")

    def test_latest_period_2026q1_present(self):
        """华凯易佰 fina_indicator 含 20260331; data_snapshot.md 必须出现"""
        self.assertIn("20260331", self.md, "§3 多年趋势表必须含最新期 20260331")

    def test_2025_annual_present(self):
        self.assertIn("20251231", self.md)

    def test_forecast_vs_actual_table_works(self):
        """§4: 2025 年报预告 13200~16200 vs 实际 14671 万 应被标 ✅ 落入区间"""
        self.assertIn("§4 业绩预告 vs 实际", self.md)
        # 实际值 14,671.01 万 落在 13,200 ~ 16,200 区间
        self.assertIn("✅ 落入区间", self.md)

    def test_top10_holders_table_min_rows(self):
        """§5 十大股东表至少 30 行 (3 期 × 10 行 = 30, 4 期 = 40)"""
        # 数 §5 段落里 "| 1 |" 这种行数
        sec5_start = self.md.find("§5 完整十大股东表")
        sec6_start = self.md.find("§6 完整十大流通股东表")
        sec5_text = self.md[sec5_start:sec6_start]
        # 数据行: 以 "| <数字> |" 开头
        import re as _re
        rows = _re.findall(r"^\| \d+ \| ", sec5_text, _re.MULTILINE)
        self.assertGreaterEqual(len(rows), 30, f"§5 十大股东行数 {len(rows)} < 30 (期望 ≥3 期 × 10 行)")

    def test_top10_floatholders_table_present(self):
        sec6_start = self.md.find("§6 完整十大流通股东表")
        sec7_start = self.md.find("§7 质押")
        sec6_text = self.md[sec6_start:sec7_start]
        import re as _re
        rows = _re.findall(r"^\| \d+ \| ", sec6_text, _re.MULTILINE)
        self.assertGreaterEqual(len(rows), 30, f"§6 十大流通股东行数 {len(rows)} < 30")

    def test_phase3_must_read_directive_present(self):
        """头部强约束规则必须存在"""
        self.assertIn("Phase 3 必读规则", self.md)
        self.assertIn("禁止用预告", self.md)


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (TestUtilities, TestEndToEnd):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
