# 09 流水线目标架构

Type: grilling
Status: closed (2026-08-16)
Blocked by: 03, 06

## Answer

**Agent 清单 9→10(写手边界=节点边界=手册边界)**:data-collector(照旧+增量模式:脚本全量刷新、只下新增 PDF)/ **doc-analyst(新,Phase 2 文档精析独立化**,增量只喂新增 PDF,主 agent 退回纯调度)/ 四节点写手 node-{quality,state,odds,path}(与 08 四份节点手册一一对应)/ decision-writer(⑤怎么办+首页 3-5 句导读)/ reviewer-{logic,delivery} / compare-judge(04 对比页「组内裁决」具名节点)。**砍掉**:phase3-part1-5、reviewer-{narrative,valuation,redflag}、主 agent 自跑 Phase 2、Phase 7 monitor。

**写作顺序=依赖图两波**:质地∥赔率∥路径 并行 → 状态(四维体检③引用赔率 verdict)→ 决策;写作顺序≠章节顺序,装配脚本排版。全量与增量复查共用同一套「按依赖图跑任意节点子集」调度,不维护两套顺序。

**产物形态=单文件内嵌结构化块**:每节点一个 md,顶部 fenced YAML verdict 块(verdict/子判定表/最硬证据引用/红旗提名/面板自选字段/区间锚同向标记/封顶字段等),正文 verdict 先行+展开段。装配(决断卡/面板/Top3/变化区块)与增量对比**只读 YAML 块**;schema 落 `scripts/schemas/`(node×4+assembly 产物),单文件杀死 md/JSON 双份漂移。

**附录 A-E 零写手全脚本装配**:A/B/C/E 挂 data-collector 整合视图,D=装配脚本合并 audit_report+节点提名(05 两源制)。旧对标/舆情叙事章消失,判断归节点章引用。

**质量环**:anti_lazy_lint 重写为 v8 lint——杀 Rule2 字数下限/Rule3 覆盖率(与上限预算/下沉附录正面冲突),留改 Rule1 外链/Rule6→决策 YAML 字段齐全/Rule7 反例,新增 schema 校验、红旗闭环机检(取代旧 redflag 人工查)、数字唯一 home fail、章预算 warn、区间锚同向标记。LLM reviewer 3→2:**logic**(跨节点引用不重推/影子结论/verdict-正文自洽/最硬证据真硬/叙事 SOTP 与 N 有据)∥ **delivery**(结论先行/人话/07 的 390px 手机走查对成品 HTML);fresh-restart 修正循环+review_loop.py 适配+3 轮上限照旧。

**增量复查 --review 四段链**:R1 证据刷新(两证据 agent 增量模式)→ R2 `scripts/triage.py` **纯脚本分诊**(旧 monitor 对比内核改造;机检标脏四条+硬规则,规则外拿不准一律标脏,宁多重评)→ R3 依赖图跑标脏子集,未重评节点从上版拷贝盖「复用」戳 → R4 决策必跑+变化区块装配(分诊单+YAML diff)+lint+双 reviewer 不打折。

**状态存储=runs/ 目录制+manifest**:`output/{company}/runs/{date}/` 每次一目录(旧 run 整目录即留档);`manifest.json` 公司级状态唯一源(runs 列表 full/incremental、增量计数、上次全量、下次披露日、所属对比组)。

**对比页=独立轻链**:`--compare` 入口;compare_assemble.py 从各家 manifest 取最新 YAML 块机器装配并排卡片+超龄警示;compare-judge 只读各家决断卡产排序+每家一句(过 schema 校验);复查收尾读 manifest 对比组字段提示联动。

**调度文档**(agent-protocol / phase-orchestration / SKILL.md / phases/)随 spec 重写;phase7 文件删除。

**铁律验收**:东山精密全量+2026 中报增量双向场景在新架构上的执行轨迹——每组件唯一生产者、前置票(02/03/05/06/07/08)全部规则有落点、判断与既有推演零漂移,见 [research/09-pipeline-dongshan-trace.md](../research/09-pipeline-dongshan-trace.md)。

## Question

目标报告结构与增量复查需求确定后,流水线怎么切:

- sub-agent 数量与分工(现 9 个:data-collector / phase3-part1-5 / reviewer×3)
- review loop 保留几维、anti_lazy_lint 去留
- 增量复查在架构上怎么支撑:哪些 Phase 可独立重跑、状态存哪
- 质量优先约束下(见地图 Notes),哪些环节是纯冗余可砍,哪些是质量保障必须留

前置:[报告目标结构](06-report-target-structure.md)(输出决定分工)+ [增量复查模式需求](03-incremental-review-requirements.md)(复查需求决定切分粒度)。
