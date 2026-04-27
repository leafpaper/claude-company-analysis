"""单元测试: scripts.data_snapshot

运行:
    python3 -m scripts.tests.test_data_snapshot
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from io import StringIO
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


# ============================================================================
# v4.8.1 Bug 1 回归: §4 forecast vs actual 去重 end_date
# ============================================================================


class TestForecastVsActualDedup(unittest.TestCase):
    """Bug 1 回归: 当 income.parquet 同 end_date 有多行(年报修正/原始稿),
    必须按 ann_date 倒序去重取最新披露版本, 否则会用旧 actual 误判兑现状态。"""

    def _build_bundle(self, td: Path, income_rows: list[dict], forecast_rows: list[dict]) -> Path:
        """在临时目录构造最小 raw_data 含 income + forecast_vip 两个 parquet"""
        bundle = td / "raw_data"
        bundle.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(income_rows).to_parquet(bundle / "income.parquet")
        pd.DataFrame(forecast_rows).to_parquet(bundle / "forecast_vip.parquet")
        return bundle

    def test_revised_annual_report_overrides_original(self):
        """Bug 1 直击场景: 原始 2024 年报 actual=14000 万落预告下沿; 4 个月后修正稿 actual=15000 万 ✅ 落入区间.
        新逻辑必须取修正稿(ann_date 较新), 而不是原始稿."""
        with tempfile.TemporaryDirectory() as td:
            bundle = self._build_bundle(
                Path(td),
                income_rows=[
                    # 原始稿 (ann_date 较早)
                    {"ts_code": "TEST.SZ", "end_date": "20241231", "ann_date": "20250130",
                     "n_income_attr_p": 1.40e8},
                    # 修正稿 (ann_date 较新, ★必须被采用)
                    {"ts_code": "TEST.SZ", "end_date": "20241231", "ann_date": "20250428",
                     "n_income_attr_p": 1.50e8},
                ],
                forecast_rows=[{
                    "ts_code": "TEST.SZ", "end_date": "20241231", "ann_date": "20250115",
                    "type": "略减",
                    "net_profit_min": 14500.0, "net_profit_max": 16000.0,  # 万元
                }],
            )
            buf = StringIO()
            data_snapshot._render_section_4(bundle, buf)
            out = buf.getvalue()
            # 修正稿 1.50 亿 = 15000 万, 落入 [14500, 16000] → ✅ 落入区间
            # 旧 buggy 版本会取 1.40 亿 = 14000 万 → ⬇️ 低于下沿
            self.assertIn("✅ 落入区间", out, f"应以修正稿 1.50 亿判定为 ✅; 实际:\n{out}")
            self.assertNotIn("低于预告下沿", out, "原始稿(应被去重忽略)误判为低于下沿")
            # 实际值显示也应是修正后的 15,000.00 万
            self.assertIn("15,000.00 万", out)

    def test_no_actual_yet_uses_forecast(self):
        """forecast 已发但 income 尚无对应期 → 状态 '未发布'"""
        with tempfile.TemporaryDirectory() as td:
            bundle = self._build_bundle(
                Path(td),
                income_rows=[
                    {"ts_code": "TEST.SZ", "end_date": "20231231", "ann_date": "20240315",
                     "n_income_attr_p": 1.0e8},
                ],
                forecast_rows=[{
                    "ts_code": "TEST.SZ", "end_date": "20251231", "ann_date": "20260120",
                    "type": "预增",
                    "net_profit_min": 20000.0, "net_profit_max": 25000.0,
                }],
            )
            buf = StringIO()
            data_snapshot._render_section_4(bundle, buf)
            out = buf.getvalue()
            self.assertIn("未发布", out)


# ============================================================================
# v4.8.1 Bug 2 回归: §5/§6 表格行 NaN 边界 + 列对齐
# ============================================================================


class TestFmtCellHelper(unittest.TestCase):
    """新引入的 _fmt_cell + _md_table_row 工具函数"""

    def test_fmt_cell_normal(self):
        self.assertEqual(data_snapshot._fmt_cell(1234.5678, "{:,.2f}"), "1,234.57")

    def test_fmt_cell_with_scale(self):
        # 100,000,000 元 ÷ 1e4 = 10000 万
        self.assertEqual(data_snapshot._fmt_cell(1e8, "{:,.2f}", scale=1 / 1e4), "10,000.00")

    def test_fmt_cell_signed(self):
        self.assertEqual(data_snapshot._fmt_cell(123.4, "{:+,.2f}"), "+123.40")
        self.assertEqual(data_snapshot._fmt_cell(-123.4, "{:+,.2f}"), "-123.40")

    def test_fmt_cell_nan_returns_dash(self):
        self.assertEqual(data_snapshot._fmt_cell(None, "{:.2f}"), "–")
        self.assertEqual(data_snapshot._fmt_cell(float("nan"), "{:.2f}"), "–")

    def test_fmt_cell_string_passthrough(self):
        self.assertEqual(data_snapshot._fmt_cell("一般企业", "{}"), "一般企业")

    def test_fmt_cell_custom_na(self):
        self.assertEqual(data_snapshot._fmt_cell(None, "{}", na="N/A"), "N/A")

    def test_md_table_row_basic(self):
        self.assertEqual(
            data_snapshot._md_table_row(["a", "b", "c"]),
            "| a | b | c |\n",
        )

    def test_md_table_row_escapes_pipes(self):
        """holder_name 含 | 时不应破坏表格"""
        self.assertEqual(
            data_snapshot._md_table_row(["1", "Co|Ltd", "100"]),
            "| 1 | Co\\|Ltd | 100 |\n",
        )


class TestSection5Top10HoldersBoundary(unittest.TestCase):
    """Bug 2 回归: §5 十大股东表 NaN 边界, 验证列对齐 (旧版字符串拼接易错位)"""

    def _build_bundle(self, td: Path, holders: list[dict]) -> Path:
        bundle = td / "raw_data"
        bundle.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(holders).to_parquet(bundle / "top10_holders.parquet")
        return bundle

    def test_partial_nan_keeps_columns_aligned(self):
        """混合 NaN 场景: amt 有但 ratio NaN, 列数必须仍是 7"""
        with tempfile.TemporaryDirectory() as td:
            bundle = self._build_bundle(Path(td), [
                {"ts_code": "TEST.SZ", "end_date": "20251231", "ann_date": "20260101",
                 "holder_name": "股东 A", "hold_amount": 1000000, "hold_ratio": 5.5,
                 "hold_float_ratio": 6.0, "hold_change": 100, "holder_type": "自然人"},
                # 第二行: amt 有, ratio/float_ratio/chg 都 NaN
                {"ts_code": "TEST.SZ", "end_date": "20251231", "ann_date": "20260101",
                 "holder_name": "股东 B", "hold_amount": 500000, "hold_ratio": None,
                 "hold_float_ratio": None, "hold_change": None, "holder_type": "一般企业"},
            ])
            buf = StringIO()
            data_snapshot._render_section_5_or_6(
                bundle, buf, "top10_holders", "§5 完整十大股东表 (测试)"
            )
            out = buf.getvalue()
            # 验证 第二行 列数 = 7 (#/股东/持股数/持股比例/占流通比例/期间变动/股东类型)
            for line in out.splitlines():
                if line.startswith("| 2 |"):
                    # markdown 行: "| ... | ... | ... |"; pipe 数 = 列数 + 1
                    pipe_count = line.count("|")
                    self.assertEqual(pipe_count, 8, f"第二行列数错位: {line}")
                    self.assertIn("– | – | – |", line, "NaN 单元格应显示 –")

    def test_holder_name_with_pipe_escaped(self):
        """股东名含 |(Tushare 偶发): markdown 表格不应被破坏"""
        with tempfile.TemporaryDirectory() as td:
            bundle = self._build_bundle(Path(td), [
                {"ts_code": "TEST.SZ", "end_date": "20251231", "ann_date": "20260101",
                 "holder_name": "ABC|XYZ Co", "hold_amount": 1000000, "hold_ratio": 5.5,
                 "hold_float_ratio": 6.0, "hold_change": 100, "holder_type": "一般企业"},
            ])
            buf = StringIO()
            data_snapshot._render_section_5_or_6(
                bundle, buf, "top10_holders", "§5 完整十大股东表 (测试)"
            )
            out = buf.getvalue()
            self.assertIn(r"ABC\|XYZ Co", out, "holder_name 中的 | 应被转义")


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
