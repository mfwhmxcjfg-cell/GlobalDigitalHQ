@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONUTF8=1"
py -3.12 --version >nul 2>nul
if not errorlevel 1 (
  py -3.12 -m gdhq.cli serve --port 8824
) else (
  python -m gdhq.cli serve --port 8824
)
if errorlevel 1 (
 echo.
 echo ERREUR : installer Python 3.12 ou verifier le port 8824.
 pause
)
