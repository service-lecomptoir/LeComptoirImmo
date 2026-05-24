@echo off
title LeComptoirImmo - Backend
cd /d "%~dp0backend"

:: Tuer toute instance precedente sur le port 8000
echo Arret des instances precedentes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr " 0.0.0.0:8000 " 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

:: Eviter le cache .pyc (probleme OneDrive/Windows)
set PYTHONDONTWRITEBYTECODE=1

echo Demarrage du backend FastAPI sur http://localhost:8000 ...
echo API Docs: http://localhost:8000/api/docs
echo.
.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
pause
