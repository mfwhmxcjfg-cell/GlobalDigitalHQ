@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "GDHQ_DATA_DIR=%LOCALAPPDATA%\GlobalDigitalHQ_Next_1_1_Desktop\data"
set "PYTHON_CMD="
py -3.12 --version >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD (
  py -3 --version >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD set "PYTHON_CMD=python"
echo ==== Tests locaux ====
%PYTHON_CMD% -m unittest discover -s tests -q
if errorlevel 1 (echo [ERREUR] Tests non valides. & pause & exit /b 1)
echo ==== Base de donnees et profils ====
%PYTHON_CMD% -m gdhq.cli verify
if errorlevel 1 (echo [ERREUR] Verification du moteur. & pause & exit /b 2)
echo ==== LM Studio (serveur local seulement) ====
%PYTHON_CMD% -m gdhq.cli models
if errorlevel 1 echo [INFO] LM Studio est arrete, aucun modele charge ou serveur non disponible. Ceci ne bloque pas l'interface.
echo.
pause
