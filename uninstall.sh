#!/bin/bash
#
# Claude Code Company Analysis Skill - Uninstall
#

set -e

SKILL_DIR="$HOME/.claude/skills/company-analysis"

echo "Removing Company Analysis Skill..."

if [ -d "$SKILL_DIR" ]; then
    rm -rf "$SKILL_DIR"
    echo "Uninstalled successfully."
else
    echo "Skill not found at $SKILL_DIR, nothing to remove."
fi
