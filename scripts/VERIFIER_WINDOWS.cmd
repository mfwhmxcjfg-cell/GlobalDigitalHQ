@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONUTF8=1"
py -3.12 --version >nul 2>nul
if not errorlevel 1 (
  py -3.12 -m unittest discover -s tests -v
  if errorlevel 1 (echo Tests en echec & pause & exit /b 1)
  py -3.12 -m gdhq.cli verify
) else (
  python -m unittest discover -s tests -v
  if errorlevel 1 (echo Tests en echec & pause & exit /b 1)
  python -m gdhq.cli verify
)
pause
