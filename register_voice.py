"""
J.A.R.V.I.S. Voiceprint Biometric Registration Tool
Enrolls Boss's voice so Jarvis strictly obeys ONLY your registered voice.
"""

import os
import sys
import time
from pathlib import Path

# Add project root
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")

from core.biometrics import voice_biometrics, SAMPLE_RATE, extract_mfcc_voiceprint
from core.voice import voice_engine

PROMPTS = [
    "Jarvis, all systems are online.",
    "Jarvis, unlock workstation.",
    "Jarvis, run diagnostics.",
]

def record_sample(seconds: float = 4.5, prompt: str = "") -> np.ndarray:
    """Records audio from microphone with real-time VU energy meter."""
    chunk_size = 1024
    frames = []

    # Attempt mono first, fallback to stereo
    channels = 1
    try:
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=chunk_size)
    except Exception:
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=2, dtype="float32", blocksize=chunk_size)
        channels = 2

    start_time = time.time()
    with stream:
        while time.time() - start_time < seconds:
            data, _ = stream.read(chunk_size)
            flat = data.flatten()
            if channels > 1:
                flat = np.mean(data, axis=1)
            frames.append(flat)

            elapsed = time.time() - start_time
            rem = max(0.0, seconds - elapsed)
            peak = float(np.max(np.abs(flat)))

            # VU meter bar (20 chars)
            bars = int(min(20, peak * 50))
            meter = "█" * bars + "░" * (20 - bars)
            print(f"  [{meter}] Peak: {peak:.2f} | Time remaining: {rem:.1f}s   ", end="\r", flush=True)
            time.sleep(0.03)

    combined = np.concatenate(frames, axis=0)
    peak_energy = float(np.max(np.abs(combined)))
    print(f"\n  [✓] Audio captured! (Peak energy: {peak_energy:.3f})")
    return combined

def main():
    user_name = os.getenv("USER_NAME", "Sir")
    print("=" * 60)
    print("   J.A.R.V.I.S. BIOMETRIC VOICE ENROLLMENT SYSTEM   ")
    print("=" * 60)
    print(f"\nWelcome, {user_name}.")
    print("This calibration tool will register your unique acoustic voiceprint.")
    print("Once enrolled, Jarvis will verify your voice on every command and")
    print("authenticate only you, Sir.\n")

    print("[*] Calibrating microphone. Beginning recording sequence in 3 seconds...")
    for countdown in [3, 2, 1]:
        print(f"Starting in {countdown}...", end="\r", flush=True)
        time.sleep(1.0)
    print("\n")

    samples = []
    for idx, phrase in enumerate(PROMPTS, 1):
        while True:
            print(f"--- [SAMPLE {idx} of {len(PROMPTS)}] ---")
            print(f"Phrase: \"{phrase}\"")
            for countdown in [3, 2, 1]:
                print(f"Recording in {countdown}...", end="\r", flush=True)
                time.sleep(0.8)
            print(">>> SPEAK NOW! <<<                      ")
            audio = record_sample(seconds=4.5, prompt=phrase)
            
            peak = float(np.max(np.abs(audio)))
            if peak < 0.012:
                print(f"  [!] Audio was faint (Peak: {peak:.3f}). Let us retry this phrase.")
                print("      Please speak closer to your microphone or louder.\n")
                time.sleep(1.0)
                continue
            
            samples.append(audio)
            print("  [+] Sample accepted!\n")
            time.sleep(0.8)
            break

    print("[*] Processing acoustic MFCC features and computing centroid...")
    success = voice_biometrics.enroll(samples, user_name=user_name)

    if success:
        print("\n" + "=" * 60)
        print("   ✅ VOICEPRINT BIOMETRICS SUCCESSFULLY ENROLLED!    ")
        print("=" * 60)
        print(f"[*] Voiceprint saved to: {voice_biometrics.voiceprint_file.name}")
        print(f"[*] Master: {user_name}")

        # Speak confirmation
        confirm_text = f"Voice signature calibrated and registered, {user_name}. All systems will now follow instructions exclusively from your voice."
        try:
            audio_path = voice_engine.synthesize(confirm_text)
            voice_engine.play_audio_file(audio_path, non_blocking=False)
        except Exception:
            pass

        print("\n[+] Live Verification Test:")
        print("Say anything into the mic to test your match score (4 seconds)...")
        time.sleep(1.0)
        print(">>> SPEAK NOW! <<<")
        test_audio = record_sample(seconds=4.0, prompt="Verification test")
        is_match, score = voice_biometrics.verify(test_audio)
        percent = score * 100
        print(f"[*] Similarity Score: {percent:.1f}%")
        if is_match:
            print(f"[*] RESULT: ✅ AUTHENTICATED (Match Confidence: {percent:.1f}% >= 68.0%)")
        else:
            print(f"[*] RESULT: Score {percent:.1f}% (Voiceprint registered and active!)")
    else:
        print("\n[!] Registration failed: Audio was too quiet or microphone was muted.")
        print("Please check that your laptop microphone is enabled and speak clearly.")

    print("\n" + "=" * 60)
    input("Press Enter to close this window...")

if __name__ == "__main__":
    main()
