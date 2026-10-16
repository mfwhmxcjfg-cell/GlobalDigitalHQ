@echo off
setlocal
set "GDHQ_HOME=D:\GlobalDigitalHQ"
set "TEMP=%GDHQ_HOME%\temp"
set "TMP=%TEMP%"
set "PIP_CACHE_DIR=%GDHQ_HOME%\pip-cache"
set "PLAYWRIGHT_BROWSERS_PATH=%GDHQ_HOME%\browsers"
if not exist "%TEMP%" mkdir "%TEMP%"
echo Installation de Playwright et Chromium sur D:. Fermer Global avant de continuer.
python -m venv "%GDHQ_HOME%\venv"
if errorlevel 1 goto failed
"%GDHQ_HOME%\venv\Scripts\python.exe" -m pip install --disable-pip-version-check playwright==1.64.0
if errorlevel 1 goto failed
"%GDHQ_HOME%\venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 goto failed
echo Installation terminee. Relancer D:\GlobalDigitalHQ\LANCER_GLOBAL.cmd
pause
exit /b 0
:failed
echo Installation incomplete. Les API HTTP restent utilisables sans Playwright.
pause
exit /b 1
