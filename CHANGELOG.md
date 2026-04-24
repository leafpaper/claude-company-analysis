# Changelog

所有重要变更按版本记录。格式受 [Keep a Changelog](https://keepachangelog.com/) 启发。

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
