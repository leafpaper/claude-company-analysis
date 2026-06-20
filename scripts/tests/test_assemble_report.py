"""单元测试: scripts.assemble_report (v6.0 — 8 章节 / 4 part)

运行:
    python3 -m scripts.tests.test_assemble_report
    或  python3 -m pytest scripts/tests/test_assemble_report.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from scripts import assemble_report


def _make_part(idx: int, sections: list[str], extra: str = "") -> str:
    """构造一个 part 文件内容."""
    parts = []
    for sec in sections:
        parts.append(f"\n{sec}\n\n这是 {sec} 的内容。\n")
    if extra:
        parts.append(extra)
    return "\n".join(parts)


class TestValidatePart(unittest.TestCase):
    def test_part1_with_required_section(self):
        content = _make_part(1, ["## §一 执行摘要"])
        issues = assemble_report.validate_part(1, content)
        self.assertEqual(issues, [])

    def test_part2_missing_section_raises(self):
        content = _make_part(2, ["## §二 公司基本面"])  # 缺 §三
        issues = assemble_report.validate_part(2, content)
        self.assertEqual(len(issues), 1)
        self.assertIn("§三", issues[0])

    def test_part4_all_sections(self):
        content = _make_part(4, ["## §六 风险与红旗审计", "## §七 舆情与市场情绪", "## §八 数据来源与信息缺口"])
        issues = assemble_report.validate_part(4, content)
        self.assertEqual(issues, [])

    def test_part4_with_tab_after_section(self):
        """§七 后用 tab 代替空格也应识别 (正则边界匹配, 不依赖尾部空格)"""
        content = "## §六 风险\n\n## §七\t舆情\n\n## §八 来源\n"
        issues = assemble_report.validate_part(4, content)
        self.assertEqual(issues, [], "§七 后跟 tab 应被正则识别")

    def test_part4_with_multiple_spaces(self):
        """§七 后多个空格(常见手抖)也应识别"""
        content = "## §六 风险\n\n## §七   舆情\n\n## §八 来源\n"
        issues = assemble_report.validate_part(4, content)
        self.assertEqual(issues, [], "§七 后多空格应被正则识别")

    def test_section_at_end_of_line_no_title(self):
        """§标题 后无正文化标题(行末)也应识别(罕见但合法)"""
        content = "## §六\n\n内容\n\n## §七 舆情\n\n## §八 来源\n"
        issues = assemble_report.validate_part(4, content)
        self.assertEqual(issues, [])


class TestAssembleEndToEnd(unittest.TestCase):
    def test_assemble_4_parts_writes_final(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            # 构造 4 个 part 文件 (含必需章节, v6.0 = 8 章节)
            (d / "phase3-part1.md").write_text(_make_part(1, ["## §一 执行摘要"]), encoding="utf-8")
            (d / "phase3-part2.md").write_text(_make_part(2, ["## §二 公司基本面", "## §三 行业与竞争对标"]), encoding="utf-8")
            (d / "phase3-part3.md").write_text(_make_part(3, ["## §四 评分与维度证据", "## §五 估值与回报"]), encoding="utf-8")
            (d / "phase3-part4.md").write_text(_make_part(4, ["## §六 风险与红旗审计", "## §七 舆情与市场情绪", "## §八 数据来源与信息缺口"]), encoding="utf-8")
            out = d / "final.md"
            ret = assemble_report.assemble("TestCo", "2026-06-20", d, out)
            self.assertEqual(ret, 0)
            self.assertTrue(out.exists())
            content = out.read_text(encoding="utf-8")
            # 8 章节齐全
            for sec_name in ("§一", "§四", "§六", "§八"):
                self.assertIn(sec_name, content)
            # section 数 = 8
            self.assertEqual(content.count("\n## §"), assemble_report.EXPECTED_SECTION_COUNT)

    def test_assemble_missing_part_returns_1(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            # 只写 3 个 part (缺 part4)
            for i in range(1, 4):
                (d / f"phase3-part{i}.md").write_text(f"## §{i} test\n", encoding="utf-8")
            out = d / "final.md"
            ret = assemble_report.assemble("TestCo", "2026-06-20", d, out)
            self.assertEqual(ret, 1)

    def test_assemble_missing_section_validation_fails(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            # part2 缺 §三
            (d / "phase3-part1.md").write_text(_make_part(1, ["## §一 执行摘要"]), encoding="utf-8")
            (d / "phase3-part2.md").write_text("## §二 公司基本面\n仅 §二, 缺 §三\n", encoding="utf-8")
            (d / "phase3-part3.md").write_text(_make_part(3, ["## §四 评分", "## §五 估值"]), encoding="utf-8")
            (d / "phase3-part4.md").write_text(_make_part(4, ["## §六 风险", "## §七 舆情", "## §八 来源"]), encoding="utf-8")
            out = d / "final.md"
            ret = assemble_report.assemble("TestCo", "2026-06-20", d, out)
            self.assertEqual(ret, 1, "缺章节应返回 1")


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (TestValidatePart, TestAssembleEndToEnd):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
