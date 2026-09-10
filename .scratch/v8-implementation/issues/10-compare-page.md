# 10 — 产业链对比 --compare

**What to build:** `--compare <锚公司>` 产业链同行对比页,答「同行组里钱该放哪家」。成组流程:自动查候选 5-8 家(优先级:Longbridge 产业链/成分股工具 → 报告库内 peer 对标 → 模型按业务描述兜底)→ 用户确认/增删成组 → slug 由用户命名(系统建议产业链 kebab-case 英文短名,兜底 {锚ticker}-peers)。全报告制:只在有完整报告的成员间对比,缺报告成员成组时列出、用户决定分批补跑。产出一页上下两半:上半=各家决断卡/四问 verdict/区间锚/Top3 从各家 manifest 最新 YAML 块机器装配并排(零新判断)+ 每家基准日 + 超 90 天标「陈旧」提示先 --review;下半=compare-judge「组内裁决」具名节点(只读各家决断卡,产排序+每家一句原因,过 schema,不自产证据)。交付:Inves-Report 独立对比页+本地 md 底稿,首页对比卡与单报告卡并列、互相可点。联动:--review 收尾读 manifest 对比组字段,在组内→提示一句,确认后重装配对比页(卡片刷新+裁决重跑);不做自动联动。

**Blocked by:** 08(成员需 v8 报告与 manifest)、09(复查收尾联动改 --review 链尾)

**Status:** done(2026-09-01)

- [~] 东山+中际旭创成组走通:候选查询(按优先级三路)→确认→slug→对比页发布可看,每家可点回单报告
      —— **链路走通了,第二家不是中际旭创**:C0→C4 全段用真实东山 run(只读拷贝)+ 一家标明合成的同行
      端到端跑过(CLI 全绿,页面 27.8k chars,回链 = update_index 同一套 slug)。中际旭创在库里没有
      v8 报告,它这次落在「缺报告成员」那条路径上并被正确列出。**live demo 待第二份真报告**。
- [x] 上半并排卡片全部取自各家 YAML 块,零新判断;基准日标注,超 90 天成员标「陈旧」
      —— 测试逐格比对成员 assembly.json;陈旧档线写进产物 `stale_threshold_days`,不做隐藏常量
- [x] compare-judge 裁决过 schema:排序+每家一句,只引用各报告结论
      —— schema + **四条机检**(具名成员/排名连号/全组覆盖/数字回得了源);agent 定义硬边界四条
- [x] 缺报告成员在成组时列出并支持分批补跑后重装配
      —— `missing_members` 带原因 + 补跑命令;测试覆盖「补跑后重装配即并入」
- [x] --review 收尾联动提示生效,确认后对比页重装配(含裁决重跑);manifest 对比组字段读写正确
      —— `compare status --company` + `manifest.add/remove_compare_group`;review-pipeline 收尾写成
      「问过用户才重跑」的具体命令序列(不做自动联动)

---

## 落地记录(2026-09-01)

**产物**:`scripts/compare.py`(成组/装配/裁决机检/同步状态)· 契约四件
(`compare-group` / `compare` / `compare-judge` / **`compare-member-source`**)·
`agents/compare-judge.md`(第 10 个 sub-agent)· `phases/compare-pipeline.md`(C0-C4)·
`assets/html/compare-v8.html` + `build_html --compare-slug` + `update_index --compare-slug`。
53 项对比测试,全库 404 项绿。

**真数据验收暴露的一个真缺陷(已修)**:成员报告是**不同时间**产出的,拿今天的完整
`assembly.schema` / `node-odds.schema` 去校验昨天的完整报告会误判 ——
东山 08-24 那份真实报告产于票 11 之前,面板指标没有 `series`、③赔率没有 `derivation`,
结果 (a) 整家被判「缺报告」(b) 区间锚读不出来。**对比页两样都不消费**。
修法 = 新增 `compare-member-source.schema.json`,只 `$ref` 真正消费的四处
(verdict_card / top3 / metadata / anchor_range+current_price),定义仍在原 schema 里不留第二份真相源;
读不出来的格子标 `degraded` 并在页面 notes 明说「留空」,不闷声吞掉。
→ **这条经验通用**:跨 run 消费别人的产物时,校验范围必须等于消费范围,否则无关的契约演进
会变成本功能的故障。三条回归测试钉住。

**顺手补的两处历史欠账**:
- `update_index.main()` 缺 Windows GBK 控制台守卫(其余脚本都有)——cp936 终端上第一个 `✅` 就炸;
- `install.sh` 的逐文件清单漏了票 09/11 的 `triage.py` / `derivation.py` / `review-pipeline.md` /
  `triage.schema.json`(`install.ps1` 整目录拷所以没暴露,curl 装出来的是缺件版本),已补齐并同步计数。

**未做 / 留给后续**:
- 站点首页「对比卡与单报告卡并列」的**渲染**在 Inves-Report 的 `src/app.jsx`(另一个仓库,
  且有别的会话与 cron 在写)。本票产出了站点条目 `data/compare.json` 与页面本体 `compare/{slug}/`,
  JSX 侧渲染待用户确认后单独做。
- `references/html-template-guide.md` 仍 v4.3,没收录 compare-v8 版式(已有单独一张票)。
