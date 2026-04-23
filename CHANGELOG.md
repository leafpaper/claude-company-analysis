# Changelog

所有重要变更按版本记录。格式受 [Keep a Changelog](https://keepachangelog.com/) 启发。

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
