@echo off
title J.A.R.V.I.S. Biometric Voice Enrollment
cd /d "%~dp0"

echo ========================================================
echo   J.A.R.V.I.S. BIOMETRIC VOICE REGISTRATION
echo ========================================================
echo.

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0register_voice.py"
) else (
    python "%~dp0register_voice.py"
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Voice registration encountered an issue (Exit Code: %ERRORLEVEL%).
)

echo.
pause
