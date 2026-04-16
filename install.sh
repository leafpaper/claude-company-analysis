#!/bin/bash
#
# Claude Code 公司投资分析 Skill — 一键安装
#
# 使用方法：
#   curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/install.sh | bash
#

set -e

SKILL_DIR="$HOME/.claude/skills/company-analysis"
REPO_URL="https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main"

echo "================================================"
echo "  Claude Code — 公司投资分析 Skill 安装程序"
echo "================================================"
echo ""

# 创建目录
echo "[1/3] 创建目录结构..."
mkdir -p "$SKILL_DIR/references"

# 下载文件
echo "[2/3] 下载 Skill 文件..."

curl -fsSL "$REPO_URL/SKILL.md" -o "$SKILL_DIR/SKILL.md"
curl -fsSL "$REPO_URL/references/scoring-rubric.md" -o "$SKILL_DIR/references/scoring-rubric.md"
curl -fsSL "$REPO_URL/references/search-strategy.md" -o "$SKILL_DIR/references/search-strategy.md"
curl -fsSL "$REPO_URL/references/report-template.md" -o "$SKILL_DIR/references/report-template.md"
curl -fsSL "$REPO_URL/references/qualitative-frameworks.md" -o "$SKILL_DIR/references/qualitative-frameworks.md"
curl -fsSL "$REPO_URL/references/valuation-frameworks.md" -o "$SKILL_DIR/references/valuation-frameworks.md"
curl -fsSL "$REPO_URL/references/term-sheet-guide.md" -o "$SKILL_DIR/references/term-sheet-guide.md"
curl -fsSL "$REPO_URL/references/html-template-guide.md" -o "$SKILL_DIR/references/html-template-guide.md"

# 验证安装
echo "[3/3] 验证安装..."

FILE_COUNT=$(find "$SKILL_DIR" -name "*.md" | wc -l | tr -d ' ')
if [ "$FILE_COUNT" -eq "8" ]; then
    echo ""
    echo "============================================"
    echo "  安装成功！"
    echo "============================================"
    echo ""
    echo "已安装文件："
    echo "  $SKILL_DIR/SKILL.md"
    echo "  $SKILL_DIR/references/scoring-rubric.md"
    echo "  $SKILL_DIR/references/search-strategy.md"
    echo "  $SKILL_DIR/references/report-template.md"
    echo ""
    echo "使用方法：在 Claude Code 中输入"
    echo ""
    echo "  /company-analysis <公司名称>"
    echo ""
    echo "示例："
    echo "  /company-analysis 纽瑞芯"
    echo "  /company-analysis Stripe"
    echo "  /company-analysis 月之暗面"
    echo ""
    echo "提示：重启 Claude Code 后生效"
    echo ""
else
    echo "错误：安装可能不完整，预期 8 个文件，实际找到 $FILE_COUNT 个。"
    exit 1
fi
