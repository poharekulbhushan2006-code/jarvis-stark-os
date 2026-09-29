"""
Installs J.A.R.V.I.S. Background Listener to Windows Startup.
"""

import os
import sys
from pathlib import Path
import win32com.client

BASE_DIR = Path(__file__).resolve().parent
APPDATA = os.environ.get("APPDATA", "")
STARTUP_DIR = Path(APPDATA) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
SHORTCUT_PATH = STARTUP_DIR / "JarvisBackgroundListener.lnk"
VBS_TARGET = BASE_DIR / "run_jarvis_silent.vbs"

def install():
    print(f"[*] Project directory: {BASE_DIR}")
    print(f"[*] Target VBS runner: {VBS_TARGET}")
    print(f"[*] Destination: {SHORTCUT_PATH}")

    if not STARTUP_DIR.exists():
        STARTUP_DIR.mkdir(parents=True, exist_ok=True)

    ws = win32com.client.Dispatch("WScript.Shell")
    shortcut = ws.CreateShortcut(str(SHORTCUT_PATH))
    shortcut.TargetPath = "wscript.exe"
    shortcut.Arguments = f'"{VBS_TARGET}"'
    shortcut.WorkingDirectory = str(BASE_DIR)
    shortcut.WindowStyle = 7  # Minimized
    shortcut.Description = "J.A.R.V.I.S. Autonomous Background Listener"
    shortcut.Save()

    if SHORTCUT_PATH.exists():
        print(f"[SUCCESS] J.A.R.V.I.S. installed to Windows Startup!")
        print(f"File created: {SHORTCUT_PATH}")
        return True
    else:
        print("[ERROR] Failed to create shortcut.")
        return False

if __name__ == "__main__":
    install()
