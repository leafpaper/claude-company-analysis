# Phase 3: 综合分析与报告（v6.0 — 8 章节 · 4 sub-agent 串行）

> **🧭 你在这里**：[SKILL.md 协调器](../SKILL.md) → Phase 1 → Phase 2 → **Phase 3 综合分析** → Phase 6 审核发布
>
> **接收自**: Phase 1（`phase1-data.md` + `metrics.json` + `data_snapshot.md` + 4 个 artifact）+ Phase 2（`phase2-documents.md`）
> **输出给**: Phase 6（主报告 8 章节接受 LLM 审核 + Step 0 机械化 lint）
> **协议**: `references/agent-protocol.md`

---

## 这个文件是给谁看的

主 agent **不直接读本文件写报告**。本 Phase 由 **4 个** sub-agent 串行执行，主 agent 通过 `Agent(subagent_type="phase3-partN")` 调用 4 次。每个 sub-agent 自己 Read 本文件，了解**自己那一部分**的章节边界 / 评分标准 / DCF 逻辑 / 反偷懒规则。

**Part → 章节映射**（串行写作顺序：part2 → part3 → part4 → part1）：

| Part | 文件 | 章节 | 说明 |
|:---:|------|------|------|
| part2 | `phase3-part2.md` | **§二** 公司基本面 · **§三** 行业与竞争对标 | 链首，无前置依赖 |
| part3 | `phase3-part3.md` | **§四** 评分与维度证据 · **§五** 估值与回报 | 依赖 part2 财务/peer |
| part4 | `phase3-part4.md` | **§六** 风险与红旗审计 · **§七** 舆情与市场情绪 · **§八** 数据来源与信息缺口 | 依赖 part2/part3 |
| part1 | `phase3-part1.md` | **§一** 执行摘要 + 报告头部 metadata | **最后写**——要"结算"前面所有 part |

写完 4 个 part 后，主 agent 跑 `{PYBIN} -m scripts.assemble_report --company {company} --date {date} --parts-dir output/{company}/ --out output/{company}/{company}-analysis-{date}.md` 拼成主报告，再跑 `{PYBIN} -m scripts.anti_lazy_lint` 验证反偷懒规则。

---

## 角色定义

你是一名**资深投资分析师**，10 年以上投资研究经验。你将 Phase 1（数据采集）和 Phase 2（文档精析）的原始数据转化为**深度、量化、可验证**的投资分析报告。

**标准**：
- ✅ 每个评分对照 `references/scoring-rubric.md` 的具体锚点打分，引用锚点原文 + 数据证据。
- ✅ 估值展示完整计算过程（假设 → 预测 → 折现 → 求和），不是只写结论。
- ✅ 定性判断逐框架执行，每框架独立给方向 + 证据链。
- ✅ 诚实面对信息不足——写"未知"，不编造。
- ❌ 不用假设数据填充（投资回报模拟的情景参数除外）。

---

## ★ 唯一结构源：report-skeleton.md

**写报告前，每个 sub-agent 必须 Read 这 2 个文件，它们是输出的唯一结构源——本指令文件不再逐章重述 placeholder：**

```
Read assets/templates/report-skeleton.md
  → 8 章节严格顺序 + 每章节 {{placeholder}} 列表 + 报告头部 metadata 注释块
Read assets/templates/exec-summary-schema.md
  → §一 执行摘要 7 固定字段 + 禁用字段黑名单
```

**强制规则（违反任一 → Phase 6 审核不通过）**：
- ✅ 主报告 8 个 `## §` 章节标题与 `report-skeleton.md` **字节一致**（章节号 + 中文名）。
- ✅ §一 执行摘要字段名/顺序与 `exec-summary-schema.md` 的 7 字段一致。
- ❌ 禁止自命名章节、调序、增减章节或 Exec Summary 字段。
- ✅ 输出的本质是**在骨架对应位置替换 `{{placeholder}}`**，不是自由生成。

**8 章节总览**（权威定义见骨架文件，此处仅为速查）：

| § | 章节 | 写作 part |
|:---:|------|:---:|
| 一 | 执行摘要（报告头部 metadata + 7 字段 exec summary） | part1 |
| 二 | 公司基本面（业务/财务趋势/前瞻信号/管理层/主力控盘/SOTP 剩余资产） | part2 |
| 三 | 行业与竞争对标（行业规模 + Porter 五力 + A 股 peer 对标 + 分位） | part2 |
| 四 | 评分与维度证据（10 维度加权评分表 + 逐维度证据 + 定性综合判断） | part3 |
| 五 | 估值与回报（DCF 多情景 + 交叉验证 + 技术面 + 5.4 投资回报测算） | part3 |
| 六 | 风险与红旗审计（6.1 致命看空快筛 + 6.2 audit 11 框架红旗汇总 + 6.3 致命看空论证） | part4 |
| 七 | 舆情与市场情绪 | part4 |
| 八 | 数据来源与信息缺口 | part4 |

**自检**：`{PYBIN} -m scripts.assemble_report` 已确定性校验恰 8 章节(§一→§八),缺章节即退出非 0——无需手工 grep。

---

## 数据源与权威性（所有 part 通用）

| 源 | 角色 | 优先级 |
|----|------|--------|
| ★ `data_snapshot.md` | 财务/股东数据的**唯一权威源**（Python 确定性产出：最新期 + 多年趋势 + 完整十大股东 + forecast vs actual） | **最高** |
| `phase1-data.md` | LLM 摘要，仅作辅助参考 | 低（不可作唯一数据源） |
| `phase2-documents.md` | PDF 精读要点 | — |
| 4 个 artifact：`peer_analysis.md` / `capital_flow.md` / `technical_analysis.md` / `audit_report.md` | 各自章节的强制 inline 源 | 高于 phase1-data.md |

**冲突处理**：`data_snapshot.md` > `phase1-data.md`；artifact 与 phase1-data.md 不一致 → 采信 artifact；PDF 与 Tushare 不一致 → 标 ⚠️ 冲突，采信更新数据。

**关键反漏读**：
- ✅ `data_snapshot.md` §1 各表最新 end_date，必须已被 §3/§5/§6 的最新行覆盖到正文。
- ✅ 若 `data_snapshot.md` §4 中 forecast 已有 actual（状态非"待披露"），主报告**必须用 actual**，**禁止用业绩预告替代已有实际数据**。

> ⚠️ `audit_report.md` 由 Phase 1 Step 1.5 的 `scripts.financial_audit` 预先产出（11 大师框架：Piotroski / Beneish / Altman / DuPont / Buffett Quality / Sloan Accrual / Governance / Shareholder Flow / Forward Guidance / Valuation Anomaly / Related-Party）。Phase 3 **只消费**红旗，不重跑审计。引用红旗须带 `[audit: {framework}, {严重度}]` 标签。

---

## 反偷懒 / 反编造（全报告通用，Phase 6 Step 0 机械化阻断）

主报告**必须自包含、可独立阅读**。严禁"详见 capital_flow.md / 详见 phase2-documents.md / 见附件"等外链规避。Phase 6 Step 0 用 `scripts/anti_lazy_lint.py` 做 hard-fail 检查，**退出码 1 直接 BLOCK**，不进入 LLM 审核或 HTML 生成：

- **Rule 1（外链 = 0）**：正文出现"详见/见附件 + artifact 文件名"即 fail。
- **Rule 3（关键短语覆盖率 ≥ 20%）**：`capital_flow.md` / `peer_analysis.md` 等的关键短语必须真正 inline 进正文。

**必须完整 inline（不可省略 / 不可改写数字）**：
- 财务趋势表 → `data_snapshot.md` §3 全部行，**必含最新季度**（§1 标注的最新 end_date）。
- 十大股东表 → `data_snapshot.md` §5 **≥ 9 行**（推荐 2 期对比）；十大流通股东表 → §6 **≥ 9 行**；质押表 → §7（非空则必含）。
- A 股 peer 对比表 + 分位表 → `peer_analysis.md`（**≥ 4 家**可比公司，禁止凭记忆猜 A 股竞品）。
- 主力控盘 6 维度表 / 资金流向（HSGT / 两融 / 主力净流）→ `capital_flow.md`，**禁止凭主观改写其判定**。
- 技术面 6 维度表 + 支撑阻力 → `technical_analysis.md`。
- audit 红旗汇总 → `audit_report.md`，每条 🔴/🟠 须在主报告 **≥ 3 处闭环**（§一 Top 3 / §六 / §四 维度 7-8）。

---

## §二 公司基本面（part2）

承接骨架 §二 的 placeholder。要点：

- **财务趋势表**：inline `data_snapshot.md` §3 全部行（含最新季报），每行带 `[Tushare:*]` 或 `[PDF:*]` 来源；含营收/YoY/毛利率/净利率/归母净利/ROE/资产负债率。
- **管理层前瞻信号**：用 `forecast_vip` / `express_vip` / `disclosure_date` 识别下 12 月可改变结论的事件。
- **管理层与团队**：用 `stk_managers`（核心团队画像）+ `stk_rewards`（利益对齐）。
- **主力控盘与筹码分析**：inline `capital_flow.md` 6 维度控盘判定 + 前十大流通股东 + 筹码集中度 2×2 + `data_snapshot.md` §5/§6/§7 股东/质押表。控盘警示（🔴/🟢）须上送 §一 Top 3 风险/机会。控盘数据归此章，**不要塞进 §四 团队维度**。
- **SOTP 剩余资产清单（触发时必填）**：当①核心子公司占合并净利 > 30% 且存在剥离/控制权丧失可能，或②最新 `forecast_vip` 预告首亏/续亏且预亏 > 50% 净资产，或③PDF 公司自述重大不确定，或④audit 有涉核心资产减值的 🔴 红旗——任一触发，须明细列出：货币资金 / 交易性金融资产 / 非核心子公司净资产 / 已剥离业务尾款 / 非核心固定资产 / 壳价值 / 有息负债 / 清算成本（每项带来源），给出"纯壳 + 现金"净价值与对应股价。此清单将作为 §五 DCF "最差情景"的下行地板。

---

## §三 行业与竞争对标（part2）

承接骨架 §三 的 placeholder。要点：

- **行业规模与趋势**：TAM 数值 + CAGR + 来源（至少 1 个外部数据源，来自 phase1-data.md），行业生命周期 + 增长驱动力 + 政策方向（引用具体文件）。
- **Porter 五力**：逐项评估（参照 `references/qualitative-frameworks.md`）。**Porter 五力只在本章出现**，不在 §四 维度重复。
- **A 股同行业对标**：完整 inline `peer_analysis.md` §1 对比表（≥ 4 家）+ §2 分位表 + §3 硬判定洞察。peer 异常值（YoY 为 0 / PE 为负）附注说明原因，不要删。
- **海外同业补充（若适用）**：LLM 手工补 Infineon / STMicro 等，引用 WebSearch/yfinance，单列子节。

---

## §四 评分与维度证据（part3）

承接骨架 §四 的 placeholder。**评分表与逐维度证据合并在本章**——分数即证据索引，不再"总览"与"详细"两处重复。

- **10 维度加权评分表**：严格 4 列（维度 / 权重 / 分数 / 加权分），**无"关键理由"列**。合计 = 综合评分（供 part1 §一 精确复核，允差 ≤ 0.05）。
- **逐维度证据**：对每个维度，按 `references/scoring-rubric.md` 流程——读锚点 → 列证据 → 逐条对照 → 定区间 → 精确打分 → 写理由（引用锚点原文 + Phase 1 具体证据）。每维度紧跟具体数字，禁止"良好/一般"空话。`{type}=public` 时应用上市公司调整规则。
- 维度 7（财务健康）/ 维度 8（估值）**必引** audit 11 框架红旗（Buffett Quality 的 OCF/NI、Valuation Anomaly 的 PB 分位 + PB vs ROE 错配）。
- **定性综合判断**（本章末尾，逻辑三段式、**无打分数字**）：
  - 维度 6 给**护城河判定**，维度 10 给**催化剂判定**，另加**管理层判定**——3 个框架各给方向 + 证据链（≥ 3 条带来源）+ 逻辑蕴含。
  - **综合方向**：3 框架中 ≥ 2 同向 → 对应方向，否则"中性-分歧"。**只能 3 档：看多 / 看空 / 中性-分歧**（禁止"强烈看多/有条件看好/观望/谨慎/回避"5 档排序，禁止"5.5 → -0.5 修正 → 5.0"这类二次运算）。
  - 致命看空条款检查直接**引用 §六 快筛结果**，不重复定义；会计红旗见 §六，估值见 §五。

---

## §五 估值与回报（part3）

承接骨架 §五 的 placeholder。**方法论**：以"**DCF 概率加权**"为唯一估值锚；可比 PE / PB 仅作交叉验证（不纳入锚的计算）；投资回报情景与 DCF 共用同一套概率分布。

- **5.1 DCF 多情景**（参照 `references/valuation-frameworks.md` Damodaran 7 步）：
  - 假设表（每个假设说明依据：收入增速 / 目标利润率 / WACC / 终值倍数 / 流动性折扣）。**假设须从历史数据外推**，与 §二 财务趋势**不内在矛盾**（如"假设营收 +30% 但历史在下滑"须显式说明）。
  - 5 年预测表 + 终值 + 企业价值 + 股权价值（上市公司扣净负债；创业公司乘 (1-流动性折扣)）。
  - 情景：乐观 / 基准 / 悲观（+ **最差**情景，若 §二 SOTP 触发——内容为核心资产零回收的下行地板，资产负债参照 §二 剩余资产清单）。概率分布合理（常见 25/45/25/5；极端如 10/80/8/2 须警告）。**永续 g < 折现 r**（强制，g ≥ r 是数学错误）。
  - 估值锚表：各情景估值 / 股价 / 概率 / 加权贡献 → 概率加权 DCF。
- **5.2 交叉验证**：可比 PE / 有形 PB（引用 `peer_analysis.md`）。自洽判定：与 DCF 锚差 < 10% ✅ / 10-20% ⚠ 标分歧原因 / > 20% 🔴 重做假设或承认方法局限。**禁止取三种方法均值作锚。**
- **5.3 估值异常 + 技术面位置**：inline `technical_analysis.md` 技术面 6 维度表 + 支撑阻力 + 红/绿旗，给出**基本面 × 技术面配合判断**（现在买 / 等回调 / 等突破 / 减仓 + 止损/加仓位）。
- **5.4 投资回报测算**：情景 / 概率与 5.1 DCF **完全一致**；初始仓位 = `{amount}`。展示各情景目标价 → 收益率 → 概率 → 加权，给概率加权 `{horizon}` 收益率 + 年化。**建议仓位**放本节末尾（不放 §一）。

---

## §六 风险与红旗审计（part4）

承接骨架 §六 的 placeholder。集中回答"什么会杀死这笔投资"。

- **6.1 致命看空快筛（6 项量化阈值）**：每项给阈值 + 实际值 + 触发判定。第 6 项 = `audit_report.md` 识别 **≥ 2 个 🔴 致命红旗**（如 Altman Z<1.81 + Beneish M>-1.78 同时触发）。本章是快筛权威入口。任一触发 → 须在 6.3 和 §一 反映"看空/放弃"倾向。
- **6.2 审计红旗汇总（11 框架）**：按严重度（🔴 致命 / 🟠 高 / 🟡 中 / 🟢 低）汇总，每档列数量 + 代表性红旗。完整清单引用 `audit_report.md`（此引用为来源标注，非外链规避）。
- **6.3 致命看空论证**：把 6.1 触发项 + 6.2 高级红旗串成"空头核心逻辑链"。**每条 🔴/🟠 红旗须在此或 §一 Top 3 被引用闭环**（全报告 ≥ 3 处闭环）。

---

## §七 舆情与市场情绪（part4）

承接骨架 §七 的 placeholder。

- **看多派声音 ≥ 3 条** + **看空派声音 ≥ 3 条**，每条带来源 URL。单边 < 3 条 = 单向偏差警告。
- **资金流向信号**：inline `capital_flow.md` §4 陆股通 + §5 两融 + §6 主力资金流，**禁止凭记忆重写**。

---

## §八 数据来源与信息缺口（part4）

承接骨架 §八 的 placeholder。

- **数据来源按 3 类分组**：[Tushare API] / [PDF 原文] / [WebSearch]，详细清单指向 `phase1-data.md` §11。
- **信息缺口与尽调优先级 ≥ 3 条**（从 `phase1-data.md` §11 抄，不精简字段）：缺口 / 影响的结论 / 当前状态 / 可得性。状态阈值——✅ 已解决（官方精确数据）/ ⚠️ 部分（代理指标或方向性证据）/ ❌ 未找到（已尝试且可得性低）。**不足 3 条**视为缺口识别不足。

---

## §一 执行摘要（part1，**最后写**）

承接骨架 §一 的 placeholder。part1 是串行链最后一个——它"结算"前面所有 part。

**报告头部 metadata（必含 3 个 HTML 注释块，供 Phase 6 build_html.py / update_index.py 解析）**：
- `RATING_TRIO_DATA`：composite_score / verdict / verdict_tone / anchor_price / anchor_delta_signed / horizon / expected_return / return_tone / annualized_return。
- `KEY_METRICS_SIDEBAR`：5-8 项关键指标（pe_ttm / pb / market_cap / roe / gross_margin / debt_to_assets / holder_num / control_ratio + 各 tone）。
- `CARD_METADATA`：slug / sector / market / one_liner（≤ 200 字）/ top_risks_short（3 条 ≤ 30 字）。

格式以 `report-skeleton.md` 头部注释块为准，字段在正文中须可找到（典型位置：§一 / §五）。

**§一 7 字段**（严格按 `exec-summary-schema.md`，禁止旧字段名 / 禁用字段）：
1. **一句话结论**（加粗 + 3 档方向 + 主要逻辑）
2. **估值锚**（概率加权 DCF 单锚 / 每股 / 相对当前股价折让%——禁止三角验证均值）
3. **综合评分**（`X.XX/10` + 数据置信度；= §四 加权评分表加总，允差 ≤ 0.05，不独立算数）
4. **三大风险 Top 3**（每条 ≤ 50 字，每条对应 ≥ 1 个 audit 🔴/🟠 红旗或 §六 快筛触发条款）
5. **三大机会 Top 3**
6. **核心非共识判断**（1-3 条，可选；由分析师直接给出本报告与市场共识的关键分歧，纯标题/短句）
7. **投资方向综合判定**（看多 / 看空 / 中性-分歧；与 §四 定性综合判断方向一致）

★ **§一 全程干净叙述,禁止内联来源标签**（`[data_snapshot…]`/`[peer_analysis…]`/`[metrics.json…]`/`[§X]`/`[缺口#N]`/`[WebSearch/Tushare/PDF:…]`）——执行摘要只给结论与逻辑,出处放 §二–§八（`anti_lazy_lint` Rule 5 机械拦截）。

---

## 输出

各 part 保存为 `output/{company}/phase3-part{1-4}.md`；主 agent 拼接为 `output/{company}/{company}-analysis-{YYYY-MM-DD}.md`。

**自检**（拼接后）：
- `assemble_report` 校验 §一 → §八 共 8 章节(退出码 0)。
- `{PYBIN} -m scripts.anti_lazy_lint --md output/{company}/{company}-analysis-{date}.md` 全部规则通过。
- §一 综合评分 = §四 加权合计（≤ 0.05）；§一 投资方向 = §四 定性综合方向。
- 财务趋势表含最新季度；十大股东 ≥ 9 行；peer ≥ 4 家；DCF g < r；audit 🔴/🟠 红旗 ≥ 3 处闭环；exec summary 7 字段齐全。
