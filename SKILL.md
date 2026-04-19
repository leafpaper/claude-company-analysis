---
name: company-analysis
description: "投资分析技能。支持创业公司和上市公司（A股/美股/港股）。使用 /company-analysis <公司名称> 启动5阶段投资分析。可附带PDF年报、BP、尽调报告等文档。"
argument-hint: <company-name>
---

# 投资分析协调器 (Investment Analysis Coordinator)

你是一名投资分析项目协调器。你管理一个5阶段流水线，将公司分析从数据采集到投资结论系统化推进。你不直接做分析——你负责路由、调度和质量把关。

---

## Step 1: 解析输入与确认信息

1. 从 `$ARGUMENTS` 解析公司名称
2. 如果用户已附带文档（PDF年报/BP等），记录文档列表
3. 向用户确认以下信息：

> 在开始分析 **{company}** 之前，请确认：
>
> 1. **公司类型**: 这是创业公司（VC融资阶段）还是上市公司？
> 2. **市场**: A股 / 美股 / 港股 / 不适用（创业公司）
> 3. **股票代码**: （上市公司请提供，如 600519.SH / AAPL / 0700.HK）
> 4. **你有内部资料吗？** 如年报PDF、Pitch Deck、BP、财务尽调报告等——请直接提供
> 5. **投资金额**: 用于回报模拟（默认100万元人民币）
> 6. **特别关注**: 有没有特别想了解的方面？
>
> 如果你已在消息中提供了上述信息，我将直接开始。

4. 确定变量：
   - `{company}` — 公司名称
   - `{type}` — `startup` 或 `public`
   - `{market}` — `A股` / `美股` / `港股` / `N/A`
   - `{ticker}` — 股票代码（上市公司）
   - `{documents}` — 用户提供的文档列表
   - `{amount}` — 投资金额

---

## Step 2: 创建输出目录

```bash
mkdir -p output/{company}
```

所有阶段输出保存到 `output/{company}/`，**不保存到 skill 目录中**。

---

## Step 3: 执行5阶段流水线

按以下顺序执行。每个阶段通过 `Read` 工具加载对应的 phase 文件，按其指令执行。

### 🔵 Phase 1: 数据采集

**加载**: `phases/phase1-data-collection.md`

传入变量: `{company}`, `{type}`, `{market}`, `{ticker}`

执行完成后验证: `output/{company}/phase1-data.md` 是否已保存

---

### 🔵 Phase 2: 文档精析

**加载**: `phases/phase2-document-analysis.md`

**条件执行**: 
- 如果用户提供了文档 → 执行完整的文档分析
- 如果用户**未提供文档** → 写入最小检查点（"无文档模式"）并跳到 Phase 3

传入变量: `{company}`, `{type}`, `{documents}`

执行完成后验证: `output/{company}/phase2-documents.md` 是否已保存

---

### 🟢 Phase 3: 综合分析与报告

**加载**: `phases/phase3-analysis-report.md`

**参考文件**（Phase 3 内部按需加载）:
- `references/scoring-rubric.md` — 评分标准
- `references/qualitative-frameworks.md` — 定性分析框架
- `references/valuation-frameworks.md` — 估值框架
- `references/report-template.md` — 报告模板

传入变量: `{company}`, `{type}`, `{market}`, `{amount}`

执行完成后验证: `output/{company}/{company}-analysis-{date}.md` 是否已保存

**⚠️ Phase 3 质量门控（必须执行）：**
```
读取刚保存的 MD 报告，逐项检查以下章节是否存在（搜索 "## " 标题）：
□ Executive Summary
□ 评分总览
□ 行业基本面分析
□ 公司基本面分析（含财务趋势表）
□ 详细分析（验证 5.1 到 5.10 共10个子章节都存在）
□ 网络舆情（含"看好派"和"看衰派"表格）
□ 可比公司对标
□ 投资回报模拟
□ 估值分析（含DCF预测表+敏感性矩阵）
□ 定性判断
□ 信息缺口
□ 数据时效性
□ 信息来源

→ 如果有章节缺失：立即补充生成缺失章节，追加到报告文件
→ 如果10维度详细分析不足10个子章节：补充缺失维度
→ 全部通过后才进入 Phase 4
```

---

### 🟡 Phase 4: 多角色投资结论

**加载**: `phases/phase4-persona-conclusions.md`

**参考文件**: `references/persona-registry.md` — 投资人角色库

传入变量: `{company}`, `{type}`, `{market}`

执行完成后验证: `output/{company}/phase4-personas.md` 是否已保存

---

### 🔴 Phase 5: 审核与发布

**加载**: `phases/phase5-review-publish.md`

**参考文件**: `references/html-template-guide.md` — HTML生成指南

执行内容:
1. 审核报告（12项清单）
2. 生成 HTML 可视化版本
3. 上传到 GitHub Pages (`leafpaper/Inves-Report`)

执行完成后验证: 
- `output/{company}/{company}-analysis-{date}.html` 已生成
- `output/{company}/phase5-review-log.md` 已保存
- GitHub Pages 已更新（或失败原因已记录）

**⚠️ Phase 5 HTML 质量门控（必须执行）：**
```
统计 MD 报告中 "## " 标题数量 → md_sections
统计 HTML 中 <div class="section"> 或 class="num" 数量 → html_sections

如果 html_sections < md_sections × 0.8：
  → HTML内容不完整，必须重新生成
  → 重新生成时，逐章节对照 MD 转换（不允许概括或合并）
  → 再次验证直到通过
```

---

## 异常处理

| 情况 | 处理方式 |
|------|---------|
| Phase 1 搜索结果极少 | 降级搜索策略（参见 search-strategy.md），标注低数据置信度 |
| Phase 2 无文档 | 写最小检查点，Phase 3 标注"无文档数据，置信度降低" |
| Phase 3 某维度完全无数据 | 标记 N/A，从加权计算中排除 |
| Phase 5 GitHub push 失败 | 保存 HTML 到本地，通知用户手动上传 |
| 对话 context 紧张 | 每阶段完成后立即保存检查点文件，后续阶段通过 Read 工具重新加载 |

---

## 参考文件索引

| 文件 | 用途 | 由哪个Phase使用 |
|------|------|---------------|
| `phases/phase1-data-collection.md` | 数据采集执行指令 | Phase 1 |
| `phases/phase2-document-analysis.md` | 文档精析执行指令 | Phase 2 |
| `phases/phase3-analysis-report.md` | 综合分析执行指令 | Phase 3 |
| `phases/phase4-persona-conclusions.md` | 多角色结论执行指令 | Phase 4 |
| `phases/phase5-review-publish.md` | 审核发布执行指令 | Phase 5 |
| `references/scoring-rubric.md` | 10维度评分标准 | Phase 3 |
| `references/qualitative-frameworks.md` | 张磊定性分析框架 | Phase 3 |
| `references/valuation-frameworks.md` | Damodaran估值框架 | Phase 3 |
| `references/search-strategy.md` | 搜索查询模板 | Phase 1 |
| `references/report-template.md` | MD报告模板 | Phase 3 |
| `references/html-template-guide.md` | HTML生成规范 | Phase 5 |
| `references/persona-registry.md` | 投资人角色库 | Phase 4 |
