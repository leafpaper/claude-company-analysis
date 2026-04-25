# Phase 6: 审核与发布（v4.3）

> **🧭 你在这里**：[SKILL.md 协调器](../SKILL.md) → Phase 5 → **Phase 6 审核与发布**（终点）
>
> **接收自**: 所有上游产出（`phase1-data.md` / `phase2-documents.md` / 主报告 `{company}-analysis-*.md` / `phase4-personas.md` / `phase5-variant-perception.md`）
> **输出**: `*.html` + `phase6-review-log.md` + GitHub Pages（leafpaper/Inves-Report）
> **v4.3 说明**: 审核 **22 项**（v4.2 新增 #19/#20 估值一致性+SOTP；v4.3 新增 #21 HTML 资产加载 + #22 Exec Summary 7 字段）+ Part D 5 步穷举补查保留
> **v4.3 HTML 规则**: 必须从 `assets/html/base.html` + `assets/html/styles.css` + `assets/html/components.html` 加载,**禁止凭记忆重写 CSS 或自创变量名**
> **质量门控**: 全部 22 项通过；每个缺口有 ✅/⚠️/❌ 状态；HTML section 数 = 15；Phase 5 洞察的 9 字段在 HTML 中完整；CSS 变量数 ≥ 16

---

## 角色定义

你有两个身份：

**身份A — 报告质量审计师**：逐项审核分析报告，检查逻辑错误、数据问题、夸大描述、遗漏考虑。你**不能改变分析结论**，只能标记问题并修正事实/计算/格式错误。

**身份B — 发布经理**：将审核通过的报告转化为HTML可视化版本，并上传到GitHub Pages。

---

## 前置条件

1. `output/{company}/{company}-analysis-{date}.md` 存在（Phase 3）
2. `output/{company}/phase4-personas.md` 存在（Phase 4）
3. HTML模板指南可用：`references/html-template-guide.md`

---

## 基本事项

1. 审核只标记和修正问题，**不改变分析结论或评分**
2. 每个审核项记录 PASS/FAIL + 具体说明
3. 如发现严重问题（如计算错误），在修正后标注 `[Phase 5 修正]`
4. HTML 版本必须与 MD 内容完全一致——不省略任何章节

---

## Part A: 报告审核

### Step 0 (v4.7 强制门控): 机械化深度检查 — 任一规则 fail 直接 BLOCK

**为什么必须先跑这一步**: 23 项 LLM 自审看不见自己的"懒"(写者=审者)。机械化的 grep + 字数 + diff 是确定性的, 能挡住下列懒惰模式:
- "详见 capital_flow.md / phase2-documents.md" 这种把内容推到附件的外链
- §四/§五/§六 等深度章节字符数过低(摘要式填充)
- artifact 关键数字短语没有 inline 到主报告
- §一~§十五 章节标题被 LLM 重命名(如 §四 公司基本面 → §四 业务概况)

**执行**:
```bash
python3 -m scripts.anti_lazy_lint --md output/{company}/{company}-analysis-{date}.md
# 退出码 0 = 进入下面的 23 项 LLM 审核
# 退出码 1 = BLOCK, 必须返回 Phase 3 修复后再来; 不允许 LLM 自审"绕过"机械检查
```

**4 条规则 (全部 hard fail)**:

| # | 规则 | 阈值 | 例外白名单 |
|:---:|------|------|---------|
| 1 | 外链引用扫描 (详见 xxx.md / 见 phaseX.md / [xxx](xxx.md)) | 命中 = 0 | §十二 允许引用 phase5-variant-perception.md / §十三 允许 phase4-personas.md / §十五 允许 audit_report.md 等 |
| 2 | 章节最小字符数 (中文+字母+数字) | 见 `assets/validation/report-checklist.json:anti_lazy_lint` | – |
| 3 | Artifact 关键短语覆盖率 (capital_flow / peer / tech / audit) | overall ≥ 40% AND 单 artifact ≥ 20% | 美股/港股无 artifact 时跳过 |
| 4 | 章节标题与 `assets/templates/report-skeleton.md` 字节一致 (去括号注释后) | 0 differences | – |

**修复指引**:
- Rule 1 命中 → 删除外链, **inline 完整内容**(表格 / 数字 / 段落)到对应章节
- Rule 2 不足 → 补充该章节内容深度(展开证据链 / 加表格 / 加数字事实)
- Rule 3 不足 → Read 对应 artifact, 把关键数字短语真实搬入主报告
- Rule 4 不一致 → 把 ## §X 标题改回 skeleton 的字面字符串(允许加括号注释如 "## §四 公司基本面(v4.5 含主力控盘)")

**Step 0 通过后才能进入下面 22 项 LLM 审核 + Part B HTML 生成**。

---

### 审核清单（逐项执行，记录结果）

| # | 审核项 | 通过标准 |
|---|--------|---------|
| 1 | **逻辑一致性** | 评分是否与引用的证据方向一致？（高分=正面证据，低分=负面证据） |
| 2 | **计算准确性** | 加权分计算是否正确？综合分公式是否正确？定性修正计算是否正确？ |
| 3 | **夸大检查** | 是否存在无依据的夸张描述？（如"行业最佳"但无数据支撑） |
| 4 | **遗漏检查** | 是否有明显的风险/问题未被讨论？ |
| 5 | **数据时效性** | 旧数据是否标注 `[历史数据]`？是否存在用旧数据支撑当前结论？ |
| 6 | **来源完整性** | 关键论断是否都有来源URL？信息来源列表是否完整？ |
| 7 | **章节完整性** | 所有必需章节是否存在？10维度详细分析是否全覆盖？ |
| 8 | **数据自洽** | 不同章节引用的同一数据是否一致？ |
| 9 | **基本面覆盖** | 行业基本面和公司基本面是否作为独立章节充分分析？ |
| 10 | **舆情平衡** | 看好/看衰观点是否均衡？是否都有来源？ |
| 11 | **假设透明度** | 投资回报模拟中的假设是否全部明确标注？ |
| 12 | **角色结论质量** | Phase 4 角色是否保持了各自风格？是否引用了报告数据？ |
| 13 | **差异化洞察质量** | §十二 每条洞察是否 **9** 字段齐全（v4.1 从 13 精简；含 ★数学推导 + ★信号强度合并字段 Level/置信度/时间窗）？是否至少 1 条看空方向？是否至少 1 条是 AI 自主感知议题？Executive Summary 是否列出 Top 3？**Level C 附录是否存在于独立文件 `phase5-variant-perception.md` §3**？独立文件**不重复**主报告洞察卡片？ |
| 14 | **评分独立性 + 理由列删除（v4.1）** | §二 评分总览是否**只 4 列**（维度/权重/分数/加权分），**无"关键理由"列**？10 维度分数是否未因洞察被调整？**无"定性修正系数 -0.5"这种打分式写法**？ |
| 15 | **Persona 洞察回应** | 每位 persona 是否各自选了 2-3 条洞察深度回应？不同 persona 选择是否有差异？ |
| **16** | **定性判断为逻辑三段式（v4.1 强化）** | §十一 定性判断是否用"核心问题 → 判断 → 证据链 → 逻辑蕴含"模板？**只有 3 个框架**（护城河/管理层/催化剂，**不含估值判断**）？开头是否引用"估值见 §九，会计红旗见 audit_report.md"？**致命看空条款是否直接引用 §三快筛结果**（不再重复定义 6 项）？是否**无打分数字**？**是否出现"修正值 ±X"/"调整后 X"/"+Y%"等打分换壳表述？是否出现"强烈看多/有条件看好/谨慎/回避"等 5 档连续排序？**（命中任一视为不合格）综合结论是否严格为 "看多方向/看空方向/中性-分歧" 3 档？ |
| **17** | **缺口补查闭环（v3 新增）** | §十三 "信息缺口与尽调优先级"表格中每一项是否有**明确状态**（✅已解决 / ⚠️部分 / ❌未找到）？是否列出了 Phase 1 尝试的查询路径？**若有 ❌ 未找到的条目，Part D 是否已执行补查？** |
| **18** | **数据来源可审计（v3 新增）** | 关键财务数据（§4 财务趋势表、§5 10 维度、§9 估值）是否都有 `[Tushare:*]` 或 `[PDF:*]` 来源标签？是否无任何`[证券之星算法]` / `[某财经网摘要]`作为关键数据来源？ |
| **19** | **估值-回报一致性（v4.2 新增）** | §九 估值锚（DCF 概率加权）和 §十 投资回报测算是否**共用同一组情景**（乐观/基准/悲观 ± 最差）和同一组概率？是否禁止"三角验证均值"作为综合锚？交叉验证的可比倍数/PB 差距 > 20% 是否已解释分歧原因？**若审核发现 §九 锚 ≠ §十 基准或概率分布不同则不通过**。 |
| **20** | **核心资产剥离风险 SOTP（v4.2 新增）** | 若满足以下**任一**触发条件：①核心子公司占合并净利 > 30% 且存在剥离/控制权丧失可能；②`forecast_vip` 预亏 > 50% 净资产；③PDF 自述"若 XX 发生面临阶段性下调"；④audit_report 🔴 涉及核心资产减值 —— 主报告 §四 是否有"若核心资产被剥离的剩余资产清单"子节（含货币/金融资产/非核心子公司/已剥离尾款/非核心固定资产/壳价值/有息负债/清算成本）？§九 是否有"最差情景"（3-10% 权重）作为下行地板？**若触发但缺其中任一则不通过**。 |
| **21** | **HTML 资产加载（v4.3 新增）** | Phase 6 Part B 生成 HTML 是否**从 `assets/html/base.html` 加载骨架**？是否**内联了 `assets/html/styles.css` 完整内容**（`grep -c '^\s*--c-' *.html` ≥16 个 CSS 变量）？是否使用了 `assets/html/components.html` 中的 9 个组件 class（`grep -c 'class="(score-ring|dimension-bar|scenario|expected-return|team-card|risk-item|timeline|sentiment-bar|valuation-range)"'` ≥8）？是否 15 个 `<div class="section"` 对应 §一～§十五 且 id 属性正确？**禁止 Claude 自写 CSS 变量或组件 class**。 |
| **22** | **Executive Summary 7 字段 schema（v4.3 新增）** | §一 执行摘要是否严格按 `assets/templates/exec-summary-schema.md` 的 7 固定字段展开？字段名与顺序字节一致（一句话结论 / 估值锚 / 综合评分 / 三大风险 / 三大机会 / 核心非共识观点 / 投资方向综合判定）？**是否出现禁用字段**：综合评级 / 量化分 / 定性修正 / 调整后分 / 建议仓位 / 尽调优先级（出现任一则不通过）？**章节标题 15 个 `## §` 是否与 `assets/templates/report-skeleton.md` 字节一致**？ |
| **23** | **Phase 1 结构化 artifact 消费（v4.4 新增）** | Phase 1 生成的 4 个 artifact 必须被 Phase 3 对应章节**真实消费**（Read 后搬运数据，不凭记忆改写）: ① `peer_analysis.md` → §八 ② `capital_flow.md` → §四（主力控盘子节）+ §七（资金流向信号子节）③ `technical_analysis.md` → §九 9.4 技术面位置 ④ `audit_report.md` → §一 Top 3 风险 + §三 快筛 #6。**若 artifact 存在（A 股）但对应章节未见相应表格 → 不通过**。美股/港股可缺 peer/capital/tech 三者，但须显式标注“本市场无 Tushare 分析，改用 yfinance/WebSearch 手工”。 |

### 修正规则

- **轻微问题**（格式/拼写/计算偏差）：直接修正，标注 `[Phase 5 修正]`
- **严重问题**（结论与证据矛盾/重大遗漏）：标记但**不改变结论**，在审核日志中详细说明
- **致命问题**（数据造假/严重计算错误）：修正错误，标注 `[Phase 5 重大修正]`，在报告开头加警示

---

## Part B: HTML 生成（v4.6.1 — 脚本化, 不丢章节）

### ★ 推荐: 直接调用 `scripts/build_html.py`(v4.6.1 一键转换)

```bash
python3 -m scripts.build_html --company {company} --version 4.6
```

此脚本会:
1. 读 `assets/html/base.html` + `styles.css` + `components.html`
2. 读 `output/{company}/{company}-analysis-{date}.md`
3. 解析结构化注释块(CARD_METADATA / RATING_TRIO_DATA / KEY_METRICS_SIDEBAR)
4. 按 ^## 切 MD section,**前 15 填固定 placeholder,第 16+ 追加到 extra_sections** (避免 v4.6 之前的"附录丢失"bug)
5. 填 rating-trio / metric-strip 面板
6. 替换 hero meta 占位符
7. 自检输出 section 数 + 组件命中率

验证门槛(脚本自动检查): HTML section 数 >= MD ## 章节数;若少于则报警并返回非零退出码。

### ★ 备选: 手动流程(LLM 按旧指令执行,但 v4.6.1 已不推荐)

```
Step 0: Read assets/html/base.html
        Read assets/html/styles.css
        Read assets/html/components.html
        — 这三个文件是 HTML 的唯一真相源

Step 1: 复制 base.html 到 output/{company}/{company}-analysis-{date}.html

Step 2: 将 styles.css 完整内容替换 base.html 中的
        <!-- PLACEHOLDER: styles.css 整体内联到此处 --> 注释
        (禁止精简 / 删变量 / 改颜色值)

Step 3: 替换 Header Hero 区域的 {{company_name}} / {{ticker}} / {{report_date}}
        / {{latest_close}} / {{market_cap}} / {{pb}} / {{anchor_price}} / {{price_tail}}

★ Step 3.5 (v4.6 新增): 填充前置评级卡 + 侧边栏关键指标
        从主报告 §一 Executive Summary 抽取:
          composite_score / verdict / verdict_tone / anchor_price /
          anchor_delta_signed / horizon / expected_return / return_tone / annualized_return
        复制 components.html 中 "v4.6-1 前置评级三件套" 片段,填入 <!-- PLACEHOLDER: rating_trio --> 占位
        (3 张 rating-card: 评分 / 估值锚 / 期望收益)

        从 phase1-data.md §2.3 + audit_report + capital_flow 抽 5-8 个关键指标:
          PE TTM / PB / 市值 / ROE / 毛利率 / 资产负债率 / 股东户数 / 控盘度
        复制 components.html "v4.6-3 粘性侧边栏关键指标" 片段,填入 <aside class="metric-sidebar"> 的 <!-- PLACEHOLDER: key_metrics --> 占位
        (metric-row tone 判定: ROE<0 / 资产负债率>60% / 家族持股>=40% → negative/risk/critical)

Step 4: 逐章节填充 15 个 <!-- PLACEHOLDER: section_N_xxx --> 占位:
        - 用 markdown 转 HTML (表格 → <table>, 列表 → <ul>, 加粗 → <strong>)
        - 当章节需要可视化组件时从 components.html 复制对应片段并填充数据
        - §一 三大风险 → 使用 v4.6-2 彩条风险卡 (risk-card-v2), tone 按致命/高/中/低分
        - §八 Peer 对标 → 使用 v4.6-4 comparison-card (你 vs peer 中位)
        - §十二 差异化洞察 → 使用 variant-perception 卡片
        - §四 财务趋势或 §六 维度 3 盈利 → 可选 v4.6-6 heatmap-grid (历史趋势可视化)

Step 4.5 (v4.6 新增): 深度内链(可选增强可读性)
        在主报告中如果 §一 提到 "游戏业务崩塌 -94%",可加:
          <a href="#detail" class="deep-link">维度 3 证据</a>
        点击跳到 §六 并高亮脉冲
        其他示例: §三 快筛触发 → 链到 §六 对应维度; §十二 洞察 → 链到 §九 估值影响

Step 5: 自检 (v4.6 更新):
        - grep -c '<div class="section"' 应 = 15
        - grep -c '^\s*--c-' 应 ≥ 16 (CSS 变量未被删)
        - 9 个基础组件 class 命中率 ≥ 8/9
        - v4.6 新组件 (rating-trio / metric-sidebar) 必须出现在 HTML 中
        - 所有 {{placeholder}} 必须已被替换 (grep 后应无 `{{`)
        - `<div class="container has-sidebar">` 存在 (验证两栏布局)
        - `<aside class="metric-sidebar">` 内 metric-row 数量 ∈ [5, 8]
        - `.rating-trio .rating-card` 数量 = 3
```

**绝对禁止（v4.3 强化）**:
- ❌ **禁止凭记忆重写 CSS** — 必须整体内联 `styles.css` 文件
- ❌ **禁止自创 CSS 变量名**（如 `--primary` 取代 `--c-primary`;`--accent` 取代 `--c-yellow` 等）
- ❌ **禁止自命名组件 class** — 必须用 components.html 中定义的 9 个标准 class
- ❌ **禁止"概括/合并/简化"** MD 章节 — 15 个 section 必须一一对应

**HTML 15 章节要求**（严格与 `assets/templates/report-skeleton.md` 对齐）:

| # | 章节 | MD 骨架标题 | HTML section id |
|---|------|--------|---------|
| 1 | 执行摘要 | `## §一 执行摘要` | `exec-summary` |
| 2 | 评分总览 | `## §二 事实评分总览（10 维度）` | `scoring` |
| 3 | 快速筛选 | `## §三 快速筛选（致命看空条款 - 6 项）` | `screening` |
| 4 | 公司基本面 | `## §四 公司基本面` | `fundamentals` |
| 5 | 行业与竞争格局 | `## §五 行业与竞争格局` | `industry` |
| 6 | 10 维度详细证据 | `## §六 10 维度详细证据` | `detail` |
| 7 | 网络舆情 | `## §七 网络舆情与市场情绪` | `sentiment` |
| 8 | 可比公司对标 | `## §八 可比公司对标` | `peers` |
| 9 | 估值与回报模拟 | `## §九 估值与回报模拟` | `valuation` |
| 10 | 投资回报测算 | `## §十 投资回报测算（与 §九 共用情景）` | `invest-sim` |
| 11 | 定性判断 | `## §十一 定性判断（3 框架，v4.1 — 无打分）` | `qualitative` |
| 12 | 差异化洞察 | `## §十二 差异化洞察（Phase 5 回写 — 9 字段卡片）` | `variant`（加 `.variant-perception` class） |
| 13 | 多角色投资结论 | `## §十三 多角色投资结论（Phase 4 回写 — 3 角色 × 3 段精简版）` | `personas` |
| 14 | 信息缺口与尽调 | `## §十四 信息缺口与尽调优先级` | `gaps` |
| 15 | 数据可审计性 | `## §十五 数据可审计性（时效性 + 来源 3 类分组）` | `sources` |

保存为 `output/{company}/{company}-analysis-{date}.html`

---

## Part C: GitHub Pages 发布(v4.6 — 主页动态联动)

> **v4.6 重大变更**: 不再手工编辑 `index.html` 加卡片。Phase 6 Part C Step 4 调用 `scripts/update_index.py` 自动抽取 card-metadata + upsert `data/reports.json`,主页通过 JS `fetch` 动态渲染。index.html 只有骨架,**永不需手工改**。

**目标仓库**: `leafpaper/Inves-Report`

**执行步骤**(v4.6 自动化):

```
1. 确保仓库已克隆:
   cd /tmp/Inves-Report-v2 && git pull origin main
   (如不存在则 git clone)

2. 创建/更新公司报告目录:
   mkdir -p /tmp/Inves-Report-v2/reports/{CompanySlug}_{CompanyNameCN}

3. 复制 HTML 报告:
   cp output/{company}/{company}-analysis-{date}.html /tmp/Inves-Report-v2/reports/{CompanySlug}_{CompanyNameCN}/分析报告_dashboard.html

4. ★ 自动更新主页卡片数据(v4.6 替换旧的"手工编辑 index.html"):
   python3 -m scripts.update_index --company {company} \
       --repo /tmp/Inves-Report-v2 \
       --force

   这会:
   - 解析主报告 MD 的 <!-- CARD_METADATA / RATING_TRIO_DATA / KEY_METRICS_SIDEBAR --> 结构化注释块
   - 生成 output/{company}/card-metadata.json
   - 复制到 /tmp/Inves-Report-v2/reports/{slug}/card-metadata.json
   - upsert 到 /tmp/Inves-Report-v2/data/reports.json
   - 主页 JS 会从 reports.json 自动渲染新卡片 + 更新统计数字

   若解析结果不理想(老报告未带结构化注释块), 会走 regex fallback 并输出警告。
   **v4.6 起新生成的报告必须在 hero 后带 CARD_METADATA/RATING_TRIO_DATA/KEY_METRICS_SIDEBAR
   三个注释块**(见 assets/templates/report-skeleton.md)。

5. 提交推送(v4.6 新 — 改动由 4 项减为 3 项: HTML + card-metadata + reports.json):
   cd /tmp/Inves-Report-v2
   git add reports/{CompanySlug}_{CompanyNameCN}/ data/reports.json
   git commit -m "feat: 新增/更新 {company} 投资分析报告"
   git push origin main
```

**失败处理**: 如 git push 失败, 保存 HTML 到本地并通知用户手动上传。

**向后兼容 v4.5 及之前的老报告**:
- 老报告未带 CARD_METADATA 注释块, update_index.py 会走 regex fallback
- 某些字段(sector/expected_return)可能不准, 用户需手动检查 reports.json 对应条目
- v4.6 起的新报告必须带注释块(Phase 3 骨架 assets/templates/report-skeleton.md 已强制要求)

---

## Part D: 缺口补查闭环（v3 新增 → v3.1 强化）

### 触发条件（两种）

**触发 A**: Part A 审核清单第 17 项发现 §十三"信息缺口"表格中有**状态为 ⚠️ 或 ❌ 的条目**。

**触发 B（反向扫描，v3.1 新增）**: Phase 1 §11 条目数 < 3 **或** Phase 3 §十三 条目数 < 3 → 自动降级报告置信度 **-0.5**，并触发 Part D 反向扫描：强制从以下清单里挑至少 3 项作为"潜在缺口"执行 5 步补查：
- 最新报告期资产减值损失明细
- 核心子公司/参股公司近 12 月动态
- 股权激励对象明细（有激励计划时）
- 分业务/分产品毛利率（若 Phase 5 任一洞察依赖）
- 关联方交易金额
- 对外担保变动

### 5 步穷举补查流程（★顺序调整，由粗到精）

对每一条 ⚠️ / ❌ 缺口，依次执行（**找到即停止**，但每步必须登记结果）：

#### Step D.1: WebFetch 巨潮资讯索引（先从公告入手）

```
WebFetch http://www.cninfo.com.cn/new/disclosure/stock?stockCode={code}&orgId=...
→ 获取该股所有公告标题列表
→ 按关键词过滤，WebFetch 相关公告 PDF
```

**为什么放第 1**: 缺口多半来自**未读的公告**（如"超隆光电出售/破产"这类临时公告）。巨潮覆盖面最广且时效最高。

#### Step D.2: WebFetch 公司官网 IR

```
1. 定位公司官网（从 stock_basic.parquet 的 website 字段或 Google 搜 "{company} 官网"）
2. WebFetch {domain}/investors 或 /ir
3. 翻找"公告""投资者关系""新闻"页
```

#### Step D.3: PDF 原文全文搜索（用 pypdf 正则）

对所有已下载的 PDF 做搜索：

```bash
python3 -m scripts.pdf_reader \
  output/{company}/raw_data/pdfs/annual_2024.pdf \
  --search "{关键词正则}"
```

#### Step D.4: Google site 精确搜索

```
WebSearch site:cninfo.com.cn {company} {缺口关键词}
WebSearch site:sse.com.cn / site:szse.cn {company} {缺口关键词}
WebSearch site:sec.gov {ticker} {缺口关键词}
WebSearch "{company}" "{缺口关键词}" filetype:pdf
```

#### Step D.5: Tushare 结构化 API 查询（最后的兜底）

```python
from scripts.tushare_collector import TushareCollector
c = TushareCollector()

# 缺口 → 接口映射：
# "分业务毛利" → c.fina_mainbz(ts_code, start_year=...)
# "股权激励明细" → c.stk_rewards(ts_code=...)
# "高管变动" → c.stk_managers(ts_code=...)
# "股东户数/结构" → c.stk_holdernumber(...) / c.top10_holders(...)
# "业绩预告/快报" → c.forecast_vip(...) / c.express_vip(...)
# "回购" → c.repurchase(...)
```

**为什么放最后**: Tushare API 聚焦结构化数据，对"事件性"信息（破产/诉讼/高管异动）覆盖较差。先网络搜索抓新鲜事件，再 API 补结构化数据。

### ★成功阈值（明确判断标准，避免草率结束）

每步结果按以下标准分档：

| 判定 | 标准 |
|------|------|
| ✅ **该步成功** | 找到**直接回答缺口的数据**（不是"提到了"而是"回答了"） |
| ⚠️ **该步部分** | 找到**相关上下文/代理指标**，但不是直接回答（如"半年报披露资不抵债"回答了"是否健康"但没回答"是否破产"） |
| ❌ **该步失败** | 接口返回空 / PDF 无匹配 / 页面无相关内容 |
| ⏭️ **该步跳过** | 明确不适用（如 Tushare 不适合查"主观性信息"） |

**5 步整体判断**（写入最终状态）：
| 整体状态 | 条件 |
|---------|------|
| ✅ 已解决 | 至少 1 步 ✅ 且数据已交叉验证 |
| ⚠️ 部分解决 | 至少 1 步 ⚠️，其余 ❌ 或 ⏭️；**必须**说明"还需要什么数据才能完全解决" |
| ❌ 未找到 | 全部 ❌ / ⏭️；**必须**标注"信息可得性判断（低/原则上不可得）"并说明原因 |

**⚠️ 禁止**:
- 单次 ⚠️ 就草率标最终状态为"部分解决"——要看 5 步整体
- 失败时不写"还需要什么数据" — 否则无法指导下次补查

### 结果登记（每条缺口一张表）

```markdown
#### 缺口 #N: {缺口项}

| 步骤 | 执行命令/查询 | 结果 | 关键发现 |
|-----|-------------|:----:|---------|
| D.1 巨潮公告索引 | WebFetch 公告列表 搜 "超隆光电" | ⚠️ | 找到 3 份 2025 年担保/业绩补偿公告，但无破产 |
| D.2 官网 IR | WebFetch sunfuntoys.com/ir | ❌ | 页面无更新 |
| D.3 PDF 正则 | pdf_reader h1_2025 --search "超隆光电" | ✅ | Page 18: 净资产 -3,289 万，资不抵债 |
| D.4 Google site | site:cninfo.com.cn 002862 超隆光电 | ⚠️ | 同 D.1 结果 |
| D.5 Tushare | stk_managers / 其他—不适用 | ⏭️ | 主观信息不在结构化库 |
| **整体** | — | **⚠️ 部分** | 已知资不抵债但无破产公告。若要 ✅，需等 2025 年报披露处置方案 |
```

### ★反写到报告的范围（强化，v3.1 新增）

补查结果**必须同步更新**以下所有位置（不仅是 §十三）：

| 补查结果 | 必须更新的章节 |
|---------|---------------|
| 数据直接涉及 Q3 亏损归因 | §5.3 盈利质量 + §十二 洞察 #相关条目的"数学推导"字段 |
| 数据涉及分业务毛利/收入 | §4 财务趋势表（加 5.1.X 分业务） + §7 可比对标 |
| 数据涉及子公司/参股公司 | §5 基本面分析 + §十二 相关洞察 |
| 数据涉及高管/股权激励 | §5 维度 3 团队 + §10 条款分析 + §十二 洞察 #相关条目 |
| 数据涉及估值（分红/回购/股东户数） | §2 评分总览 + §9 估值分析 |
| 补查升级了 Phase 5 的 Level C 候选 | §十二 附录 **→ 移至主清单**（若升级为 Level A/B） + §十二 Top 3 重新排序 |

**强制反写校验**：生成最终报告前，对每个补查成功条目执行 grep：
```bash
grep -l "{缺口项关键词}" output/{company}/{company}-analysis-*.md
```
若只在 §十三 出现一次，而其他应引用的章节里没引用 → 视为"孤岛化错误"，必须补写。

### Part D 自检（保存 phase5-review-log.md 前必须通过）

- [ ] 所有状态 ⚠️ / ❌ 的缺口都执行了 5 步补查？
- [ ] 每一步的尝试结果（✅/⚠️/❌/⏭️）都详细记录在登记表？
- [ ] 补查成功的数据已反写到 **所有相关章节**（不只 §十三）？
- [ ] 补查失败的条目标注 "信息可得性：低 / 原则上不可得" 且说明原因？
- [ ] **"部分解决"条目**都写明"还需要什么数据才能升级为已解决"？
- [ ] §十三 缺口条目数 ≥ 3（若 Phase 1/Phase 3 少于 3，Part D 已触发反向扫描）？
- [ ] Phase 5 Level C 附录中被补查升级的洞察，已从附录移至主清单？

---

## 输出

1. `output/{company}/{company}-analysis-{date}.html` — HTML 报告
2. `output/{company}/phase5-review-log.md` — 审核日志
3. GitHub Pages 更新

### 审核日志格式

```markdown
# Phase 5 审核日志: {company}
**审核日期:** {YYYY-MM-DD}

| # | 审核项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 逻辑一致性 | PASS/FAIL | {具体说明} |
| 2 | 计算准确性 | PASS/FAIL | {具体说明} |
| ... | ... | ... | ... |

**修正记录:**
- {修正1: 原文 → 修正后，原因}
- ...

**HTML生成:** ✅ 完成
**GitHub发布:** ✅ 完成 / ❌ 失败（原因）
```

---

## 质检清单

- [ ] **18 项**审核清单全部执行且有记录？（v3 新增第 16/17/18 项）
- [ ] HTML 包含全部章节（含差异化洞察 §12 + 角色结论 + 洞察回应子块）？
- [ ] HTML 中 `.variant-perception` section 存在，每条洞察一张卡片，**13 字段**（含数学推导 + 证据等级）完整显示？
- [ ] HTML Level C 附录 section 存在？
- [ ] HTML 评分总览保持单列（未因 Phase 5 引入双列，无"调整后"分数）？
- [ ] HTML §十三 定性判断**无打分数字**，用逻辑三段式？
- [ ] Persona 卡片内"对差异化洞察的回应"子区块存在且显示 2-3 条回应？
- [ ] HTML 与 MD 内容一致？
- [ ] **Part D 缺口补查是否已执行？每个 ⚠️/❌ 缺口是否有 5 步尝试记录？**
- [ ] GitHub Pages 已更新（或失败原因已记录）？
