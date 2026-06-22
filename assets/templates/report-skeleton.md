# {{company_name}}（{{ticker}}）投资分析报告

**报告日期**: {{report_date}}
**报告期**: {{data_coverage}}
**最新收盘**: {{latest_close}} 元（{{latest_date}}）
**总市值**: {{market_cap}} 亿元 · PB {{pb}} · {{pe_display}}
**分析师**: Claude Opus 4.8 · Skill v{{skill_version}}

<!-- v6.0 HTML 生成锚点: 供 Phase 6 Part B 抽取以下字段填充前置评级卡 + 顶部指标条
     供 update_index.py 生成主页卡片 metadata
     LLM 写报告时务必让下列字段在正文中可找到(典型位置: §一 执行摘要 / §五 估值、赔率与定价充分度) -->

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

**估值锚**: **{{valuation_anchor}} 亿元 / {{anchor_price}} 元**（§五 综合估值锚；{{scenario_count}} 情景）。当前 {{latest_close}} 元相对此锚 {{anchor_delta}}%。

**综合评分**: **{{composite_score}}/10** · **数据置信度**: {{confidence_level}}（§四 评分表加总；★ 此为「基本面静态快照」——衡量"公司本身多好"，**不是投资结论**；投资方向看下方「决策结论」/§七）

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

**决策结论**（来自 §七 投资决策内核——本报告的权威结论；与 §七 7.4 一致）:
- **决策三元组**: [状态后验: {{state_posterior_verdict}} | 赔率: {{odds_verdict}} | 路径: {{path_verdict}}]
- **三分结论**: 好公司? {{good_company}} · 好下注(现价)? {{good_bet}} · 好价格? {{good_price}}
- **行动档位**: {{action_tier}}（核心仓 / 期权仓 / 等证据临界 / 不追高 / 减仓 / 回避）· **该等什么**: {{wait_for}}

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

> 综合护城河 / 管理层 / 催化剂三个维度的方向（≥ 2 同向 → 对应方向；否则"中性-分歧"）。v7.0：此 verdict 作为 §七 7.1 状态后验的**输入之一**，不再直接定 §一 投资方向——权威结论在 §七 投资决策内核。会计红旗见 §六，估值见 §五。

**护城河 → {{moat_verdict}}** · **管理层 → {{mgmt_verdict}}** · **催化剂 → {{catalyst_verdict}}**

**综合方向**: **{{qualitative_overall}}**

### 4.11 状态评估（正在变好吗？被独立证据确认吗？）

> 10 维度评分 = 静态基线（公司"现在"多好，即 F）。本节给"导数"——是否正在变好、是否被独立证据确认。各机制原料供 §七 投资决策内核合成。机制定义见 `references/investment-decision-core.md`。

#### 【λ 与证据临界密度】（泊松 + 贝叶斯）

- **λ（向上状态跳变强度）定义**（按资产类型）+ **核心状态跳变事件** = {{lambda_definition_and_event}}
- **λ↑ 信号**（★分部级，注明是否被集团主体稀释）: {{lambda_signals}}

| 信号 | 内容 | 独立证据 / 叙事回声 |
|------|------|:---:|
{{evidence_network_rows}}

- **是否达临界密度**: {{evidence_critical_status}}；**临界点** = {{evidence_critical_event}}
- **贝叶斯三问**: 后验提高还是注意力提高? {{bayes_q1}}｜独立证据还是回声? {{bayes_q2}}｜价格是否过度反映? {{bayes_q3}}

#### 【身份切换 · 升级基本面5元组】（喊线）

- **身份切换 P1→P4**: 旧身份 → 新身份候选 = {{identity_switch}}；当前 **P{{production_position}}**；是否已被市场重命名: {{renamed_status}}
- **升级基本面5元组**: 生产函数位置 {{f5_position}}｜约束释放能力 {{f5_constraint}}｜权威认证 {{f5_authority}}｜证据再验证节奏 {{f5_cadence}}｜定价充分度 {{f5_pricing}}

#### 【四层验证 · 权威认证】（喊线）

| 层 | 判定 | 依据 |
|----|:---:|------|
| ① 能一句话传播? | {{layer1_verdict}} | {{layer1_basis}} |
| ② 真实产业约束接棒?（订单/收入/客户/毛利/FCF） | {{layer2_verdict}} | {{layer2_basis}} |
| ③ 权威节点认证?（权威分发 vs 券商回声） | {{layer3_verdict}} | {{layer3_basis}} |
| ④ 价格已买完完美未来?（详见 §五） | {{layer4_verdict}} | {{layer4_basis}} |

#### 【右尾识别 · 幂律来源 · 左尾预警】（十倍股 + 幂律）

- **右尾清单**: 需求真实可延展 {{rt_demand}}｜难替代提价权 {{rt_pricing}}｜FCF 自造血 {{rt_fcf}}｜利润率持续提升 {{rt_margin}}｜估值起点偏低 {{rt_valuation}}
- **幂律来源**（是不是"幂律生成器节点"）: {{power_law_sources}}
- **左尾预警**: {{left_tail_warning}}（详见 §六 6.4）

#### 【无记忆性检查】（泊松）

> 买入理由必须是 λ↑ 或证据斜率变正，不得是"跌久了/沉寂久了/讲多年该兑现/估值压久了"这类等待时间幻觉。

**本标的买入逻辑是否落入无记忆性幻觉**: {{memorylessness_check}}

→ **状态后验初判**（供 §七 7.1）: {{state_posterior_verdict}}（↑变好+证据确认 / ↑变好但仅注意力·未确认 / 横盘 / ↓变差）

---

## §五 估值、赔率与定价充分度

> **方法论 (v7.0)**: 不以"DCF 概率加权单锚"为唯一说服力。先用 **P = 基本面F + 叙事溢价N** 分解价格、用**反向DCF**读市场隐含预期、用**叙事分部 SOTP** 拆分不混账，判"赔率/定价充分度"；正向 DCF 仅作 F 的一种交叉验证。框架见 `references/investment-decision-core.md` + `references/valuation-frameworks.md`。

### 5.1 价格分解 P = 基本面F + 叙事溢价N

| 项 | 值 | 说明 |
|------|---:|------|
| 基本面价值 F（主业行业倍数 + 已兑现分部，保守） | {{fundamental_value_F}} | {{F_method}} |
| 叙事溢价 N = 现价市值 − F | {{narrative_premium_N}} | 占现价市值 {{N_pct}}% |

- **N 在为什么定价**: {{N_narrative}}
- **N 是 free option 还是 embedded obligation**: {{N_option_or_obligation}}
- **N'/N vs F'/F**（驱动股价的是叙事增速还是基本面增速）: {{growth_decomposition}}

### 5.2 反向 DCF：市场隐含预期

| 隐含假设 | 现价隐含值 | 历史/同业参照 | 可信? | 证伪条件 |
|---------|---------|------------|:---:|--------|
{{reverse_dcf_rows}}

**结论**: 现价隐含的预期 {{reverse_dcf_verdict}}（可信 / 过度乐观 / 已买完完美未来）。

### 5.3 ΔP 传播因子分解（本轮上涨由谁驱动）

{{delta_p_factor_decomposition}}

> 因子: Authority Weight / Narrative Compression / Attention Velocity / Marginal Buyer Urgency / Peer Resonance / Gamma·Flow / Right-tail Optionality − (PFPC / Crowding / Valuation Exhaustion)。逐项判强弱 → 是"权威认证驱动"还是"散户拥挤 + 估值耗尽驱动"。

### 5.4 叙事分部 SOTP：拆分不混账（≥ 2 条增长叙事且分部差异大时必填）

**触发判定**: {{sotp_trigger_status}}

| 分部 | 各自合适倍数/方法 | 估值（亿） | 各自证伪指标 |
|------|------------|---------:|------------|
{{narrative_sotp_rows}}

**SOTP 合计** {{sotp_total}} vs 现价市值 {{market_cap}} 亿 → {{sotp_vs_price}}。*禁止用单一笼统倍数盖全公司。*

### 5.5 正向 DCF（作为 F 的交叉验证，{{scenario_count}} 情景）

> 退出倍数须 vs 同业当前 + 历史分位 sanity；转型公司放松"终端利润率≈历史均值"硬锚时须显式举证。forecast vs actual 兑现度见 data_snapshot.md §4。

{{dcf_scenarios_description}}

| 情景 | 估值（亿） | 对应股价 | 概率 | 加权贡献 |
|------|---------:|-------:|:----:|-------:|
| 乐观 | {{valuation_bull}} | {{price_bull}} | {{weight_bull}}% | {{contrib_bull}} |
| 基准 | {{valuation_base}} | {{price_base}} | {{weight_base}}% | {{contrib_base}} |
| 悲观 | {{valuation_bear}} | {{price_bear}} | {{weight_bear}}% | {{contrib_bear}} |
| 最差 | {{valuation_tail}} | {{price_tail}} | {{weight_tail}}% | {{contrib_tail}} |
| **概率加权（DCF 交叉验证锚）** | **{{valuation_anchor}}** | **{{anchor_price}}** | 100% | {{valuation_anchor}} |

**forecast vs actual 兑现度**: {{forecast_vs_actual}}

### 5.6 回报与路径成本 + 技术面位置（Read `technical_analysis.md`）

{{technical_summary_table}}

{{support_resistance_levels}}

**基本面 × 技术面配合判断**: {{fundamental_technical_combo_judgment}}

**初始仓位**: {{amount}} 元人民币 · **当前买入**: {{latest_close}} 元 × {{shares_bought}} 股

| 情景 | 目标价 | 终点收益率 | 中途最大回撤 | 时间窗 | 概率 | 加权 |
|------|:---:|:---:|:---:|:---:|:----:|:---:|
| 乐观 | {{price_bull}} 元 | {{return_bull}}% | {{drawdown_bull}} | {{horizon_bull}} | {{weight_bull}}% | {{weighted_return_bull}}% |
| 基准 | {{price_base}} 元 | {{return_base}}% | {{drawdown_base}} | {{horizon_base}} | {{weight_base}}% | {{weighted_return_base}}% |
| 悲观 | {{price_bear}} 元 | {{return_bear}}% | {{drawdown_bear}} | {{horizon_bear}} | {{weight_bear}}% | {{weighted_return_bear}}% |
| 最差 | {{price_tail}} 元 | {{return_tail}}% | {{drawdown_tail}} | {{horizon_tail}} | {{weight_tail}}% | {{weighted_return_tail}}% |
| **概率加权 {{horizon}} 收益率** | – | – | – | – | 100% | **{{weighted_expected_return}}%** |

**年化** ≈ {{annualized_return}}%。**时间成本 + 机会成本**（vs 同期更优替代）: {{time_opportunity_cost}}。**假阳性成本**（把回声当证据的代价）: {{false_positive_cost}}。**建议仓位**: {{position_sizing}}。

### 5.7 赔率/定价充分度小结

**赔率判定**: {{odds_verdict}}（便宜（有 slack）/ 合理 / 已 price-in / 买完完美未来（无 slack））→ 供 §七 7.2。

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

### 6.4 左尾防护 · 高信仰股特征（供 §七 7.3 路径判定）

- **左尾毁灭清单**（兑现前可能"归零/腰斩"的事件）: {{left_tail_destruction_list}}（减值 / 退市 / key-person / 踩踏 / 控制权丧失…）
- **高信仰股特征体检**（命中越多，下跌时越是"组合波动放大器"）: 高估值 {{faith_valuation}}｜高波动 {{faith_volatility}}｜高散户参与 {{faith_retail}}｜高媒体/期权活跃 {{faith_media}}｜key-person 依赖 {{faith_keyperson}}
- **路径可承受性初判**（供 §七 7.3）: {{path_verdict}}（可承受 / 高尾险·不可承受）

---

## §七 投资决策内核

> 用"**投资价值 = 状态后验 × 赔率 × 路径可承受性**"（乘法，任一为"差"即拉低整体）合成 §四（状态）、§五（赔率）、§六（路径），输出"好公司 / 好下注 / 好价格"三分结论与行动档位。本章是各篇理念的合成结论，逐机制原料在 §四 4.11 / §五。框架定义见 `references/investment-decision-core.md`。

### 7.1 状态后验合成（引 §四 4.11）

{{state_posterior_synthesis}}

→ **状态后验**: {{state_posterior_verdict}}（↑变好+证据确认 / ↑变好但仅注意力·未确认 / 横盘 / ↓变差）

### 7.2 赔率合成（引 §五）

{{odds_synthesis}}

→ **赔率**: {{odds_verdict}}（便宜 / 合理 / 已 price-in / 买完完美未来）

### 7.3 路径可承受性合成（引 §六 6.4 + §五 5.6）

{{path_synthesis}}

→ **路径**: {{path_verdict}}（可承受 / 高尾险·不可承受）

### 7.4 决策合成

> 价值 = 状态后验 × 赔率 × 路径。结合 λ×payoff 四象限 + 高质量等待 vs 资本钝化 + 仓位纪律（叙事越远仓位越小）+ 现金=选择权。

- **决策三元组**: [状态后验: {{state_posterior_verdict}} | 赔率: {{odds_verdict}} | 路径: {{path_verdict}}]
- **三分结论**: 好公司? {{good_company}} · 好下注（现价）? {{good_bet}} · 好价格? {{good_price}}（各带一句依据）
- **行动档位**: {{action_tier}}（核心仓 / 期权仓（小）/ 等证据临界（观察）/ 不追高（贵但优质）/ 减仓 / 回避）— {{action_rationale}}
- **该等什么**: {{wait_for}}（跳变事件 + 预计时点）
- **证伪/退出条件**: {{falsification_exit}}（每条核心叙事 1 个可证伪指标 + λ下降 / 证据恶化触发 → 接 Phase 7 监控）
- **信仰陷阱五弊端自检**: {{faith_trap_selfcheck}}

### 7.5 与 §一 对齐

> §一「决策结论」的决策三元组 / 三分结论 / 行动档位必须与本节 7.4 一致。

---

## §八 舆情与市场情绪

### 看多派声音（≥ 3 条）

{{bull_sentiment_table}}

### 看空派声音（≥ 3 条）

{{bear_sentiment_table}}

### 资金流向信号（Read `capital_flow.md` §4/§5/§6）

{{capital_flow_hsgt_margin_mainflow}}

---

## §九 数据来源与信息缺口

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
