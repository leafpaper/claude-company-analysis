#!/bin/bash
#
# Claude Code 投资分析 Skill — 一键安装 (v6.0)
#
# 使用方法：
#   curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/install.sh | bash
#

set -e

SKILL_DIR="$HOME/.claude/skills/company-analysis"
REPO_URL="https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main"

echo "================================================"
echo "  Claude Code — 投资分析 Skill 安装程序 v6.0"
echo "  结构化数据 + PDF 精析 + 11 大师框架审计"
echo "  v7.0: 9 章节报告(含投资决策内核) + 5 part 写手编排"
echo "  v7.2: Phase 2 文档精析独立化 (doc-analyst, 10 sub-agent)"
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
mkdir -p "$SKILL_DIR/assets/templates"
mkdir -p "$SKILL_DIR/assets/html"
mkdir -p "$SKILL_DIR/assets/validation"
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
# [3/6] 下载 5 个阶段文件 + 10 个 sub-agent
# ------------------------------------------------
echo "[3/6] 下载 5 个阶段文件 + 10 个 sub-agent..."
for phase in \
    phase1-data-collection \
    phase2-document-analysis \
    phase3-analysis-report \
    phase6-review-publish \
    phase7-quantitative-monitor; do
  curl -fsSL "$REPO_URL/phases/${phase}.md" -o "$SKILL_DIR/phases/${phase}.md"
done

for agent in \
    data-collector \
    doc-analyst \
    phase3-part1 \
    phase3-part2 \
    phase3-part3 \
    phase3-part4 \
    phase3-part5 \
    reviewer-narrative \
    reviewer-valuation \
    reviewer-redflag; do
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
# [5/6] 下载 assets/ (报告骨架 + HTML 模板 + 审核 schema)
# ------------------------------------------------
echo "[5/6] 下载 assets/（9 章节骨架强制）..."
# 2 个模板
curl -fsSL "$REPO_URL/assets/templates/report-skeleton.md"     -o "$SKILL_DIR/assets/templates/report-skeleton.md"
curl -fsSL "$REPO_URL/assets/templates/exec-summary-schema.md" -o "$SKILL_DIR/assets/templates/exec-summary-schema.md"
# 3 个 HTML
curl -fsSL "$REPO_URL/assets/html/base.html"       -o "$SKILL_DIR/assets/html/base.html"
curl -fsSL "$REPO_URL/assets/html/styles.css"      -o "$SKILL_DIR/assets/html/styles.css"
curl -fsSL "$REPO_URL/assets/html/components.html" -o "$SKILL_DIR/assets/html/components.html"
# 1 个 validation
curl -fsSL "$REPO_URL/assets/validation/report-checklist.json" -o "$SKILL_DIR/assets/validation/report-checklist.json"

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
    assemble_report \
    red_flags \
    assembly \
    assemble_report_v8 \
    anti_lazy_lint \
    review_loop \
    lessons_manager \
    update_index \
    build_html; do
  curl -fsSL "$REPO_URL/scripts/${py}.py" -o "$SKILL_DIR/scripts/${py}.py"
done
curl -fsSL "$REPO_URL/scripts/requirements.txt" -o "$SKILL_DIR/scripts/requirements.txt"
curl -fsSL "$REPO_URL/scripts/README.md" -o "$SKILL_DIR/scripts/README.md"
# v8 契约层 schema(节点×4 + decision + assembly + appendix-d + manifest + common)
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
    manifest; do
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
# v7.2 期望: 5 phases + 10 agents + 9 refs + 30 scripts + 6 assets + 1 SKILL.md
# (v7.1→v7.2 变更: agents 9→10 新增 doc-analyst;scripts 25→27 新增 v8 契约层 verdict_block/manifest,
#  27→30 新增 v8 装配层 red_flags/assembly/assemble_report_v8;
#  refs 8→9 v8 手册层 1+4 取代旧四份框架文档)

if [ "$PHASE_COUNT" -eq "5" ] && [ "$AGENT_COUNT" -eq "10" ] && [ "$REF_COUNT" -eq "9" ] && [ "$SCRIPT_COUNT" -eq "30" ] && [ "$ASSETS_COUNT" -eq "6" ]; then
    echo ""
    echo "============================================"
    echo "  ✅ 安装成功！(v7.2)"
    echo "============================================"
    echo ""
    echo "  协调器:  SKILL.md"
    echo "  阶段:    $PHASE_COUNT 个 (phases/)"
    echo "  子智能体: $AGENT_COUNT 个 (agents/)"
    echo "  框架:    $REF_COUNT 个 (references/)"
    echo "  脚本:    $SCRIPT_COUNT 个 Python 模块 (scripts/)"
    echo "  资产:    $ASSETS_COUNT 个 (assets/ - 9 章节骨架 + HTML 模板 + 审核 schema)"
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
    echo "     /company-analysis <公司名称> --monitor   # 量化监控"
    echo ""
    echo "示例："
    echo "  /company-analysis 贵州茅台 600519.SH     # A 股"
    echo "  /company-analysis Apple AAPL             # 美股"
    echo "  /company-analysis 腾讯控股 0700.HK       # 港股"
    echo ""
else
    echo ""
    echo "❌ 错误：安装不完整"
    echo "  预期(v7.2): phases=5 agents=10 refs=9 scripts=27 assets=6"
    echo "  实际:       phases=$PHASE_COUNT agents=$AGENT_COUNT refs=$REF_COUNT scripts=$SCRIPT_COUNT assets=$ASSETS_COUNT"
    exit 1
fi
