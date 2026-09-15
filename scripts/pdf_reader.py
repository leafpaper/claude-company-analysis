"""PDF reader for annual / quarterly reports.

Design:
- Download PDFs from URLs (cninfo.com.cn for A-shares, hkex for HK, SEC for US).
- Extract text page-by-page using pypdf.
- Section-level extraction using regex patterns tuned for CN reports:
    * 主要会计数据和财务指标
    * 资产负债表项目变动（含"变动原因"）
    * 利润表项目变动（含"变动原因"——关键！）
    * 现金流量表项目变动
    * 管理层讨论与分析 / 经营情况讨论
    * 主要控股参股公司
    * 风险因素
    * 前十大股东
    * 非经常性损益项目

Usage:
    from scripts.pdf_reader import PDFReader
    r = PDFReader()
    p = r.download("http://cninfo.com.cn/.../xxx.PDF", "output/.../raw_data/pdfs/q3_2025.pdf")
    sections = r.extract_sections(p)
    print(sections["income_change_reasons"])  # 原文
    hits = r.search(p, r"超隆光电")           # 关键词定位

CLI:
    python3 -m scripts.pdf_reader path/to/report.pdf [--section income]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Iterable

import pypdf
import requests

# ---- A-share report section heading patterns ----
# 每个 section 对应 (regex 开始标识, 候选结束标识列表, 含义描述)
# 标题在**目录页**同样会命中, 抓到的却只是一行目录条目 —— 华特(科创板)实测 mda 判 found=true,
# 而 text 只有 595 / 181 字、start_page=2。所以每个候选起点都算一遍长度, 取第一个够长的;
# 全都太短 = 这份 PDF 里它只在目录里出现过, 判未找到。
MIN_SECTION_CHARS = 500

SECTION_PATTERNS: dict[str, dict] = {
    "main_financial_data": {
        # SSE(科创板)标题带章节序号与「近三年」前缀:「六、近三年主要会计数据和财务指标 → (一) 主要会计数据」,
        # 深市模板的 `一、` 锚点直接失配(华特实测 9 段只命中 5 段, 缺的都是「披露了、只是标题不同」)
        "start": (
            r"一、?\s*主要财务数据"
            r"|[一二三四五六七八九十]+、?\s*(?:近三年)?主要会计数据和财务指标"
            r"|(?:近三年)?主要会计数据及财务指标"
            r"|（一）\s*主要会计数据"
        ),
        "end": [
            r"二、?\s*股东信息", r"非经常性损益项目和金额",
            r"二、?\s*股东人数", r"资产负债表项目变动",
        ],
        "desc": "核心财务数据表",
    },
    "non_recurring_items": {
        "start": r"非经常性损益项目和金额|非经常性损益",
        "end": [
            r"主要会计数据和财务指标发生变动", r"变动的情况及原因",
            r"资产负债表项目变动",
        ],
        "desc": "非经常性损益明细",
    },
    "balance_sheet_changes": {
        "start": r"(?:1\s*、|1\s*\.)\s*资产负债表项目变动|资产负债表项目变动的原因",
        "end": [
            r"(?:2\s*、|2\s*\.)\s*利润表项目变动",
            r"利润表项目变动的原因",
        ],
        "desc": "资产负债表项目变动（含变动原因）",
    },
    "income_statement_changes": {
        "start": r"(?:2\s*、|2\s*\.)\s*利润表项目变动|利润表项目变动的原因",
        "end": [
            r"(?:3\s*、|3\s*\.)\s*现金流量表项目变动",
            r"现金流量表项目变动的原因",
            r"二、?\s*股东信息",
        ],
        "desc": "★ 利润表项目变动（含关键'变动原因'说明 — Q3 亏损归因在此）",
    },
    "cashflow_changes": {
        "start": r"(?:3\s*、|3\s*\.)\s*现金流量表项目变动|现金流量表项目变动的原因",
        "end": [
            r"二、?\s*股东信息",
            r"二、?\s*股东人数",
            r"三、?\s*其他重要事项",
        ],
        "desc": "现金流量表项目变动",
    },
    # ---- 以下三段是 SSE(科创板)模板专属, 深市模板没有对应标题 ----
    "sse_statement_changes": {
        # SSE 年报把利润表与现金流量表的科目变动**合并成一张表**;半年报连「利润表」三个字都没有,
        # 叫「1、财务报表相关科目变动分析表」。上面三段深市模式在科创板报告上全部落空。
        "start": (
            r"(?:\d\s*、|\d\s*\.)?\s*利润表及现金流量表相关科目变动分析表"
            r"|(?:\d\s*、|\d\s*\.)?\s*财务报表相关科目变动分析表"
        ),
        "end": [
            r"（[二三四五六]）\s*非主营业务", r"（[二三四五六]）\s*资产、负债情况",
            r"资产、负债情况分析", r"二、?\s*股东信息",
        ],
        "desc": "★ SSE 合并的科目变动分析表(利润表+现金流量表;半年报为三表合并)",
    },
    "sse_rd_investment": {
        # 科创板专属两表:「3、研发投入情况表」+「4、在研项目情况」(第三节 → 三、核心竞争力分析下)
        "start": r"(?:\d\s*、|\d\s*\.)?\s*研发投入情况表",
        "end": [
            r"（[五六七]）\s*报告期内核心技术人员变动", r"核心技术人员变动",
            r"四、?\s*报告期内主要经营情况", r"第四节",
        ],
        "desc": "★ 科创板研发投入情况表 + 在研项目情况(研发强度与在研项目进展)",
    },
    "sse_raised_funds": {
        "start": r"[一二三四五六七八九十]+、?\s*募集资金使用进展说明|募集资金使用情况对照表",
        "end": [
            r"[一二三四五六七八九十]+、?\s*重大资产和股权出售", r"第[六七八]节", r"公司治理",
        ],
        "desc": "★ 科创板募集资金使用进展(募投项目投入进度与效益)",
    },
    "mda": {
        "start": r"管理层讨论与分析|经营情况讨论与分析|报告期内公司所处行业情况",
        "end": [
            r"公司治理", r"重要事项", r"股份变动及股东情况",
        ],
        "desc": "管理层讨论与分析（MD&A）",
    },
    "subsidiaries": {
        "start": r"主要控股参股公司|主要子公司及对公司净利润影响达|主要境外资产情况",
        "end": [
            r"报告期内取得和处置子公司",
            r"公司控制的结构化主体情况",
            r"公司面临的风险",
            r"十、?\s*公司面临",
        ],
        "desc": "主要子公司 / 参股公司业绩表",
    },
    "risks": {
        "start": r"公司面临的风险和应对措施|公司面临的风险|风险因素",
        "end": [
            r"市值管理制度", r"质量回报双提升",
            r"第四节", r"公司治理",
        ],
        "desc": "风险因素披露",
    },
    "top10_holders": {
        "start": r"前\s*10?\s*名股东持股情况|前十名股东持股情况",
        "end": [
            r"前\s*10?\s*名无限售条件股东",
            r"优先股股东",
            r"三、?\s*其他重要事项",
        ],
        "desc": "前十大股东（季报/年报披露）",
    },
}


class PDFReader:
    """Read A-share / HK / US report PDFs with section-level extraction."""

    def __init__(self, timeout: int = 60):
        self._timeout = timeout

    # ---- download ----

    def download(self, url: str, out_path: str | Path) -> Path:
        """Download a PDF from a URL to local path. Returns the Path."""
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists() and out_path.stat().st_size > 1024:
            return out_path  # assume cached
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0 Safari/537.36",
            "Accept": "application/pdf,*/*",
        }
        resp = requests.get(url, headers=headers, timeout=self._timeout, stream=True)
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return out_path

    # ---- extraction ----

    def extract_text(self, pdf_path: str | Path, pages: Iterable[int] | None = None) -> list[str]:
        """Return list[str] where element i = page i+1 text. If pages given, only extract those."""
        pdf_path = Path(pdf_path)
        reader = pypdf.PdfReader(str(pdf_path))
        n = len(reader.pages)
        idxs = list(pages) if pages is not None else list(range(n))
        texts: list[str] = []
        for i in idxs:
            if i >= n:
                texts.append("")
                continue
            try:
                texts.append(reader.pages[i].extract_text() or "")
            except Exception:  # noqa: BLE001
                texts.append("")
        return texts

    def full_text(self, pdf_path: str | Path) -> str:
        """Return concatenated text with page markers."""
        pages = self.extract_text(pdf_path)
        return "\n".join(f"\n===== PAGE {i + 1} =====\n{t}" for i, t in enumerate(pages))

    def extract_sections(self, pdf_path: str | Path) -> dict[str, dict]:
        """Extract known sections from the PDF. Returns dict keyed by section id.

        Each value:
            {
              "desc": str,
              "found": bool,
              "start_page": int | None,
              "end_page": int | None,
              "text": str,   # extracted text (empty if not found)
            }
        """
        pages = self.extract_text(pdf_path)
        full = "\n".join(f"__PAGE_{i + 1}__\n{t}" for i, t in enumerate(pages))
        out: dict[str, dict] = {}

        for sec_id, conf in SECTION_PATTERNS.items():
            start_re = re.compile(conf["start"])
            candidates = list(start_re.finditer(full))
            if not candidates:
                out[sec_id] = {"desc": conf["desc"], "found": False, "start_page": None, "end_page": None, "text": ""}
                continue

            payload = None      # 第一个够长的候选
            longest = None      # 兜底:全都太短时留最长的那段供人工核
            for m_start in candidates:
                start_pos = m_start.start()
                # find end (first of candidates after start)
                end_positions = []
                for end_pat in conf["end"]:
                    m_end = re.compile(end_pat).search(full, pos=m_start.end())
                    if m_end:
                        end_positions.append(m_end.start())
                end_pos = min(end_positions) if end_positions else min(start_pos + 8000, len(full))

                snippet = full[start_pos:end_pos]

                # figure out start/end page from __PAGE_N__ markers
                start_page = self._find_page(full, start_pos)
                end_page = self._find_page(full, max(end_pos - 1, start_pos))

                # strip __PAGE_N__ markers from snippet but keep annotations
                snippet_clean = re.sub(r"__PAGE_(\d+)__", lambda m: f"\n[P.{m.group(1)}] ", snippet).strip()

                cand = {
                    "desc": conf["desc"],
                    "found": True,
                    "start_page": start_page,
                    "end_page": end_page,
                    "text": snippet_clean,
                }
                if len(snippet_clean) >= MIN_SECTION_CHARS:
                    payload = cand
                    break
                if longest is None or len(snippet_clean) > len(longest["text"]):
                    longest = cand

            if payload is None:
                # 所有候选都短得不像正文 —— 多半只在目录页命中。判未找到, 但把最长的那段留着,
                # 并在 desc 里说明, 免得下游把「没抓到」读成「公司没披露」(华特实测踩到的正是这一条)。
                payload = dict(
                    longest,
                    found=False,
                    desc=f"{conf['desc']}(只命中疑似目录页, 正文未抓到)",
                )

            out[sec_id] = payload

        return out

    @staticmethod
    def _find_page(full: str, pos: int) -> int:
        """Given position in the full-text with __PAGE_N__ markers, return page number (1-indexed)."""
        sub = full[:pos]
        pages = re.findall(r"__PAGE_(\d+)__", sub)
        if not pages:
            return 1
        return int(pages[-1])

    def search(self, pdf_path: str | Path, pattern: str, flags: int = re.IGNORECASE) -> list[dict]:
        """Full-text regex search. Returns list of {page, line, snippet}."""
        pages = self.extract_text(pdf_path)
        hits: list[dict] = []
        rx = re.compile(pattern, flags)
        for i, text in enumerate(pages):
            for line_no, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    hits.append({
                        "page": i + 1,
                        "line": line_no,
                        "snippet": line.strip()[:300],
                    })
        return hits


# ---- CLI ----

def _download_dir(explicit: str | None, out_json: str | None) -> Path:
    """URL 下载落哪儿。

    `Path("/tmp")` 在 Windows 上会解析成**盘根的 `C:\\tmp`** —— PDF 全跑到那里去,
    而采集产物在 `output/{company}/raw_data/`, 下次复查根本找不到原件(华特实测)。
    默认跟着 `--out` 走:`raw_data/pdf_sections_X.json` → `raw_data/pdfs/`。
    """
    if explicit:
        return Path(explicit)
    if out_json:
        return Path(out_json).parent / "pdfs"
    return Path(tempfile.gettempdir())


def main():
    for stream in (sys.stdout, sys.stderr):      # Windows 控制台 GBK 下 print emoji 会炸
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    ap = argparse.ArgumentParser(description="Read a financial report PDF.")
    ap.add_argument("pdf_path", help="Path or URL to PDF")
    ap.add_argument("--section", default=None,
                    help=f"Extract a single section. Choices: {','.join(SECTION_PATTERNS)}")
    ap.add_argument("--search", default=None, help="Regex to search in full text")
    ap.add_argument("--all-sections", action="store_true", help="Extract all known sections")
    ap.add_argument("--out", default=None, help="If given, dump extracted sections to this JSON path")
    ap.add_argument("--download-dir", default=None,
                    help="URL 下载落盘目录(默认跟着 --out 放到 raw_data/pdfs/, 没有 --out 才用系统临时目录)")
    args = ap.parse_args()

    r = PDFReader()

    # download if URL
    p = args.pdf_path
    if p.startswith("http://") or p.startswith("https://"):
        dl_dir = _download_dir(args.download_dir, args.out)
        dl_dir.mkdir(parents=True, exist_ok=True)
        p = r.download(p, dl_dir / Path(p).name)
        print(f"Downloaded to {p}", file=sys.stderr)

    if args.search:
        hits = r.search(p, args.search)
        for h in hits[:50]:
            print(f"[P.{h['page']}:L{h['line']}] {h['snippet']}")
        if len(hits) > 50:
            print(f"... ({len(hits) - 50} more)", file=sys.stderr)
        return

    if args.section:
        if args.section not in SECTION_PATTERNS:
            print(f"Unknown section. Choices: {list(SECTION_PATTERNS)}", file=sys.stderr)
            sys.exit(2)
        sections = r.extract_sections(p)
        s = sections[args.section]
        print(f"# {s['desc']}")
        print(f"found: {s['found']}  pages: {s['start_page']}-{s['end_page']}\n")
        print(s["text"])
        return

    if args.all_sections or args.out:
        sections = r.extract_sections(p)
        if args.out:
            Path(args.out).write_text(json.dumps(sections, ensure_ascii=False, indent=2))
            print(f"Saved sections to {args.out}")
        else:
            for sec_id, info in sections.items():
                marker = "✅" if info["found"] else "❌"
                pg = f"P.{info['start_page']}-{info['end_page']}" if info["found"] else "(not found)"
                print(f"{marker} {sec_id:28s} {pg}  — {info['desc']}")
        return

    # default: page count + length summary
    pages = r.extract_text(p)
    total_chars = sum(len(t) for t in pages)
    print(f"{len(pages)} pages, {total_chars} chars total")
    for i, t in enumerate(pages[:3]):
        print(f"\n--- Page {i + 1} preview ---")
        print(t[:500])


if __name__ == "__main__":
    main()
