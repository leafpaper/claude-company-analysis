# Phase 调度详细 Checklist (v6.0)

> 本文件由主智能体在 Step 3 加载,详细说明每个 Phase 的调度顺序、工具调用方式、判定标准。SKILL.md 只引用本文件不重复。
>
> **关键设计**(对照 v5.1.x 失败教训):
> - ❌ **不使用 `Agent(resume=...)` 参数** — 该参数不存在,Agent 工具实际 schema 仅含 description/isolation/model/prompt/run_in_background/subagent_type
> - ✅ **Fresh-Restart with Context Injection** — 修正循环时启动全新 sub-agent,prompt 注入上轮 FIX 列表 + 已修改文件路径
> - ❌ **不再写伪代码"函数"**(`apply_fix_to_parts()` / `wait_all_background_agents()` 都不存在)— 所有循环逻辑下沉到 `scripts/review_loop.py`
> - ✅ **自然语言 checklist + 真实工具**(Agent / Bash / Edit / Read)

---

## Phase 1: 数据采集 (Agent 工具 → data-collector)

**调度 checklist**:

1. 用 Agent 工具启动 data-collector:
   - subagent_type = `data-collector`
   - prompt 含 ticker / company / market / output_dir
2. 等 sub-agent 完成(前台,等响应)
3. 直接从响应文本读出"判定"字段(响应就在你的上下文里,无需 shell)
4. 把判定写入 main-log.md(暂手工,v5.1.3 后续配置 hook 自动)
5. PASS / 部分降级 → Phase 2;FAIL → 中止 + 给用户报错

**质量门控**:`**判定**: PASS / 部分降级`

---

## Phase 2: 文档精析(主 agent 自跑)

**调度 checklist**:

1. 主 agent 读 `pdfs/*.pdf` + `pdf_sections_*.json`
2. 精读 6 个高价值 section(income_statement_changes / subsidiaries / MD&A / 风险因素 / 非经常性损益 / 关联交易)
3. 写 `output/{company}/phase2-documents.md`
4. 跑 `{PYBIN} -m scripts.check_phase2 --md output/{company}/phase2-documents.md`;退出 1 → 补写后重跑

**质量门控**:`check_phase2` 退出码 0(§1-§8 齐全 + §2 [PDF:] 原文引用≥3 + §8 锚点≥5);每份 PDF 都被列出

---

## Phase 3: 综合分析(4 个 phase3-part sub-agent 串行 + assemble)

**串行顺序固定**:`part2 → part3 → part4 → part1`(part1 最后,§一 执行摘要依赖 §四 评分加权 + §五 估值 + §六 风险)

**章节边界**(真理来源 `scripts/assemble_report.py:PART_EXPECTED_SECTIONS`):
part1=§一 · part2=§二/§三 · part3=§四/§五 · part4=§六/§七/§八。

**调度 checklist**:

对每个 N ∈ [2, 3, 4, 1] 顺序:

1. 用 Agent 工具启动 `phase3-part{N}`:
   - prompt 含 `output_dir / company / date / type / market / ticker / amount`
2. 等响应,直接从响应文本读出"判定"字段(响应就在你的上下文里,无需 shell)
3. **判定 = PASS / 部分降级** → 进下一个 part
4. **判定 = FAIL** → fresh-restart 同一 subagent_type(不是 Resume!):
   - 启动新 phase3-partN sub-agent
   - prompt 注入"上一轮判定 FAIL,问题点: {主 agent 审到的具体问题}, 请重写"
   - 最多 1 次 fresh-restart;仍 FAIL → 转人工
5. 4 个 part 全部 PASS 后,用 Bash 跑 assemble_report.py:

   ```
   {PYBIN} -m scripts.assemble_report \
       --company "{company}" --date "{date}" \
       --parts-dir "output/{company}/" \
       --out "output/{company}/{company}-analysis-{date}.md"
   ```
6. 检查脚本退出码 + 主报告 section 数 = 8

**质量门控**:每 part 自检 PASS + assemble 退出码 0 + 8 章节齐全 + Audit 红旗全部被引用

---

## Phase 6: 审核发布

> v5.1.4 删除 Phase 4(多角色)+ Phase 5(差异化洞察)。Phase 3 完成后直接进 Phase 6 审核。



### Part A: 18 项审核 + Part D 缺口补查 + anti_lazy_lint

主 agent 加载 `phases/phase6-review-publish.md` Part A 流程,然后跑:

```
{PYBIN} -m scripts.anti_lazy_lint output/{company}/{company}-analysis-{date}.md
```

退出码 0 → 进 Part A.5;退出码 1 → 主 agent Edit 修对应 part,重 assemble,重跑 lint,最多 3 次。

### Part A.5: reviewer 3 维度并行 + 修正循环(v5.1.3 重写)

**Round 1** checklist:

1. 主 agent **并行**启动 3 个 reviewer(都 `run_in_background=True`):

   ```python
   Agent(subagent_type="reviewer-narrative",  run_in_background=True,
         prompt=f"评审 ...{company}-analysis-{date}.md, artifacts_dir=...")
   Agent(subagent_type="reviewer-valuation",  run_in_background=True, prompt=...)
   Agent(subagent_type="reviewer-redflag",    run_in_background=True, prompt=...)
   ```
2. 等 3 个完成(系统通过 task-notification 自动通知)
3. 主 agent 把 3 份响应**保存为文件**:

   ```
   # 主 agent 把每份 response 文本 Write 到:
   output/{company}/reviewer_responses/round_1_narrative.md
   output/{company}/reviewer_responses/round_1_valuation.md
   output/{company}/reviewer_responses/round_1_redflag.md
   ```
4. **调用 `review_loop.py`** 合并判定 + 处理 FIX:

   ```
   {PYBIN} -m scripts.review_loop \
       --company "{company}" --date "{date}" \
       --output-dir "output/{company}/" \
       --round 1
   ```

   脚本会:
   - 读 round_1_*.md 提取 PASS/FAIL + FIX 列表
   - 合并 FIX(P1-P4 分组,去重)
   - 计算 part 文件 diff signature(md5)
   - 如果是 round > 1:对比上轮 signature → 若重复标 "diff_repeat"
   - 输出 JSON: `{"overall_pass": bool, "fix_applied": int, "diff_repeat": bool, "fix_list_path": "..."}`
5. 主 agent 读 JSON,决定下一步:
   - `overall_pass = true` → 进 Part B(HTML 生成)
   - `diff_repeat = true` → 转人工(LLM 反复对抗)+ 输出累计 FIX 给用户
   - 否则,主 agent 用 Edit 工具按 review_loop.py 输出的 FIX 列表 改 phase3-partN.md(脚本只输出 FIX 列表,实际 Edit 由主 agent 做)
6. 主 agent 重新跑 `assemble_report.py` + `anti_lazy_lint`
7. 进 **Round 2**:重新并行启动 3 个 reviewer(全部 fresh,prompt 注入"上轮 FIX 已应用如下: {list},请重审")
8. 重复 Round 2 / Round 3 直到 PASS 或转人工

**round 上限**:3 轮(超过转人工)

### Part B: HTML 生成

```
{PYBIN} -m scripts.build_html --md output/{company}/{company}-analysis-{date}.md \
    --out output/{company}/{date}.html
```

### Part C: 推送 GitHub Pages

> 本发布步骤为**可选**;`$INVES_REPORT_DIR` 路径可配置(环境变量;Mac/Linux 默认 /tmp/Inves-Report,Windows 设为如 C:\Inves-Report)。

```
{PYBIN} -m scripts.update_index ...    # 更新 reports.json
git -C $INVES_REPORT_DIR add reports/*.html reports.json index.html
git -C $INVES_REPORT_DIR commit -m "..." && git -C $INVES_REPORT_DIR push
```

**质量门控**:anti_lazy_lint 4 项 PASS + reviewer 3 维度 PASS + HTML section 数 = 8

---

## 主 agent 通用规则(贯穿全 Phase)

1. **不读 sub-agent 响应全文**,直接从响应文本读出关键字段(判定 / `### 维度` / `[FIX-P` 等;响应就在你的上下文里,无需 shell)
2. **修正循环只能 fresh-restart**,不要尝试 `Agent(resume=...)`(该参数不存在,会被忽略 → sub-agent 起新实例丢上下文)
3. **状态持久化**: 任何要跨循环保留的状态(reviewer 响应 / FIX 列表 / diff signature)都**写文件**(`output/{company}/reviewer_responses/...`),不要靠 context 记忆
4. **日志双层**:
   - 当前(v5.1.3 过渡):主 agent 在 Phase 启停 / sub-agent 调用前后 / 判定时,**用 Edit 工具**追加 main-log.md 一行(格式 `- {yymmdd hhmm} {事件}`)
   - 未来(v5.2 规划):SubagentStop hook 自动追加(待 verify hook 环境变量后启用)
5. **失败处理**:每个 Phase 失败时,主 agent 先尝试 1 次 fresh-restart 同 subagent_type;仍失败则用 PushNotification 通知用户 + 把累计的 FIX 列表 / 错误信息保存到 `output/{company}/_failure_report.md`

---

## 引用

- 工具 schema 真实参数:见 SKILL.md 顶部"调度协议"段(本文件不重复)
- reviewer FIX 指令 schema:`reviewer-{narrative,valuation,redflag}.md` 各自定义
- 章节 → Part 映射:`scripts/assemble_report.py` 的 `PART_EXPECTED_SECTIONS`(真理来源)
- review_loop.py 接口:见 `scripts/review_loop.py` 头部 docstring
