# Claude Code 投资分析 Skill (v6.0)

> **结构化数据 + PDF 原文 + 11 大师框架自动审计** 的专业投资分析技能
>
> 支持 A 股 / 美股 / 港股 · 4 阶段流水线 + 可选量化监控 · 适用于 Anthropic Claude Code

<p align="center">
  <img src="https://img.shields.io/badge/version-v6.0-blue" alt="version">
  <img src="https://img.shields.io/badge/markets-A%E8%82%A1%20%7C%20%E7%BE%8E%E8%82%A1%20%7C%20%E6%B8%AF%E8%82%A1-green" alt="markets">
  <img src="https://img.shields.io/badge/audit-11%20frameworks-orange" alt="frameworks">
  <img src="https://img.shields.io/badge/report-8%20chapters-purple" alt="chapters">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="license">
</p>

**在线报告示例**: [leafpaper.github.io/Inves-Report](https://leafpaper.github.io/Inves-Report)

---

## 这是什么

一个跑在 Claude Code 里的 slash command（`/company-analysis`）。给它一个公司名（可选股票代码），它会自动采集结构化财报数据、强制精读年报/季报 PDF 原文、跑 11 个大师级会计审计框架，然后用 5 个串行写手分工写出一份 **9 章节**（含 **§七 投资决策内核**）的投资分析报告，再经 3 个评审 agent 并行打分 + 修正循环，最后渲染 HTML 并发布到 GitHub Pages。

核心定位：**用确定性数据 + 数学推导对抗"伪量化"和"AI 编故事"**。所有关键数字带来源标签（`[Tushare:income.revenue]` / `[PDF:q3_2025, P.4]`），估值走 P=F+N 分解 + 反向DCF + 叙事SOTP（DCF 概率加权作交叉验证），决策走"状态后验×赔率×路径"三分（好公司/好下注/好价格），所有红旗由脚本机械扫出。

---

## 设计原则

| 原则 | 含义 |
|------|------|
| **强制 PDF 精读** | 不依赖第三方摘要。年报/季报 PDF 必须下载并提取关键段落（利润表变动原因 / 子公司业绩 / MD&A / 风险因素 / 非经常损益 等），关键结论带 `[PDF:报告期, P.x]` 引用。 |
| **数学推导优先** | 估值赔率走 **P=F+N 分解 + 反向DCF 隐含预期 + 叙事分部SOTP**（v7.0），DCF 概率加权作 F 的交叉验证；逻辑猜测不得替代算术，每块须出数字。 |
| **决策内核（v7.0）** | 投资价值 = **状态后验 × 赔率 × 路径可承受性**，把"是不是好公司"拆成 **好公司 / 好下注 / 好价格** 三分 + 行动档位（六档）。源自"贝叶斯之美"五篇，定义见 `references/investment-decision-core.md`。 |
| **11 框架防盲点** | `scripts/financial_audit.py` 自动跑 Piotroski F / Beneish M / Altman Z / DuPont / Sloan 应计 / 治理 / 关联方等 11 个框架，机械扫出红旗，进入 §六。 |
| **定性不伪量化** | 护城河 / 管理层 / 催化剂走"看多 / 看空 / 中性-分歧"三档定性判断，**不打 `-2~+2` 分**、不做百分比修正——定性就是定性。 |
| **缺口必闭环** | §八 信息缺口强制 ≥ 3 条，每条记录已尝试的查询路径；补查成功必须反写到所有相关章节。 |
| **9 章节单一事实源去重** | 每个事实只在一处展开（评分即证据索引、估值与回报共用同一套情景概率），章节间不重复造数。章节边界真理源：`scripts/assemble_report.py:PART_EXPECTED_SECTIONS`。 |
| **可追溯监控** | `--monitor` 以历史报告的带标签指标为基线，重跑数据层比对变化，给出"维持 / 复评 / 重大修订"。 |

---

## 流水线（4 阶段 + 可选监控）

```
Step 0-2：环境自检 + 输入确认 + 建目录
   ↓
Phase 1 数据采集        （data-collector：Tushare + yfinance + 港股 + PDF 下载解析 + 11 框架 audit + peer / capital_flow / technical 快照）
   ↓
Phase 2 文档精析        （主 agent 自跑：精读 PDF 关键段落，提取原文引用）
   ↓
Phase 3 综合分析与报告  （phase3-part{1,2,3,4,5} 5 个串行写手 → assemble_report 拼成 9 章节）
   ↓
Phase 6 审核发布        （anti_lazy_lint 7 条机械规则 + reviewer-{narrative,valuation,redflag} 3 并行 + 修正循环 + build_html + GitHub Pages）

    [可选，手动触发] ↓
Phase 7 量化监控        （/company-analysis <公司> --monitor）
```

> 编号沿用历史（原 Phase 4 多角色、Phase 5 差异化洞察已在 v5.1.4 删除，不再占用阶段）。完整调度协议 / 质量门控 / 异常处理见 [SKILL.md](./SKILL.md) + [references/phase-orchestration.md](./references/phase-orchestration.md)。

**9 个 sub-agent**：`data-collector`（1）+ `phase3-part{1,2,3,4,5}`（5 个串行写手，§一执行摘要由 part1 在链尾汇总、§七 投资决策内核由 part4 合成）+ `reviewer-{narrative,valuation,redflag}`（3 个并行评审）。

---

## 报告结构（9 章节）

权威骨架：[`assets/templates/report-skeleton.md`](./assets/templates/report-skeleton.md)。

| 章节 | 内容 |
|------|------|
| **§一 执行摘要** | 一句话结论 + 估值锚 + 综合评分（基本面快照）+ Top3 风险/机会 + **决策结论**（来自 §七：决策三元组 + 三分 + 行动档位）。字段定义见 `assets/templates/exec-summary-schema.md`。 |
| **§二 公司基本面** | 业务板块 / 近 12 月动态 / 多年财务趋势表 / 前瞻信号 / 管理层 / 主力控盘与筹码 / SOTP 剩余资产。 |
| **§三 行业与竞争对标** | 行业规模趋势 + Porter 五力 + A 股同行业对标（peer 自动采集）+ 分位 + 海外同业补充。 |
| **§四 评分与维度证据** | 10 维度加权评分 + 逐维度证据（分数即证据索引，不再"总览/详细"两处重复）+ 定性综合判断。 |
| **§四 评分与维度证据** 续 | 末尾 **4.11 状态评估**：λ与证据临界密度 / 身份切换P1-P4 / 四层验证·权威认证 / 右尾·幂律·左尾 / 无记忆性检查（机制原料供 §七 合成）。 |
| **§五 估值、赔率与定价充分度** | P=F+N 价格分解（含 free option vs embedded obligation）+ 反向DCF 隐含预期 + ΔP 传播因子分解 + 叙事分部SOTP + DCF 概率加权（交叉验证）+ 回报与路径成本 + 赔率小结。 |
| **§六 风险与红旗审计** | 致命看空快筛 6 项 + 11 框架审计红旗汇总 + 致命看空论证 + **6.4 左尾防护·高信仰股特征**。 |
| **§七 投资决策内核**（v7.0 新增） | 状态后验 × 赔率 × 路径可承受性 → **决策三元组** + **三分结论**（好公司?/好下注?/好价格?）+ **行动档位**（核心仓/期权仓/等证据临界/不追高/减仓/回避）+ 证伪退出。各篇理念的合成结论。 |
| **§八 舆情与市场情绪** | 看多/看空声音各 ≥ 3 条 + 资金流向信号（北向 / 融资融券 / 主力）。 |
| **§九 数据来源与信息缺口** | 三类来源分组（Tushare / PDF / WebSearch）+ 信息缺口与尽调优先级 ≥ 3 条。 |

---

## 单次分析产出

```
output/{公司名}/
├── raw_data/
│   ├── *.parquet                  # Tushare / yfinance 结构化数据
│   ├── pdfs/*.pdf                 # 下载的财报 PDF
│   └── pdf_sections_*.json        # PDF 关键段落抽取
├── data_snapshot.md               # 9 节确定性数据（含限售解禁日历）
├── audit_report.md                # ⭐ 11 框架红旗清单
├── peer_analysis.md               # 同行业对标
├── capital_flow.md                # 资金流 / 筹码 / 北向 / 大宗
├── technical_analysis.md          # 技术面位置
├── phase1-data.md                 # 数据采集总结
├── phase2-documents.md            # 文档精析
├── phase3-part{1,2,3,4,5}.md      # 5 写手分稿
├── {公司}-analysis-{date}.md      # ⭐ 主报告（9 章节，assemble 拼接）
├── {公司}-analysis-{date}.html    # ⭐ HTML 可视化
├── phase6-review-log.md           # 审核日志
└── monitor_{公司}_{date}.md       # 监控简报（--monitor 触发时）
```

---

## 仓库结构

```
claude-company-analysis/
├── README.md                   # 本文件
├── CHANGELOG.md                # 版本演进
├── LICENSE                     # MIT
├── .env.sample                 # 环境变量模板
├── SKILL.md                    # ⭐ 协调器主智能体（调度 9 sub-agent）
├── install.sh / uninstall.sh   # 一键安装 / 卸载
│
├── agents/                     # 9 个 sub-agent 定义
│   ├── data-collector.md           # Phase 1 数据采集
│   ├── phase3-part1.md             # 写手：§一 执行摘要（链尾汇总，决策结论照抄 §七）
│   ├── phase3-part2.md             # 写手：§二 基本面 / §三 行业
│   ├── phase3-part3.md             # 写手：§四 评分+4.11状态 / §五 估值赔率
│   ├── phase3-part4.md             # 写手：§六 风险红旗+6.4左尾 / §七 投资决策内核
│   ├── phase3-part5.md             # 写手：§八 舆情 / §九 来源缺口
│   ├── reviewer-narrative.md       # 评审：叙事 / 证据
│   ├── reviewer-valuation.md       # 评审：估值 / 数学
│   └── reviewer-redflag.md         # 评审：红旗 / 风险
│
├── phases/                     # 阶段执行指令（sub-agent 内部参考）
│   ├── phase1-data-collection.md
│   ├── phase2-document-analysis.md
│   ├── phase3-analysis-report.md
│   ├── phase6-review-publish.md
│   └── phase7-quantitative-monitor.md
│
├── references/                 # 参考文档
│   ├── agent-protocol.md           # ⭐ Agent 调度协议 + Fresh-Restart
│   ├── phase-orchestration.md      # ⭐ 每 Phase 详细 checklist
│   ├── scoring-rubric.md           # 10 维度事实评分标尺
│   ├── qualitative-frameworks.md   # 3 定性框架（护城河/管理层/催化剂）
│   ├── valuation-frameworks.md     # Damodaran 估值 + v7.0 P=F+N/反向DCF/叙事SOTP
│   ├── investment-decision-core.md # ⭐ v7.0 投资决策内核全机制（状态后验×赔率×路径）
│   ├── search-strategy.md          # WebSearch 辅助规范
│   └── html-template-guide.md      # HTML 可视化规范
│
├── assets/
│   ├── templates/
│   │   ├── report-skeleton.md      # ⭐ 9 章节严格骨架
│   │   └── exec-summary-schema.md  # 执行摘要字段定义
│   ├── html/                       # base.html / styles.css / components.html
│   └── validation/                 # report-checklist.json / insight-card-schema.json
│
└── scripts/                    # ⭐ Python 数据层
    ├── config.py               # Token / 缓存 / 速率
    ├── check_env.py            # 环境自检
    ├── data_cache.py           # Parquet 缓存
    ├── tushare_collector.py    # A 股 Tushare Pro
    ├── us_collector.py         # 美股 yfinance
    ├── hk_collector.py         # 港股混合
    ├── legacy_quote.py         # 行情兜底
    ├── pdf_reader.py           # 财报 PDF 段落精析
    ├── data_snapshot.py        # ⭐ 9 节确定性数据
    ├── derived_metrics.py      # CAGR / FCF / ROIC / Owner Earnings
    ├── peer_collector.py       # 同行业对标采集
    ├── capital_flow.py         # 资金流 / 筹码 / 北向 / 大宗
    ├── technical_analysis.py   # 技术面位置
    ├── financial_audit.py      # ⭐ 11 大师框架红旗审计
    ├── assemble_report.py      # ⭐ Phase 3 拼接成 9 章节
    ├── anti_lazy_lint.py       # ⭐ Phase 6 Part A 4 条机械规则
    ├── review_loop.py          # ⭐ reviewer FIX 合并 + 对抗检测
    ├── build_html.py           # HTML 渲染
    ├── update_index.py         # 主页索引联动
    ├── lessons_manager.py      # 全局经验库
    ├── report_parser.py        # 解析历史报告（monitor 用）
    ├── monitor.py              # ⭐ 量化监控核心
    ├── requirements.txt
    ├── README.md
    └── tests/                  # pytest 单测
```

---

## 快速开始

> **跨平台**：Mac/Linux 与 Windows 都可用。Windows 上 Python 解释器用 `py -3`(`python` 可能是 Microsoft Store 占位符), skill 内部会自动探测 `{PYBIN}`。

### 1. 安装 skill

**Mac / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/install.sh | bash
```
**Windows (PowerShell, 在克隆的仓库根目录里):**
```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```
装到 `~/.claude/skills/company-analysis/` + 9 个 sub-agent 到 `~/.claude/agents/company-analysis/`。

### 2. 安装 Python 依赖

依赖：`tushare yfinance pypdf pandas pyarrow requests markdown`
- **Mac / Linux:** `pip3 install --user -r ~/.claude/skills/company-analysis/scripts/requirements.txt`
- **Windows:** `py -3 -m pip install --user tushare yfinance pypdf pandas pyarrow requests markdown`

### 3. 配置 Tushare Token（A 股 / 港股必需）

注册 [tushare.pro](https://tushare.pro/register)，获取 token（建议申请学生权限获 5000+ 免费积分；或购买 2000 积分约 ¥200 解锁所有核心财报接口）。

- **Mac / Linux:** `echo 'export TUSHARE_TOKEN="your_token_here"' >> ~/.zshrc && source ~/.zshrc`
- **Windows (PowerShell):** `[Environment]::SetEnvironmentVariable('TUSHARE_TOKEN','your_token_here','User')`(重开终端生效)

> ⚠️ **千万别把 token 提交到 git**。[`.env.sample`](./.env.sample) 是模板；token 走环境变量(不在仓库内)。

### 4. 环境自检

cd 到 skill 根目录(`~/.claude/skills/company-analysis`)后:
- **Mac / Linux:** `python3 -m scripts.check_env`
- **Windows:** `py -3 -m scripts.check_env`

全部 `[OK]` + `TUSHARE_TOKEN set` → 可用。

### 5. 启动分析

在 Claude Code 对话里：

```
/company-analysis 实丰文化 002862
```

或只给公司名（让它自动定位代码）：

```
/company-analysis 贵州茅台
```

量化监控（基于历史基线报告）：

```
/company-analysis 实丰文化 --monitor
```

---

## 与 Inves-Report 仓库的关系

本仓库（`claude-company-analysis`）是 **skill 代码**。

生成的 **分析报告 HTML** 发布在姊妹仓库 [leafpaper/Inves-Report](https://github.com/leafpaper/Inves-Report)，经 GitHub Pages 在线浏览：

👉 **在线报告**: [leafpaper.github.io/Inves-Report](https://leafpaper.github.io/Inves-Report)

Phase 6 自动把 HTML 推到 Inves-Report 仓库。

---

## 版本演进（详见 [CHANGELOG.md](./CHANGELOG.md)）

| 版本 | 发布 | 关键变化 |
|------|------|---------|
| **v7.0** | 2026-06-22 | 投资决策内核（贝叶斯之美五篇）: 8→9 章新增 §七 投资决策内核（状态后验×赔率×路径 → 好公司/好下注/好价格三分 + 行动档位）; §五 估值重做（P=F+N/反向DCF/叙事SOTP，DCF 降为交叉验证）; §四 加 4.11 状态评估; §六 加 6.4 左尾防护; anti_lazy_lint +Rule6/7; phase3 写手 4→5 |
| **v6.0** | 2026-06-20 | 13→8 章节精简: 合并"评分总览+详细维度"/"行业+对标"/"估值+回报", 风险红旗集中; phase3 写手 5→4; 清理 Phase4/5 残留 + 删 LEGACY 模板 |
| **v5.1.3** | 2026-05-04 | 删除不存在的 `Agent(resume=...)` API，改 Fresh-Restart with Context Injection + `review_loop.py` |
| **v5.1.1** | 2026-04-30 | SKILL.md 调度规范化 + lessons-learned + reviewer 拆 3 并行 |
| **v4.1** | 2026-04-24 | 激进精简：4→3 定性框架 / 独立文件职责分离 |
| **v4.0** | 2026-04-23 | Python 数据层 + 11 框架审计 + 量化监控 (Phase 7) |
| **v3.2** | 2026-04-19 | 协调器质量门控 + HTML 完整性 |
| **v3.0** | 2026-04-16 | 5 阶段流水线 + 上市公司支持 |

---

## 贡献

欢迎 issue / PR。重点方向：
- 更多大师框架（Graham Net-Net / Lynch PEG / Piotroski G-Score）
- 更多市场（新三板 / 日股 / 欧股）
- 分析师 / 机构持仓数据源
- 量化监控升级（因子模型 + IC 检验）

---

## License

[MIT](./LICENSE)

---

**作者**: [@leafpaper](https://github.com/leafpaper)
**思路借鉴**: [terancejiang/Turtle_investment_framework](https://github.com/terancejiang/Turtle_investment_framework)
