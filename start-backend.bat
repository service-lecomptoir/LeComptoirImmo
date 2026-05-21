@echo off
title Locataire Cloud - Backend
cd /d "%~dp0backend"
echo Demarrage du backend FastAPI sur http://localhost:8000 ...
echo API Docs: http://localhost:8000/api/docs
echo.
.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
pause
