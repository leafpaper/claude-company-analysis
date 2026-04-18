#!/bin/bash
#
# Claude Code 投资分析 Skill — 一键安装 (v3)
#
# 使用方法：
#   curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/install.sh | bash
#

set -e

SKILL_DIR="$HOME/.claude/skills/company-analysis"
REPO_URL="https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main"

echo "================================================"
echo "  Claude Code — 投资分析 Skill 安装程序 v3"
echo "  支持创业公司 + 上市公司（A股/美股/港股）"
echo "================================================"
echo ""

# 创建目录
echo "[1/4] 创建目录结构..."
mkdir -p "$SKILL_DIR/phases"
mkdir -p "$SKILL_DIR/references"
mkdir -p "$HOME/投资报告"

# 下载协调器
echo "[2/4] 下载协调器..."
curl -fsSL "$REPO_URL/SKILL.md" -o "$SKILL_DIR/SKILL.md"

# 下载阶段文件
echo "[3/4] 下载 5 个阶段文件..."
curl -fsSL "$REPO_URL/phases/phase1-data-collection.md" -o "$SKILL_DIR/phases/phase1-data-collection.md"
curl -fsSL "$REPO_URL/phases/phase2-document-analysis.md" -o "$SKILL_DIR/phases/phase2-document-analysis.md"
curl -fsSL "$REPO_URL/phases/phase3-analysis-report.md" -o "$SKILL_DIR/phases/phase3-analysis-report.md"
curl -fsSL "$REPO_URL/phases/phase4-persona-conclusions.md" -o "$SKILL_DIR/phases/phase4-persona-conclusions.md"
curl -fsSL "$REPO_URL/phases/phase5-review-publish.md" -o "$SKILL_DIR/phases/phase5-review-publish.md"

# 下载参考文件
echo "[4/4] 下载 7 个分析框架..."
curl -fsSL "$REPO_URL/references/scoring-rubric.md" -o "$SKILL_DIR/references/scoring-rubric.md"
curl -fsSL "$REPO_URL/references/qualitative-frameworks.md" -o "$SKILL_DIR/references/qualitative-frameworks.md"
curl -fsSL "$REPO_URL/references/valuation-frameworks.md" -o "$SKILL_DIR/references/valuation-frameworks.md"
curl -fsSL "$REPO_URL/references/search-strategy.md" -o "$SKILL_DIR/references/search-strategy.md"
curl -fsSL "$REPO_URL/references/report-template.md" -o "$SKILL_DIR/references/report-template.md"
curl -fsSL "$REPO_URL/references/html-template-guide.md" -o "$SKILL_DIR/references/html-template-guide.md"
curl -fsSL "$REPO_URL/references/persona-registry.md" -o "$SKILL_DIR/references/persona-registry.md"

# 验证安装
PHASE_COUNT=$(find "$SKILL_DIR/phases" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
REF_COUNT=$(find "$SKILL_DIR/references" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
TOTAL=$((PHASE_COUNT + REF_COUNT + 1))

if [ "$TOTAL" -eq "13" ]; then
    echo ""
    echo "============================================"
    echo "  安装成功！共 $TOTAL 个文件"
    echo "============================================"
    echo ""
    echo "  协调器:  SKILL.md"
    echo "  阶段:    $PHASE_COUNT 个 (phases/)"
    echo "  框架:    $REF_COUNT 个 (references/)"
    echo "  输出目录: ~/投资报告/"
    echo ""
    echo "使用方法：在 Claude Code 中输入"
    echo ""
    echo "  /company-analysis <公司名称>"
    echo ""
    echo "示例："
    echo "  /company-analysis 苹果       # 上市公司"
    echo "  /company-analysis Tesla      # 美股"
    echo "  /company-analysis 纽瑞芯     # 创业公司"
    echo ""
    echo "提示：重启 Claude Code 后生效"
    echo ""
else
    echo "错误：安装可能不完整，预期 13 个文件，实际找到 $TOTAL 个。"
    echo "  协调器: 1, 阶段: $PHASE_COUNT/5, 框架: $REF_COUNT/7"
    exit 1
fi
