"""单元测试: lint_v8 的两条新规则(v8.4 实战 lesson 转成机检)。

两条都来自票 10 的真实修正循环 —— reviewer-logic 手工抓到、机器当时查不出来:

**R13 证伪清单同源**:③换了权重依据 → ④主动改写了对应证伪 → ⑤那条**因④而写、
又只在④被删掉**的退出线留在原地,成了全链唯一持有它的节点。手册 §1.4 写死
「证伪的唯一出处是④」,于是它是一处权威之外的第二处,下次增量复查逐条核销时无源可核。
数字对不对机器早就在查(R3/R12),但「这个**条目**还该不该存在」查不了。

**R14 机器块无过程注释**:⑤的证伪条尾巴挂着「该条表述④正在同步改写,以④定稿为准」——
写下时诚实,④定稿(方向是删除)那一刻就成了指向空处的指针,且会随成品长期留档。

运行:
    python -m unittest scripts.tests.test_lint_r13_r14
"""
from __future__ import annotations

import unittest

from scripts import lint_v8


def path_block(conditions: list[str]) -> dict:
    return {"node": "path", "falsifications": [{"condition": c, "triggered": False} for c in conditions]}


def decision_block(exits: list[str]) -> dict:
    return {"node": "decision", "falsification_exit": exits}


# 取自中际旭创 2026-09-01 run 的真实条目(④共 10 条, 这里留有代表性的 4 条)
PATH_REAL = [
    "【毛利率】2026 年三季报(2026-10 披露,季报利润表口径)单季毛利率跌破 40%——2026H1 为 46.25%、光模块分部 46.59%,FY2025 为 42.04%",
    "【客户】FY2026 年报(2027-04,年报前五大客户表口径)前五大客户合计 >80% 或客户 A 单家 >30%(FY2025 为 75.98% / 24.06%)",
    "【现金】经营现金流 ÷ 归母净利 <0.5x——2026H1 中期口径 0.13x 已命中(2025H1 为 0.81x、FY2025 为 1.01x)",
    "【乐观情景的产能腿】2027-04-30 前在建工程较 2026-06-30 的 37.07 亿元不增反降且未转固形成新增产能,或 FY2026 产能利用率跌破 70%(2026H1 为 85.1%)",
]
# ⑤ 会把④的长条件压缩成一句 —— 这是允许的, 规则要的是「找得到同一个门槛」
DECISION_OK = [
    "【毛利率】2026 年三季报单季毛利率跌破 40%(2026H1 为 46.25%、光模块分部 46.59%)(引用④)",
    "【客户】FY2026 年报前五大客户合计 >80% 或客户 A 单家 >30%(FY2025 为 75.98% / 24.06%)(引用④)",
    "【现金】经营现金流 ÷ 归母净利 <0.5x——2026H1 中期口径 0.13x 已命中(引用④)",
    "【乐观情景的产能腿】2027-04-30 前在建工程较 37.07 亿元不增反降且未转固,或 FY2026 产能利用率跌破 70%(引用④)",
]
# 实战里那条真孤儿:④删掉之后⑤还留着
ORPHAN = ("【外部锚】2026-12-31 前 2027 年归母一致预期自 524 亿下修 >20%(降至 <420 亿)"
          "(引用④;该条表述④正在同步改写,以④定稿为准)")


class TestR13FalsificationSource(unittest.TestCase):

    def rule(self, exits, conditions=None):
        return lint_v8.rule_falsification_source({
            "path": path_block(conditions if conditions is not None else PATH_REAL),
            "decision": decision_block(exits),
        })

    def test_compressed_restatements_are_accepted(self):
        """⑤压缩④的措辞是允许的 —— 只要门槛数字对得上就算同源, 不要求逐字相等。"""
        r = self.rule(DECISION_OK)
        self.assertTrue(r.passed, r.findings)

    def test_orphan_exit_line_is_caught(self):
        """④已删掉的那条留在⑤里 = 孤儿, 必须报出来(这是实战里漏掉的那条)。"""
        r = self.rule(DECISION_OK + [ORPHAN])
        self.assertFalse(r.passed)
        self.assertEqual(len(r.findings), 1)
        self.assertIn("外部锚", r.findings[0])

    def test_dates_and_small_numbers_do_not_count_as_shared_evidence(self):
        """年份与两位小整数满篇都是, 不能当同源证据 —— 否则任意两条都能撞上。

        这正是第一版规则放过那条孤儿的原因:它与④共享 `2026`/`20`, 就被判成有源。
        """
        r = self.rule(["【瞎编】2026 年之前某个指标下降 >20%"])
        self.assertFalse(r.passed)

    def test_baseline_numbers_inside_parentheses_still_count(self):
        """基线数字常在括注里 —— 指纹取全文, 剥括注只用于骨架比对。

        第二版规则曾因剥掉括注把【客户】那条误判成孤儿(剥完只剩 >80%/>30% 两位数)。
        """
        r = self.rule([DECISION_OK[1]])
        self.assertTrue(r.passed, r.findings)

    def test_path_without_falsifications_is_a_hard_fail(self):
        r = self.rule(DECISION_OK, conditions=[])
        self.assertFalse(r.passed)

    def test_no_exit_lines_is_skipped_not_failed(self):
        r = self.rule([])
        self.assertTrue(r.skipped)


class TestR14ProcessNotes(unittest.TestCase):

    def rule(self, nodes):
        return lint_v8.rule_no_process_notes(nodes)

    def test_tense_word_in_yaml_is_caught(self):
        """实战原话:「该条表述④正在同步改写,以④定稿为准」。"""
        r = self.rule({"decision": decision_block([ORPHAN])})
        self.assertFalse(r.passed)
        self.assertIn("正在同步", r.findings[0])

    def test_clean_block_passes(self):
        r = self.rule({"decision": decision_block(DECISION_OK), "path": path_block(PATH_REAL)})
        self.assertTrue(r.passed, r.findings)

    def test_observation_windows_are_not_process_notes(self):
        """「待 FY2026 年报确认」是给读者的观察窗口, 不是给自己的备忘 —— 不该误报。"""
        r = self.rule({"path": path_block([
            "【现金】经营现金流 ÷ 归母净利 <0.5x,2026H1 已命中,待 FY2026 年报确认全年",
        ])})
        self.assertTrue(r.passed, r.findings)

    def test_is_a_warning_not_a_blocker(self):
        """时态词是留档瑕疵, 不该挡住出片 —— 判 warn。"""
        r = self.rule({"decision": decision_block([ORPHAN])})
        self.assertEqual(r.severity, lint_v8.WARN)

    def test_walks_nested_fields(self):
        """YAML 块是嵌套的, 时态词可能藏在任意一层。"""
        r = self.rule({"odds": {"node": "odds", "derivation": {"sotp": {"note": "倍数暂定,稍后补"}}}})
        self.assertFalse(r.passed)


if __name__ == "__main__":
    unittest.main()
