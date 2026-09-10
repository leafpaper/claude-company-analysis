# 03 — 手册层:judgment-chain 链手册 + 四节点手册

**What to build:** 「1+4 节点制」框架文档。judgment-chain 链手册=链结构唯一真理源(总公式/四问定义/决策层三元组×封顶×六档行动档位映射/摘要层装配规则/写作规范:人话词典+最硬证据制+黑白分割纪律+证据质量门控/消化路径总表);node-quality / node-state / node-odds / node-path 四份节点证据手册,每份头部「你是谁/读什么/产什么」。文档边界=判断节点边界;写手只读链手册+本节点手册,跨节点只引用 verdict;schema 只引用 01 的文件名、不复制字段表。旧四份框架文档(scoring-rubric/qualitative-frameworks/valuation-frameworks/investment-decision-core)按 [research/08 零孤儿映射](../../v8-refactor/research/08-doc-mapping.md) 消化后直接删除(git 即归档),创业口径随删。

**Blocked by:** 01(手册引用节点 schema 文件名与字段边界)

**Status:** done (2026-08-17)

- [x] 链手册含六档行动档位映射表(承接旧 investment-decision-core)、封顶规则(任一致命红旗→回避)、区间锚[SOTP,DCF]两端同向规则(不同向→「取决于口径」+保守一档)
- [x] 四份节点手册与 01 的四个节点 schema 一一对应;消化纪律(只读两份/跨节点只引 verdict/机制文本一处安家)写明
- [x] research/08 映射表逐项核对:52 项全有家或有据可删,零孤儿;Damodaran 基准表等文档级重复消除
- [x] 旧四份框架文档删除,SKILL 不再问创业/上市,CHANGELOG 记一笔

**实现记录(2026-08-17)**:`references/` 新增 5 份、删除 4 份(8→9 个 md)。judgment-chain.md 230 行(§1 总公式与四问定义[verdict 取值域表/质地不进乘法/一处权威表]、§2 决策层[三元组→六档映射、封顶规则、区间锚两端同向、三分结论、右尾纪律、该等什么/证伪引用、仓位唯一出处、五弊端]、§3 摘要层装配[决断卡/面板/Top3/红标纯展示层/提名通道 + schema 文件名表,零字段复制]、§4 写作规范[人话词典/结论先行+最硬证据制/黑白分割/证据质量门控/数字唯一 home+章预算/禁止项/BEFORE→AFTER]、§5 消化路径总表 + 增量模式读法);node-quality 138 / node-state 130 / node-odds 106 / node-path 113,每份头部「你是谁/读什么/产什么」+ verdict 取值域 + 跨节点引用行表 + 红旗提名段。消化负担:任一写手读 ~350 行(旧 part3 读 3 份 ~1200 行)。

**零孤儿核对(逐项过 research/08 的 52 项)**:rubric 19 项——维1→quality①(LTV/CAC 等 C/D 轮指标随创业口径删)、维2→state 赛道右尾、维3/6→quality③、维4→state 成长标尺、维5→quality④(上市追加的内部人持股/薪酬/独董并入「治理」子项)、维7→quality⑤偿债标尺表 + path 左尾、维8→path 风险标尺表(做空比率/降级/miss/审计意见并入)、维9→odds、维10 上市版回报→path §3;锚点/加权/信号表/定性叠加/早期适配全删;证据质量门控与「信息不足」→链手册 §4.4;Damodaran 与财务基准两表分别归 odds §4(合并唯一一份)与 quality 附表。qualitative 8 项——三框架分别归 quality③④与 state §6,综合方向 verdict 与三段式模板删,黑白分割/禁止项→链手册 §4.3/§4.6。valuation 14 项——三件套+区间锚归 odds §1/§2(20% 红线废除写在链手册 §2.4),证据菜单归 odds §3,剥离清单归 path §1(odds 放引用行),实物期权/条款/退出瀑布删。decision-core 11 项——总公式/决策合成/右尾纪律/写作规范→链手册,1.x→state、2.x→odds、3+4 左尾→path,决断卡与四维体检模板删(字段外置 schema),λ 监控段改写为「接增量复查分诊」,写手对照表拆进五份手册头部 + §5 总表。

**连带改动**:install.sh 参考文档 8→9(名单换成 1+4,REF_COUNT 期望同步);SKILL.md 输入确认删「类型(创业/上市)」与 `{type}` 变量 + 参考索引改指手册层 + 消化纪律一行;README.md 目录树与两处 investment-decision-core 链接改指 judgment-chain;CHANGELOG 加 `[v8.0-dev]` 段(含四份旧文档的逐章去向,git 历史即归档)。

**遗留(交给后续票,本票不动)**:v7 管线文件仍引用已删的四份文档——`agents/phase3-part{1,3,4}.md`、`agents/reviewer-valuation.md`、`phases/phase3-analysis-report.md`(9 处)、`assets/templates/report-skeleton.md`、`assets/validation/report-checklist.json`。这些在 05(写手管线)/04(装配)/06(质量环)重写时一并消除;在那之前 v7 全量管线跑不通(旧写手会 Read 到不存在的文件),这是 spec「1-6 合成才可发版」的预期中间态。

**并行会话提醒**:本票落盘时另一会话刚完成 ticket 02(doc-analyst,v7.2),working tree 里有其未提交改动(SKILL/README/install.sh/CHANGELOG/phases/agent-protocol/phase-orchestration/check_phase2)。本票只 stage 自己的路径,未碰对方文件的其他部分。
