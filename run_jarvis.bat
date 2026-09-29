@echo off
title J.A.R.V.I.S. // Stark Industries Desktop AI
color 0b
echo ====================================================
echo        INITIALIZING J.A.R.V.I.S. SYSTEM
echo ====================================================

cd /d "%~dp0"

:: Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo [*] Virtual environment not found. Setting up .venv...
    python -m venv .venv
    echo [*] Installing dependencies from requirements.txt...
    .venv\Scripts\pip.exe install -r requirements.txt
)

:: Run Jarvis Main Launcher
echo [*] Starting J.A.R.V.I.S. Core Interface...
.venv\Scripts\python.exe main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Jarvis stopped with an error code: %ERRORLEVEL%
    pause
)
