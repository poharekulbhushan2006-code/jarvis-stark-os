@echo off
title Stop J.A.R.V.I.S. Processes
cd /d "%~dp0"

echo Stopping all running J.A.R.V.I.S. servers and background listeners...

taskkill /F /IM python.exe /FI "WINDOWTITLE eq J.A.R.V.I.S.*" 2>nul
taskkill /F /IM pythonw.exe 2>nul
wmic process where "CommandLine like '%%background_listener.py%%'" call terminate >nul 2>&1
wmic process where "CommandLine like '%%uvicorn server:app%%'" call terminate >nul 2>&1

echo [DONE] All J.A.R.V.I.S. processes stopped.
pause
