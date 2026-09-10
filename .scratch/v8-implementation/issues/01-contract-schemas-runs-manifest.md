# 01 — 契约层:schema + runs 目录制 + manifest

**What to build:** v8 全体组件读写的机器契约。五个节点 YAML verdict 块(质地/状态/赔率/路径/决策)、装配产物(决断卡/面板/Top3/变化区块)、红旗条目与面板指标块、公司级 manifest 的 schema 文件;每次 run 一个日期目录的 runs 目录制(旧 run 整目录即留档);run 初始化脚本适配新布局。字段定义以 [spec §3/§6/§8](../../v8-refactor/spec.md) 为准。做完后,任何下游组件(写手/装配/lint/分诊/对比)都只面向这套契约开发。

**Blocked by:** None — can start immediately.

**Status:** done (2026-08-16)

- [x] 节点×4+决策 YAML 块 schema:必含 verdict/子判定表(判定+最硬证据引用)/红旗提名;节点特有字段——质地:面板自选指标;赔率:区间锚两端+同向标记;路径:证伪与左尾清单;状态:临界点(该等什么);决策:三元组/行动档位/封顶检查结果
- [x] 装配产物 schema(决断卡/面板/Top3/变化区块)与红旗条目(id/级别/证据/来源 script|nomination/归属节点/关联指标引用)、面板指标块(指标/数值/趋势/peer 分位/红标引用/备注+面板级选择理由与结论行引用)字段齐备
- [x] manifest schema:runs 列表(full/incremental)/增量计数/上次全量日期/下次预约披露日/所属对比组
- [x] runs 日期目录制落地,run 初始化建目录+初始化 manifest;旧输出留档不动
- [x] 每个 schema 配合法/非法 fixture 各至少一例,pytest 全绿(沿用现有 scripts/tests 的 fixture 风格)

**实现记录(2026-08-16)**:scripts/schemas/ 八个 schema 文件(common 共享 $defs + 节点×4 + decision + assembly + manifest);scripts/verdict_block.py(顶部 fenced YAML 块抽取+跨文件 $ref 校验+CLI,退出码 0/1/2);scripts/manifest.py(create_run/load/save/latest_run,full 重置增量计数、incremental +1,写前校验);init_run 加可选 --run-type(不传保持 v7 行为,expand 式);requirements/install.sh/install.ps1/README 登记 pyyaml+jsonschema 与 schemas 下载。测试 scripts/tests/test_contract_v8.py 39 项全绿(合法 fixture 取自东山推演;含 reused_from 盖戳、同向条件必填、重复 run 日期拒绝等);全套件 62 项中 59 绿、3 错为本机缺 pandas 的既有环境问题(与本票无关)。补充决策:同日期重复 create_run 抛 RunExists;装配只认顶部 YAML 块(正文中部块不算,单一数据源纪律进了测试);schema 均不设 additionalProperties:false(允许前向扩展字段);decision 块无子判定表与红旗提名——依据 research/02 决策层形态(三元组→档位+三分+证伪,无 ✓/⚠️/✗ 表)与 spec §3 红旗归属节点枚举(quality|state|odds|path 不含 decision),「必含子判定表」按四问节点解读。

**Code review(两轴,2026-08-16)后修复**:scripts/README.md 依赖行+模块表补登记(硬伤×2);referencing 直接依赖入 requirements;manifest 的 next_disclosure_date 升 required(可空不可缺);change_block 三张清单(红旗/证伪/指标 delta)升 required(空列表=明示无变化);质地五问锁名(schema contains×5);面板指标六键齐备(可空≠可缺);RUN_TYPES 常量收敛三处字面量;reused_from 复用 iso_date $ref。未采纳:verdict_block 模块拆分(契约=块+schema 一体,规模不够摊两个模块);sub_verdicts wrapper 下沉 node_base(各节点 minItems 不同,就地可读性优先)。修复后契约测试 43/43 绿。
