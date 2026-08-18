# YEZHI Company Analysis (v7.1)

> **像一个谨慎的投资人那样，把一家公司从头到尾看一遍** —— 结构化财报数据 + 年报/季报 PDF 原文 + 11 大师框架自动审计 + 一张看得懂的「投资决断卡」，**全程说人话**。
>
> 支持 A 股 / 美股 / 港股 · 跑在 Anthropic Claude Code 里的 `/company-analysis` 命令 · 帮你**一眼筛好公司**，并把"是不是好公司"和"现在该不该买"分开回答

<p align="center">
  <img src="https://img.shields.io/badge/version-v7.1-blue" alt="version">
  <img src="https://img.shields.io/badge/markets-A%E8%82%A1%20%7C%20%E7%BE%8E%E8%82%A1%20%7C%20%E6%B8%AF%E8%82%A1-green" alt="markets">
  <img src="https://img.shields.io/badge/audit-11%20frameworks-orange" alt="frameworks">
  <img src="https://img.shields.io/badge/report-9%20chapters-purple" alt="chapters">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="license">
</p>

**在线报告示例**: [leafpaper.github.io/Inves-Report](https://leafpaper.github.io/Inves-Report)

---

## 这是什么

一个跑在 Claude Code 里的 slash command（`/company-analysis`）。给它一个公司名（可选股票代码），它会自动采集结构化财报数据、强制精读年报/季报 PDF 原文、跑 11 个大师级会计审计框架，然后用**判断链五个节点写手**（质地 / 状态 / 赔率 / 路径 / 怎么办，依赖图两波调度）各写一章，首页决断卡与附录全部机器装配，再经质量环评审 + 修正循环，最后渲染 HTML 并发布到 GitHub Pages。

核心定位：**用确定性数据 + 数学推导对抗"伪量化"和"AI 编故事"，再用大白话讲给你听**。所有关键数字带来源标签（`[Tushare:income.revenue]` / `[PDF:q3_2025, P.4]`），估值走 P=F+N 分解 + 反向DCF + 叙事SOTP（DCF 概率加权作交叉验证），决策走"状态后验×赔率×路径"三分（好公司/好下注/好价格），所有红旗由脚本机械扫出。最后落到一张 **5 行的「投资决断卡」**——把"是不是好公司"和"现在该不该买"分开回答。

---

## 我们的投资理念（大白话）

> 一句话：**先弄清"是不是一家好公司"，再决定"现在这个价格该不该买"——这是两件事，绝不能混。**

判断一家公司值不值得投，我们就问六个问题，全用人话回答：

1. **它在变好吗？变好被证据坐实了没？**（状态）
   不听故事、看实锤——财报有没有改善、订单 / 客户 / 产能是不是真的，还是只是"小作文 + 喊单"。**分清「实锤」和「传闻」**，传闻一律打折。

2. **现在的价格，是不是已经把未来所有好事都提前买走了？**（赔率）
   把股价拆成两块：**已经赚到的** + **对未来的想象**。想象占比越大，越要它后面真兑现，否则就是"故事变成了必须完成的任务，做不到就杀估值"。看现在还有没有**安全垫**。

3. **就算方向对，兑现之前你扛得住中途大跌吗？**（路径）
   方向对、但中途腰斩你拿不住，照样亏。所以先看**最坏会怎样**（左尾风险），再决定下不下注、下多重。

   > 这三关——**变好了吗 × 贵不贵 × 扛得住吗**——有任何一个"差"，现在就不是好下注。

4. **四个维度都要懂：懂财报、懂叙事、懂估值、懂热点。**（借鉴"喊单"四关）
   只懂财报会错过成长，只追热点会接盘。四个都过关，才敢说看懂了这家公司。

5. **机器扫雷，不靠感觉。**
   11 个会计审计框架（Piotroski 健康度 / Beneish 造假 / Altman 破产 / 应计粉饰 / 关联方…）自动扫财务地雷，扫出的红旗必须在报告里闭环出现、不许藏着掖着。

6. **最后给你一张「投资决断卡」。**
   5 行看懂结论：① 是不是好公司 ② 故事真不真 ③ 贵不贵 ④ 该不该买 ⑤ 该怎么办（具体动作 + 该等什么事件）。**好公司 ≠ 现在能买**，卡片把这两件事分开告诉你。

> 这套方法的内核来自「贝叶斯之美」五篇（《投资是泊松过程》《喊线时代》《三大数学模型之美》《信仰投资最大陷阱》《十年十倍股》）。框架只是**内部思考引擎**，报告**输出**永远是大白话 + 具体证据 + 一句结论。完整机制见 [`references/judgment-chain.md`](./references/judgment-chain.md) 与四份节点手册。

---

## 设计原则

| 原则 | 含义 |
|------|------|
| **强制 PDF 精读** | 不依赖第三方摘要。年报/季报 PDF 必须下载并提取关键段落（利润表变动原因 / 子公司业绩 / MD&A / 风险因素 / 非经常损益 等），关键结论带 `[PDF:报告期, P.x]` 引用。 |
| **数学推导优先** | 估值赔率走 **P=F+N 分解 + 反向DCF 隐含预期 + 叙事分部SOTP**（v7.0），DCF 概率加权作 F 的交叉验证；逻辑猜测不得替代算术，每块须出数字。 |
| **决策内核（v7.0）** | 投资价值 = **状态后验 × 赔率 × 路径可承受性**，把"是不是好公司"拆成 **好公司 / 好下注 / 好价格** 三分 + 行动档位（六档）。源自"贝叶斯之美"五篇，定义见 `references/judgment-chain.md`（v8 手册层）。 |
| **全说人话（v7.1）** | 框架是内部思考引擎，**报告正文不出现裸术语**（λ / P=F+N / embedded obligation 等只在小括号里标注）。每段结论先行，§一/§五/§七 正文无来源标签（机械拦截，来源统一 §九）。落到一张 **5 行投资决断卡**：是不是好公司 / 故事真不真 / 贵不贵 / 该不该买 / 该怎么办。 |
| **11 框架防盲点** | `scripts/financial_audit.py` 自动跑 Piotroski F / Beneish M / Altman Z / DuPont / Sloan 应计 / 治理 / 关联方等 11 个框架，机械扫出红旗，进入 §六。 |
| **黑白分割不骑墙** | 子判定只有 ✓ / ⚠️ / ✗ 三态，verdict 只能取本节点的取值域；**禁止任何隐性打分**（分数、权重、修正系数、综合评级）——v8.0 已删除全部评分机制。 |
| **缺口必闭环** | 附录E 信息缺口强制 ≥ 3 条，每条记录已尝试的查询路径；补查成功必须反写到所有相关章节。 |
| **一处权威（v8.0）** | 同一个问题全报告只答一次："贵不贵"只在③、"该等什么"只在②、仓位与行动档位只在⑤、每条红旗只在其归属节点叙述一次（总清单在附录D，Top3 机器带出）。10 维评分 / 定性综合方向 / 快筛章节等"结论假面"已删除。 |
| **首页零人工抄写（v8.0）** | 决断卡五行 / 赚钱面板 / Top3 风险 / 主页 metadata 全部由 `assemble_report_v8` 从五个节点的 YAML verdict 块装配，人工只写 3-5 句导读。 |

---

## 流水线（判断链两波 + 装配）

```
Step 0-2：环境自检 + 输入确认 + 建 run 目录（runs/{date}/ + manifest.json）
   ↓
Phase 1 数据采集   （data-collector：Tushare + yfinance + 港股 + PDF 下载解析 + 11 框架 audit
                    → red_flags.json（带 id 的红旗清单）+ peer / capital_flow / technical 快照）
   ↓
Phase 2 文档精析   （doc-analyst：精读 PDF 关键段落，提取原文引用 + 自跑 check_phase2 门控）
   ↓
Phase 3 判断链写作 （依赖图两波，波次由 scripts/node_graph.py 算）
     第一波（并行）  node-quality ∥ node-odds ∥ node-path
     第二波          node-state（四层验证第④关引用③赔率 verdict）
     第三波          decision-writer（三元组 → 行动档位 + 封顶检查 + 首页导读）
     装配            assemble_report_v8：首页（决断卡/面板/Top3）+ 五章 + 附录A-E
   ↓
Phase 6 质量环与发布（v8 lint + reviewer 并行 + 修正循环 + build_html + GitHub Pages）
```

> 每波结束由主 agent 复核 `verdict_block` schema 门控，过了才进下一波；写手只读「链手册 + 自己那份节点手册」，跨节点只引用对方 verdict。完整调度协议 / 质量门控 / 异常处理见 [SKILL.md](./SKILL.md) + [references/phase-orchestration.md](./references/phase-orchestration.md) + [phases/phase3-node-writing.md](./phases/phase3-node-writing.md)。

**sub-agent**：`data-collector`（1）+ `doc-analyst`（1）+ **判断链四节点写手** `node-{quality,state,odds,path}`（4）+ `decision-writer`（1）+ 质量环 reviewer。全量与增量复查共用同一套「按依赖图跑任意节点子集」的调度。

---

## 报告结构（判断链本身）

章节 = 判断链：结论先行、每章 verdict 块 + 最硬证据、完整表格全部下沉附录。规则真理源：[`references/judgment-chain.md`](./references/judgment-chain.md)。

| 章节 | 内容 | 谁产 |
|------|------|------|
| **首页 一眼结论** | 决断卡五行（是不是好公司 / 在变好吗 / 贵不贵 / 扛得住吗 / 怎么办）+ 赚不赚钱面板（3-5 指标 + 红标）+ Top3 风险 + 3-5 句导读 | 机器装配（导读来自 decision-writer） |
| **① 质地 是不是好公司** | 五个子判定（生意模式赚钱吗 / 赚钱质量真吗 / 护城河存在吗 / 管理层可信吗 / 财务底子稳吗）✓⚠️✗ + 面板自选指标 | node-quality |
| **② 状态 在变好吗** | λ 载体与分部稀释 / 实锤 vs 传闻分级 / 身份切换 P1→P4 / 四层验证 / **临界点（该等什么，全链唯一）** | node-state |
| **③ 赔率 贵不贵** | P=F+N 分解 + 反向 DCF 隐含预期 + 叙事分部 SOTP + **区间锚 [SOTP, DCF] 与两端同向标记**；估值类红旗归家 | node-odds |
| **④ 路径 扛得住吗** | 左尾清单（含剩余资产清单）+ 高信仰股体检 + 回报路径成本 + **证伪/退出清单（全链权威）** | node-path |
| **⑤ 怎么办** | 三元组[状态\|赔率\|路径] → 六档行动档位 + **封顶规则**（致命红旗 → 强制回避）+ 仓位（唯一出处）+ 三分结论 + 该等什么/证伪退出（引用②④） | decision-writer |
| **附录 A-E** | A 财务与经营明细 / B 行业与对标明细 / C 舆情与资金底稿 / **D 红旗总清单（脚本 audit ⊕ 写手提名机器合并）** / E 数据来源与信息缺口 | 零写手，全脚本装配 |

---

## 单次分析产出

```
output/{公司名}/
├── manifest.json                  # ⭐ 公司级状态唯一源（runs 列表 / 增量计数 / 上次全量 / 预约披露日 / 对比组）
├── raw_data/
│   ├── *.parquet                  # Tushare / yfinance 结构化数据
│   ├── pdfs/*.pdf                 # 下载的财报 PDF
│   └── pdf_sections_*.json        # PDF 关键段落抽取
├── data_snapshot.md               # 9 节确定性数据（含限售解禁日历）
├── audit_report.md / .json        # ⭐ 11 框架红旗清单（json 供机器读）
├── red_flags.json                 # ⭐ 红旗清单（稳定 id；写手引用 + 附录D 脚本源）
├── peer_analysis.md               # 同行业对标
├── capital_flow.md                # 资金流 / 筹码 / 北向 / 大宗
├── technical_analysis.md          # 技术面位置
├── phase1-data.md                 # 数据采集总结
├── sentiment.md / data_sources.md # 附录C / 附录E 底稿
├── phase2-documents.md            # 文档精析
└── runs/{date}/                   # ⭐ 每次 run 一个目录（旧 run 整目录即留档）
    ├── nodes/node-{quality,state,odds,path,decision}.md   # 五个判断节点（顶部 YAML verdict 块）
    ├── assembly/assembly.json     # 装配产物（决断卡/面板/Top3/metadata/变化区块）
    ├── reviewer_responses/        # 质量环往返
    ├── {公司}-analysis-{date}.md  # ⭐ 主报告（首页 + 五章 + 附录A-E）
    └── {date}.html                # ⭐ HTML 可视化
```

---

## 仓库结构

```
claude-company-analysis/
├── README.md                   # 本文件
├── CHANGELOG.md                # 版本演进
├── LICENSE                     # MIT
├── .env.sample                 # 环境变量模板
├── SKILL.md                    # ⭐ 协调器主智能体（判断链调度）
├── install.sh / uninstall.sh   # 一键安装 / 卸载
│
├── agents/                     # sub-agent 定义
│   ├── data-collector.md           # Phase 1 数据采集
│   ├── doc-analyst.md              # Phase 2 文档精析（PDF 精读 + check_phase2 自门控）
│   ├── node-quality.md             # 写手：①质地 是不是好公司（+ 赚钱面板选指标）
│   ├── node-odds.md                # 写手：③赔率 贵不贵（+ 区间锚两端同向）
│   ├── node-path.md                # 写手：④路径 扛得住吗（+ 左尾/证伪清单）
│   ├── node-state.md               # 写手：②状态 在变好吗（+ 临界点=该等什么，第二波）
│   ├── decision-writer.md          # 写手：⑤怎么办（三元组→档位+封顶+仓位）+ 首页导读
│   └── reviewer-*.md               # 质量环评审（v8 质量环重写中）
│
├── phases/                     # 阶段执行指令
│   ├── phase1-data-collection.md   # data-collector 内部读
│   ├── phase2-document-analysis.md # doc-analyst 内部读
│   ├── phase3-node-writing.md      # ⭐ 主 agent 读：波次 / prompt 模板 / 逐波验收 / 装配
│   └── phase6-review-publish.md    # 质量环与发布
│
├── references/                 # 参考文档
│   ├── agent-protocol.md           # ⭐ Agent 调度协议 + Fresh-Restart
│   ├── phase-orchestration.md      # ⭐ 每 Phase 详细 checklist
│   ├── judgment-chain.md           # ⭐ v8 判断链手册（四问定义/决策层/装配规则/写作规范）
│   ├── node-quality.md             # ①质地证据手册（五子判定 + 赚钱面板菜单）
│   ├── node-state.md               # ②状态证据手册（λ/实锤分级/身份切换/临界点）
│   ├── node-odds.md                # ③赔率证据手册（P=F+N/反向DCF/叙事SOTP/区间锚）
│   ├── node-path.md                # ④路径证据手册（左尾清单/高信仰体检/证伪清单）
│   ├── search-strategy.md          # WebSearch 辅助规范
│   └── html-template-guide.md      # HTML 可视化规范
│
├── assets/
│   ├── html/                       # base.html / styles.css / components.html
│   └── validation/                 # report-checklist.json
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
    ├── init_run.py             # 建 run 目录 + manifest 登记
    ├── manifest.py             # 公司级状态（runs / 增量计数 / 披露日 / 对比组）
    ├── verdict_block.py        # ⭐ 节点 YAML 块抽取 + schema 校验（波次门控）
    ├── node_graph.py           # ⭐ 判断链依赖图：任意节点子集 → 执行波次
    ├── red_flags.py            # ⭐ 红旗两源合并 / Top3 / 红标反查
    ├── assembly.py             # ⭐ 摘要层装配（决断卡/面板/Top3/变化区块）
    ├── assemble_report_v8.py   # ⭐ 报告总装（首页 + 五章 + 附录A-E）
    ├── schemas/                # 契约层 JSON Schema（节点×5 + assembly + manifest + common）
    ├── anti_lazy_lint.py       # ⭐ 质量环机械规则
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
装到 `~/.claude/skills/company-analysis/` + sub-agent 到 `~/.claude/agents/company-analysis/`。

### 2. 安装 Python 依赖

依赖：`tushare yfinance pypdf pandas pyarrow requests markdown pyyaml jsonschema`
- **Mac / Linux:** `pip3 install --user -r ~/.claude/skills/company-analysis/scripts/requirements.txt`
- **Windows:** `py -3 -m pip install --user tushare yfinance pypdf pandas pyarrow requests markdown pyyaml jsonschema`

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

> v7 的 `--monitor` 量化监控已随 v8.0 退役；增量复查 `--review`（分层重评 + 首页「较上版变化」）在 v8 后续版本提供。

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
| **v8.0** | 施工中 | 判断链收敛: 9 章节 → 首页一眼结论 + 五章（①质地/②状态/③赔率/④路径/⑤怎么办）+ 附录A-E; 一处权威（删 10 维评分/定性综合方向/快筛章节/§七 7.1-7.3/§一人工抄本）; 5 个 part 写手 → 四节点写手 + decision-writer，依赖图两波调度; 首页与附录机器装配（YAML verdict 块为唯一数据源）; 框架文档 4 份 → 链手册 1 + 节点手册 4; runs/{date}/ + manifest 状态制 |
| **v7.1** | 2026-06-23 | 可读性重写（全说人话）: 框架退为内部思考引擎，正文大白话 + 证据 + **5 行投资决断卡**（分开"是不是好公司"与"现在该不该买"）+ §四 四维体检（懂财报/叙事/估值/热点）+ 实锤/传闻表; §七 短合成（7.1-7.3 一句话+详见，重心压到 7.4 决策）; "谁在买"统一归 §八; anti_lazy_lint Rule5 = §一/§五/§七 正文无来源标签; 项目更名 **YEZHI Company Analysis** |
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
