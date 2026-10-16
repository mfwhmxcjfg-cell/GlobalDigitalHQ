@echo off
setlocal
cd /d "%~dp0.."
set "GDHQ_DATA_DIR=%LOCALAPPDATA%\GlobalDigitalHQ_Next_1_1_Desktop\data"
py -3.12 --version >nul 2>nul
if not errorlevel 1 (
  py -3.12 -m gdhq.cli audit
) else (
  python -m gdhq.cli audit
)
