"""单元测试: v8 依赖图调度 — 任意节点子集 → 执行波次。

实现票 05(.scratch/v8-implementation/issues/05-fullrun-writer-pipeline.md)。
测试的是外部行为:子集进、波次出;全量与增量(标脏子集)共用同一套调度,
波次基线取 research/09 §A + 票 11 裁决(第一波 质地∥赔率 → 第二波 状态∥路径 → 第三波 决策;
④路径的左尾深度 depth_pct 以③的锚为分母, 所以不能与③同波)
与 research/03 的中报双向场景(场景A 质地复用 / 场景B 质地标脏)。

运行:
    python -m pytest scripts/tests/test_node_graph.py
    或  python -m unittest scripts.tests.test_node_graph
"""
from __future__ import annotations

import unittest

from scripts import node_graph as ng


class TestFullRun(unittest.TestCase):
    def test_two_waves_plus_decision(self):
        """全量 = 三波:质地∥赔率 → 状态∥路径 → 决策(票 11 把④从第一波挪到第二波)。"""
        self.assertEqual(
            ng.plan_waves(ng.NODES),
            [["quality", "odds"], ["path", "state"], ["decision"]],
        )

    def test_moving_path_costs_no_extra_wave(self):
        """挪波次的代价必须是零:总波次仍是 3, 前两波仍各有两个节点并行。"""
        waves = ng.plan_waves(ng.NODES)
        self.assertEqual(len(waves), 3)
        self.assertEqual([len(w) for w in waves], [2, 2, 1])

    def test_state_never_shares_a_wave_with_odds(self):
        """②状态四层验证第④关要引用③赔率 verdict, 不能并行。"""
        for wave in ng.plan_waves(ng.NODES):
            self.assertFalse({"state", "odds"} <= set(wave))

    def test_path_never_shares_a_wave_with_odds(self):
        """④路径的 left_tail[].depth_pct 分母 = ③的锚与现价(票 11), 不能并行。

        票 09 验收暴露的真缺陷: ③④同波时④只拿得到上一版的③锚, 终稿两套锚并存,
        靠评审轮回填。左尾还是散文时只是措辞不齐, 变成数值字段之后就是硬错。
        """
        for wave in ng.plan_waves(ng.NODES):
            self.assertFalse({"path", "odds"} <= set(wave))

    def test_decision_is_last(self):
        waves = ng.plan_waves(ng.NODES)
        self.assertEqual(waves[-1], ["decision"])

    def test_every_node_has_exactly_one_writer(self):
        """1 节点 = 1 手册 = 1 写手(research/09 §C 的绑定表)。"""
        self.assertEqual(set(ng.AGENTS), set(ng.NODES))
        self.assertEqual(len(set(ng.AGENTS.values())), len(ng.NODES))


class TestSubsetRun(unittest.TestCase):
    """增量复查: 只跑标脏子集, 子集外依赖由上版复用块供给。"""

    def test_scenario_a_quality_reused(self):
        """research/03 场景A: 质地复用, 其余重评 → 赔率 → 状态∥路径 → 决策。"""
        self.assertEqual(
            ng.plan_waves(["odds", "path", "state", "decision"]),
            [["odds"], ["path", "state"], ["decision"]],
        )

    def test_scenario_b_quality_dirty(self):
        """research/03 场景B: 分部占比跨档 → 质地标脏, 退化回全量波次。"""
        self.assertEqual(
            ng.plan_waves(["quality", "odds", "path", "state", "decision"]),
            ng.plan_waves(ng.NODES),
        )

    def test_state_alone_runs_immediately(self):
        """子集只有②状态时, ③赔率是复用块——不阻塞, 但要被列进 external_deps。"""
        self.assertEqual(ng.plan_waves(["state"]), [["state"]])
        self.assertEqual(ng.external_deps(["state"]), {"state": ["odds"]})

    def test_external_deps_empty_on_full_run(self):
        self.assertEqual(ng.external_deps(ng.NODES), {})

    def test_decision_only_lists_all_four_as_external(self):
        """R4「决策层+首页永远重装配」: 单跑决策时四个节点块必须都已就位。"""
        self.assertEqual(
            ng.external_deps(["decision"]),
            {"decision": ["quality", "state", "odds", "path"]},
        )

    def test_reused_is_the_complement(self):
        p = ng.plan(["state", "decision"])
        self.assertEqual(p["reused"], ["quality", "odds", "path"])

    def test_always_rerun_nodes_are_on_the_chain(self):
        """spec §8: 状态/赔率每次必重评, 决策层必跑。"""
        self.assertTrue(set(ng.ALWAYS_RERUN) <= set(ng.NODES))


class TestNormalize(unittest.TestCase):
    def test_accepts_comma_string_and_dedupes(self):
        self.assertEqual(ng.normalize("state, odds ,state"), ["odds", "state"])

    def test_order_is_canonical_not_input_order(self):
        """波次输出稳定可比: 与调用方给的顺序无关。"""
        self.assertEqual(ng.normalize(["decision", "quality"]), ["quality", "decision"])

    def test_unknown_node_rejected(self):
        """旧的 part 名(或拼错)必须炸, 不许静默跑一半。"""
        with self.assertRaises(ng.UnknownNode):
            ng.normalize(["quality", "phase3-part3"])

    def test_empty_subset_is_empty_plan(self):
        self.assertEqual(ng.plan_waves([]), [])


class TestDescribe(unittest.TestCase):
    def test_describe_marks_parallel_wave(self):
        lines = ng.describe(ng.plan_waves(ng.NODES))
        for i in (0, 1):                    # 前两波各两个节点并行(票 11 后)
            self.assertIn("并行", lines[i])
            self.assertIn("∥", lines[i])
        self.assertIn("单个", lines[2])     # ⑤决策独占末波

    def test_plan_agents_mirror_waves(self):
        p = ng.plan(ng.NODES)
        self.assertEqual(p["agents"][0], ["node-quality", "node-odds"])
        self.assertEqual(p["agents"][1], ["node-path", "node-state"])
        self.assertEqual(p["agents"][-1], ["decision-writer"])


if __name__ == "__main__":
    unittest.main()
