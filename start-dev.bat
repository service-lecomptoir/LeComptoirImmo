@echo off
echo ================================================
echo   Locataire Cloud - Environnement de dev local
echo ================================================
echo.
echo Demarrage du backend  → http://localhost:8000
echo Demarrage du frontend → http://localhost:5173
echo.
start "Backend" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload"
timeout /t 3 /nobreak >nul
start "Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"
echo.
echo Les deux serveurs sont en cours de demarrage dans leurs fenetres respectives.
echo Attendez quelques secondes puis ouvrez: http://localhost:5173
echo.
pause
