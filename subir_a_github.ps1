$ErrorActionPreference = "Stop"
$repo = "https://github.com/mxjava/chispazo-exact5-lab.git"

Write-Host "============================================================"
Write-Host " CHISPAZO EXACT5 LAB - SUBIDA A GITHUB"
Write-Host "============================================================"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git no esta instalado o no esta en PATH." -ForegroundColor Red
    Write-Host "Instala Git for Windows y vuelve a ejecutar este script."
    exit 1
}

$name = git config --global user.name
$email = git config --global user.email
if (-not $name) {
    $name = Read-Host "Nombre para Git"
    git config --global user.name "$name"
}
if (-not $email) {
    $email = Read-Host "Email de GitHub"
    git config --global user.email "$email"
}

if (-not (Test-Path ".git")) { git init }
git branch -M main
git remote remove origin 2>$null
git remote add origin $repo
git add .

$staged = git diff --cached --name-only
if ($staged) {
    git commit -m "Initial Chispazo Exact5 Lab V263-V265"
}

Write-Host ""
Write-Host "GitHub puede abrir una ventana de autenticacion. Usa la cuenta mxjava."
git push -u origin main

Write-Host ""
Write-Host "LISTO: https://github.com/mxjava/chispazo-exact5-lab" -ForegroundColor Green
