# 02 — doc-analyst 独立化(预重构)

**What to build:** 把 Phase 2 文档精析从主 agent 抽成独立 sub-agent doc-analyst,并在**现行 v7 管线上先跑通**——先把变更做容易,再做容易的变更。主 agent 退回纯调度,doc-analyst 读 PDF 清单产文档精析产物,格式与现行 Phase 2 产物一致,Phase 3 消费无感。v8 里 doc-analyst 是 10 agent 之一;其增量模式(只喂新增 PDF)不在本票,归 09。

**Blocked by:** None — can start immediately.

**Status:** done (2026-08-17)

- [x] doc-analyst agent 定义就位:输入 PDF 清单与公司上下文,输出与现行 Phase 2 产物同格式的文档精析
- [x] 主 agent 调度文档更新:Phase 2 改为调 doc-analyst,主 agent 不再自跑精析
- [x] 用一家已有公司数据走 Phase 2:产物被 Phase 3 正常消费,v7 全量管线仍绿

**实现记录(2026-08-17)**:`agents/doc-analyst.md` 新增(tools=Read/Write/Edit/Bash/Glob/Grep,**disallow WebSearch/WebFetch**=离线纪律,缺料只降级标注不联网补——补料是 Phase 1 的活);6 步执行链(前置检查→盘点→精读 6 高价值 section→用户文档→写 §1-§8→自跑 `check_phase2` 自补 ≤3 轮→回报),响应末尾固定 `**判定**:` 结构含 `**check_phase2**: exit N` 一行。调度侧:SKILL.md(❌清单加"不自跑 Phase 2/不读 PDF"、Phase 2 行改 doc-analyst、9→10 agent、{PYBIN} 传递清单、质量门控行改"读判定+复核")、phase-orchestration Phase 2 段重写为 6 步 Agent checklist、agent-protocol 版本演进登记、phases/phase2 头部标执行者 + Step 6 改"自跑自补 + 主 agent 复核"、README/install.sh/install.ps1/CHANGELOG 同步。

**关键决策**:① **门控双跑**——doc-analyst 自跑自补(不甩锅主 agent),主 agent 收响应后**复核**同一条命令(便宜且确定,不信任自证);红了主 agent 只 fresh-restart,**不自己补写**(否则又变回执行者)。② **产物契约零改动**——仍是 `output/{company}/phase2-documents.md` §1-§8,phase3-part2(§2 利润表变动)/part5(§九 来源)与 `anti_lazy_lint` §九 白名单均无需改;v8 的 `evidence-documents.md` 更名归 05/08。③ doc-analyst 保留 Edit(只准 Edit 自己那一个文件,写进严禁事项)——门控补写要打补丁,整篇 Write 太贵。

**验收(东山精密真实数据 dry-run)**:本会话无法真调 `subagent_type="doc-analyst"`(新 agent 未进本次会话注册表,需 install + 重启 Claude Code),故**照 doc-analyst.md 的指令逐步执行**跑通:`C:\Users\tinyb\.claude\output\东山精密\raw_data` 5 个 PDF/3 份报告(去重),section 命中矩阵显示 **3 份报告的 `income_statement_changes` 全部未命中**(季报无此表/摘要无附注/年报全文该表在附注第十节 regex 未覆盖)——正好走通"回原件补读"降级路径:§2 改用主要会计数据表同比列 + 分季度表 + 非经常明细三处原文重建,9 行带 `[PDF:]`。产物 `check_phase2` **exit 0**(R1 ✅ / R2 9 行 / R3 12 行);golden 旧产物回归同样 exit 0;全测试套件 66 项 3 错(均为本机缺 pandas 的既有环境问题,与本票无关)。dry-run 产物留在 scratchpad,**未覆盖用户 output 下的 golden**。

**顺手修的**:① `scripts/check_phase2.py` 强制 UTF-8 stdout——报告含 ✅/❌,Windows GBK 控制台 `print` 抛 `UnicodeEncodeError` → 退出码 1,doc-analyst 会误读成"门控红了"空转 3 轮(本机实测复现)。② install.sh 校验期望 scripts 25→27(票 01 把 verdict_block/manifest 加进下载列表但没同步计数,现状会误报"安装不完整")。

**遗留给用户**:新 agent 要生效需 `powershell -ExecutionPolicy Bypass -File .\install.ps1` 重装 + 重启 Claude Code(`~/.claude/agents/company-analysis/` 目前仍是 9 个)。同类隐患:其余 26 个脚本仍无 UTF-8 stdout 兜底,本票只修了 Phase 2 门控这一个(不扩散改动),要不要统一下沉到 `scripts/__init__.py` 留给票 08 决定。
