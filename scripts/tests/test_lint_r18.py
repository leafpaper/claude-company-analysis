"""lint R18: 写手读的 `red_flags.json` 不能落后于 `audit_report.json`。

金山办公 688111 实测:新增红旗后重跑了 audit(06:06),而 `red_flags.json` 停在 05:37。
装配层是**直接从 audit JSON 重算**红旗的,所以成品不会漏 —— 漏的是写手作判断时看到的那份:
①质地想在面板上引「投资收益占营业利润过高」时取不到 id,那一格只能填 null。
面板哑了不影响装配、不触发任何既有规则,没有这条规则就没人会发现。

运行:
    python -m unittest scripts.tests.test_lint_r18
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import lint_v8 as L


AUDIT = [
    {"id": "buffett-quality-c95859", "level": "🟠", "title": "投资收益占营业利润过高"},
    {"id": "dupont-96a180", "level": "ℹ️", "title": "ROE 归因"},
]


def _dirs(td: str, listed: list[dict], *, filename: str = "red_flags.json") -> list[Path]:
    root = Path(td)
    (root / filename).write_text(
        json.dumps({"red_flags": listed}, ensure_ascii=False), encoding="utf-8"
    )
    return [root]


class R18Test(unittest.TestCase):

    def test_in_sync_passes(self):
        with tempfile.TemporaryDirectory() as td:
            r = L.rule_flags_in_sync(AUDIT, _dirs(td, AUDIT))
        self.assertTrue(r.passed)
        self.assertFalse(r.skipped)

    def test_stale_list_fails_and_names_the_missing_flag(self):
        with tempfile.TemporaryDirectory() as td:
            r = L.rule_flags_in_sync(AUDIT, _dirs(td, AUDIT[1:]))
        self.assertFalse(r.passed)
        self.assertIn("buffett-quality-c95859", r.findings[0])
        self.assertIn("red_flags", r.findings[0])          # 带补跑命令, 不只报错

    def test_writer_nominations_do_not_count_as_coverage(self):
        """提名是写手自己加的, 不能拿它顶替 audit 那条 —— 否则漂移会被提名掩盖。"""
        listed = [dict(AUDIT[1]), {"id": "x-1", "level": "🟠", "title": "写手提的",
                                   "source": "nomination"}]
        with tempfile.TemporaryDirectory() as td:
            r = L.rule_flags_in_sync(AUDIT, _dirs(td, listed))
        self.assertFalse(r.passed)

    def test_no_audit_flags_is_skipped_not_failed(self):
        with tempfile.TemporaryDirectory() as td:
            r = L.rule_flags_in_sync([], _dirs(td, []))
        self.assertTrue(r.skipped)

    def test_missing_file_is_skipped(self):
        """没有 red_flags.json 说明这条流水线不消费它, 不是漂移。"""
        with tempfile.TemporaryDirectory() as td:
            r = L.rule_flags_in_sync(AUDIT, [Path(td)])
        self.assertTrue(r.skipped)

    def test_broken_json_fails_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "red_flags.json").write_text("{不是 json", encoding="utf-8")
            r = L.rule_flags_in_sync(AUDIT, [Path(td)])
        self.assertFalse(r.passed)
        self.assertFalse(r.skipped)


if __name__ == "__main__":
    unittest.main()
