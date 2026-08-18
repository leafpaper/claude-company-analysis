"""单元测试: v8 质量环 — lint_v8(机器门控 10 条)+ review_loop(两 reviewer 分诊)。

实现票 06(.scratch/v8-implementation/issues/06-quality-loop.md)。
测试缝 = run 目录契约(spec Testing Decisions):fixture 的五个节点 YAML 块 + audit 红旗进,
断言 lint 判定出;golden 基线取东山精密推演稿(见 dongshan_fixture)。

正反 fixture 覆盖票 06 验收要求的四类:越预算 / 缺字段 / 异地裸数字 / 红旗无家,
外加封顶、Top3 漂移、报告脱节、越权、外链、无记忆性。

运行:
    python -m pytest scripts/tests/test_quality_loop_v8.py
    或  python -m unittest scripts.tests.test_quality_loop_v8
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts import assemble_report_v8 as render
from scripts import lint_v8
from scripts import red_flags as rf
from scripts import review_loop
from scripts.tests import dongshan_fixture as fx


def write_run_dir(base: Path, nodes: dict, bodies: dict, audit: dict | None) -> Path:
    """把 fixture 落成真实 run 目录(nodes/*.md 顶部 YAML 块 + 正文 + audit JSON)。"""
    run_dir = base / "runs" / "2026-06-22"
    (run_dir / "nodes").mkdir(parents=True, exist_ok=True)
    for node, block in nodes.items():
        text = yaml.safe_dump(block, allow_unicode=True, sort_keys=False)
        (run_dir / "nodes" / f"node-{node}.md").write_text(
            f"```yaml\n{text}```\n\n{bodies[node]}", encoding="utf-8"
        )
    if audit is not None:
        (run_dir / "audit_report.json").write_text(
            json.dumps(audit, ensure_ascii=False), encoding="utf-8"
        )
    return run_dir


class _Run(unittest.TestCase):
    """每个用例一个临时 run 目录:节点块 + 正文 + audit,可选装配。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.nodes = fx.nodes()
        self.bodies = dict(fx.NODE_BODIES)
        self.audit = fx.audit_result()

    def tearDown(self):
        self._tmp.cleanup()

    def build(self, assemble=True) -> Path:
        run_dir = write_run_dir(self.base, self.nodes, self.bodies, self.audit)
        if assemble:
            render.assemble_run(run_dir=run_dir, company="东山精密", date="2026-06-22")
        return run_dir

    def lint(self, assemble=True):
        return lint_v8.lint_run(self.build(assemble=assemble))

    def rule(self, result, prefix):
        for r in result.rules:
            if r.name.startswith(prefix):
                return r
        raise AssertionError(f"没有规则 {prefix}(实际:{[r.name for r in result.rules]})")

    def append_body(self, node: str, line: str):
        self.bodies[node] = self.bodies[node] + line + "\n"


# ---------------------------------------------------------------- golden(正 fixture)

class TestGoldenRunPasses(_Run):
    def test_dongshan_golden_run_has_no_fail(self):
        """东山 golden run:fail 项全过, exit 0(warn 不阻断)。"""
        result = self.lint()
        failed = [r.name for r in result.rules if r.severity == lint_v8.FAIL and not r.passed]
        self.assertEqual(failed, [], result.report)
        self.assertTrue(result.passed)

    def test_schema_and_sync_rules_actually_ran(self):
        """R1 与 R10 不是被跳过的——golden run 里两条都真判过。"""
        result = self.lint()
        for prefix in ("R1 ", "R10 "):
            rule = self.rule(result, prefix)
            self.assertFalse(rule.skipped, f"{prefix} 被跳过了")
            self.assertTrue(rule.passed)

    def test_no_report_means_sync_rule_skipped_not_failed(self):
        """没装配主报告时 R10 记 SKIP,不误判为 fail(写手刚交货就能自查)。"""
        result = self.lint(assemble=False)
        self.assertTrue(self.rule(result, "R10 ").skipped)
        self.assertTrue(result.passed)


# ---------------------------------------------------------------- R1 缺字段

class TestSchemaGate(_Run):
    def test_missing_decision_field_fails_schema(self):
        """缺字段(决策块没有 gear_cap)→ R1 fail, 且后续规则跳过而不是刷屏。"""
        self.nodes["decision"].pop("gear_cap")
        result = self.lint(assemble=False)
        r1 = self.rule(result, "R1 ")
        self.assertFalse(r1.passed)
        self.assertTrue(any("gear_cap" in f for f in r1.findings), r1.findings)
        self.assertTrue(self.rule(result, "R2 ").skipped)
        self.assertFalse(result.passed)

    def test_decision_rule_lists_every_required_field(self):
        """R7 的字段清单单测(schema 之外再兜一层, 报错话术对写手更直白)。"""
        block = copy.deepcopy(fx.decision_block())
        block.pop("what_to_wait")
        fail, _ = lint_v8.rule_decision({"decision": block}, [])
        self.assertFalse(fail.passed)
        self.assertTrue(any("what_to_wait" in f for f in fail.findings), fail.findings)


# ---------------------------------------------------------------- R2 红旗闭环

class TestRedFlagClosure(_Run):
    def _make_fatal_goodwill(self):
        """把商誉红旗升为 🔴 致命(它归④路径), 用来测归家与封顶。"""
        for entry in self.audit["red_flags"]:
            if entry["signal"] == "商誉占净资产过高":
                entry["severity"] = "🔴 致命"
        self.nodes["decision"]["action_gear"] = "回避"
        self.nodes["decision"]["gear_cap"] = {"triggered": True, "reason": "商誉减值致命红旗"}

    def test_fatal_flag_not_narrated_in_home_node_fails(self):
        """红旗无家:🔴 未在归属节点④叙述 → fail。"""
        self._make_fatal_goodwill()
        result = self.lint(assemble=False)
        r2 = self.rule(result, "R2 ")
        self.assertFalse(r2.passed)
        self.assertTrue(any("商誉" in f and "④路径" in f for f in r2.findings), r2.findings)

    def test_fatal_flag_narrated_in_home_node_passes(self):
        """同一条 🔴 在④路径讲了(命中标题词)→ 归家成立。"""
        self._make_fatal_goodwill()
        self.append_body("path", "- 商誉占净资产过高:47.69 亿商誉是左尾地板。")
        result = self.lint(assemble=False)
        self.assertTrue(self.rule(result, "R2 ").passed, self.rule(result, "R2 ").findings)

    def test_high_flag_missing_is_warn_not_fail(self):
        """🟠 未归家只是 warn——提示写手补一句, 不阻断出片。"""
        result = self.lint(assemble=False)
        self.assertFalse(self.rule(result, "R2w").passed)
        self.assertTrue(result.passed)

    def test_top3_drift_in_assembly_fails(self):
        """有人改了 assembly.json 的 Top3(或没重装配)→ 与重算不一致 = fail。"""
        run_dir = self.build()
        product_path = run_dir / "assembly" / "assembly.json"
        product = json.loads(product_path.read_text(encoding="utf-8"))
        product["top3"][0], product["top3"][1] = product["top3"][1], product["top3"][0]
        product["top3"][0]["rank"], product["top3"][1]["rank"] = 1, 2
        product_path.write_text(json.dumps(product, ensure_ascii=False), encoding="utf-8")

        result = lint_v8.lint_run(run_dir)
        r2 = self.rule(result, "R2 ")
        self.assertFalse(r2.passed)
        self.assertTrue(any("Top3 漂移" in f for f in r2.findings), r2.findings)

    def test_nomination_added_after_assembly_fails(self):
        """节点新提名了一条红旗却没重跑装配 → 清单不一致 = fail。"""
        run_dir = self.build()
        block = copy.deepcopy(self.nodes["state"])
        block["red_flag_nominations"] = [{
            "id": "late-nomination", "level": "🟠", "title": "订单口径变更",
            "evidence": "中报把代工口径并入自有品牌", "source": "nomination", "node": "state",
        }]
        text = yaml.safe_dump(block, allow_unicode=True, sort_keys=False)
        (run_dir / "nodes" / "node-state.md").write_text(
            f"```yaml\n{text}```\n\n{self.bodies['state']}", encoding="utf-8"
        )
        result = lint_v8.lint_run(run_dir)
        r2 = self.rule(result, "R2 ")
        self.assertFalse(r2.passed)
        self.assertTrue(any("late-nomination" in f for f in r2.findings), r2.findings)


# ---------------------------------------------------------------- R3 数字唯一 home

class TestNumberHome(_Run):
    def test_bare_number_reused_in_another_chapter_fails(self):
        """异地裸数字:③赔率的现价 273 元被④路径裸引 → fail。"""
        self.append_body("path", "现价 273 元 已经把完美未来买走。")
        result = self.lint(assemble=False)
        r3 = self.rule(result, "R3 ")
        self.assertFalse(r3.passed)
        self.assertTrue(any("273元" in f and "④路径" in f for f in r3.findings), r3.findings)

    def test_same_number_with_citation_passes(self):
        """带出处的引用(指向③)是链手册允许的异地写法 → pass。"""
        self.append_body("path", "现价 273 元(见③赔率)已经把完美未来买走。")
        result = self.lint(assemble=False)
        self.assertTrue(self.rule(result, "R3 ").passed, self.rule(result, "R3 ").findings)

    def test_appendix_and_front_page_are_not_judged(self):
        """首页与附录不进 R3——首页是机器装配, 附录本就是全表下沉的家。"""
        run_dir = self.build()
        md = lint_v8.find_report_md(run_dir).read_text(encoding="utf-8")
        self.assertIn("273", md)                       # 首页决断卡确实重复了现价
        self.assertTrue(lint_v8.lint_run(run_dir).passed)


# ---------------------------------------------------------------- R4 章预算

class TestChapterBudget(_Run):
    def test_over_budget_warns_but_does_not_block(self):
        """越预算:①质地 80 行 > 70 行 → warn, 出片不阻断。"""
        self.bodies["quality"] += "\n".join(f"- 第 {i} 条证据。" for i in range(80))
        result = self.lint(assemble=False)
        r4 = self.rule(result, "R4 ")
        self.assertFalse(r4.passed)
        self.assertEqual(r4.severity, lint_v8.WARN)
        self.assertTrue(any("①质地" in f and "70" in f for f in r4.findings), r4.findings)
        self.assertTrue(result.passed)

    def test_no_lower_bound_rule(self):
        """v7 的字数下限已删:三行的短章不该被判 fail(与下沉附录正面冲突)。"""
        result = self.lint(assemble=False)
        self.assertTrue(self.rule(result, "R4 ").passed)


# ---------------------------------------------------------------- R5 区间锚

class TestAnchorRange(_Run):
    def test_inverted_anchor_fails(self):
        self.nodes["odds"]["anchor_range"]["low"]["value"] = 200
        result = self.lint(assemble=False)
        r5 = self.rule(result, "R5 ")
        self.assertFalse(r5.passed)
        self.assertTrue(any("倒置" in f for f in r5.findings), r5.findings)

    def test_price_above_anchor_but_verdict_cheap_fails(self):
        self.nodes["odds"]["verdict"] = "便宜(有 slack)"
        result = self.lint(assemble=False)
        r5 = self.rule(result, "R5 ")
        self.assertFalse(r5.passed)
        self.assertTrue(any("自相矛盾" in f for f in r5.findings), r5.findings)

    def test_divergent_ends_need_a_note(self):
        """两端不同向必须写分歧原因(schema 也管, lint 再兜一层并给人话)。"""
        block = copy.deepcopy(fx.odds_block())
        block["anchor_range"]["same_direction"] = False
        block["anchor_range"].pop("divergence_note", None)
        fail, warn = lint_v8.rule_anchor({"odds": block})
        self.assertFalse(fail.passed)
        self.assertTrue(any("divergence_note" in f for f in fail.findings), fail.findings)
        self.assertFalse(warn.passed)          # verdict 没标「取决于口径」→ warn


# ---------------------------------------------------------------- R6 / R8 / R9 正文规则

class TestProseRules(_Run):
    def test_external_link_fails(self):
        self.append_body("state", "订单细节详见 capital_flow.md。")
        result = self.lint(assemble=False)
        self.assertFalse(self.rule(result, "R6 ").passed)

    def test_anchor_link_to_appendix_is_fine(self):
        """指向本报告附录的锚点链接不算外链。"""
        self.append_body("state", "完整时序见[附录A](#appendix-a)。")
        result = self.lint(assemble=False)
        self.assertTrue(self.rule(result, "R6 ").passed)

    def test_position_advice_outside_decision_fails(self):
        self.append_body("path", "建议仓位 ≤3%,设硬止损。")
        result = self.lint(assemble=False)
        r8 = self.rule(result, "R8 ")
        self.assertFalse(r8.passed)
        self.assertTrue(any("④路径" in f for f in r8.findings), r8.findings)

    def test_gear_word_referred_to_decision_is_exempt(self):
        """引用行(写明归⑤)豁免——跨节点引用是链手册鼓励的写法。"""
        self.append_body("path", "扛不扛得住只影响⑤的行动档位, 仓位不在这里给。")
        result = self.lint(assemble=False)
        self.assertTrue(self.rule(result, "R8 ").passed, self.rule(result, "R8 ").findings)

    def test_decision_chapter_may_speak_position(self):
        """⑤决策本来就是仓位与档位的唯一出处, 不进 R8。"""
        self.append_body("decision", "期权小仓 ≤2-3%,建议仓位以此为上限。")
        result = self.lint(assemble=False)
        self.assertTrue(self.rule(result, "R8 ").passed)

    def test_memoryless_fallacy_fails(self):
        self.append_body("state", "股价横盘这么久该突破了。")
        result = self.lint(assemble=False)
        self.assertFalse(self.rule(result, "R9 ").passed)

    def test_memoryless_meta_discussion_exempt(self):
        self.append_body("state", "警惕「横盘这么久该突破」这种等待时间幻觉。")
        result = self.lint(assemble=False)
        self.assertTrue(self.rule(result, "R9 ").passed)


# ---------------------------------------------------------------- R7 封顶

class TestGearCap(_Run):
    def _fatal(self):
        for entry in self.audit["red_flags"]:
            if entry["signal"] == "商誉占净资产过高":
                entry["severity"] = "🔴 致命"
        self.append_body("path", "- 商誉占净资产过高:47.69 亿商誉是左尾地板。")

    def test_fatal_flag_forces_avoid_gear(self):
        """有 🔴 却不封顶「回避」→ fail(链手册 §2.3 硬规则)。"""
        self._fatal()
        result = self.lint(assemble=False)
        r7 = self.rule(result, "R7 ")
        self.assertFalse(r7.passed)
        self.assertTrue(any("回避" in f for f in r7.findings), r7.findings)

    def test_capped_decision_passes(self):
        self._fatal()
        self.nodes["decision"]["action_gear"] = "回避"
        self.nodes["decision"]["verdict"] = "回避:致命红旗封顶"
        self.nodes["decision"]["gear_cap"] = {"triggered": True, "reason": "商誉减值 🔴"}
        result = self.lint(assemble=False)
        self.assertTrue(self.rule(result, "R7 ").passed, self.rule(result, "R7 ").findings)

    def test_cap_without_fatal_flag_warns(self):
        self.nodes["decision"]["gear_cap"] = {"triggered": True, "reason": "写手自己加的"}
        result = self.lint(assemble=False)
        self.assertFalse(self.rule(result, "R7w").passed)
        self.assertTrue(result.passed)          # 只是 warn


# ---------------------------------------------------------------- R10 报告同步

class TestReportSync(_Run):
    def test_edited_node_without_reassembly_fails(self):
        """表述类 FIX 改了节点正文却没重跑装配 → 报告与节点脱节 = fail。"""
        run_dir = self.build()
        node_md = run_dir / "nodes" / "node-quality.md"
        node_md.write_text(
            node_md.read_text(encoding="utf-8") + "\n补写一句:卡位是真的。\n", encoding="utf-8"
        )
        result = lint_v8.lint_run(run_dir)
        r10 = self.rule(result, "R10 ")
        self.assertFalse(r10.passed)
        self.assertTrue(any("①质地" in f for f in r10.findings), r10.findings)

    def test_reassembly_clears_it(self):
        run_dir = self.build()
        node_md = run_dir / "nodes" / "node-quality.md"
        node_md.write_text(
            node_md.read_text(encoding="utf-8") + "\n补写一句:卡位是真的。\n", encoding="utf-8"
        )
        render.assemble_run(run_dir=run_dir, company="东山精密", date="2026-06-22")
        self.assertTrue(lint_v8.lint_run(run_dir).passed)


# ---------------------------------------------------------------- CLI 退出码

class TestLintCli(_Run):
    def _main(self, *argv) -> int:
        old = sys.argv
        sys.argv = ["lint_v8", *argv]
        try:
            return lint_v8.main()
        finally:
            sys.argv = old

    def test_exit_0_on_golden(self):
        self.assertEqual(self._main("--run-dir", str(self.build()), "--quiet"), 0)

    def test_exit_1_on_fail(self):
        self.append_body("path", "建议买入,仓位 ≤3%。")
        self.assertEqual(self._main("--run-dir", str(self.build()), "--quiet"), 1)

    def test_exit_2_when_run_dir_incomplete(self):
        self.assertEqual(self._main("--run-dir", str(self.base), "--quiet"), 2)


# ---------------------------------------------------------------- review_loop

LOGIC_FAIL = """### 维度 1 判断链逻辑: FAIL

### FIX 指令
- [FIX-odds-判断] 反向 DCF 没给隐含增长 → 补隐含 CAGR 与可信度判定
- [FIX-state-表述] 结论没先行 → 首行改成一句话判定
"""

DELIVERY_FAIL = """### 维度 2 可读性与交付: FAIL

### FIX 指令
- [FIX-state-表述] 结论没先行 → 首行改成一句话判定
- [FIX-front-判断] 导读没答「该等什么」 → 导读补一句临界点
- [FIX-delivery-表述] 附录B 宽表在 390px 溢出 → 套横滚容器
"""

BOTH_PASS = "### 维度 1 判断链逻辑: PASS\n"


class TestReviewLoop(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.run_dir = Path(self._tmp.name) / "runs" / "2026-06-22"
        (self.run_dir / "nodes").mkdir(parents=True)
        for node, block in fx.nodes().items():
            text = yaml.safe_dump(block, allow_unicode=True, sort_keys=False)
            (self.run_dir / "nodes" / f"node-{node}.md").write_text(
                f"```yaml\n{text}```\n\n{fx.NODE_BODIES[node]}", encoding="utf-8"
            )
        (self.run_dir / "reviewer_responses").mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def respond(self, round_n: int, logic: str, delivery: str):
        d = self.run_dir / "reviewer_responses"
        (d / f"round_{round_n}_logic.md").write_text(logic, encoding="utf-8")
        (d / f"round_{round_n}_delivery.md").write_text(delivery, encoding="utf-8")

    def test_parse_judgment_and_fixes(self):
        parsed = review_loop.parse_reviewer_response(LOGIC_FAIL)
        self.assertEqual(parsed["judgment"], "FAIL")
        self.assertEqual(len(parsed["fixes"]), 2)

    def test_merge_dedupes_across_reviewers(self):
        merged = review_loop.merge_fix_lists({
            "logic": review_loop.parse_reviewer_response(LOGIC_FAIL)["fixes"],
            "delivery": review_loop.parse_reviewer_response(DELIVERY_FAIL)["fixes"],
        })
        self.assertEqual(len(merged), 4)        # 两边都提的「结论没先行」只留一条

    def test_triage_routes_judgment_to_writer_and_prose_to_main_agent(self):
        merged = review_loop.merge_fix_lists({
            "logic": review_loop.parse_reviewer_response(LOGIC_FAIL)["fixes"],
            "delivery": review_loop.parse_reviewer_response(DELIVERY_FAIL)["fixes"],
        })
        plan = review_loop.triage(merged)
        self.assertEqual(plan["restart_writers"], ["node-odds", "decision-writer"])
        self.assertEqual(plan["edit_targets"], ["nodes/node-state.md"])
        self.assertEqual(len(plan["by_node"]["delivery"]), 1)   # 交付类不惊动写手

    def test_run_reports_fail_and_writes_fix_list(self):
        self.respond(1, LOGIC_FAIL, DELIVERY_FAIL)
        out = review_loop.run(self.run_dir, 1)
        self.assertFalse(out["overall_pass"])
        self.assertEqual(out["fix_count"], 4)
        self.assertEqual(out["judgments"], {"logic": "FAIL", "delivery": "FAIL"})
        self.assertEqual(out["delivery_fixes"], 1)
        self.assertFalse(out["diff_repeat"])
        fix_md = Path(out["fix_list_path"]).read_text(encoding="utf-8")
        self.assertIn("node-odds", fix_md)
        self.assertIn("lint_v8", fix_md)        # 应用步骤必须带「重装配 + 重 lint」

    def test_both_pass_means_overall_pass(self):
        self.respond(1, BOTH_PASS, "### 维度 2 可读性与交付: PASS\n")
        self.assertTrue(review_loop.run(self.run_dir, 1)["overall_pass"])

    def test_missing_response_is_an_error_not_a_pass(self):
        (self.run_dir / "reviewer_responses" / "round_1_logic.md").write_text(
            BOTH_PASS, encoding="utf-8"
        )
        out = review_loop.run(self.run_dir, 1)
        self.assertIn("error", out)
        self.assertNotIn("overall_pass", out)

    def test_unchanged_nodes_two_rounds_is_diff_repeat(self):
        """节点 md 一个字没改就进第二轮 = 对抗, 主 agent 该转人工。"""
        self.respond(1, LOGIC_FAIL, DELIVERY_FAIL)
        review_loop.run(self.run_dir, 1)
        self.respond(2, LOGIC_FAIL, DELIVERY_FAIL)
        self.assertTrue(review_loop.run(self.run_dir, 2)["diff_repeat"])

    def test_edited_node_clears_diff_repeat(self):
        self.respond(1, LOGIC_FAIL, DELIVERY_FAIL)
        review_loop.run(self.run_dir, 1)
        p = self.run_dir / "nodes" / "node-state.md"
        p.write_text(p.read_text(encoding="utf-8") + "\n结论先行:确实在变好。\n", encoding="utf-8")
        self.respond(2, LOGIC_FAIL, DELIVERY_FAIL)
        self.assertFalse(review_loop.run(self.run_dir, 2)["diff_repeat"])


if __name__ == "__main__":
    unittest.main()
