# 09 流水线推演:东山精密在目标架构上的执行轨迹

> 铁律验收:09 不产新判断(链在 02/03/05/06 已验),本推演验证的是**生产方式**——
> 每个判断/组件在新架构里有且只有一个生产者,全量与增量双场景零孤儿、判断零漂移。
> 判断内容全部取自 research/02(全量)与 research/03(中报增量)的已验推演。

## A. 全量 run 轨迹(/company-analysis 东山精密 002384)

| 阶段 | 执行者 | 东山实际产物 |
|---|---|---|
| P1 采集 | data-collector | `runs/{date}/raw_data/` + data_snapshot / audit_report(2🟠 估值红旗:PB 22.09 近1年100%分位、PB/ROE 错配 25.7x;+2🟡)/ peer_analysis / capital_flow / 完整度报告;manifest.json 初始化(type=full) |
| P2 精析 | doc-analyst(新) | evidence-documents.md(年报 6 高价值 section:并表利润口径、关联交易、非经常损益) |
| P3 第一波(并行) | node-quality ∥ node-odds ∥ node-path | quality:「部分好——真卡位+平庸财务」+面板自选字段提名+红旗提名(05 商誉对赌场景);odds:「极贵——买完完美未来」+区间锚[57,89] 两端同向标记+ΔP 引附录C+2🟠2🟡 归家;path:「高尾险·扛不住」+高信仰 5/5 引附录C 拥挤度+证伪/左尾清单 |
| P3 第二波 | node-state | 「↑变好但未确认,注意力先行」;四维体检③引用 odds verdict、④引用附录C;「该等什么」=中报+谷歌验证(一处权威) |
| P4 决策 | decision-writer | 三元组 部分是·否·否 → 先观察等证据临界,期权小仓≤2-3%;封顶检查:无🔴不触发;首页导读 3-5 句 |
| P5 装配 | assemble 脚本 | 首页决断卡 5 行(=research/02 §决断卡逐行)/赚钱面板(quality 提名字段+红标映射)/Top3(audit+提名机器带出)/附录A-E 挂载;主体 ~275 行(06 实测) |
| P6 质量环 | v8 lint → reviewer-logic ∥ delivery | lint:5 个 YAML 块 schema 校验、红旗闭环机检(2🟠2🟡 各一处归家+Top3)、数字唯一 home(273 元只在赔率章权威)、区间锚同向标记✓;reviewer 双维 PASS |
| P7 发布 | build_html + push | HTML(B 仪表盘样式)+ manifest 更新 |

**首页/章节 → 生产者零孤儿表**(06 目标结构逐项):

决断卡/面板/Top3 = assemble 脚本(吃 5 个 YAML 块 + 附录D 清单)· 导读 = decision-writer · ①质地 = node-quality · ②状态 = node-state · ③赔率 = node-odds · ④路径 = node-path · ⑤怎么办 = decision-writer · 附录A = data_snapshot(脚本)· 附录B = peer_analysis(脚本)· 附录C = capital_flow+舆情节(脚本)· 附录D = audit_report ⊕ 节点提名(merge 脚本)· 附录E = 完整度报告(脚本)。**无一处需要已删除的 part1-5 / 旧 reviewer / 主 agent 写作。**

## B. 增量 run 轨迹(2026 中报双向场景,判断取自 research/03)

**情景 1(兑现不足)**:R1 data-collector 增量模式刷新脚本+只下中报 PDF,doc-analyst 只喂中报;R2 triage.py:标脏条1(年报)不触发、条4(最硬证据变号:放量证据未兑现)→ 分诊单=状态/赔率/路径必重评(本就必重评)、质地复用;R3 依赖图跑 {odds ∥ path} → state,quality 的 YAML 块从上版 run 拷贝盖「复用」戳;R4 决策重跑:状态翻转 → 档位 观察→回避;变化区块=新旧 YAML diff,首句「阿尔法:变了——排队论据兑现不足」;lint+双 reviewer 不打折;manifest 增量计数+1。

**情景 2(超预期)**:triage 条4 触发(并表利润跳档)→ 质地标脏重评;若业务结构跨档 → 硬规则 → 首页明示「建议全量重跑」(照常产出)。

**04 联动**:manifest 对比组含中际旭创 → 复查收尾主 agent 提示一句 → 确认后重跑轻链(compare_assemble.py + compare-judge)。

**与 research/03 推演比对:双向场景判断零漂移**——分层重评边界、档位变化、变化区块首句全部一致;架构只改了「谁在什么文件里产出」,没改任何判断。

## C. 前置票规则 → 架构落点(零孤儿)

| 前置要求 | 架构落点 |
|---|---|
| 03 状态/赔率必重评、路径核销 | 分诊单固定字段 + node-path 增量 prompt 固定任务 |
| 03 质地标脏四条 | triage.py 机检(结构化 YAML 块使四条全部可机检;规则外拿不准一律标脏) |
| 03 决策层+首页永远重装配 | R4 必跑(decision-writer + assemble) |
| 03 增量计数 / >12月 / 4次 / 旧结构基线 | manifest.json 字段 + triage 硬规则 |
| 03 披露日被动提醒 | manifest 字段 + assemble 在报告内写预约行 + Inves-Report 超龄警示 |
| 05 红旗两源制(脚本+提名) | 节点 YAML `red_flag_nominations` 字段 + 附录D merge 脚本 |
| 05 面板菜单+写手自选 3-5 | node-quality YAML `panel_fields` 字段(结论行引用质地子判定) |
| 06 数字唯一 home / 章预算 | v8 lint fail / warn |
| 07 390px 手机走查 | reviewer-delivery 固定走查清单(对成品 HTML) |
| 02 封顶规则 / C4 区间锚两端同向 | decision / odds YAML 必填字段 + lint 校验 |
| 08 schema 外置代码侧 | scripts/schemas/node-{x}.schema.json + assembly 产物 schema |
| 08 节点→写手绑定 | 1 节点 = 1 手册 = 1 写手(文档边界=节点边界=写手边界) |

## D. 结论

10 个 agent、两波依赖图、YAML 块单一数据源的目标架构,在东山全量+中报增量双场景下:每个组件唯一生产者、前置票全部规则有家、判断与 02/03 推演零漂移。09 可关票,地图到达目的地。
