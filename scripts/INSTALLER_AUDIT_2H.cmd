@echo off
setlocal
set "TASK=Global Digital HQ Next - Audit 2h"
set "SCRIPT=%~dp0AUDIT_2H.cmd"
echo Installation de la tache Windows deux heures ...
schtasks /Create /F /SC HOURLY /MO 2 /TN "%TASK%" /TR "\"%SCRIPT%\""
if errorlevel 1 (echo ERREUR - planification non creee & pause & exit /b 1)
echo Tache creee. Voir taskschd.msc. Le PC doit etre allume.
pause
