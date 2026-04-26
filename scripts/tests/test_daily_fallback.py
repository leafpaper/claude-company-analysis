"""集成测试: TushareCollector.daily() 在 Pro 返回空时会触发 legacy fallback.

无法在 CI 模拟"Pro 积分不足", 因此用 monkeypatch 直接让 Pro 接口返回空,
验证下游 fallback 分支命中并产生 Pro 风格 schema 的 DataFrame。

运行:
    cd skills/company-analysis
    python3 -m scripts.tests.test_daily_fallback
"""
from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from scripts.tushare_collector import TushareCollector
from scripts.legacy_quote import get_daily_history_legacy


class TestDailyFallback(unittest.TestCase):
    def setUp(self):
        self.tc = TushareCollector()
        # 强制走真实 _ensure_pro 但拦截 _call 让其返回空,模拟"Pro 积分不足"
        self.tc._ensure_pro()
        # 清缓存避免之前测试 / 真实调用结果干扰
        from scripts import data_cache
        for ts_code in ("920522.BJ",):
            for years in (1, 3):
                data_cache.invalidate(f"tushare_daily_{ts_code}_y{years}")

    def test_pro_empty_triggers_legacy_fallback(self):
        """Pro 返回空 → fallback 命中 → DataFrame schema 与 Pro 一致."""
        # patch _call 让它对 daily 返回空
        original_call = self.tc._call

        def mock_call(fn, **kwargs):
            if getattr(fn, "__name__", "") == "daily":
                return pd.DataFrame()
            return original_call(fn, **kwargs)

        with patch.object(self.tc, "_call", side_effect=mock_call):
            df = self.tc.daily("920522.BJ", years=1)

        self.assertGreater(len(df), 0, "fallback 应返回非空 DataFrame")
        expected_cols = {
            "ts_code", "trade_date", "open", "high", "low", "close",
            "pre_close", "change", "pct_chg", "vol", "amount",
        }
        self.assertEqual(set(df.columns), expected_cols)
        self.assertEqual(df["ts_code"].iloc[0], "920522.BJ")

    def test_pro_nonempty_no_fallback(self):
        """Pro 返回非空 → 不会触发 fallback (走正常路径)."""
        # 让 _call 返回明显标记的"Pro 数据"
        sentinel_df = pd.DataFrame({
            "ts_code": ["920522.BJ"],
            "trade_date": ["20260424"],
            "open": [100.0], "high": [101.0], "low": [99.0], "close": [100.5],
            "pre_close": [99.5], "change": [1.0], "pct_chg": [1.005],
            "vol": [99999.0], "amount": [9999999.0],
            "_marker": ["from_pro"],
        })

        def mock_call(fn, **kwargs):
            return sentinel_df.copy()

        # 同时 mock legacy 以确保不被调用
        with patch.object(self.tc, "_call", side_effect=mock_call), \
             patch("scripts.legacy_quote.get_daily_history_legacy") as mock_legacy:
            df = self.tc.daily("920522.BJ", years=1)

        mock_legacy.assert_not_called()
        self.assertIn("_marker", df.columns)
        self.assertEqual(df["_marker"].iloc[0], "from_pro")


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestDailyFallback)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
