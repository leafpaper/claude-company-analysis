# Phase 调度详细 Checklist (v8.0)

> 本文件由主智能体在 Step 3 加载,详细说明每个 Phase 的调度顺序、工具调用方式、判定标准。SKILL.md 只引用本文件不重复。
>
> **关键设计**(对照 v5.1.x 失败教训):
> - ❌ **不使用 `Agent(resume=...)` 参数** — 该参数不存在,Agent 工具实际 schema 仅含 description/isolation/model/prompt/run_in_background/subagent_type
> - ✅ **Fresh-Restart with Context Injection** — 修正循环时启动全新 sub-agent,prompt 注入上轮 FIX 列表 + 已修改文件路径
> - ✅ **自然语言 checklist + 真实工具**(Agent / Bash / Edit / Read),循环逻辑下沉到脚本
>
> **v8.0 变更**:Phase 3 由"5 个 part 串行写手"改为"判断链五节点 + 依赖图两波";报告首页与附录**机器装配**;
> 状态落 `runs/{date}/` + `manifest.json`。Phase 7 量化监控退役(增量复查 `--review` 取而代之)。

---

## 目录结构约定(v8)

```
output/{company}/
├── manifest.json               公司级状态唯一源(runs 列表 / 增量计数 / 上次全量 / 预约披露日 / 对比组)
├── main-log.md                 双层调度日志
├── data_snapshot.md / audit_report.{md,json} / red_flags.json /
│   peer_analysis.md / capital_flow.md / technical_analysis.md /
│   phase1-data.md / sentiment.md / data_sources.md / phase2-documents.md   ← 采集与精析产物(跨 run 共享)
└── runs/{date}/                本次 run(旧 run 整目录即留档)
    ├── nodes/node-{quality,state,odds,path,decision}.md    五个判断节点(顶部 YAML verdict 块)
    ├── assembly/assembly.json  装配产物(决断卡/面板/Top3/metadata/变化区块)
    ├── reviewer_responses/     质量环往返
    └── {company}-analysis-{date}.md   主报告
```

`{artifacts_dir}` = `output/{company}/`;`{run_dir}` = `output/{company}/runs/{date}/`。两个路径都要写进每个 sub-agent 的 prompt。

---

## Phase 1: 数据采集 (Agent 工具 → data-collector)

**调度 checklist**:

1. 用 Agent 工具启动 data-collector:
   - subagent_type = `data-collector`
   - prompt 含 `ticker / company / market / output_dir(= {artifacts_dir}) / {PYBIN}`
2. 等 sub-agent 完成(前台,等响应)
3. 直接从响应文本读出"判定"字段(响应就在你的上下文里,无需 shell)
4. 把判定写入 main-log.md
5. PASS / 部分降级 → Phase 2;FAIL → 中止 + 给用户报错

**质量门控**:`**判定**: PASS / 部分降级` + `red_flags.json` 存在(v8 写手引用红旗 id 的来源)

---

## Phase 2: 文档精析 (Agent 工具 → doc-analyst)

> 主 agent **不读 PDF、不读 pdf_sections_*.json、不写 phase2-documents.md**,只调度 + 复核门控。

**调度 checklist**:

1. 启动 doc-analyst:prompt 含 `output_dir(= {artifacts_dir}) / company / ticker / market / date / {PYBIN}` + 用户额外文档路径(若有)
2. 等响应,读 `**判定**:` 与 `**check_phase2**:` 两行
3. **复核**跑一次同一条门控命令(便宜且确定,不信任自证):

   ```
   {PYBIN} -m scripts.check_phase2 --md {artifacts_dir}/phase2-documents.md
   ```
4. 判定 + 降级标注写入 main-log.md
5. 退出码 0 且判定 PASS / 部分降级 → Phase 3;否则 **fresh-restart doc-analyst 一次**(注入三行 R 结果),仍失败 → 转人工。**主 agent 不自己补写**

**质量门控**:doc-analyst `**判定**: PASS / 部分降级` + 主 agent 复核 `check_phase2` 退出码 0

---

## Phase 3: 判断链写作与装配(五节点 + 依赖图两波 + 装配)

**详细执行细则见 `phases/phase3-node-writing.md`**(prompt 模板 / 逐波验收 / 装配命令 / 失败处理);本节只列不变量。

**波次由脚本算,不手写顺序**:

```
{PYBIN} -m scripts.node_graph --all
→ 第1波(并行): ①质地 ∥ ③赔率 ∥ ④路径   第2波: ②状态   第3波: ⑤决策
```

| 波 | 谁 | 产物 | 验收 |
|:-:|---|---|---|
| 1 | node-quality ∥ node-odds ∥ node-path(3 个 `run_in_background=True`) | `{run_dir}/nodes/node-{quality,odds,path}.md` | 三条 `verdict_block --schema node-X` 退出 0 |
| 2 | node-state(前台;引用③ verdict) | `node-state.md`(含 `critical_point`) | `verdict_block --schema node-state` 退出 0 |
| 3 | decision-writer(前台;只读四个 YAML 块) | `node-decision.md`(含 `gear_cap` / `front_page_intro`) | `verdict_block --schema node-decision` 退出 0 + triad 与②③④同源 + 有 🔴 必封顶 |
| — | 装配脚本 | `assembly/assembly.json` + 主报告 md | `assemble_report_v8` 退出 0 + Top3 非空 + 无缺附录告警 |

**不变量**:

1. **写手只读两份手册**(链手册 + 自己那份节点手册),跨节点只引用 verdict——主 agent 派活时不要把别人的手册或正文塞进 prompt。
2. **主 agent 复核 schema**,不信 sub-agent 自证(同 Phase 2 的门控哲学)。
3. **装配零人工抄写**:决断卡 / 面板 / Top3 / 主页 metadata / 附录 A-E 全部脚本生成;主 agent **不手改节点 md 的 YAML 块**——判断是写手的,要改就 fresh-restart 写手。
4. 每波结束写一行 main-log.md(`- {ts} Phase 3 第N波 完成,判定 …`)。

---

## Phase 6: 质量环与发布(机器门控 + 两 reviewer 并行 + 出片发布)

**详细执行细则见 `phases/phase6-review-publish.md`**(lint 规则表 / reviewer prompt / FIX 分诊 / 发布步骤 /
缺口补查);本节只列不变量。

| 步 | 谁 | 命令 / 工具 | 验收 |
|:-:|---|---|---|
| 0 | 主 agent | `{PYBIN} -m scripts.lint_v8 --run-dir {run_dir} --artifacts-dir {artifacts_dir}` | 退出 0(fail 项全过;warn 记账不阻断) |
| 1 | reviewer-logic ∥ reviewer-delivery(2 个 `run_in_background=True`) | Agent 工具 | 两份响应落 `{run_dir}/reviewer_responses/round_{N}_{logic,delivery}.md` |
| 2 | 主 agent | `{PYBIN} -m scripts.review_loop --run-dir {run_dir} --round {N}` | 读 JSON:`overall_pass` / `diff_repeat` / `restart_writers` / `edit_targets` |
| 3 | 写手 fresh-restart(判断类)+ 主 agent Edit(表述类) | Agent / Edit | 改完**必须**重跑 `assemble_report_v8` + `lint_v8` |
| B | 主 agent | `{PYBIN} -m scripts.build_html --company {company} --run-dir {run_dir}` | 退出 0(脚本内置再跑一次 lint,fail 阻断) |
| C | 主 agent | `{PYBIN} -m scripts.update_index --company {company} --repo $INVES_REPORT_DIR --force` + git push | 卡片 + `data/reports.json` 已更新 |

**不变量**:

1. **机器先于人**:`lint_v8` 没过就不派 reviewer——确定性规则挡得住的错,不花 LLM 的注意力。
2. **两个 reviewer 并行**,不是串行;判定与 FIX 一律落文件,不靠 context 记忆。
3. **FIX 落点 = 节点 md**(`{run_dir}/nodes/node-{node}.md`),不是已删除的 `phase3-partN.md`:
   判断类 → fresh-restart 写手(主 agent **不改 YAML 块**);表述类 → 主 agent 改正文;交付类 → 改 HTML 模板。
4. **3 轮上限 + diff 对抗检测**:`diff_repeat=true`(两轮之间节点 md 一个字没变)或 round 3 仍 FAIL → 转人工。
5. 每轮写一行 `main-log.md`(`- {ts} reviewer Round N 综合判定 …,FIX 数 M`)。

---

## 主 agent 通用规则(贯穿全 Phase)

1. **不读 sub-agent 响应全文**,直接从响应文本读关键字段(`**判定**:` / `**verdict**:` / `[FIX-` 等)
2. **修正循环只能 fresh-restart**,不要尝试 `Agent(resume=...)`(该参数不存在)
3. **状态持久化**:要跨循环保留的状态(reviewer 响应 / FIX 列表 / diff signature)一律写文件(`{run_dir}/reviewer_responses/…`),不靠 context 记忆
4. **日志双层**:Phase 启停 / sub-agent 完成 / 判定 / 转人工,用 Edit 追加 `main-log.md` 一行(`- {yymmdd hhmm} {事件}`)
5. **失败处理**:先 fresh-restart 同 subagent_type 一次;仍失败 → PushNotification + `{run_dir}/_failure_report.md`(累计 FIX / 响应路径 / main-log tail 30 行 / 建议下一步)

---

## 引用

- 工具 schema 真实参数:见 SKILL.md 顶部"调度协议"段(本文件不重复)
- 判断链规则(四问 / 决策层 / 装配 / 写作规范):`references/judgment-chain.md`(唯一真理源)
- 节点 → 写手 → 手册 → schema 的绑定表:`references/judgment-chain.md` §5 消化路径总表
- 依赖图与波次:`scripts/node_graph.py`(全量与增量共用,票 09 的子集调度复用同一套)
- 装配产物字段:`scripts/schemas/assembly.schema.json`(文档不复制字段表)
