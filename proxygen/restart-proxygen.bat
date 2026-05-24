@echo off
title ProxyGen - Redemarrage

echo [ProxyGen] Arret des services en cours...

:: Tuer backend port 8001
for /f "tokens=5" %%a in ('netstat -aon ^| findstr " 0.0.0.0:8001 " 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Tuer frontend port 5174
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5174 " 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

timeout /t 3 /nobreak >nul

set PYTHONDONTWRITEBYTECODE=1

echo [ProxyGen] Redemarrage du backend...
start "ProxyGen Backend" cmd /k "cd /d "%~dp0backend" && "%~dp0..\backend\.venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8001 --reload"

timeout /t 3 /nobreak >nul

echo [ProxyGen] Redemarrage du frontend...
start "ProxyGen Frontend" cmd /k "cd /d "%~dp0frontend" && "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\npm.cmd" run dev"

echo.
echo [ProxyGen] Redemarrage termine.
echo   Backend  : http://localhost:8001
echo   Frontend : http://localhost:5174
echo.
pause
