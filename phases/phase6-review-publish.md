# Phase 6: 质量环与发布 (v8.0 — 机器门控 + 两 reviewer 并行 + 出片发布)

> **谁读这份**:**主 agent**。本文件讲「怎么把装配好的报告验收、修正、出片、发布」,不讲报告怎么写。
>
> **🧭 你在这里**:[SKILL.md 协调器](../SKILL.md) → [Phase 3 判断链写作与装配](phase3-node-writing.md) → **Phase 6 质量环与发布**(终点)
>
> **接收自**:`{run_dir}/nodes/node-*.md`(五块)+ `{run_dir}/assembly/assembly.json` + `{run_dir}/{company}-analysis-{date}.md`
> **输出**:`*.html` + `{run_dir}/phase6-review-log.md` + GitHub Pages(leafpaper/Inves-Report)
> **质量环规模**:机器门控 10 条(`lint_v8`)+ 2 个 LLM reviewer 并行 + fresh-restart 修正循环(3 轮上限)
>
> **v7 → v8 变了什么**:9 章节骨架比对 / 章节字数下限 / artifact 覆盖率 / 20 项 LLM 清单 / 3 个 reviewer
> 全部删除——它们校验的是「四套机制互抄一致」和「写够字数」,v8 把复述层删了、把长度改成上限,
> 那套校验对 v8 报告只会误判。取而代之:机器查结构性质(`scripts/lint_v8.py`),LLM 查判断链逻辑与可读性。

---

## 角色定义

你有两个身份:

**身份 A — 质量环调度员**:跑机器门控、派两个 reviewer、按 FIX 分诊结果决定「重启写手」还是「自己改措辞」。
你**不改判断**——YAML 块永远只有写手能动。

**身份 B — 发布经理**:把过关的报告出成 v8 仪表盘 HTML,推到 GitHub Pages,更新主页卡片。

---

## 前置条件

| 项 | 检查 |
|---|---|
| 五个节点块 | `{run_dir}/nodes/node-{quality,state,odds,path,decision}.md`,Phase 3 逐波 `verdict_block` 已过 |
| 装配产物 | `{run_dir}/assembly/assembly.json` + `{run_dir}/{company}-analysis-{date}.md`(`assemble_report_v8` 退出 0) |
| 采集产物 | `{artifacts_dir}/audit_report.json`(红旗闭环要它)+ 附录 A/B/C/E 的挂载源 |
| 往返目录 | `{run_dir}/reviewer_responses/`(`init_run` 已建) |

---

## Part A: 质量环

### Step 0(强制门控):机器规则 — 任一 fail 直接 BLOCK

```
{PYBIN} -m scripts.lint_v8 --run-dir {run_dir} --artifacts-dir {artifacts_dir}
# 退出码 0 = fail 项全过(warn 不阻断)→ 进 Step 1
# 退出码 1 = BLOCK,按 FAIL 项修完再来,不许让 reviewer「绕过」机器规则
# 退出码 2 = run 目录不完整(缺 nodes/),回 Phase 3
```

**为什么先跑它**:LLM 自审看不见自己的结构性错误(写者=审者)。确定性的 schema 校验 + 重算比对 + grep
能挡住的,不该花 LLM 的注意力。

| # | 规则 | 级别 | 判什么 |
|:-:|---|:--:|---|
| R1 | 五块 schema 校验 | fail | 五个节点 YAML 块逐块过 `scripts/schemas/` |
| R2 | 红旗闭环 | fail | Top3 与红旗清单**重算一致**(装配没重跑也在这里现形);🔴 致命红旗必须在归属节点叙述过 |
| R3 | 数字唯一 home | fail | 同一数字跨章出现时,异地那处必须带出处引用(①-⑤ / 附录A-E) |
| R4 | 章预算 | warn | 70/60/70/60/50 行上限 + 主体合计 400 行(**没有下限**——下沉附录是规定动作) |
| R5 | 区间锚 | fail | 同向标记必填、不同向必写分歧原因、两端不倒置、verdict 与现价方向不自相矛盾 |
| R6 | 外链引用 | fail | 正文禁「详见 xxx.md」「[x](x.md)」(指向本报告附录的 `#锚点` 合法) |
| R7 | 决策字段 + 封顶 | fail | 决策块九个必填字段;**有 🔴 → 行动档位强制「回避」且 `gear_cap.triggered=true`** |
| R8 | 越权发声 | fail | 仓位 / 行动档位 / 买卖建议只能出现在⑤(写明「归⑤/见⑤」的引用行豁免) |
| R9 | 无记忆性反例 | fail | 禁「跌久了该涨 / 估值压久了该修复」当买入理由 |
| R10 | 报告与节点同步 | fail | 主报告五章正文 = 节点 md 正文(改完没重装配 = 脱节) |
| R2w | 🟠 高级红旗归家 | warn | 🟠 未在归属节点叙述——提示补一句,不阻断 |

**修复指引**:

| 症状 | 怎么修 |
|---|---|
| R1 / R2(🔴 未归家)/ R5 / R7 | **判断问题** → fresh-restart 对应写手(prompt 注入 lint 报错原文);主 agent 不许手改 YAML 块 |
| R2(Top3 漂移 / 清单不一致)/ R10 | 重跑 `assemble_report_v8`——十有八九是改了节点却忘了重装配 |
| R3 / R6 / R8 / R9 | 多半是措辞 → 主 agent 用 Edit 改**节点 md 正文**,改完重跑装配 |
| R4 warn | 看能不能把表格/时序下沉附录;下沉不了就留着,不阻断 |

### Step 1: 两个 reviewer 并行

```python
Agent(subagent_type="reviewer-logic", run_in_background=True, description="维度1 判断链逻辑",
      prompt=f"""评审判断链逻辑(第 {round} 轮)。
run_dir     = {run_dir}
artifacts_dir = {artifacts_dir}
report_path = {run_dir}/{company}-analysis-{date}.md
lint_v8 已全绿(schema/红旗闭环/数字home/区间锚/封顶/越权/外链/同步都查过了),别重复机器规则。
按 agents/reviewer-logic.md 的 5 项检查出判定与 FIX,响应只回评审结论,不要回放文件内容。""")

Agent(subagent_type="reviewer-delivery", run_in_background=True, description="维度2 可读性与交付",
      prompt=f"""评审可读性与交付(第 {round} 轮)。run_dir / artifacts_dir / report_path 同上;
html_path = {run_dir}/{company}-analysis-{date}.html
按 agents/reviewer-delivery.md 的三组检查(结论先行 / 全说人话 / 390px 走查清单)出判定与 FIX。""")
```

两个都 `run_in_background=True`,等系统的 task-notification 收齐两份响应。
**Round 1 的 HTML**:Part B 的出片脚本自带 lint 门控,可以先跑一次 `build_html` 给 reviewer-delivery 看
(出片不等于发布);也可以让它只审 md,第一轮 FIX 修完再出片——两种都行,但 prompt 里要说清 `html_path` 有没有。

**收到响应后**:两份原文 Write 到

```
{run_dir}/reviewer_responses/round_{N}_logic.md
{run_dir}/reviewer_responses/round_{N}_delivery.md
```

(不依赖 context 记忆——修正循环是 fresh-restart,状态只能落文件。)

### Step 2: 合并判定 + FIX 分诊

```
{PYBIN} -m scripts.review_loop --run-dir {run_dir} --round {N}
```

输出 JSON(主 agent **只看这个**,不读 reviewer 响应全文):

```json
{
  "overall_pass": false,
  "judgments": {"logic": "FAIL", "delivery": "FAIL"},
  "fix_count": 4,
  "fix_by_node": {"odds": 1, "state": 2, "delivery": 1},
  "fix_by_kind": {"判断": 2, "表述": 2},
  "restart_writers": ["node-odds", "decision-writer"],
  "edit_targets": ["nodes/node-state.md"],
  "delivery_fixes": 1,
  "fix_list_path": "…/round_1_merged_fix.md",
  "diff_repeat": false
}
```

| JSON | 主 agent 的动作 |
|---|---|
| `overall_pass: true` | → Part B 出片 |
| `diff_repeat: true` | → **转人工**(两轮之间节点 md 一个字没变 = 改回原状的对抗) |
| `round == 3` 仍 FAIL | → **转人工**,附累计 FIX |
| 否则 | → Step 3 应用 FIX,Round+1 |

### Step 3: 修正循环(fresh-restart,3 轮上限)

1. **判断类 FIX**(`restart_writers` 非空)→ 用 Agent 重启对应写手,prompt 注入:任务描述 + `{run_dir}`/`{artifacts_dir}` +
   本轮 FIX 原文 + 「这是重跑,只看当前文件状态」。**主 agent 不改 YAML 块**。
2. **表述类 FIX**(`edit_targets` 非空)→ 主 agent 用 Edit 改对应节点 md 的**正文**(不碰顶部 YAML 块)。
3. **交付类 FIX**(`delivery_fixes > 0`)→ 改 `assets/html/report-v8.{html,css}` 或渲染逻辑,不惊动写手。
4. **重跑两条命令,缺一不可**:

   ```
   {PYBIN} -m scripts.assemble_report_v8 --run-dir {run_dir} --company {company} --date {date} \
       --ticker {ticker} --artifacts-dir {artifacts_dir}
   {PYBIN} -m scripts.lint_v8 --run-dir {run_dir} --artifacts-dir {artifacts_dir}
   ```

5. Round+1:重新并行启动两个 reviewer(fresh-restart,prompt 注明「上轮 FIX 已应用」)。

每轮写一行 `main-log.md`:`- {ts} reviewer Round N 综合判定 <PASS/FAIL>,FIX 数 M`。

---

## Part B: HTML 出片

```
{PYBIN} -m scripts.build_html --company {company} --run-dir {run_dir}
```

脚本会:**先跑一次 `lint_v8`(fail 阻断)** → 读 `assembly/assembly.json`(结构化件)+ 主报告 md(正文)→
按 `assets/html/report-v8.{html,css}` 渲染 B 仪表盘版式 → 红标三通道与附录D 反查 → 成品自检
(决断卡五行 / Top3 / 面板指标 / 五章 / 附录一个都不能少)。

退出码 0 = 出片成功;2 = 自检未命中(stderr 列出缺了什么);1 = lint 未过或渲染失败。

**绝对禁止**:手写 HTML、凭记忆重写 CSS、自创组件 class。模板是唯一真相源,
版式规范见 `references/html-template-guide.md`。

---

## Part C: GitHub Pages 发布(主页动态联动)

**目标仓库**:`leafpaper/Inves-Report`。`$INVES_REPORT_DIR` 为环境变量(Mac/Linux 如 `/tmp/Inves-Report`,
Windows 如 `C:\Inves-Report`);下面写法为 Mac/Linux,Windows 把 `mkdir -p`→`New-Item -ItemType Directory -Force`、
`cp`→`Copy-Item`、`$INVES_REPORT_DIR`→`$env:INVES_REPORT_DIR`,`cd` / `git` 两边通用。

```
1. cd $INVES_REPORT_DIR && git pull origin main       # 不存在则先 git clone

2. mkdir -p $INVES_REPORT_DIR/reports/{CompanySlug}_{CompanyNameCN}

3. cp {run_dir}/{company}-analysis-{date}.html \
      $INVES_REPORT_DIR/reports/{CompanySlug}_{CompanyNameCN}/分析报告_dashboard.html

4. {PYBIN} -m scripts.update_index --company {company} --repo $INVES_REPORT_DIR --force
   # 解析主报告的 CARD_METADATA + assembly.json → card-metadata.json → upsert data/reports.json
   # v8 卡片字段:verdict = 行动档位人话 / quality = 质地字段 / action_gear / next_disclosure_date

5. cd $INVES_REPORT_DIR
   git add reports/{CompanySlug}_{CompanyNameCN}/ data/reports.json
   git commit -m "feat: 新增/更新 {company} 投资分析报告"
   git push origin main
```

**失败处理**:push 失败 → 保存 HTML 到本地并通知用户手动上传(不重试超过一次)。

---

## Part D: 信息缺口补查(触发式)

**触发**:附录E(`data_sources.md`)里有 ⚠️/❌ 状态的缺口,**或**某个写手的完成报告带了「降级标注」
(缺什么、什么事件能补上)。没有触发条件就跳过本 Part。

**5 步补查**(对每条缺口依次执行,找到即停,但每步都要登记):

| 步 | 动作 | 为什么在这个位置 |
|:-:|---|---|
| D.1 | WebFetch 巨潮资讯公告索引,按关键词过滤后取 PDF | 缺口多半来自没读的临时公告,巨潮覆盖最广、时效最高 |
| D.2 | WebFetch 公司官网 IR / 投资者关系页 | 官方口径,二手转述之上 |
| D.3 | `{PYBIN} -m scripts.pdf_reader {pdf} --search "{关键词正则}"` | 已下载 PDF 的全文命中 |
| D.4 | WebSearch `site:cninfo.com.cn` / `site:sse.com.cn` / `site:sec.gov` + 关键词 | 事件性信息 |
| D.5 | Tushare 结构化接口(`fina_mainbz` / `stk_rewards` / `stk_managers` / `top10_holders` / `forecast_vip` …) | 结构化兜底,对事件性信息覆盖差,放最后 |

**判定分档**:✅ 直接回答了缺口 / ⚠️ 只找到相关上下文或代理指标 / ❌ 空手 / ⏭️ 明确不适用。
整体状态:至少 1 步 ✅ 且交叉验证 = **已解决**;有 ⚠️ 其余 ❌ = **部分解决**(必须写「还需要什么数据才能升级」);
全 ❌/⏭️ = **未找到**(必须写「信息可得性:低 / 原则上不可得」+ 原因)。

**★ 补到的数据往哪写(v8 落点)**:

| 补到的是什么 | 落点 |
|---|---|
| 改变某个子判定的证据 | **fresh-restart 对应节点写手**(判断变了,主 agent 不代笔) |
| 只是补充明细 / 时序 / 表格 | 采集产物(`data_snapshot.md` 等)→ 重跑装配,自动进附录 |
| 缺口状态本身 | `data_sources.md`(附录E 的挂载源)→ 重跑装配 |

补完一律重跑 `assemble_report_v8` + `lint_v8`;**不要只改附录E 而不动判断**——那是孤岛化。

---

## 输出

1. `{run_dir}/{company}-analysis-{date}.html` — v8 仪表盘 HTML
2. `{run_dir}/phase6-review-log.md` — 质量环日志
3. `{run_dir}/reviewer_responses/round_*.md` — 两 reviewer 往返 + 合并 FIX 列表
4. GitHub Pages 更新

### 质量环日志格式

```markdown
# Phase 6 质量环日志: {company}
**日期:** {YYYY-MM-DD} · **run:** runs/{date}/

## 机器门控 lint_v8
| 轮次 | 退出码 | fail 项 | warn 项 |
|:-:|:-:|---|---|
| 初次 | 1 | R8 越权发声 / R10 报告与节点同步 | R2w 🟠 归家 ×2 |
| 修正后 | 0 | — | R2w 🟠 归家 ×2 |

## reviewer 往返
| 轮次 | logic | delivery | FIX 数 | 重启写手 | 主 agent 改正文 |
|:-:|:-:|:-:|:-:|---|---|
| 1 | FAIL | FAIL | 4 | node-odds, decision-writer | nodes/node-state.md |
| 2 | PASS | PASS | 0 | — | — |

## 交付
**HTML:** ✅(决断卡 5 / Top3 3 / 五章 + 附录A-E)
**发布:** ✅ leafpaper/Inves-Report / ❌(原因)
**缺口补查(Part D):** 未触发 / N 条,{已解决 x / 部分 y / 未找到 z}
```

---

## 质检清单

- [ ] `lint_v8` 退出码 0(fail 项全过);warn 项已在日志里记账
- [ ] reviewer-logic 与 reviewer-delivery 都 PASS(或 3 轮上限已转人工并通知用户)
- [ ] 每轮 reviewer 响应都落在 `{run_dir}/reviewer_responses/`,没有只存在 context 里的判定
- [ ] 判断类 FIX 都由**写手 fresh-restart** 落地,YAML 块没有被主 agent 手改
- [ ] 每次 FIX 应用后都重跑了「装配 + lint」两条命令
- [ ] `build_html` 退出 0 且成品自检无缺项
- [ ] 主页卡片字段(行动档位 / 质地 / 下次预约披露日)已随 `update_index` 更新
- [ ] Part D 若触发:每条缺口有 5 步记录 + 明确整体状态 + 补到的数据已回到判断或附录
- [ ] `main-log.md` 有 Phase 6 的启停、每轮判定、转人工(若有)记录
