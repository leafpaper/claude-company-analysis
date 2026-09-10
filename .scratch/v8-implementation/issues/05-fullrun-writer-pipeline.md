# 05 — 全量写手管线:四节点写手 + decision-writer + 两波调度

**What to build:** 五个写作 agent 定义(node-quality/state/odds/path 四节点写手 + decision-writer 写⑤怎么办+3-5 句导读),每写手只读链手册+本节点手册,产单文件 md:顶部 fenced YAML verdict 块(过 01 schema)+ 正文 verdict 先行+最硬证据子判定表+必要展开段、章预算自检。依赖图两波调度:质地∥赔率∥路径 并行→状态(体检项引用赔率 verdict)→决策;实现为「按依赖图跑任意节点子集」的通用调度(09 增量复用同一套)。调度文档(SKILL/agent-protocol/phase-orchestration/phases)随之重写;旧 part1-5 写手与 phase7 文件删除。铁律基线:[research/02](../../v8-refactor/research/02-dongshan-walkthrough.md) 与 [research/09](../../v8-refactor/research/09-pipeline-dongshan-trace.md)。

**Blocked by:** 01(YAML 块契约)、02(doc-analyst 产 Phase 2 精析供写手引用)、03(写手手册)

**Status:** done(2026-08-18)

- [x] 东山真实 run:五个节点 md 全部过 schema 校验
- [x] 五节点 verdict 与 research/02 零漂移:部分好/↑变好未确认/买完完美未来+区间锚[57,89]两端同向/高尾险·扛不住/等证据临界+期权小仓≤2-3%,封顶检查=不触发
- [x] 状态写手引用赔率 verdict 不重推;「该等什么」只在状态节点产出;仓位只在决策层发声
- [x] 红旗归家:估值红旗只在赔率节点、写手提名(级别+证据+来源)落所属节点清单
- [x] 调度可按依赖图跑任意节点子集;旧 part1-5/phase7 删除,主 agent 纯调度

---

## 实现记录(2026-08-18)

### 落了什么

**五个写手**(`agents/node-{quality,odds,path,state}.md` + `agents/decision-writer.md`)

| 写手 | 波次 | 必读 | YAML 块特有字段 | 正文预算 |
|---|:--:|---|---|:--:|
| node-quality | 1 | 链手册 + node-quality | `panel`(自选 3-5 指标 + `industry_reason`) | ≤70 |
| node-odds | 1 | 链手册 + node-odds | `anchor_range`(两端 + `same_direction` + 不同向必填 `divergence_note`)、`current_price` | ≤70 |
| node-path | 1 | 链手册 + node-path | `falsifications`(带 `triggered`)、`left_tail` | ≤60 |
| node-state | 2 | 链手册 + node-state + **③赔率 YAML 块** | `critical_point.items`(2-4 条,带时间窗与判据) | ≤60 |
| decision-writer | 3 | 链手册 §2/§3 + **四个 YAML 块**(不读正文、不读节点手册) | `triad`/`action_gear`/`position`/`three_part`/`gear_cap`/`front_page_intro` | ≤50 |

每份都含:必读清单(**手册只此两份**)、执行顺序、文件形状示例(顶部 fenced YAML + verdict 先行正文)、`verdict_block` 自检(≤3 轮自补)+ 四条自查、完成报告格式(`**判定**:` / `**verdict**:` 单独一行)、严禁事项、错误处理表。

**通用调度** `scripts/node_graph.py`:`DEPS` 声明依赖边(state←odds;decision←四节点),`plan_waves(子集)` 做子集内拓扑分层,子集外依赖视为"上版复用块已就位"并记进 `external_deps`(调度开跑前校验)。CLI `--all` / `--nodes a,b,c` / `--json`。09 的增量子集调度直接复用,不再写第二套。

**调度文档**:`SKILL.md`(判断链调度器)、`references/phase-orchestration.md`(v8 目录约定 + 三波 checklist)、`references/agent-protocol.md`(名册/写手完成报告 schema/修正循环落点)、新增 `phases/phase3-node-writing.md`(主 agent 的 Phase 3 细则:波次→prompt 模板→逐波门控→装配)。

**采集侧补齐**(全量 run 跑得通的前提):`financial_audit --json` → `red_flags.json`(写手 `red_flag_ref` 与决策层封顶检查的 id 来源);拆 `sentiment.md` / `data_sources.md`(附录 C/E 挂载源,原本只藏在 phase1-data.md 的 §8/§11 里,装配会告警缺产物)。

**删除**:`agents/phase3-part{1-5}.md`、`phases/phase3-analysis-report.md`、`phases/phase7-quantitative-monitor.md`、`assets/templates/{report-skeleton,exec-summary-schema}.md`、`scripts/assemble_report.py` + 其测试。

### 验收:东山精密 dry-run

只模拟"写手的产出"(LLM 部分用 04 的 golden fixture),其余全走真脚本:`manifest.create_run` → 五个节点 md → `verdict_block` CLI ×5 → `node_graph --all` → `assemble_report_v8`(`--artifacts-dir` 指真实 `~/.claude/output/东山精密`)。

- 五块 schema:`exit=0` ×5
- 波次:第1波 质地∥赔率∥路径 / 第2波 状态 / 第3波 决策 = research/09 §A
- **决断卡五行与 research/02 §6 逐行一致**(零漂移):部分好——真卡位+平庸财务 / ↑变好但未确认,注意力先行 / 买完完美未来;锚区间 57-89 元 vs 现价 273 元 / 高尾险·扛不住,高信仰 5/5 / 先观察等证据临界,期权小仓 ≤2-3%
- Top3 两源同池机器带出(🟠散户暴增+两融拥挤〔提名〕/ 🟠商誉占净资产过高〔脚本〕/ 🟠PB 历史分位〔脚本〕)——与 research/02 §6 的三条风险同集合,排序按 04 已定的机器规则(级别→组内条数→path>odds>quality>state)
- 主页卡片:verdict=行动档位人话、行动档位=等证据临界、质地=部分好;附录 A/B/C 挂上真实采集产物,C/E 提示缺 `sentiment.md`/`data_sources.md`(即本票给 data-collector 补的两份底稿)
- 单测:`test_node_graph.py` 17 项绿;全量 `python -m unittest discover -s scripts/tests -t .` 除既有 3 个缺 pandas 的环境错外全绿

### 与 research/09 的一处偏离(生产者不变)

research/09 §A 把采集产物写成落 `runs/{date}/raw_data/`。实际 collectors(`tushare_collector` / `us_collector` / `hk_collector`)的输出目录由 `config.output_dir(company)` 写死在公司级,改成 run 级要动采集脚本本身(不在本票范围,且 09 的"增量刷新"会重谈这块)。**本票的落点约定**:采集产物落公司级 `output/{company}/`(跨 run 共享,装配用 `--artifacts-dir` 指过去),`runs/{date}/` 只放 `nodes/` + `assembly/` + `reviewer_responses/` + 主报告;run 目录内的 `raw_data/` 保留为增量证据快照的位置。零孤儿映射与"每个组件唯一生产者"不受影响。

### 留给别的票

- **Phase 6**(票 06):v7 的 `anti_lazy_lint` 与 3 个 reviewer 校验的是 9 章节结构,对 v8 报告会误判;已在 SKILL/orchestration 标注"v8 质量环施工中",reviewer agent 定义、`review_loop.py` 的 part 文件签名、`assets/validation/report-checklist.json` 全部留给 06。
- **`--review`**(票 09):`node_graph --nodes` 子集调度、路径节点的证伪核销、装配的 `--prev-run-dir` 变化区块都已就位,triage 与四段链归 09;SKILL 里 `--monitor` 暂为退役提示。
- **交付**(票 07,并行会话):`build_html` / `assets/html` / index 卡片未碰;`install.sh` 与 `CHANGELOG.md` 是共享文件,本次只提交 05 的部分,工作区保留 07 未提交的行。
