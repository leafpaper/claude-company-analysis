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

# ---------------------------------------------------------------- 人工指定同业(v8.7)

STOCK_BASIC = pd.DataFrame([
    {"ts_code": "688268.SH", "symbol": "688268", "name": "华特气体", "industry": "化工原料"},
    {"ts_code": "600378.SH", "symbol": "600378", "name": "昊华科技", "industry": "化工原料"},
    {"ts_code": "688087.SH", "symbol": "688087", "name": "英科再生", "industry": "化工原料"},
    {"ts_code": "688716.SH", "symbol": "688716", "name": "中船特气", "industry": "化学制品"},
    {"ts_code": "688106.SH", "symbol": "688106", "name": "金宏气体", "industry": "化学制品"},
])


def _peer_df() -> pd.DataFrame:
    base = {
        "total_mv_yi": 165.09, "pe_ttm": 109.86, "pb": 6.21, "ps_ttm": 10.22, "dv_ratio": 0.43,
        "fi_period": "20260630", "roe_latest": 3.97, "grossprofit_margin": 30.09,
        "netprofit_margin": 10.43, "debt_to_assets": 26.27, "revenue_yoy": 28.95,
    }
    return pd.DataFrame([
        {"ts_code": "688268.SH", "name": "华特气体", "industry": "化工原料", "is_target": True, **base},
        {"ts_code": "688716.SH", "name": "中船特气", "industry": "化学制品", "is_target": False, **base},
    ])


class TestPeerUniverse(unittest.TestCase):
    """按行业分类自动选同业是**已知会选错**的一步, 所以要有一条人工指定的正路。

    华特气体被 Tushare 归进「化工原料」(262 家), 自动选出的对照物与本公司零业务重合,
    估值分位与真实同业正好相反;而真同业(中船特气、金宏气体)挂在「化学制品」——
    人工指定时必须**不按行业过滤**, 否则真同业会被自己的规则筛掉。
    """

    def test_auto_mode_filters_by_industry(self):
        pool, manual, missing = peer_collector._peer_universe(STOCK_BASIC, "688268.SH", "化工原料")
        self.assertFalse(manual)
        self.assertEqual(missing, [])
        self.assertEqual(set(pool["ts_code"]), {"688268.SH", "600378.SH", "688087.SH"})

    def test_manual_mode_crosses_industry_and_keeps_target(self):
        pool, manual, missing = peer_collector._peer_universe(
            STOCK_BASIC, "688268.SH", "化工原料", ["688716.SH", "688106"]
        )
        self.assertTrue(manual)
        self.assertEqual(missing, [])
        # 裸代码补全 + 本公司自动在列
        self.assertEqual(set(pool["ts_code"]), {"688268.SH", "688716.SH", "688106.SH"})

    def test_unknown_code_is_reported_not_silently_dropped(self):
        pool, manual, missing = peer_collector._peer_universe(
            STOCK_BASIC, "688268.SH", "化工原料", ["000001.SZ"]
        )
        self.assertEqual(missing, ["000001.SZ"])


class TestPeerSourceIsStated(unittest.TestCase):
    """同业哪来的, 要写在表上 —— 读者据此决定信不信这张表的估值分位。"""

    def test_auto_mode_warns_it_may_have_picked_wrong_peers(self):
        md = peer_collector._format_markdown(_peer_df(), "688268.SH", "华特气体", "化工原料", "20260910")
        self.assertIn("零业务重合", md)
        self.assertIn("--peer-codes", md)

    def test_manual_mode_says_so_and_drops_the_warning(self):
        md = peer_collector._format_markdown(
            _peer_df(), "688268.SH", "华特气体", "化工原料", "20260910", None, True
        )
        self.assertIn("人工指定", md)
        self.assertNotIn("零业务重合", md)
