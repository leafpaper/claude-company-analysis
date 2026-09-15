"""附录C 的技术面底稿不许替⑤决策发号施令。

金山 688111 R1 逻辑评审报出:`technical_analysis.py` §4 是 v7 时代留下的「应用指南」,
写着「是加仓时机」「应减仓或止损」「可作为止损参考」「向上突破为技术面买点信号」,
与同一份报告里⑤决策的「0 仓位、等证据临界」直接冲突。

为什么不做成 lint 规则:R8 越权发声只扫**节点正文**,附录是外部产物挂进来的;
把 R8 扩到附录会误伤资金面/舆情底稿里对券商观点的**引述**(引述别人说买不等于自己在建议)。
缺陷的源头是我们自己的模板在下指令,判据就钉在脚本产出上。

运行:
    python -m unittest scripts.tests.test_technical_analysis
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from scripts import technical_analysis as ta


# 行动档位语:出现在自家模板里就是越权(引述场景不在本脚本的职责内)
ACTION_WORDS = (
    "加仓时机", "应减仓", "止损参考", "买点信号", "卖点信号",
    "建议买入", "建议卖出", "可以抄底", "该建仓", "不要追",
)


def _series(n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(20260916)
    close = 100 + np.cumsum(rng.normal(0, 1.5, n))
    dates = pd.date_range("2025-01-02", periods=n, freq="B").strftime("%Y%m%d")
    return pd.DataFrame({
        "trade_date": dates,
        "open": close, "high": close * 1.02, "low": close * 0.98,
        "close": close, "vol": rng.integers(1e5, 1e6, n).astype(float),
    })


class NoActionTierLanguageTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import tempfile
        from pathlib import Path

        cls._td = tempfile.TemporaryDirectory()
        p = Path(cls._td.name) / "daily.parquet"
        _series().to_parquet(p)
        _df, _s, cls.md = ta.analyze(p, "688111.SH")

    @classmethod
    def tearDownClass(cls):
        cls._td.cleanup()

    def test_no_buy_sell_orders(self):
        hits = [w for w in ACTION_WORDS if w in self.md]
        self.assertEqual(hits, [], f"技术面底稿出现行动档位语: {hits}")

    def test_it_says_who_owns_the_call(self):
        """不是删干净就完了 —— 要明说档位归⑤,否则下游写手仍会拿它当依据。"""
        self.assertIn("⑤决策", self.md)

    def test_price_levels_are_still_there(self):
        """支撑/阻力位本身有用(④量左尾深度、⑤写价格条件都要引),不能连数字一起删掉。"""
        self.assertIn("支撑", self.md)
        self.assertIn("阻力", self.md)


if __name__ == "__main__":
    unittest.main()
