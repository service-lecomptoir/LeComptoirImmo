@echo off
title Alice - Frontend
cd /d "%~dp0alice\frontend"
"%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\npm.cmd" run dev
pause
