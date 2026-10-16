@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title Global Digital HQ Next - Installation Bureau

echo ===========================================================
echo    Global Digital HQ Next 1.1 - Installation Bureau
 echo    Installation locale, gratuite et sans GitHub.
echo ===========================================================
echo.
set "PYTHON_CMD="
py -3.12 -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD (
  py -3 -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  python -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
 echo [BLOQUE] Python 3.11 ou plus recent est necessaire.
 echo Installer Python 3.12 depuis https://www.python.org/downloads/windows/
 echo Puis relancer ce fichier. Aucune modification apportee.
 pause
 exit /b 2
)
where node >nul 2>nul
if errorlevel 1 (
 echo [INFO] Node.js absent. Installation possible : le moteur et LM Studio fonctionnent sans Node.
 echo [INFO] Seule la validation des modifications JavaScript generees par IA sera desactivee.
 echo [INFO] Pour activer cette fonction plus tard, installer Node.js LTS : https://nodejs.org/
) else (
 echo [INFO] Node.js detecte : verification JavaScript disponible.
)
echo.
echo [1/4] Verification des empreintes et du code avant installation...
%PYTHON_CMD% scripts\VERIFIER_EMPREINTES.py
if errorlevel 1 (
 echo [BLOQUE] Fichiers incomplets ou modifies. Aucune installation effectuee.
 pause
 exit /b 7
)
%PYTHON_CMD% -m unittest discover -s tests -q
if errorlevel 1 (
 echo [BLOQUE] Des tests echouent. Aucune installation effectuee.
 echo Envoyer une capture de cette fenetre a ChatGPT.
 pause
 exit /b 3
)
set "ROOT=%LOCALAPPDATA%\GlobalDigitalHQ_Next_1_1_Desktop"
set "DEST=%ROOT%\app"
set "GDHQ_DATA_DIR=%ROOT%\data"
if not exist "%ROOT%" mkdir "%ROOT%"
if not exist "%DEST%" mkdir "%DEST%"
if not exist "%GDHQ_DATA_DIR%" mkdir "%GDHQ_DATA_DIR%"
echo [2/4] Copie dans un dossier separe : %DEST%
robocopy "%~dp0" "%DEST%" /E /XD __pycache__ .git .pytest_cache /XF *.pyc /NFL /NDL /NJH /NJS /NC /NS >nul
if errorlevel 8 (
 echo [ERREUR] Copie Windows impossible. Les anciennes versions restent intactes.
 pause
 exit /b 4
)
echo [3/4] Validation de l'application installee...
pushd "%DEST%"
%PYTHON_CMD% -m gdhq.cli verify
if errorlevel 1 (
 popd
 echo [ERREUR] Validation locale impossible. Anciennes versions intactes.
 pause
 exit /b 5
)
popd
set "GDHQ_LAUNCHER=%DEST%\LANCER_BUREAU.cmd"
set "GDHQ_WORKDIR=%DEST%"
echo [4/4] Creation du raccourci du Bureau...
powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop';$d=[Environment]::GetFolderPath('Desktop');$f=Join-Path $d 'Global Digital HQ Next 1.1.lnk';$s=(New-Object -ComObject WScript.Shell).CreateShortcut($f);$s.TargetPath=$env:GDHQ_LAUNCHER;$s.WorkingDirectory=$env:GDHQ_WORKDIR;$s.Description='Global Digital HQ Next 1.1 - Local et sans depenses';$s.Save();Write-Host ('Raccourci cree : '+$f)"
if errorlevel 1 (
 echo [ERREUR] Application installee, mais raccourci impossible.
 echo Lancez directement : "%GDHQ_LAUNCHER%"
 pause
 exit /b 6
)
echo.
echo [OK] Installation terminee. Les versions V8 et Hybrid sont inchangees.
echo [OK] Double-cliquez Global Digital HQ Next 1.1 sur le Bureau.
echo [INFO] Donnees dans %GDHQ_DATA_DIR%
echo [INFO] LM Studio : charger Qwen3.5 9B et demarrer son serveur 1234.
echo.
pause
exit /b 0
