# Claude Code 公司投资分析 Skill

一个用于 Claude Code 的自定义 Skill，系统性分析 C/D 轮融资公司，辅助投资决策。
例子： https://leafpaper.github.io/Inves-Report/reports/NewRadioTech_%E7%BA%BD%E7%91%9E%E8%8A%AF/%E5%88%86%E6%9E%90%E6%8A%A5%E5%91%8A_dashboard.html
## 功能特性

- **10维度加权评分** — 商业模式、市场机会、竞争格局、增长指标、团队、产品技术、财务健康、风险、融资估值、退出潜力
- **7轮结构化联网搜索** — 自动抓取最新公开数据，含条款搜索和行业专项模板（半导体/SaaS/生物医药/AI 等）
- **定性分析框架 (v2 新增)** — 融合张磊《价值》（结构性价值、动态护城河、大雪长坡）+ VC 定性方法论（Founder-Market Fit、S 曲线、Porter 五力 VC 版）
- **Damodaran 估值分析 (v2 新增)** — DCF 简化估值 + 相对估值 + 实物期权 + Narrative-to-Numbers + 估值三角验证
- **条款分析 (v2 新增)** — 基于《Venture Deals》框架，分析优先清算权/反稀释/对赌/董事会构成，建模退出瀑布
- **投资回报模拟** — 三种退出情景 + 稀释建模 + 敏感性分析 + 条款影响
- **网络舆情分析** — 收集投资人、分析师、客户、员工、社交媒体评价，划分看好/看衰阵营
- **证据质量门控** — 每维度最低证据要求，低于门槛自动降权标注
- **早期公司适配** — Pre-revenue 公司自动切换评分标准（用户指标替代收入、现金跑道替代资本效率等）
- **HTML 可视化报告 (v2 新增)** — 自动生成 dashboard 风格 HTML（评分环形图、情景卡片、估值区间条、定性雷达图）
- **完整报告输出** — 12 章节报告（含估值分析、条款分析、定性判断、信息缺口），保存为 `.md` + `.html`

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

1. **输入收集** — 询问内部资料、投资金额、条款信息
2. **联网搜索** — 7 轮结构化搜索 + 行业专项搜索
3. **整合与缺口识别** — 交叉验证 + 标记信息缺口
4. **10维度评分** — 基于证据逐项打分，加权计算综合分
5. **定性分析叠加** — 张磊《价值》+ VC 定性框架 → 修正系数 ±1.5
6. **估值分析** — DCF + 倍数 + 实物期权 + 叙事 → 估值三角验证
7. **条款分析** — 优先清算权/反稀释/对赌 → 退出瀑布建模
8. **投资回报模拟** — 三种退出情景 + 敏感性分析
9. **生成报告** — 保存为 `.md` + 自动生成 `.html` 可视化版本

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
  SKILL.md                              # Skill 主编排（Phase 1-6 + 子阶段 4.5/4.7/4.8/5.5）
  references/
    scoring-rubric.md                   # 10维度评分标准 + 早期适配 + 质量门控 + 行业基准
    search-strategy.md                  # 7轮搜索模板 + 行业专项 + 降级策略
    report-template.md                  # 12章节报告模板
    qualitative-frameworks.md           # 张磊《价值》定性框架 + VC定性方法论
    valuation-frameworks.md             # Damodaran 估值框架（DCF/倍数/期权/叙事）
    term-sheet-guide.md                 # Venture Deals 条款分析指南
    html-template-guide.md              # HTML 报告生成规范
```

## 许可证

MIT
