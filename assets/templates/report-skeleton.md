# {{company_name}}（{{ticker}}）投资分析报告

**报告日期**: {{report_date}}
**报告期**: {{data_coverage}}
**最新收盘**: {{latest_close}} 元（{{latest_date}}）
**总市值**: {{market_cap}} 亿元 · PB {{pb}} · {{pe_display}}
**分析师**: Claude Opus 4.7 · Skill v{{skill_version}}

---

## §一 执行摘要

**一句话结论**: {{one_line_conclusion_with_direction}}

**估值锚**: **{{valuation_anchor}} 亿元 / {{anchor_price}} 元**（DCF 概率加权；{{scenario_count}} 情景）。当前 {{latest_close}} 元相对此锚 {{anchor_delta}}%。

**综合评分**: **{{composite_score}}/10** · **数据置信度**: {{confidence_level}}

**三大风险（Top 3）**:
1. {{risk_1}}
2. {{risk_2}}
3. {{risk_3}}

**三大机会（Top 3）**:
1. {{opportunity_1}}
2. {{opportunity_2}}
3. {{opportunity_3}}

**核心非共识观点**（来自 §十一 差异化洞察）:
1. {{insight_1_title}}
2. {{insight_2_title}}
3. {{insight_3_title}}

---

## §二 事实评分总览（10 维度）

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

*详细证据见 §六。评分标尺见 `references/scoring-rubric.md`。表格严格 4 列（维度/权重/分数/加权分）——不添加"关键理由"列。*

---

## §三 快速筛选（致命看空条款 - 6 项）

| 条款 | 阈值 | 实际 | 触发? |
|------|------|------|:----:|
| 1. 单季 / 单年度净利 < -50% | 50% | {{screen_1_actual}} | {{screen_1_triggered}} |
| 2. 资产负债率 > 70% | 70% | {{screen_2_actual}} | {{screen_2_triggered}} |
| 3. 大股东累计质押 > 50% | 50% | {{screen_3_actual}} | {{screen_3_triggered}} |
| 4. 审计机构连续 2 年变更 | 1 次 | {{screen_4_actual}} | {{screen_4_triggered}} |
| 5. CFO 非正常离任 | 1 次 | {{screen_5_actual}} | {{screen_5_triggered}} |
| 6. **Audit ≥ 2 个 🔴 红旗** | 2 | {{screen_6_actual}} | {{screen_6_triggered}} |

**结果**: {{screen_summary}}

---

## §四 公司基本面

### 业务板块

{{business_segments_table}}

### 最新经营动态（近 12 个月关键事件）

{{recent_events_table}}

### 财务趋势表（近 3-5 年 + 最新季度）

| 期末 | 营收 | YoY | 毛利率 | 净利率 | 归母净利 | ROE | 资产负债率 | 来源 |
|------|-----:|----:|-----:|-----:|-------:|----:|----:|------|
{{financial_trend_rows}}

### 管理层前瞻信号（`forecast_vip` 解读）

{{forecast_signal_analysis}}

### 主力控盘与筹码分析（v4.4 — Read `capital_flow.md`）

{{capital_flow_summary_table}}

{{top10_float_holders_table}}

{{chip_concentration_2x2}}

### ★ 若核心资产被剥离的剩余资产清单（v4.2 触发时必填）

**触发判定**: {{sotp_trigger_status}}

{{sotp_remaining_assets_table}}

---

## §五 行业与竞争格局

### 行业规模与趋势

{{industry_size_and_trends}}

### Porter 五力分析（集中在本节，不重复到 §六 维度 3）

{{porter_five_forces}}

### 关键竞品对标

{{key_competitor_summary}}

---

## §六 10 维度详细证据

### 维度 1 · 市场规模与结构（{{score_1}}/10）
{{dim_1_evidence}}

### 维度 2 · 商业模式（{{score_2}}/10）
{{dim_2_evidence}}

### 维度 3 · 盈利能力（{{score_3}}/10）
{{dim_3_evidence}}

### 维度 4 · 产品与技术（{{score_4}}/10）
{{dim_4_evidence}}

### 维度 5 · 团队与管理层（{{score_5}}/10）

#### 管理层利益对齐（`stk_rewards`）
{{team_alignment}}

#### 核心团队画像（`stk_managers`）
{{team_profile}}

{{dim_5_evidence}}

### 维度 6 · 市场进入与护城河（{{score_6}}/10）
{{dim_6_evidence}}

### 维度 7 · 财务健康度（{{score_7}}/10）
{{dim_7_evidence}}

### 维度 8 · 估值合理性（{{score_8}}/10）
{{dim_8_evidence}}

### 维度 9 · 风险与治理（{{score_9}}/10）
{{dim_9_evidence}}

### 维度 10 · 催化剂与时机（{{score_10}}/10）
{{dim_10_evidence}}

---

## §七 网络舆情与市场情绪

### 看多派声音

{{bull_sentiment_table}}

### 看空派声音

{{bear_sentiment_table}}

### 资金流向信号（v4.4 — Read `capital_flow.md` §4/§5/§6）

{{capital_flow_hsgt_margin_mainflow}}

---

## §八 可比公司对标（v4.4 — Read `peer_analysis.md`）

### §8.1 A 股同行业对标（自动采集）

{{peer_comparison_table}}

### §8.2 目标公司在 peer 中的分位

{{peer_percentile_table}}

### §8.3 硬判定对比洞察

{{peer_insights_list}}

### §8.4 海外同业补充（若适用）

{{overseas_peers_llm_filled}}

---

## §九 估值与回报模拟

> **方法论**: 以"**DCF 概率加权**"为唯一估值锚，§十（投资回报）沿用同一套情景。§9.2 可比 PE 和 PB 作为**交叉验证**而非独立锚。

### 9.1 DCF 情景分析（v4.2 — {{scenario_count}} 情景）

#### 乐观情景（{{weight_bull}}% 权重）
{{scenario_bull_description}}
**SOTP**: {{sotp_bull}}

#### 基准情景（{{weight_base}}% 权重）
{{scenario_base_description}}
**SOTP**: {{sotp_base}}

#### 悲观情景（{{weight_bear}}% 权重）
{{scenario_bear_description}}

{{scenario_bear_sotp_table}}

#### 最差情景（{{weight_tail}}% 权重，若触发 Step 9.5）
{{scenario_tail_description}}

#### 估值锚（概率加权 DCF）

| 情景 | 估值（亿） | 对应股价 | 概率 | 加权贡献 |
|------|---------:|-------:|:----:|-------:|
| 乐观 | {{valuation_bull}} | {{price_bull}} | {{weight_bull}}% | {{contrib_bull}} |
| 基准 | {{valuation_base}} | {{price_base}} | {{weight_base}}% | {{contrib_base}} |
| 悲观 | {{valuation_bear}} | {{price_bear}} | {{weight_bear}}% | {{contrib_bear}} |
| 最差 | {{valuation_tail}} | {{price_tail}} | {{weight_tail}}% | {{contrib_tail}} |
| **概率加权** | **{{valuation_anchor}}** | **{{anchor_price}}** | 100% | {{valuation_anchor}} |

### 9.2 交叉验证（仅互证，不纳入锚）

- **可比 PE**: {{comparable_pe_calc}}
- **有形 PB**: {{tangible_pb_calc}}
- **自洽判定**: {{triangulation_consistency}}（差 < 10% ✅ / 10-20% ⚠ / > 20% 🔴）

### 9.3 估值异常

{{valuation_anomalies}}

### 9.4 技术面位置（v4.4 — Read `technical_analysis.md`）

{{technical_summary_table}}

{{support_resistance_levels}}

**基本面 × 技术面配合判断**:

{{fundamental_technical_combo_judgment}}

---

## §十 投资回报测算（与 §九 共用情景）

**初始仓位**: 100 万元人民币
**当前买入**: {{latest_close}} 元 × {{shares_bought}} 股

| 情景 | 目标价 | 收益率 | 概率 | 加权 |
|------|:---:|:---:|:----:|:---:|
| 乐观 | {{price_bull}} 元 | {{return_bull}}% | {{weight_bull}}% | {{weighted_return_bull}}% |
| 基准 | {{price_base}} 元 | {{return_base}}% | {{weight_base}}% | {{weighted_return_base}}% |
| 悲观 | {{price_bear}} 元 | {{return_bear}}% | {{weight_bear}}% | {{weighted_return_bear}}% |
| 最差 | {{price_tail}} 元 | {{return_tail}}% | {{weight_tail}}% | {{weighted_return_tail}}% |
| **概率加权 {{horizon}} 收益率** | – | – | 100% | **{{weighted_expected_return}}%** |

**年化** ≈ {{annualized_return}}%。**建议仓位**: {{position_sizing}}。

---

## §十一 定性判断（3 框架，v4.1 — 无打分）

> *会计红旗检查见 `audit_report.md`（Buffett Quality + Sloan Accrual 框架已自动扫描）；估值分析见 §九。*

### 框架 1 · 护城河（Moat）→ **{{moat_verdict}}**
{{moat_analysis}}

### 框架 2 · 管理层（Management）→ **{{mgmt_verdict}}**
{{mgmt_analysis}}

### 框架 3 · 催化剂（Catalyst）→ **{{catalyst_verdict}}**
{{catalyst_analysis}}

**综合判断**（3 框架中 ≥ 2 同向 → 对应方向；否则"中性-分歧"）: **{{qualitative_overall}}**

**致命看空条款检查**: 见 §三 快筛结果（{{screen_summary_short}}）。

---

## §十二 差异化洞察（Phase 5 回写 — 9 字段卡片）

> 本章节由 Phase 5 生成并回写。详见 `phase5-variant-perception.md` 深度附件（Level C 附录 / 议题感知 / 共识映射）。

{{variant_perception_cards}}

---

## §十三 多角色投资结论（Phase 4 回写 — 3 角色 × 3 段精简版）

> 深度版（完整 3 段论述 + 哲学分歧展开）见 `phase4-personas.md`。

### 角色 A · {{persona_1_name}}（{{persona_1_philosophy}}）
{{persona_1_summary}}

### 角色 B · {{persona_2_name}}（{{persona_2_philosophy}}）
{{persona_2_summary}}

### 角色 C · {{persona_3_name}}（{{persona_3_philosophy}}）
{{persona_3_summary}}

### 三角色分歧总结
{{persona_divergence_summary}}

---

## §十四 信息缺口与尽调优先级

| # | 缺口 | 状态 | 可得性 | 影响的结论 |
|---|------|:----:|:---:|------|
{{info_gap_rows}}

---

## §十五 数据可审计性（时效性 + 来源 3 类分组）

**截止日期**: {{data_cutoff}}。**关键待披露**: {{pending_disclosures}}。

### [Tushare API]
{{tushare_sources}}

### [PDF 原文]
{{pdf_sources}}

### [WebSearch]
{{websearch_sources}}

**详细来源清单见 `phase1-data.md` §11**。

### 审计红旗汇总（11 框架）

| 严重度 | 数量 | 代表性红旗 |
|-------|:----:|------|
| 🔴 致命 | {{audit_fatal_count}} | {{audit_fatal_list}} |
| 🟠 高 | {{audit_high_count}} | {{audit_high_list}} |
| 🟡 中 | {{audit_mid_count}} | {{audit_mid_list}} |
| 🟢 低 | {{audit_low_count}} | {{audit_low_list}} |

完整清单: `audit_report.md`。

---

*本报告由 Claude Code company-analysis skill v{{skill_version}}（6+1 阶段流水线 + 11 大师框架审计）生成。禁止用于实际投资决策，仅作研究参考。*
