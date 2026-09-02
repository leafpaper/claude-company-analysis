#!/bin/bash
#
# Claude Code 投资分析 Skill — 一键安装 (v8.3)
#
# 使用方法：
#   curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/install.sh | bash
#

set -e

SKILL_DIR="$HOME/.claude/skills/company-analysis"
REPO_URL="https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main"

echo "================================================"
echo "  Claude Code — 投资分析 Skill 安装程序 v8.3"
echo "  结构化数据 + PDF 精析 + 11 大师框架审计"
echo "  v8.0: 判断链五节点(质地/状态/赔率/路径/怎么办) + 依赖图两波调度"
echo "        首页一眼决断与附录全部机器装配"
echo "  支持 A 股 / 美股 / 港股"
echo "================================================"
echo ""

# ------------------------------------------------
# [1/6] 创建目录结构
# ------------------------------------------------
echo "[1/6] 创建目录结构..."
mkdir -p "$SKILL_DIR/agents"
mkdir -p "$SKILL_DIR/phases"
mkdir -p "$SKILL_DIR/references"
mkdir -p "$SKILL_DIR/scripts"
mkdir -p "$SKILL_DIR/assets/html"
mkdir -p "$HOME/投资报告"

# ------------------------------------------------
# [2/6] 下载协调器 + 附加文件
# ------------------------------------------------
echo "[2/6] 下载协调器 + README/CHANGELOG..."
curl -fsSL "$REPO_URL/SKILL.md" -o "$SKILL_DIR/SKILL.md"
curl -fsSL "$REPO_URL/README.md" -o "$SKILL_DIR/README.md"
curl -fsSL "$REPO_URL/CHANGELOG.md" -o "$SKILL_DIR/CHANGELOG.md"
curl -fsSL "$REPO_URL/.env.sample" -o "$SKILL_DIR/.env.sample"

# ------------------------------------------------
# [3/6] 下载 6 个阶段文件 + 10 个 sub-agent
# ------------------------------------------------
echo "[3/6] 下载 6 个阶段文件 + 10 个 sub-agent..."
for phase in \
    phase1-data-collection \
    phase2-document-analysis \
    phase3-node-writing \
    phase6-review-publish \
    review-pipeline \
    compare-pipeline; do
  curl -fsSL "$REPO_URL/phases/${phase}.md" -o "$SKILL_DIR/phases/${phase}.md"
done

for agent in \
    data-collector \
    doc-analyst \
    node-quality \
    node-odds \
    node-path \
    node-state \
    decision-writer \
    reviewer-logic \
    reviewer-delivery \
    compare-judge; do
  curl -fsSL "$REPO_URL/agents/${agent}.md" -o "$SKILL_DIR/agents/${agent}.md"
done

# ------------------------------------------------
# [4/6] 下载 9 个参考文档(v8 手册层:链手册 1 + 节点手册 4)
# ------------------------------------------------
echo "[4/6] 下载 9 个参考文档..."
for ref in \
    agent-protocol \
    phase-orchestration \
    judgment-chain \
    node-quality \
    node-state \
    node-odds \
    node-path \
    search-strategy \
    html-template-guide; do
  curl -fsSL "$REPO_URL/references/${ref}.md" -o "$SKILL_DIR/references/${ref}.md"
done

# ------------------------------------------------
# [5/6] 下载 assets/ (HTML 模板)
# ------------------------------------------------
echo "[5/6] 下载 assets/（HTML 模板）..."
# 6 个 HTML(report-v8.* = v8 B 仪表盘版式; compare-v8 = 产业链对比页; base/styles/components = v7 兼容通道)
curl -fsSL "$REPO_URL/assets/html/compare-v8.html" -o "$SKILL_DIR/assets/html/compare-v8.html"
curl -fsSL "$REPO_URL/assets/html/report-v8.html"  -o "$SKILL_DIR/assets/html/report-v8.html"
curl -fsSL "$REPO_URL/assets/html/report-v8.css"   -o "$SKILL_DIR/assets/html/report-v8.css"
curl -fsSL "$REPO_URL/assets/html/base.html"       -o "$SKILL_DIR/assets/html/base.html"
curl -fsSL "$REPO_URL/assets/html/styles.css"      -o "$SKILL_DIR/assets/html/styles.css"
curl -fsSL "$REPO_URL/assets/html/components.html" -o "$SKILL_DIR/assets/html/components.html"

# ------------------------------------------------
# [6/6] 下载 Python 数据层
# ------------------------------------------------
echo "[6/6] 下载 Python 数据层（scripts/）..."
for py in \
    __init__ \
    config \
    check_env \
    check_phase2 \
    init_run \
    verdict_block \
    manifest \
    data_cache \
    tushare_collector \
    us_collector \
    hk_collector \
    pdf_reader \
    data_snapshot \
    derived_metrics \
    financial_audit \
    peer_collector \
    capital_flow \
    technical_analysis \
    legacy_quote \
    report_parser \
    monitor \
    node_graph \
    triage \
    derivation \
    compare \
    red_flags \
    assembly \
    assemble_report_v8 \
    lint_v8 \
    review_loop \
    lessons_manager \
    update_index \
    build_html; do
  curl -fsSL "$REPO_URL/scripts/${py}.py" -o "$SKILL_DIR/scripts/${py}.py"
done
curl -fsSL "$REPO_URL/scripts/requirements.txt" -o "$SKILL_DIR/scripts/requirements.txt"
curl -fsSL "$REPO_URL/scripts/README.md" -o "$SKILL_DIR/scripts/README.md"
# v8 契约层 schema(节点×4 + decision + assembly + appendix-d + manifest + triage + 对比×3 + common)
mkdir -p "$SKILL_DIR/scripts/schemas"
for schema in \
    common \
    node-quality \
    node-state \
    node-odds \
    node-path \
    node-decision \
    assembly \
    appendix-d \
    manifest \
    triage \
    compare \
    compare-group \
    compare-judge \
    compare-member-source; do
  curl -fsSL "$REPO_URL/scripts/schemas/${schema}.schema.json" -o "$SKILL_DIR/scripts/schemas/${schema}.schema.json"
done

# ------------------------------------------------
# 验证
# ------------------------------------------------
PHASE_COUNT=$(find "$SKILL_DIR/phases" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
AGENT_COUNT=$(find "$SKILL_DIR/agents" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
REF_COUNT=$(find "$SKILL_DIR/references" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
SCRIPT_COUNT=$(find "$SKILL_DIR/scripts" -name "*.py" 2>/dev/null | wc -l | tr -d ' ')
ASSETS_COUNT=$(find "$SKILL_DIR/assets" -type f 2>/dev/null | wc -l | tr -d ' ')
# v8.3 期望: 6 phases + 10 agents + 9 refs + 33 scripts + 6 assets + 1 SKILL.md
# (v7.2→v8.0 变更: phases 5→4 删 phase3-analysis-report/phase7-quantitative-monitor, 新增 phase3-node-writing;
#  agents 删 phase3-part1-5 与 reviewer-{narrative,valuation,redflag}、新增 node-{quality,odds,path,state} +
#    decision-writer + reviewer-{logic,delivery} → 9;
#  scripts 删 assemble_report/anti_lazy_lint、新增 node_graph/lint_v8(仍 30);
#  assets 6→4 删 9 章节骨架与执行摘要 schema、交付票 +2 v8 模板 → 6, 质量环票删 report-checklist.json → 5
#    —— 章节结构由链手册与装配层定义, 审核清单由 lint_v8 + 两个 reviewer 定义, 不再留第二份 JSON 真相源)
# v8.3 变更: phases +review-pipeline(票09) +compare-pipeline(票10) → 6; agents +compare-judge → 10;
#   assets +compare-v8.html → 6; scripts +triage(票09) +derivation(票11) +compare(票10) → 33
#   —— 前两个此前只进了 install.ps1(整目录拷), install.sh 的逐文件清单漏了, 一并补上)

if [ "$PHASE_COUNT" -eq "6" ] && [ "$AGENT_COUNT" -eq "10" ] && [ "$REF_COUNT" -eq "9" ] && [ "$SCRIPT_COUNT" -eq "33" ] && [ "$ASSETS_COUNT" -eq "6" ]; then
    echo ""
    echo "============================================"
    echo "  ✅ 安装成功！(v8.3)"
    echo "============================================"
    echo ""
    echo "  协调器:  SKILL.md"
    echo "  阶段:    $PHASE_COUNT 个 (phases/)"
    echo "  子智能体: $AGENT_COUNT 个 (agents/)"
    echo "  框架:    $REF_COUNT 个 (references/)"
    echo "  脚本:    $SCRIPT_COUNT 个 Python 模块 (scripts/)"
    echo "  资产:    $ASSETS_COUNT 个 (assets/ - HTML 模板)"
    echo "  输出目录: ~/投资报告/"
    echo ""
    echo "============================================"
    echo "  下一步（必做，否则 A 股/港股分析无法工作）"
    echo "============================================"
    echo ""
    echo "  1. 安装 Python 依赖:"
    echo "     cd $SKILL_DIR/scripts && pip3 install --user -r requirements.txt"
    echo ""
    echo "  2. 配置 Tushare Token（注册 https://tushare.pro/register）:"
    echo "     echo 'export TUSHARE_TOKEN=\"your_token_here\"' >> ~/.zshrc"
    echo "     source ~/.zshrc"
    echo ""
    echo "  3. 环境自检:"
    echo "     cd $SKILL_DIR && python3 -m scripts.check_env"
    echo ""
    echo "  4. 重启 Claude Code，然后使用："
    echo ""
    echo "     /company-analysis <公司名称>"
    echo ""
    echo "示例："
    echo "  /company-analysis 贵州茅台 600519.SH     # A 股"
    echo "  /company-analysis Apple AAPL             # 美股"
    echo "  /company-analysis 腾讯控股 0700.HK       # 港股"
    echo ""
else
    echo ""
    echo "❌ 错误：安装不完整"
    echo "  预期(v8.3): phases=6 agents=10 refs=9 scripts=33 assets=6"
    echo "  实际:       phases=$PHASE_COUNT agents=$AGENT_COUNT refs=$REF_COUNT scripts=$SCRIPT_COUNT assets=$ASSETS_COUNT"
    exit 1
fi
