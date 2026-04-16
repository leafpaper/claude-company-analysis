# 联网搜索策略 (Search Strategy)

> 所有搜索必须以获取**最新数据**为首要目标。使用动态日期变量 `{YEAR}` 代表当前年份。

---

## 时效性规则

1. **所有搜索查询必须附加时间限定词**: `{YEAR}`, `latest`, `recent`, `最新`
2. **来源新鲜度优先级**:
   - 优先级 1: 6 个月内的来源（高置信度）
   - 优先级 2: 6-12 个月的来源（中置信度，需交叉验证）
   - 优先级 3: 12+ 个月的来源（标记为 `[历史数据: YYYY-MM]`，仅作参考）
3. **财务数据必须标注截止日期**（如 "截至 2026Q1"）
4. **如果某维度最新数据获取失败**，执行补充搜索（见降级策略）

---

## 搜索轮次

### Round 1: 公司基础信息与最新动态
**目标**: 确定公司当前状态、最新融资、商业模式

```
搜索查询:
1. "{company} latest news {YEAR}"
2. "{company} series C OR series D funding {YEAR}"
3. "{company} business model revenue how it works"
4. "{company} 最新融资 {YEAR}"
5. "{company} CEO founder interview {YEAR}"
```

**期望获得**: 公司简介、最新融资金额/估值、投资人、商业模式描述、创始人背景

### Round 2: 市场与竞争格局
**目标**: 了解市场规模、竞争态势、行业趋势

```
搜索查询:
1. "{company} market size TAM {YEAR}"
2. "{company} competitors comparison {YEAR}"
3. "{industry} market analysis report {YEAR}"
4. "{company} market share industry position"
5. "{company} vs {competitor} comparison" (基于 Round 1 发现的竞品)
```

**期望获得**: TAM/SAM 数据、主要竞争对手列表、市场份额、行业增长率

### Round 3: 增长与财务指标
**目标**: 获取最新的增长数据和财务状况

```
搜索查询:
1. "{company} revenue growth {YEAR}"
2. "{company} users customers growth latest"
3. "{company} ARR MRR valuation {YEAR}"
4. "{company} profitability unit economics"
5. "{company} employee count hiring {YEAR}"
```

**期望获得**: 营收数据/增速、用户数、ARR、估值、员工规模变化

### Round 4: 风险与负面信息
**目标**: 发现潜在风险、负面新闻、监管问题

```
搜索查询:
1. "{company} problems issues criticism {YEAR}"
2. "{company} layoffs restructuring {YEAR}"
3. "{company} lawsuit regulatory legal"
4. "{company} {industry} regulation policy {YEAR}"
5. "{company} customer complaints reviews"
```

**期望获得**: 负面新闻、裁员信息、法律纠纷、监管风险、客户投诉

### Round 5: 网络评价与市场情绪
**目标**: 收集各方对公司的评价和看法，判断市场情绪是看好还是看衰

```
搜索查询:
1. "{company} review opinion {YEAR}"
2. "{company} 评价 口碑 怎么样 {YEAR}"
3. "{company} analyst opinion bullish bearish {YEAR}"
4. "{company} reddit OR twitter OR 知乎 评价"
5. "{company} employee review glassdoor {YEAR}"
6. "{company} customer review experience"
7. "{company} investment opinion worth {YEAR}"
```

**期望获得**:
- **投资人/分析师观点**: 知名投资人或分析师对公司的公开评价
- **用户/客户评价**: 产品好评率、差评集中的痛点
- **员工评价**: Glassdoor/脉脉评分、工作体验
- **社交媒体舆论**: Twitter/知乎/Reddit 上的讨论风向
- **媒体态度**: 主流科技媒体的报道倾向（正面/中性/负面）

**情绪分析要求**:
- 将收集到的评价分为 **看好派** 和 **看衰派**
- 提炼每一方的核心论据（不是简单列举，要归纳逻辑）
- 判断整体市场情绪倾向：强烈看好 / 偏向看好 / 中性分歧 / 偏向看衰 / 强烈看衰
- 特别关注"聪明钱"（知名投资人、行业专家）的态度

### Round 5.5: 条款与交易信息 (Term Sheet & Deal Intelligence)
**目标**: 搜索本轮融资条款、cap table 结构、投资人动态

```
搜索查询:
1. "{company} funding terms valuation cap table {YEAR}"
2. "{company} 融资条款 对赌 优先清算权 回购"
3. "{company} investor rights board composition {YEAR}"
4. "{company} convertible note SAFE outstanding debt"
5. "{company} 股权结构 持股比例 天眼查 企查查"
```

**期望获得**: 融资条款细节、cap table 结构、对赌条款、优先清算权类型、董事会构成、可转债/SAFE 信息

*注: 条款信息通常高度保密，公开搜索可能收获有限。如信息不足，在报告中标注并使用行业标准假设。*

### Round 6: 深度阅读 (WebFetch)
**目标**: 深入阅读关键页面，获取结构化详细信息

**优先 Fetch 的页面类型**:
1. 公司官网 About/Product 页面
2. Crunchbase 公司主页（融资历史、投资人、团队）
3. 1-2 篇高质量深度分析文章（来自 Round 1-5 搜索结果中质量最高的）
4. 行业报告摘要页
5. 如有：公司博客中的里程碑公告（融资、产品发布）
6. 1-2 篇有代表性的网络评价/讨论帖（来自 Round 5 中最有洞察力的）

---

## 优先信息来源（域名）

| 来源类型 | 推荐域名 |
|---------|---------|
| 融资与投资人 | crunchbase.com, pitchbook.com, cbinsights.com |
| 科技新闻 | techcrunch.com, theinformation.com, bloomberg.com, reuters.com |
| 中国公司 | 36kr.com, it桔子 (itjuzi.com), 天眼查 (tianyancha.com) |
| 行业报告 | gartner.com, mckinsey.com, statista.com |
| 公司评价 | glassdoor.com, g2.com, trustpilot.com |
| 网络舆情 | reddit.com, zhihu.com (知乎), twitter.com/x.com, producthunt.com |
| 员工评价 | glassdoor.com, maimai.cn (脉脉), levels.fyi |
| 财务数据 | sec.gov (美国上市/预上市), 企查查, 启信宝 |
| 社交媒体 | linkedin.com (团队), twitter.com (创始人动态) |

---

## 降级策略

### 当搜索结果不足时：

**策略 1: 扩大搜索范围**
- 去掉年份限定词，搜索全时间范围
- 使用公司别名、英文/中文名交替搜索
- 搜索母公司或子品牌
- 具体查询: `"{company}" OR "{company别名}" site:36kr.com OR site:crunchbase.com`

**策略 2: 间接推断**
- 招聘信息 → 团队规模和方向: `"{company} jobs careers hiring {YEAR}"`、`"{company} 招聘 BOSS直聘 猎聘"`
- 竞品数据 → 市场规模: `"{competitor1} OR {competitor2} market size revenue"`
- LinkedIn 员工数变化 → 公司健康度: `site:linkedin.com "{company}" employees`
- 专利申请 → 技术方向: `"{company} patent application {YEAR}"`、`"{company} 专利 发明"`
- 政府补贴/项目 → 政策支持: `"{company} 政府补贴 专精特新 高新技术"`

**策略 3: 专家与内部信号挖掘**
- 创始人演讲/访谈: `"{founder name}" interview speech keynote {YEAR}`
- 投资人评论: `"{lead investor}" portfolio "{company}" opinion`
- 行业会议: `"{company}" demo day pitch conference {YEAR}`
- 学术论文（技术公司）: `"{company}" OR "{founder}" paper publication`
- 供应商/合作伙伴公告: `"{company}" partnership announcement supplier`

**策略 4: 标记信息缺口**
- 如果经过以上策略仍无法获取某维度数据，在报告的"信息缺口"章节中明确标注
- 将该维度的数据置信度标记为"低"
- 参照 `scoring-rubric.md` 的证据质量门控规则处理低置信维度
- 在"关键尽调问题"中列出需要进一步调查的问题及建议获取途径

---

## 中国公司特别搜索策略

如果目标公司是中国公司，增加以下搜索:

```
1. "{company} 天眼查 股权结构"
2. "{company} 36氪 融资"
3. "{company} 裁员 问题 {YEAR}"
4. "{company} 行业报告 市场规模"
5. "{company} 创始人 背景 履历"
```

---

## 行业特定搜索补充

根据目标公司所在行业，增加以下专项搜索（选择适用的 1-2 个行业模板）：

### 半导体/芯片
```
1. "{company} tape-out wafer foundry process node {YEAR}"
2. "{company} design win customer qualification"
3. "{company} AEC-Q certification FiRa CCC {YEAR}"
4. "{industry} chip 国产替代 自主可控 {YEAR}"
```

### SaaS/企业软件
```
1. "{company} NDR churn rate ARR NRR {YEAR}"
2. "{company} customer case study ROI implementation"
3. "{company} vs {competitor} G2 review comparison"
4. "{company} enterprise contract ACV deal size"
```

### 消费品/电商
```
1. "{company} GMV repeat purchase rate {YEAR}"
2. "{company} 抖音 天猫 旗舰店 销量 评价"
3. "{company} customer acquisition cost unit economics"
4. "{company} brand awareness NPS consumer survey"
```

### 生物医药
```
1. "{company} clinical trial phase FDA NMPA CDE {YEAR}"
2. "{company} pipeline drug candidate IND NDA"
3. "{company} patent expiry freedom to operate"
4. "{company} KOL opinion scientific advisory board"
```

### 金融科技
```
1. "{company} license regulatory approval 牌照 {YEAR}"
2. "{company} take rate NPL default rate risk"
3. "{company} AUM transaction volume {YEAR}"
4. "{company} compliance fintech regulation {YEAR}"
```

### AI/大模型
```
1. "{company} model benchmark performance {YEAR}"
2. "{company} compute cost GPU training inference"
3. "{company} API usage developer adoption {YEAR}"
4. "{company} data moat proprietary dataset"
```

---

## 搜索结果处理规则

1. **每个搜索结果记录来源日期** — 后续分析中标注 `[来源: 域名, YYYY-MM]`
2. **交叉验证** — 关键数据（如营收、估值）需至少 2 个独立来源确认
3. **矛盾数据** — 如不同来源数据冲突，优先采信更新、更权威的来源，并在报告中注明差异
4. **区分事实与推测** — 明确标注 `[确认]`、`[估计]`、`[传闻]` 等信息等级
