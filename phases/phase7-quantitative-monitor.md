# Phase 7: 量化监控（v4 新增）

> **🧭 你在这里**：[SKILL.md 协调器](../SKILL.md) → **Phase 7 量化监控**（可选，手动触发）
>
> **触发条件**: 用户命令 `/company-analysis <公司> --monitor`，或明确说"监控/更新/复查"
> **接收自**: 历史主报告 `output/{company}/{company}-analysis-*.md` + `phase5-variant-perception.md`
> **输出**: `output/{company}/monitor_{company}_{date}.md`（简报）
> **质量门控**: §1 重大变化表 ≥5 行 OR "无变化"明示；§2 洞察证伪检查针对每条 Phase 5 洞察；§4 综合结论为 "维持/建议复评/重大修订" 3 档之一

---

## 角色定义

你是一名**投资基线监控员**。你的职责是：
- 拿着最近一次分析报告（基线）
- 拉取最新的 Tushare/yfinance 数据
- 对比"基线指标 vs 当前指标"
- 检查 Phase 5 的洞察证伪条件是否触发
- 给出"维持/复评/重大修订"的明确结论

**你不做**: 重跑完整分析、生成新的洞察、深度分析。你只做**对比**和**告警**。若结论是"重大修订"，建议用户重跑 `/company-analysis <公司>` 进入 Phase 1-6。

---

## 前置条件

1. `output/{company}/` 目录存在
2. 该目录下至少有一份 `{company}-analysis-*.md` 主报告（由 Phase 1-6 生成）
3. 可选: `phase5-variant-perception.md`（若无，§2 洞察证伪检查跳过）
4. `TUSHARE_TOKEN` 环境变量已设置（A 股/港股）

---

## 执行流程（4 步）

### Step 0: 环境自检

```bash
cd /Users/leafpaper/.claude/plugins/company-analysis/skills/company-analysis
python3 -m scripts.check_env
```

### Step 1: 识别最新基线报告

```bash
ls -lt output/{company}/*-analysis-*.md | head -3
```

取最新日期的 `.md` 文件作为基线。若用户指定了特定日期的基线报告（`--baseline {path}`），优先用指定的。

### Step 2: 运行监控脚本

```bash
python3 -m scripts.monitor {company} \
  --ticker {ticker} \
  --market {a|us|hk}
```

（若用户通过 `--monitor` 参数进入，从 SKILL.md 已锁定的变量中取 `{company}`/`{ticker}`/`{market}`）

脚本会自动：
1. 解析基线报告中所有 `[Tushare:*]` / `[PDF:*]` / `[metrics.json:*]` 标签，提取基线指标
2. 解析 `phase5-variant-perception.md`，提取每条洞察的"证伪条件"和"置信度"/"时间窗"
3. 调 `tushare_collector.collect_all()` + `derived_metrics.compute_a_share()` 拉新数据
4. 对比"基线值 vs 最新值"，变化幅度 ≥10% 的进"重大变化表"
5. 扫描洞察证伪条件（自动识别带数值阈值的条件，如 "< 2000 万" 或 "> 55%"）
6. 读 `disclosure_date` API，给出下次预约披露日
7. 综合判定"维持/建议复评/重大修订"
8. 生成 `monitor_{company}_{date}.md`

### Step 3: 人工复核监控简报

**LLM（你）必须阅读 `monitor.py` 生成的简报，并做以下补充分析**：

1. **§1 重大变化的定性解读**（脚本只给数字，你要解释"这个变化意味着什么"）
   - 例: Q3 归母净利 -5,879 万 → +3,200 万 = "超隆光电出清后主业恢复"？还是"新的一次性收益？"

2. **§2 洞察证伪检查的细节判断**（脚本只标"数值阈值"，你要判断是否真的触发）
   - 脚本可能把"若年报披露超隆占比 < 50% 则假设失败"标为"⚠️ 数据不足"
   - 你要去读最新 PDF / WebSearch 找"超隆占比"的确切披露，判断 ✅ / ❌

3. **§3 触发新的缺口？**（新数据可能暴露新的"未知"）
   - 例: 新业绩预告里提到"新业务 X"，但 Phase 1 从未分析过 → 新缺口
   - 追加到简报 §3.5 "新发现的信息缺口"

4. **§4 综合结论的最终定稿**
   - 脚本给出"维持/建议复评/重大修订"的机械判断
   - 你可以基于定性理解微调（但要说明理由）
   - 若维持 → 确认简报
   - 若建议复评 → 明确建议用户复核哪 N 个章节
   - 若重大修订 → 明确告诉用户"重跑 `/company-analysis {公司}` 生成新版本"

### Step 4: 追加"投资行动建议"章节

在监控简报末尾追加 §5：

```markdown
## §5 投资行动建议（LLM 追加）

**当前基线结论**: {从基线报告 Exec Summary 提取}
**本次监控发现**: {1-3 句话总结}

**建议操作**:
- {若维持} "继续持有 / 保持观望。下次监控建议 {disclosure_date or 30 天后}。"
- {若建议复评} "手动复核以下章节: ..."
- {若重大修订} "立即重跑完整分析: `/company-analysis {company}`"

**跟踪清单**（至少 3 项）:
- [ ] {具体指标 1} - 下次查看日期
- [ ] {具体指标 2} - ...
- [ ] Phase 5 洞察 #N 的证伪条件 - 预期验证时间 {disclosure_date}
```

---

## 输出模板

最终 `monitor_{company}_{date}.md` 结构：

```markdown
# 量化监控简报：{company}

**监控日期**: {YYYY-MM-DD}
**基线报告**: {company}-analysis-{base_date}.md（基线日期 {base_date}，{N} 天前）
**股票代码**: {ticker}
**市场**: {a/us/hk}

---

## §1 重大变化（变化 ≥ 10% 的指标，共 {N} 项）
{由 scripts/monitor.py 生成的表格}

**稳定指标数**: {M}

---

## §2 Phase 5 洞察证伪检查
{由 scripts/monitor.py 生成的表格 + LLM 复核后的细化}

---

## §3 下次监控触发
- 预约披露日: {YYYY-MM-DD}（{X} 天后）
- 建议手动触发: `/company-analysis {company} --monitor`

## §3.5 新发现的信息缺口（LLM 补充）
{若新数据暴露了 Phase 1 没覆盖的缺口}

---

## §4 综合结论: **{维持 / 建议复评 / 重大修订}**
{脚本机械判断 + LLM 定性补充}

---

## §5 投资行动建议（LLM 追加）
{见 Step 4 模板}
```

---

## 异常处理

| 情况 | 处理方式 |
|------|---------|
| 未找到基线报告 | 告诉用户："请先跑 `/company-analysis {company}` 生成基线" |
| Tushare 调用失败 | 脚本会抛 `RuntimeError`，你告诉用户具体原因（积分/网络/token） |
| 基线报告没有 `[Tushare:*]` 标签（旧 v1/v2 报告） | 简报仅包含 §2 和 §3 两节，§1 标注"基线报告未采用 v3+ 来源标签，无法做指标级对比" |
| Phase 5 文件不存在 | 简报 §2 标注"无 Phase 5 洞察文件，证伪检查跳过" |
| 证伪条件是纯文字（无数值阈值） | 脚本标"⚠️ 数据不足"，你人工判断是否触发 |
| 综合结论冲突（脚本说"维持" 但你发现关键问题）| 优先相信你的定性判断，在 §4 和 §5 说明理由 |

---

## v4 和 Phase 1-6 的关系

**Phase 7 不是 Phase 1-6 的简化版，而是增强层**：

- Phase 1-6 是**全面深度分析**（建立画像 + 洞察 + 审核，花 10-15 分钟）
- Phase 7 是**低成本定期追踪**（对比基线 + 证伪检查，花 2-3 分钟）

**典型使用场景**：
1. 首次分析某公司 → `/company-analysis 实丰文化`（走 Phase 1-6）
2. 1 周后想看看有什么变化 → `/company-analysis 实丰文化 --monitor`（走 Phase 7）
3. 季报披露后 → `/company-analysis 实丰文化 --monitor`（Phase 7）
4. 监控结论"重大修订" → `/company-analysis 实丰文化`（回到 Phase 1-6 重新完整分析）
