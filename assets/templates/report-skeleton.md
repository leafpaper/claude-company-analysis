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

> 按 `assets/templates/exec-summary-schema.md` 的固定字段展开。读者只读本节，就能知道"是不是好公司、现在该不该买、该等什么"。**全程说人话，不堆术语，正文不放来源标签。**

**投资要点**（3-5 条，每条一句人话，先讲最重要的）:
- {{key_point_1}}
- {{key_point_2}}
- {{key_point_3}}

**一句话结论**: {{one_line_conclusion_with_direction}}

### 投资决断卡（一眼看懂——"是否适合投资"的答案）

> ★ "是不是好公司（值不值得放进你的长期关注池）"和"现在该不该买（价格/时点）"分开看：前者给筛选信号，后者给买卖时点。

| 问题 | 结论 | 一句话理由（说人话，给最硬的那条证据） |
|------|:---:|------|
| ① 是不是好公司?（生意 + 护城河 + 赚钱质量） | {{good_company}} | {{good_company_why}} |
| ② 它讲的故事真不真?（叙事 + 热点） | {{story_real}} | {{story_real_why}} |
| ③ 现在价格贵不贵?（估值） | {{price_verdict}} | {{price_verdict_why}} |
| ④ 现在该不该买?（综合：好下注吗） | {{good_bet}} | {{good_bet_why}} |
| ⑤ 我该怎么办? | {{action_tier}} | {{action_and_wait}} |

> 决断卡与 §七 7.4 一致（行动档位六档：核心仓 / 期权仓 / 等证据临界 / 不追高 / 减仓 / 回避）。

**估值锚**: **{{valuation_anchor}} 亿元 / {{anchor_price}} 元**（§五 综合估值锚；{{scenario_count}} 情景）。当前 {{latest_close}} 元相对此锚 {{anchor_delta}}%。

**综合评分**: **{{composite_score}}/10** · **数据置信度**: {{confidence_level}}（基本面静态快照——衡量"公司本身多好"，不是投资结论；方向看上方决断卡 / §七）

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

### 4.11 这家公司在变好吗？变好被证据坐实了吗？（状态评估）

> **说人话**：上面 10 维度评分是"现在多好"的快照；本节回答"是不是正在变好、变好的证据够不够硬"。先看四维体检（一眼扫完），再看细节。每个判断只给最硬的一两条证据，正文不放来源标签（来源在 §九）。

#### 四维体检：懂财报 · 懂叙事 · 懂估值 · 懂热点

| 维度 | 看什么 | 结论 | 最硬的一条证据（人话） |
|------|------|:---:|------|
| ① 懂财报 | 现在赚钱吗、赚得健不健康 | {{check_caibao}} | {{check_caibao_evi}} |
| ② 懂叙事 | 讲的故事真不真、能否一句话传播、有没有权威背书 | {{check_xushi}} | {{check_xushi_evi}} |
| ③ 懂估值 | 现在贵不贵、贵在哪 | {{check_guzhi}} | {{check_guzhi_evi}} |
| ④ 懂热点 | 谁在买、是聪明钱还是散户跟风、透支没 | {{check_redian}} | {{check_redian_evi}} |

#### 它在"变好"吗？变好的证据够硬吗？（状态评估）

**一句话**: {{state_oneliner}}

- **变好的引擎是什么**: {{growth_engine}}
- **这条业务有多大份量**: {{engine_weight}}（占公司多少；是不是"小分部带大故事"）
- **证据硬不硬**（关键好消息是实锤还是传闻）:

| 你想知道的 | 现状 | 实锤 / 传闻 |
|------|------|:---:|
{{evidence_network_rows}}

- **缺的最后一块证据 = 该等什么**: {{evidence_critical_event}}

#### 市场是不是给它换了更值钱的"身份"？业务跟上没？（身份切换）

**一句话**: {{identity_oneliner}}

- **旧身份 → 新身份**: {{identity_switch}}
- **市场已按新身份定价了吗 / 业务跟上了吗**: {{renamed_status}}

#### 它的故事过几关？（叙事四关验证）

> 四关：能一句话讲清吗 → 有真订单真利润接住吗 → 有大佬权威背书吗 → 价格是不是已经把好结果全买走了。

| 关卡 | 过了吗 | 人话依据 |
|----|:---:|------|
| ① 能一句话讲清、好传播? | {{layer1_verdict}} | {{layer1_basis}} |
| ② 有真订单 / 真收入 / 真利润接住? | {{layer2_verdict}} | {{layer2_basis}} |
| ③ 有大佬 / 客户官方背书?（不是券商转述） | {{layer3_verdict}} | {{layer3_basis}} |
| ④ 价格还没把好结果买完?（详见 §五） | {{layer4_verdict}} | {{layer4_basis}} |

#### 它是不是"大赢家"那一类？最坏会怎样？（右尾 / 左尾）

**一句话**: {{tail_oneliner}}

- **像不像大赢家**（需求真、能提价、自己造血、估值起点低 四条对一遍）: {{right_tail_summary}}
- **最坏会怎样**（可能归零/腰斩的导火索）: {{left_tail_warning}}（详见 §六）

#### ⚠️ 别拿"涨太久了该停 / 跌太久了该涨 / 讲多年该兑现"当理由

{{memorylessness_check}}

→ **状态评估一句话**（供 §七）: {{state_posterior_verdict}}

---

## §五 估值、赔率与定价充分度

> **说人话**：这一章只回答一件事——**现在的价格贵不贵、贵在哪、值不值得现在买**。办法是把股价拆开看（已赚到的 vs 对未来的想象），再倒推"现价等于在赌它未来必须做到什么"。DCF 只作参照，不当唯一答案。正文不放来源标签（来源在 §九）。

**一句话**: {{valuation_oneliner}}

### 5.1 把股价拆成两块：已经赚到的 vs 对未来的想象（价格分解）

> 一只股票的市值 = **F（基本面：靠现在已赚到的钱该值多少）** + **N（叙事溢价：市场为"未来想象"多付的钱）**。N 占比越大，越要它把故事兑现，否则要杀估值。

| 这部分 | 值多少 | 怎么算的 |
|------|---:|------|
| F：靠现在的生意，保守该值 | {{fundamental_value_F}} | {{F_method}} |
| N：市场为"未来想象"多付的 | {{narrative_premium_N}} | 占现价市值 {{N_pct}}% |

- **市场在为什么想象多付钱**: {{N_narrative}}
- **这份想象是"白送的彩票"还是"必须做到的任务"**: {{N_option_or_obligation}}（贵到一定程度，远期故事就不是免费上行，而是做不到就跌）
- **现在拉动股价的，是故事跑得快还是业绩跑得快**: {{growth_decomposition}}

### 5.2 现价等于在赌它未来要做到什么？（反向推算市场预期）

| 隐含假设 | 现价隐含值 | 历史/同业参照 | 可信? | 证伪条件 |
|---------|---------|------------|:---:|--------|
{{reverse_dcf_rows}}

**结论**: 现价隐含的预期 {{reverse_dcf_verdict}}（可信 / 过度乐观 / 已买完完美未来）。

### 5.3 这波上涨健不健康？（一句话；资金细节见 §八）

**一句话**: {{delta_p_oneliner}}

> 只判一件事:撑起这波上涨的，是"大佬背书 + 真业绩"(健康、估值有支撑)，还是"散户拥挤 + 杠杆 + 估值已耗尽"(脆弱、一有风吹草动就踩踏)——这直接决定现价的赔率脆不脆。**谁在买的具体数据(北向/两融/散户户数/主力)放 §八，这里不重复。**

### 5.4 分开估：主业值多少 + 新业务值多少（分部估值，多条业务时必做）

> 不同业务用不同尺子，别拿一个笼统倍数盖全公司。

**触发判定**: {{sotp_trigger_status}}

| 分部 | 用什么尺子估 | 估值（亿） | 怎样算证伪（这块故事破了） |
|------|------------|---------:|------------|
{{narrative_sotp_rows}}

**分部加总** {{sotp_total}} 亿 vs 现价市值 {{market_cap}} 亿 → {{sotp_vs_price}}。

### 5.5 现金流折现交叉验证（DCF，{{scenario_count}} 情景，只作参照、不当唯一答案）

> 退出倍数须 vs 同业当前 + 历史分位对一遍；转型公司若把终端利润率假设拉高于历史，须显式说明凭什么。预告兑现度见 §九。

{{dcf_scenarios_description}}

| 情景 | 估值（亿） | 对应股价 | 概率 | 加权贡献 |
|------|---------:|-------:|:----:|-------:|
| 乐观 | {{valuation_bull}} | {{price_bull}} | {{weight_bull}}% | {{contrib_bull}} |
| 基准 | {{valuation_base}} | {{price_base}} | {{weight_base}}% | {{contrib_base}} |
| 悲观 | {{valuation_bear}} | {{price_bear}} | {{weight_bear}}% | {{contrib_bear}} |
| 最差 | {{valuation_tail}} | {{price_tail}} | {{weight_tail}}% | {{contrib_tail}} |
| **概率加权（DCF 交叉验证锚）** | **{{valuation_anchor}}** | **{{anchor_price}}** | 100% | {{valuation_anchor}} |

**forecast vs actual 兑现度**: {{forecast_vs_actual}}

### 5.6 现在买、赚赔几何？中途扛得住吗？（回报与路径成本）

**一句话**: {{return_oneliner}}

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

### 5.7 一句话：现在的价格给不给机会？（赔率小结）

**结论**: {{odds_verdict}} —— {{odds_why}}。（便宜=有安全垫 / 合理 / 已被买得差不多=没便宜可占 / 把完美未来都买走了=极贵、没安全垫）供 §七。

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

> **说人话**：把前面三件事合起来给最终答案——**①公司在变好吗（§四）× ②价格贵不贵（§五）× ③扛得住吗（§六）**。三个里只要有一个"差"，现在就不是好下注。本章给"是不是好公司 / 该不该买 / 该怎么办"的最终结论，全程说人话。

> **7.1-7.3 只给一句话结论 + 指向出处，绝不复述**（深度在 §四/§五/§六，这里不重复展开）。本章的重心是 7.4。

### 7.1 公司在变好吗？（结论；详见 §四 4.11）

{{state_posterior_verdict}}

### 7.2 价格贵不贵、给不给机会？（结论；详见 §五）

{{odds_verdict}}

### 7.3 兑现前扛得住吗？（结论；详见 §六 6.4）

{{path_verdict}}

### 7.4 最终结论：是不是好公司？该不该买？该怎么办？

> 三个一起看（公司在变好吗 × 价格贵不贵 × 扛得住吗，即**决策三元组**）：只要有一个"差"，现在就不是好下注。

- **三个维度**（决策三元组）: 公司在变好吗 = {{state_posterior_verdict}}｜价格贵不贵 = {{odds_verdict}}｜扛得住吗 = {{path_verdict}}
- **是不是好公司 / 该不该买 / 价格合不合理**（三分结论，各一句人话）: 好公司? {{good_company}} · 好下注（现价）? {{good_bet}} · 好价格? {{good_price}}
- **该怎么办**（**行动档位**，六档之一）: {{action_tier}}（核心仓 / 期权仓（小）/ 等证据临界（观察）/ 不追高（贵但优质）/ 减仓 / 回避）— {{action_rationale}}
- **该等什么**（等到哪个事件再动手）: {{wait_for}}
- **什么情况说明看错了、要走**（**证伪**/退出条件）: {{falsification_exit}}
- **信仰陷阱五弊端自检**（好公司≠好股票/远期当现金流/坏消息当噪音/时间当免费/仓位随信念）: {{faith_trap_selfcheck}}

### 7.5 与 §一 对齐

> §一「投资决断卡」的 5 行结论（是不是好公司 / 故事真不真 / 贵不贵 / 该不该买 / 怎么办）必须与本节 7.4 一致。

---

## §八 舆情与市场情绪

> **说人话**：市场上谁在喊多、谁在喊空，钱往哪儿流——判断现在是"聪明钱在买"还是"散户跟风"。**本章是"谁在买"的权威出处**（§四 4.11④ 懂热点、§五 5.3 都只给一句话、细节看这里）。

**一句话·谁在买?**: {{who_is_buying}}（散户 vs 机构 / 北向 / 杠杆的总判断 + 是不是已经透支）

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
