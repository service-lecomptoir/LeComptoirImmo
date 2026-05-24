@echo off
title ProxyGen - Frontend
cd /d "%~dp0proxygen\frontend"
"%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\npm.cmd" run dev
pause
