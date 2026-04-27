"""单元测试: scripts.assemble_report

运行:
    python3 -m scripts.tests.test_assemble_report
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
    def test_part1_with_required_sections(self):
        content = _make_part(1, ["## §一 执行摘要", "## §二 事实评分总览", "## §三 快速筛选"])
        issues = assemble_report.validate_part(1, content)
        self.assertEqual(issues, [])

    def test_part2_missing_section_raises(self):
        content = _make_part(2, ["## §四 公司基本面"])  # 缺 §五
        issues = assemble_report.validate_part(2, content)
        self.assertEqual(len(issues), 1)
        self.assertIn("§五", issues[0])

    def test_part4_section_十_with_space(self):
        """§十 后面有空格区分 §十/§十一/§十二/...; 测试边界"""
        content = _make_part(4, ["## §九 估值与回报模拟", "## §十 投资回报测算", "## §十一 定性判断"])
        issues = assemble_report.validate_part(4, content)
        self.assertEqual(issues, [])

    def test_part4_only_十一_should_fail(self):
        """如果只有 §十一 没有 §十, 应报错"""
        content = "## §九 估值与回报模拟\n\n## §十一 定性判断\n"
        issues = assemble_report.validate_part(4, content)
        # 期望报缺 §十 (由于 PART_EXPECTED_SECTIONS 中是 "## §十 " 含空格, §十一 不会匹配)
        self.assertTrue(any("§十 " in i for i in issues))


class TestExtractMetadataBlocks(unittest.TestCase):
    def test_extracts_3_blocks(self):
        part1 = """# 报告

<!-- RATING_TRIO_DATA:
  composite_score: 5.0
  verdict: 中性
-->

<!-- KEY_METRICS_SIDEBAR:
  pe_ttm: 30
-->

<!-- CARD_METADATA:
  slug: TEST_测试
-->

## §一 摘要
"""
        result = assemble_report.extract_metadata_blocks(part1)
        self.assertIn("RATING_TRIO_DATA", result)
        self.assertIn("KEY_METRICS_SIDEBAR", result)
        self.assertIn("CARD_METADATA", result)

    def test_missing_blocks_returns_empty(self):
        part1 = "# 报告\n\n## §一 摘要\n"
        result = assemble_report.extract_metadata_blocks(part1)
        self.assertEqual(result, "")


class TestAssembleEndToEnd(unittest.TestCase):
    def test_assemble_5_parts_writes_final(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            # 构造 5 个 part 文件 (含必需章节)
            (d / "phase3-part1.md").write_text(_make_part(1, ["## §一 执行摘要", "## §二 评分", "## §三 快筛"]))
            (d / "phase3-part2.md").write_text(_make_part(2, ["## §四 基本面", "## §五 行业"]))
            (d / "phase3-part3.md").write_text(_make_part(3, ["## §六 维度", "## §七 舆情", "## §八 Peer"]))
            (d / "phase3-part4.md").write_text(_make_part(4, ["## §九 估值", "## §十 回报", "## §十一 定性"]))
            (d / "phase3-part5.md").write_text(_make_part(5, ["## §十二 洞察", "## §十三 角色", "## §十四 缺口", "## §十五 来源"]))
            out = d / "final.md"
            ret = assemble_report.assemble("TestCo", "2026-04-27", d, out)
            self.assertEqual(ret, 0)
            self.assertTrue(out.exists())
            content = out.read_text()
            # 章节齐全
            for sec_name in ("§一", "§五", "§十", "§十五"):
                self.assertIn(sec_name, content)

    def test_assemble_missing_part_returns_1(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            # 只写 4 个 part
            for i in range(1, 5):
                (d / f"phase3-part{i}.md").write_text(f"## §{i} test\n")
            out = d / "final.md"
            ret = assemble_report.assemble("TestCo", "2026-04-27", d, out)
            self.assertEqual(ret, 1)

    def test_assemble_missing_section_validation_fails(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            # part2 缺 §五
            (d / "phase3-part1.md").write_text(_make_part(1, ["## §一", "## §二", "## §三"]))
            (d / "phase3-part2.md").write_text("## §四 基本面\n仅 §四, 缺 §五\n")
            (d / "phase3-part3.md").write_text(_make_part(3, ["## §六", "## §七", "## §八"]))
            (d / "phase3-part4.md").write_text(_make_part(4, ["## §九", "## §十 ", "## §十一"]))
            (d / "phase3-part5.md").write_text(_make_part(5, ["## §十二", "## §十三", "## §十四", "## §十五"]))
            out = d / "final.md"
            ret = assemble_report.assemble("TestCo", "2026-04-27", d, out)
            self.assertEqual(ret, 1, "缺章节应返回 1")


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (TestValidatePart, TestExtractMetadataBlocks, TestAssembleEndToEnd):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
