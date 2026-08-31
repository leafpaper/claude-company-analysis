# ==============================================================
#  Claude Code Investment-Analysis Skill - Windows installer (v8.3)
#  Mirrors install.sh for Windows. Installs this repo into ~/.claude:
#    - skill body    -> ~/.claude/skills/company-analysis/
#    - sub-agents    -> ~/.claude/agents/company-analysis/  (subagent_type source)
#
#  Usage (run from the cloned repo root):
#    powershell -ExecutionPolicy Bypass -File .\install.ps1
#
#  NOTE: kept ASCII-only on purpose. Windows PowerShell 5.1 reads .ps1 as the
#  system ANSI codepage unless a UTF-8 BOM is present, so non-ASCII here would
#  corrupt parsing. Keep it ASCII.
# ==============================================================
$ErrorActionPreference = "Stop"

$Src    = $PSScriptRoot
$Skill  = Join-Path $env:USERPROFILE ".claude\skills\company-analysis"
$Agents = Join-Path $env:USERPROFILE ".claude\agents\company-analysis"

Write-Host "================================================"
Write-Host "  Claude Code - Investment Analysis Skill (Windows v8.3)"
Write-Host "  Source: $Src"
Write-Host "================================================"

foreach ($d in @($Skill, $Agents)) {
  if (Test-Path $d) { Remove-Item $d -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $d | Out-Null
}

Copy-Item (Join-Path $Src "SKILL.md") -Destination $Skill -Force
foreach ($dir in @("phases", "references", "assets", "scripts")) {
  Copy-Item (Join-Path $Src $dir) -Destination $Skill -Recurse -Force
}
Copy-Item (Join-Path $Src "agents\*.md") -Destination $Agents -Force

$phaseN  = (Get-ChildItem (Join-Path $Skill "phases")     -Filter *.md).Count
$refN    = (Get-ChildItem (Join-Path $Skill "references") -Filter *.md).Count
$scriptN = (Get-ChildItem (Join-Path $Skill "scripts")    -Filter *.py).Count
$agentN  = (Get-ChildItem $Agents -Filter *.md).Count

Write-Host ""
Write-Host "Installed:"
Write-Host "  skill body : $Skill"
Write-Host "  phases     : $phaseN"
Write-Host "  references : $refN"
Write-Host "  scripts    : $scriptN"
Write-Host "  sub-agents : $agentN  ($Agents)"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Install deps (use real Python, NOT the Microsoft Store stub):"
Write-Host "       py -3 -m pip install --user tushare yfinance pypdf pandas pyarrow markdown requests pyyaml jsonschema"
Write-Host "  2. Set Tushare token (A-share / HK):"
Write-Host "       [Environment]::SetEnvironmentVariable('TUSHARE_TOKEN','your_token','User')"
Write-Host "  3. In Claude Code:  /company-analysis <company> <ticker>"
Write-Host ""
Write-Host "  Note: on Windows use 'py -3' (the skill auto-detects PYBIN)."
