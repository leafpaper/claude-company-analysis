# 04 — 装配层:决断卡/面板/Top3/红标映射/附录

**What to build:** 装配脚本重写。输入=五个节点 md 的 YAML 块(01 契约)+ audit 红旗产物,输出=首页(决断卡五行→赚钱面板→Top3 红旗→人工导读位)+ 附录A-E 挂载 + 主页 metadata(verdict=行动档位人话+质地字段)+ 红标反查映射数据(红旗条目 id↔指标,供 HTML 层渲染三通道与跳转)。附录D=audit 红旗⊕节点提名两源合并、同池排 Top3;面板结论行引用质地子判定①②,无红旗命中的指标不标色。变化区块装配(新旧 YAML diff→三元组/档位对比/翻转节点/红旗与证伪变动/首句答「阿尔法变了没」)也在本票,09 直接复用。Golden 基线取 [research/02](../../v8-refactor/research/02-dongshan-walkthrough.md) 与 [research/05](../../v8-refactor/research/05-dongshan-panel.md) 的东山数据手写 fixture。

**Blocked by:** 01(读写全走契约层 schema)

**Status:** done (2026-08-17)

- [x] 东山 fixture → 决断卡五行与 research/02 §6 逐行一致(golden test)
- [x] Top3 由红旗清单两源同池机器带出,与 research/05 一致(提名「商誉对赌」后 Top3 不变)
- [x] 面板渲染指标/数值/趋势/peer 分位/红标数据,结论行=质地子判定引用,零新结论;ROE 难看但无红旗命中→不标色(research/05 推演点 1)
- [x] 附录D 合并产物过 schema;红标反查映射数据完整(级别/证据/来源/归属节点)
- [x] 变化区块装配有双向 fixture 测试(利空:档位观察→回避;利好:质地标脏)

**实现记录(2026-08-17)**

三个模块,一条数据流:`red_flags`(附录D 引擎)→ `assembly`(装配数据)→ `assemble_report_v8`(渲染+CLI)。

- `scripts/red_flags.py`:audit JSON → 契约红旗条目(framework/signal 归家表:估值→odds、商誉→path、户数/质押→path、预告→state、其余→quality);两源 merge(脚本在前、提名在后,id 冲突即报错=一条红旗一处归家);Top3;红标反查 by_metric/by_indicator;CLI 产 `red_flags.json`(**写手引用 id 的来源**——写手在面板块填 `red_flag_ref` 必须照抄这里的 id,反查不到即装配失败,写手不能自行标红)。
- `scripts/assembly.py`:load_nodes(五块逐个过 schema,不合契约拒绝出半成品)/ 决断卡 / 面板 / metadata / 变化区块 / build_assembly(产物过 assembly.schema.json)。
- `scripts/assemble_report_v8.py`:首页(决断卡→面板→Top3→导读位[→较上版变化])+ 五章挂载节点正文 + 附录A/B/C/E 挂采集产物(标题下沉两级,缺产物记 missing 不致命)+ 附录D 机器生成(每条带 `<a id="flag-…">` 锚点供红标跳转);写 `assembly/assembly.json` + 主报告 md。旧 `assemble_report.py`(v7 五 part 拼接)保留不动,由票 08 切换时删。
- 测试 `scripts/tests/test_assembly_v8.py` 46 项全绿(全套件:契约 43 + 装配 46 + v7 20 绿;3 个数据采集测试仍因本机缺 pandas 报错,与本票无关)。golden fixture 独立成 `scripts/tests/dongshan_fixture.py`,供 06/07/09 复用。

**本票新定的机器规则(东山推演对照后落盘,铁律)**

1. **红旗分组**=按首要关联指标(`metric_refs[0]`)聚合,同指标多条视为一个风险 → 商誉(脚本规则+对赌提名)、估值(PB 分位+PB/ROE 错配)各自合并成 Top3 的一条,与 research/05 §2「合并为一条」一致。
2. **Top3 排序键**=级别 → 组内条数(旁证越多越硬)→ 归属节点(path>odds>quality>state,左尾杀伤力序)→ 清单出现序。东山跑出的 Top3 集合={估值透支、商誉减值、散户暴增+杠杆拥挤},与 research/02 §6 一致;**摘掉商誉对赌提名后集合不变**(提名合并进已有条目,不挤掉任何风险)。⚠️ 展示顺序是机器排序(散户/商誉/估值),与 research 行文列举顺序(估值/商誉/散户)不同——两者不可兼得:任何把估值排第一的规则都会让「提名前 Top3」少掉商誉那条。取集合一致 + 提名不变形。
3. **散户拥挤按 🟠 走写手提名**:audit 的户数信号只有 🟡,两融/大宗折价无脚本规则,而 research/02 §4 左尾④把它算进 −75%~−98% 踩踏 → 正是提名通道的设计场景(fixture 已按此写)。
4. **档位「跨两档」判定**=三档态度带(进攻{核心仓,期权仓}/观望{等证据临界,不追高}/撤退{减仓,回避})的带间距离 ≥2。东山场景A 等证据临界→回避=跨一档(与 research/03「不触硬规则 2」一致),场景B 质地翻转触发建议全量。
5. **翻转判定**=verdict 文本变化 或 任一子判定判定符变化(质地 ✓/⚠️/✗ 可机检)。
6. **首句「阿尔法变了没」**只陈述机器测得的变化(证伪触发/翻转节点/档位/红旗增减),不自产解释。

**契约层追加(01 的 schema 增补,均为可选字段,旧 fixture 不受影响)**

- `node-odds.current_price {value, unit}` — 决断卡赔率行要机器拼「锚区间 X-Y vs 现价 Z」,现价此前无处安放(票 05 写手 prompt 需带上)。
- `node-decision.front_page_intro` — 首页 3-5 句人工导读位;装配只读 YAML 块,导读必须在块里(不从正文捞)。
- `assembly` 增 `red_flags` / `red_mark_map` / `appendices` / `front_page_intro` / `metadata.next_disclosure_date`;新增 `appendix-d.schema.json`(附录D 合并产物校验)。

**报告解析适配(update_index)**:v8 报告的 `CARD_METADATA` 里写 verdict(行动档位人话)/quality/action_gear/version,解析优先级 RATING_TRIO_DATA(v7)→ CARD_METADATA(v8);新增 `quality_field` 字段与「质地 X」badge;tone 由行动档位直接决定(v8 无综合评分);报告发现路径加 `runs/*/`。卡片版式改造仍归票 07。

**留给后续票**:附录 C/E 的采集产物文件名(`sentiment.md` / `data_sources.md`)是按 research/09 归属预留的,票 05 接 data-collector 时对齐(缺文件只记 missing 不致命);Top3/红标的 HTML 三通道渲染与悬停反查归 07;红旗闭环机检(每条红旗一处归家 + Top3 一致)归 06 lint。
