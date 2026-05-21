@echo off
title Locataire Cloud - Frontend
cd /d "%~dp0frontend"
echo Demarrage du frontend Vite sur http://localhost:5173 ...
echo.
"%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\npm.cmd" run dev
pause
