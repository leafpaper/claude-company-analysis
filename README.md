# Claude Code 投资分析 Skill

一个用于 Claude Code 的自定义 Skill，通过 **5 阶段流水线**系统性分析公司投资价值。支持**创业公司**和**上市公司**（A股/美股/港股）。

**报告示例**：https://leafpaper.github.io/Inves-Report/

---

## 核心特性

### 5 阶段流水线架构

```
Phase 1: 数据采集 → Phase 2: 文档精析 → Phase 3: 综合分析 → Phase 4: 多角色结论 → Phase 5: 审核发布
```

| 阶段 | 角色 | 做什么 |
|------|------|--------|
| **Phase 1** | 金融调查记者 | 联网搜索 + 社交媒体舆情（雪球/知乎/Reddit/SeekingAlpha） |
| **Phase 2** | 财务文档分析师 | PDF年报/BP/尽调报告的结构化数据提取 |
| **Phase 3** | 资深投资分析师 | 行业基本面 + 公司基本面 + 10维度评分 + 估值 + 回报模拟 |
| **Phase 4** | 世界级投资人评审团 | 巴菲特/段永平/张磊/木头姐等真实投资人角色独立点评 |
| **Phase 5** | 报告审计师 + 发布经理 | 21项审核清单 + HTML生成 + GitHub Pages自动发布 |

### 支持的公司类型

| 类型 | 搜索策略 | 评分标准 | 估值方法 | 回报模拟 |
|------|---------|---------|---------|---------|
| **创业公司** | 7轮搜索+行业专项 | VC评分标准 | DCF+倍数+实物期权 | 入场→稀释→退出 |
| **上市公司** | 8轮搜索+财务数据+社交媒体 | 上市公司调整版 | 完整DCF+历史区间+DDM | 三情景目标价 |

### 分析框架

- **10维度加权评分** — 商业模式、市场机会、竞争格局、增长指标、团队、产品技术、财务健康、风险、估值、退出/回报潜力
- **张磊《价值》定性框架** — 结构性价值、动态护城河、大雪长坡、价值创造 vs 转移
- **Damodaran 估值体系** — DCF、相对估值、实物期权、Narrative-to-Numbers、估值三角验证
- **社交媒体舆情采集** — 雪球、知乎、Reddit、SeekingAlpha、东方财富等平台
- **多角色投资结论** — 5位真实投资人角色（巴菲特/段永平/张磊/木头姐/彼得林奇）独立点评

## 一键安装

```bash
curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/install.sh | bash
```

安装完成后重启 Claude Code，即可使用 `/company-analysis` 命令。

## 使用方法

在 Claude Code（CLI 或 VS Code 扩展）中输入：

```
/company-analysis 苹果
```

Skill 会自动判断公司类型（创业/上市），按 5 阶段流水线执行分析。

### 示例

```bash
# 上市公司
/company-analysis 苹果          # A股/美股自动识别
/company-analysis Tesla         # 美股
/company-analysis 腾讯          # 港股

# 创业公司（附带BP）
/company-analysis 纽瑞芯        # 可同时上传 pitch deck PDF
/company-analysis 程星通信       # 可同时上传年报/BP
```

你可以同时提供 PDF 年报、Pitch Deck、财务尽调报告等文档，Phase 2 会自动提取关键数据并与 Phase 1 的公开数据交叉验证。

### 输出位置

所有分析结果保存在 `~/投资报告/{公司名}/` 目录下：

```
~/投资报告/苹果/
├── phase1-data.md              # 阶段1：原始数据（带来源URL）
├── phase2-documents.md         # 阶段2：文档提取数据
├── 苹果-analysis-2026-04-19.md  # 最终分析报告
├── 苹果-analysis-2026-04-19.html # HTML可视化版本
├── phase4-personas.md          # 多角色投资结论
└── phase5-review-log.md        # 审核日志
```

## 多角色投资结论

Phase 4 会激活 2-3 位真实投资人角色，每人独立阅读分析报告并给出结论：

| 角色 | 投资哲学 | 适用市场 |
|------|---------|---------|
| 巴菲特 | 以合理价格买优秀企业，护城河，安全边际 | A股上市/美股 |
| 段永平 | 买对的公司以对的价格，"本分"文化 | A股创业/上市 |
| 张磊 | 长期结构性价值，大雪长坡，价值创造 | A股创业/港股 |
| 木头姐 | 颠覆性创新，5年维度，技术融合 | 美股 |
| 彼得林奇 | 投资你了解的，PEG比率，公司分类法 | 美股 |

每位角色给出独立结论（买入/持有/卖出/放弃），引用报告数据，最后总结分歧点。

## 文件结构

```
~/.claude/skills/company-analysis/
├── SKILL.md                              # 精简协调器（~100行，路由+调度）
├── phases/                               # 5个阶段执行文件
│   ├── phase1-data-collection.md         # 数据采集（社交媒体舆情）
│   ├── phase2-document-analysis.md       # 文档精析（年报/BP/尽调）
│   ├── phase3-analysis-report.md         # 综合分析（行业+公司基本面+评分）
│   ├── phase4-persona-conclusions.md     # 多角色投资结论
│   └── phase5-review-publish.md          # 审核+HTML+GitHub发布
├── references/                           # 分析框架（7个文件）
│   ├── scoring-rubric.md                 # 10维度评分标准（含上市公司调整）
│   ├── qualitative-frameworks.md         # 张磊《价值》+ VC定性方法论
│   ├── valuation-frameworks.md           # Damodaran估值 + 条款分析
│   ├── search-strategy.md                # 搜索策略（含社交媒体平台）
│   ├── report-template.md                # 报告模板（含行业/公司基本面）
│   ├── html-template-guide.md            # HTML生成规范
│   └── persona-registry.md              # 5位投资人角色库
```

## 卸载

```bash
curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/uninstall.sh | bash
```

## 许可证

MIT
