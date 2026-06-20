# Phase 6: 审核与发布（v6.0 · 8 章节 + reviewer 3 并行）

> **⚠️ v6.0 起**: 报告从 13 章重构为 **8 章**（§一执行摘要 / §二公司基本面 / §三行业与竞争对标 / §四评分与维度证据 / §五估值与回报 / §六风险与红旗审计 / §七舆情与市场情绪 / §八数据来源与信息缺口）。已删除 Phase 4 多角色与 Phase 5 差异化洞察 —— 本文件不再含任何 persona / variant-perception / 9 字段卡片 相关审核。
>
> **anti_lazy_lint 4 项机械规则通过后**, **Part A.5** 调用 3 个并行 sub-agent: `agents/reviewer-narrative.md`（叙事一致）+ `agents/reviewer-valuation.md`（估值假设）+ `agents/reviewer-redflag.md`（红旗闭环）。主 agent 用 `Agent(run_in_background=True)` 同时启动 3 个,合并 FIX 列表后做 fresh-restart 修正循环（最多 3 轮 + diff 对抗检测）。调度细节见 `references/phase-orchestration.md` Phase 6 Part A.5。

> **🧭 你在这里**：[SKILL.md 协调器](../SKILL.md) → Phase 3 → **Phase 6 审核与发布**（终点）
>
> **接收自**: 所有上游产出（`phase1-data.md` / `phase2-documents.md` / 主报告 `{company}-analysis-*.md`）
> **输出**: `*.html` + `phase6-review-log.md` + GitHub Pages（leafpaper/Inves-Report）
> **审核规模**: 20 项 LLM 审核 + Step 0 机械化 anti_lazy_lint（4 项 hard-fail）+ Part D 5 步穷举补查
> **HTML 规则**: 必须从 `assets/html/base.html` + `assets/html/styles.css` + `assets/html/components.html` 加载,**禁止凭记忆重写 CSS 或自创变量名**
> **质量门控**: 全部 20 项通过；每个缺口有 ✅/⚠️/❌ 状态；HTML section 数 = 8；CSS 变量数 ≥ 16

---

## 角色定义

你有两个身份：

**身份A — 报告质量审计师**：逐项审核分析报告，检查逻辑错误、数据问题、夸大描述、遗漏考虑。你**不能改变分析结论**，只能标记问题并修正事实/计算/格式错误。

**身份B — 发布经理**：将审核通过的报告转化为HTML可视化版本，并上传到GitHub Pages。

---

## 前置条件

1. `output/{company}/{company}-analysis-{date}.md` 存在（Phase 3 assemble 产出，8 章节齐全）
2. `output/{company}/phase1-data.md` + `phase2-documents.md` 存在（供来源审计与缺口补查回溯）
3. HTML 真相源可用：`assets/html/base.html` + `styles.css` + `components.html`

---

## 基本事项

1. 审核只标记和修正问题，**不改变分析结论或评分**
2. 每个审核项记录 PASS/FAIL + 具体说明
3. 如发现严重问题（如计算错误），在修正后标注 `[Phase 6 修正]`
4. HTML 版本必须与 MD 内容完全一致——不省略任何章节

---

## Part A: 报告审核

### Step 0（强制门控）: 机械化深度检查 — 任一规则 fail 直接 BLOCK

**为什么必须先跑这一步**: LLM 自审看不见自己的"懒"(写者=审者)。机械化的 grep + 字数 + diff 是确定性的, 能挡住下列懒惰模式:
- "详见 capital_flow.md / phase2-documents.md" 这种把内容推到附件的外链
- §四 / §五 等深度章节字符数过低(摘要式填充)
- artifact 关键数字短语没有 inline 到主报告
- §一~§八 章节标题被 LLM 重命名(如 §二 公司基本面 → §二 业务概况)

**执行**:
```
{PYBIN} -m scripts.anti_lazy_lint --md output/{company}/{company}-analysis-{date}.md
# 退出码 0 = 进入下面的 20 项 LLM 审核
# 退出码 1 = BLOCK, 必须返回 Phase 3 修对应 part 后重 assemble 再来; 不允许 LLM 自审"绕过"机械检查
```

**4 条规则 (全部 hard fail)**:

| # | 规则 | 阈值 | 例外白名单 |
|:---:|------|------|---------|
| 1 | 外链引用扫描 (详见 xxx.md / 见 phaseX.md / [xxx](xxx.md)) | 命中 = 0 | §六 允许引用 `audit_report.md`;§八 允许 `audit_report.md` / `metrics.json` / `phase1-data.md` / `phase2-documents.md` |
| 2 | 章节最小字符数 (中文+字母+数字) | 见 `scripts/anti_lazy_lint.py:MIN_SECTION_CHARS`（§一 600 / §二 800 / §三 700 / §四 1500 / §五 800 / §六 500 / §七 600 / §八 200） | – |
| 3 | Artifact 关键短语覆盖率 (capital_flow / peer / tech / audit / data_snapshot) | overall ≥ 40% AND 单 artifact ≥ 20%（data_snapshot.md 单独 5% 且不计 overall） | 美股/港股无 artifact 时跳过 |
| 4 | 章节标题与 `assets/templates/report-skeleton.md` 字节一致 (去括号注释后) | 8 章节, 0 differences | – |

**修复指引**:
- Rule 1 命中 → 删除外链, **inline 完整内容**(表格 / 数字 / 段落)到对应章节
- Rule 2 不足 → 补充该章节内容深度(展开证据链 / 加表格 / 加数字事实)
- Rule 3 不足 → Read 对应 artifact, 把关键数字短语真实搬入主报告
- Rule 4 不一致 → 把 `## §X` 标题改回 skeleton 的字面字符串(允许加括号注释如 "## §二 公司基本面(v6.0)")

**Step 0 通过后才能进入下面 20 项 LLM 审核 + Part B HTML 生成**。

---

### 审核清单（逐项执行，记录结果）

| # | 审核项 | 通过标准 |
|---|--------|---------|
| 1 | **逻辑一致性** | 评分是否与引用的证据方向一致？（高分=正面证据，低分=负面证据） |
| 2 | **计算准确性** | §四 加权分计算是否正确？综合分公式是否正确？ |
| 3 | **夸大检查** | 是否存在无依据的夸张描述？（如"行业最佳"但无数据支撑） |
| 4 | **遗漏检查** | 是否有明显的风险/问题未被讨论？ |
| 5 | **数据时效性** | 旧数据是否标注 `[历史数据]`？是否存在用旧数据支撑当前结论？ |
| 6 | **来源完整性** | 关键论断是否都有来源URL？§八 信息来源列表是否完整？ |
| 7 | **章节完整性** | 8 个 `## §` 章节是否全部存在？§四 10 维度逐维度证据是否全覆盖？ |
| 8 | **数据自洽** | 不同章节引用的同一数据是否一致？（如 §二 财务趋势 vs §四 维度证据 vs §五 估值口径） |
| 9 | **基本面覆盖** | §二 公司基本面与 §三 行业对标是否作为独立章节充分分析？ |
| 10 | **舆情平衡** | §七 看多/看衰观点是否均衡（各 ≥ 3 条）？是否都有来源？ |
| 11 | **假设透明度** | §五 投资回报测算中的情景概率与假设是否全部明确标注？ |
| 12 | **定性判断为逻辑三段式** | §四 末"定性综合判断"是否用"核心问题 → 判断 → 证据链 → 逻辑蕴含"思路？**只综合护城河 / 管理层 / 催化剂三个维度**（估值见 §五，会计红旗见 §六）？是否**无打分数字**（无"修正值 ±X" / "调整后 X" / "+Y%" 等打分换壳；无"强烈看多/有条件看好/谨慎/回避"5 档连续排序）？综合方向是否严格为"看多方向 / 看空方向 / 中性-分歧"3 档？ |
| 13 | **评分表 4 列纯净** | §四 10 维度评分表是否**只 4 列**（维度/权重/分数/加权分），**无"关键理由"列**、**无"定性修正系数"**这种打分式写法？合计行 = `{{composite_score}}`？ |
| 14 | **缺口补查闭环** | §八"信息缺口与尽调优先级"表格每一项是否有**明确状态**（✅已解决 / ⚠️部分 / ❌未找到）+ 可得性？**若有 ❌ 未找到的条目，Part D 是否已执行 5 步补查？** |
| 15 | **数据来源可审计** | 关键财务数据（§二 财务趋势表、§四 维度证据、§五 估值）是否都有 `[Tushare:*]` 或 `[PDF:*]` 来源标签？是否无任何 `[证券之星算法]` / `[某财经网摘要]` 作为关键数据来源？ |
| 16 | **估值-回报一致性** | §五 5.1 估值锚（DCF 概率加权）与 5.4 投资回报测算是否**共用同一组情景**（乐观/基准/悲观 ± 最差）和同一组概率？是否禁止"三角验证均值"作为综合锚？交叉验证（5.2）可比倍数/PB 差距 > 20% 是否已解释分歧原因？**若 5.1 锚 ≠ 5.4 基准或概率分布不同则不通过**。 |
| 17 | **核心资产剥离风险 SOTP** | 若满足以下**任一**触发条件：①核心子公司占合并净利 > 30% 且存在剥离/控制权丧失可能；②`forecast_vip` 预亏 > 50% 净资产；③PDF 自述"若 XX 发生面临阶段性下调"；④`audit_report` 🔴 涉及核心资产减值 —— §二 是否有"若核心资产被剥离的剩余资产清单"子节（含货币/金融资产/非核心子公司/已剥离尾款/非核心固定资产/壳价值/有息负债/清算成本）？§五 5.1 是否有"最差情景"（3-10% 权重）作为下行地板？**若触发但缺其中任一则不通过**。 |
| 18 | **红旗闭环** | §六 6.1 致命看空快筛（6 项阈值）每项有实际值 + 触发判定？§六 6.2 审计红旗汇总（11 框架）来自 `audit_report.md`？**每条 🔴/🟠 红旗是否在 §六 6.3 致命看空论证 或 §一 Top 3 风险中被引用闭环**？§四 维度 7（财务健康度）/ 维度 8（估值合理性）是否与 §六 红旗、§五 估值口径一致？ |
| 19 | **HTML 资产加载** | Part B 生成 HTML 是否**从 `assets/html/base.html` 加载骨架**？是否**内联了 `assets/html/styles.css` 完整内容**（`grep -c '^\s*--c-' *.html` ≥ 16 个 CSS 变量）？是否使用 `assets/html/components.html` 的标准组件 class（≥ 8/9）？是否 **8 个** `<div class="section"` 对应 §一～§八 且 id 属性正确（exec-summary / fundamentals / industry / scoring / valuation / risk / sentiment / sources）？**禁止 Claude 自写 CSS 变量或组件 class**。 |
| 20 | **Executive Summary 7 字段 schema** | §一 执行摘要是否严格按 `assets/templates/exec-summary-schema.md` 的 7 固定字段展开（一句话结论 / 估值锚 / 综合评分 / 三大风险 / 三大机会 / 核心非共识判断 / 投资方向综合判定）？字段名与顺序字节一致？**是否出现禁用字段**（综合评级 / 量化分+定性修正+调整后分 / 建议仓位 / 尽调优先级 / 关键假设敏感度）？**8 个 `## §` 标题是否与 `assets/templates/report-skeleton.md` 字节一致**？ |

> Phase 1 的 4 个结构化 artifact（`peer_analysis.md` → §三；`capital_flow.md` → §二 主力控盘 + §七 资金流向；`technical_analysis.md` → §五 5.3 技术面；`audit_report.md` → §一 Top 3 + §六）的"真实消费"由 Step 0 Rule 3（artifact 覆盖率）机械保证,LLM 审核不再单列；若 A 股 artifact 存在但对应章节无相应表格,Step 0 会 BLOCK。

### 修正规则

- **轻微问题**（格式/拼写/计算偏差）：直接修正，标注 `[Phase 6 修正]`
- **严重问题**（结论与证据矛盾/重大遗漏）：标记但**不改变结论**，在审核日志中详细说明
- **致命问题**（数据造假/严重计算错误）：修正错误，标注 `[Phase 6 重大修正]`，在报告开头加警示

---

## Part B: HTML 生成（脚本化, 不丢章节）

### ★ 推荐: 直接调用 `scripts/build_html.py`（一键转换）

```
{PYBIN} -m scripts.build_html --company {company} \
    --md output/{company}/{company}-analysis-{date}.md \
    --out output/{company}/{company}-analysis-{date}.html
```

此脚本会:
1. 读 `assets/html/base.html` + `styles.css` + `components.html`
2. 读 `output/{company}/{company}-analysis-{date}.md`
3. 解析结构化注释块(CARD_METADATA / RATING_TRIO_DATA / KEY_METRICS_SIDEBAR)
4. 按 `^##` 切 MD section,**前 8 填固定 placeholder（槽位从 base.html 动态发现）,超出的追加到 extra_sections**（避免附录丢失 bug）
5. 填 rating-trio / metric-strip 面板
6. 替换 hero meta 占位符
7. 自检输出 section 数 + 组件命中率

验证门槛(脚本自动检查): HTML section 数 ≥ MD `##` 章节数;若少于则报警并返回非零退出码。脚本写 HTML 前内置再跑一次 anti_lazy_lint,fail 阻断。

### ★ 备选: 手动流程（不推荐,仅在脚本不可用时）

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

Step 3.5: 填充前置评级卡 + 顶部关键指标条
        从主报告 §一 执行摘要 + RATING_TRIO_DATA 注释块抽取:
          composite_score / verdict / verdict_tone / anchor_price /
          anchor_delta_signed / horizon / expected_return / return_tone / annualized_return
        复制 components.html 的前置评级三件套片段,填入 <!-- PLACEHOLDER: rating_trio --> 占位
        (3 张 rating-card: 评分 / 估值锚 / 期望收益)

        从 KEY_METRICS_SIDEBAR 注释块 + §二 抽 5-8 个关键指标:
          PE TTM / PB / 市值 / ROE / 毛利率 / 资产负债率 / 股东户数 / 控盘度
        复制 components.html 关键指标横排片段,填入 <!-- PLACEHOLDER: key_metrics --> 占位
        (tone 判定: ROE<0 / 资产负债率>60% / 家族持股>=40% → negative/risk/critical)

Step 4: 逐章节填充 8 个 <!-- PLACEHOLDER: section_N_xxx --> 占位:
        - 用 markdown 转 HTML (表格 → <table>, 列表 → <ul>, 加粗 → <strong>)
        - 当章节需要可视化组件时从 components.html 复制对应片段并填充数据
        - §一 三大风险 → 使用彩条风险卡 (risk-card), tone 按致命/高/中/低分
        - §三 Peer 对标 → 使用 comparison-card (你 vs peer 中位)
        - §四 财务/盈利维度 → 可选 heatmap-grid (历史趋势可视化)
        - 8 个 section id 必须为: exec-summary / fundamentals / industry / scoring / valuation / risk / sentiment / sources

Step 4.5: 深度内链(可选增强可读性)
        例: §一 提到 "游戏业务崩塌 -94%" 可加
          <a href="#scoring" class="deep-link">维度 3 证据</a>
        其他示例: §六 6.1 快筛触发 → 链到 §四 对应维度;§六 红旗 → 链到 §五 估值影响

Step 5: 自检:
        - grep -c '<div class="section"' 应 = 8
        - grep -c '^\s*--c-' 应 ≥ 16 (CSS 变量未被删)
        - 9 个基础组件 class 命中率 ≥ 8/9
        - rating-trio / metric-strip 必须出现在 HTML 中
        - 所有 {{placeholder}} 必须已被替换 (grep 后应无 `{{`)
        - .rating-trio .rating-card 数量 = 3
```

**绝对禁止**:
- ❌ **禁止凭记忆重写 CSS** — 必须整体内联 `styles.css` 文件
- ❌ **禁止自创 CSS 变量名**（如 `--primary` 取代 `--c-primary`;`--accent` 取代 `--c-yellow` 等）
- ❌ **禁止自命名组件 class** — 必须用 components.html 中定义的标准 class
- ❌ **禁止"概括/合并/简化"** MD 章节 — 8 个 section 必须一一对应

**HTML 8 章节要求**（严格与 `assets/templates/report-skeleton.md` + `assets/html/base.html` 对齐）:

| # | 章节 | MD 骨架标题 | HTML section id |
|---|------|--------|---------|
| 1 | 执行摘要 | `## §一 执行摘要` | `exec-summary` |
| 2 | 公司基本面 | `## §二 公司基本面` | `fundamentals` |
| 3 | 行业与竞争对标 | `## §三 行业与竞争对标` | `industry` |
| 4 | 评分与维度证据 | `## §四 评分与维度证据` | `scoring` |
| 5 | 估值与回报 | `## §五 估值与回报` | `valuation` |
| 6 | 风险与红旗审计 | `## §六 风险与红旗审计` | `risk` |
| 7 | 舆情与市场情绪 | `## §七 舆情与市场情绪` | `sentiment` |
| 8 | 数据来源与信息缺口 | `## §八 数据来源与信息缺口` | `sources` |

保存为 `output/{company}/{company}-analysis-{date}.html`

---

## Part C: GitHub Pages 发布（主页动态联动）

> **重大变更**: 不再手工编辑 `index.html` 加卡片。Part C 调用 `scripts/update_index.py` 自动抽取 card-metadata + upsert `data/reports.json`,主页通过 JS `fetch` 动态渲染。index.html 只有骨架,**永不需手工改**。

**目标仓库**: `leafpaper/Inves-Report`

> **本发布步骤路径可配置、且为可选**: 下文 `$INVES_REPORT_DIR` 为环境变量(Mac/Linux 默认 `/tmp/Inves-Report`, Windows 设为如 `C:\Inves-Report`);git 命令保留不变。

**执行步骤**(下方为 Mac/Linux 写法;Windows 把 `mkdir -p`→`New-Item -ItemType Directory -Force`、`cp`→`Copy-Item`、`$INVES_REPORT_DIR`→`$env:INVES_REPORT_DIR`;`cd` / `git` 两边通用):

```
1. 确保仓库已克隆:
   cd $INVES_REPORT_DIR && git pull origin main
   (如不存在则 git clone)

2. 创建/更新公司报告目录:
   mkdir -p $INVES_REPORT_DIR/reports/{CompanySlug}_{CompanyNameCN}

3. 复制 HTML 报告:
   cp output/{company}/{company}-analysis-{date}.html $INVES_REPORT_DIR/reports/{CompanySlug}_{CompanyNameCN}/分析报告_dashboard.html

4. ★ 自动更新主页卡片数据:
   {PYBIN} -m scripts.update_index --company {company} \
       --repo $INVES_REPORT_DIR \
       --force

   这会:
   - 解析主报告 MD 的 <!-- CARD_METADATA / RATING_TRIO_DATA / KEY_METRICS_SIDEBAR --> 结构化注释块
   - 生成 output/{company}/card-metadata.json
   - 复制到 $INVES_REPORT_DIR/reports/{slug}/card-metadata.json
   - upsert 到 $INVES_REPORT_DIR/data/reports.json
   - 主页 JS 会从 reports.json 自动渲染新卡片 + 更新统计数字

   若解析结果不理想(老报告未带结构化注释块), 会走 regex fallback 并输出警告。
   **新生成的报告必须在 hero 后带 CARD_METADATA / RATING_TRIO_DATA / KEY_METRICS_SIDEBAR
   三个注释块**(见 assets/templates/report-skeleton.md 顶部)。

5. 提交推送(改动 3 项: HTML + card-metadata + reports.json):
   cd $INVES_REPORT_DIR
   git add reports/{CompanySlug}_{CompanyNameCN}/ data/reports.json
   git commit -m "feat: 新增/更新 {company} 投资分析报告"
   git push origin main
```

**失败处理**: 如 git push 失败, 保存 HTML 到本地并通知用户手动上传。

---

## Part D: 缺口补查闭环

### 触发条件（两种）

**触发 A**: Part A 审核清单第 14 项发现 §八"信息缺口与尽调优先级"表格中有**状态为 ⚠️ 或 ❌ 的条目**。

**触发 B（反向扫描）**: Phase 1 §11 条目数 < 3 **或** Phase 3 §八 条目数 < 3 → 自动降级报告置信度 **-0.5**，并触发 Part D 反向扫描：强制从以下清单里挑至少 3 项作为"潜在缺口"执行 5 步补查：
- 最新报告期资产减值损失明细
- 核心子公司/参股公司近 12 月动态
- 股权激励对象明细（有激励计划时）
- 分业务/分产品毛利率
- 关联方交易金额
- 对外担保变动

### 5 步穷举补查流程（★顺序由粗到精）

对每一条 ⚠️ / ❌ 缺口，依次执行（**找到即停止**，但每步必须登记结果）：

#### Step D.1: WebFetch 巨潮资讯索引（先从公告入手）

```
WebFetch http://www.cninfo.com.cn/new/disclosure/stock?stockCode={code}&orgId=...
→ 获取该股所有公告标题列表
→ 按关键词过滤，WebFetch 相关公告 PDF
```

**为什么放第 1**: 缺口多半来自**未读的公告**（如"子公司出售/破产"这类临时公告）。巨潮覆盖面最广且时效最高。

#### Step D.2: WebFetch 公司官网 IR

```
1. 定位公司官网（从 stock_basic.parquet 的 website 字段或 Google 搜 "{company} 官网"）
2. WebFetch {domain}/investors 或 /ir
3. 翻找"公告""投资者关系""新闻"页
```

#### Step D.3: PDF 原文全文搜索（用 pypdf 正则）

```
{PYBIN} -m scripts.pdf_reader \
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
| ⚠️ **该步部分** | 找到**相关上下文/代理指标**，但不是直接回答 |
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

### ★反写到报告的范围（强化）

补查结果**必须同步更新**以下所有位置（不仅是 §八）：

| 补查结果 | 必须更新的章节 |
|---------|---------------|
| 数据涉及最新季度亏损归因 | §二 财务趋势表 + §四 维度 3（盈利能力）证据 |
| 数据涉及分业务毛利/收入 | §二 财务趋势表（加分业务行）+ §三 可比对标 |
| 数据涉及子公司/参股公司 | §二 基本面 + §五 5.1 SOTP（若涉核心资产） |
| 数据涉及高管/股权激励 | §四 维度 5（团队与管理层）+ §六 治理红旗 |
| 数据涉及估值（分红/回购/股东户数） | §四 维度 8（估值合理性）+ §五 估值 |
| 数据涉及审计红旗/减值 | §六 6.1 快筛 / 6.2 汇总 + §一 Top 3 风险 |

**强制反写校验**：生成最终报告前，对每个补查成功条目, 用 Read 打开主报告搜索 `{缺口项关键词}`, 看它出现在哪些章节(无需 shell)。
若只在 §八 出现一次，而其他应引用的章节里没引用 → 视为"孤岛化错误"，必须补写。

### Part D 自检（保存 phase6-review-log.md 前必须通过）

- [ ] 所有状态 ⚠️ / ❌ 的缺口都执行了 5 步补查？
- [ ] 每一步的尝试结果（✅/⚠️/❌/⏭️）都详细记录在登记表？
- [ ] 补查成功的数据已反写到 **所有相关章节**（不只 §八）？
- [ ] 补查失败的条目标注 "信息可得性：低 / 原则上不可得" 且说明原因？
- [ ] **"部分解决"条目**都写明"还需要什么数据才能升级为已解决"？
- [ ] §八 缺口条目数 ≥ 3（若 Phase 1/Phase 3 少于 3，Part D 已触发反向扫描）？

---

## 修正循环与 Part 映射（与 phase-orchestration.md 一致）

reviewer 提出的 FIX 要写回 Phase 3 对应 part 文件,然后重 assemble + 重跑 lint:

| Part 文件 | 负责章节 |
|-----------|---------|
| `phase3-part1.md` | §一 执行摘要 |
| `phase3-part2.md` | §二 公司基本面 / §三 行业与竞争对标 |
| `phase3-part3.md` | §四 评分与维度证据 / §五 估值与回报 |
| `phase3-part4.md` | §六 风险与红旗审计 / §七 舆情与市场情绪 / §八 数据来源与信息缺口 |

> 真理来源: `scripts/assemble_report.py:PART_EXPECTED_SECTIONS`。修正循环为 **fresh-restart**（不用 `Agent(resume=...)`,该参数不存在）,最多 3 轮,diff 重复则转人工。详见 `references/phase-orchestration.md` Phase 6 Part A.5。

---

## 输出

1. `output/{company}/{company}-analysis-{date}.html` — HTML 报告
2. `output/{company}/phase6-review-log.md` — 审核日志
3. GitHub Pages 更新

### 审核日志格式

```markdown
# Phase 6 审核日志: {company}
**审核日期:** {YYYY-MM-DD}

| # | 审核项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 逻辑一致性 | PASS/FAIL | {具体说明} |
| 2 | 计算准确性 | PASS/FAIL | {具体说明} |
| ... | ... | ... | ... |
| 20 | Executive Summary 7 字段 schema | PASS/FAIL | {具体说明} |

**anti_lazy_lint:** ✅ 4 项全过 / ❌ 失败项
**reviewer 3 维度:** narrative ✅ · valuation ✅ · redflag ✅
**修正记录:**
- {修正1: 原文 → 修正后，原因}

**HTML生成:** ✅ 完成（section 数 = 8）
**GitHub发布:** ✅ 完成 / ❌ 失败（原因）
```

---

## 质检清单

- [ ] **20 项** LLM 审核清单全部执行且有记录？
- [ ] Step 0 anti_lazy_lint 4 项 hard-fail 全部 PASS？
- [ ] reviewer 3 维度（narrative / valuation / redflag）全部 PASS？
- [ ] HTML 包含全部 8 个 section（id: exec-summary / fundamentals / industry / scoring / valuation / risk / sentiment / sources）？
- [ ] HTML §四 评分表保持单列（无"调整后"分数）、定性综合判断**无打分数字**？
- [ ] HTML 中 `grep -c '<div class="section"'` = 8、CSS 变量 ≥ 16、组件命中 ≥ 8/9？
- [ ] HTML 与 MD 内容一致（无章节丢失）？
- [ ] **Part D 缺口补查是否已执行？每个 ⚠️/❌ 缺口是否有 5 步尝试记录？**
- [ ] 每条 🔴/🟠 红旗是否在 §一 Top 3 或 §六 6.3 中闭环引用？
- [ ] GitHub Pages 已更新（或失败原因已记录）？
