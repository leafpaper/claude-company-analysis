#!/bin/bash
#
# Claude Code 公司投资分析 Skill — 卸载
#
# 使用方法：
#   curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/uninstall.sh | bash
#

SKILL_DIR="$HOME/.claude/skills/company-analysis"

echo "正在卸载 Claude Code 公司投资分析 Skill..."

if [ -d "$SKILL_DIR" ]; then
    rm -rf "$SKILL_DIR"
    echo "卸载完成。已删除 $SKILL_DIR"
    echo "提示：重启 Claude Code 后生效"
else
    echo "未找到安装目录 $SKILL_DIR，可能已经卸载。"
fi
