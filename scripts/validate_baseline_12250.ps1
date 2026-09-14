$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
python -m src.validation.preflight_v2 `
  --history data/history/Chispazo_through_12249.csv `
  --target 12250 `
  --firewall-report reports/v264_firewall100_report.json `
  --exactset-summary reports/v264_summary.json `
  --out runs/preflight_12250.json
exit $LASTEXITCODE
