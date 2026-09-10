# 07 — 交付:B 仪表盘 HTML + 移动端 + 明暗主题

**What to build:** 报告 HTML 换第二套 B「仪表盘·一眼决断」版式(07 prototype 定稿,无杂交):决断卡=5 张 verdict 瓦片、赚钱面板=stat tiles+红标角标、Top3=风险卡,扫读优先、密度即价值。红标三通道=emoji+文字+底纹(不裸靠颜色),🔴/🟠 红色系(emoji 分级)、🟡 黄色系,明暗双主题各定 token 且对比度达标;反查交互:桌面悬停浮层(红旗标题/级别/一句证据/来源/归属节点),触屏点击红标直达附录D 条目锚点。移动端一等场景:瓦片单列重排、所有表格强制横滚容器、正文子判定表≤3-4 列、禁缩字号。站点 index 卡片改版:verdict=行动档位人话+新增质地字段。视觉基线=第二套 B 样张(见 [v8-refactor issues/07](../../v8-refactor/issues/07-delivery-prototype.md) 所记链接与 prototypes 文件)。

**Blocked by:** 04(消费装配产物与红标反查映射)

**Status:** done(2026-08-17)

- [x] 东山 fixture 装配产物 → 成品 HTML:390px 走查通过(无横向溢出、无 12px 缩字、瓦片单列)
      —— 机检部分已落测试:所有表格在 `.tblwrap` 横滚容器内、`.wrap{overflow-x:clip}` 挡住绝对定位浮层、
      媒体查询里零 font-size(改结构不缩字号)、最小字号 12.5px、620px 断点下 cards5/tiles/appxnav 全单列、
      720px 断点下顶导航由吸顶改静态。**浏览器里的目测走查仍归 reviewer-delivery**(spec Testing Decisions)。
- [x] 红标三通道齐备(emoji + 文字级别词 + 底纹,任一通道单独可读);明/暗两套 token 用 WCAG 公式机检:
      正文/次要文字对页面、卡片、红/黄/绿/蓝底纹全部 ≥4.5:1,链接与红标封条 ≥3:1
- [x] 桌面悬停浮层与触屏点击跳附录D 锚点均可用(同一个 `<a class="fw">` 元素:hover/focus 弹浮层、
      点击走锚点;触屏与窄屏 `display:none` 掉浮层,`title` 属性兜底反查)
- [x] index 卡片显示行动档位人话+质地字段(另加 action_gear / next_disclosure_date 供站点陈旧警示);
      宽表格均在横滚容器内

**实现落点**:`assets/html/report-v8.{html,css}`(新版式)、`scripts/build_html.py` v8 通道(有 assembly.json
即走仪表盘,否则回落 v7 槽位)、`scripts/update_index.py` v8 卡片版式、`scripts/tests/test_delivery_html_v8.py`
(42 项,东山 fixture 全链路 run 目录 → 装配 → 成品 HTML)。

**两处实现取舍**(留给后续票/评审):
1. **瓦片语气不由 verdict 文本推导**——契约里没有 tone 字段,从 verdict 文本猜语气等于展示层自产判断。
   实现取:⑤怎么办按行动档位(复用 update_index 六档映射),①-④ 按**本节点红旗载荷**(红旗条目的 node
   是契约字段),并在瓦片上写明「🟠×2 🟡×2 红旗」,颜色含义外显、不冒充 verdict。
2. **正文红标靠逐字反查**——红旗标题/面板指标名在正文逐字命中才标,短于 4 字的词(FCF/ROE)不进词表
   (否则会命中表头与无关句子)。写手若在正文写 `[附录D](#flag-xxx)` 引用,该链接会自动升级成同一套红标。
