@echo off
setlocal
cd /d "%~dp0"
title Chispazo Exact5 Lab - Subir a GitHub

echo ============================================================
echo  CHISPAZO EXACT5 LAB - SUBIDA A GITHUB V2
echo ============================================================
echo.
echo Repositorio destino:
echo https://github.com/mxjava/chispazo-exact5-lab
echo.

where git >nul 2>&1
if errorlevel 1 goto NOGIT

set "GITNAME="
for /f "usebackq delims=" %%i in (`git config --global user.name 2^>nul`) do set "GITNAME=%%i"
if defined GITNAME goto CHECKEMAIL

set /p "GITNAME=Nombre para Git: "
if not defined GITNAME set "GITNAME=mxjava"
git config --global user.name "%GITNAME%"

:CHECKEMAIL
set "GITEMAIL="
for /f "usebackq delims=" %%i in (`git config --global user.email 2^>nul`) do set "GITEMAIL=%%i"
if defined GITEMAIL goto INIT

set /p "GITEMAIL=Email para Git: "
if not defined GITEMAIL goto NOEMAIL
git config --global user.email "%GITEMAIL%"

:INIT
if exist ".git" goto BRANCH
git init
if errorlevel 1 goto ERROR

:BRANCH
git branch -M main
if errorlevel 1 goto ERROR

git remote remove origin >nul 2>&1
git remote add origin https://github.com/mxjava/chispazo-exact5-lab.git
if errorlevel 1 goto ERROR

git add .
if errorlevel 1 goto ERROR

git diff --cached --quiet
if not errorlevel 1 goto PUSH

git commit -m "Initial Chispazo Exact5 Lab V263-V265"
if errorlevel 1 goto ERROR

:PUSH
echo.
echo Si GitHub abre el navegador, inicia sesion con la cuenta mxjava.
echo.
git push -u origin main
if errorlevel 1 goto ERROR

echo.
echo ============================================================
echo  LISTO: proyecto subido correctamente.
echo ============================================================
echo https://github.com/mxjava/chispazo-exact5-lab
echo.
pause
exit /b 0

:NOGIT
echo ERROR: Git no esta instalado o no esta en PATH.
pause
exit /b 1

:NOEMAIL
echo ERROR: necesitas indicar un email para crear el commit.
pause
exit /b 1

:ERROR
echo.
echo ============================================================
echo ERROR: no se pudo completar la operacion.
echo Mandame una captura de esta pantalla y lo resolvemos.
echo ============================================================
pause
exit /b 1
