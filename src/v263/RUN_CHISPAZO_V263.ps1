param(
  [Parameter(Mandatory=$true)][string]$Ranking,
  [Parameter(Mandatory=$true)][int]$Target,
  [string]$History = "D:\melate\Chispazo.csv",
  [string]$V262Config = "$PSScriptRoot\chispazo_v262.toml",
  [string]$AuditOut = "D:\melate\resultados_v263_$Target"
)
python "$PSScriptRoot\CHISPAZO_V263_PRODUCTION_GATE.py" `
  --ranking $Ranking `
  --target $Target `
  --history $History `
  --expected-last ($Target-1) `
  --v262-config $V262Config `
  --audit-out-dir $AuditOut
exit $LASTEXITCODE
