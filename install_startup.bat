@echo off
title Install J.A.R.V.I.S. Background Auto-Start
cd /d "%~dp0"

echo ========================================================
echo   INSTALLING J.A.R.V.I.S. TO WINDOWS STARTUP
echo ========================================================
echo.

set SCRIPT_DIR=%~dp0
set VBS_TARGET=%SCRIPT_DIR%run_jarvis_silent.vbs
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_FOLDER%\JarvisBackgroundListener.lnk

echo [*] Creating Windows Startup shortcut...
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%VBS_TARGET%\"'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.WindowStyle = 7; $s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo [SUCCESS] J.A.R.V.I.S. Autonomous Listener installed to Windows Startup!
    echo.
    echo Location: %SHORTCUT_PATH%
    echo Target:   wscript.exe "%VBS_TARGET%"
    echo.
    echo Next time your laptop boots up:
    echo - Jarvis will automatically listen in the background (0 windows open).
    echo - 2 Claps or "Jarvis" will trigger the system, unlock the screen, and greet you.
    echo - 100%% offline operation with zero internet dependency.
    echo.
    echo Starting the background listener right now...
    start "" wscript.exe "%VBS_TARGET%"
    echo [ONLINE] Background Listener is now active!
) else (
    echo [ERROR] Failed to create Startup shortcut. Please run as Administrator if restricted.
)

echo.
pause
