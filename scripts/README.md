# scripts/ — Python 数据层

为 company-analysis skill 提供**结构化金融数据**（取代纯 WebSearch）：
- **Tushare Pro** 拿 A 股三大报表 + 股权 + 估值
- **yfinance** 拿美股（及港股 fallback）
- **pypdf** 解析财报 PDF 原文（关键段落如"利润表项目变动原因"）
- **derived_metrics** 预计算 CAGR / FCF / ROE / Owner Earnings 等

LLM（Phase 1-5）只负责**分析**，不再自己去搜索和拼凑数据。

---

## 一次性配置（首次使用前）

### 1. 安装依赖

```bash
pip3 install --user tushare yfinance pypdf pandas pyarrow requests
```

### 2. 设置 Tushare Token（必需，如果要分析 A 股/港股）

注册账号：<https://tushare.pro/register>（建议申请学生权限获 5000+ 免费积分；
或购买 2000 积分解锁核心财报，约 ¥200）。

获取 token 后，写入 `~/.zshrc`：

```bash
echo 'export TUSHARE_TOKEN="your_token_here"' >> ~/.zshrc
source ~/.zshrc
```

**⚠️ Token 是私人凭证，绝不要提交到 git 仓库**（requirements.txt 里不写、任何 *.md 里也不写）。

### 3. 验证环境

```bash
cd skills/company-analysis/
python3 -m scripts.check_env
```

应该看到所有依赖 `[OK]`、`TUSHARE_TOKEN set`。

---

## 模块一览

| 模块 | 用途 | 关键类/方法 |
|------|------|-----------|
| `config` | 路径、token、速率限制 | `TUSHARE_TOKEN`, `output_dir(name)` |
| `data_cache` | 7 天 TTL Parquet 缓存 | `get(key)`, `put(key, df)` |
| `check_env` | 环境检查 CLI | `python3 -m scripts.check_env` |
| `tushare_collector` | A 股数据 | `TushareCollector().collect_all("002862.SZ")` |
| `us_collector` | 美股数据（yfinance） | `USCollector().collect_all("AAPL")` |
| `hk_collector` | 港股混合（Tushare + yfinance） | `HKCollector().collect_all("0700.HK")` |
| `pdf_reader` | 财报 PDF 原文解析 | `PDFReader().extract_sections(pdf_path)` |
| `derived_metrics` | 衍生指标计算 | `compute_a_share(bundle)` / `compute_us(bundle)` |

---

## 典型使用

### A 股：实丰文化 002862

```bash
# 1. 拉取财报 bundle（自动缓存 7 天）
python3 -m scripts.tushare_collector 002862 --name 实丰文化

# 2. 下载年报/季报 PDF 并提取关键段落
python3 -m scripts.pdf_reader \
  http://static.cninfo.com.cn/finalpage/2025-10-28/1224744018.PDF \
  --all-sections --out output/实丰文化/raw_data/pdf_sections.json

# 3. 计算衍生指标
python3 -m scripts.derived_metrics output/实丰文化/raw_data/
# 生成 output/实丰文化/metrics.json
```

输出结构：
```
output/实丰文化/
├── raw_data/
│   ├── income.parquet                    # 利润表（多年）
│   ├── balancesheet.parquet              # 资产负债表
│   ├── cashflow.parquet                  # 现金流表
│   ├── fina_indicator.parquet            # PE/PB/ROE 等
│   ├── top10_holders.parquet             # 前十大股东
│   ├── pledge_detail.parquet             # 股权质押
│   ├── daily_basic.parquet               # 每日基本面（PE/PB）
│   ├── daily.parquet                     # 日线价格
│   ├── fina_mainbz.parquet               # 分业务（可能为空）
│   ├── dividend.parquet                  # 分红
│   ├── stock_basic.parquet               # 公司基本信息
│   ├── _manifest.json                    # bundle 清单
│   ├── pdf_sections.json                 # PDF 关键段落（来自 pdf_reader）
│   └── pdfs/
│       ├── annual_2024.pdf
│       └── q3_2025.pdf
└── metrics.json                          # 衍生指标
```

### 美股：Apple

```bash
python3 -m scripts.us_collector AAPL --name Apple
python3 -m scripts.derived_metrics output/Apple/raw_data/ --market us
```

### 港股：腾讯 0700

```bash
python3 -m scripts.hk_collector 0700 --name 腾讯控股
python3 -m scripts.derived_metrics output/腾讯控股/raw_data/ --market hk
```

---

## Python API（供 Phase 1 直接调用）

```python
from scripts.tushare_collector import TushareCollector, normalize_a_code
from scripts.pdf_reader import PDFReader
from scripts.derived_metrics import compute_a_share

ts_code = normalize_a_code("002862")  # → '002862.SZ'

collector = TushareCollector()
bundle = collector.collect_all(ts_code, start_year=2022)

reader = PDFReader()
pdf_path = reader.download(report_url, "output/实丰文化/raw_data/pdfs/q3.pdf")
sections = reader.extract_sections(pdf_path)
# sections["income_statement_changes"]["text"] → 关键的"变动原因"原文

metrics = compute_a_share(bundle)
```

---

## 缓存管理

- 位置：`~/.claude/plugins/company-analysis/.cache/`（可通过 `COMPANY_ANALYSIS_CACHE` 环境变量覆盖）
- TTL：7 天（`COMPANY_ANALYSIS_CACHE_TTL` 可覆盖）
- 清理：`rm -rf ~/.claude/plugins/company-analysis/.cache/*.parquet*`

---

## 速率限制与重试

- Tushare：每次调用间隔 ≥ 500ms，失败时指数退避（最多 5 次）
- yfinance：每次 ≥ 300ms

如果积分不足或接口权限不够，具体 API 会抛 `RuntimeError`，外层 `collect_all` 会用 try/except 兜底（`fina_mainbz` / `dividend` 等可选接口即使失败也返回空 DataFrame）。

---

## 局限性（参考 plan 中的 fallback 策略）

| 场景 | 局限 | 缓解 |
|------|------|------|
| Tushare 积分不足 | 核心 3 大报表需 2000 积分 | 用学生权限或付费 ¥200 |
| 分业务数据（`fina_mainbz`）缺失 | 部分公司不披露 | 从 PDF 原文提取 |
| MD&A 原文 | Tushare 没有，需读 PDF | `pdf_reader.extract_sections()` |
| 美股股息历史 | yfinance 有时不全 | 用 SEC EDGAR 补充（未实现） |

---

## 未来扩展

- [ ] `screener.py`：批量筛选（参考 Turtle Framework 的二层筛选）
- [ ] `sec_edgar.py`：美股 10-K/10-Q XBRL 结构化解析
- [ ] `hkex_reader.py`：港交所披露易 PDF 批量下载
- [ ] `akshare_fallback.py`：Tushare 不可用时的免费备选
