"""单元测试: scripts.assemble_report (v7.0 — 9 章节 / 5 part)

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


# v7.0 各 part 的规范章节标题 (与 skeleton / PART_EXPECTED_SECTIONS 一致)
PART_TITLES = {
    1: ["## §一 执行摘要"],
    2: ["## §二 公司基本面", "## §三 行业与竞争对标"],
    3: ["## §四 评分与维度证据", "## §五 估值、赔率与定价充分度"],
    4: ["## §六 风险与红旗审计", "## §七 投资决策内核"],
    5: ["## §八 舆情与市场情绪", "## §九 数据来源与信息缺口"],
}


class TestValidatePart(unittest.TestCase):
    def test_part1_with_required_section(self):
        content = _make_part(1, PART_TITLES[1])
        self.assertEqual(assemble_report.validate_part(1, content), [])

    def test_part2_missing_section_raises(self):
        content = _make_part(2, ["## §二 公司基本面"])  # 缺 §三
        issues = assemble_report.validate_part(2, content)
        self.assertEqual(len(issues), 1)
        self.assertIn("§三", issues[0])

    def test_part4_all_sections(self):
        content = _make_part(4, PART_TITLES[4])
        self.assertEqual(assemble_report.validate_part(4, content), [])

    def test_part5_all_sections(self):
        content = _make_part(5, PART_TITLES[5])
        self.assertEqual(assemble_report.validate_part(5, content), [])

    def test_part4_missing_decision_core_raises(self):
        content = _make_part(4, ["## §六 风险与红旗审计"])  # 缺 §七
        issues = assemble_report.validate_part(4, content)
        self.assertEqual(len(issues), 1)
        self.assertIn("§七", issues[0])

    def test_part4_with_tab_after_section(self):
        """§七 后用 tab 代替空格也应识别 (正则边界匹配, 不依赖尾部空格)"""
        content = "## §六 风险\n\n## §七\t投资决策内核\n"
        self.assertEqual(assemble_report.validate_part(4, content), [])

    def test_part4_with_multiple_spaces(self):
        content = "## §六 风险\n\n## §七   投资决策内核\n"
        self.assertEqual(assemble_report.validate_part(4, content), [])

    def test_section_at_end_of_line_no_title(self):
        content = "## §六\n\n内容\n\n## §七 投资决策内核\n"
        self.assertEqual(assemble_report.validate_part(4, content), [])


class TestAssembleEndToEnd(unittest.TestCase):
    def test_assemble_5_parts_writes_final(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            for i in range(1, 6):
                (d / f"phase3-part{i}.md").write_text(_make_part(i, PART_TITLES[i]), encoding="utf-8")
            out = d / "final.md"
            ret = assemble_report.assemble("TestCo", "2026-06-20", d, out)
            self.assertEqual(ret, 0)
            self.assertTrue(out.exists())
            content = out.read_text(encoding="utf-8")
            # 9 章节齐全 (抽查含新 §七 投资决策内核 + 末章 §九)
            for sec_name in ("§一", "§四", "§七", "§九"):
                self.assertIn(sec_name, content)
            self.assertEqual(content.count("\n## §"), assemble_report.EXPECTED_SECTION_COUNT)
            self.assertEqual(assemble_report.EXPECTED_SECTION_COUNT, 9)
            self.assertEqual(assemble_report.N_PARTS, 5)

    def test_assemble_missing_part_returns_1(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            for i in range(1, 5):  # 缺 part5
                (d / f"phase3-part{i}.md").write_text(_make_part(i, PART_TITLES[i]), encoding="utf-8")
            out = d / "final.md"
            self.assertEqual(assemble_report.assemble("TestCo", "2026-06-20", d, out), 1)

    def test_assemble_missing_section_validation_fails(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "phase3-part1.md").write_text(_make_part(1, PART_TITLES[1]), encoding="utf-8")
            (d / "phase3-part2.md").write_text("## §二 公司基本面\n仅 §二, 缺 §三\n", encoding="utf-8")
            (d / "phase3-part3.md").write_text(_make_part(3, PART_TITLES[3]), encoding="utf-8")
            (d / "phase3-part4.md").write_text(_make_part(4, PART_TITLES[4]), encoding="utf-8")
            (d / "phase3-part5.md").write_text(_make_part(5, PART_TITLES[5]), encoding="utf-8")
            out = d / "final.md"
            self.assertEqual(assemble_report.assemble("TestCo", "2026-06-20", d, out), 1, "缺章节应返回 1")


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
