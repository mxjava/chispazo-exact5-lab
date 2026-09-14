@echo off
setlocal
cd /d "%~dp0"
where git >nul 2>&1
if errorlevel 1 goto NOGIT

git add .
if errorlevel 1 goto ERROR
git diff --cached --quiet
if not errorlevel 1 goto PUSH
git commit -m "V266 prospective integrity pipeline and full V263-V265 sources"
if errorlevel 1 goto ERROR
:PUSH
git push origin main
if errorlevel 1 goto ERROR
echo.
echo LISTO: V266 subido a GitHub.
pause
exit /b 0
:NOGIT
echo ERROR: Git no esta disponible en PATH.
pause
exit /b 1
:ERROR
echo ERROR: no se pudo completar commit/push.
pause
exit /b 1
