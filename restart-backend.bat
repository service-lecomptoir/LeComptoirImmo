@echo off
title LeComptoirImmo - Redemarrage Backend
echo ================================================
echo   Redemarrage du backend LeComptoirImmo
echo ================================================
echo.

:: 1. Tuer les instances actives sur 8000
echo [1/3] Arret du backend en cours...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr " 0.0.0.0:8000 " 2^>nul') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr " 127.0.0.1:8000 " 2^>nul') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 /nobreak >nul

:: 2. Nettoyer le cache Python (evite les routes non detectees sur OneDrive)
echo [2/3] Nettoyage du cache Python...
cd /d "%~dp0backend"
for /d /r "app" %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d" 2>nul
)
echo     Cache nettoye.

:: 3. Redemarrer uvicorn
echo [3/3] Demarrage du backend...
set PYTHONDONTWRITEBYTECODE=1
echo.
echo Backend accessible sur http://localhost:8000
echo API Docs : http://localhost:8000/api/docs
echo.
.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
pause
