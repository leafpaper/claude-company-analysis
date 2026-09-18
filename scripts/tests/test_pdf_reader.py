"""单元测试: pdf_reader 的段落抽取(目录页守卫 + SSE/科创板模板 + 下载落盘)。

三条都来自华特气体(科创板)实测:

1. **目录页假阳性**:`mda` 判 `found=true`, 可 `text` 只有 595 / 181 字、`start_page=2` ——
   命中的是目录里那行「管理层讨论与分析 …… 27」。下游据此以为抓到了正文。
2. **SSE 模板失配**:`SECTION_PATTERNS` 按深市模板写死, 两份定期报告各只命中 5/9;
   缺的四段**公司都披露了, 只是标题不同**(利润表与现金流量表变动合并成一张表、
   主要会计数据带「六、近三年」前缀)。判成「未披露」是把工具的洞算到公司头上。
3. **PDF 落到盘根**:`Path("/tmp")` 在 Windows 上是 `C:\\tmp`, 原件与采集产物分了家。

运行:
    python -m unittest scripts.tests.test_pdf_reader
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from scripts import pdf_reader


def _reader(pages: list[str]) -> pdf_reader.PDFReader:
    """把 extract_text 换成给定的页面列表 —— 不碰真 PDF, 只测段落切分本身。"""
    r = pdf_reader.PDFReader()
    r.extract_text = lambda _path: pages          # type: ignore[assignment]
    return r


COVER = "华特气体 2026 年年度报告"
# 目录页:标题出现, 但后面紧跟着页码与下一个条目 —— 抓出来只有一行
TOC = (
    "目录\n"
    "第二节 公司简介和主要财务指标 ...... 5\n"
    "第三节 管理层讨论与分析 ...... 27\n"
    "第四节 公司治理 ...... 95\n"
)
# 正文页:同一个标题, 后面是成篇的正文
MDA_BODY = "第三节 管理层讨论与分析\n" + ("报告期内公司实现营业收入 8.51 亿元, 同比增长 28.95%。" * 40)
# 「重要提示」页:标题带引号出现在一句指路里 —— 比 200 字门槛长, 但它不是正文
MENTION = (
    "重要提示\n"
    "本公司董事会及全体董事保证本报告内容不存在任何虚假记载。\n"
    "公司经营情况的讨论与分析, 请查阅本报告第三节“管理层讨论与分析”的相关内容。\n"
    + "公司已在本报告中详细描述可能存在的风险, 敬请查阅相关章节。" * 8
)
# 短正文:子公司表本来就这么短, 结束模式也切得对(金山实测 287 字)
SHORT_SUBSIDIARIES = (
    "主要控股参股公司分析\n"
    "金山办公软件(北京)有限公司, 注册资本 5,000 万元, 净利润 12.3 亿元。\n"
    "广州金山办公软件科技有限公司, 注册资本 1,000 万元, 净利润 1.8 亿元。\n"
    "报告期内取得和处置子公司的情况\n"
    "不适用\n"
)


class TestTableOfContentsGuard(unittest.TestCase):

    def test_body_wins_over_toc_entry(self):
        """目录页先命中, 但正文才是要的那段 —— 页码应指向正文页, 不是第 2 页。"""
        sections = _reader([COVER, TOC, "中间页", MDA_BODY]).extract_sections("x.pdf")
        mda = sections["mda"]
        self.assertTrue(mda["found"])
        self.assertEqual(mda["start_page"], 4)
        self.assertGreaterEqual(len(mda["text"]), pdf_reader.MIN_SECTION_CHARS)

    def test_toc_only_is_reported_as_not_found(self):
        """整份 PDF 里它只在目录出现 → 判未找到, 并在 desc 里说明是目录页。

        这一条是关键:`found=True` 加一段 181 字的目录条目, 会被下游当成「公司披露了、内容就这些」。
        """
        sections = _reader([COVER, TOC, "别的内容"]).extract_sections("x.pdf")
        mda = sections["mda"]
        self.assertFalse(mda["found"])
        self.assertIn("目录", mda["desc"])
        self.assertEqual(sections["mda"]["start_page"], 2)   # 仍留着线索供人工核

    def test_missing_section_stays_empty(self):
        sections = _reader([COVER, "无关内容"]).extract_sections("x.pdf")
        self.assertFalse(sections["mda"]["found"])
        self.assertEqual(sections["mda"]["text"], "")

    def test_cross_reference_does_not_win_over_body(self):
        """「重要提示」里那句带引号的指路, 不是正文。

        金山 688111 / 华特 688268 实测: P.2 的「详见“第三节管理层讨论与分析”的相关内容」
        有 353 / 595 字, 比 200 字门槛长, 会先命中并抢走整段 —— 抓回来的是一句指路。
        引号是判据: 正文标题独占一行, 前缀只有章节序号。
        """
        sections = _reader([COVER, MENTION, TOC, MDA_BODY]).extract_sections("x.pdf")
        mda = sections["mda"]
        self.assertTrue(mda["found"])
        self.assertEqual(mda["start_page"], 4)

    def test_cross_reference_only_is_reported_as_not_found(self):
        """只有交叉引用、没有正文 → 判未找到, 并在 desc 里说清是引用不是目录。"""
        sections = _reader([COVER, MENTION, "别的内容"]).extract_sections("x.pdf")
        mda = sections["mda"]
        self.assertFalse(mda["found"])
        self.assertIn("交叉引用", mda["desc"])

    def test_short_body_is_still_found(self):
        """正文本来就短(子公司表、勾了「不适用」的段)照样算找到, 只在 desc 里提示回原文核。

        金山实测: 「主要控股参股公司分析」正文 287 字, 两家子公司的表完整在内。
        """
        sections = _reader([COVER, SHORT_SUBSIDIARIES]).extract_sections("x.pdf")
        sub = sections["subsidiaries"]
        self.assertTrue(sub["found"])
        self.assertIn("金山办公", sub["text"])
        self.assertLess(len(sub["text"]), pdf_reader.MIN_SECTION_CHARS)
        self.assertIn("很短", sub["desc"])


class TestSseTemplates(unittest.TestCase):
    """科创板标题与深市不同 —— 这些段公司都披露了, 只是模板不一样。"""

    def test_half_year_merged_changes_table(self):
        body = "1、财务报表相关科目变动分析表\n" + ("营业收入 1,418,749,512.43 元, 同比增长 1.70%。" * 30)
        sections = _reader([COVER, body, "（六）资产、负债情况分析"]).extract_sections("x.pdf")
        sec = sections["sse_statement_changes"]
        self.assertTrue(sec["found"], "半年报三表合并的变动分析表没抓到")
        self.assertIn("营业收入", sec["text"])

    def test_annual_merged_changes_table(self):
        body = "1、利润表及现金流量表相关科目变动分析表\n" + ("经营活动产生的现金流量净额 2.61 亿元。" * 30)
        sections = _reader([COVER, body]).extract_sections("x.pdf")
        self.assertTrue(sections["sse_statement_changes"]["found"])

    def test_main_financial_data_with_sse_prefix(self):
        """SSE 写「六、近三年主要会计数据和财务指标」, 深市锚点 `一、` 直接失配。"""
        body = "六、近三年主要会计数据和财务指标\n" + ("营业收入 851,000,000.00 归属于上市公司股东的净利润 135,350,000.00 " * 25)
        sections = _reader([COVER, body]).extract_sections("x.pdf")
        self.assertTrue(sections["main_financial_data"]["found"])

    def test_main_financial_data_half_year_heading(self):
        """半年报又换一套:「六、 公司主要会计数据和财务指标」, 中间多个「公司」。

        金山 688111 / 华特 688268 2026 半年报实测 —— 年报命中、半年报整段丢, 落到下游
        就是「半年报没披露主要财务数据」, 而公司披露了。
        """
        body = "六、 公司主要会计数据和财务指标\n(一) 主要会计数据\n" + ("营业收入 2,791,000,000.00 归属于上市公司股东的净利润 861,000,000.00 " * 25)
        sections = _reader([COVER, body]).extract_sections("x.pdf")
        self.assertTrue(sections["main_financial_data"]["found"])
        self.assertIn("营业收入", sections["main_financial_data"]["text"])

    def test_star_market_rd_tables(self):
        body = "3、研发投入情况表\n" + ("研发投入合计 5,432 万元, 占营业收入比例 6.38%。" * 30)
        sections = _reader([COVER, body, "（五）报告期内核心技术人员变动"]).extract_sections("x.pdf")
        self.assertTrue(sections["sse_rd_investment"]["found"], "科创板研发投入表没抓到")


class TestDownloadDir(unittest.TestCase):
    """PDF 要和采集产物放在一起, 别落到盘根。"""

    def test_follows_out_json_into_raw_data_pdfs(self):
        got = pdf_reader._download_dir(None, "output/华特气体/raw_data/pdf_sections_annual_2025.json")
        self.assertEqual(got, Path("output/华特气体/raw_data/pdfs"))

    def test_explicit_dir_wins(self):
        self.assertEqual(pdf_reader._download_dir("D:/somewhere", "a/b.json"), Path("D:/somewhere"))

    def test_falls_back_to_system_temp_not_slash_tmp(self):
        """要的是「用系统临时目录」, 不是「写死 /tmp」。

        Linux 上系统临时目录本来就是 /tmp, 所以「不等于 /tmp」这条只在非 POSIX 上才有区分度。
        无条件断言会让 CI 在 ubuntu 上必红 —— 本机 Windows 一直绿, 换个平台才现形。
        """
        got = pdf_reader._download_dir(None, None)
        self.assertEqual(got, Path(tempfile.gettempdir()))
        if os.name == "nt":
            self.assertNotEqual(got, Path("/tmp"))  # Windows 上 /tmp 会变成 C:\tmp


if __name__ == "__main__":
    unittest.main()
