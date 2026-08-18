# Phase 3: 判断链写作与装配 (v8.0 — 依赖图两波 + 决策 + 机器装配)

> **谁读这份**:**主 agent**(Phase 3 执行细则)。v8 起节点写手不读 phase 文件——它们只读
> `references/judgment-chain.md` + 自己那一份节点手册(消化纪律,链手册 §5)。本文件只讲
> "主 agent 怎么派活、怎么验收、怎么装配",不讲"报告怎么写"。
>
> **v7 的 `phase3-analysis-report.md` 已删除**:9 章节骨架 / 5 个 part 写手 / 评分与定性综合方向
> 随判断链收敛一并退役(去向见 CHANGELOG v8.0)。

---

## 0. 前置条件

| 项 | 检查 |
|---|---|
| run 目录 | `output/{company}/runs/{date}/` 已由 `init_run --run-type full` 建好(含 `nodes/` `assembly/`) |
| Phase 1 产物 | `data_snapshot.md` / `audit_report.md` / `audit_report.json` / `red_flags.json` / `peer_analysis.md` / `capital_flow.md` / `technical_analysis.md` / `phase1-data.md` / `sentiment.md` / `data_sources.md` |
| Phase 2 产物 | `phase2-documents.md`(§1-§8,过 check_phase2) |
| 术语 | `{artifacts_dir}` = `output/{company}/`(采集产物落公司级,跨 run 共享);`{run_dir}` = 本次 run 目录(判断链产物落这里) |

缺 `red_flags.json` → 先补跑(写手的面板 `red_flag_ref` 与决策层封顶检查都要它):

```
{PYBIN} -m scripts.financial_audit {artifacts_dir}/raw_data --json {artifacts_dir}/audit_report.json
{PYBIN} -m scripts.red_flags --audit-json {artifacts_dir}/audit_report.json --out {artifacts_dir}/red_flags.json
```

---

## 1. 算波次(依赖图,别手写顺序)

```
{PYBIN} -m scripts.node_graph --all            # 全量:五节点
{PYBIN} -m scripts.node_graph --nodes state,path,decision   # 增量:只跑标脏子集(票 09)
```

输出即派活顺序:

```
第1波(并行): ①质地(node-quality) ∥ ③赔率(node-odds) ∥ ④路径(node-path)
第2波(单个): ②状态(node-state)
第3波(单个): ⑤决策(decision-writer)
```

**为什么是这个序**:②状态的四层验证第④关要引用③赔率 verdict;⑤决策吃四个节点的 YAML 块。
写作顺序 ≠ 章节顺序,排版是装配脚本的事。

子集调度打印 `⚠️ … 依赖本轮不跑的 …` 时:先确认那些节点的上版 YAML 块已拷进本 run 的 `nodes/` 并盖「复用」戳(`reused_from: {上版日期}`),否则不许开跑。

---

## 2. 第一波:三个写手并行

```python
Agent(subagent_type="node-quality", run_in_background=True, description="①质地",
      prompt=f"""写①质地节点。
run_dir       = output/{company}/runs/{date}/
artifacts_dir = output/{company}/
company={company} ticker={ticker} market={market} date={date} PYBIN={PYBIN}

按 references/judgment-chain.md + references/node-quality.md 两份手册写
{run_dir}/nodes/node-quality.md(顶部 YAML verdict 块 + 正文 ≤70 行),
写完自跑 verdict_block 校验,响应只回完成报告(**判定** 单独一行),不要回放文件内容。""")

Agent(subagent_type="node-odds", run_in_background=True, description="③赔率", prompt=...)
Agent(subagent_type="node-path", run_in_background=True, description="④路径", prompt=...)
```

三个都 `run_in_background=True`,等系统的 task-notification 收齐三份响应。

**验收(主 agent 复核,不信自证)**:

```
{PYBIN} -m scripts.verdict_block --schema node-quality --file {run_dir}/nodes/node-quality.md
{PYBIN} -m scripts.verdict_block --schema node-odds    --file {run_dir}/nodes/node-odds.md
{PYBIN} -m scripts.verdict_block --schema node-path    --file {run_dir}/nodes/node-path.md
```

三条退出码全 0 + 三份响应 `**判定**: PASS / 部分降级` → 进第二波。任一 FAIL/非 0 →
fresh-restart 该写手一次(prompt 注入 verdict_block 的报错原文 + "上轮 FAIL"),仍失败 → 转人工。

---

## 3. 第二波:②状态

第一波三个都过了才启动(state 要引用 odds 的 verdict)。前台等响应。

```python
Agent(subagent_type="node-state", run_in_background=False, description="②状态",
      prompt=f"""写②状态节点(第二波)。run_dir / artifacts_dir / … 同上。
③赔率已产出:{run_dir}/nodes/node-odds.md —— **只读它顶部 YAML 块的 verdict 与 anchor_range**,
四层验证第④关与贝叶斯第 3 问引用它,不要自算估值。
「该等什么」(critical_point)是全链唯一产出处,2-4 条,每条带时间窗与判据。""")
```

验收:`verdict_block --schema node-state` 退出 0 + `critical_point.items` ≥1 条(schema 已强制)。

---

## 4. 第三波:⑤决策

```python
Agent(subagent_type="decision-writer", run_in_background=False, description="⑤决策",
      prompt=f"""写⑤决策层 + 首页 3-5 句导读。run_dir / artifacts_dir / … 同上;amount={amount}。
四个节点块已就位。只读它们顶部的 YAML 块(不读正文、不读节点手册),
按 judgment-chain §2 查六档映射,封顶检查看 {artifacts_dir}/red_flags.json 有无 🔴。""")
```

验收:`verdict_block --schema node-decision` 退出 0,并**人工确认三件事**(从响应字段读,不读全文):

1. `triad` 三个字段与②③④ 的 verdict 同源(改口径 = 越权重推);
2. `gear_cap` 有结果;有 🔴 就必须封顶「回避」;
3. ③ `same_direction: false` 时档位已保守一档。

---

## 5. 装配(零人工抄写)

```
{PYBIN} -m scripts.assemble_report_v8 \
    --run-dir "{run_dir}" --company "{company}" --ticker "{ticker}" --date "{date}" \
    --artifacts-dir "{artifacts_dir}" \
    --out "{run_dir}/{company}-analysis-{date}.md"
```

脚本会:读五个 YAML 块 → 决断卡五行 / 赚钱面板(含红标反查)/ Top3 红旗(脚本 ⊕ 提名同池)/
主页 metadata → 挂载五章正文 → 装配附录 A-E(D = 红旗总清单机器合并)→ 落
`{run_dir}/assembly/assembly.json` + 主报告 md。

**验收**:退出码 0 + stdout 的 Top3 行不为空 + 无 `⚠️ 附录X 缺产物`。装配失败(节点块不合契约 /
面板 `red_flag_ref` 指向不存在的红旗 id)会硬失败并打印字段路径——按提示 fresh-restart 对应写手,
**主 agent 不手改节点 md 的 YAML 块**(那是写手的判断)。

---

## 6. 失败与降级

| 情况 | 处理 |
|---|---|
| 某写手 3 轮 schema 仍红 | 转人工;`_failure_report.md` 记 verdict_block 报错 + 该节点 md 路径 |
| 第二波报"node-odds.md 不存在" | 调度错序,先补第一波,别让 state 自算估值 |
| 装配报 `未找到采集产物` | 补跑对应采集脚本(附录 A/B/C/E 挂载源),不许让写手手写附录 |
| 装配报红旗清单不合契约 | 看是脚本 id 变了还是提名 id 撞车,重启对应写手修提名 |
| 决策层与②/④ 口径不一致 | fresh-restart decision-writer,prompt 注入"triad 必须原样搬运"+ 两边原话 |

---

## 7. 增量复查(`--review`)下的差异(票 09 落地前先记在这)

- 波次由分诊单决定:`node_graph --nodes {标脏集合}`;状态/赔率/决策每次必跑,路径每次核销证伪清单。
- 未重评节点:从上版 run 的 `nodes/` 拷 md 过来,在 YAML 块加 `reused_from: {上版日期}`。
- 装配加 `--prev-run-dir {上版 run}`(+ 可选 `--metric-deltas`)即产首页「较上版变化」区块。
