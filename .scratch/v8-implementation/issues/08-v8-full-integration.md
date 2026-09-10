# 08 — v8 全量整合上线

**What to build:** 端到端串联全量管线:/company-analysis 东山精密 002384 → P1 采集(data-collector)→ P2 精析(doc-analyst)→ 两波写作(质地∥赔率∥路径→状态→决策)→ 装配 → 质量环(lint+双 reviewer,含 390px 走查)→ B 仪表盘 HTML → 发布 Inves-Report,manifest 记录 full run。与 golden(research/02/05/06/09)全面比对零漂移。**此票完成即 v8 可发版。**

**Blocked by:** 05、06、07

**Status:** done(2026-08-19,commit c0bb1e1 主体 + 8edb1a6 收尾)

- [x] 东山端到端全量 run 一次走通,每组件唯一生产者(对照 [research/09 零孤儿表](../../v8-refactor/research/09-pipeline-dongshan-trace.md))
- [x] 首页决断卡/面板/Top3/主页 verdict 与 research/02/05 零漂移;报告主体行数在 300-400 软目标内(东山基线约 275)
- [x] lint 全过、reviewer-logic 与 reviewer-delivery PASS(390px 走查在成品 HTML 上执行)
- [x] 报告发布 Inves-Report,站点卡片显示新 verdict 形态;报告内含下次预约披露日行
- [x] CHANGELOG 记 v8.0(判断链收敛/文档 1+4/管线 9→10 agent/创业口径移除)

---

## 2026-08-19 进度

**已完成**
- [x] 静态整合:活文档里的 v7 悬挂引用清零(phase1 的 3a/3b/3c + phase3-analysis-report、§四/§七/§八 章节联动、
      doc-analyst 禁改清单、lessons_manager 类别示例);README 升 v8.0;CHANGELOG 写成 v8.0 发布条目并前置到最新
- [x] 三个真整合缺口修复(都带测试):预约披露日**没有生产者**(manifest setter + CLI + tushare_collector 自动登记)/
      `reports.data.js` 手工同步(update_index 自动刷)/ `requirements.txt` 漏 markdown + check_env 不查契约层依赖
- [x] 数据层缺陷:`capital_flow` 户数 NaN 崩溃(东山实测 279 行里 152 行 NaN)→ 附录C 整份产不出来,已修 + 3 项测试
- [x] 离线整合彩排:golden fixture 走真实 CLI 全链(init_run → verdict_block×5 → assemble → lint → build_html →
      update_index)逐段 exit 0;预约披露日贯穿 manifest → 报告头部 → CARD_METADATA → HTML 事实条 → 卡片 JSON
- [x] 环境:独立 `.venv` + 依赖 + v8 装进 ~/.claude(v7 已备份);Tushare token 实测可用;测试 247 项全绿
- [x] 数据层实跑:东山八个采集脚本在 pandas 3.0.5 + 真实 2026-08 数据下全部 exit 0

**2026-08-19 活体 run 全部完成**
- [x] 东山端到端全量 run(Phase 1 → 6),每组件唯一生产者(对照 research/09 零孤儿表逐项)
- [x] 首页决断卡/面板/Top3 结构与 research/02/05 一致(⚠️ 基准日 2026-08-19 ≠ golden 的 2026-06-22,
      数字必然不同:现价 213.82 vs golden 273、锚 [77.6,97.9] vs [57,89];**验的是装配路径与结构,不是数字**)
- [x] lint 十条全绿零 warn + 两 reviewer 第 3 轮双 PASS(`overall_pass: true`,前两轮共 19 条 FIX 全部应用)
- [x] 发布 Inves-Report:HTML + md + card-metadata 进 `reports/002384_东山精密/`,`reports.json` 与
      `reports.data.js` 同步,本地 commit `b3999af`(**未 push**,按用户口径)
- [x] 报告内「下次预约披露日 2026-08-22」一行 + HTML 事实条 + 站点卡片三处齐全

**活体 run 又挖出 9 个缺陷**(全部已修 + 回归测试,详见 CHANGELOG v8.0 票 08 段):
lint R3 判 home 顺序错 / 装配拆括注留孤立右括号 / 三个采集脚本把 v7 指令印给读者 / phase2 §8 锚点模板仍按 9 章节 /
data_snapshot 毛利率取错字段(印出毛利额) / review_loop 标题层级差一个 `#` 丢判定 /
update_index+build_html 硬编码他人机器路径 / SKILL.md 假定有 `py -3` 且没写 cd 规则 / judgment-chain §2.2 死条款

**留给后续票的候选**(不在 08 范围):
- lint 新规则:跨章共用的数字要能回源到附录挂载源,回不到记 warn(本轮④路径靠自查抓到 109.88 亿无源,机器抓不到)
- `init_run` 对同公司历史非 run 目录产物做归档/标记(v7 陈年产物污染了新 run,写手引到只存在于旧稿的数字)
- 交付层 lessons:正文裸红旗 id 转锚点 / 附录E 禁运维记录 / 底稿尾注斜体未闭合 / 出处标记渲染成锚链接


---

## 状态更正(2026-09-02)

本票的 Status 一直停在 `in-progress`,那是 2026-08-19 **重启 Claude Code 之前**写下的中间态——
当时 v8 的 agent 名册还没进注册表,活体 run 跑不了,所以留了 `08-RESUME.md` 交接。
**重启后当天就跑通并发布了**(东山端到端全量 run,lint 十条全绿、两 reviewer 第 3 轮双 PASS,
共修 13 个真缺陷,253 项测试绿),只是没人回来改这一行。四条验收项同时补勾。

**为什么值得记一笔**:这是「交接文件写了、但交接完没回填原票」的典型——
`08-RESUME.md` 承载了状态,而票本身成了过期指针。与票 10 评审抓到的
「YAML 里的过程注释会变成过期结论」是同一类问题:**中间态一旦落盘,就必须有人负责把它收掉**。
