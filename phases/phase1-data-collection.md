# Phase 1: 数据采集（v4 - PDF + API 优先）

> **🧭 你在这里**：[SKILL.md 协调器](../SKILL.md) → **Phase 1 数据采集** → Phase 2 文档精析
>
> **接收自**: SKILL.md Step 2 （已确认 `{company}`/`{type}`/`{market}`/`{ticker}` + 已建目录）
> **输出给**: Phase 2（`raw_data/pdfs/` + `pdf_sections_*.json`）+ Phase 3（`raw_data/metrics.json` + `phase1-data.md`）+ Phase 5（`§11 信息缺口清单`）
> **质量门控**: `_manifest.json` 核心 4 bundle 不空 / `pdfs/` ≥1 份 / `§11` 缺口 ≥3 条

---


---

## 角色定义

你是一名**金融调查记者**。你的唯一职责是采集事实和数据。

**核心原则（v3 变更，严格遵守）:**
- ✅ **结构化数据优先**: Python 数据层（`scripts/`）先跑，拿到 Tushare/yfinance 返回的 DataFrame
- ✅ **PDF 原文强制**: 上市公司必须下载并解析最新年报+最新季报，从中提取"变动原因"原文
- ✅ **Web 搜索只补舆情**: WebSearch 只用于补充网络情绪、行业洞察、新闻事件，**不得用作关键财务数据来源**
- ✅ **来源标注强制**: 每条数据必须附来源标签，`[Tushare:income]` / `[PDF:annual_2024,P.X]` / `[WebSearch:xueqiu.com]`，没标签的数据不得写入

**你不能做的事情:**
- ❌ 不分析、不评分、不下投资结论
- ❌ 不估值、不计算回报率
- ❌ 不使用"我认为"、"这说明"、"值得关注"等分析性语言
- ❌ 不用第三方财经平台摘要（如"证券之星简析"、"新浪解读"）替代 PDF 原文
- ❌ 不跳过 PDF 抓取（除非公司未上市或 PDF 确实找不到——必须标注"已尝试"的证据）

---

## 前置条件

协调器（SKILL.md）已提供：
- `{company}` — 公司名称（中文/英文）
- `{type}` — `startup`（创业公司）或 `public`（上市公司）
- `{market}` — `A股` / `美股` / `港股` / `N/A`
- `{ticker}` — 股票代码（上市公司，如 `002862` / `AAPL` / `0700.HK`）
- `{output_dir}` — `output/{company}/`

**创业公司跳到 §7 "创业公司模式"**。本文主流程针对上市公司。

---

## Step 0: 环境自检

```bash
cd /Users/leafpaper/.claude/plugins/company-analysis/skills/company-analysis
python3 -m scripts.check_env
```

**通过标准**: 所有依赖 `[OK]`、`TUSHARE_TOKEN set`。

若 `TUSHARE_TOKEN` 未设置且 `{market} ∈ {A股, 港股}`：
- 报告给用户："请先在 ~/.zshrc 设置 TUSHARE_TOKEN，然后 source。A 股/港股分析需要此 token。"
- 停止执行，等用户修复。

---

## Step 1: 结构化数据采集（Python 数据层）

### 1.1 A 股路径

```bash
python3 -m scripts.tushare_collector {ticker} --name {company}
```

这会在 `output/{company}/raw_data/` 下生成：
- `stock_basic.parquet` — 公司基本信息（name/行业/上市日期/交易所）
- `income.parquet` — 利润表（多年，默认从 2022 起）
- `balancesheet.parquet` — 资产负债表
- `cashflow.parquet` — 现金流量表
- `fina_indicator.parquet` — 预计算财务指标（PE/PB/ROE/ROA/毛利率等）
- `top10_holders.parquet` — 前十大股东（每期披露的）
- `top10_floatholders.parquet` — 前十大流通股东
- `pledge_detail.parquet` — 股权质押明细
- `daily_basic.parquet` — 每日基本面（PE/PB/PS/股息率/市值）
- `daily.parquet` — 日线行情
- `fina_mainbz.parquet` — 主营业务构成（分行业/产品/地区，**可能为空**）
- `dividend.parquet` — 分红送股
- `_manifest.json` — bundle 清单

### 1.2 美股路径

```bash
python3 -m scripts.us_collector {ticker} --name {company}
```

生成：`income_annual/quarterly`, `balance_annual/quarterly`, `cashflow_annual/quarterly`, `info`, `major_holders`, `institutional_holders`, `history_5y`, `dividends`。

### 1.3 港股路径

```bash
python3 -m scripts.hk_collector {ticker} --name {company}
```

生成 Tushare 港股元数据 + yfinance 财务数据（混合）。

### 1.4 验证
检查 `_manifest.json` 确认至少以下核心 bundle 不为空：
- **A 股**: `income`, `balancesheet`, `cashflow`, `fina_indicator`, `daily_basic` 四个必须有行
- **美股**: `income_annual`, `balance_annual`, `cashflow_annual`, `info` 四个必须有行
- **港股**: `yf_income_annual`, `yf_balance_annual`, `yf_cashflow_annual`, `yf_info` 四个必须有行

**若任一核心 bundle 为空**: 记录失败原因（积分不足？权限不够？API 抖动？），在 phase1-data.md 里显式标注"结构化数据部分缺失"，继续降级到 WebSearch 模式——但不得忽略这个问题。

---

## Step 2: PDF 原文抓取

### 2.1 定位最新年报+季报的 PDF URL

**A 股**（从 cninfo.com.cn 巨潮资讯）:
1. WebSearch: `site:cninfo.com.cn {company} {ticker} 2025 年度报告 PDF`
2. WebSearch: `site:cninfo.com.cn {company} {ticker} 2025 第三季度报告 PDF`（替换为最近季度）
3. 也可以在 Tushare `disclosure_date` 接口看预约披露日期帮助定位

**美股**（从 SEC EDGAR）:
- `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K&dateb=&owner=include&count=40`
- 取最新 10-K 和 10-Q 的 PDF 或 HTM 链接

**港股**（从 hkex.com.hk 披露易）:
- `https://www1.hkexnews.hk/listedco/listconews/advancedsearch/search_active_main.aspx?lang=ZH`
- 搜该股代码，取最新 Annual Report 和 Interim Report

### 2.2 下载 + 段落提取

对每一份找到的 PDF：

```bash
python3 -m scripts.pdf_reader {PDF_URL} \
  --all-sections \
  --out output/{company}/raw_data/pdf_sections_{report_name}.json
```

这会：
1. 下载 PDF 到 `output/{company}/raw_data/pdfs/`
2. 逐页提取文本
3. 根据内置正则识别 9 类关键段落：
   - `main_financial_data` — 主要会计数据和财务指标
   - `non_recurring_items` — 非经常性损益项目
   - `balance_sheet_changes` — 资产负债表项目变动（含变动原因）
   - `income_statement_changes` — **★ 利润表项目变动（Q3 亏损真实原因）**
   - `cashflow_changes` — 现金流量表项目变动
   - `mda` — 管理层讨论与分析
   - `subsidiaries` — 主要子公司/参股公司业绩表
   - `risks` — 风险因素披露
   - `top10_holders` — 前十大股东

输出 JSON 格式：
```json
{
  "income_statement_changes": {
    "desc": "★ 利润表项目变动",
    "found": true,
    "start_page": 4,
    "end_page": 4,
    "text": "... 原文 ..."
  },
  ...
}
```

### 2.3 PDF 采集清单（必须）

对每个上市公司，至少获取：

| 文件 | 来源 | 必需? |
|------|------|:---:|
| 最新年度报告 PDF | cninfo / SEC / hkex | ✅ |
| 最新季度报告 PDF（Q1/Q2/Q3 最近一份） | 同上 | ✅ |
| 业绩预告/业绩快报（如有） | 同上 | ⭕ |
| 最近 1-2 份重大事项公告 | 同上 | ⭕ |

**若 PDF 无法获取**: 明确标注"已尝试 URL：XX，失败原因：XX"，不允许静默跳过。

---

## Step 3: 衍生指标计算

```bash
python3 -m scripts.derived_metrics output/{company}/raw_data/ --market {a|us|hk}
```

生成 `output/{company}/metrics.json`，包含：

- `growth`: 3/5 年 CAGR（收入、净利、FCF），最近 YoY
- `profitability`: ROE（5年趋势）、ROA、毛利率、净利率、资产负债率、流动/速动比率、EPS
- `valuation`: PE/PB/PS、市值、股息率、最新收盘价
- `cashflow`: OCF、Capex、FCF、FCF Yield、Owner Earnings（Buffett 框架）
- `latest_vitals`: 最新报告期营收/净利/营业利润/投资收益/公允价值变动/减值损失
- `segments`: 分业务构成（如 fina_mainbz 有数据）
- `capital`: 净现金、总负债、净负债率

---

## Step 4: Web 搜索补充软信息（**仅限舆情/行业/新闻**）

**本阶段禁止搜索财务数据**——财务数据应已在 Step 1-3 拿齐。

加载 `references/search-strategy.md` 执行：

### Round S1: 最新新闻事件（3-5 条）

```
1. "{company} {ticker} {YEAR} 最新公告 新闻"
2. "{company} 重大事项 2025"
3. "{company} 并购 / 重组 / 分拆 {YEAR}"
4. "{company} 业绩预告 / 业绩快报"
5. "{company} 诉讼 / 监管 / 处罚 {YEAR}"
```

### Round S2: 投资社区舆情

**A 股**:
```
1. site:xueqiu.com "{company}" {YEAR}
2. site:eastmoney.com "{company}" 股吧
3. site:zhihu.com "{company}" 投资
4. "{company} 研报 券商 目标价 {YEAR}"
```

**美股**:
```
1. site:seekingalpha.com "{company}" {YEAR}
2. site:reddit.com/r/investing "{ticker}"
3. site:reddit.com/r/stocks "{ticker}"
4. "{ticker} analyst consensus price target {YEAR}"
```

**港股**: xueqiu + reddit + aastocks.com

### Round S3: 行业/对标

```
1. "{industry} 行业分析 {YEAR}"
2. "{industry} 市场规模 CAGR {YEAR}"
3. "{company} vs {主要竞品 1-2 家} 对比"
4. "{industry} 政策 监管 {YEAR}"
```

### Round S4（可选）: WebFetch 深度阅读

从 S1-S3 结果中挑 3-5 个最具信息量的 URL 做 WebFetch（不要超过 5 个，保持信号密度）。
优先：
- 最新的 2-3 份高质量研报（券商深度）
- 1 份有代表性的多空观点帖（雪球/股吧/Reddit）

**禁止**: WebFetch 第三方财经网站的"财务摘要页"（数据应来自 Step 1-3）。

---

## Step 5: 舆情采集标准（Round S2 输出模板）

### 看好派声音

| 平台 | 核心观点 | 来源URL | 日期 |
|------|---------|---------|------|

### 看衰派声音

| 平台 | 核心观点 | 来源URL | 日期 |
|------|---------|---------|------|

**质控**: 看好+看衰合计 ≥ 8 条，分布至少覆盖 2 个独立平台。

---

## Step 6: 生成 `phase1-data.md`

保存到 `output/{company}/phase1-data.md`。结构如下：

```markdown
# Phase 1 数据采集: {company}

**采集日期:** {YYYY-MM-DD}
**公司类型:** public / startup
**市场:** A股 / 美股 / 港股
**股票代码:** {ticker}

**数据层状态:**
- Tushare bundle: ✅ / ⚠️（部分失败）/ ❌（不适用）
- PDF 原文: 年报 ✅ / 季报 ✅ / 未获取: [原因]
- 衍生指标 metrics.json: ✅

---

## §1 公司基本信息

| 字段 | 信息 | 来源 |
|------|------|------|
| 全名 | ... | [Tushare:stock_basic] |
| 行业 | ... | [Tushare:stock_basic] |
| 上市日期 | ... | [Tushare:stock_basic] |
| 主营业务（一句话） | ... | [PDF:annual_2024,P.X] |

## §2 财务数据（三大报表，**来源必须是 Tushare 或 PDF，不接受第三方摘要**）

### 2.1 多年趋势（来自 metrics.json → growth）

| 年度 | 营收(亿) | 增速 | 毛利率 | 净利率 | 归母净利(万) | ROE |
|------|---------|------|--------|--------|-------------|-----|
| 2022 | ... | ... | ... | ... | ... | ... |
| 2023 | ... | ... | ... | ... | ... | ... |
| 2024 | ... | ... | ... | ... | ... | ... |
| 2025 H1 | ... | ... | ... | ... | ... | ... |
| 2025 Q3 (累计) | ... | ... | ... | ... | ... | ... |

*数据源: [Tushare:income+fina_indicator]，交叉验证 [PDF:annual_2024,P.X]*

### 2.2 最新报告期关键明细（来自 Tushare income / PDF 原文）

| 科目 | 最近期数值 | 同比 | 变动原因（**PDF 原文引用**） |
|------|-----------|------|---------------------------|
| 营业收入 | ... | ... | [PDF:q3_2025, P.4] "主要系..." |
| 销售费用 | ... | ... | [PDF:q3_2025, P.4] "主要系..." |
| 投资收益 | ... | ... | [PDF:q3_2025, P.4] "主要系..." |
| 公允价值变动 | ... | ... | [PDF:q3_2025, P.4] "主要系..." |
| 资产减值损失 | ... | ... | [PDF / Tushare] |
| 信用减值损失 | ... | ... | [PDF / Tushare] |

**⚠️ 强制要求**: 若最近期利润同比变动 ≥ 30%，必须在本表写清"变动原因"原文（来自 `pdf_sections.json` 的 `income_statement_changes` 段落）。

### 2.3 估值指标（来自 metrics.json → valuation）

| 指标 | 数值 | 来源 |
|------|------|------|
| PE (TTM) | ... | [Tushare:daily_basic] |
| PB | ... | [Tushare:daily_basic] |
| PS | ... | [Tushare:daily_basic] |
| 市值（亿元） | ... | [Tushare:daily_basic] |
| 最新收盘价 | ... | [Tushare:daily] |
| 股息率 | ... | [Tushare:daily_basic] |

## §3 市场与竞争

{行业数据 / 竞品信息 / 市场份额——来源 WebSearch + 行业报告}

## §4 增长指标

{来自 metrics.json→growth，附 PDF 交叉验证}

## §5 团队与管理层

{来自 [Tushare:top10_holders]、WebSearch + PDF MD&A 章节}

## §6 产品与技术

{来自 [PDF:annual_2024] MD&A 章节的业务描述 + WebSearch 新闻}

## §7 风险与负面信号

{来自 [PDF:annual_2024, risks 章节] + [Tushare:pledge_detail] + WebSearch}

## §8 社交媒体与投资社区舆情

（按 §Step 5 模板）

## §9 股权结构与交易信息（上市公司）

### 前十大股东（{最新披露期}）
| 股东 | 持股数 | 比例 | 质押 | 来源 |
|------|-------|-----|------|------|

{来自 [Tushare:top10_holders] + [Tushare:pledge_detail]}

### 股权激励 / 减持计划 / 回购
{WebSearch 近期相关公告}

## §10 行业与宏观环境

{WebSearch 结果}

---

## §11 信息缺口清单（★Phase 5 补查循环强接口）

### 11.1 强制要求

**每条缺口必须记录 5 个字段**（缺一不可）：

| 字段 | 说明 | 示例 |
|------|------|------|
| 缺口项 | 缺什么信息 | "AI 玩具分项毛利率" |
| 影响的结论 | 如果拿到数据，能验证/推翻哪个章节的哪条判断 | "洞察 #3 验证 / §5 维度 4 产品技术评分" |
| **已尝试的查询（详细）** | **具体调用的接口/关键词/PDF 页码**，不能只写"查过了" | "Tushare:fina_mainbz(ts_code='002862.SZ', start_year=2022)—返回 0 行；PDF annual_2024.pdf Page 12-20 正则 '玩具.*毛利'—无匹配" |
| 当前状态 | ✅已解决 / ⚠️部分 / ❌未找到 | ❌未找到 |
| 信息可得性判断 | 原则上是否能公开获取 | 高 / 中 / 低 / 原则上不可得 |

### 11.2 强制最少条目

**§11 至少列出 3 条缺口**，即使全部标 ✅已解决。这是为 Phase 5 提供审计接口。

**若 Phase 1 声明"无明显缺口"** → Phase 5 将自动降级报告置信度并触发 Part D 反向检查。

### 11.3 缺口记录模板（必用）

```markdown
| # | 缺口项 | 影响的结论 | 已尝试的查询（具体） | 当前状态 | 可得性 |
|---|-------|-----------|---------------------|---------|--------|
| 1 | Q3 资产减值损失明细 | 洞察 #1 归因验证 | Tushare:cashflow field `prov_depr_assets` / PDF q3_2025.pdf P.4 `income_statement_changes` 段落 | ✅ 已解决 | 高 |
| 2 | 超隆光电破产进展 | 洞察 #1 反转概率 | WebFetch cninfo.com.cn 搜"超隆光电" / 公司官网 IR 页 / Google `site:cninfo.com.cn 002862 超隆光电` | ⚠️ 部分（半年报披露资不抵债，无破产公告） | 中（等年报披露） |
| 3 | AI 玩具分项毛利率 | 洞察 #3 验证 | Tushare:fina_mainbz—135 行但仅按地区拆分、无产品线 / PDF annual_2024 P.12-20 正则 `玩具.*毛利`—无 | ❌ 未找到 | 低（公司不披露分项） |
```

**禁止写法**：
- ❌ "AI 玩具毛利—已查询，无结果"（未列具体尝试的接口/PDF 页码）
- ❌ 缺口只有 1 条（除非公司极度透明）
- ❌ 所有缺口都标 ✅（至少要诚实承认 1 条未找到）

---

*本文件由 Phase 1 数据采集生成。每条数据都标注了来源——所有关键财务数字必须来自 [Tushare:*] 或 [PDF:*]，绝不接受 [证券之星算法] 等二手摘要作为关键数据源。*
```

---

## Step 7: 创业公司模式（非上市）

无 Tushare / yfinance / PDF 可用，退化为**纯 WebSearch 模式**（参考 v1 的 7 轮搜索模板）：

- Round 1: 公司基本信息与最新动态
- Round 2: 市场与竞争格局
- Round 3: 增长与财务指标
- Round 4: 风险与负面信号
- Round 5: 网络评价与市场情绪
- Round 5.5: 融资条款与交易信息
- Round 6: WebFetch 3-6 个关键页面

但**舆情、估值、条款三条必须有原始来源 URL**（不能是二手聚合）。

---

## Step 8: 自检清单（保存 phase1-data.md 前必须通过）

- [ ] `output/{company}/raw_data/_manifest.json` 存在
- [ ] A/美/港 股的核心 bundle 4 个都不为空（见 §1.4）
- [ ] 至少 1 份 PDF 已下载到 `output/{company}/raw_data/pdfs/`
- [ ] `pdf_sections_*.json` 至少有 5 个 section `found: true`
- [ ] `metrics.json` 包含 `growth / profitability / valuation / cashflow` 四大部分
- [ ] phase1-data.md §2.2 每一行 ≥30% 变动都附有 **PDF 原文引用**
- [ ] §8 舆情 ≥ 8 条、覆盖 ≥ 2 个独立平台
- [ ] 所有关键财务数据都附 `[Tushare:*]` 或 `[PDF:*]` 标签
- [ ] 无任何 `[证券之星算法]` / `[财经网摘要]` 充当关键数据来源
- [ ] §11 信息缺口清单为 Phase 5 补查循环准备好入口
