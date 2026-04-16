# Claude Code - Company Analysis Skill

A Claude Code custom skill for systematically analyzing C/D round funding companies for investment decision making.

## Features

- **10-dimension scoring system** with weighted composite score
- **Structured web research** — 6 rounds of automated searches ensuring latest data
- **Online sentiment analysis** — collects opinions from investors, analysts, customers, employees, and social media; classifies into bullish vs bearish camps
- **Data freshness enforcement** — all data timestamped, outdated info flagged
- **Detailed report output** — executive summary, scoring table, per-dimension analysis, comparable companies, and source citations
- **Saves report as Markdown file** for easy sharing

## Analysis Dimensions

| # | Dimension | Weight |
|---|-----------|--------|
| 1 | Business Model & Unit Economics | 1.5x |
| 2 | Market Opportunity (TAM/SAM/SOM) | 1.5x |
| 3 | Competitive Landscape & Moat | 1.5x |
| 4 | Growth Metrics & Traction | 1.5x |
| 5 | Team & Leadership | 1.0x |
| 6 | Product & Technology | 1.0x |
| 7 | Financial Health & Capital Efficiency | 1.0x |
| 8 | Risks & Challenges | 1.0x |
| 9 | Funding History & Valuation | 0.75x |
| 10 | Exit Potential | 0.75x |

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/install.sh | bash
```

## Manual Install

```bash
mkdir -p ~/.claude/skills/company-analysis/references
cd ~/.claude/skills/company-analysis

# Download all files
curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/SKILL.md -o SKILL.md
curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/references/scoring-rubric.md -o references/scoring-rubric.md
curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/references/search-strategy.md -o references/search-strategy.md
curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/references/report-template.md -o references/report-template.md
```

## Usage

In Claude Code (CLI or VS Code extension), type:

```
/company-analysis Stripe
```

The skill will:
1. Ask if you have internal materials (pitch deck, financials, etc.)
2. Run 6 rounds of web searches for the latest public data
3. Collect and analyze online reviews and market sentiment
4. Score across 10 dimensions (1-10 scale, weighted)
5. Generate a full analysis report and save it as a `.md` file

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/leafpaper/claude-company-analysis/main/uninstall.sh | bash
```

Or manually:

```bash
rm -rf ~/.claude/skills/company-analysis
```

## License

MIT
