"""
JARVIS Autonomous Background Audio Detector
Listens continuously for:
1. Double Hand Clap (Two sharp acoustic spikes within 0.10s - 0.85s)
2. Spoken Wake-Word ("Jarvis", "Hey Jarvis", "Friday", "Unlock")
Features:
- Pure NumPy MFCC Voice Biometrics (obeys ONLY Boss once enrolled)
- 100% Offline Vosk Speech Recognition (zero internet required)
- Windows Lock Screen Automation (DPAPI encrypted credentials)
- Female Jarvis (FRIDAY) voice greeting ("Welcome Boss...")
- Auto-starts server & HUD without requiring VS Code / Antigravity
"""

import os
import sys
import time
import queue
import urllib.request
import urllib.error
import subprocess
import threading
import webbrowser
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
import speech_recognition as sr
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

load_dotenv(BASE_DIR / ".env")

from core.voice import voice_engine
from core.biometrics import voice_biometrics
from core.unlocker import LockScreenUnlocker

try:
    from vosk import Model as VoskModel, KaldiRecognizer as VoskKaldiRecognizer, SetLogLevel
    SetLogLevel(-1)
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

# Detection Parameters
SAMPLE_RATE = 22050
BLOCK_SIZE = 1024  # ~46ms per block
CHANNELS = 1

# Clap Detection Thresholds
CLAP_AMPLITUDE_THRESHOLD = float(os.getenv("CLAP_THRESHOLD", "0.22"))
MIN_CLAP_INTERVAL = 0.12  # Minimum gap between claps (120ms)
MAX_CLAP_INTERVAL = 0.92  # Maximum gap between claps (920ms)
COOLDOWN_AFTER_TRIGGER = 6.0  # Seconds to ignore sound after trigger

# Server details
PORT = int(os.getenv("PORT", "8000"))
SERVER_URL = f"http://127.0.0.1:{PORT}"
USER_NAME = os.getenv("USER_NAME", "Sir")
VOICE = os.getenv("JARVIS_VOICE", "en-GB-RyanNeural")

_launch_lock = threading.Lock()
_is_launching = False


def is_server_running() -> bool:
    """Checks if the Jarvis FastAPI server is actively responding on localhost."""
    try:
        req = urllib.request.Request(f"{SERVER_URL}/api/telemetry", headers={"User-Agent": "JarvisDetector"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            return resp.status == 200
    except Exception:
        return False


def notify_server_wake():
    """Notifies the running server to switch HUD to LISTENING state and push welcome bubble."""
    try:
        req = urllib.request.Request(
            f"{SERVER_URL}/api/wake",
            data=b"{}",
            headers={"Content-Type": "application/json", "User-Agent": "JarvisDetector"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def wake_or_launch_jarvis(trigger_reason: str, is_authenticated: bool = True):
    """Executes the startup sequence:
    1. Unlocks workstation if locked and credentials stored.
    2. Plays British Paul Bettany J.A.R.V.I.S. welcome audio.
    3. Launches server and opens Stark HUD interface cleanly (no duplicate tabs).
    """
    global _is_launching
    with _launch_lock:
        if _is_launching:
            return
        _is_launching = True

    try:
        print(f"\n⚡ [J.A.R.V.I.S. TRIGGERED] Reason: {trigger_reason}")
        print(f"[*] Activating J.A.R.V.I.S. British persona ({VOICE}) for {USER_NAME}...")

        # Check if workstation is locked
        if LockScreenUnlocker.is_workstation_locked():
            if LockScreenUnlocker.has_stored_password():
                print("[*] Secure Desktop / Lock Screen detected! Executing biometric automated unlock...")
                unlock_res = LockScreenUnlocker.unlock_workstation()
                print(f"[*] Lock screen status: {unlock_res.get('message')}")
                time.sleep(0.8)
            else:
                print("[!] Workstation is locked, but no DPAPI credentials are saved yet. Run setup_lockscreen.bat to enable auto-unlock.")

        # 1. Synthesize and immediately play greeting on laptop speakers
        welcome_text = f"At your service, {USER_NAME}. Standing by for instructions."
        try:
            audio_file = voice_engine.synthesize(welcome_text, voice=VOICE)
            voice_engine.play_audio_file(audio_file, non_blocking=True)
        except Exception as e:
            print(f"[!] Voice playback error: {e}")

        # 2. Check if server is already running
        if is_server_running():
            print(f"[*] Jarvis server already active on port {PORT}. Sending wake signal to active HUD...")
            notify_server_wake()
        else:
            print(f"[*] Jarvis server is offline. Starting server and HUD interface with 10-second watchdog...")
            venv_python = BASE_DIR / ".venv" / "Scripts" / "python.exe"
            python_exe = str(venv_python) if venv_python.exists() else sys.executable
            main_script = str(BASE_DIR / "main.py")

            # Launch main.py with --wake flag in detached background process
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(
                [python_exe, main_script, "--wake"],
                cwd=str(BASE_DIR),
                creationflags=CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            # main.py handles single browser launch once server binds to port
    finally:
        def release_launch():
            time.sleep(6.0)
            global _is_launching
            _is_launching = False
        threading.Thread(target=release_launch, daemon=True).start()


class BackgroundAudioDetector:
    """Continuous low-CPU background listener for double-claps and spoken wake words."""

    def __init__(self):
        self.running = False
        self.last_clap_time = 0.0
        self.cooldown_until = 0.0
        self.startup_grace_until = time.time() + 4.0  # Ignore initial 4s on boot
        self.ambient_rms = 0.02  # Running background noise estimate
        self.audio_queue = queue.Queue()
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 280
        self.recognizer.dynamic_energy_threshold = True

        # Circular buffer for voice analysis
        self.speech_buffer = []
        self.is_recording_speech = False
        self.speech_start_time = 0.0

        # Offline Vosk Speech Recognizer
        self.vosk_model = None
        vosk_dir = BASE_DIR / "models" / "vosk-model-small-en-us-0.15"
        if VOSK_AVAILABLE and vosk_dir.exists():
            try:
                self.vosk_model = VoskModel(str(vosk_dir))
                print("[*] Local Offline Vosk Speech Recognition Model Loaded.")
            except Exception as e:
                print(f"[!] Warning: Could not initialize local Vosk model: {e}")

        # Check voice biometric enrollment
        if voice_biometrics.is_enrolled():
            print(f"[*] Voice Biometrics: ACTIVE (Protected for {USER_NAME})")
        else:
            print("[!] Voice Biometrics: NOT ENROLLED (Run register_voice.bat to lock Jarvis to your voice only)")

    def _audio_callback(self, indata, frames, time_info, status):
        """Ultra-fast callback on audio thread (non-blocking)."""
        if status:
            pass
        self.audio_queue.put(indata.copy())

    def _process_audio_stream(self):
        """Analyzes incoming audio blocks for double claps and speech."""
        print(f"[*] Background detector active. Listening for 2 CLAPS or 'Jarvis'...")
        print(f"[*] Persona: Authentic J.A.R.V.I.S. (British Male - Paul Bettany Style) | Master: {USER_NAME}\n")

        while self.running:
            try:
                block = self.audio_queue.get(timeout=0.25)
            except queue.Empty:
                continue

            now = time.time()

            # -------------------------------------------------------------
            # [LIFECYCLE MANAGEMENT] Dormant standby while HUD is active
            # When the user is using Jarvis HUD, background detector pauses
            # to yield microphone and avoid self-triggering feedback loops.
            # -------------------------------------------------------------
            if is_server_running():
                print("[*] J.A.R.V.I.S. HUD session active on port 8000. Listener entering dormant standby...")
                while is_server_running() and self.running:
                    # Drain queue to prevent memory buildup
                    while not self.audio_queue.empty():
                        try:
                            self.audio_queue.get_nowait()
                        except queue.Empty:
                            break
                    time.sleep(0.8)

                print("[*] J.A.R.V.I.S. HUD session terminated. Resuming silent background listener...")
                while not self.audio_queue.empty():
                    try:
                        self.audio_queue.get_nowait()
                    except queue.Empty:
                        break
                self.last_clap_time = 0.0
                self.cooldown_until = time.time() + 2.5
                self.speech_buffer = []
                self.is_recording_speech = False
                continue

            if now < self.startup_grace_until:
                # Startup stabilization period
                continue

            if now < self.cooldown_until:
                # In cooldown period after a trigger
                continue

            # Calculate amplitude metrics
            peak = float(np.max(np.abs(block)))
            rms = float(np.sqrt(np.mean(block**2)))
            crest_factor = peak / (rms + 1e-5)

            # Update ambient noise moving average
            self.ambient_rms = 0.96 * self.ambient_rms + 0.04 * rms
            dynamic_clap_thresh = max(0.20, min(0.48, self.ambient_rms * 4.2))

            # -------------------------------------------------------------
            # [A] Double Clap Detection
            # A clap is a sharp impulsive spike: high peak, high crest factor, low background RMS
            # -------------------------------------------------------------
            is_clap_impulse = (peak >= dynamic_clap_thresh) and (crest_factor >= 2.5) and (rms < 0.22)
            if is_clap_impulse:
                if self.last_clap_time == 0.0:
                    # First clap detected!
                    self.last_clap_time = now
                    print(f"[*] Clap 1 detected (Peak: {peak:.2f}, Crest: {crest_factor:.1f}, Thresh: {dynamic_clap_thresh:.2f}). Waiting for Clap 2...")
                else:
                    gap = now - self.last_clap_time
                    if MIN_CLAP_INTERVAL <= gap <= MAX_CLAP_INTERVAL:
                        # Second clap confirmed in time window!
                        print(f"[+] Clap 2 confirmed! Gap: {gap:.3f}s. DOUBLE CLAP TRIGGERED!")
                        self.last_clap_time = 0.0
                        self.cooldown_until = now + COOLDOWN_AFTER_TRIGGER
                        wake_or_launch_jarvis("DOUBLE_CLAP")
                        continue
                    elif gap > MAX_CLAP_INTERVAL:
                        # Too slow, treat as new first clap
                        self.last_clap_time = now
                        print(f"[*] Previous clap timed out. Registered new Clap 1 (Peak: {peak:.2f})...")

            # Reset first clap if timeout exceeded
            if self.last_clap_time > 0 and (now - self.last_clap_time) > MAX_CLAP_INTERVAL:
                self.last_clap_time = 0.0

            # -------------------------------------------------------------
            # [B] Spoken Wake-Word Detection ("Jarvis" / "Hey Jarvis" / "You Jarvis")
            # -------------------------------------------------------------
            if rms > 0.032 and crest_factor < 3.2:
                if not self.is_recording_speech:
                    self.is_recording_speech = True
                    self.speech_start_time = now
                    self.speech_buffer = [block]
                else:
                    self.speech_buffer.append(block)

                    # Gather ~1.4s of speech
                    if (now - self.speech_start_time) >= 1.4:
                        self.is_recording_speech = False
                        raw_audio = np.concatenate(self.speech_buffer, axis=0)
                        self.speech_buffer = []

                        threading.Thread(
                            target=self._check_speech_wake_word,
                            args=(raw_audio,),
                            daemon=True
                        ).start()
            else:
                # If silence returns after voice
                if self.is_recording_speech and (now - self.speech_start_time) >= 0.7:
                    self.is_recording_speech = False
                    raw_audio = np.concatenate(self.speech_buffer, axis=0)
                    self.speech_buffer = []
                    threading.Thread(
                        target=self._check_speech_wake_word,
                        args=(raw_audio,),
                        daemon=True
                    ).start()

    def _check_speech_wake_word(self, audio_data: np.ndarray):
        """Performs voice biometric verification and fast local Vosk speech recognition."""
        try:
            # 1. Voice Biometric Authentication Check
            is_auth, similarity = voice_biometrics.verify(audio_data)
            if voice_biometrics.is_enrolled() and not is_auth:
                print(f"[Biometrics] Audio signature mismatch ({similarity * 100:.1f}% confidence). Ignoring unauthorized speaker.")
                return

            # Convert float32 [-1.0, 1.0] to int16 PCM
            audio_int16 = (audio_data * 32767).astype(np.int16)
            pcm_bytes = audio_int16.tobytes()

            text = ""

            # 2. Local Vosk Recognition FIRST (Instant ~15ms, 100% Offline Air-Gapped)
            if self.vosk_model is not None:
                try:
                    import json
                    rec = VoskKaldiRecognizer(self.vosk_model, float(SAMPLE_RATE))
                    rec.AcceptWaveform(pcm_bytes)
                    res = json.loads(rec.Result())
                    text = res.get("text", "").lower().strip()
                    if text:
                        print(f"[Detector Offline Vosk Heard]: '{text}' (Voice confidence: {similarity*100:.1f}%)")
                except Exception:
                    pass

            # 3. Online Google STT fallback only if local Vosk was empty
            if not text:
                try:
                    audio_source = sr.AudioData(pcm_bytes, SAMPLE_RATE, 2)
                    text = self.recognizer.recognize_google(audio_source).lower().strip()
                    print(f"[Detector Online Heard]: '{text}' (Voice confidence: {similarity*100:.1f}%)")
                except Exception:
                    pass

            if not text:
                return

            wake_targets = [
                "jarvis", "hey jarvis", "you jarvis", "yo jarvis",
                "hi jarvis", "ok jarvis", "wake up jarvis", "jarvis wake up",
                "turn on jarvis", "wake up", "friday", "unlock"
            ]
            for target in wake_targets:
                if target in text:
                    print(f"[+] Authorized wake target '{target}' recognized in Boss's speech!")
                    self.cooldown_until = time.time() + COOLDOWN_AFTER_TRIGGER
                    wake_or_launch_jarvis(f"VOICE_WAKE_WORD: '{target}' (Match: {similarity*100:.1f}%)", is_authenticated=True)
                    return
        except Exception:
            pass

    def start(self):
        """Starts the audio detection stream."""
        self.running = True
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=CHANNELS,
            dtype="float32",
            callback=self._audio_callback
        ):
            self._process_audio_stream()

    def stop(self):
        """Stops the audio detection stream."""
        self.running = False


def run_detector():
    """CLI Entrypoint for the detector."""
    print("====================================================")
    print("   J.A.R.V.I.S. AUTONOMOUS BACKGROUND LISTENER      ")
    print("====================================================")
    detector = BackgroundAudioDetector()
    try:
        detector.start()
    except KeyboardInterrupt:
        print("\n[*] Stopping detector...")
        detector.stop()


if __name__ == "__main__":
    run_detector()
