---
name: company-analysis
description: "投资分析技能 v4.6（PDF+Tushare+量化监控+大厂风格 HTML+主页动态联动）。支持 A 股/美股/港股。使用 /company-analysis <公司名称> 启动 6 阶段投资分析，或 /company-analysis <公司> --monitor 触发量化监控。"
argument-hint: <company-name> [--monitor]
---

# 🎯 投资分析协调器 v4.6

## 你是谁？你的职责是什么？

**你是项目经理，不是执行者。** 协调 6 阶段流水线 + 可选量化监控，但不亲自做数据采集或分析。

- ✅ 路由输入 → 确认 `{company}`/`{type}`/`{market}`/`{ticker}`
- ✅ 环境自检 → 运行 `python3 -m scripts.check_env`
- ✅ 按顺序调度 Phase 1→2→3→4→5→6（v4 新顺序！差异化洞察在最后）
- ✅ 每阶段结束检查质量门控
- ✅ 处理异常（Tushare 失败 / PDF 下载失败 / 降级标注）
- ✅ 识别监控模式（`--monitor` 参数 或 用户说"监控/复查"）→ 跳转到 Phase 7

---

## 📊 6+1 阶段流水线

```
    Step 0-2 （环境+确认+建目录）
        ↓
    ╔═══════════════════════════════════════════════╗
    ║ Phase 1 数据采集                              ║
    ║ ─────────────────────────                     ║
    ║ 输入: {ticker}, {market}                      ║
    ║ 动作: tushare/yfinance/hk collector +         ║
    ║       PDF 下载解析 + derived_metrics          ║
    ║ 输出: raw_data/*.parquet, pdfs/*.pdf,         ║
    ║       pdf_sections_*.json, metrics.json,      ║
    ║       phase1-data.md                          ║
    ║ 门控: _manifest 核心 4 bundle 不空 / PDF ≥1 / ║
    ║       §11 缺口 ≥3 条                          ║
    ╚═══════════════════════════════════════════════╝
        ↓
    ╔═══════════════════════════════════════════════╗
    ║ Phase 2 文档精析                              ║
    ║ ─────────────────────────                     ║
    ║ 输入: Phase 1 的 PDF + pdf_sections JSON      ║
    ║ 动作: 精读利润表变动原因 / 子公司业绩 /        ║
    ║       MD&A / 风险因素 / 非经常性损益          ║
    ║ 输出: phase2-documents.md                     ║
    ║ 门控: §2 利润表变动 ≥3 行原文引用             ║
    ╚═══════════════════════════════════════════════╝
        ↓
    ╔═══════════════════════════════════════════════╗
    ║ Phase 3 综合分析与报告                        ║
    ║ ─────────────────────────                     ║
    ║ 输入: Phase 1 + Phase 2                       ║
    ║ 动作: 10 维度评分 / DCF+可比估值 / 4 框架定性 ║
    ║ 输出: {company}-analysis-{date}.md（初版，    ║
    ║       §十二 "差异化洞察" 和 §十二.5 "多角色结 ║
    ║       论"留白待 Phase 4/5 回写）              ║
    ║ 门控: 14 章节齐全 / 10 维度评分 / 4 框架      ║
    ╚═══════════════════════════════════════════════╝
        ↓
    ╔═══════════════════════════════════════════════╗
    ║ Phase 4 多角色投资结论                        ║
    ║ ─────────────────────────                     ║
    ║ 输入: Phase 3 主报告                          ║
    ║ 动作: 2-3 位投资人角色独立分析 + 识别分歧     ║
    ║ 输出: phase4-personas.md + 回写主报告 §十二.5 ║
    ║ 门控: ≥2 角色 / 至少 1 条显著分歧             ║
    ╚═══════════════════════════════════════════════╝
        ↓
    ╔═══════════════════════════════════════════════╗
    ║ Phase 5 差异化洞察                            ║
    ║ ─────────────────────────                     ║
    ║ 输入: Phase 1 数据 + Phase 2 PDF +            ║
    ║       Phase 3 画像 + audit_report 红旗 +      ║
    ║       Phase 4 角色分歧                        ║
    ║ 动作: 基于完整画像提炼非共识；每条有数学推导 ║
    ║ 输出: 主报告 §十二（9 字段卡片） +            ║
    ║       phase5-variant-perception.md 深度附件   ║
    ║       (Level C / 议题感知 / 共识映射)         ║
    ║ 门控: 9 字段齐全 / 信号强度三合一（Level A    ║
    ║       / 置信度 / 时间窗）/ Level A/B ∈ [3,7]  ║
    ╚═══════════════════════════════════════════════╝
        ↓
    ╔═══════════════════════════════════════════════╗
    ║ Phase 6 审核与发布                            ║
    ║ ─────────────────────────                     ║
    ║ 输入: 所有上游产出                            ║
    ║ 动作: 18 项审核 + Part D 缺口补查 + HTML +    ║
    ║       GitHub Pages                            ║
    ║ 输出: *.html / phase6-review-log.md /         ║
    ║       更新 leafpaper/Inves-Report             ║
    ║ 门控: 全部 18 项通过 / 每缺口有结果           ║
    ╚═══════════════════════════════════════════════╝

    [可选 - 手动触发] ↓
    ╔═══════════════════════════════════════════════╗
    ║ Phase 7 量化监控 ★v4 新增                     ║
    ║ ─────────────────────────                     ║
    ║ 触发: /company-analysis <公司> --monitor 或   ║
    ║       用户说"监控/更新/复查"                  ║
    ║ 输入: 最近一次分析报告 + 新的 Tushare/PDF     ║
    ║ 动作: 对比基线指标 / 扫描 Phase 5 证伪条件 /  ║
    ║       识别业绩预告变化                        ║
    ║ 输出: monitor_{company}_{date}.md             ║
    ║       给出"维持/复评/重大修订"结论            ║
    ╚═══════════════════════════════════════════════╝
```

---

## 📖 快速导航

| 我想... | 去哪 |
|--------|------|
| 看 6+1 阶段流程图 | ↑ 上面 |
| 执行 Phase N | 加载 `phases/phaseN-*.md` |
| 量化监控（新） | 加载 `phases/phase7-quantitative-monitor.md` |
| 查看质量门控 | 见每个 Phase 的说明（下方） |
| 处理异常 | 见下方"异常处理" |
| 数据层说明 | `scripts/README.md` |
| **报告骨架(v4.3 强制)** | **`assets/templates/report-skeleton.md`** |
| **Exec Summary 字段 schema(v4.3)** | **`assets/templates/exec-summary-schema.md`** |
| **HTML 骨架(v4.3)** | **`assets/html/base.html` + `styles.css` + `components.html`** |
| 审核清单 JSON | `assets/validation/report-checklist.json` |
| 评分标准 | `references/scoring-rubric.md` |
| 3 框架定性（v4.1） | `references/qualitative-frameworks.md` |
| 估值框架 | `references/valuation-frameworks.md` |
| HTML 设计哲学(说明) | `references/html-template-guide.md` |

---

## Step 0: 环境自检（v3 起必执行）

```bash
cd /Users/leafpaper/.claude/plugins/company-analysis/skills/company-analysis
python3 -m scripts.check_env
```

**通过标准**: 依赖全部 `[OK]`、`TUSHARE_TOKEN set`（A 股/港股必需；美股可略）。

不通过则停止，告诉用户具体修复命令（`pip3 install` / `export TUSHARE_TOKEN=xxx`）。

---

## Step 1: 解析输入 + 识别模式（v4 新增 monitor 分支）

### 1.1 识别运行模式

检查 `$ARGUMENTS`：

- **若包含 `--monitor` 或用户明确说"监控/更新/复查"** → **进入 Phase 7 监控模式**
  - 跳过下方 Step 1.2 ~ Step 3 的正常流程
  - 直接加载 `phases/phase7-quantitative-monitor.md`
- **其余情况** → 正常 6 阶段流水线（下方 Step 1.2）

### 1.2 正常流水线的输入确认

1. 从 `$ARGUMENTS` 解析公司名
2. 若用户附带文档，记录
3. 向用户确认：

> 开始分析 **{company}** 前请确认：
> 1. 公司类型：创业公司 / 上市公司
> 2. 市场：A 股 / 美股 / 港股 / 不适用
> 3. 股票代码：如 `002862` / `AAPL` / `0700.HK`
> 4. 你有内部资料吗？（可选，Phase 1 会自动下载公开 PDF）
> 5. 投资金额（默认 100 万元人民币）
> 6. 特别关注（可选，作为 Phase 5 的 additive 输入）

4. 锁定变量：`{company}`/`{type}`/`{market}`/`{ticker}`/`{documents}`/`{amount}`/`{focus_points}`

---

## Step 2: 创建输出目录

```bash
mkdir -p output/{company}/raw_data/pdfs
```

`output/{company}/` 下 artefacts：
- `raw_data/*.parquet` — Tushare/yfinance 结构化数据
- `raw_data/pdfs/*.pdf` — 下载的财报 PDF
- `raw_data/pdf_sections_*.json` — PDF 关键段落提取
- `raw_data/metrics.json` — 衍生指标
- `phase1-data.md` / `phase2-documents.md`
- `{company}-analysis-{date}.md` / `.html`（主报告）
- `phase4-personas.md`（Phase 4 工作文件）
- `phase5-variant-perception.md`（Phase 5 工作文件）
- `phase6-review-log.md`（Phase 6 审核日志）
- `monitor_{company}_{date}.md`（可选，Phase 7 生成）

---

## Step 3: 执行 6 阶段流水线（v5.0 — 关键 phase 改 sub-agent 化）

**v5.0 关键变化**:Phase 1 / Phase 4 / Phase 6 改为通过 `Agent(subagent_type)` 调用独立 sub-agent,主 agent 只做调度,不直接处理原始数据 / 长 LLM 输出。Phase 2 / 3 / 5 仍由主 agent 自己执行(已基于文件机制充分隔离)。

### 🔵 Phase 1: 数据采集 (v5.0 sub-agent 化)
**调用**:
```python
Agent(
  subagent_type: "data-collector",
  prompt: f"采集 {company} ({ticker}) 全部数据,输出至 output/{company}/。市场: {market}。"
)
```
**主 agent 收到**:仅"Phase 1 完成报告"(artifact 路径列表 + 各 bundle 行数 + 质量门控判定),**不接触** Bash stdout / Tushare DataFrame / WebSearch 完整结果。
**质量门控**:主 agent 用 Grep `### Phase 1 完成报告` 后 `质量门控: 全部通过 ✅`,失败则中止 + 报错。

### 🔵 Phase 2: 文档精析(主 agent 自己执行)
**加载**: `phases/phase2-document-analysis.md`
**质量门控**: `§2` 利润表变动 ≥3 行原文引用;每份 PDF 都被列出

### 🟢 Phase 3: 综合分析与报告(v4.8.1 流程,主 agent 自己执行)
**加载**: `phases/phase3-analysis-report.md`
**参考**: `references/scoring-rubric.md` / `qualitative-frameworks.md`(**v4.1 — 3 框架**) / `valuation-frameworks.md` / `assets/templates/report-skeleton.md`
**v4.8.1 流程**: 3a 全量预加载 → dump → 3b 5 个 part → 3c assemble_report 拼接
**质量门控**: **15 章节齐全**(§十二/十三 可留白带注释);10 维度评分完整;**Audit 🔴/🟠 红旗全部在主报告被引用**

### 🟡 Phase 4: 多角色投资结论 (v5.0 sub-agent 化, 单 agent 内 3 角色)
**调用**:
```python
Agent(
  subagent_type: "persona-agent",
  prompt: f"读 output/{company}/{company}-analysis-{date}.md, 产 phase4-personas.md。3 角色: 巴菲特 / 拐点交易者 / ARK 长期主义。"
)
```
**主 agent 收到**:phase4-personas.md 路径 + 精简版回写片段(直接拼到主报告 §十三) + 质量门控判定。
**注**:三角色非关键决策依据,只提供观点参考。
**质量门控**:跨角色分歧 ≥ 1 条;角色独立性自检通过。

### 🟣 Phase 5: 差异化洞察(主 agent 自己执行)
**加载**: `phases/phase5-variant-perception.md`
**参考**: 输入 4 源(P1 数据 + P2 PDF + P3 画像 + P4 分歧)
**v4.1 字段**: 9 字段卡片(★数学推导 + ★信号强度 Level/置信度/时间窗 三合一)
**质量门控**: 9 字段齐全;Level A/B ∈ [3,7];回写主报告 §十二 + §一 Top 3

### 🔴 Phase 6: 审核与发布 (v5.0 加 reviewer-agent sub-agent)
**Part A**: 主 agent 跑 18 项审核清单 + Part D 缺口补查
**Part A.5 (v5.0 新)**: anti_lazy_lint 通过后调用 reviewer-agent
```python
Agent(
  subagent_type: "reviewer-agent",
  prompt: f"评审 output/{company}/{company}-analysis-{date}.md, artifacts_dir = output/{company}/"
)
```
主 agent Grep `### 总体: (PASS|FAIL)`:
- PASS → 进 Part B(HTML 生成)
- FAIL → 看修复建议, 回 Phase 3 修对应 part 文件

**Part B**: build_html.py 生成 HTML
**Part C**: 推送 GitHub Pages (Inves-Report)
**质量门控**: anti_lazy_lint 4 项 PASS + reviewer-agent 3 维度 PASS = 7/7;HTML section 数 = 15

---

## Step 4（仅 Phase 7 监控模式）: 执行量化监控

**加载**: `phases/phase7-quantitative-monitor.md`
**前置**: `output/{company}/{company}-analysis-*.md` 至少存在一份历史报告
**输出**: `monitor_{company}_{date}.md`

---

## 异常处理

| 情况 | 处理方式 |
|------|---------|
| Step 0 环境失败 | 明确告诉用户修复命令，停止流水线 |
| Phase 1 Tushare 失败 | 降级：记录原因 → 尝试 akshare → 最后 WebSearch + 标注"数据降级" |
| Phase 1 PDF 下载失败 | 尝试备用 URL（公司官网 IR），最后标注"PDF 未获取" |
| Phase 2 无 PDF 可读 | 降级模式但标注"数据源不可用，建议重跑 Phase 1" |
| Phase 3 某维度无数据 | 标记 N/A，从加权排除 |
| Phase 4 角色无分歧 | 强制第 3 位角色挑战共识；仍无则标注"单向偏差警告" |
| Phase 5 Level A/B 不足 3 条 | 降级为 1-2 条并标注"数据不足，洞察置信度降低" |
| Phase 6 GitHub push 失败 | 保存 HTML 到本地，通知用户手动上传 |
| Phase 6 缺口补查仍无结果 | 标注"信息可得性极低"，但记录 5 步尝试轨迹 |
| Phase 7 基线报告解析失败 | 告诉用户需要指定特定报告路径或重跑 Phase 1 |
| 对话 context 紧张 | 每阶段完成立即保存检查点，后续通过 Read 重载 |

---

## 参考文件索引

| 文件 | 用途 | Phase |
|------|------|:-----:|
| `scripts/check_env.py` | 环境检查 | 0 |
| `scripts/tushare_collector.py` | A 股结构化数据 | 1 / 7 |
| `scripts/us_collector.py` | 美股 yfinance | 1 / 7 |
| `scripts/hk_collector.py` | 港股混合 | 1 / 7 |
| `scripts/pdf_reader.py` | 财报 PDF 解析 | 1 / 2 / 6 |
| `scripts/derived_metrics.py` | 衍生指标计算 | 1 / 7 |
| `scripts/monitor.py` | 量化监控核心 | **7** |
| `scripts/report_parser.py` | 历史报告解析 | **7** |
| **`scripts/peer_collector.py`** ⭐v4.4 | **A 股同行业自动采集对比** | **1** |
| **`scripts/capital_flow.py`** ⭐v4.4 | **主力控盘与资金流向 (6 接口 + 6 指标)** | **1** |
| **`scripts/technical_analysis.py`** ⭐v4.4 | **MA/MACD/RSI/布林带/支撑阻力** | **1** |
| **`scripts/update_index.py`** ⭐v4.6 | **主页联动:抽 card-metadata + upsert reports.json** | **6** |
| `scripts/README.md` | 数据层说明 | 参考 |
| `phases/phase1-data-collection.md` | 数据采集指令 | 1 |
| `phases/phase2-document-analysis.md` | 文档精析指令 | 2 |
| `phases/phase3-analysis-report.md` | 综合分析指令 | 3 |
| `phases/phase4-persona-conclusions.md` | 多角色指令 | 4 |
| `phases/phase5-variant-perception.md` | 差异化洞察指令（原 2.5 后移）| 5 |
| `phases/phase6-review-publish.md` | 审核发布指令（原 5 后移）| 6 |
| `phases/phase7-quantitative-monitor.md` | 量化监控指令（新）| 7 |
| `references/scoring-rubric.md` | 10 维度评分 | 3 |
| `references/qualitative-frameworks.md` | 3 框架定性（v4.1） | 3 |
| `references/valuation-frameworks.md` | Damodaran 估值 + v4.2 SOTP 强制规则 | 3 |
| `references/search-strategy.md` | WebSearch 辅助 | 1 |
| `references/html-template-guide.md` | HTML 设计哲学(无代码,代码见 assets/html/) | 6 |
| `references/persona-registry.md` | 投资人角色库 | 4 |
| ~~`references/report-template.md`~~ | **v4.3 废弃** → `assets/templates/report-skeleton.md` | – |
| **`assets/templates/report-skeleton.md`** ⭐ | **报告 15 章节严格骨架(v4.3 Phase 3 强制加载)** | **3** |
| **`assets/templates/exec-summary-schema.md`** ⭐ | **Exec Summary 7 字段 schema(v4.3)** | **3** |
| **`assets/html/base.html`** ⭐ | **HTML 骨架 + 15 section 占位(v4.3 Phase 6 强制加载)** | **6** |
| **`assets/html/styles.css`** ⭐ | **真 CSS 文件(16 变量 + 9 组件样式)** | **6** |
| **`assets/html/components.html`** | **10 个组件片段库** | **6** |
| `assets/validation/report-checklist.json` | 机器可读的 22 项审核清单(供 v4.4 validator) | 6 |
| `assets/validation/insight-card-schema.json` | Phase 5 9 字段 schema(供 v4.4 validator) | 5 / 6 |
