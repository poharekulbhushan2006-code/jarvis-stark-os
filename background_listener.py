"""
J.A.R.V.I.S. Background Audio Listener
Listens continuously in the background for 2 Claps or 'Jarvis' and launches the system automatically.
Safely logs all background telemetry to notes/detector.log.
"""

import os
import sys
import traceback
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Unconditionally log all output to notes/detector.log
LOG_DIR = BASE_DIR / "notes"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "detector.log"

class DualLogger:
    def __init__(self, original_stream, file_path):
        self.original = original_stream
        self.file = None
        try:
            self.file = open(file_path, "a", encoding="utf-8", buffering=1)
        except Exception:
            pass

    def write(self, data):
        if self.original:
            try:
                self.original.write(data)
                self.original.flush()
            except Exception:
                pass
        if self.file:
            try:
                self.file.write(data)
                self.file.flush()
            except Exception:
                pass

    def flush(self):
        if self.original:
            try:
                self.original.flush()
            except Exception:
                pass
        if self.file:
            try:
                self.file.flush()
            except Exception:
                pass

sys.stdout = DualLogger(sys.stdout, LOG_FILE)
sys.stderr = DualLogger(sys.stderr, LOG_FILE)

from core.detector import run_detector

if __name__ == "__main__":
    print(f"\n========================================================")
    print(f" J.A.R.V.I.S. Background Listener Active (PID: {os.getpid()})")
    print(f"========================================================")
    try:
        run_detector()
    except Exception as e:
        print(f"[CRITICAL DETECTOR ERROR]: {e}")
        traceback.print_exc()
