@echo off
title J.A.R.V.I.S. Lock Screen Password Setup
cd /d "%~dp0"

echo ========================================================
echo   J.A.R.V.I.S. SECURE LOCK SCREEN CREDENTIAL SETUP
echo ========================================================
echo.

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0setup_lockscreen.py"
) else (
    python "%~dp0setup_lockscreen.py"
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Setup encountered an issue (Exit Code: %ERRORLEVEL%).
)

echo.
pause
