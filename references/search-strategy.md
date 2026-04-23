# 联网搜索策略（v3 - 辅助定位）

> **v3 重大调整**：本文件从 v1/v2 的"主数据源"降级为**辅助定位**工具。
> 主数据源是 `scripts/tushare_collector.py` 和 `scripts/pdf_reader.py`，见 `phases/phase1-data-collection.md`。
>
> WebSearch 只用于：**舆情 / 新闻事件 / 行业背景 / PDF URL 定位**。
> **禁止**用于关键财务数据（收入、利润、PE、PB、ROE 等）——这些必须来自 Tushare API 或 PDF 原文。

---

## 时效性规则

1. 所有查询附加时间限定词：`{YEAR}`, `latest`, `recent`, `最新`
2. 来源新鲜度优先级：
   - ≤ 6 个月：高置信度
   - 6-12 个月：中置信度，需交叉验证
   - > 12 个月：标记 `[历史数据: YYYY-MM]`，仅作背景参考
3. 所有引用必须带 URL + 发表日期

---

## 允许的用途

### A. 定位 PDF 报告 URL（最重要）

用 WebSearch 找到财报 PDF 的直接下载地址，然后交给 `pdf_reader.py` 处理。

**A 股（巨潮资讯）**:
```
site:cninfo.com.cn "{company}" {ticker} 年度报告 {YEAR}
site:cninfo.com.cn "{company}" 第三季度报告 {YEAR}
site:cninfo.com.cn "{company}" 业绩预告 {YEAR}
```

**美股（SEC EDGAR）**:
```
site:sec.gov {ticker} 10-K {YEAR}
site:sec.gov {ticker} 10-Q {YEAR}
```

**港股（披露易）**:
```
site:hkexnews.hk "{company}" annual report {YEAR}
site:hkexnews.hk "{company}" interim report {YEAR}
```

### B. 社交媒体舆情（Phase 1 §8）

**A 股**:
```
site:xueqiu.com "{company}" {YEAR}
site:eastmoney.com "{company}" 股吧
site:zhihu.com "{company}" 投资
"{company}" 研报 券商 目标价 {YEAR}
```

**美股**:
```
site:seekingalpha.com "{company}" {YEAR}
site:reddit.com/r/investing "{ticker}"
site:reddit.com/r/stocks "{ticker}"
"{ticker}" analyst consensus price target {YEAR}
```

**港股**: 混合：xueqiu + aastocks + seekingalpha

### C. 行业与宏观背景

```
"{industry}" 行业分析 市场规模 {YEAR}
"{industry}" policy regulation {YEAR}
"{industry}" CAGR 增速 {YEAR}
"{company}" vs "{competitor}" 对比
```

### D. 突发新闻与重大事件

```
"{company}" 公告 {YEAR}
"{company}" 并购 / 重组 / 分拆 {YEAR}
"{company}" 诉讼 / 监管 / 处罚 {YEAR}
"{company}" 业绩预告 / 业绩快报
```

---

## 禁止的用途

以下场景**严禁**使用 WebSearch 作为数据来源，必须走 Tushare API / PDF：

| 场景 | 正确来源 |
|------|---------|
| 最近 3 年的营收 / 净利 / 毛利率 | `tushare_collector.income()` + `fina_indicator()` |
| 当前 PE / PB / PS / 市值 | `tushare_collector.daily_basic()` |
| 资产负债表任一科目 | `tushare_collector.balancesheet()` |
| 现金流量表任一科目 | `tushare_collector.cashflow()` |
| Q3 亏损的具体构成 | `pdf_reader.extract_sections()` → `income_statement_changes` |
| 子公司/参股公司业绩 | `pdf_reader.extract_sections()` → `subsidiaries` |
| 前十大股东 | `tushare_collector.top10_holders()` + PDF 交叉 |
| 股权质押 | `tushare_collector.pledge_detail()` |

**为什么禁止？**

v1 的 Q3 亏损归因错误根因就是用 WebSearch 拿到了"证券之星简析"，被"三费占比上升"的简化叙事误导，完全错过了**超隆光电参股爆雷**这个真实主因（PDF Page 4 明确写着）。

v3 的铁律是：**关键数据必须有可审计的原文锚点**。Tushare 给你结构化数字，PDF 给你"为什么变动"的管理层原文——两者不可替代。

---

## WebFetch 深度阅读（精选 3-5 份）

从 WebSearch 结果中**精选** 3-5 个最有信息密度的页面做 WebFetch：

**优先级 P1（必读）**:
- 1-2 份近期高质量研报（券商深度分析）
- 管理层最新一次电话会议 / 调研纪要

**优先级 P2（选做）**:
- 1-2 份代表性的多空辩论帖（雪球 / Reddit）
- 1 份行业协会 / 咨询机构的年度报告

**禁止 WebFetch**:
- 财经网站的财务摘要页（如 `stockstar.com` / `eastmoney.com` 的"财务分析"页）——这些是二手数据，走 Tushare 就行
- 算法生成的评级页面（如"证券之星评级"）

---

## 查询模板速查

### 创业公司（非上市）
创业公司没有 Tushare / PDF，只能靠 WebSearch。参考 `phases/phase1-data-collection.md` §7 "创业公司模式"。

### 条款 / 交易
```
"{company}" Series {X} funding {YEAR}
"{company}" valuation post-money pre-money
"{company}" term sheet leak OR "liquidation preference"
"{company}" down round OR up round {YEAR}
```

### 团队背景
```
"{CEO name}" "{company}" LinkedIn
"{founder name}" biography previous companies
"{company}" executive team hiring firing {YEAR}
```

### 社交媒体监控（负面信号）
```
"{company}" controversy scandal lawsuit {YEAR}
"{company}" former employee review glassdoor
"{company}" 离职 负面 评价
```

---

## 降级策略（Tushare/PDF 失败时）

若 Phase 1 Step 1-3（结构化数据 + PDF）失败：

1. **记录失败原因**（积分不足？接口抖动？PDF URL 错误？）
2. **通知用户**：告诉用户降级原因，征求是否继续
3. **降级为 WebSearch 模式**，但 **Phase 1 生成的 phase1-data.md 必须在开头显式标注**：

```markdown
⚠️ **数据降级**: 本次采集未能使用 Tushare API / PDF 原文，仅依赖 WebSearch 二手摘要。
   结论的置信度整体降低。建议:
   - 核对 TUSHARE_TOKEN 是否有效（积分是否充足）
   - 核对 PDF URL 是否正确
   - 重跑 Phase 1
```

降级时所有关键数据打 `[WebSearch-降级: domain.com]` 标签，Phase 3 综合分至少 -0.5。
