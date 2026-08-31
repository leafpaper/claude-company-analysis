"""单元测试: v8 产业链同行对比 `--compare`(scripts/compare.py + build_html 对比通道)。

实现票 10(.scratch/v8-implementation/issues/10-compare-page.md)。
测试缝同全链唯一那条 = **run 目录契约**: 成员的 runs/{date}/(nodes YAML 块 + assembly.json)
与 manifest 进, compare.json / md 底稿 / 对比页 HTML 出。

行为基线(票 10 的五条验收):
  · 上半并排卡片**全部取自各家 YAML 块与装配产物, 零新判断**;基准日标注, 超 90 天标「陈旧」;
  · 组内裁决过 schema + 四条机检(具名成员 / 排名连号 / 全组覆盖 / 数字回得了源);
  · 缺报告成员成组时列出并给补跑命令, 补跑后重装配即并入;
  · --review 收尾联动: manifest 对比组字段读写 + status 判「要不要重装配」;
  · 每家可点回自己的单报告(站点相对链接与 update_index 的 slug 同一套)。

语料: 东山精密 golden fixture(真实推演稿)+ 一家**合成**同行「测试同行A」(在 fixture 上改判定,
不是任何真公司)。真实的第二家(中际旭创)在库里还没有 v8 报告 —— 它正好是「缺报告成员」那条路径的用例。

运行:
    python -m unittest scripts.tests.test_compare_v8
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts import assembly, build_html, compare, config, update_index, verdict_block
from scripts import manifest as manifest_mod
from scripts.tests import dongshan_fixture as fx

ANCHOR = "东山精密"
ANCHOR_TICKER = "002384.SZ"
PEER = "测试同行A"                      # 合成同行, 不是真公司
PEER_TICKER = "999999.SZ"
ABSENT = "中际旭创"                     # 真实的产业链同行, 库里还没有 v8 报告
ABSENT_TICKER = "300308.SZ"
SLUG = "pcb-optics"
TODAY = "2026-08-25"
ANCHOR_DATE = "2026-08-24"


def write_nodes(nodes_dir: Path, nodes: dict) -> None:
    nodes_dir.mkdir(parents=True, exist_ok=True)
    for node, block in nodes.items():
        text = yaml.safe_dump(block, allow_unicode=True, sort_keys=False)
        (nodes_dir / f"node-{node}.md").write_text(
            f"```yaml\n{text}```\n\n{fx.NODE_BODIES[node]}", encoding="utf-8"
        )


def read_odds_block(path: Path) -> dict:
    return verdict_block.extract_yaml_block(path.read_text(encoding="utf-8"))


def write_odds_block(path: Path, block: dict) -> None:
    text = yaml.safe_dump(block, allow_unicode=True, sort_keys=False)
    path.write_text(f"```yaml\n{text}```\n\n{fx.NODE_BODIES['odds']}", encoding="utf-8")


def peer_nodes() -> dict:
    """合成同行 = 在 golden 块上改判定(更好的质地、更便宜的锚、更进攻的档位)。"""
    nodes = copy.deepcopy(fx.nodes())
    nodes["quality"]["verdict"] = "好——现金流真、卡位稳"
    nodes["state"]["verdict"] = "↑变好且已确认,订单落地"
    nodes["odds"]["verdict"] = "价格还算合理"
    nodes["odds"]["anchor_range"]["low"]["value"] = 120
    nodes["odds"]["anchor_range"]["high"]["value"] = 180
    nodes["odds"]["current_price"] = {"value": 150, "unit": "元"}
    nodes["path"]["verdict"] = "扛得住,左尾可控"
    nodes["decision"]["verdict"] = "可以买,核心仓 5-8%"
    nodes["decision"]["action_gear"] = "核心仓"
    return nodes


class CompareEnv(unittest.TestCase):
    """搭一个隔离的 output 根: 锚 + 一家合成同行有完整报告, 第三家只在名单上。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = self.root / "output"
        self.output.mkdir()

        # config 的三处解析入口全部指到临时根(产出侧与消费侧必须问同一个人)
        for attr, value in (
            ("PLUGIN_ROOT", self.root), ("SKILL_ROOT", self.root), ("OUTPUT_ROOT", self.output)
        ):
            original = getattr(config, attr)
            setattr(config, attr, value)
            self.addCleanup(setattr, config, attr, original)

        self.make_member(ANCHOR, ANCHOR_TICKER, ANCHOR_DATE, fx.nodes(), run_type="incremental")
        self.make_member(PEER, PEER_TICKER, "2026-08-20", peer_nodes())

    # ---------- 造数据 ----------

    def make_member(self, company, ticker, date, nodes, run_type="full", next_disclosure=None):
        company_dir = self.output / company
        run_dir = company_dir / "runs" / date
        write_nodes(run_dir / "nodes", nodes)
        product = assembly.build_assembly(
            company, date, nodes, fx.script_flags(), next_disclosure_date=next_disclosure
        )
        (run_dir / "assembly").mkdir(parents=True, exist_ok=True)
        (run_dir / "assembly" / "assembly.json").write_text(
            json.dumps(product, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (run_dir / f"{company}-analysis-{date}.md").write_text(
            f"# {company} 投资分析报告 {date}\n", encoding="utf-8"
        )
        # 已有 manifest 就追加一次 run(同 manifest.create_run 的行为)——
        # 覆盖式重写会把 compare_groups 抹掉, 那是测试道具的 bug, 不是产品行为
        m = manifest_mod.load(company_dir) or {
            "company": company, "ticker": ticker, "market": "a", "runs": [],
            "incremental_count": 0, "last_full_date": None,
            "next_disclosure_date": next_disclosure, "compare_groups": [],
        }
        m["runs"].append({"date": date, "type": run_type})
        if run_type == "full":
            m["last_full_date"] = date
            m["incremental_count"] = 0
        else:
            m["incremental_count"] += 1
        manifest_mod.save(company_dir, m)
        return company_dir, product

    def make_group(self, members=None, **kw):
        members = members if members is not None else [
            {"company": PEER, "ticker": PEER_TICKER, "source": "longbridge"},
            {"company": ABSENT, "ticker": ABSENT_TICKER, "source": "longbridge"},
        ]
        return compare.create_group(
            anchor=ANCHOR, anchor_ticker=ANCHOR_TICKER, members=members,
            slug=kw.pop("slug", SLUG), name=kw.pop("name", "PCB↔光模块产业链"),
            created=kw.pop("created", TODAY), **kw
        )

    def write_judge(self, block: dict, slug: str = SLUG):
        gdir = compare.group_dir(slug)
        gdir.mkdir(parents=True, exist_ok=True)
        text = yaml.safe_dump(block, allow_unicode=True, sort_keys=False)
        (gdir / compare.JUDGE_NAME).write_text(
            f"```yaml\n{text}```\n\n## 组内裁决\n\n正文随便写, 装配只读顶部块。\n", encoding="utf-8"
        )

    def good_judge(self) -> dict:
        return {
            "node": "compare-judge",
            "group": SLUG,
            "verdict": f"钱先放 {PEER}: 同一条链上它的判定更硬、锚离现价更近",
            "ranking": [
                {"rank": 1, "company": PEER, "one_liner": "质地判定「好」且档位到核心仓,现价 150 落在锚区间内",
                 "basis": ["quality", "odds", "decision"]},
                {"rank": 2, "company": ANCHOR, "one_liner": "卡位是真的,但现价 273 已把完美未来付清",
                 "basis": ["odds", "path"]},
            ],
            "common_risk": "同一条产业链,光模块需求证伪时两家一起挨打",
            "not_comparable": ["两家锚区间用的方法不同,区间宽度不可直接相减"],
        }


# ================================================================ 成组

class TestGrouping(CompareEnv):

    def test_create_group_writes_contract_and_registers_manifest(self):
        group = self.make_group()
        self.assertEqual(group["slug"], SLUG)
        self.assertEqual(group["members"][0]["company"], ANCHOR)      # 锚自动进名单且排头
        self.assertEqual(group["members"][0]["source"], "anchor")
        # 组定义过 schema(load_group 内含校验)
        self.assertEqual(compare.load_group(SLUG)["anchor"], ANCHOR)
        # 成员归属写进各自 manifest —— --review 收尾靠这个字段知道要不要提示
        for company in (ANCHOR, PEER, ABSENT):
            m = manifest_mod.load(self.output / company)
            if m:                                        # 缺报告成员没有 manifest, 不建空壳
                self.assertIn(SLUG, m["compare_groups"])
        self.assertIsNone(manifest_mod.load(self.output / ABSENT))
        self.assertEqual(compare.groups_of(ANCHOR), [SLUG])

    def test_default_slug_falls_back_to_ticker_peers(self):
        group = self.make_group(slug=None)
        self.assertEqual(group["slug"], "002384-peers")

    def test_source_priority_is_recorded_per_member(self):
        group = self.make_group(members=[
            {"company": PEER, "ticker": PEER_TICKER, "source": "longbridge"},
            {"company": ABSENT, "ticker": ABSENT_TICKER, "source": "library", "note": "库内 peer 对标"},
        ])
        sources = {m["company"]: m["source"] for m in group["members"]}
        self.assertEqual(sources, {ANCHOR: "anchor", PEER: "longbridge", ABSENT: "library"})

    def test_anchor_must_be_in_members(self):
        with self.assertRaises(compare.CompareError):
            compare.save_group({
                "slug": "x", "name": "x", "anchor": "不在名单里的公司", "created": TODAY,
                "members": [{"company": PEER, "ticker": PEER_TICKER, "source": "model"},
                            {"company": ANCHOR, "ticker": ANCHOR_TICKER, "source": "model"}],
            })

    def test_parse_member_spec(self):
        self.assertEqual(
            compare.parse_member("中际旭创:300308.SZ:longbridge:成分股同链"),
            {"company": "中际旭创", "ticker": "300308.SZ", "source": "longbridge", "note": "成分股同链"},
        )
        with self.assertRaises(compare.CompareError):
            compare.parse_member("只有公司名")
        with self.assertRaises(compare.CompareError):
            compare.parse_member("公司:代码:胡说的来源")

    def test_library_candidates_reports_readiness(self):
        by_name = {c["company"]: c for c in compare.library_candidates(ANCHOR)}
        self.assertIn(PEER, by_name)
        self.assertTrue(by_name[PEER]["report_ready"])
        self.assertNotIn(ANCHOR, by_name)                 # 锚不进自己的候选


# ================================================================ 上半:并排装配

class TestAssembleSideBySide(CompareEnv):

    def test_cells_are_copied_from_member_products_zero_new_judgment(self):
        self.make_group()
        product = compare.assemble(SLUG, today=TODAY)

        by_name = {m["company"]: m for m in product["members"]}
        for company in (ANCHOR, PEER):
            source = json.loads(
                (self.output / company / "runs" / by_name[company]["report_date"]
                 / "assembly" / "assembly.json").read_text(encoding="utf-8")
            )
            self.assertEqual(by_name[company]["verdict_card"], source["verdict_card"])
            self.assertEqual(by_name[company]["top3"], source["top3"])
            self.assertEqual(by_name[company]["action_gear"], source["metadata"]["action_gear"])
            self.assertEqual(by_name[company]["quality_field"], source["metadata"]["quality_field"])

    def test_anchor_range_comes_from_odds_yaml_block(self):
        self.make_group()
        product = compare.assemble(SLUG, today=TODAY)
        anchor_member = next(m for m in product["members"] if m["company"] == ANCHOR)
        block = fx.odds_block()["anchor_range"]
        self.assertEqual(anchor_member["anchor_range"]["low"]["value"], block["low"]["value"])
        self.assertEqual(anchor_member["anchor_range"]["high"]["value"], block["high"]["value"])
        self.assertIn("57-89", compare.anchor_text(anchor_member))
        self.assertIn("现价 273", compare.anchor_text(anchor_member))

    def test_anchor_company_sorts_first(self):
        self.make_group()
        product = compare.assemble(SLUG, today=TODAY)
        self.assertEqual(product["members"][0]["company"], ANCHOR)
        self.assertTrue(product["members"][0]["is_anchor"])

    def test_report_href_matches_site_slug(self):
        self.make_group()
        product = compare.assemble(SLUG, today=TODAY)
        anchor_member = next(m for m in product["members"] if m["company"] == ANCHOR)
        self.assertEqual(
            anchor_member["report_href"], f"../../reports/002384_{ANCHOR}/分析报告_dashboard.html"
        )

    def test_baseline_date_and_staleness(self):
        self.make_group()
        fresh = compare.assemble(SLUG, today=TODAY)
        anchor_member = next(m for m in fresh["members"] if m["company"] == ANCHOR)
        self.assertEqual(anchor_member["age_days"], 1)
        self.assertFalse(anchor_member["stale"])
        self.assertFalse(any("陈旧" in n for n in fresh["notes"]))

        # 同一批报告, 100 天后再看 —— 超 90 天档线, 标陈旧并提示先复查
        aged = compare.assemble(SLUG, today="2026-12-02")
        anchor_member = next(m for m in aged["members"] if m["company"] == ANCHOR)
        self.assertTrue(anchor_member["stale"])
        note = next(n for n in aged["notes"] if "陈旧" in n)
        self.assertIn("--review", note)
        self.assertIn("⚠️陈旧", compare.date_text(anchor_member))

    def test_stale_threshold_is_recorded_and_configurable(self):
        self.make_group()
        product = compare.assemble(SLUG, today=TODAY, stale_days=1)
        self.assertEqual(product["stale_threshold_days"], 1)
        # 锚 1 天前(不超)、同行 5 天前(超)—— 档线是可调的, 但产物里必须记着用的是哪条
        by_name = {m["company"]: m["stale"] for m in product["members"]}
        self.assertFalse(by_name[ANCHOR])
        self.assertTrue(by_name[PEER])

    def test_needs_two_members_with_reports(self):
        self.make_group(members=[{"company": ABSENT, "ticker": ABSENT_TICKER, "source": "longbridge"}])
        with self.assertRaises(compare.CompareError) as ctx:
            compare.assemble(SLUG, today=TODAY)
        self.assertIn("至少要 2 家", str(ctx.exception))


# ================================================================ 缺报告成员(全报告制)

class TestMissingMembers(CompareEnv):

    def test_missing_member_listed_with_rerun_command(self):
        self.make_group()
        product = compare.assemble(SLUG, today=TODAY)
        self.assertEqual([m["company"] for m in product["missing_members"]], [ABSENT])
        missing = product["missing_members"][0]
        self.assertIn(ABSENT, missing["command"])
        self.assertIn(ABSENT_TICKER, missing["command"])
        self.assertEqual(missing["source"], "longbridge")
        self.assertTrue(any("缺完整报告" in n for n in product["notes"]))
        # 缺报告的不许混进上半
        self.assertNotIn(ABSENT, [m["company"] for m in product["members"]])

    def test_half_finished_run_counts_as_missing(self):
        """跑了一半的 run(有 manifest 有目录, 没装配产物)= 缺报告, 不拿半成品凑数。"""
        company_dir = self.output / ABSENT
        (company_dir / "runs" / "2026-08-01" / "nodes").mkdir(parents=True)
        manifest_mod.save(company_dir, {
            "company": ABSENT, "ticker": ABSENT_TICKER, "market": "a",
            "runs": [{"date": "2026-08-01", "type": "full"}], "incremental_count": 0,
            "last_full_date": "2026-08-01", "next_disclosure_date": None, "compare_groups": [],
        })
        self.make_group()
        product = compare.assemble(SLUG, today=TODAY)
        reason = product["missing_members"][0]["reason"]
        self.assertIn("assembly", reason)

    def test_batch_backfill_then_reassemble_absorbs_member(self):
        self.make_group()
        first = compare.assemble(SLUG, today=TODAY)
        self.assertEqual(len(first["members"]), 2)

        # 用户按提示分批补跑了缺的那家
        self.make_member(ABSENT, ABSENT_TICKER, "2026-08-25", peer_nodes())
        second = compare.assemble(SLUG, today=TODAY)
        self.assertEqual(len(second["members"]), 3)
        self.assertEqual(second["missing_members"], [])
        self.assertIn(ABSENT, [m["company"] for m in second["members"]])


# ================================================================ 下半:组内裁决

class TestJudge(CompareEnv):

    def setUp(self):
        super().setUp()
        self.make_group()

    def members(self):
        return compare.assemble(SLUG, today=TODAY)["members"]

    def test_good_judge_passes_and_lands_in_product(self):
        self.write_judge(self.good_judge())
        product = compare.assemble(SLUG, today=TODAY)
        self.assertEqual(product["judge"]["ranking"][0]["company"], PEER)
        self.assertFalse(any("裁决尚未产出" in n for n in product["notes"]))

    def test_missing_judge_is_noted_not_fatal(self):
        product = compare.assemble(SLUG, today=TODAY)
        self.assertNotIn("judge", product)
        self.assertTrue(any("裁决尚未产出" in n for n in product["notes"]))

    def test_require_judge_blocks_publish(self):
        with self.assertRaises(compare.CompareError):
            compare.assemble(SLUG, today=TODAY, require_judge=True)

    def test_schema_violation_rejected(self):
        bad = self.good_judge()
        del bad["ranking"][0]["basis"]
        self.write_judge(bad)
        with self.assertRaises(compare.CompareError) as ctx:
            compare.assemble(SLUG, today=TODAY)
        self.assertIn("schema", str(ctx.exception))

    def test_group_mismatch_rejected(self):
        bad = self.good_judge()
        bad["group"] = "别的组"
        self.write_judge(bad)
        with self.assertRaises(compare.CompareError):
            compare.assemble(SLUG, today=TODAY)

    def test_ranking_must_cover_every_member_with_a_report(self):
        judge = self.good_judge()
        judge["ranking"] = judge["ranking"][:1] + [
            {"rank": 2, "company": "别家公司", "one_liner": "凑数", "basis": ["quality"]}
        ]
        problems = compare.check_judge(judge, self.members())
        self.assertTrue(any("不是本组有报告的成员" in p for p in problems))
        self.assertTrue(any("漏了成员" in p for p in problems))

    def test_ranks_must_be_contiguous(self):
        judge = self.good_judge()
        judge["ranking"][1]["rank"] = 3
        problems = compare.check_judge(judge, self.members())
        self.assertTrue(any("连号" in p for p in problems))

    def test_judge_may_not_invent_numbers(self):
        judge = self.good_judge()
        judge["ranking"][1]["one_liner"] = "毛利率只有 12.7%,不如同行"
        problems = compare.check_judge(judge, self.members())
        self.assertTrue(any("找不到出处" in p and "12.7" in p for p in problems))

    def test_numbers_quoted_from_any_member_card_are_fine(self):
        judge = self.good_judge()
        # 273 来自锚的现价、150 来自同行的现价 —— 跨成员引用也算回得了源
        judge["verdict"] = f"{PEER} 现价 150 在锚区间内,{ANCHOR} 现价 273 在区间外"
        self.assertEqual(compare.check_judge(judge, self.members()), [])

    def test_single_digit_prose_is_not_treated_as_evidence(self):
        judge = self.good_judge()
        judge["verdict"] = "两家里先放 1 家就够,另 1 家等证据"
        self.assertEqual(compare.check_judge(judge, self.members()), [])


# ================================================================ md 底稿

class TestRenderMd(CompareEnv):

    def setUp(self):
        super().setUp()
        self.make_group()
        self.write_judge(self.good_judge())
        self.product = compare.assemble(SLUG, today=TODAY)
        self.md = (compare.group_dir(SLUG) / compare.md_name(SLUG, TODAY)).read_text(encoding="utf-8")

    def test_md_draft_written_next_to_product(self):
        self.assertIn("产业链同行对比", self.md)
        self.assertIn(ANCHOR, self.md)
        self.assertIn(PEER, self.md)

    def test_every_card_question_gets_a_row(self):
        for question in compare.CARD_QUESTIONS:
            self.assertIn(f"| {question} |", self.md)

    def test_judge_ranking_rendered_with_basis(self):
        self.assertIn(self.good_judge()["verdict"], self.md)
        self.assertIn("③赔率", self.md)                      # basis 用节点中文名, 不露 key
        self.assertIn("全组共担", self.md)

    def test_missing_members_section_lists_backfill_command(self):
        self.assertIn("缺报告成员", self.md)
        self.assertIn(ABSENT, self.md)
        self.assertIn("/company-analysis", self.md)


# ================================================================ --review 收尾联动

class TestReviewLinkage(CompareEnv):

    def test_status_is_clean_right_after_assembly(self):
        self.make_group()
        self.write_judge(self.good_judge())
        compare.assemble(SLUG, today=TODAY)
        st = compare.status(SLUG, today=TODAY)
        self.assertFalse(st["needs_rebuild"])
        self.assertEqual(st["generated"], TODAY)

    def test_status_flags_rebuild_after_member_review(self):
        self.make_group()
        self.write_judge(self.good_judge())
        compare.assemble(SLUG, today=TODAY)

        # 某成员跑了 --review, 落了新的一版 run
        company_dir = self.output / PEER
        self.make_member(PEER, PEER_TICKER, "2026-09-01", peer_nodes(), run_type="incremental")
        m = manifest_mod.load(company_dir)
        self.assertIn(SLUG, m["compare_groups"])            # 复查收尾第一问: 我在组里吗

        st = compare.status(SLUG, today="2026-09-01")
        self.assertTrue(st["needs_rebuild"])
        self.assertEqual([o["company"] for o in st["outdated_members"]], [PEER])
        self.assertTrue(any("成员报告已更新" in r for r in st["reasons"]))

    def test_status_flags_missing_judge(self):
        self.make_group()
        compare.assemble(SLUG, today=TODAY)
        st = compare.status(SLUG, today=TODAY)
        self.assertTrue(st["needs_rebuild"])
        self.assertTrue(any("裁决" in r for r in st["reasons"]))

    def test_status_never_assembled(self):
        self.make_group()
        st = compare.status(SLUG, today=TODAY)
        self.assertTrue(st["needs_rebuild"])
        self.assertIsNone(st["generated"])

    def test_manifest_group_membership_round_trip(self):
        self.make_group()
        company_dir = self.output / ANCHOR
        self.assertFalse(manifest_mod.add_compare_group(company_dir, SLUG))    # 幂等
        self.assertTrue(manifest_mod.remove_compare_group(company_dir, SLUG))
        self.assertEqual(manifest_mod.load(company_dir)["compare_groups"], [])
        self.assertFalse(manifest_mod.remove_compare_group(company_dir, SLUG))


# ================================================================ 出片(对比页 HTML)

class TestCompareHtml(CompareEnv):

    def setUp(self):
        super().setUp()
        self.make_group(chain_note="东山做 PCB 与光芯片, 同行做光模块, 同一条算力光互联链")
        self.write_judge(self.good_judge())
        self.product = compare.assemble(SLUG, today=TODAY)
        self.html = build_html.build_compare_html(self.product)

    def test_page_carries_group_identity(self):
        self.assertIn("PCB", self.html)
        self.assertIn("同一条算力光互联链", self.html)
        self.assertIn(TODAY, self.html)

    def test_every_member_and_verdict_rendered(self):
        for member in self.product["members"]:
            self.assertIn(member["company"], self.html)
            self.assertIn(member["action_gear"], self.html)
            for row in member["verdict_card"]:
                head = row["verdict"].split("——")[0].split(";")[0][:8]
                self.assertIn(build_html._esc(head), self.html)

    def test_member_cards_link_back_to_their_report(self):
        for member in self.product["members"]:
            self.assertIn(member["report_href"], self.html)

    def test_judge_section_present_with_ranking(self):
        self.assertIn(build_html._esc(self.product["judge"]["verdict"]), self.html)
        for item in self.product["judge"]["ranking"]:
            self.assertIn(build_html._esc(item["one_liner"]), self.html)

    def test_missing_members_and_notes_surface_on_page(self):
        self.assertIn(ABSENT, self.html)
        self.assertIn("缺完整报告", self.html)

    def test_stale_member_gets_visible_badge(self):
        aged = compare.assemble(SLUG, today="2026-12-02")
        html = build_html.build_compare_html(aged)
        self.assertIn("陈旧", html)
        self.assertIn("--review", html)

    def test_wide_table_scrolls_in_its_own_container(self):
        """390px 走查第一条: 宽表进横滚容器, 页面本体不横向滚动。"""
        self.assertIn('class="tblwrap"', self.html)

    def test_theme_toggle_and_no_font_size_in_media_queries(self):
        self.assertIn('id="themetoggle"', self.html)
        self.assertIn("data-theme", self.html)
        for chunk in self.html.split("@media")[1:]:
            block = chunk.split("}\n}")[0]
            self.assertNotIn("font-size", block, "移动端只重排不缩字号(交付票 07 硬纪律)")

    def test_no_external_resources(self):
        self.assertNotIn("<script src=", self.html)
        self.assertNotIn("https://cdn", self.html)


# ================================================================ 发布(站点条目)

class TestPublish(CompareEnv):

    def setUp(self):
        super().setUp()
        # 发布路径会 print emoji; 控制台在 Windows 上是 GBK, 收进 buffer 免得测试受制于终端编码
        redirect = contextlib.redirect_stdout(io.StringIO())
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)
        self.make_group()
        self.write_judge(self.good_judge())
        self.product = compare.assemble(SLUG, today=TODAY)
        self.repo = self.root / "site"
        (self.repo / "data").mkdir(parents=True)

    def test_card_quotes_judge_and_members_without_new_conclusions(self):
        card = update_index.compare_card(self.product)
        self.assertEqual(card["kind"], "compare")
        self.assertEqual(card["verdict"], self.product["judge"]["verdict"])
        self.assertEqual(card["winner"], PEER)
        self.assertEqual(card["member_count"], 2)
        self.assertEqual(card["missing_count"], 1)
        self.assertEqual(card["href"], f"compare/{SLUG}/index.html")
        # 成员链接从对比页视角(../../)换成首页视角(站点根)
        self.assertTrue(all(not m["href"].startswith("..") for m in card["members"]))

    def test_publish_writes_page_and_site_entry(self):
        rc = update_index.publish_compare(SLUG, self.repo)
        self.assertEqual(rc, 0)
        page = self.repo / "compare" / SLUG / "index.html"
        self.assertTrue(page.exists())
        self.assertIn(ANCHOR, page.read_text(encoding="utf-8"))
        data = json.loads((self.repo / "data" / "compare.json").read_text(encoding="utf-8"))
        self.assertEqual([g["slug"] for g in data["groups"]], [SLUG])

    def test_upsert_is_a_semantic_merge_not_a_file_overwrite(self):
        """站点仓库有别的会话和 cron 在写 —— 整文件覆盖会毁掉别人的条目。"""
        data_json = self.repo / "data" / "compare.json"
        data_json.write_text(json.dumps({
            "schema_version": "v1",
            "groups": [{"slug": "别人的组", "name": "别人的组", "generated": "2026-01-01"}],
        }, ensure_ascii=False), encoding="utf-8")

        update_index.publish_compare(SLUG, self.repo)
        slugs = [g["slug"] for g in json.loads(data_json.read_text(encoding="utf-8"))["groups"]]
        self.assertIn("别人的组", slugs)
        self.assertIn(SLUG, slugs)

    def test_upsert_replaces_same_slug_instead_of_duplicating(self):
        update_index.publish_compare(SLUG, self.repo)
        compare.assemble(SLUG, today="2026-09-10")
        update_index.publish_compare(SLUG, self.repo)
        groups = json.loads((self.repo / "data" / "compare.json").read_text(encoding="utf-8"))["groups"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["generated"], "2026-09-10")

    def test_older_version_does_not_overwrite_newer_without_force(self):
        compare.assemble(SLUG, today="2026-09-10")
        update_index.publish_compare(SLUG, self.repo)
        compare.assemble(SLUG, today=TODAY)                 # 回头装了个更旧的
        update_index.publish_compare(SLUG, self.repo)
        groups = json.loads((self.repo / "data" / "compare.json").read_text(encoding="utf-8"))["groups"]
        self.assertEqual(groups[0]["generated"], "2026-09-10")
        update_index.publish_compare(SLUG, self.repo, force=True)
        groups = json.loads((self.repo / "data" / "compare.json").read_text(encoding="utf-8"))["groups"]
        self.assertEqual(groups[0]["generated"], TODAY)


# ================================================================ 与旧版报告的兼容(真数据里踩到的)

class TestOlderContractMembers(CompareEnv):
    """成员报告是不同时间产出的 —— 用今天的完整契约去判昨天的完整报告, 会把它误判成缺报告。

    真事: 东山 2026-08-24 那份真实报告产于票 11 之前, 面板指标没有 `series`、③赔率没有
    `derivation`。对比页两样都不消费, 却因为整块校验而(a)整家被判「缺报告」(b)区间锚读不出来。
    """

    def _strip_new_contract_fields(self, company, date):
        run_dir = self.output / company / "runs" / date
        product_path = run_dir / "assembly" / "assembly.json"
        product = json.loads(product_path.read_text(encoding="utf-8"))
        for ind in product["panel"]["indicators"]:
            ind.pop("series", None)                       # 票 11 之前没有这个键
        product_path.write_text(json.dumps(product, ensure_ascii=False), encoding="utf-8")

        odds_md = run_dir / "nodes" / "node-odds.md"
        block = read_odds_block(odds_md)
        block.pop("derivation", None)                     # 票 11 之前没有这个块
        write_odds_block(odds_md, block)

    def test_pre_ticket11_member_still_compares_with_anchor(self):
        self._strip_new_contract_fields(ANCHOR, ANCHOR_DATE)
        self.make_group()
        product = compare.assemble(SLUG, today=TODAY)
        member = next(m for m in product["members"] if m["company"] == ANCHOR)
        self.assertNotIn("degraded", member)
        self.assertEqual(member["anchor_range"]["low"]["value"], fx.odds_block()["anchor_range"]["low"]["value"])
        self.assertIn("57-89", compare.anchor_text(member))

    def test_unreadable_anchor_degrades_that_cell_not_the_member(self):
        (self.output / ANCHOR / "runs" / ANCHOR_DATE / "nodes" / "node-odds.md").write_text(
            "没有 YAML 块的正文", encoding="utf-8")
        self.make_group()
        product = compare.assemble(SLUG, today=TODAY)
        member = next(m for m in product["members"] if m["company"] == ANCHOR)
        self.assertNotIn("anchor_range", member)
        self.assertTrue(member["degraded"])                       # 留空可以, 不说不行
        self.assertTrue(any("留空" in n for n in product["notes"]))
        self.assertEqual(compare.anchor_text(member), "–")

    def test_malformed_anchor_is_dropped_with_a_reason(self):
        run_dir = self.output / ANCHOR / "runs" / ANCHOR_DATE
        odds_md = run_dir / "nodes" / "node-odds.md"
        block = read_odds_block(odds_md)
        block["anchor_range"]["low"] = {"method": "SOTP"}          # 缺 value
        write_odds_block(odds_md, block)
        self.make_group()
        product = compare.assemble(SLUG, today=TODAY)
        member = next(m for m in product["members"] if m["company"] == ANCHOR)
        self.assertNotIn("anchor_range", member)
        self.assertIn("不合契约", member["degraded"][0])

    def test_missing_consumed_field_still_counts_as_missing_report(self):
        """不消费的字段可以旧, 消费的字段缺了就是缺报告 —— 兼容不等于什么都放过。"""
        product_path = self.output / PEER / "runs" / "2026-08-20" / "assembly" / "assembly.json"
        product = json.loads(product_path.read_text(encoding="utf-8"))
        del product["top3"]
        product_path.write_text(json.dumps(product, ensure_ascii=False), encoding="utf-8")
        self.make_group()
        with self.assertRaises(compare.CompareError):              # 只剩 1 家有报告
            compare.assemble(SLUG, today=TODAY)


if __name__ == "__main__":
    unittest.main()
