# Agent 调度协议 (v8.0)

主智能体(SKILL.md)与所有 sub-agent 之间的统一调度规范。**已对照 Claude Code 真实工具 schema 修订** — v5.1.0 ~ v5.1.2 的 `Agent(resume=...)` / ID 探测 / 伪函数协议**已删除**,因为 Agent 工具实际不支持。

**v8.0 的 sub-agent 名册**(9 个):`data-collector` / `doc-analyst` / `node-quality` / `node-odds` / `node-path` / `node-state` / `decision-writer` / `reviewer-logic` / `reviewer-delivery`。旧的 `phase3-part{1-5}` 五个写手随判断链收敛删除;旧的 `reviewer-{narrative,valuation,redflag}` 随质量环重写删除(抄写一致性校验已无对象,红旗闭环改机检)。

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

1. 状态持久化到**文件**(`{run_dir}/reviewer_responses/round_{N}_{logic,delivery}.md` 等),不靠 sub-agent context 记忆
2. 修正时启动**同 subagent_type** 的全新 sub-agent
3. prompt 必须包含:
   - 任务描述(同首次,从 sub-agent 模板)
   - 关键上下文输入路径(主报告 / artifacts dir)
   - 上轮历史摘要(判定 + FIX 列表 / 已修改文件路径)

### 示例: 节点写手 schema 门控失败后的重启

```python
# 主 agent 复核 verdict_block 时拿到报错原文(sub-agent 自证 PASS 也不算数)
Agent(
    subagent_type="node-odds",
    run_in_background=False,
    description="node-odds retry",
    prompt=f"""重写③赔率节点。
run_dir       = output/{company}/runs/{date}/
artifacts_dir = output/{company}/
company={company} ticker={ticker} market={market} date={date} PYBIN={PYBIN}

★ 这是重跑。上一轮 {run_dir}/nodes/node-odds.md 未过 schema 校验:

anchor_range: 'divergence_note' is a required property
sub_verdicts/0/hardest_evidence/0: 'mechanism' is a required property

请只看当前文件状态,按 references/judgment-chain.md + references/node-odds.md 重写并自跑
verdict_block 校验通过后再回报。"""
)
```

**修正循环的落点(v8)**:reviewer 的 FIX 指向**节点 md**(`runs/{date}/nodes/node-{node}.md`),不是已删除的 `phase3-partN.md`。判断本身(YAML 块的 verdict / 子判定)由**写手 fresh-restart 改**,主 agent 不手改;纯文字表述类 FIX 才由主 agent 用 Edit 改正文。改完必须重跑 `assemble_report_v8` + `lint_v8`(lint 的 R10 专抓「改了节点没重装配」)。

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

## 4. 两类循环:波次门控 与 reviewer 修正

### 4.1 Phase 3 波次门控(v8)

1. 每波的写手用同一批 prompt 字段(`run_dir` / `artifacts_dir` / `company` / `ticker` / `market` / `date` / `PYBIN`),第一、二波各两个 `run_in_background=True` 并行,第三波前台。
2. **主 agent 复核 schema**:`{PYBIN} -m scripts.verdict_block --schema node-X --file {run_dir}/nodes/node-X.md`;退出 0 才进下一波(sub-agent 的自证不算数)。
3. 波次顺序由 `{PYBIN} -m scripts.node_graph`(全量 `--all` / 增量 `--nodes …`)算出,不手写。
4. 单个写手最多 fresh-restart 1 次;仍红 → 转人工,**不许主 agent 手改 YAML 块**。

### 4.2 reviewer 修正循环(v8:机器门控 + 两 reviewer)

完整步骤见 `phases/phase6-review-publish.md`。**关键不变量**:

1. **机器先于人**:`{PYBIN} -m scripts.lint_v8 --run-dir {run_dir}` 退出 0 之后才派 reviewer
2. **两个 reviewer 并行**(`reviewer-logic` ∥ `reviewer-delivery`,`run_in_background=True`),不是串行
3. 主 agent **必须保存**每份响应到 `{run_dir}/reviewer_responses/round_{N}_{logic,delivery}.md`(不依赖 context)
4. **判定 + FIX 分诊** 由 `scripts/review_loop.py` 处理,主 agent 只看它的 JSON(`overall_pass` /
   `restart_writers` / `edit_targets` / `delivery_fixes` / `diff_repeat`)
5. **FIX 应用**:`判断` 类 → fresh-restart 对应节点写手(主 agent **不改 YAML 块**);`表述` 类 → 主 agent 用
   `Edit` 改节点 md 正文;`delivery` 落点 → 改 HTML 模板。三类改完都要**重跑装配 + 重跑 lint**
6. **diff signature 对抗检测**:Round N+1 的五个节点 md md5 拼接 == Round N → 自动转人工

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

主 agent 直接从响应文本读出 `**判定**:` 字段(响应就在你的上下文里, 无需 shell)。

**节点写手特例**(五个写手用同一骨架,字段随节点略有差异,详见各 agent 定义):

```markdown
### {①质地/②状态/③赔率/④路径/⑤决策}节点 完成报告
**判定**: PASS / FAIL / 部分降级
**verdict**: {本节点 verdict 取值域之一}——{一句话}
**artifacts**: {run_dir}/nodes/node-{node}.md ({N} 行正文)
**schema 校验**: exit 0 [重跑 {k} 轮]
**降级标注**: 无 / {缺什么、什么事件能补上}
```

主 agent 读 `**判定**:` 与 `**verdict**:` 两行即可(verdict 之后要与决断卡对照);**不读节点 md 全文**。

**reviewer 特例**(两个 reviewer 用同一 schema):
```markdown
### 维度 {1 判断链逻辑 / 2 可读性与交付}: PASS / FAIL

### FIX 指令(FAIL 时必填,每条单行)
- [FIX-{node}-{kind}] {问题≤30 字} → {建议≤60 字}
```

`node` ∈ `quality` / `state` / `odds` / `path` / `decision` / `front`(首页导读)/ `delivery`(HTML 交付);
`kind` ∈ `判断`(→ fresh-restart 写手)/ `表述`(→ 主 agent Edit 正文)。**这两个字段决定修正循环走哪条路**,
写错了会把措辞问题送去重跑写手、把判断问题交给主 agent 手改。`review_loop.py` 按此正则解析并分诊
(判定行 `^### 维度` 或 `^### 总体` 两种写法都认)。

---

## 6. lessons-learned 跨任务经验库

### 目的

sub-agent 完成后,主 agent 提取 `**lessons**` 字段追加到全局经验库;下次同类 sub-agent 启动前注入近 30 天 lessons。

### 位置

`output/_global/lessons-learned.md`(跨公司共享)

### 主 agent 处理协议

完成 sub-agent 后:
```
# 1. 提取 lessons (直接从 sub-agent 响应文本读出 **lessons** 字段下的列表行, 响应就在你的上下文里, 无需 shell)
lessons=<从响应文本读出的 lessons 列表行>

# 2. 追加到全局(如有)
test -n "$lessons" && {PYBIN} -m scripts.lessons_manager append \
    --category <sub_agent_name> --company <company> --date <yymmdd> \
    --lines "$lessons"
```

启动新 sub-agent 前:
```
# 注入近 30 天 lessons
recent=$({PYBIN} -m scripts.lessons_manager recent --category <sub_agent_name> --days 30)
# 把 $recent 拼到下次 Agent() 的 prompt 头部
```

---

## 7. 失败处理协议

### Sub-agent 单点失败

- **首次启动 FAIL** → fresh-restart 1 次(prompt 注入"上轮 FAIL 原因"),仍失败 → 转人工
- **reviewer 修正循环 FAIL** → 见 §4 round 上限规则
- **`assemble_report_v8` / `lint_v8` 退出码非 0** → 主 agent 看 stderr 与规则名决定:判断类 fresh-restart 写手,表述类自己 Edit,仍不行转人工

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
| **v7.2** | **Phase 2 抽成 `doc-analyst` sub-agent(9→10),主 agent 退回纯调度;门控 sub-agent 自补 + 主 agent 复核** |
| **v8.0** | **Phase 3 五个 part 写手 → 判断链四节点写手 + decision-writer;依赖图两波调度(`node_graph`)+ 每波 `verdict_block` schema 门控;写手响应加 `**verdict**:` 字段;修正循环落点改为节点 md** |
| **v8.0 质量环** | **reviewer 3→2(`reviewer-logic` ∥ `reviewer-delivery`);机器门控 `anti_lazy_lint` → `lint_v8`(判定对象=节点块+装配产物);FIX 行加 `kind` 字段做判断/表述分诊** |
| v5.2 (规划) | SubagentStop hook 自动写日志 |
| v5.3 (规划) | 真量化系统(因子模型 + IC 检验) |
