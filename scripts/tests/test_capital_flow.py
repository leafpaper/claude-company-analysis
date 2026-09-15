"""单元测试: capital_flow 的股东户数口径(附录C 的资金底稿源)。

Tushare `stk_holdernumber` 会返回一批还没填 `holder_num` 的期(值为 NaN，东山精密
2026-08 实测 279 行里 152 行是 NaN)。这些行没有信息量，但排序后落到最新一期时会让
户数变化变成 NaN 并在 `int()` 上直接崩掉 —— 附录C 整份产不出来。

运行:
    python -m unittest scripts.tests.test_capital_flow
"""
from __future__ import annotations

import unittest

import pandas as pd

from scripts import capital_flow as cf


def _raw(holder_rows: list[tuple[str, float | None]]) -> dict:
    """最小 raw bundle: 只喂户数, 其余维度给空表(走各自的"数据不足"分支)。"""
    raw = {
        k: pd.DataFrame()
        for k in ("top10_all", "top10_float", "daily_basic", "stock_basic",
                  "hk_hold", "margin_detail", "moneyflow", "top_inst", "top_list",
                  "block_trade")
    }
    raw["holder_num"] = pd.DataFrame(
        [{"ts_code": "002384.SZ", "end_date": ed, "holder_num": n} for ed, n in holder_rows]
    )
    return raw


class TestHolderNumberNaN(unittest.TestCase):
    def test_nan_rows_dropped_not_crashed(self):
        """最新两期是 NaN → 跳过它们取真正有值的两期, 而不是 ValueError。"""
        m = cf._derive_metrics(
            "002384.SZ",
            _raw([("20260603", None), ("20260601", None),
                  ("20260529", 306048.0), ("20260520", 284513.0)]),
        )
        self.assertEqual(m["holder_num_latest"], 306048)
        self.assertEqual(m["holder_num_period_current"], "20260529")
        self.assertEqual(m["holder_num_period_prev"], "20260520")
        self.assertAlmostEqual(m["holder_num_change"], 7.57, places=2)
        self.assertIn("筹码分散", m["chip_concentration"])      # 户数 +7.57% > 5%

    def test_all_nan_degrades_quietly(self):
        """全是 NaN → 这一维度缺失(标"数据不足"), 不写脏字段、不抛异常。"""
        m = cf._derive_metrics("002384.SZ", _raw([("20260603", None), ("20260601", None)]))
        self.assertNotIn("holder_num_latest", m)
        self.assertNotIn("holder_num_change", m)

    def test_single_valid_period_is_not_enough(self):
        """只剩一期有值 → 算不出环比, 同样不写字段。"""
        m = cf._derive_metrics(
            "002384.SZ", _raw([("20260603", None), ("20260529", 306048.0)])
        )
        self.assertNotIn("holder_num_change", m)


if __name__ == "__main__":
    unittest.main()

# ---------------------------------------------------------------- 接口没调通 ≠ 没有数据(v8.7)

class TestBlockTradeDegraded(unittest.TestCase):
    """空表有两种含义:接口没调通 / 真的没有大宗。

    华特实测: `block_trade` 静默返回 0 行, 而减持公告明写走大宗交易 —— 报告却印成
    「近 60 日无大宗交易记录」, 写手据此写了「近 60 日无大宗」。必须分开说。
    """

    def setUp(self):
        cf._CALL_ERRORS.clear()
        self.addCleanup(cf._CALL_ERRORS.clear)

    def _md(self) -> str:
        raw = _raw([("20260630", 34429.0), ("20260331", 14758.0)])
        return cf._format_markdown("002384.SZ", raw, cf._derive_metrics("002384.SZ", raw))

    def test_failed_call_is_not_reported_as_no_block_trade(self):
        cf._CALL_ERRORS["block_trade"] = "抱歉，您没有访问该接口的权限"
        md = self._md()
        self.assertIn("没调通", md)
        self.assertNotIn("无大宗交易记录", md)
        self.assertIn("§11 采集降级", md)               # 降级也要写进报告, 不只打在控制台

    def test_empty_but_successful_call_still_says_no_block_trade(self):
        md = self._md()
        self.assertIn("无大宗交易记录", md)
        self.assertNotIn("没调通", md)
        self.assertNotIn("§11 采集降级", md)
