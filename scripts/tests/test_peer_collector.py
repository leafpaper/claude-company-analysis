"""单元测试: peer_collector 的「最新期」选取(v8.4 实战缺陷回归)。

**这个 bug 会污染任何一份报告**,所以单独钉一条:
`fina_indicator` 的最新期必须**按 end_date 排序后取第一行**,不能直接 `iloc[-1]` ——
Tushare 返回的是**最新在前**,`iloc[-1]` 拿到的是最旧那期。

实测后果(中际旭创 2026-09-01 run):`start_year=今年-2` 时取到 **20240331** 的
ROE 6.74 / 毛利率 32.76,而真实最新期是 44.16% / 46.25%。
于是附录B 与正文当场打架,①质地的 peer 分位五个指标只能全部留 null。
装配层已加就地口径提示止血,但根因在这里。

运行:
    python -m unittest scripts.tests.test_peer_collector
"""
from __future__ import annotations

import unittest

import pandas as pd

from scripts import peer_collector


def fina_indicator_frame() -> pd.DataFrame:
    """模拟 Tushare fina_indicator 的返回:**最新在前**(这是被踩到的那个前提)。"""
    return pd.DataFrame(
        [
            {"end_date": "20260630", "roe": 44.16, "grossprofit_margin": 46.25,
             "netprofit_margin": 35.27, "debt_to_assets": 25.45},
            {"end_date": "20251231", "roe": 30.97, "grossprofit_margin": 42.04,
             "netprofit_margin": 30.28, "debt_to_assets": 28.10},
            {"end_date": "20240331", "roe": 6.74, "grossprofit_margin": 32.76,
             "netprofit_margin": 21.22, "debt_to_assets": 25.45},
        ]
    )


def pick_latest(fi: pd.DataFrame) -> tuple[pd.Series, str | None]:
    """复刻 peer_collector 里那段选取逻辑(与源码同形, 便于单独钉住行为)。"""
    latest = pd.Series(dtype=object)
    period = None
    if not fi.empty and "end_date" in fi.columns:
        ordered = fi.sort_values("end_date", ascending=False)
        latest = ordered.iloc[0]
        period = str(latest.get("end_date") or "") or None
    elif not fi.empty:
        latest = fi.iloc[0]
    return latest, period


class TestLatestPeriodSelection(unittest.TestCase):

    def test_picks_newest_not_oldest(self):
        """最新在前的输入下, 取到的必须是 20260630, 不是 iloc[-1] 的 20240331。"""
        latest, period = pick_latest(fina_indicator_frame())
        self.assertEqual(period, "20260630")
        self.assertAlmostEqual(latest["roe"], 44.16)
        self.assertAlmostEqual(latest["grossprofit_margin"], 46.25)

    def test_iloc_minus_one_would_have_been_wrong(self):
        """把踩过的坑本身钉住:旧写法在这份输入上拿到的就是那个错值。"""
        fi = fina_indicator_frame()
        self.assertAlmostEqual(fi.iloc[-1]["roe"], 6.74)      # ← 旧 bug 的产物
        self.assertNotEqual(fi.iloc[-1]["end_date"], pick_latest(fi)[1])

    def test_order_agnostic(self):
        """升序输入也要拿到同一期 —— 不依赖上游的返回顺序。"""
        ascending = fina_indicator_frame().sort_values("end_date")
        self.assertEqual(pick_latest(ascending)[1], "20260630")

    def test_empty_frame_is_safe(self):
        latest, period = pick_latest(pd.DataFrame())
        self.assertTrue(latest.empty)
        self.assertIsNone(period)

    def test_missing_end_date_column_does_not_take_last_row(self):
        """没有 end_date 列时不猜期别, 但也别退回 `iloc[-1]` 那个已知会取旧值的写法。"""
        fi = fina_indicator_frame().drop(columns=["end_date"])
        latest, period = pick_latest(fi)
        self.assertIsNone(period)
        self.assertAlmostEqual(latest["roe"], 44.16)          # = iloc[0], 不是 6.74


class TestPeriodIsExposed(unittest.TestCase):

    def test_fi_period_is_a_table_column(self):
        """期别要出现在对标表里 —— 各家不同期时读者必须看得见, 不能只在代码里知道。"""
        fields = dict(peer_collector.COMPARE_FIELDS)
        self.assertIn("fi_period", fields)
        self.assertEqual(fields["fi_period"], "财务期别")
        # 排在盈利能力列之前, 读者先看到口径再看数
        keys = [k for k, _ in peer_collector.COMPARE_FIELDS]
        self.assertLess(keys.index("fi_period"), keys.index("roe_latest"))


if __name__ == "__main__":
    unittest.main()
