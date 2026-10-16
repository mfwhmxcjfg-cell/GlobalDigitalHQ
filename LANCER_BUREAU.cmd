@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Global Digital HQ Next 1.1 - Serveur local
set "GDHQ_DATA_DIR=%LOCALAPPDATA%\GlobalDigitalHQ_Next_1_1_Desktop\data"
set "PYTHONUTF8=1"
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
 echo [ERREUR] Python 3.11+ introuvable.
 pause
 exit /b 1
)
%PYTHON_CMD% -c "import socket,sys; s=socket.socket(); s.settimeout(.7); occupied=s.connect_ex(('127.0.0.1',8824))==0;s.close();sys.exit(1 if occupied else 0)"
if errorlevel 1 (
 echo [INFO] Le port 8824 est deja utilise. Fermez l'ancien serveur Global Next avant de relancer.
 echo Ouvrir manuellement http://127.0.0.1:8824/ seulement si c'est votre Global.
 pause
 exit /b 2
)
start "" /MIN powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\OUVRIR_INTERFACE.ps1"
echo Demarrage de Global Digital HQ Next sur http://127.0.0.1:8824/
echo Garder cette fenetre ouverte pendant l'utilisation.
%PYTHON_CMD% -m gdhq.cli serve --port 8824
if errorlevel 1 (
 echo [ERREUR] Echec du serveur. Utilisez DIAGNOSTIC_BUREAU.cmd.
 pause
 exit /b 3
)
