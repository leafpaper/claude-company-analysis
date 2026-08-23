"""单元测试: v8 装配层 — red_flags(附录D 两源合并/Top3/红标反查)+ assembly + 报告渲染。

实现票 04(.scratch/v8-implementation/issues/04-assembly-layer.md)。
测试缝 = run 目录契约(spec Testing Decisions):fixture 的五个节点 YAML 块 + audit 红旗进,
断言装配产物出;golden 基线取东山精密推演稿(见 dongshan_fixture)。

运行:
    python -m pytest scripts/tests/test_assembly_v8.py
    或  python -m unittest scripts.tests.test_assembly_v8
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts import assemble_report_v8 as render
from scripts import assembly
from scripts import red_flags as rf
from scripts import update_index
from scripts import verdict_block
from scripts.tests import dongshan_fixture as fx


def build(nodes=None, script_flags=None, **kw) -> dict:
    return assembly.build_assembly(
        company="东山精密",
        date="2026-06-22",
        nodes=nodes or fx.nodes(),
        script_flags=script_flags if script_flags is not None else fx.script_flags(),
        **kw,
    )


def write_run_dir(base: Path, nodes: dict, audit: dict | None = None) -> Path:
    """把 fixture 落成一个真实 run 目录(nodes/*.md 顶部 YAML 块 + audit JSON)。"""
    run_dir = base / "runs" / "2026-06-22"
    (run_dir / "nodes").mkdir(parents=True)
    for node, block in nodes.items():
        text = yaml.safe_dump(block, allow_unicode=True, sort_keys=False)
        body = fx.NODE_BODIES[node]
        (run_dir / "nodes" / f"node-{node}.md").write_text(
            f"```yaml\n{text}```\n\n{body}", encoding="utf-8"
        )
    if audit is not None:
        (run_dir / "audit_report.json").write_text(
            json.dumps(audit, ensure_ascii=False), encoding="utf-8"
        )
    return run_dir


# ---------------------------------------------------------------- 决断卡(golden)

class TestVerdictCard(unittest.TestCase):
    def test_five_rows_match_research_02(self):
        """决断卡五行与 research/02 §6 逐行一致(零人工抄写、零漂移)。"""
        card = build()["verdict_card"]
        self.assertEqual([r["verdict"] for r in card], fx.RESEARCH_CARD)

    def test_questions_and_sources(self):
        card = build()["verdict_card"]
        self.assertEqual(
            [(r["question"], r["source_node"]) for r in card],
            [("是不是好公司", "quality"), ("在变好吗", "state"), ("贵不贵", "odds"),
             ("扛得住吗", "path"), ("怎么办", "decision")],
        )

    def test_odds_row_is_machine_composed(self):
        """赔率行 = verdict + 区间锚两端 + 现价, 机器拼(不靠写手抄)。"""
        nodes = fx.nodes()
        nodes["odds"]["current_price"] = {"value": 210, "unit": "元"}
        row = assembly.build_verdict_card(nodes)[2]["verdict"]
        self.assertEqual(row, "买完完美未来;锚区间 57-89 元 vs 现价 210 元")

    def test_divergent_anchor_marked(self):
        """区间两端不同向 → 决断卡显式标「取决于口径」。"""
        nodes = fx.nodes()
        nodes["odds"]["anchor_range"]["same_direction"] = False
        self.assertIn("两端不同向", assembly.build_verdict_card(nodes)[2]["verdict"])

    def test_quality_field(self):
        self.assertEqual(assembly.quality_field("部分好——真卡位+平庸财务"), "部分好")
        self.assertEqual(assembly.quality_field("好公司(护城河深)"), "好公司")


# ---------------------------------------------------------------- Top3(两源同池)

class TestTop3(unittest.TestCase):
    def test_top3_is_machine_derived_from_two_sources(self):
        """Top3 与 research/05 §2 一致:估值透支 / 商誉 / 散户拥挤,脚本与提名同池。"""
        top3 = build()["top3"]
        self.assertEqual([t["rank"] for t in top3], [1, 2, 3])
        self.assertEqual(
            {t["red_flag_id"] for t in top3},
            {fx.PB_FLAG_ID, fx.GOODWILL_FLAG_ID, fx.NOMINATION_CROWDING},
        )

    def test_goodwill_entry_merges_script_and_nomination(self):
        """脚本商誉规则 + 写手「对赌未披露」提名 = Top3 里的同一条(不是两条)。"""
        entry = next(t for t in build()["top3"] if t["red_flag_id"] == fx.GOODWILL_FLAG_ID)
        self.assertEqual(set(entry["red_flag_ids"]), {fx.GOODWILL_FLAG_ID, fx.NOMINATION_GOODWILL})
        self.assertIn("商誉对赌条款未披露", entry["evidence"])
        self.assertIn("写手提名", entry["evidence"])

    def test_top3_unchanged_by_goodwill_nomination(self):
        """提名「商誉对赌」后 Top3 不变(合并进已有条目, 不挤掉任何风险)——research/05 零漂移。"""
        without = fx.nodes()
        without["path"]["red_flag_nominations"] = [
            n for n in without["path"]["red_flag_nominations"]
            if n["id"] != fx.NOMINATION_GOODWILL
        ]
        before = {t["red_flag_id"] for t in build(nodes=without)["top3"]}
        after = {t["red_flag_id"] for t in build()["top3"]}
        self.assertEqual(before, after)

    def test_ranking_prefers_severity_then_corroboration(self):
        """排序键 = 级别 → 组内条数 → 归属节点; 🟡 组永远排在 🟠 组之后。"""
        levels = [rf.LEVEL_ORDER[t["level"]] for t in build()["top3"]]
        self.assertEqual(levels, sorted(levels))
        sizes = [len(t["red_flag_ids"]) for t in build()["top3"]]
        self.assertEqual(sizes[0], 3)          # 散户组: 2 条脚本户数信号 + 1 条提名

    def test_top3_skips_green_and_info(self):
        """🟢/ℹ️ 不是风险, 不进 Top3(仍留在附录D)。"""
        ids = {t["red_flag_id"] for t in build()["top3"]}
        greens = {f["id"] for f in build()["red_flags"] if f["level"] in ("🟢", "ℹ️")}
        self.assertFalse(ids & greens)


# ---------------------------------------------------------------- 赚钱面板 + 红标

class TestPanel(unittest.TestCase):
    def test_indicators_pass_through(self):
        panel = build()["panel"]
        self.assertEqual(len(panel["indicators"]), 5)
        self.assertEqual(panel["indicators"][2]["name"], "现金含量(OCF÷净利)")
        self.assertIn("五件套", panel["industry_reason"])

    def test_conclusion_quotes_quality_sub_verdicts(self):
        """结论行 = 引用质地子判定①②, 面板零新结论。"""
        conclusion = build()["panel"]["conclusion"]
        self.assertEqual(conclusion["biz_model"], "✗ 生意模式赚钱吗")
        self.assertEqual(conclusion["quality_true"], "✗ 赚钱质量真吗")

    def test_cash_indicators_marked_red_by_same_flag(self):
        """现金含量与 FCF 同挂一条 🟠 现金流红旗(research/05 §1)。"""
        by_ind = build()["red_mark_map"]["by_indicator"]
        for name in ("现金含量(OCF÷净利)", "FCF"):
            self.assertEqual(by_ind[name]["mark"], "red")
            self.assertEqual(by_ind[name]["flags"][0]["id"], fx.CASH_FLAG_ID)

    def test_roe_ugly_but_unflagged_is_not_marked(self):
        """research/05 推演点 1:ROE 0% 分位难看, 但无 audit 规则命中 → 不标色。"""
        product = build()
        self.assertNotIn("ROE + peer 分位", product["red_mark_map"]["by_indicator"])
        # DuPont 的 ℹ️ 条目关联 roe 指标, 但 ℹ️ 不是色档 → by_metric 里也不标
        self.assertNotIn("roe", product["red_mark_map"]["by_metric"])

    def test_red_mark_map_entries_are_complete(self):
        """红标反查数据齐备:级别/证据/来源/归属节点 + 附录D 锚点。"""
        entry = build()["red_mark_map"]["by_metric"]["goodwill"]
        self.assertEqual(entry["mark"], "red")
        self.assertEqual({f["source"] for f in entry["flags"]}, {"script", "nomination"})
        for flag in entry["flags"]:
            for key in ("id", "level", "title", "evidence", "source", "node", "anchor"):
                self.assertTrue(flag.get(key), f"红标条目缺 {key}")
            self.assertEqual(flag["node"], "path")

    def test_unknown_red_flag_ref_rejected(self):
        """写手不得随手标红:red_flag_ref 反查不到红旗即装配失败。"""
        nodes = fx.nodes()
        nodes["quality"]["panel"]["indicators"][4]["red_flag_ref"] = "no-such-flag"
        with self.assertRaises(rf.RedFlagError):
            build(nodes=nodes)


# ---------------------------------------------------------------- 附录D 合并产物

class TestAppendixD(unittest.TestCase):
    def test_merged_list_passes_schema(self):
        flags = build()["red_flags"]
        self.assertEqual(rf.validate_flags(flags), [])
        self.assertEqual(len(flags), 12 + 2)          # 12 条脚本 + 2 条提名

    def test_every_flag_has_a_home(self):
        for flag in build()["red_flags"]:
            self.assertIn(flag["node"], rf.NODES)
            self.assertIn(flag["source"], ("script", "nomination"))

    def test_valuation_flags_belong_to_odds(self):
        """估值红旗归赔率节点, 不混进赚钱面板(research/05 推演点 2)。"""
        flags = {f["id"]: f for f in build()["red_flags"]}
        self.assertEqual(flags[fx.PB_FLAG_ID]["node"], "odds")

    def test_goodwill_flag_belongs_to_path(self):
        flags = {f["id"]: f for f in build()["red_flags"]}
        self.assertEqual(flags[fx.GOODWILL_FLAG_ID]["node"], "path")

    def test_duplicate_id_rejected(self):
        nodes = fx.nodes()
        nodes["quality"]["red_flag_nominations"] = [
            dict(nodes["path"]["red_flag_nominations"][0], node="quality")
        ]
        with self.assertRaises(rf.RedFlagError):
            build(nodes=nodes)

    def test_flag_id_is_stable_and_ascii(self):
        """id 只随 framework+signal 变, 与清单顺序和数值无关(增量按 id diff)。"""
        self.assertEqual(rf.flag_id("Valuation", "PB 历史分位"), fx.PB_FLAG_ID)
        self.assertRegex(fx.PB_FLAG_ID, r"^[A-Za-z0-9_-]+$")

    def test_counts(self):
        c = rf.counts(build()["red_flags"])
        self.assertEqual(c["total"], 14)
        self.assertEqual(c["by_source"], {"script": 12, "nomination": 2})
        self.assertEqual(c["by_level"]["🟠"], 6)


# ---------------------------------------------------------------- 主页 metadata / 整体产物

class TestProduct(unittest.TestCase):
    def test_passes_assembly_schema(self):
        self.assertEqual(verdict_block.validate(build(), "assembly"), [])

    def test_metadata_is_action_gear_plain_plus_quality(self):
        meta = build()["metadata"]
        self.assertEqual(meta["action_gear"], "等证据临界")
        self.assertEqual(meta["verdict_plain"], "先观察等证据临界,期权小仓 ≤2-3%")
        self.assertEqual(meta["quality_field"], "部分好")

    def test_front_page_intro_carried(self):
        self.assertIn("等 2026 中报", build()["front_page_intro"])

    def test_missing_node_block_fails_loudly(self):
        with tempfile.TemporaryDirectory() as td:
            nodes = fx.nodes()
            run_dir = write_run_dir(Path(td), nodes)
            (run_dir / "nodes" / "node-odds.md").unlink()
            with self.assertRaises(assembly.AssemblyError):
                assembly.load_nodes(run_dir / "nodes")

    def test_invalid_node_block_fails_loudly(self):
        with tempfile.TemporaryDirectory() as td:
            nodes = fx.nodes()
            del nodes["state"]["critical_point"]           # 「该等什么」缺失
            run_dir = write_run_dir(Path(td), nodes)
            with self.assertRaises(assembly.AssemblyError) as cm:
                assembly.load_nodes(run_dir / "nodes")
            self.assertIn("critical_point", str(cm.exception))


# ---------------------------------------------------------------- 变化区块(增量复查双向)

class TestChangeBlock(unittest.TestCase):
    def _change(self, after_nodes) -> dict:
        product = build(
            nodes=after_nodes,
            prev_nodes=fx.nodes(),
            prev_script_flags=fx.script_flags(),
            metric_deltas=[{"name": "股价", "before": "273 元", "after": "210 元"}],
        )
        self.assertEqual(verdict_block.validate(product, "assembly"), [])
        return product["change_block"]

    def test_scenario_a_bearish(self):
        """research/03 场景A:证伪触发 + 状态翻转 → 档位 等证据临界→回避,首句答「阿尔法变了」。"""
        cb = self._change(fx.scenario_a_nodes())
        self.assertTrue(cb["alpha_summary"].startswith("阿尔法变了"))
        self.assertEqual((cb["gear_before"], cb["gear_after"]), ("等证据临界", "回避"))
        self.assertEqual(cb["flipped_nodes"], ["state"])
        self.assertIn("档位 等证据临界→回避", cb["alpha_summary"])
        self.assertEqual(
            cb["falsification_changes"],
            [{"condition": "H1 光模块营收 <40 亿或毛利率 <30%", "change": "triggered"}],
        )
        self.assertEqual(cb["metric_deltas"][0]["after"], "210 元")

    def test_scenario_a_does_not_advise_full_rerun(self):
        """观察→回避 = 跨一档(观望→撤退), 质地未翻转 → 不触硬规则 2。"""
        cb = self._change(fx.scenario_a_nodes())
        self.assertFalse(cb["full_rerun_advice"]["advised"])
        self.assertIsNone(cb["full_rerun_advice"]["reason"])

    def test_scenario_b_bullish_advises_full_rerun(self):
        """research/03 场景B:质地标脏重评后翻转 → 照常产出 + 明示「建议全量重跑」。"""
        cb = self._change(fx.scenario_b_nodes())
        self.assertTrue(cb["alpha_summary"].startswith("阿尔法变了"))
        self.assertIn("quality", cb["flipped_nodes"])
        self.assertEqual(cb["gear_after"], "期权仓")
        self.assertTrue(cb["full_rerun_advice"]["advised"])
        self.assertIn("质地判定翻转", cb["full_rerun_advice"]["reason"])

    def test_no_change_says_alpha_unchanged(self):
        cb = self._change(fx.nodes())
        self.assertTrue(cb["alpha_summary"].startswith("阿尔法没变"))
        self.assertEqual(cb["flipped_nodes"], [])
        self.assertEqual(cb["red_flag_changes"], [])
        self.assertFalse(cb["full_rerun_advice"]["advised"])

    def test_red_flag_diff_by_id(self):
        """新增/解除红旗按 id 机器 diff(增量复查用)。"""
        after = fx.nodes()
        after["path"]["red_flag_nominations"] = [
            n for n in after["path"]["red_flag_nominations"] if n["id"] != fx.NOMINATION_GOODWILL
        ]
        cb = self._change(after)
        self.assertEqual(
            [(c["id"], c["change"]) for c in cb["red_flag_changes"]],
            [(fx.NOMINATION_GOODWILL, "resolved")],
        )

    def test_gear_distance_bands(self):
        self.assertEqual(assembly.gear_distance("等证据临界", "回避"), 1)
        self.assertEqual(assembly.gear_distance("核心仓", "回避"), 2)
        self.assertEqual(assembly.gear_distance("等证据临界", "期权仓"), 1)
        self.assertEqual(assembly.gear_distance("减仓", "回避"), 0)


# ---------------------------------------------------------------- 报告渲染 + 附录挂载

class TestRenderReport(unittest.TestCase):
    def _assemble(self, td: str, with_artifacts: bool = True):
        base = Path(td) / "东山精密"
        run_dir = write_run_dir(base, fx.nodes(), fx.audit_result())
        if with_artifacts:
            (run_dir / "data_snapshot.md").write_text(
                "# 数据快照\n\n## §3 多年趋势\n\n| 年 | 营收 |\n|---|---|\n| 2025 | 400 亿 |\n",
                encoding="utf-8",
            )
            (run_dir / "peer_analysis.md").write_text("# Peer 对标\n\n5 家可比公司。\n", encoding="utf-8")
            (run_dir / "capital_flow.md").write_text("# 资金流\n\n散户户数 30.60 万。\n", encoding="utf-8")
        product, out = render.assemble_run(
            run_dir=run_dir, company="东山精密", date="2026-06-22", ticker="002384.SZ",
            next_disclosure_date="2026-08-30",
        )
        return product, out.read_text(encoding="utf-8"), run_dir

    def test_report_structure(self):
        with tempfile.TemporaryDirectory() as td:
            _, text, _ = self._assemble(td)
            for heading in ("## 首页 一眼结论", "### 决断卡", "### 赚不赚钱面板",
                            "### Top3 风险", "### 导读",
                            "## ① 质地——是不是好公司", "## ② 状态——在变好吗",
                            "## ③ 赔率——贵不贵", "## ④ 路径——扛得住吗",
                            "## ⑤ 怎么办——行动档位与证伪",
                            "## 附录A 财务与经营明细", "## 附录B 行业与对标明细",
                            "## 附录C 舆情与资金底稿", "## 附录D 红旗总清单",
                            "## 附录E 数据来源与信息缺口"):
                self.assertIn(heading, text, f"报告缺 {heading}")

    def test_front_page_carries_card_panel_top3(self):
        with tempfile.TemporaryDirectory() as td:
            _, text, _ = self._assemble(td)
            front = text.split("## ① 质地")[0]
            for row in fx.RESEARCH_CARD:
                self.assertIn(row, front)
            self.assertIn("**面板结论**", front)
            self.assertIn("散户 2.8 倍暴增+两融杠杆拥挤", front)
            self.assertIn("等 2026 中报", front)          # 人工导读位已填

    def test_metadata_block_and_stamp(self):
        with tempfile.TemporaryDirectory() as td:
            _, text, _ = self._assemble(td)
            self.assertIn("<!-- CARD_METADATA:", text)
            self.assertIn("verdict: 先观察等证据临界,期权小仓 ≤2-3%", text)
            self.assertIn("quality: 部分好", text)
            self.assertIn("next_disclosure_date: 2026-08-30", text)
            self.assertIn("**下次预约披露日**:2026-08-30", text)

    def test_appendix_d_anchors_every_flag(self):
        with tempfile.TemporaryDirectory() as td:
            product, text, _ = self._assemble(td)
            appendix_d = text.split("## 附录D")[1].split("## 附录E")[0]
            for flag in product["red_flags"]:
                self.assertIn(f'<a id="{rf.anchor(flag["id"])}"></a>', appendix_d)
            self.assertIn("写手提名", appendix_d)
            self.assertIn("脚本", appendix_d)

    def test_appendix_mounts_collector_artifacts_demoted(self):
        with tempfile.TemporaryDirectory() as td:
            product, text, _ = self._assemble(td)
            appendix_a = text.split("## 附录A")[1].split("## 附录B")[0]
            self.assertIn("### 数据快照", appendix_a)         # # → ### (下沉两级)
            self.assertIn("| 2025 | 400 亿 |", appendix_a)
            mounted = {a["key"]: a["mounted"] for a in product["appendices"]}
            self.assertTrue(mounted["A"] and mounted["B"] and mounted["C"])

    def test_missing_artifact_is_recorded_not_fatal(self):
        with tempfile.TemporaryDirectory() as td:
            product, text, _ = self._assemble(td, with_artifacts=False)
            missing = {a["key"]: a["missing"] for a in product["appendices"]}
            self.assertIn("data_snapshot.md", missing["A"])
            self.assertIn("未找到采集产物", text)
            self.assertEqual(missing["D"], [])               # D 是机器产物, 不依赖采集

    def test_assembly_json_written_and_valid(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, run_dir = self._assemble(td)
            data = json.loads((run_dir / "assembly" / "assembly.json").read_text(encoding="utf-8"))
            self.assertEqual(verdict_block.validate(data, "assembly"), [])
            self.assertEqual(len(data["verdict_card"]), 5)

    def test_node_body_heading_not_duplicated(self):
        with tempfile.TemporaryDirectory() as td:
            _, text, _ = self._assemble(td)
            self.assertEqual(text.count("## ① 质地——是不是好公司"), 1)

    def test_body_subheading_kept(self):
        """只吃本章的章节标题, 正文里的小标题原样保留。"""
        body = assembly.strip_yaml_block("```yaml\nnode: path\n```\n\n## 左尾清单\n\n五条。\n", "path")
        self.assertTrue(body.startswith("## 左尾清单"))
        eaten = assembly.strip_yaml_block("```yaml\nnode: path\n```\n\n## ④ 路径——扛得住吗\n\n正文。\n", "path")
        self.assertTrue(eaten.startswith("正文。"))

    def test_table_cells_escape_pipes(self):
        nodes = fx.nodes()
        nodes["quality"]["panel"]["indicators"][0]["value"] = "14.09% | 3.47%"
        product = build(nodes=nodes)
        table = render.render_panel(product["panel"], product["red_mark_map"])
        self.assertIn("14.09% \\| 3.47%", table)


# ---------------------------------------------------------------- 报告解析适配(站点卡片)

class TestIndexCardParsing(unittest.TestCase):
    """update_index 读 v8 报告:verdict = 行动档位人话, 新增质地字段(v7 报告解析不受影响)。"""

    def _card(self, td: str):
        base = Path(td) / "东山精密"
        run_dir = write_run_dir(base, fx.nodes(), fx.audit_result())
        _, out = render.assemble_run(
            run_dir=run_dir, company="东山精密", date="2026-06-22", ticker="002384.SZ",
        )
        return update_index.extract_metadata(out, "东山精密")

    def test_v8_card_fields(self):
        with tempfile.TemporaryDirectory() as td:
            card = self._card(td)
            self.assertEqual(card.verdict, "先观察等证据临界,期权小仓 ≤2-3%")
            self.assertEqual(card.quality_field, "部分好")
            self.assertEqual(card.verdict_tone, "neutral")     # 等证据临界 → 中性
            self.assertEqual(card.version, "v8.0")
            self.assertEqual(card.ticker, "002384.SZ")
            self.assertEqual(card.report_date, "2026-06-22")

    def test_quality_badge_present(self):
        with tempfile.TemporaryDirectory() as td:
            labels = [b["label"] for b in self._card(td).badges]
            self.assertIn("质地 部分好", labels)

    def test_gear_drives_tone(self):
        self.assertEqual(update_index.GEAR_TONE["回避"], "bearish")
        self.assertEqual(update_index.GEAR_TONE["核心仓"], "bullish")


class TestPreviewData(unittest.TestCase):
    """reports.data.js = reports.json 的派生快照(file:// 预览的兜底数据源)。"""

    def _repo(self, td: str, with_preview: bool) -> Path:
        repo = Path(td) / "Inves-Report"
        (repo / "data").mkdir(parents=True)
        (repo / "data" / "reports.json").write_text(
            json.dumps({"schema_version": "v1", "reports": [{"slug": "002384_东山精密"}]},
                       ensure_ascii=False),
            encoding="utf-8",
        )
        if with_preview:
            (repo / "reports.data.js").write_text("window.REPORTS_RAW = {};\n", encoding="utf-8-sig")
        return repo

    def test_refresh_rewrites_snapshot_with_bom(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self._repo(td, with_preview=True)
            self.assertTrue(update_index.refresh_preview_data(repo))
            raw = (repo / "reports.data.js").read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "缺 BOM 会让浏览器按 ANSI 解中文")
            text = raw.decode("utf-8-sig")
            self.assertIn("window.REPORTS_RAW = {", text)
            self.assertIn("002384_东山精密", text)
            self.assertTrue(text.rstrip().endswith("};"))

    def test_absent_file_needs_explicit_create(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self._repo(td, with_preview=False)
            self.assertFalse(update_index.refresh_preview_data(repo))
            self.assertFalse((repo / "reports.data.js").exists())
            self.assertTrue(update_index.refresh_preview_data(repo, create=True))
            self.assertTrue((repo / "reports.data.js").exists())

    def test_no_reports_json_is_noop(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "Inves-Report"
            repo.mkdir()
            self.assertFalse(update_index.refresh_preview_data(repo, create=True))


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (TestVerdictCard, TestTop3, TestPanel, TestAppendixD, TestProduct,
                TestChangeBlock, TestRenderReport, TestIndexCardParsing, TestPreviewData):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
