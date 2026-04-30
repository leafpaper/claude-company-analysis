# Agent 调度协议 (v5.1)

主智能体(SKILL.md)与所有 sub-agent 之间的统一调度规范。本文件由主 agent 在 Step 0 加载,作为协议层真理来源。

---

## 1. Agent ID 收集协议

**目的**: sub-agent 完成后获取其裸 ID,用于后续 Resume(修正循环)。

### 探测命令(macOS / Linux 通用)

```bash
ls -lt ~/.claude/projects/*/*/subagents/agent-*.meta.json 2>/dev/null \
  | head -1 | awk '{print $NF}' | xargs basename | sed 's/agent-//;s/\.meta\.json//'
```

返回纯 ID(如 `a95e84cd0b54c85ad`),不含 `agent-` 前缀和 `.meta.json` 后缀。

> 备注: macOS BSD `find` 不支持 `-printf`,故不用 `find -printf`。`ls -lt` 按修改时间倒序,`head -1` 取最近,`awk '{print $NF}'` 取最后一列(路径)。

### 何时探测

每次 `Agent(subagent_type=X)` **前台**(非 background)调用完成的**第一时间**:

1. 立刻跑探测命令拿到 ID
2. 把 ID 写进 `output/{company}/main-log.md`(见 §3)
3. 把 ID 存进当前 phase 上下文变量(如 `DATA_COLLECTOR_ID` / `PERSONA_ID` / `REVIEWER_ID` / `PHASE3_PART1_ID` 等)

> background 调用不适用 — Resume 当前架构只对前台 agent 设计。

### ID 失效规则

- **Phase 切换** → 老 ID 立即作废,新 Phase 重新探测
- **同一 Phase 修正循环内** → 复用同一 ID,严禁启动新 agent(否则丢上下文)
- **跨次分析** → ID 完全失效,即使是同一公司

---

## 2. Resume 修正循环协议

**核心原则**: 当 reviewer FAIL / Phase 3 某 part 需要重写,**必须 Resume 同一个 sub-agent**,而不是新启动。

### 调用规范

```python
# ❌ 错误 — 新启动,sub-agent 丢失上次上下文
Agent(subagent_type="reviewer-narrative",   # v5.1.1 拆 3 并行,这里仅举一例
      prompt="重审 ...")

# ✅ 正确 — Resume 同一 ID,sub-agent 还记得上轮判定
Agent(resume="<REVIEWER_ID>",
      subagent_type="reviewer-narrative",   # Resume 必须仍然指定 type,与初次一致
      prompt="主 agent 已按你上轮 FIX 修了 part1 的评分,请重审")
```

### 关键点

1. `resume` 参数填**裸 ID**,不带 `agent-` 前缀或 `.meta.json` 后缀
2. `subagent_type` 必须仍然指定,且与初次调用时一致
3. prompt 不重复 sub-agent 自己已知的内容(它还记得),只说"主 agent 做了 X 改动,请验证"

---

## 3. main-log.md 双层日志协议

### 位置

`output/{company}/main-log.md`,主 agent 在 Step 2(创建输出目录)同时创建,初始内容仅一行:

```
# {company} 分析日志 (v5.1)
```

### 格式

每行 `- {yymmdd hhmm} {事件}`,时间精确到分,例如 `260429 1430`。

### 强制日志事件清单

主 agent 在以下时点必须写日志:

| 时点 | 日志条目 |
|---|---|
| 分析启动 | `- {ts} ━━━ 开始分析 {company}({ticker}) ━━━` |
| Phase N 启动 | `- {ts} 启动 Phase N {sub-agent 名 / "主 agent 自跑"}` |
| sub-agent 完成 | `- {ts} Phase N 完成 {AGENT}_ID={裸 ID},判定 {PASS/FAIL/降级}` |
| reviewer 判定 | `- {ts} reviewer 第 {N} 轮判定 {PASS/FAIL},REVIEWER_ID={ID}` |
| 修正循环每轮 | `- {ts} 第 {N} 轮 FIX 应用 {part 列表},重 assemble 完成` |
| 转人工 | `- {ts} ⚠️ {原因},转人工 + 输出累计 FIX` |
| 分析完成 | `- {ts} ━━━ 完成 {company} 分析 ━━━` |

### 子 agent 内部日志

sub-agent 内部不强制写文件日志,但响应末尾必含**自检报告**结构(见 §5)。主 agent 用 Grep 提取关键字段写入 main-log.md。

---

## 4. 修正循环防死锁协议

适用于 Phase 6 Part A.5 reviewer FAIL 场景。

### 伪代码

```python
round = 0
last_diff_sig = None
fix_history = []   # 累计 FIX 列表,转人工时一并输出

while round < 3 and not reviewer_pass:
    round += 1

    # Step 1: 提取 FIX 列表
    fix_list = grep("^- \\[FIX-P[1-5]-§", reviewer_output)
    fix_history.extend(fix_list)

    # Step 2: 按 part 分组应用 FIX
    apply_fix_to_parts(fix_list)

    # Step 3: diff 对抗检测
    new_sig = md5(read part1.md + part2.md + ... + part5.md)
    if new_sig == last_diff_sig:
        log(f"⚠️ 第 {round} 轮 diff signature 重复,LLM 在反复对抗,转人工")
        break
    last_diff_sig = new_sig

    # Step 4: 重 assemble + 重跑 lint + Resume reviewer
    bash("python3 -m scripts.assemble_report ...")
    bash("python3 -m scripts.anti_lazy_lint ...")
    # v5.1.1: 实际跑时这里是 3 个 reviewer 并行 Resume(narrative/valuation/redflag),此处简化为 1 个
    Agent(resume=REVIEWER_ID,
          subagent_type="reviewer-narrative",
          prompt=f"已应用第 {round} 轮 FIX,请重审")

if round == 3 and not reviewer_pass:
    log("⚠️ reviewer 连续 3 轮 FAIL,转人工")
    output_to_user(fix_history, "请人工介入修复,主 agent 已停止自动重试")
```

### 边界

- **3 轮上限**: 含初次判定共 4 次 reviewer 调用(1 初判 + 3 重审)
- **diff signature**: `md5sum` 拼接 5 个 part 文件内容,简单可靠
- **§十三 / §十四 涉及 FIX**: 不能直接改 part5,标 ❌ 转人工(留 v5.1.x 处理 Phase 4 重跑)

---

## 5. Sub-agent 自检报告统一结构

所有 sub-agent 响应**末尾**必含以下结构,主 agent 用 Grep 提取,不 Read 完整响应:

```markdown
### {Phase N / Part N} 完成报告
**判定**: PASS / FAIL / 部分降级
**artifacts**: {路径 1}, {路径 2}, ...
**降级标注**: {若有,说明哪些数据/步骤降级;若无写"无"}
**(可选)精简版片段**: {若 sub-agent 需要主 agent 拼到主报告某处,直接给可复制的 markdown 片段}
```

主 agent 用 `grep "^\\*\\*判定\\*\\*:"` 提取判定结果。

---

## 6. lessons-learned 跨任务经验库 (v5.1.1)

### 目的

主 agent 在每次 sub-agent 完成后,从其自检报告里抽取 **lessons** 字段,追加到全局经验库。下次同类 sub-agent 启动时,主 agent 读经验库**最近 30 天**条目注入到 prompt,防止重复踩坑。

### 文件位置

`output/_global/lessons-learned.md` — 跨公司共享,**不在某家公司的 output/ 下**。首次写入时主 agent 自动创建文件 + 头部。

### 文件格式

```markdown
# Company Analysis 全局经验库 (lessons-learned, v5.1.1)

## 类别: data-collector
- [{yymmdd} {company}] {经验,≤ 100 字}
- [260424 实丰文化] 北交所代码已迁移 832522→920522,resolve_ticker 命中保住数据
- [260415 闻泰科技] PDF 缺新一期年报, 备用 sina 源补救成功

## 类别: phase3-part2 (基本面+行业)
- [{yymmdd} {company}] {经验}

## 类别: phase3-part4 (估值+回报+定性)
- [260429 盛美上海] DCF 假设营收+30% 但历史下滑, reviewer FAIL → 调整到+12%

## 类别: persona-agent
- ...

## 类别: reviewer (合并 narrative/valuation/redflag)
- ...
```

类别用 sub-agent 名,新类别由主 agent 自动新建段。

### Sub-agent 输出协议(可选字段)

每个 sub-agent 自检报告**末尾可选**追加:

```markdown
**lessons (≥0 条,可选)**:
- {本次任务踩到的非显然坑或验证的关键思路,≤ 100 字 / 条}
- {若无新经验,本字段可省略,不要写"无"}
```

判断"是否值得记":
- ✅ 值得记: 数据降级触发条件 / API 怪异行为 / 反偷懒红线 / 验证过的判断框架
- ❌ 不值得记: 显然信息(已在 protocol/skeleton 里) / 临时调试笔记 / 公司特定细节(下家公司用不上)

### 主 agent 处理协议

**完成 sub-agent 后**:
```python
# 1. 提取 lessons
lessons = bash(f"grep -A 100 '\\*\\*lessons' sub_agent_response | grep '^-'")
if lessons:
    # 2. 追加到全局文件(若类别段不存在则新建)
    bash(f"python3 -m scripts.lessons_append --category {sub_agent_name} "
         f"--company {company} --date {yymmdd} --lines '{lessons}'")
```

**启动 sub-agent 前**:
```python
# 注入近 30 天该类别 lessons
recent_lessons = bash(f"python3 -m scripts.lessons_recent --category {sub_agent_name} --days 30")
if recent_lessons:
    sub_agent_prompt = f"## 近 30 天经验提示\n{recent_lessons}\n\n## 任务\n{原 prompt}"
```

(scripts/lessons_append.py + lessons_recent.py 是 v5.1.1 配套实现的小脚本,见下方协议)

### 经验库限制

- 每类别上限 100 条,超过则按时间最旧 5 条被脚本归档到 `output/_global/lessons-archive-{YYYY-MM}.md`
- 单条上限 200 字符;脚本 lessons_append.py 强制截断
- 重复检测:新条目与近 30 天任意一条 cosine similarity > 0.85 时跳过(简单实现:先用 fuzzy match 或直接字串包含)

---

## 7. 版本演进

| 版本 | 范围 |
|:-:|---|
| v5.0 | sub-agent 模板存在 + Agent() 调用方式(形状层) |
| **v5.1** | Agent ID 收集 + Resume + 日志 + 防死锁(§1-§5) |
| **v5.1.1** | **lessons-learned 经验库(§6) + SKILL.md 调度规范风格 + reviewer 拆 3 维度并行** |
| v5.2 (规划) | Phase 2 / Phase 5 sub-agent 化 |
| v5.3 (规划) | 真量化系统(因子模型 / 线性回归 / IC 检验) |
