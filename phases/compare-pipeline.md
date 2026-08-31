# 产业链同行对比 `--compare` 执行细则(v8 票 10)

> 主 agent 在用户触发 `--compare {公司}`(或自然语言"和同行比比 / 同行里买哪个 / 对比")时加载本文件。
> 产物是**一页上下两半**:上半各家决断卡并排(机器装配,零新判断),下半「组内裁决」(唯一判断节点)。
>
> 两条底线,全流程不许松:
> · **全报告制** —— 只在有完整 v8 报告的成员间对比,缺报告的列出来让用户决定分批补跑,
>   **不建 peer-lite 轻判断管线**(两套判断口径必打架);
> · **上半零新判断** —— 每一格都搬自各家最新 run 的 YAML 块与装配产物,主 agent 不改一个字。

---

## C0: 锚定 + 查候选(三路优先级)

1. 锁定锚公司 `{anchor}` / `{anchor_ticker}`。锚**必须自己先有完整 v8 报告**;没有 → 告知用户
   "先跑 `/company-analysis {anchor}`,有了报告才谈得上跟谁比",流程终止。
2. 查同行候选 **5-8 家**,按这个优先级往下走,前一路够数就不必再往下:

| 优先级 | 路子 | 怎么查 |
|:--:|---|---|
| ① | Longbridge 产业链 / 成分股 | `longbridge-intel` skill(产业链分析 / 板块成分股),同链上下游都算 |
| ② | 报告库内已有 peer 对标 | `{PYBIN} -m scripts.compare candidates --anchor {anchor}` —— 库里还有谁、各自有没有可用报告 |
| ③ | 模型按业务描述兜底 | 读 `{artifacts_dir}/data_snapshot.md` 的主营构成,自己列同链公司 |

3. 同行口径 = **产业链相关**(如东山精密 ↔ 中际旭创),不是证监会窄行业分类。
   给每个候选记下它是从哪条路来的(`longbridge` / `library` / `model`)—— 成组时要写进 `member.source`。

## C1: 用户确认成组 + 命名

**候选必经用户确认/增删**,不许脚本自作主张成组。给用户看一张表:公司 / ticker / 来源 / 库里有没有报告。

组 slug 由用户命名:**建议产业链 kebab-case 英文短名**(如 `pcb-optics`),兜底 `{锚ticker}-peers`。

```
{PYBIN} -m scripts.compare init --anchor {anchor} --anchor-ticker {anchor_ticker} \
    --slug {slug} --name "{组的人话名字}" --chain-note "{这组凭什么算同行, 一句话}" \
    --member "{公司}:{ticker}:{source}" --member "..."
```

- 建 `output/_compare/{slug}/group.json`(过 `compare-group.schema.json`),
  并把 slug 登记进**每个有 manifest 的成员**的 `manifest.compare_groups` —— `--review` 收尾靠这个字段。
- 锚没写进 `--member` 也会自动进名单并排头。

## C2: 上半并排装配(机器)

```
{PYBIN} -m scripts.compare assemble --slug {slug}
```

- 产 `{group_dir}/compare.json`(过 `compare.schema.json`)+ `{slug}-compare-{date}.md` 本地底稿。
- 每家一列:基准日(全量/增量)、行动档位、决断卡五问、区间锚 vs 现价、红旗计数、Top3、下次披露日;
  全部搬自 `runs/{最新}/assembly/assembly.json` 与 `nodes/node-odds.md` 的 YAML 块。
- **基准日超 90 天标「陈旧」**并在页面提示先 `--review`;把这句转告用户,由用户决定先复查还是照比。
- **缺报告成员**进 `missing_members`(带原因 + 补跑命令),不进上半。把清单给用户:
  「这几家还没有完整报告,要现在补跑哪几家?可以分批 —— 补完重跑一次装配就并进来」。
  用户选了就照常走 `/company-analysis` 全量流程,跑完回到本步重装配。
- 有报告的成员**不足 2 家**→ 脚本退出码 2,先补跑,本流程暂停。

## C3: 组内裁决(唯一判断节点)

```python
Agent(
    subagent_type="compare-judge",
    run_in_background=False,
    description="compare judge",
    prompt=f"""产出组内裁决。
slug      = {slug}
group_dir = output/_compare/{slug}/
证据源    = {group_dir}/compare.json(**你唯一能读的文件**, 别读任何一家的报告)
PYBIN     = {PYBIN}

读各家决断卡 → 产排序 + 每家一句原因 + 全组共担风险, 写 {group_dir}/compare-judge.md
(顶部 fenced YAML 块 + 正文 ≤40 行)。
不自产数字、不发仓位与档位、不给缺报告成员排序、陈旧成员要点明。
自检: {PYBIN} -m scripts.compare assemble --slug {slug} --require-judge 退出码 0。""",
)
```

**门控**(主 agent 复核,不信 sub-agent 自证):

```
{PYBIN} -m scripts.compare assemble --slug {slug} --require-judge
```

退出码 0 = 裁决过 schema + 四条机检(具名成员 / 排名连号 / 全组覆盖 / 数字回得了源),
且已并进 `compare.json`。非 0 → **fresh-restart compare-judge 一次**(prompt 注入 stderr 原文);
仍失败 → 转人工,不手改它的 YAML 块。

## C4: 出片 + 发布

```
{PYBIN} -m scripts.build_html --compare-slug {slug}
{PYBIN} -m scripts.update_index --compare-slug {slug} --repo $INVES_REPORT_DIR --force
```

- `build_html --compare-slug` 用 `assets/html/compare-v8.html` + 报告页同一套 CSS token 出片,
  自检每家的公司名 / 五行判定 / 回原报告的链接一个都不能少(退出码 2 = 自检未过)。
- `update_index --compare-slug` 把页面写到 `{repo}/compare/{slug}/index.html`,
  并**语义合并**进 `{repo}/data/compare.json`(按 slug upsert,不整文件覆盖 —— 那个仓库有别的会话
  和 cron 在写)。首页对比卡与单报告卡并列,卡上每家可点回自己的报告。
- 提交:`git add compare/{slug}/ data/compare.json` (+ `compare.data.js` 若存在) → commit → push。
  **push 前先 `git fetch`**;失败一次就停,保存本地并告诉用户。

## 收尾

- 完成消息给用户四件事:裁决那一句 / 排序 / 陈旧或缺报告的提醒 / 页面链接。
- `main-log.md` 记账:C0 候选来源与家数、C1 成组、C2 装配(几家进/几家缺)、C3 裁决判定、C4 发布。
- 之后任何成员跑完 `--review`,复查流程收尾会提示重装配本页(见 `phases/review-pipeline.md` 收尾)。
  重装配 = 重跑 C2 → C3 → C4,**卡片刷新 + 裁决重跑**(成员判断变了,旧裁决就是过期结论)。

---

## 状态查询(随时可用)

```
{PYBIN} -m scripts.compare list                          # 有哪些组
{PYBIN} -m scripts.compare status --slug {slug}          # 这组要不要重装配
{PYBIN} -m scripts.compare status --company {company}    # 这家在的每个组分别什么状态
```

`needs_rebuild: true` 的三种原因:没装配过 / 成员报告已更新 / 裁决尚未产出。
