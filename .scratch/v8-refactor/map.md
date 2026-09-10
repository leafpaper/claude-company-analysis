# Map: company-analysis v8.0 重构

Label: wayfinder:map
Tracker: local markdown(本目录;约定见 wayfinder 本地 tracker 规则)

## Destination

v8.0 重构 spec 定稿:四层瘦身(判断链 / 框架文档 / 报告结构 / 流水线)+ 四个新功能(报告交付形态升级、「赚不赚钱」+红标、增量复查模式、多公司对比/组合视角)的全部设计决策清晰,可经 /to-spec 折叠为可执行 spec。地图只产决策,不动代码。

## Notes

- **质量优先、成本其次**:瘦身只砍冗余;质量与成本冲突时保质量。
- **铁律**:判断链类设计必须在真实公司(**东山精密 002384**)上走完整逻辑链、推出实际判断后才可采纳;表面映射直接拒;每个机制在输出中具名可追溯,不混成浆糊。(源自 v7.0 融框架时的用户反馈)
- **评分约束已解除**:10 维评分允许降格为证据输入,喂给决策内核三分(好公司/好下注/好价格),不再平行给结论。(v7.0 的「评分原样保留」Option B 不再有效)
- **阅读习惯**:结论先行、全说人话(同 Hermes 通知重构的「只要买卖+原因」原则)。
- Skills:grilling 票用 /grilling + /domain-modeling;prototype 票用 /prototype;research 票由 /research 子代理后台解。
- 每会话最多解一张 ticket(research 票除外)。
- 现状基线:v7.1;9 章节报告;9 个 sub-agent;references/ 四份框架文档(scoring-rubric / qualitative-frameworks / valuation-frameworks / investment-decision-core)。

## Decisions so far

<!-- 每张关闭的 ticket 一行:标题链接 + 一句话答案 gist -->

- [机制重叠盘点](issues/01-mechanism-overlap-survey.md) — 真判断只在 4.11 状态/§五赔率/6.4 路径三处,其余(§七 7.1-7.3、§一决断卡、综合评分、定性方向、6.1 快筛)是复述/抄本/已架空的"结论假面";两份真实报告(东山精密/景嘉微)判断链内部零矛盾,但「贵不贵」答约 9 次、框架文档存 6 处矛盾(rubric 双维度表/悬空定性叠加/信号表 vs 行动档位/锚 vs SOTP 超 20% 红线等),3 个 reviewer 中 2 个专职校验抄写一致——收敛空间在砍复述层与结论双轨,证据见 research/01-mechanism-overlap.md
- [判断链收敛方案](issues/02-judgment-chain-convergence.md) — 收敛为「证据层→四问中间层(质地/状态/赔率/路径,各一处权威;质地=筛选信号不进乘法)→决策层一处(三元组乘法+档位封顶规则)→摘要层(机器装配)」;评分数字全删证据归家、定性综合方向删除、快筛并入 audit、锚改区间锚[SOTP,DCF]两端同向、仓位唯一出处=决策层、红旗一处权威+Top3 机器带出、7.1-7.3 与 §一人工抄写删除;C1-C6 六矛盾与 R1-R9 九冗余全部有解;东山精密铁律推演零漂移,见 research/02-dongshan-walkthrough.md
- [红标机制定义](issues/05-red-flag-marking.md) — 红标=纯展示层映射(摘要/装配层,非判断节点):红旗清单唯一权威,🔴🟠红/🟡黄/🟢ℹ️不标,零新增阈值,无红旗的难看数字不标色;「赚不赚钱」面板=菜单(默认五件套+行业扩展)+写手自选 3-5+固定 schema 结构化输出,结论行引用质地子判定①②不自产,ROIC−WACC 不新增;写手提名通道=一张清单两个来源(脚本+提名,结构化落所属节点,同渠道映射进 Top3);东山推演零漂移(商誉对赌提名后 Top3 不变),见 research/05-dongshan-panel.md
- [报告目标结构](issues/06-report-target-structure.md) — 章节=判断链:首页一眼结论(机器装配:决断卡→面板→Top3→3-5句导读)→ ①质地②状态③赔率④路径⑤怎么办 → 附录A-E(财务/对标/舆情资金底稿/红旗总清单/来源缺口);最硬证据制(verdict先行+子判定表+全表下沉附录,数字唯一home+异地必引用→R7死);长度软目标 主体300-400行+章预算(40/70/60/70/60/50);东山 33 小节全量映射零孤儿、主体实测~275行,见 research/06-dongshan-structure.md
- [多公司对比/组合视角的产品形态](issues/04-multi-company-portfolio-form.md) — 多公司对比=产业链同行对比页,答「同行组里钱该放哪家」;同行口径=产业链相关(东山↔中际旭创),锚定发起→自动查候选(Longbridge产业链+库内peer+模型兜底)→用户确认成组;全报告制(缺报告先跑、可分批,不建 peer-lite 管线);产出=各家决断卡机器装配并排+「组内裁决」具名判断节点(排序+每家一句原因,只引用不自产);交付=Inves-Report 独立对比页(视觉归 07);新鲜度=标基准日+超龄陈旧警示+手动重跑;组合视角(跨行业仪表盘/watchlist 联动)划出 v8.0 进 Out of scope
- [交付形态 prototype](issues/07-delivery-prototype.md) — 第二套 B「仪表盘·一眼决断」定稿无杂交(决断卡=verdict 瓦片/面板=stat tiles+红标角标/Top3=风险卡,扫读优先);B2 减压版否决——密度即 B 的价值;手机阅读升为一等场景(瓦片单列重排/表格强制横滚容器/正文子判定表≤3-4列/禁缩字号/390px 走查进 Phase 6 验收);红标三通道(emoji+文字+底纹)与明暗双主题随样张定;样张链接在 ticket 07
- [增量复查模式需求](issues/03-incremental-review-requirements.md) — 彻底取代 --monitor(其内核降格为复查第一阶段「分诊」);产出=新版完整报告+首页「较上版变化」机器装配区块(首句答「阿尔法变了没」),旧版留档;手动触发+被动提醒(披露日+超龄警示,不建守护);固定规则分层重评(状态/赔率必重评、质地默认复用+四条标脏、路径核销、决策层+首页永远机器重装配,成本约全量1/3);全量边界=硬规则(旧结构基线/质地翻转或跨两档)+建议档(>12个月或4次增量);入口 --review,monitor 做重定向;复查后提示一键重装配 04 对比页;东山中报场景双向推演零漂移,见 research/03-dongshan-incremental.md

- [框架文档合并](issues/08-framework-doc-merge.md) — 四份学科文档重组为「1+4 节点制」:judgment-chain 链手册(唯一链真理源+写作规范+消化路径总表)+ node-quality/state/odds/path 四份节点手册,文档边界=节点边界;写手硬边界只读链手册+本节点手册、跨节点只引用 verdict;装配产物 schema 外置代码侧(文档只引用文件名);创业口径(C/D轮/条款/实物期权)划出 v8 随重组删除,SKILL 不再问创业/上市;旧文本直接删(git 即归档);全章节零孤儿映射见 research/08-doc-mapping.md;节点→写手绑定归 09
- [流水线目标架构](issues/09-pipeline-target-architecture.md) — Agent 9→10:data-collector(+增量模式)/ doc-analyst(新,Phase 2 独立化)/ 四节点写手 / decision-writer(⑤+导读)/ reviewer-{logic,delivery} / compare-judge;砍 part1-5+旧 3 reviewer+主 agent 自跑 Phase 2+monitor;写作=依赖图两波(质地∥赔率∥路径→状态→决策),全量/增量共用同一套子集调度;节点 md 内嵌 YAML verdict 块=装配与增量对比唯一数据源,schema 落 scripts/schemas/;附录 A-E 零写手全脚本装配;anti_lazy_lint 重写 v8 lint(杀字数/覆盖率,新增 schema/红旗闭环机检/数字唯一 home/预算 warn/区间锚同向);--review 四段链(证据刷新→triage.py 纯脚本分诊「拿不准即标脏」→标脏子集重跑+复用盖戳→决策必跑+变化区块),状态=runs/{date}/+manifest.json;--compare 轻链=脚本装配+compare-judge;东山全量+中报增量轨迹零孤儿见 research/09-pipeline-dongshan-trace.md

## Status

**🏁 到达目的地(2026-08-16)**:9 张票全部关闭,四层瘦身+四个新功能的设计决策齐备。

**📄 spec 已定稿(2026-08-16)**:[spec.md](spec.md)(Label: ready-for-agent)——九票折叠 + 遗留四项定稿(红标视觉三通道规范/对比页细节[90 天陈旧阈值、组 slug、候选优先级]/面板与红旗 schema 字段/实现切分 8 步顺序)。

**🎫 实现票已切(2026-08-16,用户批准 10 张方案)**:[../v8-implementation/issues/](../v8-implementation/issues/) 01-10,编号即依赖序,全部 ready-for-agent。frontier:01 契约层、02 doc-analyst 独立化(均无阻塞,可并行);08 完成即可发版,09/10(--review/--compare)随后。下一步:/implement 解 frontier 票。

**⚙️ 实现进度**:01 契约层 ✅(2026-08-16, commit 8805cc6)、02 doc-analyst 独立化 ✅(2026-08-17,未提交:agents/doc-analyst.md + SKILL/orchestration/agent-protocol/phase2 调度改写 + install/README/CHANGELOG 同步,东山精密真实数据 dry-run 过 check_phase2;**新 agent 需 install + 重启 Claude Code 才进注册表**)、03 手册层 ✅(2026-08-17:references/ 8→9,judgment-chain 链手册 230 行 + node-{quality,state,odds,path} 四份 106-138 行;旧四份框架文档删除、创业口径随删、SKILL 不再问类型;research/08 的 52 项逐项核对零孤儿;Damodaran 基准表合并唯一一份。**副作用**:v7 管线文件[phase3-part1/3/4、reviewer-valuation、phase3-analysis-report、report-skeleton、report-checklist]仍引用已删文档,v7 全量跑不通,由 04/05/06 重写时消除)。04 装配层 ✅(2026-08-17:red_flags/assembly/assemble_report_v8 三模块 + 46 项装配测试;红旗聚合与 Top3 排序键、跨两档带间距离、翻转判定四条机器规则落盘;契约层追加 current_price/front_page_intro 等可选字段)、07 交付 HTML ✅(2026-08-17:assets/html/report-v8.{html,css} B 仪表盘版式 + build_html v8 通道[结构化件读 assembly.json、正文读 md]+ update_index v8 卡片版式 + 42 项交付测试;红标三通道与反查一套实现[hover 浮层 / 点击直达附录D / title 兜底],明暗双主题对比度按 WCAG 机检,移动端改结构不缩字号[媒体查询零 font-size]。**取舍**:瓦片语气不从 verdict 文本猜——⑤按行动档位、①-④按本节点红旗载荷并在卡上写明旗数;正文红标靠逐字反查、短词不入词表。**浏览器目测 390px 走查仍归 reviewer-delivery**)、06 质量环 ✅(2026-08-18:`scripts/lint_v8.py` 取代 anti_lazy_lint[判定对象换成 run 目录契约,10 条规则:五块 schema / 红旗闭环含 Top3 重算比对 + 🔴 归家 / 数字唯一 home / 区间锚 / 决策字段+致命红旗封顶 / 越权发声 / 外链 / 无记忆性 / 报告与节点同步 = fail,章预算与 🟠 归家 = warn]+ `agents/reviewer-{logic,delivery}.md` 取代旧三 reviewer + `review_loop.py` 重写[FIX 行加 `判断|表述` 类型,脚本直接分诊出 restart_writers / edit_targets / delivery_fixes]+ `phases/phase6-review-publish.md` 重写;build_html v8 通道内置 lint 门控;删 anti_lazy_lint/旧三 reviewer/report-checklist.json[审核标准落在 lint 规则集与 reviewer 定义,不留第二真相源]。test_quality_loop_v8 41 项绿,东山 golden run fail 项全过。**取舍**:🔴 归家 fail / 🟠 归家 warn[文本命中有误判空间,不卡出片];R10「报告与节点同步」是 spec 外补的,专抓修正循环里「改了节点忘重装配」)。05 全量写手管线 ✅(2026-08-18:五个写作 agent[node-{quality,odds,path,state} + decision-writer,各只读链手册+本节点手册、产顶部 YAML 块 + 正文、自跑 verdict_block] + `scripts/node_graph.py` 通用子集调度[全量三波 / 增量 `--nodes` 标脏子集,09 复用同一套] + `phases/phase3-node-writing.md` 主 agent 细则 + SKILL/orchestration/agent-protocol 重写;删 part1-5 写手、phase3-analysis-report、phase7、9 章节骨架与 exec-summary schema、v7 assemble_report;data-collector 补 `red_flags.json` 与 sentiment/data_sources 底稿。东山 dry-run:五块 schema 全过、装配决断卡与 research/02 §6 逐行零漂移、Top3 两源同池、附录挂真实采集产物;test_node_graph 17 项绿。**偏离**:采集产物仍落公司级 `output/{company}/`(collectors 路径写死),run 目录只放判断链与装配产物,生产者与零孤儿映射不变)。

**🌿 分支与提交(2026-08-18)**:v8 全程走 `v8-refactor` 分支(中间态 v7 跑不通,不留在 main),01-07 已按票各一个 commit:8805cc6(01)→98f0896(02)→49a9e59(03)→003e77f(04)→effc571(05)→7fce504(07)→af01b8d(06)。**frontier 现为 08 全量整合上线**(05+06+07 全绿,可发版);08 之后是 09 `--review` → 10 `--compare`。05 与 07 并行时共享 `install.sh` 与 `CHANGELOG.md`,两边各自只提交自己的行,已收口:install.sh assets **4→6**(05 删 templates/ 两份骨架、07 加两份 v8 模板),计数三处(注释/校验条件/失败提示)与磁盘实际一致;CHANGELOG 两条互不覆盖。06 已全绿(commit 见下),08 可发版。

**📌 05 留给 06/09 的接口**:①Phase 6 在 SKILL/orchestration 里标为「v8 质量环施工中」——v7 lint 与 3 个 reviewer 校验 9 章节结构、对 v8 报告会误判,reviewer agent 定义 / `review_loop.py` 的 part 文件签名与 FIX 落点 / `report-checklist.json` 全部留给 06;②修正循环协议已改好(判断类 FIX → fresh-restart 写手,表述类 FIX → 主 agent 改节点 md 正文,改完必重跑装配),06 按此接;③`node_graph --nodes {标脏集合}` + `external_deps`(校验上版复用块是否就位)= 09 的子集调度接口,triage 只需产标脏集合;④`--monitor` 在 SKILL 里暂为退役提示,09 落 `--review` 时替换。

**📌 07 留给 06/08 的接口**:①`build_html` 的 v8 通道不跑 v7 `anti_lazy_lint`——v8 lint 由 06 重写后自行接入(v7 通道的 lint 调用原样保留);②reviewer-delivery 的 390px 与明暗主题走查对象 = `python -m scripts.build_html --company X --run-dir runs/{date}` 的产物;③站点卡片新增 `action_gear` / `next_disclosure_date` 字段,Inves-Report 侧的陈旧警示渲染归 10。

**📌 票 10 已解(2026-09-01)**:`--compare` 产业链对比落地 —— 上半各家决断卡并排(机器搬运,零新判断,超 90 天标陈旧)+ 下半 `compare-judge` 组内裁决(第 10 个 sub-agent,只引用不自产,四条机检);全报告制(缺报告成员列出 + 分批补跑);站点独立对比页 + `data/compare.json` 语义合并;`--review` 收尾问过用户才重装配。**实现票 01-11 全部完成**,剩下的是票 12(R11 多样本标定,卡语料)与两张单独票(红旗 id 归一化 / html-template-guide 仍 v4.3)。

## Not yet specified(留给 /to-spec,不再切票)

- 红标的视觉规范细节(色彩/层级/交互)——07 已定**并入 spec 不切票**:以 B 样张三通道方案为基线,/to-spec 时写成实现规范;悬停反查类交互统一处理
- spec 的切分与实现顺序——由 /to-spec 处理

## Out of scope

- Living Thesis / Hermes 监控联动——新功能候选未入选;若将来要做,v8.0 落地后另起一张图
- 组合视角(跨行业持仓仪表盘、watchlist 联动)——04 grilling 时用户否掉跨行业比较,整体划出 v8.0;将来要做另起一张图(2026-08-12)
- 实现本身——spec 定稿后走 to-tickets / implement 主流程
- stock-monitor(Hermes)侧的任何改动
