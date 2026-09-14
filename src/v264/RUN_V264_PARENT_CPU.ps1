$ErrorActionPreference = "Stop"
python .\CHISPAZO_V264_PARENT_REPAIR.py `
  --history "D:\melate\Chispazo.csv" `
  --ml --gpu-optional `
  --lines 30 `
  --backtest 100 `
  --v249-full-refresh `
  --prospective-register
