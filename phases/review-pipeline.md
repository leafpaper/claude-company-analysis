# 增量复查 `--review` 执行细则(v8 票 09)

> 主 agent 在用户触发 `--review`(或自然语言"复查 / 更新 / 看看有什么变化",或旧入口
> `--monitor`——先告知一句已改名,然后照常走本流程)时加载本文件。
> 四段链 R1→R4 彻底取代 v7 的量化监控;**lint + 双 reviewer 不打折**,旧版整目录留档,发布替换。
>
> 分层重评规则(spec §8,机器执行):状态/赔率/路径/决策每次必重评;**质地默认复用**,
> 只有分诊四条标脏机检(年报披露 / 分部占比跨档 / 新质地红旗 / 关键指标变号)触发才重评。
> 成本目标 ≈ 全量 1/3(质地复用时:4 个写手 + 机器装配,省掉 1 写手 + Phase 2 全量精读)。

---

## R0: 建 run + 基线快照(含硬规则 1)

```
{PYBIN} -m scripts.init_run --company "{company}" --ticker "{ticker}" --run-type incremental
```

- 成功:stdout 两行 = `{artifacts_dir}` / `{run_dir}`;`{run_dir}/baseline/` 已快照刷新前的
  `metrics.json` / `red_flags.json` / `audit_report.json` / `fina_mainbz.parquet` / PDF 清单
  (采集产物落公司级、R1 会原地覆盖,快照是分诊 diff 的唯一 before 侧)。
- **退出码 3 = 硬规则 1**:基线不是可用的 v8 结构(旧 v7 报告 / 无 manifest / 节点块不合契约)
  → 告知用户"旧结构基线,本次直接全量",改跑 `--run-type full` 走 SKILL.md 正常全量流程,**本文件流程终止**。
- `RunExists` 同全量处理(确认重跑意图后清理同日目录)。

## R1: 证据刷新(增量模式)

1. **data-collector**(增量模式):prompt 照 Phase 1 模板,外加四行——
   - 「**先设 `CA_CACHE_MAX_AGE_DAYS=0`**(PowerShell `$env:CA_CACHE_MAX_AGE_DAYS='0'` / bash `export`)
     再跑全部采集脚本——复查的意义就是披露后的新证据,7 天数据缓存会把行情/筹码悄悄换成旧值」
   - 「**增量模式**:全部脚本 artifact 正常全量刷新(便宜);PDF 只下**新增披露**——先读
     `{run_dir}/baseline/pdfs_before.json` 已有清单,只下载清单外的新报告(本次复查的主角
     通常就是刚披露的定期报告)并抽 section」
   - 「WebSearch 时间过滤:重点查 {上次 run 日期} 之后的新公告/舆情,sentiment.md / data_sources.md 整体重写」
   - 「完成报告加一行 `**新增 PDF**: {清单或"无"}`」
2. **doc-analyst**(增量模式,仅当有新增 PDF):prompt 照 Phase 2 模板,外加——
   - 「**增量模式**:只精读新增 PDF {清单};把要点**并入更新** `phase2-documents.md`——§1 清单加行,
     相关章节增补『{date} 增量精析』小节,不重写旧内容;`check_phase2` 门控照跑」
   - 无新增 PDF → 跳过本步,main-log 记一行"无新增文档,Phase 2 跳过"。
3. 门控同全量:data-collector `**判定**:` + red_flags.json 存在;doc-analyst 跑了就复核 `check_phase2`。

## R2: 纯脚本分诊(零 LLM)

```
{PYBIN} -m scripts.triage --company-dir {artifacts_dir} --run-dir {run_dir} --apply-reuse
```

- 产 `{run_dir}/triage.json`(过 triage.schema.json):质地四条标脏机检 + 重评波次 +
  指标 diff + 红旗 diff + 证伪清单 + 临界点 + 建议档。**分诊单是结构化产物,主 agent 不改判**。
- `--apply-reuse` 已把未重评节点(质地未标脏时)从上版拷进 `{run_dir}/nodes/` 并盖
  `reused_from` 戳 + 正文 ♻️ 说明行——**不要再手动拷贝或改它**。
- 读 stdout 摘要写入 main-log.md 一行;「拿不准→脏」的规则(triggered=null)属正常保守行为。
- ⚠️ 建议档提示(>12 个月未全量 / ≥4 次增量)→ 完成消息里转告用户"建议下次全量重锚",本次照常增量。

## R3: 依赖图跑标脏子集

- 波次以 `triage.json` 的 `waves` 为准(= `node_graph --nodes {rerun_nodes}` 同一套调度,别手写)。
- prompt 模板与逐波验收同 `phases/phase3-node-writing.md`,**每个重评写手 prompt 额外注入**:
  - 通用一行:「本次是增量复查,基准日 {date},上版 {prev_run_date} 的判断在 `{prev_run_dir}/nodes/`,
    证据已全量刷新;你要**重新独立判断**,不是给旧文打补丁」
  - **node-path**:注入 `triage.json` 的 `falsification_checklist`——「逐条核销:每条给 ✅未触发 /
    ❌已触发 / ⚠️数据不足,落进新 YAML 块 falsifications 的 triggered 字段;左尾清单同步复核」
  - **node-state**:注入 `critical_points`——「上版『该等什么』临界点逐条判定到达/未到达,写进正文;
    新块照常产出新的 critical_point」
  - **node-quality**(仅标脏时):注入触发的标脏规则与 evidence——「标脏原因:{rules};全量口径重评五子判定」
- 每波结束照常 `verdict_block` 复核 schema;复用节点无需验收(triage 拷贝时已复检)。

## R4: 决策层 + 首页必重装配

```
{PYBIN} -m scripts.assemble_report_v8 --run-dir {run_dir} --company {company} --date {date} \
    --ticker {ticker} --artifacts-dir {artifacts_dir} \
    --prev-run-dir {artifacts_dir}/runs/{prev_run_date} --metric-deltas {run_dir}/triage.json
```

- `--prev-run-dir` + `--metric-deltas` 装出首页「较上版变化」区块:首句机器答「阿尔法变了没」,
  三元组/档位对比、翻转节点、红旗与证伪变化、关键指标 delta 全部 diff 自 YAML 块与分诊单。
- **硬规则 2 在这里机判**(质地判定翻转 或 档位跨两档 → `change_block.full_rerun_advice.advised=true`,
  首页明示「建议全量重跑」)——**照常产出本次报告**,完成消息里把这句转告用户。
- 之后 **Phase 6 全套不打折**:`lint_v8` → reviewer-logic ∥ reviewer-delivery → 修正循环 →
  `build_html` → `update_index`(卡片带 `review_hint` 超龄字段)。规则、轮次上限、FIX 分诊全同全量。

## 收尾

- manifest 由 init_run 自动登记(runs +1 incremental / incremental_count+1 / 全量日期不动);
  发布后确认 `manifest --show` 与实际一致。旧版 run 整目录留档,站点条目按日期自然替换。
- 该公司在对比组(manifest.compare_groups 非空)→ 提示用户一句"对比页成员已更新,可重跑对比"
  (对比页重装配是票 10 的 `--compare`,本流程不自动触发)。
- main-log.md 记账贯穿 R0-R4,每段一行(同全量双层日志规范)。
