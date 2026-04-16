#!/bin/bash
#
# Claude Code Company Analysis Skill - One-click Install
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/install.sh | bash
#

set -e

SKILL_DIR="$HOME/.claude/skills/company-analysis"
REPO_URL="https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main"

echo "================================================"
echo "  Claude Code - Company Analysis Skill Installer"
echo "================================================"
echo ""

# Create directory structure
echo "[1/3] Creating directory structure..."
mkdir -p "$SKILL_DIR/references"

# Download files
echo "[2/3] Downloading skill files..."

curl -fsSL "$REPO_URL/SKILL.md" -o "$SKILL_DIR/SKILL.md"
curl -fsSL "$REPO_URL/references/scoring-rubric.md" -o "$SKILL_DIR/references/scoring-rubric.md"
curl -fsSL "$REPO_URL/references/search-strategy.md" -o "$SKILL_DIR/references/search-strategy.md"
curl -fsSL "$REPO_URL/references/report-template.md" -o "$SKILL_DIR/references/report-template.md"

# Verify installation
echo "[3/3] Verifying installation..."

FILE_COUNT=$(find "$SKILL_DIR" -name "*.md" | wc -l | tr -d ' ')
if [ "$FILE_COUNT" -eq "4" ]; then
    echo ""
    echo "Installation successful!"
    echo ""
    echo "Installed files:"
    echo "  $SKILL_DIR/SKILL.md"
    echo "  $SKILL_DIR/references/scoring-rubric.md"
    echo "  $SKILL_DIR/references/search-strategy.md"
    echo "  $SKILL_DIR/references/report-template.md"
    echo ""
    echo "Usage: In Claude Code, type:"
    echo "  /company-analysis <company-name>"
    echo ""
    echo "Example:"
    echo "  /company-analysis Stripe"
    echo ""
else
    echo "ERROR: Installation may be incomplete. Expected 4 files, found $FILE_COUNT."
    exit 1
fi
