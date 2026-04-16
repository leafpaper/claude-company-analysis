# HTML 报告生成指南 (HTML Report Generation Guide)

> 在保存 `.md` 报告后，自动生成同名 `.html` 可视化 dashboard 版本。

---

## 一、输出规范

- 文件名: `{company-name}-analysis-{YYYY-MM-DD}.html`
- 与 `.md` 报告保存在同一目录
- **自包含**: 所有 CSS 内联于 `<style>` 标签，不依赖外部 JS/CSS/CDN
- **单文件**: 可独立打开，可作为附件发送

---

## 二、CSS 设计系统

复用以下 CSS 变量（参考纽瑞芯报告的实现）：

```css
:root {
  --c-primary: #1a56db;
  --c-primary-light: #e8effc;
  --c-green: #059669;
  --c-green-bg: #ecfdf5;
  --c-yellow: #d97706;
  --c-yellow-bg: #fffbeb;
  --c-red: #dc2626;
  --c-red-bg: #fef2f2;
  --c-gray-50: #f9fafb;
  --c-gray-100: #f3f4f6;
  --c-gray-200: #e5e7eb;
  --c-gray-500: #6b7280;
  --c-gray-700: #374151;
  --c-gray-900: #111827;
  --radius: 12px;
  --shadow: 0 1px 3px rgba(0,0,0,.1), 0 1px 2px rgba(0,0,0,.06);
  --shadow-md: 0 4px 6px rgba(0,0,0,.07), 0 2px 4px rgba(0,0,0,.06);
}
```

字体: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif`

---

## 三、必需组件

### 3.1 Sticky 顶部导航栏

```html
<nav class="top-nav">
  <a href="../../index.html" class="nav-brand">叶纸的投资报告</a>
  <a href="../../index.html" class="nav-back">← 返回首页</a>
  <a href="#scoring">评分</a>
  <a href="#detail">详细分析</a>
  <a href="#valuation">估值分析</a>
  <a href="#terms">条款分析</a>
  <a href="#qualitative">定性判断</a>
  <a href="#invest-sim">投资模拟</a>
</nav>
```

样式: `position: sticky; top: 0; z-index: 200; backdrop-filter: blur(12px); height: 50px`

### 3.2 评分环形图 (Score Ring)

使用 SVG 实现:
```html
<svg width="140" height="140" viewBox="0 0 140 140">
  <circle cx="70" cy="70" r="58" fill="none" stroke="#e5e7eb" stroke-width="10"/>
  <circle cx="70" cy="70" r="58" fill="none" stroke="#1a56db" stroke-width="10"
    stroke-dasharray="364.4" stroke-dashoffset="{364.4 - (score/10 * 364.4)}"
    stroke-linecap="round" transform="rotate(-90 70 70)"/>
</svg>
```

需同时展示: 量化综合分 + 定性调整后综合分（如有差异，用小字标注调整值）

### 3.3 维度评分条形图

每个维度一行: `名称 | 分数 | 进度条 | 权重`

进度条颜色按 Tier:
- tier1 (1.5x): `linear-gradient(90deg, #3b82f6, #1d4ed8)` — 蓝色
- tier2 (1.0x): `linear-gradient(90deg, #8b5cf6, #6d28d9)` — 紫色
- tier3 (0.75x): `linear-gradient(90deg, #f59e0b, #d97706)` — 琥珀色

条宽 = `score * 10%`

### 3.4 三色情景卡片

```css
.scenario.bull { background: var(--c-green-bg); border: 1px solid #a7f3d0; }
.scenario.base { background: var(--c-yellow-bg); border: 1px solid #fde68a; }
.scenario.bear { background: var(--c-red-bg); border: 1px solid #fecaca; }
```

每张卡片显示: 标签（概率）、大数字（回报倍数）、详情（退出估值/金额/IRR）

### 3.5 期望回报高亮条

深蓝渐变背景 (`linear-gradient(135deg, #1e3a5f, #1a56db)`)，白色文字，展示概率加权期望回报和 IRR。

### 3.6 团队名片网格

`display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr))`

每张卡片: 头像圆圈（取姓氏首字）、姓名、职位、简要背景

### 3.7 风险矩阵

每项风险: 彩色圆点（红/黄/绿）+ 标题 + 描述 + 严重度/可能性 badge

### 3.8 融资时间轴

水平时间轴，每轮一个节点（dot），显示年份/轮次/金额。当前拟融轮用不同颜色标注。

### 3.9 情绪量表

水平条，渐变色从红到绿，带标记指针显示当前情绪位置。

---

## 四、新增组件（v2）

### 4.1 估值区间可视化

水平范围条，显示三种估值方法的区间和重叠:

```
DCF:     |----[=====]--------|
倍数:       |---[======]----|
最近交易:          |X|
```

用不同颜色区分方法，重叠区域为估值共识区间。

### 4.2 条款星级评估

用 CSS 实现 ★ 填充/空心显示:
```css
.star-filled { color: #fbbf24; }
.star-empty { color: #e5e7eb; }
```

### 4.3 定性修正表

表格列出每个定性框架的评估结果和修正值。最终行显示加粗的平均修正系数。
如修正为正 → 绿色；为负 → 红色。

### 4.4 信息缺口优先级表

使用彩色 badge:
- 🔴 关键: `background: #fef2f2; color: #dc2626`
- 🟡 重要: `background: #fffbeb; color: #d97706`
- 🟢 补充: `background: #ecfdf5; color: #059669`

---

## 五、自适应行为

当某些章节缺少数据时（如无 term sheet、无法做 DCF）:
- **不跳过该章节**
- 显示占位提示: `"本分析暂无足够数据支持此章节。以下为基于行业标准假设的分析框架，建议在尽调中补充。"`
- 仍展示框架结构（空表格+说明），让读者知道应关注什么

---

## 六、响应式与打印

- 响应式断点: `@media (max-width: 768px)` — 卡片单列、表格横向滚动
- 打印: `@media print` — 去阴影、加边框、`break-inside: avoid`
- 所有 section 加 `id` 属性供导航栏锚点跳转
