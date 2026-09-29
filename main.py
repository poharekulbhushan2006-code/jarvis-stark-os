"""
J.A.R.V.I.S. Main Launcher
Starts the Jarvis Web HUD server and opens the browser interface.
"""

import os
import sys
import time
import webbrowser
import threading
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

# Load environment
load_dotenv()

if "--wake" in sys.argv:
    os.environ["JARVIS_WAKE_BOOT"] = "1"

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
USER_NAME = os.getenv("USER_NAME", "Sir")

BANNER = r"""
       _     ___     ______   __     __  ___    ____  
      | |   /   \   |  _ \ \ / /    |  |/ __\  / ___| 
   _  | |  / _ \ \  | |_) \ V /     |  |\__ \  \___ \ 
  | |_| | / ___ \ \ |  _ < | |   _  |  | ___) | ___) |
   \___/ /_/   \_\| |_| \_\|_|  (_) |__| \___/ |____/ 
                                                       
   ====================================================
   STARK INDUSTRIES // AUTONOMOUS LAPTOP AI ASSISTANT
   ====================================================
"""

def open_browser_delayed(url: str, delay: float = 1.5):
    """Opens the HUD interface in default web browser after server initializes."""
    time.sleep(delay)
    print(f"\n[JARVIS] Launching Holographic HUD at: {url}")
    webbrowser.open(url)

def main():
    print(BANNER)
    hud_url = f"http://localhost:{PORT}"
    print(f"[*] Initializing Core Neural Network...")
    print(f"[*] Interface Address: {hud_url}")
    print(f"[*] Master: {USER_NAME}")
    print(f"[*] Audio Engine: Microsoft Edge Neural TTS (en-GB-RyanNeural)")
    print(f"[*] Press CTRL+C to disconnect Jarvis.\n")

    # Start browser opener in background thread
    threading.Thread(target=open_browser_delayed, args=(hud_url,), daemon=True).start()

    # Launch Uvicorn Server
    uvicorn.run(
        "server:app",
        host=HOST,
        port=PORT,
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    main()
