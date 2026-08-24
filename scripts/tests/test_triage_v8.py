"""单元测试: v8 增量复查 R2 纯脚本分诊(scripts/triage.py)+ init_run 基线快照/硬规则1。

实现票 09(.scratch/v8-implementation/issues/09-incremental-review.md)。
行为基线 = research/03 东山中报双向场景:
  场景 A(兑现不足): 质地四条标脏规则均未触发 → 复用盖戳, 重评 赔率∥路径 → 状态 → 决策;
  场景 B(超预期):   光模块分部占比 3.58%→12% 跨 10% 档线 → 质地标脏, 五节点全重评。
只测外部行为: 目录进、triage.json 出;不断言内部数据结构。

运行:
    python -m unittest scripts.tests.test_triage_v8
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts import assembly, init_run, node_graph, triage, verdict_block
from scripts import manifest as manifest_mod
from scripts.tests import dongshan_fixture as fx

PREV_DATE = "2026-06-22"
NEW_DATE = "2026-08-24"

# 基线指标(东山 2026-06-22 版口径, 数字取自推演稿量级)
BASE_METRICS = {
    "valuation": {"pb": 17.3, "pe_ttm": 192.0, "latest_close": 273.0},
    "profitability": {"roe_latest": 1.58},
    "growth": {"net_income_yoy_latest": 0.27},
    "cashflow": {"operating_cashflow_latest": -2.4e9, "free_cashflow_latest": -2.4e9},
    "latest_vitals": {"latest_net_income": 1.1e9},
}

# 场景 A: 股价/PB 下杀但现金流未变号
FRESH_METRICS_A = {
    "valuation": {"pb": 12.1, "pe_ttm": 130.0, "latest_close": 210.0},
    "profitability": {"roe_latest": 1.62},
    "growth": {"net_income_yoy_latest": 0.21},
    "cashflow": {"operating_cashflow_latest": -1.8e9, "free_cashflow_latest": -2.0e9},
    "latest_vitals": {"latest_net_income": 1.2e9},
}

SEG_BASE = [("20251231", "PCB", 96.42e8), ("20251231", "光模块", 3.58e8)]
SEG_A = [("20260630", "PCB", 92.9e8), ("20260630", "光模块", 7.1e8)]     # 未跨 10% 档线
SEG_B = [("20260630", "PCB", 88.0e8), ("20260630", "光模块", 12.0e8)]    # 跨 10% 档线

PDFS_BEFORE = ["annual_2025_full.pdf", "q1_2026.pdf"]


def write_mainbz(path: Path, rows) -> None:
    import pandas as pd

    pd.DataFrame(
        [
            {"ts_code": "002384.SZ", "end_date": d, "bz_item": i, "bz_code": "P", "bz_sales": s}
            for d, i, s in rows
        ]
    ).to_parquet(path)


def write_nodes(nodes_dir: Path, nodes: dict) -> None:
    nodes_dir.mkdir(parents=True, exist_ok=True)
    for node, block in nodes.items():
        text = yaml.safe_dump(block, allow_unicode=True, sort_keys=False)
        (nodes_dir / f"node-{node}.md").write_text(
            f"```yaml\n{text}```\n\n{fx.NODE_BODIES[node]}", encoding="utf-8"
        )


class TriageEnv(unittest.TestCase):
    """搭一个完整的公司目录 + 基线快照, 各测试改动最少的那一侧。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.company_dir = Path(self.tmp.name) / "东山精密"
        self.run_dir = self.company_dir / "runs" / NEW_DATE
        self.bl = self.run_dir / init_run.BASELINE_DIR

        write_nodes(self.company_dir / "runs" / PREV_DATE / "nodes", fx.nodes())
        (self.run_dir / "nodes").mkdir(parents=True)
        self.bl.mkdir()

        self.write_manifest()
        # 基线侧
        self._json(self.bl / "metrics.json", BASE_METRICS)
        self._json(self.bl / "red_flags.json", fx.script_flags())
        self._json(self.bl / "pdfs_before.json", PDFS_BEFORE)
        self._json(self.bl / "baseline.json", {"prev_run_date": PREV_DATE, "prev_run_type": "full", "files": []})
        write_mainbz(self.bl / "fina_mainbz.parquet", SEG_BASE)
        # 刷新后(默认 = 场景 A: 新增中报 PDF, 无年报, 红旗不变, 未变号, 未跨档)
        self._json(self.company_dir / "metrics.json", FRESH_METRICS_A)
        self._json(self.company_dir / "red_flags.json", fx.script_flags())
        pdfs = self.company_dir / "raw_data" / "pdfs"
        pdfs.mkdir(parents=True)
        for name in PDFS_BEFORE + ["h1_2026.pdf"]:
            (pdfs / name).write_bytes(b"%PDF-1.4 stub")
        write_mainbz(self.company_dir / "raw_data" / "fina_mainbz.parquet", SEG_A)

    def _json(self, path: Path, data) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def write_manifest(self, last_full=PREV_DATE, incremental_count=1):
        manifest_mod.save(self.company_dir, {
            "company": "东山精密",
            "ticker": "002384.SZ",
            "market": "a",
            "runs": [
                {"date": PREV_DATE, "type": "full"},
                {"date": NEW_DATE, "type": "incremental"},
            ],
            "incremental_count": incremental_count,
            "last_full_date": last_full,
            "next_disclosure_date": None,
            "compare_groups": [],
        })

    def triage(self, **kw) -> dict:
        return triage.run_triage(self.company_dir, self.run_dir, **kw)


# ---------------------------------------------------------------- 场景 A: 质地复用

class TestScenarioA(TriageEnv):
    def test_quality_clean_and_reused(self):
        """research/03 场景 A: 四条规则全未触发 → 质地复用, 其余全部重评。"""
        result = self.triage()
        self.assertFalse(result["quality"]["dirty"])
        for rule in result["quality"]["rules"]:
            self.assertIs(rule["triggered"], False, rule)
        self.assertEqual(result["reused_nodes"], ["quality"])
        self.assertEqual(result["rerun_nodes"], ["odds", "path", "state", "decision"])
        self.assertEqual(result["waves"], [["odds"], ["path", "state"], ["decision"]])

    def test_triage_json_written_and_valid(self):
        self.triage()
        data = json.loads((self.run_dir / triage.TRIAGE_NAME).read_text(encoding="utf-8"))
        self.assertEqual(verdict_block.validate(data, "triage"), [])

    def test_metric_deltas_have_pb_and_close(self):
        """PB 17.3→12.1 与收盘价 273→210 都超 ±10% 阈值, 形状 = 变化区块的 {name,before,after}。"""
        deltas = {d["name"]: d for d in self.triage()["metric_deltas"]}
        self.assertIn("PB", deltas)
        self.assertIn("收盘价", deltas)
        self.assertEqual(deltas["PB"]["before"], "17.30")
        self.assertEqual(deltas["PB"]["after"], "12.10")

    def test_small_change_excluded(self):
        """ROE 1.58→1.62(+2.5%)不到阈值, 不进 delta 清单。"""
        names = [d["name"] for d in self.triage()["metric_deltas"]]
        self.assertNotIn("ROE", names)

    def test_falsification_checklist_from_prev_path_block(self):
        """证伪清单原样带给④路径写手逐条核销(条件文本 = 上版 YAML 块)。"""
        result = self.triage()
        expected = [f["condition"] for f in fx.path_block()["falsifications"]]
        self.assertEqual([f["condition"] for f in result["falsification_checklist"]], expected)

    def test_critical_points_from_prev_state_block(self):
        result = self.triage()
        self.assertEqual(result["critical_points"], fx.state_block()["critical_point"]["items"])

    def test_new_interim_pdf_listed_but_not_annual(self):
        result = self.triage()
        self.assertEqual(result["new_pdfs"], ["h1_2026.pdf"])
        self.assertFalse(result["annual_disclosed"])

    def test_apply_reuse_stamps_quality(self):
        """复用戳: 拷上版 md + reused_from + 正文可见的 ♻️ 说明行, 且仍过 schema。"""
        self.triage(apply_reuse=True)
        dest = self.run_dir / "nodes" / "node-quality.md"
        data, errs = verdict_block.load_and_validate(dest, "node-quality")
        self.assertEqual(errs, [])
        self.assertEqual(data["reused_from"], PREV_DATE)
        text = dest.read_text(encoding="utf-8")
        self.assertIn("♻️ 本章判断复用", text)
        self.assertIn("部分好", text)                      # 上版正文保留

    def test_chained_reuse_keeps_original_date(self):
        """连续两次复用: reused_from 始终指向最后一次真实重评, 说明行不叠加。"""
        prev_nodes = fx.nodes()
        prev_nodes["quality"]["reused_from"] = "2026-05-01"
        write_nodes(self.company_dir / "runs" / PREV_DATE / "nodes", prev_nodes)
        self.triage(apply_reuse=True)
        dest = self.run_dir / "nodes" / "node-quality.md"
        data, _ = verdict_block.load_and_validate(dest, "node-quality")
        self.assertEqual(data["reused_from"], "2026-05-01")
        self.assertEqual(dest.read_text(encoding="utf-8").count("♻️"), 1)


# ---------------------------------------------------------------- 场景 B: 质地标脏

class TestScenarioB(TriageEnv):
    def test_segment_band_crossing_marks_quality_dirty(self):
        """research/03 场景 B: 光模块占比 3.6%→12% 跨 10% 档线 → 质地标脏, 五节点全重评。"""
        write_mainbz(self.company_dir / "raw_data" / "fina_mainbz.parquet", SEG_B)
        result = self.triage()
        rule = {r["rule"]: r for r in result["quality"]["rules"]}[triage.RULE_SEGMENT]
        self.assertTrue(rule["triggered"])
        self.assertIn("光模块", rule["evidence"])
        self.assertTrue(result["quality"]["dirty"])
        self.assertEqual(result["reused_nodes"], [])
        self.assertEqual(result["waves"], [["quality", "odds"], ["path", "state"], ["decision"]])

    def test_annual_pdf_marks_dirty(self):
        (self.company_dir / "raw_data" / "pdfs" / "annual_2026_full.pdf").write_bytes(b"%PDF stub")
        result = self.triage()
        rule = {r["rule"]: r for r in result["quality"]["rules"]}[triage.RULE_ANNUAL]
        self.assertTrue(rule["triggered"])
        self.assertTrue(result["annual_disclosed"])
        self.assertTrue(result["quality"]["dirty"])

    def test_new_quality_flag_marks_dirty(self):
        flags = fx.script_flags() + [{
            "id": "moat-order-confirmed", "level": "🟠",
            "title": "光模块订单坐实改变竞争格局", "evidence": "谷歌 200G EML 验证通过",
            "source": "script", "node": "quality", "metric_refs": ["segment"],
        }]
        self._json(self.company_dir / "red_flags.json", flags)
        result = self.triage()
        rule = {r["rule"]: r for r in result["quality"]["rules"]}[triage.RULE_FLAG]
        self.assertTrue(rule["triggered"])
        self.assertTrue(result["quality"]["dirty"])

    def test_new_path_flag_or_info_level_does_not_mark_dirty(self):
        """归家路径的新红旗、或 🟢/ℹ️ 级别, 都不构成质地重评理由。"""
        flags = fx.script_flags() + [
            {"id": "pledge-up", "level": "🟠", "title": "质押率上升", "evidence": "…",
             "source": "script", "node": "path", "metric_refs": []},
            {"id": "z-safe", "level": "🟢", "title": "Z 值安全", "evidence": "…",
             "source": "script", "node": "quality", "metric_refs": []},
        ]
        self._json(self.company_dir / "red_flags.json", flags)
        result = self.triage()
        rule = {r["rule"]: r for r in result["quality"]["rules"]}[triage.RULE_FLAG]
        self.assertIs(rule["triggered"], False)

    def test_sign_flip_marks_dirty(self):
        """经营现金流 −24 亿→+5.3 亿 变号 → 规则 (d) 触发(最硬证据「现金流为负」失效)。"""
        fresh = json.loads(json.dumps(FRESH_METRICS_A))
        fresh["cashflow"]["operating_cashflow_latest"] = 5.3e9
        self._json(self.company_dir / "metrics.json", fresh)
        result = self.triage()
        rule = {r["rule"]: r for r in result["quality"]["rules"]}[triage.RULE_SIGN]
        self.assertTrue(rule["triggered"])
        self.assertIn("经营现金流", rule["evidence"])
        self.assertTrue(result["quality"]["dirty"])

    def test_red_flag_diff_reports_resolved(self):
        """基线里有、刷新后消失的红旗 → resolved(变化区块同一口径)。"""
        flags = fx.script_flags()
        removed = flags.pop(0)
        self._json(self.company_dir / "red_flags.json", flags)
        result = self.triage()
        changes = {c["id"]: c["change"] for c in result["red_flag_diff"]}
        self.assertEqual(changes.get(removed["id"]), "resolved")


# ---------------------------------------------------------------- 拿不准一律标脏 / 两侧皆无不触发

class TestConservativeFallback(TriageEnv):
    def test_missing_one_side_metrics_marks_dirty(self):
        (self.bl / "metrics.json").unlink()
        result = self.triage()
        rule = {r["rule"]: r for r in result["quality"]["rules"]}[triage.RULE_SIGN]
        self.assertIsNone(rule["triggered"])
        self.assertTrue(result["quality"]["dirty"])
        self.assertEqual(result["metric_deltas"], [])     # 单侧缺失出不了 diff, 但不崩

    def test_missing_one_side_mainbz_marks_dirty(self):
        (self.bl / "fina_mainbz.parquet").unlink()
        result = self.triage()
        rule = {r["rule"]: r for r in result["quality"]["rules"]}[triage.RULE_SEGMENT]
        self.assertIsNone(rule["triggered"])
        self.assertTrue(result["quality"]["dirty"])

    def test_both_sides_missing_mainbz_is_no_signal(self):
        """港股/美股不产 fina_mainbz: 两侧皆无 = 无变化信号, 不因此永久标脏。"""
        (self.bl / "fina_mainbz.parquet").unlink()
        (self.company_dir / "raw_data" / "fina_mainbz.parquet").unlink()
        result = self.triage()
        rule = {r["rule"]: r for r in result["quality"]["rules"]}[triage.RULE_SEGMENT]
        self.assertIs(rule["triggered"], False)
        self.assertFalse(result["quality"]["dirty"])

    def test_missing_baseline_dir_raises(self):
        import shutil

        shutil.rmtree(self.bl)
        with self.assertRaises(triage.TriageInputError):
            self.triage()


# ---------------------------------------------------------------- 建议档(manifest 状态机)

class TestFullRerunAdvice(TriageEnv):
    def test_recent_full_not_advised(self):
        self.assertFalse(self.triage()["full_rerun_advice"]["advised"])

    def test_stale_full_advised(self):
        """距上次全量 >12 个月 → 建议全量重锚(照常产出本次增量)。"""
        self.write_manifest(last_full="2025-06-22")
        advice = self.triage()["full_rerun_advice"]
        self.assertTrue(advice["advised"])
        self.assertTrue(any(">12 个月" in r for r in advice["reasons"]))

    def test_four_increments_advised(self):
        self.write_manifest(incremental_count=4)
        advice = self.triage()["full_rerun_advice"]
        self.assertTrue(advice["advised"])
        self.assertTrue(any("≥4" in r for r in advice["reasons"]))


# ---------------------------------------------------------------- init_run: 硬规则1 + 基线快照

class TestInitRunIncremental(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.company_dir = Path(self.tmp.name) / "东山精密"
        write_nodes(self.company_dir / "runs" / PREV_DATE / "nodes", fx.nodes())
        manifest_mod.save(self.company_dir, {
            "company": "东山精密", "ticker": "002384.SZ", "market": "a",
            "runs": [{"date": PREV_DATE, "type": "full"}],
            "incremental_count": 0, "last_full_date": PREV_DATE,
            "next_disclosure_date": None, "compare_groups": [],
        })

    def test_valid_baseline_accepted(self):
        prev = init_run._validate_v8_baseline(self.company_dir)
        self.assertEqual(prev, {"date": PREV_DATE, "type": "full"})

    def test_hard_rule_1_no_manifest(self):
        """硬规则1: 无 manifest(v8 之前旧结构基线)→ 拒绝增量, 提示直接全量。"""
        (self.company_dir / manifest_mod.MANIFEST_NAME).unlink()
        with self.assertRaises(init_run.BaselineInvalid):
            init_run._validate_v8_baseline(self.company_dir)

    def test_hard_rule_1_broken_nodes(self):
        (self.company_dir / "runs" / PREV_DATE / "nodes" / "node-decision.md").unlink()
        with self.assertRaises(init_run.BaselineInvalid):
            init_run._validate_v8_baseline(self.company_dir)

    def test_snapshot_baseline_copies_evidence(self):
        (self.company_dir / "metrics.json").write_text(
            json.dumps(BASE_METRICS), encoding="utf-8"
        )
        (self.company_dir / "red_flags.json").write_text("[]", encoding="utf-8")
        pdfs = self.company_dir / "raw_data" / "pdfs"
        pdfs.mkdir(parents=True)
        (pdfs / "annual_2025_full.pdf").write_bytes(b"%PDF stub")
        run_dir = self.company_dir / "runs" / NEW_DATE
        run_dir.mkdir(parents=True)

        bl = init_run.snapshot_baseline(
            self.company_dir, run_dir, {"date": PREV_DATE, "type": "full"}
        )
        self.assertTrue((bl / "metrics.json").exists())
        self.assertTrue((bl / "red_flags.json").exists())
        meta = json.loads((bl / "baseline.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["prev_run_date"], PREV_DATE)
        pdfs_before = json.loads((bl / "pdfs_before.json").read_text(encoding="utf-8"))
        self.assertEqual(pdfs_before, ["annual_2025_full.pdf"])


# ---------------------------------------------------------------- 杂项口径

class TestHelpers(unittest.TestCase):
    def test_path_always_rerun(self):
        """spec §8: 路径每次对照新数据核销证伪/左尾清单 = 每次重跑。"""
        self.assertIn("path", node_graph.ALWAYS_RERUN)
        self.assertNotIn("quality", node_graph.ALWAYS_RERUN)

    def test_annual_pdf_detection(self):
        self.assertTrue(triage.is_annual_pdf("annual_2025_full.pdf"))
        self.assertTrue(triage.is_annual_pdf("2025年度报告.pdf"))
        self.assertFalse(triage.is_annual_pdf("semiannual_2026.pdf"))
        self.assertFalse(triage.is_annual_pdf("2026半年报.pdf"))
        self.assertFalse(triage.is_annual_pdf("q1_2026.pdf"))

    def test_flip_ignores_rationale_rewording(self):
        """research/03 场景 A 反例: 判定态度没变、只重写论据 → 不算翻转;首短语变了才算。"""
        before = {"verdict": "部分好——真卡位+平庸财务", "sub_verdicts": []}
        reworded = {"verdict": "部分好——真卡位已长成第二引擎,但现金裂口没合上", "sub_verdicts": []}
        flipped = {"verdict": "偏好——卡位坐实+财务仍平庸", "sub_verdicts": []}
        self.assertFalse(assembly._node_flipped(before, reworded))
        self.assertTrue(assembly._node_flipped(before, flipped))
        path_b = {"verdict": "高尾险·扛不住,高信仰 5/5", "sub_verdicts": []}
        path_a = {"verdict": "高尾险·不可承受(拥挤加深)", "sub_verdicts": []}
        self.assertFalse(assembly._node_flipped(path_b, path_a))

    def test_flip_ignores_free_text_sub_judgments(self):
        """自由文本子判定(状态/赔率/路径)重写措辞不算翻转;符号子判定(质地)变化才算。"""
        base = {"verdict": "买完完美未来", "sub_verdicts": [
            {"question": "价格分解 P=F+N", "judgment": "N 占市值 84%"}]}
        reworded = {"verdict": "买完完美未来", "sub_verdicts": [
            {"question": "价格分解 P=F+N", "judgment": "N 占市值 63.8%(上版 84.4%)"}]}
        self.assertFalse(assembly._node_flipped(base, reworded))
        q_base = {"verdict": "部分好——旧论据", "sub_verdicts": [
            {"question": "生意模式赚钱吗", "judgment": "✗"}]}
        q_new = {"verdict": "部分好——新论据", "sub_verdicts": [
            {"question": "生意模式赚钱吗", "judgment": "⚠️"}]}
        self.assertTrue(assembly._node_flipped(q_base, q_new))

    def test_segment_shares_drop_aggregate_row(self):
        """Tushare P 口径常有一行「产品」=全部之和(名字抓不住的合计行), 按数值剔除。

        东山真数据验收踩到: 不剔的话所有真分部占比被腰斩(合计行独占 50%)。
        """
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "mainbz.parquet"
            write_mainbz(p, [
                ("20260630", "产品", 100.0e8),          # 聚合行 = 下面三行之和
                ("20260630", "PCB", 60.0e8),
                ("20260630", "光模块", 30.0e8),
                ("20260630", "其他", 10.0e8),
            ])
            shares = triage.segment_shares(p)
        self.assertNotIn("产品", shares)
        self.assertAlmostEqual(shares["PCB"], 0.60, places=3)
        self.assertAlmostEqual(shares["光模块"], 0.30, places=3)

    def test_flag_list_accepts_wrapped_shape(self):
        """red_flags.py CLI 产物是 {"red_flags": [...]} 包壳, 裸列表与包壳都要认。"""
        flags = fx.script_flags()
        self.assertEqual(triage._flag_list({"red_flags": flags}), flags)
        self.assertEqual(triage._flag_list(flags), flags)
        self.assertIsNone(triage._flag_list(None))

    def test_read_json_tolerates_gbk(self):
        """Windows ANSI 控制台写出的 GBK JSON 也要能读(东山验收实测踩到)。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "metrics.json"
            p.write_bytes(json.dumps({"名字": "东山精密"}, ensure_ascii=False).encode("gbk"))
            self.assertEqual(triage._read_json(p), {"名字": "东山精密"})

    def test_segment_bands_match_research_03(self):
        """3.58%→7% 不跨档(场景 A)、3.58%→12% 跨档(场景 B)。"""
        self.assertEqual(
            triage.segment_band_crossings({"光模块": 0.0358}, {"光模块": 0.071}), []
        )
        crossings = triage.segment_band_crossings({"光模块": 0.0358}, {"光模块": 0.12})
        self.assertEqual(len(crossings), 1)


if __name__ == "__main__":
    unittest.main()
