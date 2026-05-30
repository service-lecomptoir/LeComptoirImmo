@echo off
title Alice
for /f "tokens=5" %%a in ('netstat -aon ^| findstr " 0.0.0.0:8001 " 2^>nul') do taskkill /F /PID %%a >nul 2>&1
timeout /t 1 /nobreak >nul
set PYTHONDONTWRITEBYTECODE=1
cd /d "%~dp0alice\backend"
"%~dp0backend\.venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8001 --reload
pause
