@echo off
echo Running Alembic migrations...
cd /d "%~dp0"
.venv\Scripts\alembic.exe upgrade head
if %ERRORLEVEL% NEQ 0 (
    echo Migration FAILED.
    pause
) else (
    echo Migration OK.
)
