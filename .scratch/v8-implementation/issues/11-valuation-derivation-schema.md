# 11 — 估值推导结构化(机器验算术 + 解锁可视化)

**What to build:** 把③赔率的推导从「散文里的数字」变成**契约里的数据**。`node-odds.schema.json` 新增 `derivation` 结构:`share_count`(值+口径+期别+来源标签)、`sotp.segments[]`(name/profit/multiple/unit/value/basis/falsify)+`net_debt`+`equity_value`+`per_share`、`dcf.discount_rate[]`(分项加法栈)+`scenarios[]`(name/p/cagr/margin/exit/pv)+`equity_value`+`per_share`。装配层据此**渲染成表**(写手不再手搓 markdown 表),`lint_v8` 新增算术闭合规则:`Σsegments − net_debt = equity_value`、`Σ(p×pv) = equity_value`、`equity_value ÷ share_count = per_share`、`Σ概率 = 1`、`Σdiscount_rate 分项 = 折现率`。同时解锁三个此前做不了的图(数据一旦结构化即可机器生成、零写手工作):**P=F+N 占比尺**(需 `p_f_n` 字段真填,东山这次是 null)、**左尾深度阶梯**(需 `path.left_tail[]` 加 `depth_pct` 数值字段,现在只有 `{scenario, note}` 自由文本)、**面板 sparkline**(需 `quality.panel_fields[]` 加 `series[]` 数值序列,现在 `value` 是字符串)。

**起因:** 票 08 首份成品实测——「从 1,421 亿到 77.6 元/股」这一步**全章没有交代**(要 ÷18.31 亿股,股本数字一次都没出现),三轮双 reviewer 都没抓到,是**真人读者读出来的**。机器抓不到的原因就是这些数字只以散文形式存在,没有可校验的结构。

**Blocked by:** 08

**Status:** ✅ done(2026-08-25;东山 08-24 人工版倒灌验收,零漂移)

- [x] 五条算术闭合规则全部机检 —— 实际落了 **十条**(另加:分部乘法、分部加总=EV、锚=两法推出来的每股价、F+N=市值、市值=现价×股本)。带回归测试 `test_derivation_v8`(26 项),两个头等用例就是票里点名的那两类错:`TestPerShareConversion`(每股换算整个丢失)/ `TestSumErrors`(合计加错)
- [x] 装配层渲染 SOTP / 折现率 / 三情景三张表 —— 写手在正文写 `{{sotp}}` / `{{discount_rate}}` / `{{dcf}}` 占位,`assembly.load_node_bodies` 按 `derivation` 渲染;R12 另查占位是否真在正文里(数据填了却没占位 = 读者一格看不到)
- [x] `p_f_n` / `left_tail[].depth_pct` / `panel.indicators[].series` 三处补数值字段,手册写清「填数不填话」(node-odds §2.5 / node-path §1.1 / node-quality §3.1);后两处**键必填、值可空**——逼写手明说「没有」而不是忘了
- [x] 三个图按 `dataviz` 方法论落地:形态先定(部分-整体条 / 排序条 / 无轴折线)再上色;`--viz-*` 与红标状态色分开取,明暗各自取色;色板跑 `validate_palette.js` 六项检查(不是肉眼),浅色 viz-2 的 relief 由可见直标解除;左尾阶梯单色(长度已编码量级,再调色是编码两遍)
- [x] 东山零漂移:SOTP 表 6×5、DCF 表 5×6 与人工版**逐格一致**,其余四章一字未动,十条闭合在真实数据上 `ALL CLOSED`,lint exit 0
- [x] 章预算不爆:R4 PASS,主体 190 行 / 上限 400

## 顺手裁决:票 09 遗留项①(③④同波)

**选了「④挪到第二波」,否决「装配期锚占位」。**

票 09 验收暴露:③④同波时④第一波只拿得到**上一版**的③锚,终稿两套锚并存、靠评审轮回填。
左尾还是散文时这只是措辞不齐;票 11 把左尾深度变成**数值字段**之后就是硬错——`depth_pct`
(「跌回③锚要跌多少」)的分母就是③的锚与现价。

- 占位方案只能让④**拿到**数字,不能让它**据此推理**;而「回吐到 F 是 −64%」本身就是④的结论,
  给一个渲染期才填上的数字,等于让写手围着一个自己没看过的数写散文。
- 挪波次**代价是零**:第二波原本只有②一个节点在跑,④并进去,总波次仍是 3、前两波各两个并行。
- 反向引用(③手册 §6「地板见④」)是**指路**不是取数,不构成环。

同步改了 `node_graph.DEPS` / 链手册 §1.2 与写手表 / `phase-orchestration` / `agent-protocol` /
`SKILL.md` / 四个 agent 名册,并把 `agents/node-path.md` 的「第一波不应依赖③」FAIL 条款改成
「③块不存在 = 调度错序,**不许自己估一个锚顶上**」。

## 本票**没有**并进来的

- **红旗 id 归一化**(票 09 遗留项②:id 哈希含动态数值 `Z=8.767`,刷新必然成对新增/解除)——
  会破坏在途引用,**单独切票**,按用户要求不与 11 混。
- `html-template-guide.md` 仍 v4.3 旧版(票 09 遗留项③),另票。

## 留给后续

- **东山③要真重跑一次**:本票只做了「人工版倒灌进契约」的零漂移验证,不是写手按新契约重新推导。
  ③的契约变了,而票 09 刚重评过③——下一次 `--review` 会带出来。
- `dcf.scenarios[].cagr/margin` 已是数值字段,但暂时只用于渲染;若将来要画「隐含假设 vs 历史/同业」
  的对照图,数据已经在契约里了。
