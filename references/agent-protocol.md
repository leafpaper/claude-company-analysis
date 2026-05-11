# Agent 调度协议 (v5.1.3)

主智能体(SKILL.md)与所有 sub-agent 之间的统一调度规范。**已对照 Claude Code 真实工具 schema 修订** — v5.1.0 ~ v5.1.2 的 `Agent(resume=...)` / ID 探测 / 伪函数协议**已删除**,因为 Agent 工具实际不支持。

---

## 1. Agent 工具真实 Schema(必读)

`Agent` 工具的合法参数(来源: 当前 Claude Code 实际 schema):

| 参数 | 类型 | 说明 |
|---|---|---|
| `description` | string | 短描述(3-5 词),给 UI 显示 |
| `prompt` | string | 给 sub-agent 的任务 prompt(必填) |
| `subagent_type` | string | sub-agent 类型(如 `data-collector`)(必填) |
| `run_in_background` | bool | 后台跑(true)/ 前台等(false) |
| `isolation` | string (可选) | `"worktree"` 创建临时 git worktree |
| `model` | string (可选) | 覆盖 sub-agent 模型 |

**⚠️ `Agent` 工具没有以下参数**(v5.1.0-v5.1.2 错误地引用过它们):
- ❌ `resume` — 不存在。每次 `Agent()` 调用都启动 fresh sub-agent
- ❌ `agent_id` — 不存在

文档原话:**"A new Agent call starts a fresh agent with no memory of prior runs."**

---

## 2. Fresh-Restart with Context Injection 协议

由于没有 Resume 能力,修正循环用**"启动新 sub-agent + prompt 注入历史"**实现。

### 原则

1. 状态持久化到**文件**(`output/{company}/reviewer_responses/round_N_*.md` 等),不靠 sub-agent context 记忆
2. 修正时启动**同 subagent_type** 的全新 sub-agent
3. prompt 必须包含:
   - 任务描述(同首次,从 sub-agent 模板)
   - 关键上下文输入路径(主报告 / artifacts dir)
   - 上轮历史摘要(判定 + FIX 列表 / 已修改文件路径)

### 示例: Phase 6 reviewer Round 2

```python
# 主 agent 已存好 round_1 响应到文件 + 应用过 FIX + 重 assemble 完成
prev_fix_md = bash("cat output/{company}/reviewer_responses/round_1_merged_fix.md")

Agent(
    subagent_type="reviewer-narrative",
    run_in_background=True,
    description="reviewer-narrative round 2",
    prompt=f"""评审 output/{company}/{company}-analysis-{date}.md 维度 1 叙事一致性。
artifacts_dir = output/{company}/

★ 这是 Round 2 重审。上一轮判定 FAIL,主 agent 已按以下 FIX 修过 phase3-partN.md 并重 assemble:

{prev_fix_md}

请只看当前文件状态(忽略上轮原报告),重新独立评审本维度 5 项检查。"""
)
```

### 多花的 token 是值得的

Fresh-restart 每次重传完整任务描述 + 上轮 FIX(~500-2000 token),换来**确定性能跑** — 比 Resume 协议(不存在)更可靠。

---

## 3. main-log.md 双层日志协议

### 位置

`output/{company}/main-log.md`,主 agent 在 Step 2(创建输出目录)立即创建。

### 格式

每行 `- {yymmdd hhmm} {事件}`,时间精确到分,例如 `260504 1430`。

### 强制日志事件清单

主 agent 在以下时点必须用 `Edit` 工具追加日志:

| 时点 | 日志条目 |
|---|---|
| 分析启动 | `- {ts} ━━━ 开始分析 {company}({ticker}) ━━━` |
| Phase N 启动 | `- {ts} 启动 Phase N <由谁执行>` |
| sub-agent 完成 | `- {ts} Phase N <sub-agent 名> 完成,判定 <PASS/FAIL/降级>` |
| reviewer 每轮 | `- {ts} reviewer Round N 综合判定 <PASS/FAIL>,FIX 数 M` |
| 修正循环每轮 | `- {ts} Round N FIX 应用完成,重 assemble 完成` |
| 转人工 | `- {ts} ⚠️ <原因>,转人工` |
| 分析完成 | `- {ts} ━━━ 完成 {company} 分析 ━━━` |

### 未来增强(v5.2 规划)

`~/.claude/settings.json` 配置 `SubagentStop` hook 自动追加 main-log.md,消除主 agent 漏写风险。
配置示例(待 verify 环境变量):

```json
{
  "hooks": {
    "SubagentStop": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "test -n \"$CLAUDE_COMPANY\" && echo \"- $(date +'%y%m%d %H%M') subagent stopped\" >> \"output/$CLAUDE_COMPANY/main-log.md\" || true"
      }]
    }]
  }
}
```

---

## 4. reviewer 修正循环协议(v5.1.3 新)

完整步骤见 `references/phase-orchestration.md` §Phase 6 Part A.5。本节只列**关键不变量**。

### 不变量

1. **3 个 reviewer 并行**(`run_in_background=True`),不是串行
2. 主 agent **必须保存** 3 份响应到 `output/{company}/reviewer_responses/round_N_{reviewer}.md`(不依赖 context)
3. **判定 + FIX 合并** 由 `scripts/review_loop.py` 处理,主 agent 只看 JSON 输出
4. **FIX 应用** 由主 agent 用 `Edit` 工具做(脚本不改 part 文件,因为需要 LLM 语义理解)
5. **diff signature 对抗检测**:Round N+1 的 5 个 part md5 拼接 == Round N → 自动转人工

### round 上限

3 轮(初次 + 2 次重审)。round 3 仍 FAIL 或 diff_repeat → 转人工 + 输出累计 FIX。

---

## 5. Sub-agent 自检报告统一结构

所有 sub-agent 响应**末尾**必含:

```markdown
### {Phase N / Part N} 完成报告
**判定**: PASS / FAIL / 部分降级
**artifacts**: {路径 1}, {路径 2}, ...
**降级标注**: {若有 / 否则"无"}
**(可选)精简版片段**: {若 sub-agent 需要主 agent 拼到主报告某处,直接给可复制 markdown}
```

主 agent 用 `grep "^\*\*判定\*\*:"` 提取判定。

**reviewer 特例**(3 个 reviewer 用不同 schema):
```markdown
### 维度 {N} {名称}: PASS / FAIL

### FIX 指令(FAIL 时必填,每条单行)
- [FIX-P{1-5}-§{X}] {问题} → {建议}
```

`review_loop.py` 已经处理两种 schema(grep `^### 维度` 或 `^### 总体`)。

---

## 6. lessons-learned 跨任务经验库

### 目的

sub-agent 完成后,主 agent 提取 `**lessons**` 字段追加到全局经验库;下次同类 sub-agent 启动前注入近 30 天 lessons。

### 位置

`output/_global/lessons-learned.md`(跨公司共享)

### 主 agent 处理协议

完成 sub-agent 后:
```bash
# 1. 提取 lessons (用 grep 在 sub-agent 响应文件里)
lessons=$(grep -A 100 '^\*\*lessons' sub_agent_response.md | grep '^-' | sed 's/^- //')

# 2. 追加到全局(如有)
test -n "$lessons" && python3 -m scripts.lessons_manager append \
    --category <sub_agent_name> --company <company> --date <yymmdd> \
    --lines "$lessons"
```

启动新 sub-agent 前:
```bash
# 注入近 30 天 lessons
recent=$(python3 -m scripts.lessons_manager recent --category <sub_agent_name> --days 30)
# 把 $recent 拼到下次 Agent() 的 prompt 头部
```

---

## 7. 失败处理协议

### Sub-agent 单点失败

- **首次启动 FAIL** → fresh-restart 1 次(prompt 注入"上轮 FAIL 原因"),仍失败 → 转人工
- **reviewer 修正循环 FAIL** → 见 §4 round 上限规则
- **assemble_report.py / anti_lazy_lint 退出码非 0** → 主 agent 看 stderr 决定是 Edit 修复还是转人工

### 转人工触发

主 agent 用 `PushNotification` 通知用户 + 保存累计上下文到 `output/{company}/_failure_report.md`:
- 累计 FIX 列表
- 各 sub-agent 响应路径
- 当前 main-log.md tail 30 行
- 建议下一步(由用户决定继续 / 重启 / 放弃)

---

## 8. 工具不可用 fallback

| 期望工具 | 当前 schema | Fallback |
|---|---|---|
| `Agent(resume=...)` | ❌ 不存在 | Fresh-restart + 注入历史 |
| `SendMessage(to=, message=)` | ❌ ToolSearch 未发现 | 同上 |
| SubagentStop hook | ⚠️ 待 verify 环境变量 | 主 agent Edit 工具手动写 main-log.md |
| `find -printf` | ❌ macOS BSD find 不支持 | 用 `ls -lt` + `awk`(若需要时间排序) |

---

## 9. 版本演进

| 版本 | 范围 |
|:-:|---|
| v5.0 | sub-agent 模板 + Agent() 调用方式 |
| v5.1.0-1 | (失败)假设 Resume / ID 探测 / 伪函数协议 — 实际 API 不支持 |
| **v5.1.3** | **删除不存在的 API,改 Fresh-Restart + Context Injection + 真脚本 review_loop.py** |
| v5.2 (规划) | SubagentStop hook 自动写日志 / Phase 2-5 sub-agent 化 |
| v5.3 (规划) | 真量化系统(因子模型 + IC 检验) |
