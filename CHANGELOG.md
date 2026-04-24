# Changelog

所有重要变更按版本记录。格式受 [Keep a Changelog](https://keepachangelog.com/) 启发。

---

## [v4.6.2] — 2026-04-25 — 补 v4.6.1 的 preamble 丢失 + 内容命中率 ≥99% 自检

> **用户追问**: "你确定 MD→HTML 不会有任何缺失了吗?" — 经严格验证发现 v4.6.1 还有一层丢失。

### Fixed

**Preamble 区丢失** — v4.6.1 只处理 15 个固定 section + extra_sections(第 16+ `##`),但**第一个 `##` 之前的内容**(MD 顶部 title 后、首章 §一 前)全部被丢弃:
- 报告元数据(`报告期`/`最新收盘日期尾巴`/`总市值的 PE_TTM 说明`/`分析师的 skill 版本附注`)的详细部分 — hero 模板只填基础占位,后半说明丢失
- **关键:版本切换 blockquote**(如实丰 `> 本报告为 v3 全新版...历史版本 [v1] [v2]`)— 读者无法知道当前看的是哪一版

### Added

1. **`base.html` 新增 `<div class="preamble">` 区**:hero 之后、rating-trio 之前,填充主报告第一个 `##` 之前的内容
2. **`styles.css` 新增 `.preamble` 样式**:浅灰底 + 橙色左边框 + 小字号,区别于主 section
3. **`build_html.py` preamble 填充逻辑**:剥注释块 + 剥 title 行后转 HTML 注入
4. **内容命中率自检(核心!)**:
   - 算法:归一化 MD 每行(去标点/list marker/空白/URL)→ 取中间 20 字符指纹 → 在归一化 HTML 中查找
   - 阈值:≥ 98% 通过;< 90% 非零退出码
   - 7 家公司实测命中率:
     - 实丰文化 v4.1: **455/455 = 100.0%** ✅
     - 震安科技 v1: **335/335 = 100.0%** ✅
     - 西藏矿业 v1: **389/389 = 100.0%** ✅
     - 同泰怡 v1: **302/302 = 100.0%** ✅
     - Adobe v3: **165/166 = 99.4%** ✅
     - Circle v1: **284/285 = 99.6%** ✅
     - Starway v1: **250/251 = 99.6%** ✅
     - 平均 **99.9%**,剩余 ≤1% 是个别特殊格式的自检误报,非真实丢失

### Changed

- `_normalize()`: 简化为只保留 `\w` + CJK,忽略所有标点(全半角)
- sig 取指纹从"前 20 字符"改为"**中间 20 字符**",避免 list marker / bold 标记干扰
- URL 预处理:`[text](url)` → 只保留 `text`(HTML `<a>` 肉眼不显示 URL)

---

## [v4.6.1] — 2026-04-25 — HTML 生成脚本化 + 补 v4.6 3 处缺陷

> **主题**: 修 v4.6 上线 1 小时后用户发现的 3 个问题。

### Fixed (v4.6 → v4.6.1)

1. **MD → HTML 转换丢章节**: v4.6 主报告 17 个 `##` 章节, base.html 只有 15 个固定 placeholder (§一 ~ §十五), 附录的第 16/17 (v4 修订日志 / v4.1 补丁) 被完全丢弃
   - 修: base.html 在 §十五 后加 `<!-- PLACEHOLDER: extra_sections -->`, build_html.py 把第 16+ 章节自动追加到这里
   - 修: 新增 `scripts/build_html.py` (~300 行) 替代 LLM inline Python 做 MD → HTML 转换, 保证 section 零丢失
   - 副产物: 修了一个隐蔽的 `re.sub` bug — markdown 输出 HTML 中的 `\g` 会被当反向引用, 改用 lambda repl 避开

2. **粘性侧边栏改为顶部横排**: 用户反馈"关键指标放旁边没必要, 放最上面就行"
   - `<aside class="metric-sidebar">` 粘性右栏 → `<div class="metric-strip">` 顶部横排 (8 个 metric-chip 平铺)
   - `.container.has-sidebar` 两栏 → 普通单栏
   - `.metric-sidebar` 保留但降级为块级显示, 向后兼容 v4.6 老报告

3. **主页去"龟龟策略"文案**: 用户反馈"龟龟策略的表述可以去掉"
   - `<title>`: "Inves Reports · 龟龟投资策略" → "叶纸的投资分析报告 · Inves Reports"
   - `.hero-badge`: "✦ 龟龟投资策略 v2 ✦" → "✦ AI 投资分析 v4.6 ✦"
   - `<h1>`: "🐢 叶纸的投资分析报告" → "叶纸的投资分析报告"(去🐢)
   - hero `<p>`: "基于龟龟策略框架..." → "基于 11 大师框架的定量审计 + DCF 概率加权估值..."
   - footer: "🐢 基于龟龟策略框架..." → "AI 自动生成 · v4.6 动态联动 · 11 大师框架审计"
   - `.nav-logo` 仍保留小🐢 + "叶纸的投资报告"(作为个人身份,非策略表述)

### Added

- **`scripts/build_html.py`** (~300 行)
  - `_parse_structured_block()`: 解析 RATING_TRIO_DATA / KEY_METRICS_SIDEBAR / CARD_METADATA 注释块
  - `split_sections()`: 按 `^## ` 稳健切 MD, 保留所有章节
  - `build_rating_trio()`: 按 data 生成 3 张 rating-card
  - `build_metric_strip()`: 按 data 生成 5-8 个 metric-chip (取代 sidebar)
  - `build_html()`: 主流程, 自检 + 自动报警
  - CLI: `python3 -m scripts.build_html --company X --md Y --out Z`

- **assets/html/styles.css**: 新增 `.metric-strip` + `.metric-chip` 样式(横排自适应 5-8 chip), 保留 `.metric-sidebar` 降级为块式

- **assets/html/base.html**: 去 `has-sidebar` 两栏, 在 hero + rating-trio 后加 `<div class="metric-strip">` 顶部面板, 在 §十五 后加 `extra_sections` 占位

- **assets/html/components.html**: 新增 `.metric-strip` 完整 8 chip 片段

### Changed

- `phases/phase6-review-publish.md` Part B: 改为"推荐 `python3 -m scripts.build_html`"自动化, 手动流程降为备选
- `install.sh`: scripts 数 16 → 17 (加 build_html)

### Verified

- 实丰 002862 重生 HTML: 17 section 全入 (15 固定 id + extra-1 + extra-2), metric-chip 8 个, rating-card 3 个, 0 个 {{placeholder}} 残留

---

## [v4.6] — 2026-04-25 — 大厂风格 HTML + 主页动态联动

> **主题**: 两个用户反馈方向合并实现:①主页手工维护痛点(每次加新报告都要 Edit index.html);②报告 HTML 视觉单调,缺大厂标配元素。

### 根因

1. **主页联动**: `phase6-review-publish.md Part C` 第 4 步写的是"手工编辑 index.html" —— 14 张卡片硬编码 + 4 个统计数字硬编码,每次新报告 5-10 分钟手工维护,易遗漏
2. **报告单调**: 国外大厂(Goldman / Morgan Stanley / Bloomberg / Morningstar)标配的"前置评级卡 / 彩条风险 / 粘性侧边栏 / 对标卡 / 热力图 / 深度内链"全部缺失

### Added

#### 1. Inves-Report 仓库侧(`/tmp/Inves-Report-v2/` → `github.com/leafpaper/Inves-Report`)

- **`data/reports.json`**: 所有报告的元数据 JSON(ticker / 评分 / verdict / tone / 一句话结论 / 指标 / badge 等)
- **`assets/css/main.css`**: 从 index.html 内联 CSS 抽出(~300 行)+ 新增搜索/筛选/排序 UI 样式
- **`assets/js/render.js`**: fetch reports.json → 按 market 分组 → 渲染卡片 + 搜索 + 市场 tab + 排序 + 评分筛选
- **`index.html`**: 从 500 行压缩为 **~130 行骨架**,所有卡片由 JS 动态渲染
- **搜索/筛选 UI**: 全文搜索框 + 市场 tab(全部/美股/A股/港股/一级) + 排序下拉(最新/评分/收益) + 评分筛选(全部/≥4/≥6/≥7.5)

#### 2. skill 侧 HTML 大厂风格升级

**`assets/html/styles.css`** 新增 6 个组件 class(~300 行新代码):
- `.rating-trio` + `.rating-card` — Goldman 风格前置三件套(评分/估值锚/期望收益)
- `.risk-card-v2` + `risk-critical/high/medium/low` — Bloomberg 风格彩条风险卡(替代 Markdown 表格)
- `.metric-sidebar` + `.metric-row` — 粘性侧边栏(right 260px,滚动常驻,展示 5-8 关键指标)
- `.comparison-card` + `cmp-col center/bar` — Morningstar 风格对标卡(你 vs peer 中位 vs 历史)
- `.deep-link` + `:target` 脉冲 — 章节内链跳转 + 高亮动画
- `.heatmap-grid` + `.hm-cell.hm--2/--1/0/1/2` — 微型 5 档色块热力图

**`assets/html/base.html`** 改造:
- `<div class="container">` → `<div class="container has-sidebar">` 两栏布局
- hero 下新增 `<div class="rating-trio">` 前置评级卡占位
- body 右侧新增 `<aside class="metric-sidebar">` 粘性关键指标

**`assets/html/components.html`** 加 6 个新片段(供 Phase 6 按数据填充)

**`assets/templates/report-skeleton.md`** 补 3 个 HTML 注释结构化块(Phase 3 写报告时填):
- `<!-- RATING_TRIO_DATA: ... -->` 前置评级卡数据
- `<!-- KEY_METRICS_SIDEBAR: ... -->` 侧边栏 5-8 指标
- `<!-- CARD_METADATA: ... -->` 主页卡片元数据(sector/market/one_liner/top_risks_short)

#### 3. `scripts/update_index.py` 新增(~300 行)

- 解析主报告 MD 的 3 个结构化注释块(100% 精准)
- Fallback: 老报告走 regex 抽取(部分字段可能不准,会输出警告)
- 生成 `output/{company}/card-metadata.json`
- 复制到 `/tmp/Inves-Report/reports/{slug}/card-metadata.json`
- upsert 合并到 `/tmp/Inves-Report/data/reports.json`(by ticker match, --force 覆盖)
- 自动按 report_date 降序排序 + 重算统计

#### 4. 风格配色升级

- 保留 Goldman 深蓝主色 `--c-primary: #1a56db`
- 新增 Bloomberg 高对比风险等级色: `--c-risk-red/amber/yellow/green`
- 新增 Morningstar 卡片化灰阶: `--c-card-border/header/hover`

### Changed

- **`phases/phase6-review-publish.md`** Part B:新增 Step 3.5 强制填 rating-trio + metric-sidebar
- **`phases/phase6-review-publish.md`** Part C:Step 4 "手工编辑 index.html" → `python3 -m scripts.update_index` 自动调用
- **Part C Step 5** git add 从 `-A` 收紧为 `reports/{slug}/ data/reports.json`(避免误提交)

### Verified

- 实丰 002862 v4.1 报告:抽结构化块后精准得到 sector="玩具 + 游戏 + 光伏参股" / expected_return="-44.1%" / valuation_tag="估值锚 10.1 元"
- 主页本地启 `python3 -m http.server 8766` 验证:10 张卡片动态渲染 / 搜索"实丰"筛选正确 / 市场 tab 切换正确 / 统计数字从 reports.json 实时算
- HTML 重生成:rating-trio 出现 1 次(正确) / metric-sidebar 出现 13 次(CSS + HTML 结构) / has-sidebar 出现 5 次 / 178 个 CSS 变量引用

### Known limitations

- `update_index.py` 对 **v4.6 之前的老报告**(无 CARD_METADATA 注释块)走 regex fallback,sector/expected_return 等可能不准 — 需手工检查 reports.json
- 移动端 sidebar 折叠成顺序(未做复杂响应式)
- 深色模式未做
- GitHub Action 自动扫描报告目录推迟到 v4.7

---

## [v4.5] — 2026-04-25 — capital_flow 口径修正 + 家族一致行动人识别

> **主题**:修复 v4.4 `capital_flow.py` 在限售股占比高的公司严重低估实控人控盘度的 bug。用户在实丰文化分析中发现 "蔡氏家族真实持股 40% vs 脚本报告 22.61%" 的矛盾,追溯到数据源口径错误。

### 根因

v4.4 `capital_flow.py _derive_metrics` 只拉 `top10_floatholders`(前十大**流通**股东,不含限售),对实控人大量持有限售股的公司(典型上市 3 年内 / 股权激励未解锁 / 家族控股)**严重低估真实控盘度**:

**实丰文化案例**(2025 年报):
- v4.4 输出: 主力控盘度 22.61% (🟢 分散)
- 真实情况: 前 10 大全体股东 **47.46%** + 蔡氏家族合计 **40.77%** (🔴 绝对控盘)
- 差 17.4 pp,定性判断从 🟢 变 🔴(反向!)

### Fixed

- **`scripts/capital_flow.py`**:
  - 新增 `raw["top10_all"]` 数据源(`tushare.top10_holders`,含限售股)
  - `_derive_metrics` 控盘度改用 `top10_all` 优先,`top10_float` 降为补充参考
  - 新增启发式 `_family_control()`:识别同姓自然人股东合并算"实控人家族合计"
  - 输出 3 个口径:前 10 大总股东占总股本 / 前 10 大流通占总股本(旧)/ 前 10 大流通占流通股本
  - 综合档位:前 10 大 ≥50% 🔴 / ≥30% 🟡 / <30% 🟢
  - 家族档位:≥40% 🔴 绝对控盘 / ≥25% 🟡 相对控盘 / <25% 🟢 非控盘
- **`_format_markdown`**:
  - §1 综合判定表从 6 维度 → **7 维度**(新增 "实控人家族合计持股" 独立行)
  - §2 "前十大流通股东" → **"前十大全体股东(含限售)"**
  - §8 警示规则:家族控盘 ≥40% 触发 🔴 关联交易/大股东占款风险提示

### Known limitations

- `_family_control()` 是**启发式识别**(同姓自然人),**不替代年报"一致行动人"正式披露**:
  - 对**姓氏不同的一致行动人**(夫妻、姻亲)漏识别
  - 对**通过控股公司实控**的结构识别不全(如闻泰的"张学政 → 闻天下科技集团"路径,只识别到张学政 2.97%,漏了闻天下 12.37%)
  - Phase 3 §四"主力控盘"子节的 LLM 仍应**手工核对**年报的"实际控制人"章节

### Regression

- 闻泰 600745.SH 回归:控盘度 44.79% 不变(该股限售已解锁,top10_all = top10_float),家族识别到张学政 2.97%(算法能识别单自然人)
- 实丰 002862.SZ 验证:控盘度 22.61% → **47.46%**,家族 **40.77%** 自动识别 ✅

---

## [v4.4] — 2026-04-24 — 技术分析 + 可比公司 + 主力控盘三合一

> **主题**:补齐 A 股投资者最关心的 3 个空白 — 技术面、同行对标、机构/主力控盘。
> 所有逻辑下沉到 Python 脚本,Phase 指令仅作触发器;Phase 3 对应章节强制 Read 结构化 artifact(不再 LLM 凭记忆)。

### 根因

用户反馈 skill 只有基本面审计,**A 股投资者最核心的 3 个维度全部空白**:
- 技术面分析 = 0(有 3 年日线数据但没算 MA/MACD/RSI)
- 可比公司对比 = LLM 手写猜竞品
- 主力控盘/资金流 = 只用了 top10_holders + stk_holdernumber,完全没消费陆股通/两融/龙虎榜/大单资金流

### Added

#### 1. `scripts/peer_collector.py` — A 股同行业自动采集

- 基于 `stock_basic.industry` + `daily_basic` 按市值相近度排序取 Top N peer
- 输出 `peer_analysis.md`: §1 对比表(6 行 × 13 列) + §2 分位分析(ROE/毛利/净利/PE/PB/增速 6 维度) + §3 硬判定对比洞察
- 闻泰实跑: 5 家同行业 peer(格科微/全志/国科/星宸/赛微),PB 分位 100%(最便宜),毛利率分位 20%(落后),**事实客观**

#### 2. `scripts/capital_flow.py` — 主力控盘与资金流向(6 接口 + 6 推导指标)

**数据源**(Tushare 2000+ 积分):
- `moneyflow`(个股主力资金近 60 日)
- `moneyflow_hsgt`(陆股通大盘)
- `hk_hold`(陆股通个股持股每日)
- `margin_detail`(两融每日)
- `top_list` + `top_inst`(龙虎榜 + 机构席位近 30 日)

**推导 6 控盘指标**(每个都有🟢/🟡/🔴 自动档位):
1. 主力控盘度(前 10 流通股东合计持股 <30% / 30-50% / ≥50%)
2. 筹码集中度 2×2 矩阵(户数变化 × 户均持股)
3. 陆股通持仓趋势(20/60 日变化)
4. 两融杠杆方向(融资余额相对 60 日中位数)
5. 主力资金流(近 20 日大单净流入天数)
6. 龙虎榜机构活跃(上榜次数 + 机构净买入)

**闻泰实跑**:🔴 "筹码分散(户数+5.7%, 户均-5.4%)= 机构退出, 散户涌入" + 🔴 "主力资金近 20 日仅 6 日净流入, 累计 -2,692 万" — **精确定量打脸散户信心**

#### 3. `scripts/technical_analysis.py` — MA/MACD/RSI/布林带/成交量/支撑阻力

- 输入: Phase 1 `daily.parquet`(近 3 年日线)
- 指标: MA5/20/60/120 排列、MACD(12,26,9)金叉死叉、RSI(14)超买超卖、BOLL(20,2σ)位置、成交量异常、近 60/120 日支撑阻力位
- **闻泰实跑**: 3 🔴 信号 — 均线空头排列 + 破 MA120 + MACD 死叉;近 60 日 -28%;距 60 日支撑 28.27 元仅 0.28%(几乎贴底)

### Changed

- **Phase 1 指令** (`phases/phase1-data-collection.md`) 新增 3 步:
  - Step 1.2 `peer_collector` → `peer_analysis.md`
  - Step 1.3 `capital_flow` → `capital_flow.md`
  - Step 1.4 `technical_analysis` → `technical_analysis.md`

- **Phase 3 指令** (`phases/phase3-analysis-report.md`) 强制联动:
  - Step 4 §四 公司基本面 加 **"主力控盘与筹码分析"** 子节 → Read `capital_flow.md` §1/§2/§3/§8
  - Step 8 §八 可比公司对标 **强制 Read `peer_analysis.md`** → §1 对比表 + §2 分位 + §3 洞察直接搬入,禁止凭记忆猜竞品
  - Step 9 §九 估值末尾加 **9.4 技术面位置** 子节 → Read `technical_analysis.md`,必写"基本面 × 技术面" 4 种配合判断
  - Step 12 自检清单加 3 项(§四/§七/§八/§九 强制联动)

- **`assets/templates/report-skeleton.md`** 骨架更新:
  - §四 加 `capital_flow_summary_table / top10_float_holders_table / chip_concentration_2x2` 3 个 placeholder
  - §七 `资金流向信号` 改为 Read `capital_flow.md` §4/§5/§6
  - §八 骨架改为 §8.1-8.4 四子节(A 股 peer / 分位 / 洞察 / 海外补充)
  - §九 加 9.4 `技术面位置` 子节 + 3 个 placeholder

- **`assets/validation/report-checklist.json`** 新增 `phase3_mandatory_data_artifacts` section,列出 4 个必须消费的 artifact

- **Phase 6 审核清单** 从 22 项扩至 **23 项**(新增 #23 "Phase 1 结构化 artifact 消费"检查)

### Coverage

- 🇨🇳 A 股: 5 个 Python 模块全部可用(tushare_collector + financial_audit + peer_collector + capital_flow + technical_analysis)
- 🇺🇸 美股: 仅 yfinance + financial_audit,peer/capital/tech 三模块暂不支持
- 🇭🇰 港股: 同美股

### Not in scope (v4.5 继续)

- ❌ `scripts/validate_report.py` validator(仍推迟)
- ❌ `scripts/event_backtest.py`(业绩预告/回购/增持事件 → 次日/次月股价表现的历史规律)
- ❌ 美股/港股版本的 peer/capital/tech 3 模块

---

## [v4.3] — 2026-04-24 — assets 目录 + 报告骨架强制化

> **主题**:符合 Anthropic 官方 skill 规范的资产分离,修复"每次报告格式都不一样"的根因。

### 根因诊断(用户反馈驱动)

用户反馈 2 个问题,调研发现是**同一个根因的 3 重坏**:
1. "我怎么没有用 assets" — skill 从未建 `assets/` 目录
2. "每次报告的风格都不一样" — 3 份历史报告(闻泰/实丰/震安)的 Exec Summary 字段名和字段数量完全不同

**根因**:
- `references/report-template.md` 本身是坏的(12 章节 + 两个"四"、两个"五")
- Phase 3 指令**从未加载**它 → LLM 每次凭记忆生成 15 章节
- `references/html-template-guide.md` 是纯散文,没有真实 `.css` 或 `.html` 文件 → HTML 样式每次重写

### Added

- **`assets/` 目录**(官方 L3 资源层,按需加载,零上下文成本)
  - `assets/templates/report-skeleton.md` — 15 章节严格骨架 + `{{placeholder}}`(Phase 3 强制加载)
  - `assets/templates/exec-summary-schema.md` — Exec Summary 7 固定字段 + 6 类禁用字段黑名单
  - `assets/html/base.html` — HTML 骨架(sticky nav + hero + 15 section placeholder + footer)
  - `assets/html/styles.css` — 真 CSS 文件(16 变量 + 9 组件样式 + 响应式 + 打印)
  - `assets/html/components.html` — 10 个组件片段库(评分环/维度条/4 情景卡/期望回报/团队名片/风险项/时间轴/情绪量表/估值区间/洞察卡片)
  - `assets/validation/report-checklist.json` — 机器可读的 22 项审核清单(供 v4.4 validator)
  - `assets/validation/insight-card-schema.json` — Phase 5 9 字段 schema

### Changed

- **Phase 3 指令**(`phases/phase3-analysis-report.md`)
  - 新增 **Step 0.5 强制加载骨架**:Read `assets/templates/report-skeleton.md` + `exec-summary-schema.md`
  - Step 12 组装规则改为"以骨架为真相源",15 章节列表指向骨架文件
  - 分段写入 5 批的内容描述改为"填充骨架对应章节 placeholder"
  - 新增自检指令:`grep -c '^## §' *.md` 应 = 15

- **Phase 6 指令**(`phases/phase6-review-publish.md`)
  - Part B HTML 生成改为"Read assets/html/base.html + styles.css + components.html 并按占位填充"
  - 禁止凭记忆重写 CSS、自创变量名、自命名组件 class
  - 修复 L103-121 章节表 bug(原表跳过 §十一,编号错乱)→ 新 15 章节表与骨架字节对齐
  - 审核清单从 20 项扩至 **22 项**:
    - #21 HTML 资产加载(`grep -c '^\s*--c-' *.html` ≥16, 组件命中率 ≥8/9)
    - #22 Exec Summary 7 字段 schema(禁用字段黑名单扫描)

- **`references/report-template.md` → `report-template.LEGACY.md`**(改名废弃,加头注"已废弃,用 assets/templates/report-skeleton.md")
- **`references/html-template-guide.md` 精简**(删除所有代码块,保留设计哲学;所有可执行代码迁至 `assets/html/`)
- **`SKILL.md`** 参考索引表补充 `assets/` 三个子目录;废弃 `report-template.md` 行

### Fixed

- `references/report-template.md` 章节号错乱(两个"四"、两个"五",总数仅 12 章节)——从根本上靠骨架文件替代
- Phase 6 L103-121 章节表跳过 §十一(从 §十 直接到 §十二)——修正为完整 15 章节顺序

### Not in scope (v4.4 继续)

- ❌ `scripts/validate_report.py` validator 脚本 — 推迟到 v4.4,基于 v4.3 新骨架稳定 1-2 次后定规则
- ❌ 翻修已发布的闻泰/实丰/震安 HTML(保留作历史对照)
- ❌ 多语言模板

### 向后兼容

- `scripts/report_parser.py` **不需要改** — 它按 `[Tushare:*]`/`[PDF:*]` 标签匹配,不按章节标题,历史报告监控不受影响
- 已发布的 GitHub Pages 报告链接保持有效

---

## [v4.2] — 2026-04-24 — 估值一致性 + 核心资产剥离 SOTP

> **主题**：修复真实案例（闻泰科技 600745.SH 分析）暴露的 3 个估值框架缺陷，防止未来同类错误。

### Fixed (3 个真实案例暴露的缺陷)

1. **估值锚与投资回报锚不一致**
   - 症状：§九"三角验证均值 30.6 元" vs §十"投资回报基准 33.8 元" 两个数字让读者混淆
   - 修复：`references/valuation-frameworks.md §3.3` 改为"交叉验证"而非均值；`phase3-analysis-report.md Step 9` 强制 DCF 概率加权为**唯一锚**，§十 与 §九 共用情景
   - 新增 Phase 6 审核项 #19：§九 与 §十 共用情景/概率分布不一致则审核不通过

2. **悲观情景 SOTP 不完整**
   - 症状：悲观情景只算"核心资产按 1x PB 出售"，忽略母公司剩余现金/金融资产/负债/清算成本
   - 修复：`valuation-frameworks.md` 新增 §3.4 **核心资产剥离风险的 SOTP 强制要求**；`phase3-analysis-report.md` 新增 **Step 9.5** 触发条件与两步强制执行
   - 新增 Phase 6 审核项 #20：若触发但缺"剩余资产清单"或"最差情景"则不通过

3. **"剥离后剩什么"缺乏披露**
   - 症状：主报告没有"若核心资产被剥离，上市公司还剩什么资产"的清单，读者无法评估下行地板
   - 修复：`phase3-analysis-report.md Step 9.5.1` 强制在 §四 业务概况加子节"★ 若核心资产被剥离的剩余资产清单"，明细列出 7 项可变现资产 + 3 项负债

### Added

- **4 情景 DCF**（乐观/基准/悲观 + **最差 3-10% 权重**）替代 3 情景，最差情景作为 tail risk floor
- **估值表角色列**: DCF 概率加权 = ⭐ 估值锚；可比倍数/PB = 交叉验证（自洽判定 < 10% ✓ / 10-20% ⚠ / > 20% 🔴）

### Changed

- `phase6-review-publish.md`：审核清单从 18 项扩至 **20 项**
- `phase3-analysis-report.md Step 7/9/9.5/11` 逻辑重构

---

## [v4.1] — 2026-04-24 — 精简 + 关键信息保护

> **主题**：激进精简阅读负荷（-40%），同时 100% 保护防作弊机制、监控链路、分歧多样性。

### Changed
- **定性判断框架 4 → 3**：删除"估值判断"框架（§九 估值分析 + `audit_report.md` 的 Valuation Anomaly 已完全覆盖）
- **洞察字段 13 → 9**：合并"证据等级 + 置信度 + 时间窗"为单行"信号强度"（`Level A / 高 / 1Y` 格式）；删除低价值字段（议题来源 / 信息不对称 edge 分类 / 类型）
- **Phase 4 结构精简**：3 角色保留，每角色从 5 段 → 3 段固定结构（核心结论 / 最担忧风险 / 对 1 条洞察回应），总篇幅 -60%
- **Phase 4/5 独立文件职责重定义**：独立文件不再重复主报告内容，只保留主报告没有的深度附件（Level C 附录 / 议题感知 / 共识映射 / 哲学分歧深度解读）
- **§二评分总览**删"关键理由"列（证据由 §六 承接）
- **§三快筛 vs §十一 致命看空去重**：§十一 直接引用 §三 结果，不重复列 6 项
- **§十五数据来源按 3 类分组**（Tushare API / PDF 原文 / WebSearch）
- **§四.5 / §六.2 改为正常子节编号**（`### 管理层前瞻信号` / `### 资金流向信号`）
- **黑白分割规则**：3 框架中 ≥ 2 同向 → 对应方向；否则中性-分歧

### Fixed
- `scripts/report_parser.py` 扩展 `FIELD_SIGNAL_STRENGTH` 正则支持 v4.1 合并字段，同时向后兼容 v3 分离字段

### Preserved (关键信息保护)
- ✅ 证据等级 A/B/C（防 Level C 伪推理）
- ✅ 时间窗（Phase 7 monitor 用）
- ✅ 证伪条件（monitor 自动扫描）
- ✅ 数学推导（v4 防猜测核心）
- ✅ Level C 附录（Phase 6 Part D 补查输入）
- ✅ 关键议题感知清单 / 市场共识映射
- ✅ 3 种投资哲学分歧多样性（保留 3 角色）

---

## [v4.0] — 2026-04-23 — Python 数据层 + 大师框架 + 量化监控

> **主题**：从"LLM 凭感觉写"进化为"结构化数据 + 学术框架 + 可审计"。

### Added
- **Python 数据层 `scripts/`（10 模块）**:
  - `tushare_collector.py`：A 股 25 个 API（3 大报表 + 股东 + 质押 + 业绩预告 + 高管薪酬 + 股东户数 + 回购 + 分业务 + 北向 + 披露日历）
  - `us_collector.py`：美股 yfinance 封装
  - `hk_collector.py`：港股 Tushare + yfinance 混合
  - `pdf_reader.py`：财报 PDF 9 段落精析（利润表变动原因 / 子公司业绩 / MD&A / 风险因素 / 非经 / 前十大股东 / 资产负债变动 / 现金流变动 / 主要会计数据）
  - `derived_metrics.py`：30+ 衍生指标（CAGR / FCF / ROIC / Owner Earnings）
  - `data_cache.py`：7 天 TTL Parquet 缓存
  - `financial_audit.py`：**11 大师框架异常审计**
  - `report_parser.py`：解析历史报告带标签指标
  - `monitor.py`：量化监控核心
- **Phase 7 量化监控**：`/company-analysis <公司> --monitor` 手动触发
- **Phase 3 Step 1.5 自动 audit**：生成 `audit_report.md` + JSON
- **11 大师框架**：
  - Piotroski F-Score（0-9 分财务健康）
  - Beneish M-Score（盈余操纵检测）
  - Altman Z-Score（破产预警）
  - DuPont 5-Factor（ROE 归因）
  - Buffett Quality（OCF/NI / 应收 / 存货 / 商誉 / 非经）
  - Sloan Accrual Anomaly
  - Governance Red Flags（质押 / 减持 / CEO 对齐）
  - Shareholder Flow（户数×户均 2×2 矩阵）
  - Forward Guidance Anomaly（首亏 / 预减 / 区间宽度）
  - **Valuation Anomaly**（PB 历史分位 + **PB vs ROE Gordon 错配**）
  - Related-Party Exposure（长期股权投资波动 + 投资收益爆雷）

### Changed
- **Phase 顺序重排**：`P1 → P2 → P3 → P4 → P5(差异化) → P6(审核)`（原 Phase 2.5 后移为 Phase 5）
- **Phase 5 输入源 4 个**：Phase 1 数据 + Phase 2 PDF + Phase 3 画像 + **Phase 4 角色分歧（新）**
- **SKILL.md 协调器显式化**：前 80 行含 ASCII 流程图 + 快速导航 + 职责清单
- **每个 phase 顶部加面包屑导航**
- **洞察 11 → 13 字段**：新增 ★数学推导 + ★证据等级 A/B/C
- **洞察数学推导反例库防伪**：5 种伪推导命中即降级 Level C
- **§三快筛新增第 6 项**：Audit ≥ 2 个 🔴 触发快筛否决
- **7 定性框架 → 4 框架**（v4.0 版本，v4.1 再精简为 3）
- **章节合并**：§九估值 + §十一投资回报 → 合并；§十四时效性 + §十五信息来源 → 合并
- **Tushare 字段精简**：income 85→32 / balancesheet 152→44 / cashflow 97→34（存储 -70%）

### Fixed
- v3 审计发现的 5 个系统性缺陷全部修复：
  1. 财报获取依赖第三方摘要 → 强制 PDF 原文
  2. 洞察允许纯推理 → 强制数学推导
  3. 定性判断只是打分 → 改为逻辑三段式
  4. 信息缺口不闭环 → Part D 5 步穷举补查
  5. 无结构化数据层 → Tushare + yfinance + pypdf

---

## [v3.3] — 2026-04-20

### Added
- Phase 2.5 差异化洞察（Variant Perception）

---

## [v3.2] — 2026-04-19

### Added
- 协调器质量门控（每阶段检查清单）
- HTML 完整性强制（HTML section ≥ MD ## × 0.8）
- 分段写入保护（避免超长报告丢失内容）

---

## [v3.1] — 2026-04-18

### Added
- output 目录结构规范（`output/{company}/`）
- Phase 2 自动搜索模式（用户未提供文档时）
- Phase 3 深度分析增强

---

## [v3.0] — 2026-04-16

### Added
- 5 阶段流水线（数据采集 / 文档精析 / 综合分析 / 多角色结论 / 审核发布）
- 上市公司支持（A股 / 美股 / 港股）
- 多角色投资人评审（段永平 / 巴菲特 / 张磊 等）
- 10 维度事实评分

---

## [v2] — 历史版本

### v2 修订
- 实丰文化案例发现 v1 归因错误（应为超隆光电参股爆雷）
- 新增手工精读 PDF 流程
- 评分计算错误修正

---

## [v1] — 初版

- 基础 skill 框架
- WebSearch 驱动的数据采集
- 基于第三方摘要的分析（已被 v4 取代）
