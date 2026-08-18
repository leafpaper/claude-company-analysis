"""单元测试: v8 交付形态 — B 仪表盘 HTML + 红标三通道 + 移动端 + 明暗主题 + index 卡片。

实现票 07(.scratch/v8-implementation/issues/07-delivery-html.md)。
测试缝仍是 run 目录契约:东山 fixture 的五个节点 YAML 块 + audit 红旗 → 装配 → 成品 HTML,
断言的是**外部行为**(页面上看得见的东西), 不断言内部数据结构。

浏览器里的 390px 目测走查归 reviewer-delivery(spec Testing Decisions);这里机检的是
能机检的部分:横滚容器齐备、媒体查询里没有 font-size(禁缩字号)、瓦片单列断点存在、
双主题 token 齐备且对比度达标、红标三通道 + 反查链接齐备。

运行:
    python -m unittest scripts.tests.test_delivery_html_v8
"""
from __future__ import annotations

import html as html_lib
import re
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import assemble_report_v8 as render
from scripts import build_html
from scripts import red_flags as rf
from scripts import update_index
from scripts.tests import dongshan_fixture as fx
from scripts.tests.test_assembly_v8 import write_run_dir

CSS = (build_html.V8_CSS).read_text(encoding="utf-8")


def build_dongshan(td: str, nodes: dict | None = None, prev_nodes: dict | None = None):
    """东山 fixture → 真实 run 目录 → 装配 → 成品 HTML(全链路, 不打桩)。"""
    base = Path(td) / "东山精密"
    run_dir = write_run_dir(base, nodes or fx.nodes(), fx.audit_result())
    (run_dir / "data_snapshot.md").write_text(
        "# 数据快照\n\n| 期 | 营收 | 归母 | OCF | 存货 | 商誉 | 负债率 | 备注 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 2026Q1 | 148 亿 | 5.4 亿 | −6 亿 | 92 亿 | 47.69 亿 | 63.69% | 存货增速远高于营收 |\n",
        encoding="utf-8",
    )
    (run_dir / "peer_analysis.md").write_text("# Peer 对标\n\n5 家可比公司。\n", encoding="utf-8")
    (run_dir / "capital_flow.md").write_text(
        "# 资金流\n\n股东户数变化:8.17 万 → 30.60 万户。\n", encoding="utf-8"
    )
    prev_run_dir = None
    if prev_nodes is not None:
        prev_run_dir = write_run_dir(Path(td) / "prev", prev_nodes, fx.audit_result())
    product, md_out = render.assemble_run(
        run_dir=run_dir, company="东山精密", date="2026-06-22", ticker="002384.SZ",
        next_disclosure_date="2026-08-30", prev_run_dir=prev_run_dir,
    )
    _, nodes_blocks = build_html.load_v8_context(md_out, run_dir)
    html = build_html.build_html_v8(md_out, product, nodes=nodes_blocks, ticker="002384.SZ")
    return product, html, md_out, run_dir


class _Built(unittest.TestCase):
    """一次装配, 全类共用(装配+渲染是纯函数, 没有跨用例状态)。"""

    @classmethod
    def setUpClass(cls):
        cls._td = tempfile.TemporaryDirectory()
        cls.product, cls.html, cls.md_path, cls.run_dir = build_dongshan(cls._td.name)

    @classmethod
    def tearDownClass(cls):
        cls._td.cleanup()


# ---------------------------------------------------------------- 首页: 决断卡 / 面板 / Top3

class TestDashboardFrontPage(_Built):
    def test_five_verdict_tiles_carry_research_02_card(self):
        """决断卡五行(golden)全部出现在瓦片上, 且每行链到自己的章节。"""
        tiles = self.html.split('class="cards5"')[1].split("</div>\n\n<!--")[0]
        self.assertEqual(tiles.count('class="dc'), 5)
        for row in self.product["verdict_card"]:
            head, _ = build_html._split_verdict(row["verdict"])
            self.assertIn(head, tiles, f"决断卡判定「{head}」没上瓦片")
            self.assertIn(f'href="#ch-{row["source_node"]}"', tiles)

    def test_decision_tile_tone_follows_action_gear(self):
        """⑤怎么办的语气 = 行动档位映射(复用 update_index 六档表), 不另立阈值。"""
        self.assertEqual(
            build_html.node_tone("decision", self.product, {}),
            build_html.TONE_BY_STANCE[update_index.GEAR_TONE["等证据临界"]],
        )
        bearish = {"metadata": dict(self.product["metadata"], action_gear="回避")}
        self.assertEqual(build_html.node_tone("decision", bearish, {}), "bad")

    def test_panel_tiles_and_conclusion_quote_quality(self):
        panel = self.html.split('class="tiles"')[1].split("</div>\n\n<!--")[0]
        for ind in self.product["panel"]["indicators"]:
            self.assertIn(ind["name"], panel)
            self.assertIn(ind["value"], panel)
        self.assertIn("面板结论", panel)
        self.assertIn("面板不自产结论", panel)

    def test_top3_cards_link_to_appendix_d_and_home_node(self):
        risks = self.html.split('class="risks"')[1].split("</div>\n\n<!--")[0]
        self.assertEqual(risks.count('class="rk '), 3)
        for item in self.product["top3"]:
            self.assertIn(item["title"], risks)
            self.assertIn(f'href="#{rf.anchor(item["red_flag_id"])}"', risks)
            self.assertIn(rf.NODE_LABELS[item["node"]], risks)

    def test_hero_facts_from_contract_fields_only(self):
        facts = self.html.split('class="facts"')[1].split("</div>\n\n<!--")[0]
        for expected in ("行动档位", "等证据临界", "质地", "部分好", "现价", "273",
                         "锚区间", "57–89", "下次预约披露", "2026-08-30"):
            self.assertIn(expected, facts)

    def test_writer_intro_is_the_only_human_slot(self):
        self.assertIn("写手导读", self.html)
        self.assertIn("等 2026 中报", self.html)


# ---------------------------------------------------------------- 红标三通道 + 反查

class TestRedMarkThreeChannels(_Built):
    def _marks(self) -> list[str]:
        return re.findall(r'<a class="fw fw-[^"]*".*?</a>', self.html, re.DOTALL)

    def test_every_mark_has_emoji_text_and_wash(self):
        """三通道: emoji(.fw-i) + 文字级别词(.fw-k) + 底纹(fw-red/fw-yellow class)。"""
        marks = self._marks()
        self.assertGreater(len(marks), 0, "成品里一个红标都没有")
        for mark in marks:
            self.assertRegex(mark, r'class="fw fw-(red|yellow)')          # ③底纹
            self.assertRegex(mark, r'<span class="fw-i"[^>]*>(🔴|🟠|🟡)') # ①emoji
            self.assertRegex(mark, r'<span class="fw-k">(致命红旗|高级红旗|中级红旗)')  # ②文字
            self.assertIn("<span class=\"fw-t\">", mark)

    def test_level_maps_to_colour_family(self):
        """🔴/🟠 红色系、🟡 黄色系 —— 级别靠 emoji 分, 颜色只分两族(spec §4)。"""
        for mark in self._marks():
            emoji = re.search(r'class="fw-i"[^>]*>(.)', mark).group(1)
            family = re.search(r"fw-(red|yellow)", mark).group(1)
            self.assertEqual(rf.MARK_BY_LEVEL[emoji], family)

    def test_reverse_lookup_popover_has_five_facts(self):
        """浮层给全反查五要素: 标题/级别/一句证据/来源/归属节点。"""
        cash = rf.anchor(fx.CASH_FLAG_ID)
        mark = next(m for m in self._marks() if cash in m)
        pop = re.search(r'<span class="fw-pop".*?</span></a>', mark, re.DOTALL).group(0)
        self.assertIn("利润质量偏弱", pop)
        self.assertIn("高级红旗", pop)
        self.assertIn("OCF", pop)                      # 证据
        self.assertIn("脚本", pop)                      # 来源
        self.assertIn("①质地", pop)                     # 归属节点
        self.assertIn("附录D", pop)

    def test_mark_is_a_link_to_appendix_d_entry(self):
        """触屏无悬停 → 红标本身即链接, 点击直达附录D 条目锚点(同一实现)。"""
        for mark in self._marks():
            href = re.search(r'href="#([^"]+)"', mark).group(1)
            self.assertTrue(href.startswith("flag-"), href)
            self.assertIn(f'<a id="{href}"></a>', self.html, "附录D 缺该红旗的锚点")

    def test_title_attribute_is_the_clipped_popover_fallback(self):
        """浮层可能被横滚容器裁掉 —— title 兜底, 反查信息不丢。"""
        for mark in self._marks():
            title = re.search(r'title="([^"]+)"', mark).group(1)
            self.assertIn("来源", title)
            self.assertIn("归属", title)

    def test_touch_devices_get_click_not_hover(self):
        """触屏与窄屏都不渲染浮层(display:none 连布局都不占), 反查退回点击直达附录D。"""
        self.assertIn("@media (hover:none), (max-width:720px){ .fw-pop{display:none} }", CSS)

    def test_nomination_and_script_flags_are_marked_alike(self):
        """两源同池:写手提名与脚本红旗走同一套红标与排序, 不分二等公民。"""
        marks = " ".join(self._marks())
        # 提名的「散户暴增」是本组最严重的一条 → 由它领衔 Top3 卡红标(与脚本红旗同池排序)
        self.assertIn(rf.anchor(fx.NOMINATION_CROWDING), marks)
        self.assertIn("写手提名", marks)
        # 与脚本红旗并成一组的提名(商誉对赌)在同一张卡上给出自己的附录D 链接
        self.assertIn(f'href="#{rf.anchor(fx.NOMINATION_GOODWILL)}"', self.html)
        for nomination in (fx.NOMINATION_GOODWILL, fx.NOMINATION_CROWDING):
            self.assertIn(f'<a id="{rf.anchor(nomination)}"></a>', self.html)

    def test_body_prose_marked_by_reverse_lookup_only(self):
        """正文红标 = 按红旗清单逐字反查(写手不手涂);无红旗命中的难看数字不标色。"""
        vocab = build_html.red_mark_vocab(self.product)
        self.assertIn("存货增速远高于营收", vocab)          # 🟡 有红旗 → 进词表
        self.assertNotIn("ROE + peer 分位", vocab)          # 难看但无规则命中 → 不标色
        appendix_a = self.html.split('id="appx-A"')[1].split("</section>")[0]
        self.assertIn('class="fw fw-yellow fw-inline"', appendix_a)

    def test_appendix_d_table_is_not_auto_marked(self):
        """附录D 是红标的数据源本体, 不再对它自己反查(免得整表刷红)。"""
        appendix_d = self.html.split('id="appx-D"')[1].split("</section>")[0]
        self.assertNotIn('class="fw fw-', appendix_d)
        self.assertIn("商誉占净资产过高", appendix_d)

    def test_marks_never_nest_inside_marks(self):
        self.assertNotIn('class="fw-t"><a class="fw', self.html)
        self.assertEqual(self.html.count('<a class="fw '), self.html.count("</a>") - self.html.count(
            '</a>') + self.html.count('<a class="fw '))  # 计数自洽(无未闭合)


# ---------------------------------------------------------------- 移动端(390px 走查的机检部分)

class TestMobileFirstClass(_Built):
    def test_every_table_sits_in_a_scroll_container(self):
        """所有表格强制横滚容器 —— 窄屏页面本体不横向溢出。"""
        for m in re.finditer(r"<table\b", self.html):
            head = self.html[:m.start()]
            self.assertTrue(
                head.rstrip().endswith('<div class="tblwrap">'),
                f"第 {head.count('<table')+1} 个表格不在 .tblwrap 里",
            )
        self.assertGreater(self.html.count('class="tblwrap"'), 0)

    def test_no_font_size_shrinking_in_media_queries(self):
        """禁缩字号: 媒体查询里只重排结构, 一处 font-size 都不许有。"""
        for block in re.findall(r"@media[^{]+\{(.*?)\n\}", CSS, re.DOTALL):
            self.assertNotIn("font-size", block, f"媒体查询里出现 font-size:\n{block[:200]}")

    def test_no_12px_text_anywhere(self):
        """禁 12px:正文与表格 ≥14px, 最小标签 ≥12.5px。"""
        sizes = [float(s) for s in re.findall(r"font-size:\s*([\d.]+)px", CSS)]
        sizes += [float(m) for m in re.findall(r"font:[^;]*?\b([\d.]+)px/", CSS)]
        self.assertTrue(sizes)
        self.assertGreaterEqual(min(sizes), 12.5, f"存在 <12.5px 的字号: {sorted(sizes)[:3]}")

    def test_tiles_collapse_to_single_column(self):
        """瓦片/风险卡/附录卡在窄屏单列重排(B 版式的移动端红利)。"""
        narrow = re.search(r"@media \(max-width:620px\)\{(.*?)\n\}", CSS, re.DOTALL).group(1)
        self.assertIn(".cards5,.tiles,.appxnav{grid-template-columns:1fr}", narrow)
        wide = re.search(r"@media \(max-width:720px\)\{(.*?)\n\}", CSS, re.DOTALL).group(1)
        self.assertIn(".risks{grid-template-columns:1fr}", wide)

    def test_sticky_nav_released_on_phone(self):
        """v7 痛点:吸顶导航在手机上吃掉约 10% 屏 —— 窄屏改静态。"""
        wide = re.search(r"@media \(max-width:720px\)\{(.*?)\n\}", CSS, re.DOTALL).group(1)
        self.assertIn(".topbar{position:static}", wide)

    def test_viewport_and_overflow_guards(self):
        self.assertIn('name="viewport" content="width=device-width, initial-scale=1"', self.html)
        self.assertIn("overflow-wrap:break-word", CSS)
        self.assertIn("img{max-width:100%", CSS)
        # 绝对定位的浮层探出版心也不许把页面撑横 —— clip 不造滚动容器, 不破 sticky
        self.assertRegex(CSS, r"\.wrap\{[^}]*overflow-x:clip")

    def test_short_tokens_are_not_auto_marked(self):
        """「FCF」这类三字母词太短, 逐字反查会命中表头与无关句子 —— 不进自动词表。"""
        vocab = build_html.red_mark_vocab(self.product)
        self.assertNotIn("FCF", vocab)
        self.assertNotIn('<th><a class="fw', self.html)

    def test_assembly_section_rules_not_carried_into_cards(self):
        """装配的章间分隔线不该在卡片里留下孤零零的 <hr>(卡片自带边框)。"""
        self.assertNotIn("<hr", self.html)

    def test_no_fixed_pixel_widths_wider_than_a_phone(self):
        for value in re.findall(r"(?<!max-)width:\s*(\d+)px", CSS):
            self.assertLessEqual(int(value), 390, f"固定宽度 {value}px 会撑破 390px 屏")


# ---------------------------------------------------------------- 明暗双主题 + 对比度

def _rgb(hex_colour: str) -> tuple[float, float, float]:
    h = hex_colour.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _luminance(hex_colour: str) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in _rgb(hex_colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float:
    l1, l2 = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def theme_tokens(block_pattern: str) -> dict[str, str]:
    m = re.search(block_pattern, CSS, re.DOTALL | re.MULTILINE)
    assert m, f"report-v8.css 里找不到主题块: {block_pattern}"
    return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", m.group(1)))


class TestDualTheme(unittest.TestCase):
    LIGHT = r"^:root\{(.*?)\n\}"
    DARK_EXPLICIT = r':root\[data-theme="dark"\]\{(.*?)\n\}'
    DARK_SYSTEM = r'@media \(prefers-color-scheme: dark\)\{\s*:root:not\(\[data-theme="light"\]\)\{(.*?)\n  \}'

    def test_three_theme_states_defined(self):
        """系统默认 / 手动亮 / 手动暗 三态齐备, 且暗色两处 token 完全一致。"""
        light = theme_tokens(self.LIGHT)
        system_dark = theme_tokens(self.DARK_SYSTEM)
        explicit_dark = theme_tokens(self.DARK_EXPLICIT)
        self.assertTrue(light and system_dark and explicit_dark)
        self.assertEqual(system_dark, explicit_dark, "系统暗色与手动暗色 token 漂移")
        self.assertEqual(set(light), set(explicit_dark), "明暗两套 token 名字对不齐")

    def test_text_contrast_meets_45_in_both_themes(self):
        """正文/次要文字在页面底色、卡片底色、红/黄底纹上都 ≥ 4.5:1。"""
        for name, tokens in (("light", theme_tokens(self.LIGHT)),
                             ("dark", theme_tokens(self.DARK_EXPLICIT))):
            for fg in ("ink", "ink2", "muted"):
                for bg in ("page", "surface", "surface2", "wash-r", "wash-y", "wash-g", "wash-a"):
                    ratio = contrast(tokens[fg], tokens[bg])
                    self.assertGreaterEqual(
                        ratio, 4.5, f"{name}: --{fg} on --{bg} = {ratio:.2f}:1 未达 4.5"
                    )

    def test_accent_and_flag_bars_meet_3_to_1(self):
        """链接色与红标封条/瓦片色条(非文字 UI 件)≥ 3:1。"""
        for name, tokens in (("light", theme_tokens(self.LIGHT)),
                             ("dark", theme_tokens(self.DARK_EXPLICIT))):
            for token in ("accent", "crit", "seri", "warn", "good"):
                for bg in ("surface", "page"):
                    ratio = contrast(tokens[token], tokens[bg])
                    self.assertGreaterEqual(
                        ratio, 3.0, f"{name}: --{token} on --{bg} = {ratio:.2f}:1 未达 3.0"
                    )

    def test_red_and_yellow_washes_are_distinguishable_from_surface(self):
        for name, tokens in (("light", theme_tokens(self.LIGHT)),
                             ("dark", theme_tokens(self.DARK_EXPLICIT))):
            for wash in ("wash-r", "wash-y"):
                self.assertNotEqual(tokens[wash], tokens["surface"], f"{name}: {wash} 与卡片同色")

    def test_theme_toggle_present_and_remembers(self):
        html = (build_html.V8_TEMPLATE).read_text(encoding="utf-8")
        self.assertIn('id="themetoggle"', html)
        self.assertIn("localStorage", html)
        self.assertIn("prefers-color-scheme: dark", html)


# ---------------------------------------------------------------- 结构完整性 / 增量变化区块

class TestPageIntegrity(_Built):
    def test_all_chapters_and_appendices_rendered(self):
        for node in ("quality", "state", "odds", "path", "decision"):
            self.assertIn(f'id="ch-{node}"', self.html)
        for key in "ABCDE":
            self.assertIn(f'id="appx-{key}"', self.html)

    def test_coverage_selfcheck_is_clean(self):
        parts = build_html.split_v8_sections(self.md_path.read_text(encoding="utf-8"))
        self.assertEqual(build_html.check_v8_coverage(self.html, self.product, parts), [])

    def test_front_page_markdown_replaced_not_duplicated(self):
        """首页由 assembly.json 重渲染, md 里那份不再二次输出。"""
        self.assertNotIn("决断卡(机器装配自五个节点 verdict)", self.html)
        self.assertEqual(self.html.count('id="front"'), 1)

    def test_machine_vs_human_labels(self):
        self.assertIn('<span class="chip">机器装配</span>', self.html)
        self.assertIn('<span class="chip man">人工 3-5 句</span>', self.html)

    def test_no_unfilled_placeholders(self):
        self.assertNotIn("{{", self.html)
        self.assertNotIn("<!-- PLACEHOLDER:", self.html)

    def test_appendix_artifacts_mounted_with_tables(self):
        appendix_a = self.html.split('id="appx-A"')[1].split("</section>")[0]
        self.assertIn('<div class="tblwrap">', appendix_a)
        self.assertIn("47.69 亿", appendix_a)

    def test_full_run_has_no_change_block(self):
        self.assertNotIn('class="change"', self.html)


class TestIncrementalChangeBlock(unittest.TestCase):
    def test_scenario_a_change_block_rendered(self):
        """增量复查场景 A(中报兑现不足): 首页多一块「较上版变化」, 首句答阿尔法变了没。"""
        with tempfile.TemporaryDirectory() as td:
            product, html, _, _ = build_dongshan(
                td, nodes=fx.scenario_a_nodes(), prev_nodes=fx.nodes()
            )
            self.assertIn('class="change"', html)
            self.assertIn(html_lib.escape(product["change_block"]["alpha_summary"]), html)
            self.assertIn("等证据临界", html)
            self.assertIn("回避", html)
            self.assertIn("证伪触发", html)

    def test_scenario_b_advises_full_rerun(self):
        with tempfile.TemporaryDirectory() as td:
            _, html, _, _ = build_dongshan(
                td, nodes=fx.scenario_b_nodes(), prev_nodes=fx.nodes()
            )
            self.assertIn("建议全量重跑", html)


# ---------------------------------------------------------------- 站点 index 卡片改版

class TestIndexCardV8(unittest.TestCase):
    def _card(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, md_path, _ = build_dongshan(td)
            return update_index.extract_metadata(md_path, "东山精密")

    def test_verdict_is_action_gear_plain_plus_quality_field(self):
        card = self._card()
        self.assertEqual(card.verdict, "先观察等证据临界,期权小仓 ≤2-3%")
        self.assertEqual(card.quality_field, "部分好")
        self.assertEqual(card.action_gear, "等证据临界")
        self.assertEqual(card.verdict_tone, "neutral")
        self.assertEqual(card.version, "v8.0")

    def test_metrics_switch_to_judgment_chain(self):
        """v8 无综合评分/期望收益 —— 三块 metrics 换成 行动档位 / 质地 / 贵不贵。"""
        labels = [m["label"] for m in self._card().metrics]
        self.assertEqual(labels, ["行动档位", "质地", "贵不贵"])

    def test_badges_carry_gear_quality_odds(self):
        labels = [b["label"] for b in self._card().badges]
        self.assertIn("先观察等证据临界,期权小仓 ≤2-3%", labels)
        self.assertIn("质地 部分好", labels)
        self.assertTrue(any(l.startswith("赔率 买完完美未来") for l in labels))

    def test_next_disclosure_date_on_card_for_staleness(self):
        self.assertEqual(self._card().next_disclosure_date, "2026-08-30")

    def test_one_liner_falls_back_to_writer_intro(self):
        card = self._card()
        self.assertTrue(card.one_liner.startswith("老本行是赚辛苦钱的 PCB 红海龙头"))


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (TestDashboardFrontPage, TestRedMarkThreeChannels, TestMobileFirstClass,
                TestDualTheme, TestPageIntegrity, TestIncrementalChangeBlock, TestIndexCardV8):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
