#!/bin/bash
#
# Claude Code 投资分析 Skill — 一键安装 (v4.4)
#
# 使用方法：
#   curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/install.sh | bash
#

set -e

SKILL_DIR="$HOME/.claude/skills/company-analysis"
REPO_URL="https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main"

echo "================================================"
echo "  Claude Code — 投资分析 Skill 安装程序 v4.4"
echo "  结构化数据 + PDF 精析 + 11 大师框架审计"
echo "  v4.4: 技术分析 + 可比公司 + 主力控盘"
echo "  v4.3: 骨架强制 + assets 目录"
echo "  支持 A 股 / 美股 / 港股"
echo "================================================"
echo ""

# ------------------------------------------------
# [1/6] 创建目录结构
# ------------------------------------------------
echo "[1/6] 创建目录结构..."
mkdir -p "$SKILL_DIR/phases"
mkdir -p "$SKILL_DIR/references"
mkdir -p "$SKILL_DIR/scripts"
mkdir -p "$SKILL_DIR/assets/templates"
mkdir -p "$SKILL_DIR/assets/html"
mkdir -p "$SKILL_DIR/assets/validation"
mkdir -p "$HOME/投资报告"

# ------------------------------------------------
# [2/5] 下载协调器 + 附加文件
# ------------------------------------------------
echo "[2/6] 下载协调器 + README/CHANGELOG..."
curl -fsSL "$REPO_URL/SKILL.md" -o "$SKILL_DIR/SKILL.md"
curl -fsSL "$REPO_URL/README.md" -o "$SKILL_DIR/README.md"
curl -fsSL "$REPO_URL/CHANGELOG.md" -o "$SKILL_DIR/CHANGELOG.md"
curl -fsSL "$REPO_URL/.env.sample" -o "$SKILL_DIR/.env.sample"

# ------------------------------------------------
# [3/5] 下载 7 个阶段文件
# ------------------------------------------------
echo "[3/6] 下载 7 个阶段文件..."
for phase in \
    phase1-data-collection \
    phase2-document-analysis \
    phase3-analysis-report \
    phase4-persona-conclusions \
    phase5-variant-perception \
    phase6-review-publish \
    phase7-quantitative-monitor; do
  curl -fsSL "$REPO_URL/phases/${phase}.md" -o "$SKILL_DIR/phases/${phase}.md"
done

# ------------------------------------------------
# [4/6] 下载 6 个参考文档 (v4.3: report-template 废弃迁至 assets/)
# ------------------------------------------------
echo "[4/6] 下载 6 个参考文档..."
for ref in \
    scoring-rubric \
    qualitative-frameworks \
    valuation-frameworks \
    search-strategy \
    html-template-guide \
    persona-registry; do
  curl -fsSL "$REPO_URL/references/${ref}.md" -o "$SKILL_DIR/references/${ref}.md"
done
# 保留 LEGACY 标注文件供参考(不让 LLM 读取)
curl -fsSL "$REPO_URL/references/report-template.LEGACY.md" -o "$SKILL_DIR/references/report-template.LEGACY.md"

# ------------------------------------------------
# [5/6] 下载 assets/ (v4.3 新增 - 报告骨架 + HTML 模板 + 审核 schema)
# ------------------------------------------------
echo "[5/6] 下载 assets/（v4.3 骨架强制）..."
# 2 个模板
curl -fsSL "$REPO_URL/assets/templates/report-skeleton.md"     -o "$SKILL_DIR/assets/templates/report-skeleton.md"
curl -fsSL "$REPO_URL/assets/templates/exec-summary-schema.md" -o "$SKILL_DIR/assets/templates/exec-summary-schema.md"
# 3 个 HTML
curl -fsSL "$REPO_URL/assets/html/base.html"       -o "$SKILL_DIR/assets/html/base.html"
curl -fsSL "$REPO_URL/assets/html/styles.css"      -o "$SKILL_DIR/assets/html/styles.css"
curl -fsSL "$REPO_URL/assets/html/components.html" -o "$SKILL_DIR/assets/html/components.html"
# 2 个 validation
curl -fsSL "$REPO_URL/assets/validation/report-checklist.json"     -o "$SKILL_DIR/assets/validation/report-checklist.json"
curl -fsSL "$REPO_URL/assets/validation/insight-card-schema.json"  -o "$SKILL_DIR/assets/validation/insight-card-schema.json"

# ------------------------------------------------
# [6/6] 下载 Python 数据层
# ------------------------------------------------
echo "[6/6] 下载 Python 数据层（scripts/）..."
for py in \
    __init__ \
    config \
    check_env \
    data_cache \
    tushare_collector \
    us_collector \
    hk_collector \
    pdf_reader \
    derived_metrics \
    financial_audit \
    report_parser \
    monitor \
    peer_collector \
    capital_flow \
    technical_analysis \
    update_index \
    build_html; do
  curl -fsSL "$REPO_URL/scripts/${py}.py" -o "$SKILL_DIR/scripts/${py}.py"
done
curl -fsSL "$REPO_URL/scripts/requirements.txt" -o "$SKILL_DIR/scripts/requirements.txt"
curl -fsSL "$REPO_URL/scripts/README.md" -o "$SKILL_DIR/scripts/README.md"

# ------------------------------------------------
# 验证
# ------------------------------------------------
PHASE_COUNT=$(find "$SKILL_DIR/phases" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
REF_COUNT=$(find "$SKILL_DIR/references" -name "*.md" 2>/dev/null ! -name "*.LEGACY.md" | wc -l | tr -d ' ')
SCRIPT_COUNT=$(find "$SKILL_DIR/scripts" -name "*.py" 2>/dev/null | wc -l | tr -d ' ')
ASSETS_COUNT=$(find "$SKILL_DIR/assets" -type f 2>/dev/null | wc -l | tr -d ' ')
# v4.3 期望: 7 phases + 6 refs (report-template.md 废弃) + 12 scripts + 7 assets + 1 SKILL.md = 33

if [ "$PHASE_COUNT" -eq "7" ] && [ "$REF_COUNT" -eq "6" ] && [ "$SCRIPT_COUNT" -eq "17" ] && [ "$ASSETS_COUNT" -eq "7" ]; then
    echo ""
    echo "============================================"
    echo "  ✅ 安装成功！(v4.3)"
    echo "============================================"
    echo ""
    echo "  协调器:  SKILL.md"
    echo "  阶段:    $PHASE_COUNT 个 (phases/)"
    echo "  框架:    $REF_COUNT 个 (references/)"
    echo "  脚本:    $SCRIPT_COUNT 个 Python 模块 (scripts/)"
    echo "  资产:    $ASSETS_COUNT 个 (assets/ - 报告骨架 + HTML 模板 + 审核 schema)"
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
    echo "     /company-analysis <公司名称> --monitor   # v4 量化监控"
    echo ""
    echo "示例："
    echo "  /company-analysis 贵州茅台 600519.SH     # A 股"
    echo "  /company-analysis Apple AAPL             # 美股"
    echo "  /company-analysis 腾讯控股 0700.HK       # 港股"
    echo ""
else
    echo ""
    echo "❌ 错误：安装不完整"
    echo "  预期(v4.6.1): phases=7 refs=6 scripts=17 assets=7"
    echo "  实际:       phases=$PHASE_COUNT refs=$REF_COUNT scripts=$SCRIPT_COUNT assets=$ASSETS_COUNT"
    exit 1
fi
