@echo off
title Alice - Demarrage complet

:: ── Backend ───────────────────────────────────────────────────────────────────
echo [Alice] Arret des instances precedentes sur le port 8001...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr " 0.0.0.0:8001 " 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

set PYTHONDONTWRITEBYTECODE=1

echo [Alice] Demarrage du backend FastAPI sur http://localhost:8001 ...
start "Alice Backend" cmd /k "cd /d "%~dp0backend" && "%~dp0..\backend\.venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8001 --reload"

timeout /t 3 /nobreak >nul

:: ── Frontend ──────────────────────────────────────────────────────────────────
echo [Alice] Demarrage du frontend Vite sur http://localhost:5174 ...
start "Alice Frontend" cmd /k "cd /d "%~dp0frontend" && "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\npm.cmd" run dev"

echo.
echo [Alice] Services demarres :
echo   Backend  : http://localhost:8001
echo   API Docs : http://localhost:8001/api/docs
echo   Frontend : http://localhost:5174
echo.
pause
