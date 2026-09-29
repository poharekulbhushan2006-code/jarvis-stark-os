@echo off
title J.A.R.V.I.S. Background Listener (Double-Clap & Wake-Word)
cd /d "%~dp0"

echo ========================================================
echo   J.A.R.V.I.S. AUTONOMOUS BACKGROUND LISTENER
echo ========================================================
echo.
echo [*] Persona: Authentic J.A.R.V.I.S. (British Male - Paul Bettany Style)
echo [*] Trigger 1: Clap your hands 2 times
echo [*] Trigger 2: Say "Jarvis" or "Unlock"
echo [*] Auto-Action: Plays "Welcome back, Sir" and launches Stark HUD
echo.
echo Listening in background... (Press CTRL+C to stop)
echo.

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe background_listener.py
) else (
    python background_listener.py
)

pause
