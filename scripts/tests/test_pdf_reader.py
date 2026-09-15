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
        got = pdf_reader._download_dir(None, None)
        self.assertEqual(got, Path(tempfile.gettempdir()))
        self.assertNotEqual(got, Path("/tmp"))      # Windows 上 /tmp 会变成 C:\tmp


if __name__ == "__main__":
    unittest.main()
