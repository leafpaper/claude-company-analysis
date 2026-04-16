# Claude Code 公司投资分析 Skill

一个用于 Claude Code 的自定义 Skill，系统性分析 C/D 轮融资公司，辅助投资决策。

## 功能特性

- **10维度加权评分** — 商业模式、市场机会、竞争格局、增长指标、团队、产品技术、财务健康、风险、融资估值、退出潜力
- **6轮结构化联网搜索** — 自动抓取最新公开数据，中英文双语搜索，优先采信6个月内来源
- **网络舆情分析** — 收集投资人、分析师、客户、员工、社交媒体评价，划分看好/看衰阵营
- **投资回报模拟 (新)** — 输入投资金额，自动估算入场估值、建模后续稀释、构建乐观/基准/悲观三种退出情景，计算概率加权期望回报和敏感性分析
- **数据时效性管控** — 所有数据标注来源和日期，超期数据自动标记
- **完整报告输出** — Executive Summary、评分表、详细分析、舆情、可比公司、投资回报模拟、来源引用，保存为 Markdown 文件

## 评分维度

| # | 维度 | 权重 |
|---|------|------|
| 1 | 商业模式与单位经济 | 1.5x |
| 2 | 市场机会 (TAM/SAM/SOM) | 1.5x |
| 3 | 竞争格局与护城河 | 1.5x |
| 4 | 增长指标与牵引力 | 1.5x |
| 5 | 团队与领导力 | 1.0x |
| 6 | 产品与技术 | 1.0x |
| 7 | 财务健康与资本效率 | 1.0x |
| 8 | 风险与挑战 | 1.0x |
| 9 | 融资历史与估值 | 0.75x |
| 10 | 退出潜力 | 0.75x |

**投资信号**：8.0+ 强烈看好 / 6.5-7.9 有条件看好 / 5.0-6.4 谨慎 / <5.0 建议放弃

## 一键安装

在终端中运行以下命令即可完成安装：

```bash
curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/install.sh | bash
```

安装完成后重启 Claude Code，即可使用 `/company-analysis` 命令。

## 手动安装

如果你更倾向于手动操作：

```bash
# 1. 创建目录
mkdir -p ~/.claude/skills/company-analysis/references

# 2. 下载核心文件
cd ~/.claude/skills/company-analysis
curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/SKILL.md -o SKILL.md
curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/references/scoring-rubric.md -o references/scoring-rubric.md
curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/references/search-strategy.md -o references/search-strategy.md
curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/references/report-template.md -o references/report-template.md
```

## 使用方法

在 Claude Code（CLI 或 VS Code 扩展）中输入：

```
/company-analysis 纽瑞芯
```

Skill 会自动执行以下流程：

1. **输入收集** — 询问你是否有内部资料（pitch deck、财报等），以及计划投资金额
2. **联网搜索** — 6轮结构化搜索，抓取公司最新公开信息
3. **舆情分析** — 收集网络评价，划分看好/看衰阵营
4. **10维度评分** — 基于证据逐项打分（1-10分），加权计算综合分
5. **投资回报模拟** — 三种退出情景建模 + 敏感性分析
6. **生成报告** — 保存为 `.md` 文件

### 示例

```
/company-analysis Stripe
/company-analysis 月之暗面
/company-analysis SpaceX
```

你也可以同时提供公司的 pitch deck 或财报文件，Skill 会自动读取并交叉验证。

## 投资回报模拟（Phase 6）

这是新增功能。当你指定投资金额后，报告末尾会自动生成类似这样的分析：

```
假设投资 100 万元进入 C 轮：

  乐观情景（20%）：高估值 IPO → 回报 5.1x → 净赚 410 万
  基准情景（45%）：正常 IPO   → 回报 2.0x → 净赚 104 万
  悲观情景（35%）：低估值退出 → 回报 0.6x → 净亏  39 万

  概率加权期望回报：2.1x / IRR ~18%
```

包含：入场估值推算、稀释模型、三种情景详细计算、敏感性分析、风险提示。

## 卸载

```bash
curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/uninstall.sh | bash
```

或手动删除：

```bash
rm -rf ~/.claude/skills/company-analysis
```

## 文件结构

```
~/.claude/skills/company-analysis/
  SKILL.md                          # Skill 主定义（Phase 1-6）
  references/
    scoring-rubric.md               # 10维度详细评分标准
    search-strategy.md              # 联网搜索策略和查询模板
    report-template.md              # 报告输出 Markdown 模板
```

## 许可证

MIT
