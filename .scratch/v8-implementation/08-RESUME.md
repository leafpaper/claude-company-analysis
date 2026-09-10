# 票 08 续跑指引(2026-08-19,重启 Claude Code 后从这里接)

## 为什么要重启

`Agent(subagent_type="node-quality")` 在上一个会话报
`Agent type 'node-quality' not found. Available agents: ... data-collector, phase3-part1..5, reviewer-{narrative,valuation,redflag}`
—— **sub-agent 名册在会话启动时快照,install.ps1 装进去的 v8 九个 agent 要重启才注册**
(skill 描述会热更新,agent 名册不会)。缓存住的 `data-collector` 还是 **v7 定义**,不产
`red_flags.json` / `sentiment.md` / `data_sources.md`,直接用会缺件,所以不能"先跑 Phase 1"。

重启后先验一句:随便起一个 `node-quality` 探针,能解析就往下走。

## 已就绪(不用重做)

| 项 | 状态 |
|---|---|
| `.venv` | `F:\vscode\claude-company-analysis\.venv\Scripts\python.exe`,依赖全 `[OK]`,**这就是 `{PYBIN}`** |
| `check_env` | 通过(含 yaml/jsonschema/markdown 三个新查项);token 走 `config.py` 本地兜底,已实测 Tushare 可用 |
| v8 安装 | `~/.claude/skills/company-analysis` + `~/.claude/agents/company-analysis`(9 个)已是最新工作树版本 |
| v7 备份 | `F:\_claude_backup\company-analysis-v7-skill\`(要回滚就拷回去) |
| 测试 | 247 项全绿(7 skip) |
| 数据层预演 | 东山八个脚本全部实跑通过(修掉了 capital_flow 户数 NaN 崩溃) |
| Inves-Report | clone 在 `F:\vscode\_tools\Inves-Report`(**不是**记忆里的 `C:\Users\Administrator\Inves-Report`);旧账户建的,`git` 前先 `git config --global --add safe.directory F:/vscode/_tools/Inves-Report` |

## 续跑命令

```
/company-analysis 东山精密 002384
```

Step 0 选 `{PYBIN}` 时直接用上面那个 `.venv` 绝对路径(机器上**没有 `py -3`**,裸 `python` 是 Hermes 的 venv、没装依赖)。

输出会落 `C:\Users\tinyb\.claude\output\东山精密\`(config 的 `PLUGIN_ROOT/output` 优先规则;
那目录里还留着 v7 时代 2026-06-22 的产物,v8 不读它们,raw_data 会被新采集覆盖 ——
原件在 `F:\_claude_backup\.claude\output\东山精密\`)。

## 收尾(用户已定的口径)

- 发布:HTML 拷进 `F:\vscode\_tools\Inves-Report\reports\002384_东山精密\分析报告_dashboard.html`
  → `update_index --repo ... --force`(会顺带刷 `reports.data.js`)→ **本地 git commit,不 push**
- 基准日会是 2026-08-19,**与 golden(research/02 的 273 元 / 锚区间 57-89)不同源**,
  所以"零漂移"只能验结构与装配路径,判断数字必然不同 —— 报告里要说清楚,别硬套 golden。
- 票 08 剩下的验收项见 `issues/08-v8-full-integration.md`(已勾掉的别重做)
