# {{company_name}}（{{ticker}}）投资分析报告

**报告日期**: {{report_date}}
**报告期**: {{data_coverage}}
**最新收盘**: {{latest_close}} 元（{{latest_date}}）
**总市值**: {{market_cap}} 亿元 · PB {{pb}} · {{pe_display}}
**分析师**: Claude Opus 4.8 · Skill v{{skill_version}}

<!-- v6.0 HTML 生成锚点: 供 Phase 6 Part B 抽取以下字段填充前置评级卡 + 顶部指标条
     供 update_index.py 生成主页卡片 metadata
     LLM 写报告时务必让下列字段在正文中可找到(典型位置: §一 执行摘要 / §五 估值与回报) -->

<!-- RATING_TRIO_DATA:
  composite_score: {{composite_score}}      (例 4.0)
  verdict: {{verdict}}                      (例 中性-分歧偏空)
  verdict_tone: {{verdict_tone}}            (bullish / neutral / bearish)
  anchor_price: {{anchor_price}}            (例 10.1)
  anchor_delta_signed: {{anchor_delta_signed}}  (例 -44 或 +8.6, 含符号)
  horizon: {{horizon}}                      (例 2 年 / 12 月)
  expected_return: {{expected_return}}      (例 -44.1)
  return_tone: {{return_tone}}              (positive / negative)
  annualized_return: {{annualized_return}}  (例 -24.9)
-->

<!-- KEY_METRICS_SIDEBAR (5-8 项关键指标):
  pe_ttm: {{pe_ttm}}                (负值显示 "–(亏损)")
  pb: {{pb}}
  market_cap: {{market_cap}}        (亿元)
  roe: {{roe}}                      (%)
  roe_tone: {{roe_tone}}            (positive / negative / neutral)
  gross_margin: {{gross_margin}}    (%)
  debt_to_assets: {{debt_to_assets}}  (%)
  debt_tone: {{debt_tone}}
  holder_num: {{holder_num}}        (股东户数)
  control_ratio: {{control_ratio}}  (家族/前10大合计 %)
  control_tone: {{control_tone}}    (risk 若家族 >= 40% 或前10大 >= 50%)
-->

<!-- CARD_METADATA (主页卡片用):
  slug: {{company_slug}}            (目录名, 例 ShifengCulture_实丰文化)
  sector: {{sector}}                (例 玩具+游戏+光伏参股)
  market: {{market}}                (us/a/hk/pe)
  one_liner: {{one_liner}}          (≤ 200 字, §一"一句话结论"浓缩)
  top_risks_short: {{top_risks_short}}  (3 条 ≤ 30 字 array)
-->

---

## §一 执行摘要

> 按 `assets/templates/exec-summary-schema.md` 的固定字段展开。这是全报告的决策仪表盘——读者只读本节即可掌握结论。

**一句话结论**: {{one_line_conclusion_with_direction}}

**估值锚**: **{{valuation_anchor}} 亿元 / {{anchor_price}} 元**（DCF 概率加权；{{scenario_count}} 情景）。当前 {{latest_close}} 元相对此锚 {{anchor_delta}}%。

**综合评分**: **{{composite_score}}/10** · **数据置信度**: {{confidence_level}}（与 §四 评分表加总一致）

**三大风险（Top 3）**:
1. {{risk_1}}
2. {{risk_2}}
3. {{risk_3}}

**三大机会（Top 3）**:
1. {{opportunity_1}}
2. {{opportunity_2}}
3. {{opportunity_3}}

**核心非共识判断**（1-3 条，可选——本报告与市场共识的关键分歧）:
1. {{insight_1_title}}

**投资方向综合判定**: {{investment_verdict}}（看多 / 看空 / 中性-分歧；与 §四 定性综合判断对齐）

---

## §二 公司基本面

### 业务板块

{{business_segments_table}}

### 最新经营动态（近 12 个月关键事件）

{{recent_events_table}}

### 财务趋势表（近 3-5 年 + 最新季度）

<!-- ★ 强制规则: 来源 data_snapshot.md §3 多年趋势完整表 -->
<!-- ★ 必含 data_snapshot.md §1 中标注的"最新期"end_date 行 (例如 20260331); 严禁省略最新季度 -->
<!-- ★ 严禁用 forecast_vip 预告口径替代 income.parquet 已有实际数据 (查 data_snapshot.md §4 forecast vs actual 对比) -->

| 期末 | 营收 | YoY | 毛利率 | 净利率 | 归母净利 | ROE | 资产负债率 | 来源 |
|------|-----:|----:|-----:|-----:|-------:|----:|----:|------|
{{financial_trend_rows}}

### 管理层前瞻信号（`forecast_vip` 解读）

{{forecast_signal_analysis}}

### 管理层与团队（`stk_managers` / `stk_rewards`）

{{management_profile_and_alignment}}

### 主力控盘与筹码分析（Read `capital_flow.md` + `data_snapshot.md` §5/§6/§7）

<!-- ★ 强制规则: 来源 capital_flow.md + data_snapshot.md §5/§6/§7 -->
<!-- ★ 必含: 十大股东 ≥ 9 行 (data_snapshot.md §5) + 十大流通股东 ≥ 9 行 (data_snapshot.md §6) -->
<!-- ★ 若 data_snapshot.md §7 质押表非空, 必须 inline 完整质押明细 -->
<!-- ★ 推荐 2 期对比展示股东持股变动 -->

{{capital_flow_summary_table}}

{{top10_float_holders_table}}

{{chip_concentration_2x2}}

### ★ 若核心资产被剥离的剩余资产清单（触发时必填）

**触发判定**: {{sotp_trigger_status}}

{{sotp_remaining_assets_table}}

---

## §三 行业与竞争对标

### 行业规模与趋势

{{industry_size_and_trends}}

### Porter 五力分析

{{porter_five_forces}}

### A 股同行业对标（Read `peer_analysis.md`，自动采集）

{{peer_comparison_table}}

### 目标公司在 peer 中的分位

{{peer_percentile_table}}

### 硬判定对比洞察 + 海外同业补充（若适用）

{{peer_insights_and_overseas}}

---

## §四 评分与维度证据

> 评分表与逐维度证据合并在本节——分数即证据的索引，不再"总览"与"详细"两处重复。评分标尺见 `references/scoring-rubric.md`。

### 10 维度加权评分

| 维度 | 权重 | 分数(0-10) | 加权 |
|------|:---:|:---:|:----:|
| 1. 市场规模与结构 | 10% | {{score_1}} | {{weighted_1}} |
| 2. 商业模式 | 10% | {{score_2}} | {{weighted_2}} |
| 3. 盈利能力 | 15% | {{score_3}} | {{weighted_3}} |
| 4. 产品与技术 | 10% | {{score_4}} | {{weighted_4}} |
| 5. 团队与管理层 | 10% | {{score_5}} | {{weighted_5}} |
| 6. 市场进入与护城河 | 10% | {{score_6}} | {{weighted_6}} |
| 7. 财务健康度 | 15% | {{score_7}} | {{weighted_7}} |
| 8. 估值合理性 | 10% | {{score_8}} | {{weighted_8}} |
| 9. 风险与治理 | 5% | {{score_9}} | {{weighted_9}} |
| 10. 催化剂与时机 | 5% | {{score_10}} | {{weighted_10}} |
| **合计** | 100% | – | **{{composite_score}}** |

*表格严格 4 列（维度/权重/分数/加权分）——不添加"关键理由"列。*

### 逐维度证据（每维度：分数 + 数据锚 + 判断）

#### 维度 1 · 市场规模与结构（{{score_1}}/10）
{{dim_1_evidence}}

#### 维度 2 · 商业模式（{{score_2}}/10）
{{dim_2_evidence}}

#### 维度 3 · 盈利能力（{{score_3}}/10）
{{dim_3_evidence}}

#### 维度 4 · 产品与技术（{{score_4}}/10）
{{dim_4_evidence}}

#### 维度 5 · 团队与管理层（{{score_5}}/10）
{{dim_5_evidence}}

#### 维度 6 · 市场进入与护城河（{{score_6}}/10）

**护城河判定**: {{moat_verdict}}

{{dim_6_evidence}}

#### 维度 7 · 财务健康度（{{score_7}}/10）
{{dim_7_evidence}}

#### 维度 8 · 估值合理性（{{score_8}}/10）
{{dim_8_evidence}}

#### 维度 9 · 风险与治理（{{score_9}}/10）
{{dim_9_evidence}}

#### 维度 10 · 催化剂与时机（{{score_10}}/10）

**催化剂判定**: {{catalyst_verdict}}

{{dim_10_evidence}}

### 定性综合判断

> 综合护城河 / 管理层 / 催化剂三个维度的方向（≥ 2 同向 → 对应方向；否则"中性-分歧"），给出 §一 的"投资方向综合判定"。会计红旗见 §六，估值见 §五。

**护城河 → {{moat_verdict}}** · **管理层 → {{mgmt_verdict}}** · **催化剂 → {{catalyst_verdict}}**

**综合方向**: **{{qualitative_overall}}**

---

## §五 估值与回报

> **方法论**: 以"**DCF 概率加权**"为唯一估值锚；可比 PE / PB 仅作交叉验证。投资回报情景与 DCF 共用同一套概率分布。

### 5.1 DCF 情景分析（{{scenario_count}} 情景）

#### 乐观情景（{{weight_bull}}% 权重）
{{scenario_bull_description}}
**SOTP**: {{sotp_bull}}

#### 基准情景（{{weight_base}}% 权重）
{{scenario_base_description}}
**SOTP**: {{sotp_base}}

#### 悲观情景（{{weight_bear}}% 权重）
{{scenario_bear_description}}

{{scenario_bear_sotp_table}}

#### 最差情景（{{weight_tail}}% 权重，若触发）
{{scenario_tail_description}}

#### 估值锚（概率加权 DCF）

| 情景 | 估值（亿） | 对应股价 | 概率 | 加权贡献 |
|------|---------:|-------:|:----:|-------:|
| 乐观 | {{valuation_bull}} | {{price_bull}} | {{weight_bull}}% | {{contrib_bull}} |
| 基准 | {{valuation_base}} | {{price_base}} | {{weight_base}}% | {{contrib_base}} |
| 悲观 | {{valuation_bear}} | {{price_bear}} | {{weight_bear}}% | {{contrib_bear}} |
| 最差 | {{valuation_tail}} | {{price_tail}} | {{weight_tail}}% | {{contrib_tail}} |
| **概率加权** | **{{valuation_anchor}}** | **{{anchor_price}}** | 100% | {{valuation_anchor}} |

### 5.2 交叉验证（仅互证，不纳入锚）

- **可比 PE**: {{comparable_pe_calc}}
- **有形 PB**: {{tangible_pb_calc}}
- **自洽判定**: {{triangulation_consistency}}（差 < 10% ✅ / 10-20% ⚠ / > 20% 🔴）

### 5.3 估值异常 + 技术面位置（Read `technical_analysis.md`）

{{valuation_anomalies}}

{{technical_summary_table}}

{{support_resistance_levels}}

**基本面 × 技术面配合判断**: {{fundamental_technical_combo_judgment}}

### 5.4 投资回报测算（与 5.1 共用情景）

**初始仓位**: {{amount}} 元人民币 · **当前买入**: {{latest_close}} 元 × {{shares_bought}} 股

| 情景 | 目标价 | 收益率 | 概率 | 加权 |
|------|:---:|:---:|:----:|:---:|
| 乐观 | {{price_bull}} 元 | {{return_bull}}% | {{weight_bull}}% | {{weighted_return_bull}}% |
| 基准 | {{price_base}} 元 | {{return_base}}% | {{weight_base}}% | {{weighted_return_base}}% |
| 悲观 | {{price_bear}} 元 | {{return_bear}}% | {{weight_bear}}% | {{weighted_return_bear}}% |
| 最差 | {{price_tail}} 元 | {{return_tail}}% | {{weight_tail}}% | {{weighted_return_tail}}% |
| **概率加权 {{horizon}} 收益率** | – | – | 100% | **{{weighted_expected_return}}%** |

**年化** ≈ {{annualized_return}}%。**建议仓位**: {{position_sizing}}。

---

## §六 风险与红旗审计

> 集中回答"什么会杀死这笔投资"：致命看空快筛 + 11 框架审计红旗 + 治理风险，一处看全。

### 6.1 致命看空快筛（6 项量化阈值）

| 条款 | 阈值 | 实际 | 触发? |
|------|------|------|:----:|
| 1. 单季 / 单年度净利 < -50% | 50% | {{screen_1_actual}} | {{screen_1_triggered}} |
| 2. 资产负债率 > 70% | 70% | {{screen_2_actual}} | {{screen_2_triggered}} |
| 3. 大股东累计质押 > 50% | 50% | {{screen_3_actual}} | {{screen_3_triggered}} |
| 4. 审计机构连续 2 年变更 | 1 次 | {{screen_4_actual}} | {{screen_4_triggered}} |
| 5. CFO 非正常离任 | 1 次 | {{screen_5_actual}} | {{screen_5_triggered}} |
| 6. **Audit ≥ 2 个 🔴 红旗** | 2 | {{screen_6_actual}} | {{screen_6_triggered}} |

**快筛结果**: {{screen_summary}}

### 6.2 审计红旗汇总（11 框架，Read `audit_report.md`）

| 严重度 | 数量 | 代表性红旗 |
|-------|:----:|------|
| 🔴 致命 | {{audit_fatal_count}} | {{audit_fatal_list}} |
| 🟠 高 | {{audit_high_count}} | {{audit_high_list}} |
| 🟡 中 | {{audit_mid_count}} | {{audit_mid_list}} |
| 🟢 低 | {{audit_low_count}} | {{audit_low_list}} |

完整清单: `audit_report.md`。

### 6.3 致命看空论证

> 把 6.1 触发项 + 6.2 高级红旗串成"空头核心逻辑链"。每条 🔴/🟠 红旗必须在此或 §一 Top 3 风险被引用闭环。

{{fatal_short_thesis}}

---

## §七 舆情与市场情绪

### 看多派声音（≥ 3 条）

{{bull_sentiment_table}}

### 看空派声音（≥ 3 条）

{{bear_sentiment_table}}

### 资金流向信号（Read `capital_flow.md` §4/§5/§6）

{{capital_flow_hsgt_margin_mainflow}}

---

## §八 数据来源与信息缺口

**截止日期**: {{data_cutoff}}。**关键待披露**: {{pending_disclosures}}。

### 数据来源（3 类分组）

#### [Tushare API]
{{tushare_sources}}

#### [PDF 原文]
{{pdf_sources}}

#### [WebSearch]
{{websearch_sources}}

**详细来源清单见 `phase1-data.md` §11**。

### 信息缺口与尽调优先级（≥ 3 条）

| # | 缺口 | 状态 | 可得性 | 影响的结论 |
|---|------|:----:|:---:|------|
{{info_gap_rows}}

---

*本报告由 Claude Code company-analysis skill v{{skill_version}}（结构化数据 + 11 大师框架审计流水线）生成。禁止用于实际投资决策，仅作研究参考。*
