# 06 — 质量环:v8 lint + reviewer-{logic,delivery}

**What to build:** anti_lazy_lint 重写为 v8 lint,LLM reviewer 3→2 并行,review_loop 适配(fresh-restart 修正循环+3 轮上限照旧)。lint 判定对象=节点 YAML 块+装配后的报告;旧 reviewer-{narrative,valuation,redflag} 删除(其抄写校验职能已随判断链收敛消失,红旗闭环改机检)。

**Blocked by:** 01(schema 校验)、04(lint/reviewer 面向装配产物形态)

**Status:** done(2026-08-18)

- [x] v8 lint:删字数下限与覆盖率规则;新增——五块 YAML schema 校验(fail)/红旗闭环机检:每条红旗一处归家+Top3 一致(fail)/数字唯一 home:异地出现必须带来源引用(fail)/章预算(warn)/区间锚同向标记必填(fail);留改外链规则、决策字段齐全(改查 YAML)、无记忆性反例
- [x] lint 正反 fixture 判定正确(越预算/缺字段/异地裸数字/红旗无家各至少一例)
- [x] reviewer-logic 定义:跨节点引用不重推/影子结论(节点外冒出第二结论)/verdict-正文自洽/最硬证据真硬/叙事 SOTP 与 N 有据
- [x] reviewer-delivery 定义:结论先行/全说人话/390px 手机走查清单(对成品 HTML,验收在 08 落地)
- [x] review_loop 适配双 reviewer 并行与新 FIX 流转;旧三 reviewer 文件删除

---

## 实现记录(2026-08-18)

### 落了什么

**`scripts/lint_v8.py`**(取代 `anti_lazy_lint.py`)。判定对象换成 **run 目录契约**:`nodes/` 五块 YAML + 正文、
`assembly/assembly.json`、装配后的主报告。10 条规则:

| # | 规则 | 级别 | 判什么 |
|:-:|---|:--:|---|
| R1 | 五块 schema | fail | `assembly.load_nodes` 逐块过 `scripts/schemas/`;不过则后续规则 SKIP(不刷屏) |
| R2 | 红旗闭环 | fail | Top3/清单按节点块**重算比对**(装配没重跑也在这现形);🔴 未在归属节点叙述 |
| R2w | 🟠 归家 | warn | 🟠 未叙述只提示(文本命中有误判空间,不卡出片) |
| R3 | 数字唯一 home | fail | 跨章重复的数字,异地那处必须带 ①-⑤ / 附录A-E 引用;**首页与附录豁免** |
| R4 | 章预算 | warn | 70/60/70/60/50 + 主体 400 行上限,**无下限** |
| R5 | 区间锚 | fail | same_direction 必填、不同向必写 divergence_note、两端不倒置、verdict 与现价方向不矛盾 |
| R6 | 外链引用 | fail | 留改自 v7;指向本报告附录的 `#锚点` 合法 |
| R7 | 决策字段 + 封顶 | fail | 九个必填字段;**有 🔴 → 档位强制「回避」且 `gear_cap.triggered`**(链手册 §2.3 硬规则) |
| R8 | 越权发声 | fail | 仓位/档位/买卖建议只在⑤;写「归⑤/见⑤/不判」的引用行豁免(链手册 §2.8 点名 lint 拦) |
| R9 | 无记忆性反例 | fail | 留改自 v7(元讨论语境豁免) |
| R10 | 报告与节点同步 | fail | 主报告五章正文 = 节点 md 正文——改完没重装配当场现形 |

CLI `--run-dir`(+ `--md` / `--artifacts-dir` / `--audit-json`),退出码 0 / 1(有 fail)/ 2(run 目录不完整)。
`build_html` v8 通道出片前内置跑一次(fail 阻断、warn 打印);v7 兼容通道不再跑 lint(无节点块可判)。

**两个 reviewer**(`agents/reviewer-{logic,delivery}.md`):各自开头写明「机器已经查过的别重复」,
FIX 必须带落点与类型。reviewer-delivery 明确禁止声称"跑过浏览器/量过像素"——它只有 Read/Grep,
390px 是清单式静态走查,真机目测归 08 的人眼终检。

**`scripts/review_loop.py` 重写**:reviewer 3→2,`--output-dir` → `--run-dir`,diff signature 从
`phase3-part{1-5}.md` 改成五个节点 md。FIX 行加类型字段:

```
- [FIX-{node}-{判断|表述}] {问题≤30 字} → {建议≤60 字}
    node ∈ quality|state|odds|path|decision|front(首页导读)|delivery(HTML 交付)
```

脚本据此分诊,JSON 直接给出 `restart_writers`(判断类 → fresh-restart 写手)/ `edit_targets`(表述类 →
主 agent Edit 正文)/ `delivery_fixes`(改模板),主 agent 不再自己判"这条 FIX 该谁改"。
`front` 一律回 decision-writer(导读是 `front_page_intro` YAML 字段,主 agent 不许手改块)。

**文档**:`phases/phase6-review-publish.md` 重写(机器门控规则表 + 修复指引 / 两 reviewer prompt /
JSON 决策表 / 修正循环三类落点 / 出片发布 / Part D 缺口补查改触发式,补到的证据回节点或采集产物);
`phase-orchestration` Phase 6 去掉「🚧 施工中」;`agent-protocol` 名册 9 个 + reviewer schema 带 kind;
`SKILL.md` / `README.md` / `install.sh` 同步(agents 10→9、scripts 换 lint_v8、assets 6→5)。

**删除**:`scripts/anti_lazy_lint.py` + `test_anti_lazy_lint_v7.py`、`agents/reviewer-{narrative,valuation,redflag}.md`、
`assets/validation/report-checklist.json`(20 项 9 章节清单;v8 的审核标准在 lint 规则集与 reviewer 定义里,
不留没有代码读的第二份真相源)。

### 验收

`scripts/tests/test_quality_loop_v8.py` 41 项,测试缝 = run 目录契约(东山 golden fixture 进、lint 判定出):

- **票要求的四类正反例**:越预算(80 行 → warn 且不阻断)/ 缺字段(decision 掉 `gear_cap` → R1 fail + 后续 SKIP)/
  异地裸数字(④裸引③的「273 元」→ fail;带「见③」→ pass)/ 红旗无家(🔴 未在④叙述 → fail;写了标题词 → pass)
- 另加:封顶(有 🔴 不判回避 → fail)、Top3 漂移、提名后未重装配、报告脱节与重装配后转绿、越权与豁免、
  外链与 `#锚点`、无记忆性与元讨论豁免、CLI 三种退出码;review_loop 的解析/去重/分诊/对抗检测/缺响应
- **golden run 全绿**:fail 项全过 exit 0,5 条 🟠 归家 warn(fixture 正文是 3 行桩,真实报告不会这样)
- 全量 `python -m unittest discover -s scripts/tests -t .` 195 项,除既有 3 个缺 pandas 的环境错外全绿

### 判断与取舍

- **🔴 fail / 🟠 warn 的归家分档**:归家检查靠「标题词 + 证据里的数字短语」文本命中,没有更硬的机器信号
  (metric_refs 是英文键,不出现在正文)。对 🔴 严格(漏讲致命红旗是真错、条数少、误判可控),对 🟠 宽松
  (避免文本没命中就把出片卡死),漏网的由 reviewer-logic 兜。
- **R10 是本票的额外收获**:spec 没列,但修正循环最常见的事故就是"改了节点忘了重装配",
  一条 `_squash` 比对就能抓死,顺手加了。
- **数字唯一 home 只判五章之间**:首页是机器装配(链手册 §4.5 明文豁免),附录本就是全表下沉的家——
  拿附录比对会把几乎每个数字都判违规。
- **封顶检查进 lint**:链手册 §2.3 写明"硬规则,机器可检",Phase 3 原本只做人工确认,现在机器兜底。

### 留给别的票

- **08 全量整合上线**:两个新 agent 要 install + 重启 Claude Code 才进注册表;390px 真机目测与
  东山全链路(采集→写手→装配→lint→双 reviewer→出片)的一次真跑,归 08 验收。
- **09 `--review`**:增量 run 的 lint 与全量同一套(判定对象都是 run 目录);变化区块进不进 lint 规则,
  等 09 的分诊单形态定了再看。
