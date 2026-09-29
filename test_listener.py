import sys
import traceback
from pathlib import Path

try:
    import sounddevice as sd
    print("Default device:", sd.default.device)
    print("Checking InputStream...")
    with sd.InputStream(samplerate=22050, blocksize=1024, channels=1, dtype='float32'):
        print("InputStream opened successfully!")
except Exception as e:
    print("Error opening stream:")
    traceback.print_exc()
