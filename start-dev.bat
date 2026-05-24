@echo off
echo ================================================
echo   LeComptoirImmo - Environnement de dev local
echo ================================================
echo.

:: Tuer les instances precedentes
echo Arret des instances precedentes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr " 0.0.0.0:8000 " 2^>nul') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr " 127.0.0.1:8000 " 2^>nul') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173 " 2^>nul') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 /nobreak >nul

echo Demarrage du backend  >> http://localhost:8000
echo Demarrage du frontend >> http://localhost:5173
echo.

:: PYTHONDONTWRITEBYTECODE=1 evite les .pyc stales sur OneDrive
start "LeCI - Backend" cmd /k "title LeCI - Backend && set PYTHONDONTWRITEBYTECODE=1 && cd /d "%~dp0backend" && .venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload"
timeout /t 3 /nobreak >nul
start "LeCI - Frontend" cmd /k "title LeCI - Frontend && cd /d "%~dp0frontend" && "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\npm.cmd" run dev"

echo.
echo Les deux serveurs demarrent dans leurs fenetres.
echo Ouvrez : http://localhost:5173
echo.
pause
