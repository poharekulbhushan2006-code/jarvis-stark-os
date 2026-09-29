@echo off
title Uninstall J.A.R.V.I.S. Background Auto-Start
cd /d "%~dp0"

echo ========================================================
echo   REMOVING J.A.R.V.I.S. FROM WINDOWS STARTUP
echo ========================================================
echo.

set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_FOLDER%\JarvisBackgroundListener.lnk
set OLD_VBS=%STARTUP_FOLDER%\JarvisBackgroundListener.vbs

if exist "%SHORTCUT_PATH%" (
    del /f /q "%SHORTCUT_PATH%"
    echo [*] Removed %SHORTCUT_PATH%
)

if exist "%OLD_VBS%" (
    del /f /q "%OLD_VBS%"
    echo [*] Removed %OLD_VBS%
)

echo [SUCCESS] J.A.R.V.I.S. has been removed from Windows Startup.
echo.
pause
