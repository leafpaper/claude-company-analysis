"""单元测试: v8 契约层 — scripts/schemas/*.schema.json + verdict_block + manifest/runs 目录制.

实现票 01(.scratch/v8-implementation/issues/01)。合法 fixture 数据取自东山精密
铁律推演(research/02/05),非法 fixture 各缺/错一个关键字段。

运行:
    python -m pytest scripts/tests/test_contract_v8.py
    或  python -m unittest scripts.tests.test_contract_v8
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import manifest as manifest_mod
from scripts import verdict_block


# ---------------------------------------------------------------- fixtures

def legal_red_flag(**over) -> dict:
    d = {
        "id": "goodwill-vam-undisclosed",
        "level": "🟠",
        "title": "商誉对赌条款未披露",
        "evidence": "单季 +26.5 亿并购形成商誉 47.69 亿,并购公告无对赌披露",
        "source": "nomination",
        "node": "path",
        "metric_refs": ["goodwill"],
    }
    d.update(over)
    return d


def legal_indicator(**over) -> dict:
    d = {
        "name": "现金含量 OCF÷净利",
        "value": "负",
        "trend": "营收 +52.7% 而 OCF −17.5%,背离",
        "peer_percentile": None,
        "red_flag_ref": "cash-content",
        "note": None,
    }
    d.update(over)
    return d


def legal_quality() -> dict:
    sub = [
        ("生意模式赚钱吗", "✗", "集团毛利率 FY2025 14.09%、净利率 3.47%", "原维度2证据"),
        ("赚钱质量真吗", "✗", "ROE/净利率 peer 分位双 0% 垫底;FCF −24.01 亿", "原维度3+audit DuPont"),
        ("护城河存在吗", "⚠️", "200G EML IDM 窄而深,但光模块仅占营收 3.58%", "护城河框架"),
        ("管理层可信吗", "⚠️", "4 期业绩预告全部落入区间;袁永刚质押占其持股 34.6%", "管理层框架"),
        ("财务底子稳吗", "⚠️", "资产负债率 63.69% 为 18 期最高;Altman Z=8.767", "原维度7+audit"),
    ]
    return {
        "node": "quality",
        "verdict": "部分好——真卡位+平庸财务",
        "sub_verdicts": [
            {
                "question": q,
                "judgment": j,
                "hardest_evidence": [{"text": t, "mechanism": m}],
            }
            for q, j, t, m in sub
        ],
        "red_flag_nominations": [legal_red_flag()],
        "panel": {
            "industry_reason": "制造业并购扩张期,矛盾焦点在现金与回报质量,选默认五件套",
            "indicators": [
                legal_indicator(),
                legal_indicator(name="毛利率 / 净利率", value="14.09% / 3.47%", red_flag_ref=None),
                legal_indicator(name="FCF", value="−24.01 亿", red_flag_ref="cash-content"),
            ],
        },
    }


def legal_state() -> dict:
    return {
        "node": "state",
        "verdict": "↑变好但未确认(注意力先行、业绩待验证)",
        "sub_verdicts": [
            {
                "question": "λ 载体在放量吗",
                "judgment": "实锤但被稀释",
                "hardest_evidence": [
                    {"text": "索尔思毛利率 36.74% 全集团最高;高 λ 分部仅占营收 3.58%", "mechanism": "4.11 λ机制"}
                ],
            }
        ],
        "red_flag_nominations": [],
        "critical_point": {"items": ["2026 中报(光模块首个完整 H1 分部数据)", "谷歌 200G EML 验证结果(2026Q2 末)"]},
    }


def legal_odds() -> dict:
    return {
        "node": "odds",
        "verdict": "买完完美未来(无 slack)",
        "sub_verdicts": [
            {
                "question": "价格分解 P=F+N",
                "judgment": "N 占约 80%,obligation 非 option",
                "hardest_evidence": [{"text": "F≈1,000 亿,N≈4,000 亿,市值约 5,000 亿", "mechanism": "P=F+N"}],
            }
        ],
        "red_flag_nominations": [],
        "anchor_range": {
            "low": {"method": "SOTP", "value": 57, "unit": "元/股"},
            "high": {"method": "DCF", "value": 89, "unit": "元/股"},
            "same_direction": True,
            "divergence_note": "SOTP 只认已并表利润,DCF 允许 15% CAGR 温和放量,55% 分歧是信息",
        },
    }


def legal_path() -> dict:
    return {
        "node": "path",
        "verdict": "高尾险·扛不住(高信仰 5/5)",
        "sub_verdicts": [
            {
                "question": "左尾有多深",
                "judgment": "近资不抵债地板",
                "hardest_evidence": [{"text": "刨掉商誉清算净值约 −2~8 亿,最差 −98%", "mechanism": "6.4 左尾防护"}],
            }
        ],
        "red_flag_nominations": [],
        "falsifications": [
            {"condition": "H1 光模块营收 <40 亿或毛利率 <30%", "triggered": None},
            {"condition": "商誉任一减值", "triggered": None},
        ],
        "left_tail": [
            {"scenario": "商誉 47.69 亿减值 → 最差 5 元(−98%)"},
            {"scenario": "散户 2.8 倍暴增+两融拥挤 → 踩踏放大回撤至 −75%~−98%"},
        ],
    }


def legal_decision() -> dict:
    return {
        "node": "decision",
        "verdict": "先观察等证据,不追(期权小仓≤2-3%)",
        "triad": {"state": "↑未确认", "odds": "买完完美未来", "path": "高尾险"},
        "action_gear": "等证据临界",
        "action_detail": "先观察等证据临界;想赌右尾最多总资金 2-3% 期权小仓、设硬止损",
        "position": "现价 0 仓位持币;期权小仓 ≤2-3%",
        "three_part": {"good_company": "部分是(引用质地)", "good_bet": "否(三乘子两差一弱)", "good_price": "否(现价为锚区间高端 3 倍以上)"},
        "good_company_ref": "部分好——真卡位+平庸财务",
        "what_to_wait": ["2026 中报", "谷歌 200G EML 验证", "价格回调至约 160 元以内"],
        "falsification_exit": ["H1 光模块营收 <40 亿或毛利率 <30%", "商誉任一减值"],
        "gear_cap": {"triggered": False, "reason": None},
    }


def legal_assembly() -> dict:
    return {
        "verdict_card": [
            {"question": "是不是好公司", "verdict": "部分好——真卡位+平庸财务", "source_node": "quality"},
            {"question": "在变好吗", "verdict": "↑变好但未确认,注意力先行", "source_node": "state"},
            {"question": "贵不贵", "verdict": "买完完美未来;锚区间 57-89 元 vs 现价 273 元", "source_node": "odds"},
            {"question": "扛得住吗", "verdict": "高尾险·扛不住,高信仰 5/5", "source_node": "path"},
            {"question": "怎么办", "verdict": "先观察等证据临界,期权小仓 ≤2-3%", "source_node": "decision"},
        ],
        "panel": {
            "industry_reason": "制造业并购扩张期,选默认五件套",
            "conclusion": {"biz_model": "✗ 赚得薄", "quality_true": "✗ 赚得不真"},
            "indicators": [
                legal_indicator(),
                legal_indicator(name="毛利率 / 净利率", value="14.09% / 3.47%", red_flag_ref=None),
                legal_indicator(name="FCF", value="−24.01 亿"),
            ],
        },
        "top3": [
            {"rank": 1, "red_flag_id": "pb-percentile", "level": "🟠", "title": "估值透支", "evidence": "PB 22.09 近 1 年 100% 分位;PB/ROE 错配 25.7 倍"},
            {"rank": 2, "red_flag_id": "goodwill-vam-undisclosed", "level": "🟠", "title": "商誉 47.69 亿减值", "evidence": "对赌未披露,清算地板 −2~8 亿"},
            {"rank": 3, "red_flag_id": "retail-crowding", "level": "🟡", "title": "散户暴增+杠杆拥挤", "evidence": "8.17 万→30.60 万户,两融高于 60 日中位 33.4%"},
        ],
        "metadata": {
            "company": "东山精密",
            "date": "2026-06-22",
            "action_gear": "等证据临界",
            "verdict_plain": "先观察等证据,不追(期权小仓≤2-3%)",
            "quality_field": "部分好",
        },
    }


def legal_change_block() -> dict:
    return {
        "alpha_summary": "阿尔法变了:中报证伪线触发,放量故事走弱——观察下调为回避",
        "gear_before": "等证据临界",
        "gear_after": "回避",
        "triad_before": {"state": "↑未确认", "odds": "买完完美未来", "path": "高尾险"},
        "triad_after": {"state": "λ走弱", "odds": "买完完美未来", "path": "高尾险"},
        "flipped_nodes": ["state"],
        "red_flag_changes": [],
        "falsification_changes": [{"condition": "H1 光模块营收 <40 亿", "change": "triggered"}],
        "metric_deltas": [{"name": "股价", "before": "273 元", "after": "210 元"}],
        "full_rerun_advice": {"advised": False, "reason": None},
    }


def legal_manifest() -> dict:
    return {
        "company": "东山精密",
        "ticker": "002384.SZ",
        "market": "A股",
        "runs": [{"date": "2026-06-22", "type": "full"}],
        "incremental_count": 0,
        "last_full_date": "2026-06-22",
        "next_disclosure_date": "2026-08-30",
        "compare_groups": [],
    }


# ---------------------------------------------------------------- schema 校验

class TestNodeSchemas(unittest.TestCase):
    """每个节点 schema: 合法 fixture 零错误, 非法 fixture 报错并指向字段."""

    def test_quality_legal(self):
        self.assertEqual(verdict_block.validate(legal_quality(), "node-quality"), [])

    def test_quality_missing_verdict(self):
        bad = legal_quality()
        del bad["verdict"]
        errs = verdict_block.validate(bad, "node-quality")
        self.assertTrue(errs and any("verdict" in e for e in errs))

    def test_quality_needs_five_sub_verdicts(self):
        bad = legal_quality()
        bad["sub_verdicts"] = bad["sub_verdicts"][:3]
        self.assertTrue(verdict_block.validate(bad, "node-quality"))

    def test_quality_bad_judgment_enum(self):
        bad = legal_quality()
        bad["sub_verdicts"][0]["judgment"] = "还行"
        self.assertTrue(verdict_block.validate(bad, "node-quality"))

    def test_quality_five_questions_are_named(self):
        """五个子判定问题名是 spec 锁定的(§1),换名/缺名都不合法。"""
        bad = legal_quality()
        bad["sub_verdicts"][2]["question"] = "有护城河吗"  # 改名顶替「护城河存在吗」
        self.assertTrue(verdict_block.validate(bad, "node-quality"))

    def test_panel_indicator_all_keys_required(self):
        """面板指标块六键齐备(可空≠可缺), 装配零分支。"""
        bad = legal_quality()
        del bad["panel"]["indicators"][0]["note"]
        self.assertTrue(verdict_block.validate(bad, "node-quality"))

    def test_quality_panel_indicator_bounds(self):
        bad = legal_quality()
        bad["panel"]["indicators"] = bad["panel"]["indicators"][:2]  # <3 个
        self.assertTrue(verdict_block.validate(bad, "node-quality"))

    def test_quality_evidence_max_two(self):
        bad = legal_quality()
        ev = {"text": "x", "mechanism": "y"}
        bad["sub_verdicts"][0]["hardest_evidence"] = [ev, ev, dict(ev)]
        self.assertTrue(verdict_block.validate(bad, "node-quality"))

    def test_state_legal(self):
        self.assertEqual(verdict_block.validate(legal_state(), "node-state"), [])

    def test_state_missing_critical_point(self):
        bad = legal_state()
        del bad["critical_point"]
        errs = verdict_block.validate(bad, "node-state")
        self.assertTrue(errs and any("critical_point" in e for e in errs))

    def test_odds_legal(self):
        self.assertEqual(verdict_block.validate(legal_odds(), "node-odds"), [])

    def test_odds_missing_same_direction(self):
        bad = legal_odds()
        del bad["anchor_range"]["same_direction"]
        errs = verdict_block.validate(bad, "node-odds")
        self.assertTrue(errs and any("same_direction" in e for e in errs))

    def test_odds_divergent_requires_note(self):
        bad = legal_odds()
        bad["anchor_range"]["same_direction"] = False
        del bad["anchor_range"]["divergence_note"]
        self.assertTrue(verdict_block.validate(bad, "node-odds"))
        # 补上说明后合法(不同向→标「取决于口径」)
        bad["anchor_range"]["divergence_note"] = "两端不同向,取决于口径,档位保守一档"
        self.assertEqual(verdict_block.validate(bad, "node-odds"), [])

    def test_path_legal(self):
        self.assertEqual(verdict_block.validate(legal_path(), "node-path"), [])

    def test_path_missing_falsifications(self):
        bad = legal_path()
        del bad["falsifications"]
        self.assertTrue(verdict_block.validate(bad, "node-path"))

    def test_decision_legal(self):
        self.assertEqual(verdict_block.validate(legal_decision(), "node-decision"), [])

    def test_decision_bad_gear(self):
        bad = legal_decision()
        bad["action_gear"] = "梭哈"
        errs = verdict_block.validate(bad, "node-decision")
        self.assertTrue(errs and any("action_gear" in e for e in errs))

    def test_decision_gear_cap_required(self):
        bad = legal_decision()
        del bad["gear_cap"]
        self.assertTrue(verdict_block.validate(bad, "node-decision"))

    def test_wrong_node_name_rejected(self):
        bad = legal_quality()
        bad["node"] = "state"
        self.assertTrue(verdict_block.validate(bad, "node-quality"))

    def test_reused_stamp_allowed(self):
        ok = legal_quality()
        ok["reused_from"] = "2026-06-22"  # 增量复查「复用」盖戳(票 09 用)
        self.assertEqual(verdict_block.validate(ok, "node-quality"), [])

    def test_red_flag_bad_level(self):
        bad = legal_quality()
        bad["red_flag_nominations"] = [legal_red_flag(level="🔥")]
        self.assertTrue(verdict_block.validate(bad, "node-quality"))

    def test_red_flag_bad_source(self):
        bad = legal_quality()
        bad["red_flag_nominations"] = [legal_red_flag(source="manual")]
        self.assertTrue(verdict_block.validate(bad, "node-quality"))


class TestAssemblySchema(unittest.TestCase):
    def test_assembly_legal(self):
        self.assertEqual(verdict_block.validate(legal_assembly(), "assembly"), [])

    def test_assembly_with_change_block(self):
        ok = legal_assembly()
        ok["change_block"] = legal_change_block()
        self.assertEqual(verdict_block.validate(ok, "assembly"), [])

    def test_verdict_card_must_have_five_rows(self):
        bad = legal_assembly()
        bad["verdict_card"] = bad["verdict_card"][:4]
        self.assertTrue(verdict_block.validate(bad, "assembly"))

    def test_top3_max_three(self):
        bad = legal_assembly()
        bad["top3"] = bad["top3"] + [dict(bad["top3"][0], rank=4)]
        self.assertTrue(verdict_block.validate(bad, "assembly"))

    def test_change_block_requires_alpha_summary(self):
        bad = legal_assembly()
        cb = legal_change_block()
        del cb["alpha_summary"]
        bad["change_block"] = cb
        errs = verdict_block.validate(bad, "assembly")
        self.assertTrue(errs and any("alpha_summary" in e for e in errs))

    def test_change_block_lists_may_be_empty_but_not_absent(self):
        """红旗/证伪/指标 delta 三张清单必须显式存在(空列表=明示「无变化」)。"""
        bad = legal_assembly()
        cb = legal_change_block()
        del cb["metric_deltas"]
        bad["change_block"] = cb
        errs = verdict_block.validate(bad, "assembly")
        self.assertTrue(errs and any("metric_deltas" in e for e in errs))


class TestManifestSchema(unittest.TestCase):
    def test_manifest_legal(self):
        self.assertEqual(verdict_block.validate(legal_manifest(), "manifest"), [])

    def test_manifest_bad_run_type(self):
        bad = legal_manifest()
        bad["runs"][0]["type"] = "weekly"
        self.assertTrue(verdict_block.validate(bad, "manifest"))

    def test_manifest_bad_date(self):
        bad = legal_manifest()
        bad["runs"][0]["date"] = "26/06/22"
        self.assertTrue(verdict_block.validate(bad, "manifest"))

    def test_manifest_disclosure_date_key_required(self):
        """下次预约披露日可为 null 但键必须在(被动提醒的数据源)。"""
        bad = legal_manifest()
        del bad["next_disclosure_date"]
        errs = verdict_block.validate(bad, "manifest")
        self.assertTrue(errs and any("next_disclosure_date" in e for e in errs))


# ---------------------------------------------------------------- YAML 块抽取

MD_WITH_BLOCK = """```yaml
node: state
verdict: ↑变好但未确认
```

## ② 状态——在变好吗

**判定**:↑变好但未确认。
"""

MD_WITHOUT_BLOCK = "## ② 状态\n\n没有 YAML 块的正文。\n"

MD_BLOCK_NOT_FIRST = "开头有一段正文。\n\n```yaml\nnode: state\n```\n"


class TestExtractYamlBlock(unittest.TestCase):
    def test_extracts_top_block(self):
        data = verdict_block.extract_yaml_block(MD_WITH_BLOCK)
        self.assertEqual(data["node"], "state")
        self.assertEqual(data["verdict"], "↑变好但未确认")

    def test_missing_block_raises(self):
        with self.assertRaises(verdict_block.BlockNotFound):
            verdict_block.extract_yaml_block(MD_WITHOUT_BLOCK)

    def test_block_must_be_at_top(self):
        """装配与增量对比只读顶部块——正文中部的块不算(单一数据源纪律)。"""
        with self.assertRaises(verdict_block.BlockNotFound):
            verdict_block.extract_yaml_block(MD_BLOCK_NOT_FIRST)

    def test_load_node_file_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "node-state.md"
            import yaml  # noqa: PLC0415

            block = yaml.safe_dump(legal_state(), allow_unicode=True, sort_keys=False)
            p.write_text(f"```yaml\n{block}```\n\n## ② 状态\n正文。\n", encoding="utf-8")
            data, errs = verdict_block.load_and_validate(p, "node-state")
            self.assertEqual(errs, [])
            self.assertEqual(data["node"], "state")


# ---------------------------------------------------------------- runs 目录制 + manifest

class TestRunsAndManifest(unittest.TestCase):
    def _tmp_company(self, td: str) -> Path:
        return Path(td) / "东山精密"

    def test_create_full_run_layout(self):
        with tempfile.TemporaryDirectory() as td:
            base = self._tmp_company(td)
            run_dir = manifest_mod.create_run(base, "full", date="2026-06-22", ticker="002384.SZ")
            self.assertEqual(run_dir, base / "runs" / "2026-06-22")
            for sub in ("raw_data/pdfs", "nodes", "assembly", "reviewer_responses"):
                self.assertTrue((run_dir / sub).is_dir(), f"缺子目录 {sub}")
            m = manifest_mod.load(base)
            self.assertEqual(verdict_block.validate(m, "manifest"), [])
            self.assertEqual(m["runs"], [{"date": "2026-06-22", "type": "full"}])
            self.assertEqual(m["last_full_date"], "2026-06-22")
            self.assertEqual(m["incremental_count"], 0)

    def test_incremental_increments_then_full_resets(self):
        with tempfile.TemporaryDirectory() as td:
            base = self._tmp_company(td)
            manifest_mod.create_run(base, "full", date="2026-06-22")
            manifest_mod.create_run(base, "incremental", date="2026-08-20")
            m = manifest_mod.load(base)
            self.assertEqual(m["incremental_count"], 1)
            self.assertEqual(m["last_full_date"], "2026-06-22")
            manifest_mod.create_run(base, "incremental", date="2026-10-30")
            self.assertEqual(manifest_mod.load(base)["incremental_count"], 2)
            manifest_mod.create_run(base, "full", date="2027-04-30")
            m = manifest_mod.load(base)
            self.assertEqual(m["incremental_count"], 0)
            self.assertEqual(m["last_full_date"], "2027-04-30")
            self.assertEqual(len(m["runs"]), 4)
            self.assertEqual(verdict_block.validate(m, "manifest"), [])

    def test_old_runs_left_intact(self):
        """旧 run 目录整目录留档: 新建 run 不触碰旧目录内容。"""
        with tempfile.TemporaryDirectory() as td:
            base = self._tmp_company(td)
            run1 = manifest_mod.create_run(base, "full", date="2026-06-22")
            marker = run1 / "nodes" / "node-quality.md"
            marker.write_text("旧版内容", encoding="utf-8")
            manifest_mod.create_run(base, "incremental", date="2026-08-20")
            self.assertEqual(marker.read_text(encoding="utf-8"), "旧版内容")

    def test_duplicate_date_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            base = self._tmp_company(td)
            manifest_mod.create_run(base, "full", date="2026-06-22")
            with self.assertRaises(manifest_mod.RunExists):
                manifest_mod.create_run(base, "full", date="2026-06-22")

    def test_latest_run(self):
        with tempfile.TemporaryDirectory() as td:
            base = self._tmp_company(td)
            self.assertIsNone(manifest_mod.latest_run(base))
            manifest_mod.create_run(base, "full", date="2026-06-22")
            manifest_mod.create_run(base, "incremental", date="2026-08-20")
            latest = manifest_mod.latest_run(base)
            self.assertEqual(latest, {"date": "2026-08-20", "type": "incremental"})


class TestSchemaFilesExist(unittest.TestCase):
    def test_all_contract_schemas_present(self):
        names = {p.name for p in verdict_block.SCHEMA_DIR.glob("*.schema.json")}
        expected = {
            "common.schema.json",
            "node-quality.schema.json",
            "node-state.schema.json",
            "node-odds.schema.json",
            "node-path.schema.json",
            "node-decision.schema.json",
            "assembly.schema.json",
            "manifest.schema.json",
        }
        self.assertTrue(expected.issubset(names), f"缺 schema 文件: {expected - names}")

    def test_schema_files_are_valid_json(self):
        for p in verdict_block.SCHEMA_DIR.glob("*.schema.json"):
            with self.subTest(schema=p.name):
                json.loads(p.read_text(encoding="utf-8"))


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (
        TestNodeSchemas,
        TestAssemblySchema,
        TestManifestSchema,
        TestExtractYamlBlock,
        TestRunsAndManifest,
        TestSchemaFilesExist,
    ):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
