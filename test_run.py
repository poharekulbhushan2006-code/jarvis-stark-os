import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
python_exe = BASE_DIR / ".venv" / "Scripts" / "python.exe"

print("Starting background_listener.py using subprocess.Popen...")
p = subprocess.Popen(
    [str(python_exe), "background_listener.py"],
    cwd=str(BASE_DIR),
    creationflags=0x08000000  # CREATE_NO_WINDOW
)
print("PID:", p.pid)
time.sleep(2)
poll = p.poll()
print("Process return code after 2s (None means still running!):", poll)
if poll is None:
    print("SUCCESS: background listener is actively running!")
    # Leave it running
else:
    print("Exited with code:", poll)
