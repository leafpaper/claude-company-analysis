# Changelog

所有重要变更按版本记录。格式受 [Keep a Changelog](https://keepachangelog.com/) 启发。

---

## [v8.0] — 2026-08-19 — 判断链收敛（首页一眼决断 + 五章 + 附录A-E）

> **主题**: 报告结构就是判断链本身。9 章节收敛成「首页一眼结论 + ①质地 / ②状态 / ③赔率 / ④路径 /
> ⑤怎么办 + 附录A-E」,同一个问题全报告只答一次;10 维评分、定性综合方向、快筛章节、§七 7.1-7.3、
> §一人工抄写的决断卡这些**结论假面**全部删除。判断的唯一数据源是五个节点 md 顶部的 fenced YAML
> verdict 块,首页决断卡 / 赚钱面板 / Top3 红旗 / 附录 A-E **全部机器装配,零人工抄写**。
> 管线 sub-agent 名册 9 个(data-collector / doc-analyst / 四节点写手 / decision-writer /
> reviewer-{logic,delivery})、主 agent 退回纯调度;质量环换成「机器先于人」(`lint_v8` 十条规则挡完
> 再派两个 reviewer);交付形态换成 B 仪表盘 HTML,手机 390px 升为一等场景。**只分析上市公司**——
> 创业公司口径(C/D 轮评分 / 条款分析 / 实物期权 / 退出瀑布)随框架文档重组移除。
>
> 实现按 10 张票落地(01 契约 → 02 doc-analyst → 03 手册 → 04 装配 → 05 写手管线 → 06 质量环 →
> 07 交付 → **08 全量整合上线** → 09 `--review` → 10 `--compare`);本版 = 01-08。09/10 的增量复查
> 与多公司对比页在后续版本提供,`--monitor` 已随 Phase 7 量化监控一并退役。

### 全量整合上线（ticket 08，2026-08-19）

**Added**
- **预约披露日有了生产者**：`manifest.nearest_future_disclosure()`（纯 dict 列表进，不依赖 pandas，列名按
  `modify_date > pre_ann_date > pre_date > ann_date` 取最近的未来日期，列名不认识就留空**不猜**）+
  `manifest.set_next_disclosure()` + `python -m scripts.manifest --company-dir X [--show|--set-next-disclosure]` CLI。
  `tushare_collector` 采集结束时自动登记（失败只 warn，不影响采集）；美股/港股用 CLI 手工填一次。
  此前 `manifest.next_disclosure_date` 恒为 `null` —— 报告头部的「下次预约披露日」一行、HTML 事实条、
  主页卡片字段三处**全都读它**，所以三处一起是空的（票 08 端到端串联才暴露：字段、渲染、消费方都在，缺的是写入方）。
- **`update_index.refresh_preview_data()`**：`reports.data.js`（`window.REPORTS_RAW`，utf-8-sig）跟着
  `data/reports.json` 一起刷。线上页面实时 fetch reports.json，`file://` 本地预览被 CORS 挡住后退回读这个快照——
  以前它是一步只存在于口头约定的手工操作，忘了刷本地预览就停在上一版报告。upsert 成功后自动同步（文件不存在时用
  `--refresh-preview-data` 显式创建）。

**Changed**
- `manifest.RUN_SUBDIRS` 去掉 `raw_data/pdfs`：采集产物落**公司级** `output/{company}/`（= `{artifacts_dir}`，
  跨 run 共享，`references/phase-orchestration.md` 目录结构约定与所有 collector 的实际落点都是这里），
  run 目录里那份是没有生产者的空壳。
- `phases/phase1-data-collection.md`：删掉 v7 残留的「Phase 3 = 3a 预加载 / 3b 分章 / 3c `assemble_report.py`
  拼接 5 part，详见 phase3-analysis-report.md」——两个文件都已删除；改写为「data_snapshot.md = 四个写手共同的
  证据底座 + 附录A 唯一挂载源」。另补 `disclosure_date.parquet` 与预约披露日登记说明。
- `phases/phase6-review-publish.md` 发布段：`update_index` 顺带刷 `reports.data.js`（`git add` 清单加上它），
  并提醒报告不在默认 `output/` 根下时要补 `--output-dir`。
- `agents/doc-analyst.md` 禁改文件清单里的 `phase3-part*.md` → `runs/{date}/nodes/node-*.md`；
  `scripts/lessons_manager.py` 的 `--category` 示例从 `phase3-part4` 换成 v8 的 `node-odds`。
- `README.md` 升 v8.0（版本徽章 / 报告结构徽章 / 设计原则两行的 §一-§九 措辞 / 版本演进表 v8.0 行改已发布）。

**Added — 交付可读性（票 08 收尾，真人读者反馈驱动）**

读者读完首份成品的原话:**「几乎所有部分的计算和数字都堆叠到一起」**。量化后:五章 **17 行**「一行 ≥5 个数字」的散文，最密一行 **844 字 / 24 个数字**（在①质地，不在估值章）。

- **根因不是写手不会写，是章预算数错了东西**。`R4` 数的是**行数**，写手要在 ≤70 行里交代完，唯一的办法就是把行写长；列表形状的内容（四个分部 / 五项折现率 / 三个情景 / 七条传导）因此被焊成段落。**约束定成行数，结果就是奖励高密度。** 更糟的是修正循环会放大它:reviewer 提「表格单元格太长」，主 agent 让写手把解释挪到表下，于是一张密表变成一个 711 字的密段落——密度没降，只是换了地方堆。
- **`scripts/lint_v8.py` 新增 `R11 散文密度`**（warn，与 R4 同档不阻断）:一行散文 >5 个数字或 >200 字即报警，并直说「改成表格或分条」。**表格与标题不判**——表格不吃 R4（只数散文行）也不吃 R11，这条规则的作用就是把列表形状的内容推回表里。东山实测:19 行 → 五个写手返工后 **0 行**，最长散文行 844 → 94 字。4 项测试（数字超标 / 字数超标 / 同样的数字写成表就放行 / 是 warn 不是 fail）。
- **`scripts/build_html.py` + `assets/html/report-v8.{css,html}` 四项渲染能力**（纯展示层，不动判断、不改写手契约）:
  - **`<details>` 渐进披露**——章内 `###` 段折叠（东山 11 段）。写手的 `###` 标题本来就是结论句，所以**收起时读小标题就是一条判断链**，展开才看推导:信息一个字没删，只是默认不占屏。每章一个「展开全部 N 段 / 收起全部」控件；`beforeprint` 自动全展开（否则纸上缺内容）；锚点跳进折叠段会沿 DOM 向上逐层展开。⑤怎么办没有 `###`，整章常驻可见。
  - **出处锚链接**——正文里的 `(见①质地)` / `(明细见附录A)` 渲染成真链接（东山 109 处），已在 `<a>` 内的不重复包裹。窄屏顶栏不吸顶，此前读者只能手动滚回去。
  - **估值尺**——③赔率章顶的 meter:轨道 = 锚区间，标记 = 现价，出界标红并直接写「现价是区间高端的 2.18 倍」。形态按 `dataviz` 方法论选定——**不画三根柱**，柱子让人比高矮，而这里的信息是「出界」。数据全部取自 `node-odds` 已有的契约字段（`anchor_range` / `current_price`），**零写手工作**。
  - **附录长表表头吸顶**（附录A 的趋势表 543 行）。
- **票 07 的移动端一等场景规则当场生效**:`test_no_12px_text_anywhere` 与 `test_no_font_size_shrinking_in_media_queries` 拦下了本次新写的 `11.5px` 与媒体查询里的 `font-size:12px`——几个月前定的规则挡住了今天的实现。

> **留给后续票**:P=F+N 占比尺、左尾深度阶梯、面板 sparkline 都做不了，因为**数字只以散文形式存在**——`odds.p_f_n` 字段为 null、`path.left_tail[]` 只有 `{scenario, note}` 自由文本、面板 `value` 是字符串。这给"把估值推导变成结构化数据"那张票加了一条此前没想到的理由:**结构化不只是为了机器验算术，更是可视化的前提**。

**Fixed(东山精密端到端全量 run 实跑挖出，逐条带回归测试或复验）**
- **`scripts/lint_v8.py` R3 判 home 的顺序错**：「带出处的引用」原先也会**认领 home**，于是章序在前的**借用方抢走主人的 home**，反过来把真正的出处判成「异地裸引自己的数字」——东山实测：现价 213.82 与锚区间 [77.6, 97.9] 归③赔率，②状态按规矩带出处引用了它们，②在③前，lint 就去告③的状（52 处告警里 5 处是这么来的）。改为**判 home 时跳过带出处的那些**，加 2 项回归测试。
- **`scripts/build_html.py` 拆 verdict 括注留下孤立右括号**：按左括号切 `a`/`w` 两段，剥掉左括号却把右括号留在尾段，决断卡④显示成「高信仰体检 6/7)」。改为**括号成对剥离**（左右计数不平时才剥尾括号），全角半角混用也认。
- **三个采集脚本把 v7 流水线指令印给读者**：`data_snapshot.py` 头部那段「★ Phase 3 必读规则：必须把整表 inline 完整搬入主报告 §二/§五/§六，严禁"同上"」——它是**附录A 的挂载源**，这段既泄漏内部指令、又引用已删章节号，**内容还与 v8 的「章预算是上限、全表下沉附录」正好相反**；`peer_collector.py` / `capital_flow.py` 的「供 Phase 3 §八 / §四 / §七 消费」同类。三份产物模板全部改为面向读者的落点说明。`phases/phase1-data-collection.md` 与 `agents/data-collector.md` 另加防复发规则（`sentiment.md` / `data_sources.md` 原样变附录 C/E，禁流水线词与 v7 章号）。
- **`phases/phase2-document-analysis.md` §8 锚点模板仍按 9 章节制**：doc-analyst 据此把 20 条锚点的「可用于」列标成 `§一 / §五 5.4 / §六 6.3`，而 v8 报告根本没有这些章——写手拿到对不上。模板改为节点制并附常见映射表。
- **`scripts/data_snapshot.py` §2.4 毛利率取错字段**：Tushare 的 `gross_margin` 是毛利**额**（元），毛利**率**是 `grossprofit_margin`；附录A 因此印出「毛利率(%) | 2539181351.98」这种量纲炸掉的脏数（同表「本季度毛利率 19.3275」才是对的，§3 趋势表一直用的是对的那个）。已改并保留毛利额于自己的标签下，加 2 项回归测试。
- **`scripts/review_loop.py` 判定行只认 `###`**：reviewer 写成 `##` 就把整份判定丢成 UNKNOWN（fail-closed 不危险，但白丢一个判定）。放宽到 `##`-`####`，加「层级不吞判定」与「认不出必须 fail-closed」两项测试。
- **`update_index.py` / `build_html.py` 硬编码他人机器路径**：`/Users/leafpaper/.claude/plugins/...` 作为查找 fallback，却**不问 `config`**——装好的 skill 从别处跑就找不到自己刚写的报告（票 08 发布时踩到，必须手动补 `--output-dir`）。改为与产出侧同源（`config.PLUGIN_ROOT/output` → `SKILL_ROOT/output` → 相对 `output/`）。
- **`SKILL.md` Step 0 假定 Windows 一定有 `py -3`**：本机没有 Python launcher，裸 `python` 又可能是 Store 占位符。改为「按顺序试到第一个能跑通的，选定后必须用 `check_env` 验」，并把各 agent 文档里的 `{PYBIN}` 说明统一成「主 agent 给什么用什么，别自己换」。另补一条**每条命令自带 `cd`** 的硬规则——Bash 工具每次调用后工作目录会重置，忘了 cd 的症状是「改了没生效」（实测 `install.ps1` 用相对路径静默没装上，出片一直在用旧模板）。
- **`references/judgment-chain.md` §2.2 映射表第 4 行是死条款制造机**：原写「↓变差，**或**(买完完美未来 且 高尾险)」，第二个子句与状态无关，把第 2 行「↑未确认 × 买完完美未来 × 高尾险 → 等证据临界 / 期权仓，看右尾大小」整行吞掉——只要又贵又扛不住就直接回避，"看右尾大小"永远走不到（decision-writer 实跑撞上，靠「取更保守一侧」自行绕过）。第 4 行限定为「**且右尾清单不成立**」，并写明必须逐条过清单再裁决：不许跳过清单直接回避（一刀切），也不许跳过清单直接开期权仓（赌）。

**Fixed**
- **`scripts/capital_flow.py` 户数 NaN 崩溃**：Tushare `stk_holdernumber` 会返回一批还没填 `holder_num`
  的期（东山精密 2026-08 实测 279 行里 **152 行是 NaN**），排序后落到"最新一期"就在 `int(now["holder_num"])`
  上抛 `ValueError: cannot convert float NaN to integer` —— **附录C 的资金底稿整份产不出来**。改为先丢掉
  没有户数的行再取最近两期；全 NaN / 只剩一期则安静降级不写字段。新增 `scripts/tests/test_capital_flow.py` 3 项。
- **`scripts/requirements.txt` 漏 `markdown`**：`build_html` 对它是 `ImportError → sys.exit(1)` 的硬依赖，
  但照文档 `pip install -r scripts/requirements.txt` 装完，要一直跑到 Phase 6 出片才炸。`check_env.REQUIRED_PKGS`
  同步补 `yaml` / `jsonschema` / `markdown` 三个 v8 硬依赖（此前只查 6 个数据层包，契约层缺件 Step 0 查不出来）。

**Notes**
- **东山精密端到端全量 run 走通（2026-08-19，基准日即当日）**：P1 采集（22 张 parquet / 5 份 PDF / 10 条脚本红旗）→ P2 精析（5 份全精读、20 条锚点）→ 两波写作（质地 ∥ 赔率 ∥ 路径 → 状态 → 决策）→ 装配 → 质量环 → B 仪表盘 HTML → 发布 Inves-Report。每个组件唯一生产者，与 research/09 零孤儿表逐项对上。
  - **结论**：决断卡「部分好 / ↑变好但仅注意力·未确认 / 买完完美未来 / 高尾险·不可承受 / 现价回避 0 仓位」；锚区间 [SOTP 77.6, DCF 97.9] 两端同向 vs 现价 213.82；封顶未触发（零 🔴），档位由三元组自算得出。
  - **质量环真在起作用**：两个 reviewer 前两轮都判 FAIL，共 19 条 FIX；第 3 轮双 PASS、`overall_pass: true`。修正循环里 reviewer 两次**纠正了主 agent 的回查错误**——先是「①里的 7.50% 是扣非增速不是净利率，数字串撞上了指标没撞上」，再是「17.59% 只在节点 md 的 YAML 块里、不在渲染后的①质地正文里，跨章指针要按渲染后的章正文核」。
  - **写手自查抓到机器抓不到的错**：④路径发现正文「融资余额 109.88 亿 / −15.6%」在 artifacts 里**查无一手出处**（附录C 真值 107.57 亿 / −17.4%），且没有擅自改而是上报——因为该数字被③④两章共用，单方面改会破坏跨章一致。顺带追出「占流通市值 3.7%」是拿那个错值现算的衍生数（109.88 ÷ 2,964.23），挂载源里根本没有这个口径。**lint 抓不到这类错**：R3 只管「跨章重复要带出处」，不管数字本身能否回源，两章写同一个错值反而"自洽"。→ 候选新规则：跨章共用的数字要能回源到附录挂载源，回不到记 warn。
  - **陈年产物会污染新 run**：公司目录里 v7 时代的 `phase3-part*.md` 与旧报告仍在，写手引到了只存在于旧稿的「三环 27.73%」。→ 候选:`init_run` 对同公司的历史非 run 目录产物做归档或标记。
  - 报告主体 114 行（软目标 400 以内）、红旗 26 条零 🔴、Top3 与重算一致；报告内含「下次预约披露日 2026-08-22」一行（半年报 3 天后披露，②状态 2 条临界点与④路径 5 条证伪挂在这一天，是 `--review` 的第一个真实用例）。
- **离线整合彩排**（东山 golden fixture 走真实 CLI 全链，不碰网络）：`init_run` → 五块 `verdict_block`
  → `assemble_report_v8` → `lint_v8` → `build_html` → `update_index`，逐段退出码 0；装配产物为
  决断卡 5 行 / 面板 5 块 / Top3 3 张 / 红旗 14 条 / 五章 5/5 / 附录 5 个 / 红标 5 处 / 表格横滚容器 6 个，
  预约披露日贯穿「manifest → 报告头部行 → CARD_METADATA → HTML 事实条 → 卡片 JSON」五处。
  fixture 正文是 3 行桩，所以 R2w 的 5 条 🟠 归家 warn 与主体行数不代表真实报告。
- 契约与装配测试 98 项绿（+5 预约披露日 +3 预览快照）；全量 `python -m unittest discover -s scripts/tests -t .`
  除既有 3 个缺 pandas 的环境错外全绿。

### 装配层：首页与附录机器装配（ticket 04，2026-08-17）

**Added**
- **`scripts/red_flags.py`** — 附录D 红旗总清单**两源合并**（脚本 `financial_audit --json` ⊕ 写手在节点块里的
  `red_flag_nominations`），按 `metric_refs[0]` 聚合去重、算 Top3 排序键、产红标反查表（`red_flags.json`
  供写手引 id）。**`scripts/assembly.py`** — 摘要层装配：决断卡五行（逐行取自五个节点的 verdict，零人工抄写）/
  赚钱面板（写手自选 3-5 指标 + 红标映射）/ Top3 / 主页 metadata / 「较上版变化」区块。
  **`scripts/assemble_report_v8.py`** — 报告总装 CLI：首页 + 五章正文原样挂载 + 附录A-E（A/B/C/E 挂采集产物，
  D 为机器合并产物），落 `assembly/assembly.json` + 主报告 md。
- 变化区块的翻转判定落成四条机器规则；「跨两档 = 态度带距离 ≥ 2」；`scripts/tests/test_assembly_v8.py` 46 项
  （东山 golden 进，装配产物出）。

### 质量环：v8 lint + reviewer 3→2（ticket 06，2026-08-18）

**Added**
- **`scripts/lint_v8.py`** — 机器门控重写，判定对象从"9 章节主报告"换成 **run 目录契约**（五个节点 YAML 块 + 装配产物 + 装配后的报告）。10 条规则：
  - `R1` 五块 schema 校验 · `R2` **红旗闭环**（Top3 与红旗清单按节点块**重算比对**；🔴 致命红旗必须在归属节点叙述过，🟠 未叙述记 warn）· `R3` **数字唯一 home**（同一数字跨章出现时异地必须带出处引用；首页机器装配与附录豁免）· `R5` **区间锚**（同向标记必填、不同向必写分歧原因、两端不倒置、verdict 与现价方向不自相矛盾）· `R7` **决策字段 + 致命红旗封顶**（有 🔴 → 档位强制「回避」且 `gear_cap.triggered`）· `R8` **越权发声**（仓位/行动档位/买卖建议只在⑤，写明「归⑤」的引用行豁免）· `R10` **报告与节点同步**（改了节点没重装配 = 脱节）—— 以上 fail 阻断；
  - 留改自 v7：`R6` 外链引用（指向本报告附录的 `#锚点` 合法）· `R9` 无记忆性反例；
  - `R4` 章预算 = **warn**（70/60/70/60/50 行上限 + 主体 400 行，**没有下限**）。
- **`agents/reviewer-logic.md`**（维度 1）：跨节点引用不重推 / 影子结论 / verdict-正文自洽 / 最硬证据真硬 / 叙事 SOTP 与 N 有据；**`agents/reviewer-delivery.md`**（维度 2）：结论先行 / 全说人话 / 成品 HTML 的 390px 与明暗主题走查清单。两份都明写"机器已经查过的别重复"，并要求 FIX 带落点与类型。
- **`scripts/tests/test_quality_loop_v8.py`** — 41 项（东山 golden fixture 进，lint 判定出）：越预算 / 缺字段 / 异地裸数字 / 红旗无家四类正反例齐全，另加封顶、Top3 漂移、提名后未重装配、报告脱节、越权与豁免、外链与锚点、无记忆性与元讨论豁免、CLI 三种退出码，以及 review_loop 的解析/去重/分诊/对抗检测。

**Changed**
- **`scripts/review_loop.py` 重写**：reviewer 3→2（`logic` ∥ `delivery`）、入参 `--output-dir` → `--run-dir`、diff signature 从 `phase3-part{1-5}.md` 改为五个节点 md。FIX 行格式加**类型字段**：`- [FIX-{node}-{判断|表述}] 问题 → 建议`（`node` 含 `front` 首页导读与 `delivery` HTML 交付），脚本据此**分诊**并直接给出 `restart_writers`（判断类 → fresh-restart 写手）/ `edit_targets`（表述类 → 主 agent Edit 正文）/ `delivery_fixes`（改模板），主 agent 只读 JSON。
- **`scripts/build_html.py`**：v8 通道出片前内置跑一次 `lint_v8`（fail 阻断、warn 打印）；v7 兼容通道不再跑 lint（无节点块可判，只做渲染）。
- `phases/phase6-review-publish.md` 重写为 v8 质量环（Step 0 机器门控规则表与修复指引 / 两 reviewer prompt 模板 / `review_loop` JSON 决策表 / 修正循环三类落点 / 出片发布 / **Part D 缺口补查改触发式**，补到的证据回到节点或采集产物而不是只改附录）。
- `references/phase-orchestration.md` Phase 6 从「🚧 施工中」改为可执行 checklist；`references/agent-protocol.md` 名册 9 个 agent、reviewer 响应 schema 带 `kind` 分诊字段、失败处理改指 `lint_v8`。
- `SKILL.md` Phase 6 行、质量门控汇总补三行（门控/评审/出片）、异常处理补 lint fail 与 3 轮上限、脚本索引换 `lint_v8`；`README.md` 流水线与目录树同步；`install.sh` agents 10→9、scripts 换 `lint_v8`、assets 6→5，校验计数同步。

**Removed**（git 历史即归档）
- `scripts/anti_lazy_lint.py` + `scripts/tests/test_anti_lazy_lint_v7.py` —— 章节字数下限与 artifact 关键短语覆盖率**与 v8 的「章预算是上限 + 全表下沉附录」正面冲突**，9 章节骨架比对的对象已不存在。
- `agents/reviewer-{narrative,valuation,redflag}.md` —— 前两个专职校验"四套机制互抄一致"（复述层已删，无对象可校），红旗闭环改机检（lint R2）。
- `assets/validation/report-checklist.json` —— 20 项 9 章节审核清单；v8 的审核标准落在 `lint_v8` 的规则集与两个 reviewer 的定义里，不再留一份没有代码读的 JSON 当第二真相源。

**Notes**
- **门控哲学**：机器先于人——`lint_v8` 没过不派 reviewer；确定性规则挡得住的错不花 LLM 注意力，LLM 只判机器判不了的（引用是不是重推、证据硬不硬、话说得像不像人）。
- **🟠 未归家为什么只是 warn**：归家检查靠标题词与证据数字的文本命中，对 🔴 严格（漏讲致命红旗是真错，且条数少、误判可控），对 🟠 宽松（避免文本没命中就把出片卡死），漏网的由 reviewer-logic 兜。
- 东山 golden run 实测：fail 项全过、5 条 🟠 归家 warn（fixture 正文是 3 行桩，真实报告不会这样）；全量 `python -m unittest discover -s scripts/tests -t .` 195 项，除既有 3 个缺 pandas 的环境错外全绿。

### 全量写手管线：四节点写手 + decision-writer + 依赖图两波（ticket 05，2026-08-18）

**Added**
- **五个写作 agent**：`agents/node-quality.md`（①质地五子判定 + 赚钱面板选 3-5 指标）/ `agents/node-odds.md`（③赔率三件套 + **区间锚 [SOTP,DCF] 与同向标记**）/ `agents/node-path.md`（④路径左尾清单 + **证伪/退出清单**）/ `agents/node-state.md`（②状态 λ 与稀释 / 实锤 vs 传闻 / **临界点=该等什么**，第二波引用③ verdict）/ `agents/decision-writer.md`（⑤三元组→六档 + **封顶检查** + 仓位唯一出处 + 首页 3-5 句导读）。每个写手**只读「链手册 + 本节点手册」两份**，产 `runs/{date}/nodes/node-{node}.md`（顶部 fenced YAML verdict 块 + 正文 verdict 先行 + 最硬证据子判定表），自跑 `verdict_block` schema 校验（≤3 轮自补）+ 章预算自检。
- **`scripts/node_graph.py`** — 判断链依赖图：把**任意节点子集**排成执行波次（全量 `--all` → 质地∥赔率∥路径 → 状态 → 决策；增量 `--nodes {标脏集合}`，子集外依赖记进 `external_deps` 供调度校验"上版复用块是否就位"）。全量与增量复查共用这一套，不维护两条流水线。
- **`phases/phase3-node-writing.md`** — Phase 3 执行细则（**主 agent 读**）：波次计算 / 三波 prompt 模板 / 逐波 `verdict_block` 复核 / 装配命令与验收 / 失败处理 / 增量复查差异预留。
- **`scripts/tests/test_node_graph.py`** — 17 项：全量三波、②状态永不与③赔率同波、research/03 场景 A/B 的标脏子集波次、`external_deps` 与复用集合、旧 part 名必须报错。
- 采集侧补齐（装配的前提）：`financial_audit --json` → **`red_flags.json`**（稳定 id，写手面板 `red_flag_ref` 与决策层封顶检查的唯一来源）+ 拆出 **`sentiment.md` / `data_sources.md`**（附录C / 附录E 的挂载源）。

**Changed**
- `SKILL.md` 改写为 v8 判断链调度器：五节点报告结构、run 目录产物清单、逐波质量门控表、"不写任何判断 / 不手改 YAML 块 / 不手写首页"三条硬边界；`--monitor` 改为退役提示（增量复查 `--review` 待后续版本）。
- `references/phase-orchestration.md` 重写：v8 目录结构约定（`{artifacts_dir}` 公司级 / `{run_dir}` 判断链产物）+ Phase 1/2/3 checklist + Phase 3 三波不变量；Phase 6 标注 v8 质量环施工中（v7 lint 与 3 reviewer 校验 9 章节结构，对 v8 报告会误判，不拿它卡 v8 run）。
- `references/agent-protocol.md`：v8 sub-agent 名册、节点写手完成报告 schema（含 `**verdict**:` 行）、波次门控与 reviewer 修正循环分列、修正循环落点改为节点 md（判断类 FIX 走写手 fresh-restart，主 agent 只改表述）。
- `agents/data-collector.md` + `phases/phase1-data-collection.md`：路径参数化为 `{output_dir}`、新增 audit `--json` / `red_flags` / 附录底稿两步与对应质量门控；phase1 残留的创业公司口径（非上市纯 WebSearch 模式）随 v8 删除。
- `README.md` 流水线/报告结构/产物树/仓库结构改判断链版；`install.sh` phases 5→4、agents 换五写手、scripts 换 `node_graph`、assets 6→4，安装校验计数同步。

**Removed**（git 历史即归档）
- `agents/phase3-part{1,2,3,4,5}.md` — 5 个 part 写手（§一由 part1 抄写 §七、§四评分与定性综合方向等结论假面随判断链收敛退役）。
- `phases/phase3-analysis-report.md`（9 章节写作指令）、`phases/phase7-quantitative-monitor.md`（量化监控，职责由增量复查分诊接管）。
- `assets/templates/report-skeleton.md`（9 章节严格骨架）+ `assets/templates/exec-summary-schema.md`（§一 7 字段）—— 章节结构改由链手册定义、首页改由装配层生成，两份模板已无权威性。
- `scripts/assemble_report.py` + `scripts/tests/test_assemble_report.py` —— v7 五 part 拼接器；票 04 原计划留到 08 删，05 删掉 part 写手后它已无输入，提前删（v8 装配走 `assemble_report_v8`）。

**Notes**
- **东山精密 dry-run 验收**（golden 五节点块 + 真实采集产物）：五块 `verdict_block` 全过 → 波次 = research/09 §A → `assemble_report_v8` 装出的**决断卡五行与 research/02 §6 逐行零漂移**（部分好·真卡位+平庸财务 / ↑变好但未确认 / 买完完美未来·锚区间 57-89 vs 现价 273 / 高尾险·扛不住 5/5 / 先观察等证据临界·期权小仓 ≤2-3%），Top3 两源同池机器带出，主页 verdict = 行动档位人话，附录 A/B/C 挂上真实采集产物。
- **采集产物落点**：collectors 的写死路径决定采集产物仍落公司级 `output/{company}/`（跨 run 共享），`runs/{date}/` 只放判断链与装配产物；与 research/09 表里"采集落 run 目录"的写法不同，**生产者与零孤儿映射不变**。run 目录内的 `raw_data/` 预留给增量复查的证据快照。

### 交付形态「B 仪表盘 · 一眼决断」（ticket 07，2026-08-17）

**Added**
- `assets/html/report-v8.html` + `assets/html/report-v8.css` — v8 报告版式（定稿基线 = 07 prototype 第二套 B，无杂交）：决断卡 = 5 张 verdict 瓦片、赚钱面板 = stat tiles + 红标角标、Top3 = 风险卡；明暗双主题（系统跟随 + 手动切换记忆）。
- `scripts/build_html.py` **v8 通道**：结构化件（决断卡/面板/Top3/变化区块/红标反查）读 `assembly/assembly.json`，正文与附录读主报告 md —— HTML 层是纯展示，零新增阈值、零新结论。
  - **红标三通道**：emoji + 文字级别词 + 底纹，任一通道单独可读；🔴/🟠 红色系、🟡 黄色系（级别靠 emoji 分）。
  - **反查一套实现**：红标本身即链接 → 点击直达附录D 条目锚点（触屏/窄屏走这条）；桌面悬停/键盘聚焦弹浮层给五要素（标题/级别/一句证据/来源/归属节点）；`title` 属性兜底（浮层被横滚容器裁掉时仍可反查）。
  - **正文自动反查**：按红旗清单逐字命中标红（写手不手涂，见 `references/node-quality.md`），短于 4 字的词（FCF/ROE）不进词表；附录D 本体不自标。
  - CLI 新增 `--run-dir`；有装配产物即走 v8 通道，否则回落 v7 槽位填充。
- `scripts/tests/test_delivery_html_v8.py` — 42 个用例（东山 fixture 全链路：run 目录 → 装配 → 成品 HTML）。含明暗两主题的 WCAG 对比度计算（正文/次要文字对页面、卡片、红/黄底纹全部 ≥4.5:1；链接与红标封条 ≥3:1）。

**Changed**
- **移动端升为一等场景**：瓦片/风险卡/附录卡窄屏单列重排；所有表格强制 `overflow-x` 横滚容器；窄屏顶导航由吸顶改静态（v7 吃掉约 10% 屏的痛点）；**媒体查询里一处 font-size 都没有**（改结构不缩字号，机检兜底）；`.wrap{overflow-x:clip}` 保证绝对定位浮层不把页面撑横。
- `scripts/update_index.py` **v8 卡片版式**：verdict = 行动档位人话，新增 `quality_field` / `action_gear` / `next_disclosure_date`（站点陈旧警示的基准）；v8 无综合评分/期望收益，三块 metrics 改为 行动档位 / 质地 / 贵不贵，badges 同步；一句话结论回落到写手导读首段。
- `install.sh` assets 4→6（新增两个 v8 模板文件；templates/ 两份骨架已随 ticket 05 删除），安装校验计数同步。

### 框架文档「1+4 节点制」（ticket 03，2026-08-17）

**Added**
- `references/judgment-chain.md` — **链手册（全员必读）**：总公式与四问定义（含 verdict 取值域、质地=筛选信号不进乘法、一处权威表）/ 决策层（三元组→六档映射、★致命红旗封顶规则、★区间锚两端同向规则、三分结论、右尾纪律、仓位唯一出处、五弊端自检）/ 摘要层机器装配规则（决断卡/面板/Top3/红标纯展示层映射/写手提名通道，字段一律引用 `scripts/schemas/*.json` 不复制）/ 写作规范（人话词典、结论先行、最硬证据制、黑白分割纪律、证据质量门控、数字唯一 home、章预算、禁止项、BEFORE→AFTER 范例）/ 消化路径总表。
- `references/node-quality.md`（①质地：五子判定标尺 + 护城河类型表 + 财务标尺与行业基准 + 赚钱面板菜单）
- `references/node-state.md`（②状态：λ 与分部稀释 / 实锤 vs 传闻分级 / 贝叶斯三问 / 无记忆性 / 身份切换 P1-P4 与 5 元组 / 四层验证 / 催化剂→**临界点=该等什么唯一产出处** / 赛道右尾证据）
- `references/node-odds.md`（③赔率：P=F+N / 反向 DCF / 叙事 SOTP / DCF / **区间锚 [SOTP,DCF] 两端算法** / 估值证据菜单 / Damodaran 行业基准**唯一一份**）
- `references/node-path.md`（④路径：左尾清单与剥离剩余资产清单 / 高信仰体检 / 回报路径成本 / **证伪与退出清单** / 风险证据标尺 / 空头逻辑链）
- **消化纪律**：文档边界=判断节点边界=写手边界；写手只读「链手册 + 本节点手册」，跨节点只引用对方 verdict，机制文本一处安家。

**Removed**（git 历史即归档，不留 archive/；去向按 `.scratch/v8-refactor/research/08-doc-mapping.md` 零孤儿映射）
- `references/scoring-rubric.md` — 评分锚点/加权公式/投资信号表/定性叠加系数**全删**（结论假面）；各维度**证据标尺**迁入：维1/3/5/6→node-quality，维2/4→node-state，维7→node-quality 财务底子 + node-path 偿债左尾，维8→node-path，维9→node-odds，维10（上市版回报潜力）→node-path；证据质量门控→链手册 §4；上市公司财务指标行业基准→node-quality 附表。
- `references/qualitative-frameworks.md` — 「综合方向」verdict 与三段式汇总模板**删除**（结论假面）；框架1 护城河→node-quality，框架2 管理层→node-quality（路径子项在 node-path 放引用行），框架3 催化剂→node-state；黑白分割纪律与禁止项→链手册 §4。
- `references/valuation-frameworks.md` — 主体迁入 node-odds；**v4.2「三法差异 >20% 必须重做 DCF」红线废除**，改为区间锚两端同向规则；剥离剩余资产清单→node-path；7.4 投资回报模拟→node-path；实物期权法与条款分析框架**删除**。
- `references/investment-decision-core.md` — 拆为链手册主体（总公式/决策合成/右尾纪律/写作规范）+ 三份节点手册（状态后验→node-state，赔率→node-odds，路径与左尾→node-path）；决断卡与四维体检模板**删除**（字段外置 schema，首页机器装配）；λ 监控段改写为"接增量复查分诊"。
- **创业公司口径全删**：C/D 轮评分标准、早期公司适配指南、实物期权、条款分析、退出瀑布；`SKILL.md` 输入确认不再问「类型(创业/上市)」，`{type}` 变量移除。

**Changed**
- `install.sh` 参考文档 8→9（手册层 1+4 取代旧四份），`REF_COUNT` 期望同步；`SKILL.md` / `README.md` 参考索引改指手册层。

### 契约层（ticket 01，2026-08-16）
- `scripts/schemas/` 八个 schema（common / node-{quality,state,odds,path} / node-decision / assembly / manifest）+ `scripts/verdict_block.py`（顶部 fenced YAML 块抽取与校验）+ `scripts/manifest.py`（runs 日期目录制、增量计数、公司级状态唯一源）+ `init_run --run-type`。契约测试 43/43 绿。

---

## [v7.2] — 2026-08-17 — Phase 2 文档精析独立化（doc-analyst，v8 预重构）

> **主题**: v8 目标架构是 10 个 agent、主 agent 纯调度。本版先把最容易剥离的一块——Phase 2 文档精析——从主 agent 抽成独立 sub-agent，**跑在现行 v7 管线上**（先把变更做容易，再做容易的变更）。产物路径与格式不变，Phase 3 消费无感。对应 v8 实现票 02。

### Added
- **`agents/doc-analyst.md`**（sub-agent 9→10）: 输入 PDF 清单 + 公司上下文，精读 `pdf_sections_*.json`（section 缺失时回原件 `pdf_reader --search` / 直接 Read PDF），产 `phase2-documents.md`（§1-§8），**自跑 `check_phase2` 并自补 ≤3 轮**，只回报路径 + 判定 + 门控结果。工具集不含 WebSearch/WebFetch（离线纪律：补料是 Phase 1 的职责，缺料 = 降级标注）。

### Changed
- **主 agent 退回纯调度**: SKILL.md「❌ 不做的事」新增"不自跑 Phase 2 / 不读 PDF 与 pdf_sections"；Phase 2 由 `Agent(subagent_type="doc-analyst")` 调起，主 agent 只读 `**判定**:` + **复核**跑一次 `check_phase2`（不自己补写，红了 fresh-restart doc-analyst 一次）。
- `references/phase-orchestration.md` Phase 2 段改写为 Agent 调度 checklist（6 步）；`references/agent-protocol.md` 版本演进登记 v7.2。
- `phases/phase2-document-analysis.md` 定位为 doc-analyst 内部指令（执行者标注 + Step 6 门控改"自跑自补 + 主 agent 复核"）；Step 1 盘点去 `ls -la` 改 `Glob`（跨平台）。
- `install.sh` agent 列表加 `doc-analyst`；安装校验期望 agents 9→10、scripts 25→27（补上 v8 契约层 `verdict_block`/`manifest` 加入下载列表后未同步的计数，此前会误报"安装不完整"）。

### Fixed
- **`scripts/check_phase2.py` 强制 UTF-8 输出**: 报告含 ✅/❌，Windows 控制台默认 GBK 时 `print` 抛 `UnicodeEncodeError` 崩出退出码 1 —— doc-analyst 会误读成"门控红了"并空转 3 轮补写。

---

## [v7.0] — 2026-06-22 — 投资决策内核（贝叶斯之美五篇融入）

> **主题**: 把"贝叶斯之美/BayesCrest"五篇投资理念（《投资是泊松过程》《喊线时代》《三大数学模型之美》《信仰投资最大陷阱》《十年十倍股》）落成 skill 的判断逻辑链。核心公式 **投资价值 = 状态后验 × 赔率 × 路径可承受性**，把"是不是好公司"拆成 **好公司 / 好下注 / 好价格** 三分。根治旧版"DCF 单锚 lowball + 贵=回避"的 Issue 1。

### Added
- **§七 投资决策内核（新章节，8→9 章）**: 状态×赔率×路径合成 → 决策三元组 + 三分结论 + 行动档位（六档：核心仓/期权仓/等证据临界/不追高/减仓/回避）+ 证伪退出。由新写手 **phase3-part5** 之前的 part4 合成（part4=§六/§七，新增 part5=§八/§九）。
- **§四 4.11 状态评估区**: 全机制落地——【λ与证据临界密度】【身份切换·升级基本面5元组】【四层验证·权威认证】【右尾识别·幂律来源·左尾预警】【无记忆性检查】，机制原料供 §七 合成。
- **§六 6.4 左尾防护·高信仰股特征**。
- **`references/investment-decision-core.md`**: 五篇全机制权威定义 hub + 行动档位映射表 + 各报告块必填字段。
- **anti_lazy_lint Rule 6**（§七 决策内核完整性：决策三元组/行动档位/证伪）+ **Rule 7**（无记忆性反例：禁"跌久了该涨/估值压久了该修复"作买入理由）。
- phase3 写手 4→5（新增 `agents/phase3-part5.md` 写 §八/§九）；sub-agent 8→9。

### Changed
- **§五 估值重做**（替代 DCF 单锚）: 5.1 价格分解 P=F+N（含 free option vs embedded obligation、N'/N vs F'/F）/ 5.2 反向DCF 隐含预期 / 5.3 ΔP 传播因子分解 / 5.4 叙事分部SOTP / 5.5 正向DCF 降为 F 的交叉验证 / 5.6 回报含路径成本 / 5.7 赔率小结。每块须出数字。
- **§一 第 7 字段** "投资方向综合判定" → **决策结论**（决策三元组+三分+行动档位+该等什么，照抄 §七 7.4）；综合评分标注「基本面静态快照」非结论。
- **评分原样保留**（用户选定 Option B）: scoring-rubric.md 不改，10 维度评分作 F(B) 先验/快照；权威投资结论移到 §七。
- 结构管线 9 章 / 5 part: `assemble_report`(PART_EXPECTED_SECTIONS 5 part) / `anti_lazy_lint`(MIN_SECTION_CHARS 9 项) / `review_loop`(P1-P5) / `base.html`(section_7 决策内核 + nav) / `report-checklist.json`(9 章 + valuation_anchor 放宽 + forbidden_phrases 限 §四) / `build_html`(槽位动态适配 9)。
- reviewer-valuation 扩为"估值+决策可信度"（反向DCF/P=F+N/SOTP/三元组一致 6 项检查）；reviewer-narrative 1.2 改为 §一 决策结论 vs §七 7.4。
- 旧 §七 舆情 → §八，旧 §八 来源 → §九。

---

## [v6.1] — 2026-06-20 — 跨平台(Mac/Linux + Windows)

> **主题**: skill 原本写死 bash(`python3` / `mkdir -p` / `grep` / `cd "$(...)"` / `git -C /tmp`), 在 Windows PowerShell 上整跑会一路撞 shell 错。本版把编排层移植成跨平台。

### Changed
- **Python 解释器抽象成 `{PYBIN}`**: SKILL.md Step 0 探测(Mac/Linux=`python3`, Windows=`py -3`, 因为 Windows `python` 可能是 Microsoft Store 占位符), 并经 prompt 传给各 sub-agent。SKILL.md + 9 个编排 .md(agents/data-collector、phase3-part1、references/agent-protocol、phase-orchestration、phases/phase1/2/3/6/7)全部 `python3 -m scripts.X` → `{PYBIN} -m scripts.X`。
- **去 shell 依赖**:
  - `grep "^**判定**:" response`(从 sub-agent 响应提字段)→ 改为"直接从响应文本读"(本就在上下文里, 无需 shell)。
  - `mkdir -p` / `test -f` 建目录+main-log → 新增跨平台 **`scripts/init_run.py`**(SKILL Step 2 调用)。
  - phase3 自检的 `grep -E '^## §' | wc -l` 数章节 → 改用 `assemble_report` 的确定性退出码;phase6 反写校验的 `grep -l` → 改为主 agent Read 搜索。
  - 发布步骤 `/tmp/Inves-Report` → `$INVES_REPORT_DIR`(环境变量, 可配置);并给出 Windows 命令对照(`mkdir -p`→`New-Item`、`cp`→`Copy-Item`)。
  - `tushare_collector` 缺 token 报错信息 → 同时给 Mac/Linux 与 Windows 设置法。

### Added
- **`install.ps1`**: Windows PowerShell 安装器(对应 `install.sh`), 把 skill 装到 `~/.claude/skills/` + 8 个 sub-agent 装到 `~/.claude/agents/`(bundled agents 不会自动注册成 subagent_type, 必须单独放)。保持 ASCII-only(避免 PS5.1 把无 BOM 的 UTF-8 .ps1 按 GBK 解析)。
- `scripts/init_run.py`(跨平台建目录 + main-log)。
- `README.md` 快速开始补 Windows 命令(`py -3` / `install.ps1` / `SetEnvironmentVariable`)。

### Notes
- `.py` 脚本本身一直跨平台(纯 Python);docstring 里的 `python3` 示例为开发者参考, 不影响运行(运行路径以编排 .md 的 `{PYBIN}` 为准)。

---

## [v6.0] — 2026-06-20 — 报告 13→8 章节精简 + 残留清理

> **主题**: 报告"过于多余"。反复瘦身(v4.1 / v5.1.4)留下大量未清理残留——删了 Phase 4/5 阶段却没同步改文档/脚本/schema,报告里同一信息写两遍。本版做两层精简:**报告输出结构** + **skill 内部文件**,零信息丢失,只去重叠。

### Changed (报告结构 13→8)

- **章节合并**(`assets/templates/report-skeleton.md`,真理来源):
  - 旧 §二 评分总览 + §六 10维度详细 → **§四 评分与维度证据**(每维度"分数+内联证据",取消"总览再详细"双写)
  - 旧 §五 行业 + §八 可比对标 → **§三 行业与竞争对标**
  - 旧 §九 估值 + §十 回报测算 → **§五 估值与回报**(共用情景,去重复情景表)
  - 旧 §三 快筛 + 旧 §十三 audit 红旗 + 旧 §十一 致命看空 → **§六 风险与红旗审计**(集中"什么会杀死它")
  - 旧 §十二 缺口 + 旧 §十三 来源 → **§八 数据来源与信息缺口**
  - 旧 §十一 定性 3 框架 → 折入 §四(维度 6 护城河 / 维度 10 催化剂 / 末尾"定性综合判断")
- **新 8 章节**: §一 执行摘要 / §二 公司基本面 / §三 行业与竞争对标 / §四 评分与维度证据 / §五 估值与回报 / §六 风险与红旗审计 / §七 舆情与市场情绪 / §八 数据来源与信息缺口
- **phase3 写手 5→4**: `agents/phase3-part5.md` 删除;part1=§一 / part2=§二/§三 / part3=§四/§五 / part4=§六/§七/§八。sub-agent 总数 9→8。
- 借鉴其它 skill 设计:**单一事实源**(`phase3-analysis-report.md` 不再逐章复写骨架,引用即可,~37KB→~18KB)、渐进披露(reference 按需加载)、执行摘要"决策仪表盘"优先。

### Fixed (清理 Phase 4/5 删除后的残留)

- **结构漂移修复**: 全仓 `15 章节 / 13 章节` → `8 章节`(`SKILL.md` 质量门控 / `phase-orchestration.md` / `assemble_report.py` / `build_html.py` / `report-checklist.json`)。`build_html.py` section 槽位改为从 `base.html` 动态发现。`anti_lazy_lint.py` MIN_SECTION_CHARS 重 calibrate 到 8 章节。
- **功能性 bug**: `review_loop.py` 硬编码 5 个 part 文件 md5(会因缺 `phase3-part5.md` 崩)→ 改 4 part;`test_assemble_report.py` 5-part 旧章节夹具 → 4-part 新章节;`install.sh` 引用已删 `phase4/5/persona/LEGACY` 文件(404)+ **从未下载 `agents/`(8 个 sub-agent)** + 漏 6 个关键脚本 → 全部补齐。
- **过时文档**: 重写 `README.md`(去 v4.1 角色/差异化/15章节) + `phase3-analysis-report.md` + `phase6-review-publish.md`(审核项 23→20,去 persona/variant 校验);删 `references/report-template.LEGACY.md`(20KB 死文件)+ `assets/validation/insight-card-schema.json`(Phase 5 死 schema)。
- `exec-summary-schema.md` 字段 6 去除对已删 Phase 5 的依赖,改"核心非共识判断(可选)"。

### Fixed (v6.0 收尾 — 补门控 + 清死代码)

- **Phase 2 加机器门控**: 新增 `scripts/check_phase2.py`(R1 §1-§8 齐全 / R2 §2 [PDF:] 原文引用≥3 / R3 §8 锚点≥5), 取代此前"全靠主 agent 自查"——Phase 2 不再是全流程唯一无机器门控的阶段。已接入 SKILL 质量门控表 / phase-orchestration / phase2 文档 / install.sh(scripts 23→24)。
- **Phase 7 证伪检查落地为 LLM-fill**: 删 `monitor.py` 的死 Phase-5 解析链(`_find_phase5_file`/`_check_insights`/`InsightCheck`/`insight_checks`)+ `report_parser.py` 的 `extract_insights`/`InsightPoint`(保留 baseline `[Tushare:*]` 标签解析)。§2 改为主 agent 从基线 §一 核心非共识判断 + §六 致命看空论证逐条填写; phase7 文档同步, 不再描述"脚本扫描证伪"。
- **删死代码/死样式**: `components.html` 差异化洞察卡 + `styles.css .section.variant-perception`(base.html 已无对应元素); `assemble_report.py` 未被调用的 `extract_metadata_blocks`(+ 其单测)。
- **文档残留**: `scripts/README.md` "Phase 1-5"→"1/2/3"; `SKILL.md` "6 阶段流水线"→"Phase 1/2/3/6"; `html-template-guide.md` 组件 10→9; assemble/build_html 注释里的旧 §十/variant 举例。

### Notes

- Phase 7 量化监控核心(基线指标对比 + 披露日 + 初判)可跑; §2 证伪现为 LLM 填写。脚本侧"真量化证伪"仍待 v5.3 规划升级。

---

## [v5.1.3] — 2026-05-04 — 紧急修复:删除不存在的 Agent API

> **主题**: 代码 review 发现 v5.1.0-1 整套调度协议建立在**不存在的 Agent 工具参数**之上,实际跑会立刻失败。原因:照搬外部参考"主智能体提示词.md"里的 `Agent(resume=ID, ...)` 写法,**未验证** Claude Code 实际工具 schema(`resume` 参数不存在)。

### Fixed (致命)

- **`Agent(resume=...)` 协议全删除** — Claude Code Agent 工具真实 schema 只有 description/isolation/model/prompt/run_in_background/subagent_type,**无 `resume`**。改为 **Fresh-Restart with Context Injection**:启动全新 sub-agent + prompt 注入上轮 FIX 列表
- **Agent ID 探测命令删除** — `ls -lt ~/.claude/projects/*/*/subagents/agent-*.meta.json` 读 Claude Code 内部目录(未公开 API) + 并行场景下竞态。Fresh-restart 不需要 ID
- **伪代码不存在函数清理** — `apply_fix_to_parts()` / `wait_all_background_agents()` / `output_to_user()` / `log_main()` 等都是空想 API。改为真脚本 `scripts/review_loop.py` + 自然语言 checklist

### Added

- **`scripts/review_loop.py`** (~250 行) — Phase 6 Part A.5 辅助:解析 3 reviewer 响应 / 合并 FIX 列表(P1-P5 分组去重) / 计算 phase3-part md5 diff signature / 输出 JSON 给主 agent 决策
- **`references/phase-orchestration.md`** — 每 Phase 详细 checklist(从 SKILL.md Step 3 拆出) + reviewer 修正循环步骤

### Changed

- **`SKILL.md`** 427 → 234 行(45% 压缩),遵守 Anthropic 渐进披露原则:保留路由必需 + Sub-agent 调用清单 + 调度协议总览;详细 checklist defer 到 `references/phase-orchestration.md`
- **`references/agent-protocol.md`** 重写 §1-§9:Agent 真实 schema / Fresh-Restart 协议 / 双层日志 / 修正循环不变量 / 自检结构 / lessons / 失败处理 / 工具不可用 fallback
- **frontmatter `description`** 简化为纯路由信号(去版本号 + 实现细节,从"v5.1.1 主智能体调度规范风格..."改为"分析单个上市公司...生成投资分析报告...")
- **4 处硬编码 `/Users/leafpaper/` 路径** 改为自适应定位(`./skills/company-analysis` → `$HOME/.claude/plugins/...` fallback,不硬编码用户名):`agents/data-collector.md` / `phases/phase1-data-collection.md` / `phases/phase7-quantitative-monitor.md`

### Deferred to v5.2

- SubagentStop hook 自动追加 main-log.md(需先 verify `$CLAUDE_COMPANY` / `$SUBAGENT_TYPE` 等 hook 环境变量)
- Phase 2 / Phase 5 sub-agent 化

---

## [v5.1.2] — 2026-05-04 — 数据采集扩展(5 项新覆盖)

### Added

**Tier 1 高价值**:
- `tushare_collector.py` 新增 3 方法 + `collect_all` 自动调用:
  - `share_float`(限售解禁,未来 365 天)— 减持窗口预警
  - `block_trade`(大宗交易,近 90 天)— 机构建仓/清仓真实时点
  - `anns`(公告摘要,近 90 天,接口名 fallback `anns/ann_d/anns_d`)
- `data_snapshot.md` §9 限售解禁日历(30 天 🔴 / 90 天 ⚠️),节数 8 → 9

**中等价值**:
- `capital_flow.md` §8 大宗交易段(成交次数 / 累计金额 / 折溢价信号 / 近 5 笔明细)
- `capital_flow.md` §9 北向资金加权建仓成本推导(净增仓 × 当日收盘价加权,输出浮盈/浮亏 + 信号)
- `peer_analysis.md` §4 行业全员 PE/PB 分布(全行业 min/p25/中位/p75/max + 目标分位 + 信号)
- `capital_flow.md` §10 综合警示加 2 规则:大宗交易折价 / 外资浮亏-浮盈

---

## [v5.1.1] — 2026-04-30 — SKILL.md 调度规范风格 + lessons-learned + reviewer 拆 3 并行

### Changed

- SKILL.md 414 → 379 行,重写为主 agent 视角调度规范(去 6+1 阶段流水线 ASCII 图)
- 删除旧 `agents/reviewer-agent.md`,新建 `reviewer-narrative.md` / `reviewer-valuation.md` / `reviewer-redflag.md`(3 并行)
- SKILL.md Phase 6 Part A.5 改为 `run_in_background=True` 3 并行(注:v5.1.0-1 Resume 协议在 v5.1.3 已删,实际仍 fresh-restart)

### Added

- `references/agent-protocol.md` §6 lessons 协议
- `scripts/lessons_manager.py` — append + recent 子命令(单条 200 字截断 / 类别上限 100 条超限归档 / 简单去重)
- 7 个 sub-agent 模板加可选 `**lessons**` 字段

---

## [v5.1] — 2026-04-29 — 主智能体调度协议层 + Phase 3 五子串行

### Added

- 5 个新 sub-agent `agents/phase3-part{1-5}.md` — 串行 part2→part3→part4→part5→part1(part1 最后写,执行摘要依赖前 4 part 评分加权)
- `references/agent-protocol.md` 首版

### Changed

- 三个老 sub-agent 补 YAML disallowedTools + 自检报告统一末尾(`**判定**:` 字段)
- reviewer 加章节→Part 映射 + FIX 单行 schema
- SKILL.md Step 2 创建 `main-log.md`
- ⚠️ **此版本写入的 Agent ID 探测 + Resume 协议在 v5.1.3 已全删**(API 不存在)

---

## [v5.0] — 2026-04-28 — sub-agent 大架构改造

### Added

- 新增 `agents/` 目录,首批 3 个 sub-agent:`data-collector.md` / `persona-agent.md` / `reviewer-agent.md`

### Changed

- SKILL.md Step 3 — Phase 1 / 4 / 6 改为 `Agent(subagent_type)` 调用
- 主 agent 不再直接采集数据 / 不再扮演 3 角色 / 不再评审

---

## [v4.6.2] — 2026-04-25 — 补 v4.6.1 的 preamble 丢失 + 内容命中率 ≥99% 自检

> **用户追问**: "你确定 MD→HTML 不会有任何缺失了吗?" — 经严格验证发现 v4.6.1 还有一层丢失。

### Fixed

**Preamble 区丢失** — v4.6.1 只处理 15 个固定 section + extra_sections(第 16+ `##`),但**第一个 `##` 之前的内容**(MD 顶部 title 后、首章 §一 前)全部被丢弃:
- 报告元数据(`报告期`/`最新收盘日期尾巴`/`总市值的 PE_TTM 说明`/`分析师的 skill 版本附注`)的详细部分 — hero 模板只填基础占位,后半说明丢失
- **关键:版本切换 blockquote**(如实丰 `> 本报告为 v3 全新版...历史版本 [v1] [v2]`)— 读者无法知道当前看的是哪一版

### Added

1. **`base.html` 新增 `<div class="preamble">` 区**:hero 之后、rating-trio 之前,填充主报告第一个 `##` 之前的内容
2. **`styles.css` 新增 `.preamble` 样式**:浅灰底 + 橙色左边框 + 小字号,区别于主 section
3. **`build_html.py` preamble 填充逻辑**:剥注释块 + 剥 title 行后转 HTML 注入
4. **内容命中率自检(核心!)**:
   - 算法:归一化 MD 每行(去标点/list marker/空白/URL)→ 取中间 20 字符指纹 → 在归一化 HTML 中查找
   - 阈值:≥ 98% 通过;< 90% 非零退出码
   - 7 家公司实测命中率:
     - 实丰文化 v4.1: **455/455 = 100.0%** ✅
     - 震安科技 v1: **335/335 = 100.0%** ✅
     - 西藏矿业 v1: **389/389 = 100.0%** ✅
     - 同泰怡 v1: **302/302 = 100.0%** ✅
     - Adobe v3: **165/166 = 99.4%** ✅
     - Circle v1: **284/285 = 99.6%** ✅
     - Starway v1: **250/251 = 99.6%** ✅
     - 平均 **99.9%**,剩余 ≤1% 是个别特殊格式的自检误报,非真实丢失

### Changed

- `_normalize()`: 简化为只保留 `\w` + CJK,忽略所有标点(全半角)
- sig 取指纹从"前 20 字符"改为"**中间 20 字符**",避免 list marker / bold 标记干扰
- URL 预处理:`[text](url)` → 只保留 `text`(HTML `<a>` 肉眼不显示 URL)

---

## [v4.6.1] — 2026-04-25 — HTML 生成脚本化 + 补 v4.6 3 处缺陷

> **主题**: 修 v4.6 上线 1 小时后用户发现的 3 个问题。

### Fixed (v4.6 → v4.6.1)

1. **MD → HTML 转换丢章节**: v4.6 主报告 17 个 `##` 章节, base.html 只有 15 个固定 placeholder (§一 ~ §十五), 附录的第 16/17 (v4 修订日志 / v4.1 补丁) 被完全丢弃
   - 修: base.html 在 §十五 后加 `<!-- PLACEHOLDER: extra_sections -->`, build_html.py 把第 16+ 章节自动追加到这里
   - 修: 新增 `scripts/build_html.py` (~300 行) 替代 LLM inline Python 做 MD → HTML 转换, 保证 section 零丢失
   - 副产物: 修了一个隐蔽的 `re.sub` bug — markdown 输出 HTML 中的 `\g` 会被当反向引用, 改用 lambda repl 避开

2. **粘性侧边栏改为顶部横排**: 用户反馈"关键指标放旁边没必要, 放最上面就行"
   - `<aside class="metric-sidebar">` 粘性右栏 → `<div class="metric-strip">` 顶部横排 (8 个 metric-chip 平铺)
   - `.container.has-sidebar` 两栏 → 普通单栏
   - `.metric-sidebar` 保留但降级为块级显示, 向后兼容 v4.6 老报告

3. **主页去"龟龟策略"文案**: 用户反馈"龟龟策略的表述可以去掉"
   - `<title>`: "Inves Reports · 龟龟投资策略" → "叶纸的投资分析报告 · Inves Reports"
   - `.hero-badge`: "✦ 龟龟投资策略 v2 ✦" → "✦ AI 投资分析 v4.6 ✦"
   - `<h1>`: "🐢 叶纸的投资分析报告" → "叶纸的投资分析报告"(去🐢)
   - hero `<p>`: "基于龟龟策略框架..." → "基于 11 大师框架的定量审计 + DCF 概率加权估值..."
   - footer: "🐢 基于龟龟策略框架..." → "AI 自动生成 · v4.6 动态联动 · 11 大师框架审计"
   - `.nav-logo` 仍保留小🐢 + "叶纸的投资报告"(作为个人身份,非策略表述)

### Added

- **`scripts/build_html.py`** (~300 行)
  - `_parse_structured_block()`: 解析 RATING_TRIO_DATA / KEY_METRICS_SIDEBAR / CARD_METADATA 注释块
  - `split_sections()`: 按 `^## ` 稳健切 MD, 保留所有章节
  - `build_rating_trio()`: 按 data 生成 3 张 rating-card
  - `build_metric_strip()`: 按 data 生成 5-8 个 metric-chip (取代 sidebar)
  - `build_html()`: 主流程, 自检 + 自动报警
  - CLI: `python3 -m scripts.build_html --company X --md Y --out Z`

- **assets/html/styles.css**: 新增 `.metric-strip` + `.metric-chip` 样式(横排自适应 5-8 chip), 保留 `.metric-sidebar` 降级为块式

- **assets/html/base.html**: 去 `has-sidebar` 两栏, 在 hero + rating-trio 后加 `<div class="metric-strip">` 顶部面板, 在 §十五 后加 `extra_sections` 占位

- **assets/html/components.html**: 新增 `.metric-strip` 完整 8 chip 片段

### Changed

- `phases/phase6-review-publish.md` Part B: 改为"推荐 `python3 -m scripts.build_html`"自动化, 手动流程降为备选
- `install.sh`: scripts 数 16 → 17 (加 build_html)

### Verified

- 实丰 002862 重生 HTML: 17 section 全入 (15 固定 id + extra-1 + extra-2), metric-chip 8 个, rating-card 3 个, 0 个 {{placeholder}} 残留

---

## [v4.6] — 2026-04-25 — 大厂风格 HTML + 主页动态联动

> **主题**: 两个用户反馈方向合并实现:①主页手工维护痛点(每次加新报告都要 Edit index.html);②报告 HTML 视觉单调,缺大厂标配元素。

### 根因

1. **主页联动**: `phase6-review-publish.md Part C` 第 4 步写的是"手工编辑 index.html" —— 14 张卡片硬编码 + 4 个统计数字硬编码,每次新报告 5-10 分钟手工维护,易遗漏
2. **报告单调**: 国外大厂(Goldman / Morgan Stanley / Bloomberg / Morningstar)标配的"前置评级卡 / 彩条风险 / 粘性侧边栏 / 对标卡 / 热力图 / 深度内链"全部缺失

### Added

#### 1. Inves-Report 仓库侧(`/tmp/Inves-Report-v2/` → `github.com/leafpaper/Inves-Report`)

- **`data/reports.json`**: 所有报告的元数据 JSON(ticker / 评分 / verdict / tone / 一句话结论 / 指标 / badge 等)
- **`assets/css/main.css`**: 从 index.html 内联 CSS 抽出(~300 行)+ 新增搜索/筛选/排序 UI 样式
- **`assets/js/render.js`**: fetch reports.json → 按 market 分组 → 渲染卡片 + 搜索 + 市场 tab + 排序 + 评分筛选
- **`index.html`**: 从 500 行压缩为 **~130 行骨架**,所有卡片由 JS 动态渲染
- **搜索/筛选 UI**: 全文搜索框 + 市场 tab(全部/美股/A股/港股/一级) + 排序下拉(最新/评分/收益) + 评分筛选(全部/≥4/≥6/≥7.5)

#### 2. skill 侧 HTML 大厂风格升级

**`assets/html/styles.css`** 新增 6 个组件 class(~300 行新代码):
- `.rating-trio` + `.rating-card` — Goldman 风格前置三件套(评分/估值锚/期望收益)
- `.risk-card-v2` + `risk-critical/high/medium/low` — Bloomberg 风格彩条风险卡(替代 Markdown 表格)
- `.metric-sidebar` + `.metric-row` — 粘性侧边栏(right 260px,滚动常驻,展示 5-8 关键指标)
- `.comparison-card` + `cmp-col center/bar` — Morningstar 风格对标卡(你 vs peer 中位 vs 历史)
- `.deep-link` + `:target` 脉冲 — 章节内链跳转 + 高亮动画
- `.heatmap-grid` + `.hm-cell.hm--2/--1/0/1/2` — 微型 5 档色块热力图

**`assets/html/base.html`** 改造:
- `<div class="container">` → `<div class="container has-sidebar">` 两栏布局
- hero 下新增 `<div class="rating-trio">` 前置评级卡占位
- body 右侧新增 `<aside class="metric-sidebar">` 粘性关键指标

**`assets/html/components.html`** 加 6 个新片段(供 Phase 6 按数据填充)

**`assets/templates/report-skeleton.md`** 补 3 个 HTML 注释结构化块(Phase 3 写报告时填):
- `<!-- RATING_TRIO_DATA: ... -->` 前置评级卡数据
- `<!-- KEY_METRICS_SIDEBAR: ... -->` 侧边栏 5-8 指标
- `<!-- CARD_METADATA: ... -->` 主页卡片元数据(sector/market/one_liner/top_risks_short)

#### 3. `scripts/update_index.py` 新增(~300 行)

- 解析主报告 MD 的 3 个结构化注释块(100% 精准)
- Fallback: 老报告走 regex 抽取(部分字段可能不准,会输出警告)
- 生成 `output/{company}/card-metadata.json`
- 复制到 `/tmp/Inves-Report/reports/{slug}/card-metadata.json`
- upsert 合并到 `/tmp/Inves-Report/data/reports.json`(by ticker match, --force 覆盖)
- 自动按 report_date 降序排序 + 重算统计

#### 4. 风格配色升级

- 保留 Goldman 深蓝主色 `--c-primary: #1a56db`
- 新增 Bloomberg 高对比风险等级色: `--c-risk-red/amber/yellow/green`
- 新增 Morningstar 卡片化灰阶: `--c-card-border/header/hover`

### Changed

- **`phases/phase6-review-publish.md`** Part B:新增 Step 3.5 强制填 rating-trio + metric-sidebar
- **`phases/phase6-review-publish.md`** Part C:Step 4 "手工编辑 index.html" → `python3 -m scripts.update_index` 自动调用
- **Part C Step 5** git add 从 `-A` 收紧为 `reports/{slug}/ data/reports.json`(避免误提交)

### Verified

- 实丰 002862 v4.1 报告:抽结构化块后精准得到 sector="玩具 + 游戏 + 光伏参股" / expected_return="-44.1%" / valuation_tag="估值锚 10.1 元"
- 主页本地启 `python3 -m http.server 8766` 验证:10 张卡片动态渲染 / 搜索"实丰"筛选正确 / 市场 tab 切换正确 / 统计数字从 reports.json 实时算
- HTML 重生成:rating-trio 出现 1 次(正确) / metric-sidebar 出现 13 次(CSS + HTML 结构) / has-sidebar 出现 5 次 / 178 个 CSS 变量引用

### Known limitations

- `update_index.py` 对 **v4.6 之前的老报告**(无 CARD_METADATA 注释块)走 regex fallback,sector/expected_return 等可能不准 — 需手工检查 reports.json
- 移动端 sidebar 折叠成顺序(未做复杂响应式)
- 深色模式未做
- GitHub Action 自动扫描报告目录推迟到 v4.7

---

## [v4.5] — 2026-04-25 — capital_flow 口径修正 + 家族一致行动人识别

> **主题**:修复 v4.4 `capital_flow.py` 在限售股占比高的公司严重低估实控人控盘度的 bug。用户在实丰文化分析中发现 "蔡氏家族真实持股 40% vs 脚本报告 22.61%" 的矛盾,追溯到数据源口径错误。

### 根因

v4.4 `capital_flow.py _derive_metrics` 只拉 `top10_floatholders`(前十大**流通**股东,不含限售),对实控人大量持有限售股的公司(典型上市 3 年内 / 股权激励未解锁 / 家族控股)**严重低估真实控盘度**:

**实丰文化案例**(2025 年报):
- v4.4 输出: 主力控盘度 22.61% (🟢 分散)
- 真实情况: 前 10 大全体股东 **47.46%** + 蔡氏家族合计 **40.77%** (🔴 绝对控盘)
- 差 17.4 pp,定性判断从 🟢 变 🔴(反向!)

### Fixed

- **`scripts/capital_flow.py`**:
  - 新增 `raw["top10_all"]` 数据源(`tushare.top10_holders`,含限售股)
  - `_derive_metrics` 控盘度改用 `top10_all` 优先,`top10_float` 降为补充参考
  - 新增启发式 `_family_control()`:识别同姓自然人股东合并算"实控人家族合计"
  - 输出 3 个口径:前 10 大总股东占总股本 / 前 10 大流通占总股本(旧)/ 前 10 大流通占流通股本
  - 综合档位:前 10 大 ≥50% 🔴 / ≥30% 🟡 / <30% 🟢
  - 家族档位:≥40% 🔴 绝对控盘 / ≥25% 🟡 相对控盘 / <25% 🟢 非控盘
- **`_format_markdown`**:
  - §1 综合判定表从 6 维度 → **7 维度**(新增 "实控人家族合计持股" 独立行)
  - §2 "前十大流通股东" → **"前十大全体股东(含限售)"**
  - §8 警示规则:家族控盘 ≥40% 触发 🔴 关联交易/大股东占款风险提示

### Known limitations

- `_family_control()` 是**启发式识别**(同姓自然人),**不替代年报"一致行动人"正式披露**:
  - 对**姓氏不同的一致行动人**(夫妻、姻亲)漏识别
  - 对**通过控股公司实控**的结构识别不全(如闻泰的"张学政 → 闻天下科技集团"路径,只识别到张学政 2.97%,漏了闻天下 12.37%)
  - Phase 3 §四"主力控盘"子节的 LLM 仍应**手工核对**年报的"实际控制人"章节

### Regression

- 闻泰 600745.SH 回归:控盘度 44.79% 不变(该股限售已解锁,top10_all = top10_float),家族识别到张学政 2.97%(算法能识别单自然人)
- 实丰 002862.SZ 验证:控盘度 22.61% → **47.46%**,家族 **40.77%** 自动识别 ✅

---

## [v4.4] — 2026-04-24 — 技术分析 + 可比公司 + 主力控盘三合一

> **主题**:补齐 A 股投资者最关心的 3 个空白 — 技术面、同行对标、机构/主力控盘。
> 所有逻辑下沉到 Python 脚本,Phase 指令仅作触发器;Phase 3 对应章节强制 Read 结构化 artifact(不再 LLM 凭记忆)。

### 根因

用户反馈 skill 只有基本面审计,**A 股投资者最核心的 3 个维度全部空白**:
- 技术面分析 = 0(有 3 年日线数据但没算 MA/MACD/RSI)
- 可比公司对比 = LLM 手写猜竞品
- 主力控盘/资金流 = 只用了 top10_holders + stk_holdernumber,完全没消费陆股通/两融/龙虎榜/大单资金流

### Added

#### 1. `scripts/peer_collector.py` — A 股同行业自动采集

- 基于 `stock_basic.industry` + `daily_basic` 按市值相近度排序取 Top N peer
- 输出 `peer_analysis.md`: §1 对比表(6 行 × 13 列) + §2 分位分析(ROE/毛利/净利/PE/PB/增速 6 维度) + §3 硬判定对比洞察
- 闻泰实跑: 5 家同行业 peer(格科微/全志/国科/星宸/赛微),PB 分位 100%(最便宜),毛利率分位 20%(落后),**事实客观**

#### 2. `scripts/capital_flow.py` — 主力控盘与资金流向(6 接口 + 6 推导指标)

**数据源**(Tushare 2000+ 积分):
- `moneyflow`(个股主力资金近 60 日)
- `moneyflow_hsgt`(陆股通大盘)
- `hk_hold`(陆股通个股持股每日)
- `margin_detail`(两融每日)
- `top_list` + `top_inst`(龙虎榜 + 机构席位近 30 日)

**推导 6 控盘指标**(每个都有🟢/🟡/🔴 自动档位):
1. 主力控盘度(前 10 流通股东合计持股 <30% / 30-50% / ≥50%)
2. 筹码集中度 2×2 矩阵(户数变化 × 户均持股)
3. 陆股通持仓趋势(20/60 日变化)
4. 两融杠杆方向(融资余额相对 60 日中位数)
5. 主力资金流(近 20 日大单净流入天数)
6. 龙虎榜机构活跃(上榜次数 + 机构净买入)

**闻泰实跑**:🔴 "筹码分散(户数+5.7%, 户均-5.4%)= 机构退出, 散户涌入" + 🔴 "主力资金近 20 日仅 6 日净流入, 累计 -2,692 万" — **精确定量打脸散户信心**

#### 3. `scripts/technical_analysis.py` — MA/MACD/RSI/布林带/成交量/支撑阻力

- 输入: Phase 1 `daily.parquet`(近 3 年日线)
- 指标: MA5/20/60/120 排列、MACD(12,26,9)金叉死叉、RSI(14)超买超卖、BOLL(20,2σ)位置、成交量异常、近 60/120 日支撑阻力位
- **闻泰实跑**: 3 🔴 信号 — 均线空头排列 + 破 MA120 + MACD 死叉;近 60 日 -28%;距 60 日支撑 28.27 元仅 0.28%(几乎贴底)

### Changed

- **Phase 1 指令** (`phases/phase1-data-collection.md`) 新增 3 步:
  - Step 1.2 `peer_collector` → `peer_analysis.md`
  - Step 1.3 `capital_flow` → `capital_flow.md`
  - Step 1.4 `technical_analysis` → `technical_analysis.md`

- **Phase 3 指令** (`phases/phase3-analysis-report.md`) 强制联动:
  - Step 4 §四 公司基本面 加 **"主力控盘与筹码分析"** 子节 → Read `capital_flow.md` §1/§2/§3/§8
  - Step 8 §八 可比公司对标 **强制 Read `peer_analysis.md`** → §1 对比表 + §2 分位 + §3 洞察直接搬入,禁止凭记忆猜竞品
  - Step 9 §九 估值末尾加 **9.4 技术面位置** 子节 → Read `technical_analysis.md`,必写"基本面 × 技术面" 4 种配合判断
  - Step 12 自检清单加 3 项(§四/§七/§八/§九 强制联动)

- **`assets/templates/report-skeleton.md`** 骨架更新:
  - §四 加 `capital_flow_summary_table / top10_float_holders_table / chip_concentration_2x2` 3 个 placeholder
  - §七 `资金流向信号` 改为 Read `capital_flow.md` §4/§5/§6
  - §八 骨架改为 §8.1-8.4 四子节(A 股 peer / 分位 / 洞察 / 海外补充)
  - §九 加 9.4 `技术面位置` 子节 + 3 个 placeholder

- **`assets/validation/report-checklist.json`** 新增 `phase3_mandatory_data_artifacts` section,列出 4 个必须消费的 artifact

- **Phase 6 审核清单** 从 22 项扩至 **23 项**(新增 #23 "Phase 1 结构化 artifact 消费"检查)

### Coverage

- 🇨🇳 A 股: 5 个 Python 模块全部可用(tushare_collector + financial_audit + peer_collector + capital_flow + technical_analysis)
- 🇺🇸 美股: 仅 yfinance + financial_audit,peer/capital/tech 三模块暂不支持
- 🇭🇰 港股: 同美股

### Not in scope (v4.5 继续)

- ❌ `scripts/validate_report.py` validator(仍推迟)
- ❌ `scripts/event_backtest.py`(业绩预告/回购/增持事件 → 次日/次月股价表现的历史规律)
- ❌ 美股/港股版本的 peer/capital/tech 3 模块

---

## [v4.3] — 2026-04-24 — assets 目录 + 报告骨架强制化

> **主题**:符合 Anthropic 官方 skill 规范的资产分离,修复"每次报告格式都不一样"的根因。

### 根因诊断(用户反馈驱动)

用户反馈 2 个问题,调研发现是**同一个根因的 3 重坏**:
1. "我怎么没有用 assets" — skill 从未建 `assets/` 目录
2. "每次报告的风格都不一样" — 3 份历史报告(闻泰/实丰/震安)的 Exec Summary 字段名和字段数量完全不同

**根因**:
- `references/report-template.md` 本身是坏的(12 章节 + 两个"四"、两个"五")
- Phase 3 指令**从未加载**它 → LLM 每次凭记忆生成 15 章节
- `references/html-template-guide.md` 是纯散文,没有真实 `.css` 或 `.html` 文件 → HTML 样式每次重写

### Added

- **`assets/` 目录**(官方 L3 资源层,按需加载,零上下文成本)
  - `assets/templates/report-skeleton.md` — 15 章节严格骨架 + `{{placeholder}}`(Phase 3 强制加载)
  - `assets/templates/exec-summary-schema.md` — Exec Summary 7 固定字段 + 6 类禁用字段黑名单
  - `assets/html/base.html` — HTML 骨架(sticky nav + hero + 15 section placeholder + footer)
  - `assets/html/styles.css` — 真 CSS 文件(16 变量 + 9 组件样式 + 响应式 + 打印)
  - `assets/html/components.html` — 10 个组件片段库(评分环/维度条/4 情景卡/期望回报/团队名片/风险项/时间轴/情绪量表/估值区间/洞察卡片)
  - `assets/validation/report-checklist.json` — 机器可读的 22 项审核清单(供 v4.4 validator)
  - `assets/validation/insight-card-schema.json` — Phase 5 9 字段 schema

### Changed

- **Phase 3 指令**(`phases/phase3-analysis-report.md`)
  - 新增 **Step 0.5 强制加载骨架**:Read `assets/templates/report-skeleton.md` + `exec-summary-schema.md`
  - Step 12 组装规则改为"以骨架为真相源",15 章节列表指向骨架文件
  - 分段写入 5 批的内容描述改为"填充骨架对应章节 placeholder"
  - 新增自检指令:`grep -c '^## §' *.md` 应 = 15

- **Phase 6 指令**(`phases/phase6-review-publish.md`)
  - Part B HTML 生成改为"Read assets/html/base.html + styles.css + components.html 并按占位填充"
  - 禁止凭记忆重写 CSS、自创变量名、自命名组件 class
  - 修复 L103-121 章节表 bug(原表跳过 §十一,编号错乱)→ 新 15 章节表与骨架字节对齐
  - 审核清单从 20 项扩至 **22 项**:
    - #21 HTML 资产加载(`grep -c '^\s*--c-' *.html` ≥16, 组件命中率 ≥8/9)
    - #22 Exec Summary 7 字段 schema(禁用字段黑名单扫描)

- **`references/report-template.md` → `report-template.LEGACY.md`**(改名废弃,加头注"已废弃,用 assets/templates/report-skeleton.md")
- **`references/html-template-guide.md` 精简**(删除所有代码块,保留设计哲学;所有可执行代码迁至 `assets/html/`)
- **`SKILL.md`** 参考索引表补充 `assets/` 三个子目录;废弃 `report-template.md` 行

### Fixed

- `references/report-template.md` 章节号错乱(两个"四"、两个"五",总数仅 12 章节)——从根本上靠骨架文件替代
- Phase 6 L103-121 章节表跳过 §十一(从 §十 直接到 §十二)——修正为完整 15 章节顺序

### Not in scope (v4.4 继续)

- ❌ `scripts/validate_report.py` validator 脚本 — 推迟到 v4.4,基于 v4.3 新骨架稳定 1-2 次后定规则
- ❌ 翻修已发布的闻泰/实丰/震安 HTML(保留作历史对照)
- ❌ 多语言模板

### 向后兼容

- `scripts/report_parser.py` **不需要改** — 它按 `[Tushare:*]`/`[PDF:*]` 标签匹配,不按章节标题,历史报告监控不受影响
- 已发布的 GitHub Pages 报告链接保持有效

---

## [v4.2] — 2026-04-24 — 估值一致性 + 核心资产剥离 SOTP

> **主题**：修复真实案例（闻泰科技 600745.SH 分析）暴露的 3 个估值框架缺陷，防止未来同类错误。

### Fixed (3 个真实案例暴露的缺陷)

1. **估值锚与投资回报锚不一致**
   - 症状：§九"三角验证均值 30.6 元" vs §十"投资回报基准 33.8 元" 两个数字让读者混淆
   - 修复：`references/valuation-frameworks.md §3.3` 改为"交叉验证"而非均值；`phase3-analysis-report.md Step 9` 强制 DCF 概率加权为**唯一锚**，§十 与 §九 共用情景
   - 新增 Phase 6 审核项 #19：§九 与 §十 共用情景/概率分布不一致则审核不通过

2. **悲观情景 SOTP 不完整**
   - 症状：悲观情景只算"核心资产按 1x PB 出售"，忽略母公司剩余现金/金融资产/负债/清算成本
   - 修复：`valuation-frameworks.md` 新增 §3.4 **核心资产剥离风险的 SOTP 强制要求**；`phase3-analysis-report.md` 新增 **Step 9.5** 触发条件与两步强制执行
   - 新增 Phase 6 审核项 #20：若触发但缺"剩余资产清单"或"最差情景"则不通过

3. **"剥离后剩什么"缺乏披露**
   - 症状：主报告没有"若核心资产被剥离，上市公司还剩什么资产"的清单，读者无法评估下行地板
   - 修复：`phase3-analysis-report.md Step 9.5.1` 强制在 §四 业务概况加子节"★ 若核心资产被剥离的剩余资产清单"，明细列出 7 项可变现资产 + 3 项负债

### Added

- **4 情景 DCF**（乐观/基准/悲观 + **最差 3-10% 权重**）替代 3 情景，最差情景作为 tail risk floor
- **估值表角色列**: DCF 概率加权 = ⭐ 估值锚；可比倍数/PB = 交叉验证（自洽判定 < 10% ✓ / 10-20% ⚠ / > 20% 🔴）

### Changed

- `phase6-review-publish.md`：审核清单从 18 项扩至 **20 项**
- `phase3-analysis-report.md Step 7/9/9.5/11` 逻辑重构

---

## [v4.1] — 2026-04-24 — 精简 + 关键信息保护

> **主题**：激进精简阅读负荷（-40%），同时 100% 保护防作弊机制、监控链路、分歧多样性。

### Changed
- **定性判断框架 4 → 3**：删除"估值判断"框架（§九 估值分析 + `audit_report.md` 的 Valuation Anomaly 已完全覆盖）
- **洞察字段 13 → 9**：合并"证据等级 + 置信度 + 时间窗"为单行"信号强度"（`Level A / 高 / 1Y` 格式）；删除低价值字段（议题来源 / 信息不对称 edge 分类 / 类型）
- **Phase 4 结构精简**：3 角色保留，每角色从 5 段 → 3 段固定结构（核心结论 / 最担忧风险 / 对 1 条洞察回应），总篇幅 -60%
- **Phase 4/5 独立文件职责重定义**：独立文件不再重复主报告内容，只保留主报告没有的深度附件（Level C 附录 / 议题感知 / 共识映射 / 哲学分歧深度解读）
- **§二评分总览**删"关键理由"列（证据由 §六 承接）
- **§三快筛 vs §十一 致命看空去重**：§十一 直接引用 §三 结果，不重复列 6 项
- **§十五数据来源按 3 类分组**（Tushare API / PDF 原文 / WebSearch）
- **§四.5 / §六.2 改为正常子节编号**（`### 管理层前瞻信号` / `### 资金流向信号`）
- **黑白分割规则**：3 框架中 ≥ 2 同向 → 对应方向；否则中性-分歧

### Fixed
- `scripts/report_parser.py` 扩展 `FIELD_SIGNAL_STRENGTH` 正则支持 v4.1 合并字段，同时向后兼容 v3 分离字段

### Preserved (关键信息保护)
- ✅ 证据等级 A/B/C（防 Level C 伪推理）
- ✅ 时间窗（Phase 7 monitor 用）
- ✅ 证伪条件（monitor 自动扫描）
- ✅ 数学推导（v4 防猜测核心）
- ✅ Level C 附录（Phase 6 Part D 补查输入）
- ✅ 关键议题感知清单 / 市场共识映射
- ✅ 3 种投资哲学分歧多样性（保留 3 角色）

---

## [v4.0] — 2026-04-23 — Python 数据层 + 大师框架 + 量化监控

> **主题**：从"LLM 凭感觉写"进化为"结构化数据 + 学术框架 + 可审计"。

### Added
- **Python 数据层 `scripts/`（10 模块）**:
  - `tushare_collector.py`：A 股 25 个 API（3 大报表 + 股东 + 质押 + 业绩预告 + 高管薪酬 + 股东户数 + 回购 + 分业务 + 北向 + 披露日历）
  - `us_collector.py`：美股 yfinance 封装
  - `hk_collector.py`：港股 Tushare + yfinance 混合
  - `pdf_reader.py`：财报 PDF 9 段落精析（利润表变动原因 / 子公司业绩 / MD&A / 风险因素 / 非经 / 前十大股东 / 资产负债变动 / 现金流变动 / 主要会计数据）
  - `derived_metrics.py`：30+ 衍生指标（CAGR / FCF / ROIC / Owner Earnings）
  - `data_cache.py`：7 天 TTL Parquet 缓存
  - `financial_audit.py`：**11 大师框架异常审计**
  - `report_parser.py`：解析历史报告带标签指标
  - `monitor.py`：量化监控核心
- **Phase 7 量化监控**：`/company-analysis <公司> --monitor` 手动触发
- **Phase 3 Step 1.5 自动 audit**：生成 `audit_report.md` + JSON
- **11 大师框架**：
  - Piotroski F-Score（0-9 分财务健康）
  - Beneish M-Score（盈余操纵检测）
  - Altman Z-Score（破产预警）
  - DuPont 5-Factor（ROE 归因）
  - Buffett Quality（OCF/NI / 应收 / 存货 / 商誉 / 非经）
  - Sloan Accrual Anomaly
  - Governance Red Flags（质押 / 减持 / CEO 对齐）
  - Shareholder Flow（户数×户均 2×2 矩阵）
  - Forward Guidance Anomaly（首亏 / 预减 / 区间宽度）
  - **Valuation Anomaly**（PB 历史分位 + **PB vs ROE Gordon 错配**）
  - Related-Party Exposure（长期股权投资波动 + 投资收益爆雷）

### Changed
- **Phase 顺序重排**：`P1 → P2 → P3 → P4 → P5(差异化) → P6(审核)`（原 Phase 2.5 后移为 Phase 5）
- **Phase 5 输入源 4 个**：Phase 1 数据 + Phase 2 PDF + Phase 3 画像 + **Phase 4 角色分歧（新）**
- **SKILL.md 协调器显式化**：前 80 行含 ASCII 流程图 + 快速导航 + 职责清单
- **每个 phase 顶部加面包屑导航**
- **洞察 11 → 13 字段**：新增 ★数学推导 + ★证据等级 A/B/C
- **洞察数学推导反例库防伪**：5 种伪推导命中即降级 Level C
- **§三快筛新增第 6 项**：Audit ≥ 2 个 🔴 触发快筛否决
- **7 定性框架 → 4 框架**（v4.0 版本，v4.1 再精简为 3）
- **章节合并**：§九估值 + §十一投资回报 → 合并；§十四时效性 + §十五信息来源 → 合并
- **Tushare 字段精简**：income 85→32 / balancesheet 152→44 / cashflow 97→34（存储 -70%）

### Fixed
- v3 审计发现的 5 个系统性缺陷全部修复：
  1. 财报获取依赖第三方摘要 → 强制 PDF 原文
  2. 洞察允许纯推理 → 强制数学推导
  3. 定性判断只是打分 → 改为逻辑三段式
  4. 信息缺口不闭环 → Part D 5 步穷举补查
  5. 无结构化数据层 → Tushare + yfinance + pypdf

---

## [v3.3] — 2026-04-20

### Added
- Phase 2.5 差异化洞察（Variant Perception）

---

## [v3.2] — 2026-04-19

### Added
- 协调器质量门控（每阶段检查清单）
- HTML 完整性强制（HTML section ≥ MD ## × 0.8）
- 分段写入保护（避免超长报告丢失内容）

---

## [v3.1] — 2026-04-18

### Added
- output 目录结构规范（`output/{company}/`）
- Phase 2 自动搜索模式（用户未提供文档时）
- Phase 3 深度分析增强

---

## [v3.0] — 2026-04-16

### Added
- 5 阶段流水线（数据采集 / 文档精析 / 综合分析 / 多角色结论 / 审核发布）
- 上市公司支持（A股 / 美股 / 港股）
- 多角色投资人评审（段永平 / 巴菲特 / 张磊 等）
- 10 维度事实评分

---

## [v2] — 历史版本

### v2 修订
- 实丰文化案例发现 v1 归因错误（应为超隆光电参股爆雷）
- 新增手工精读 PDF 流程
- 评分计算错误修正

---

## [v1] — 初版

- 基础 skill 框架
- WebSearch 驱动的数据采集
- 基于第三方摘要的分析（已被 v4 取代）
