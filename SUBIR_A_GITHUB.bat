@echo off
setlocal
title Chispazo Exact5 Lab - Subir a GitHub

echo ============================================================
echo  CHISPAZO EXACT5 LAB - SUBIDA A GITHUB
echo ============================================================
echo.
echo Repositorio destino:
echo https://github.com/mxjava/chispazo-exact5-lab
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo ERROR: Git no esta instalado o no esta en PATH.
  echo Instala Git for Windows desde https://git-scm.com/download/win
  echo y vuelve a ejecutar este archivo.
  pause
  exit /b 1
)

for /f "delims=" %%i in ('git config --global user.name 2^>nul') do set GITNAME=%%i
for /f "delims=" %%i in ('git config --global user.email 2^>nul') do set GITEMAIL=%%i

if "%GITNAME%"=="" (
  set /p GITNAME=Escribe tu nombre para Git (ej. Jose Maciel): 
  git config --global user.name "%GITNAME%"
)

if "%GITEMAIL%"=="" (
  set /p GITEMAIL=Escribe tu email de GitHub: 
  git config --global user.email "%GITEMAIL%"
)

if not exist .git (
  git init
  if errorlevel 1 goto :error
)

git branch -M main
git remote remove origin >nul 2>nul
git remote add origin https://github.com/mxjava/chispazo-exact5-lab.git
if errorlevel 1 goto :error

git add .
if errorlevel 1 goto :error

git diff --cached --quiet
if errorlevel 1 (
  git commit -m "Initial Chispazo Exact5 Lab V263-V265"
  if errorlevel 1 goto :error
) else (
  echo No hay cambios nuevos para commit.
)

echo.
echo Se abrira el inicio de sesion de GitHub si es necesario.
echo Autoriza con tu cuenta mxjava.
echo.

git push -u origin main
if errorlevel 1 goto :error

echo.
echo ============================================================
echo  LISTO: proyecto subido correctamente a GitHub.
echo ============================================================
echo https://github.com/mxjava/chispazo-exact5-lab
echo.
pause
exit /b 0

:error
echo.
echo ============================================================
echo  ERROR: Git no pudo completar la operacion.
echo  Copia la pantalla o mandame una captura y te digo que hacer.
echo ============================================================
pause
exit /b 1
