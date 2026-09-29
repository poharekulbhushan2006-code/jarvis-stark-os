"""
JARVIS Voice Synthesis Module
Powered by Microsoft Edge Neural Text-to-Speech (Edge-TTS)
"""

import os
import hashlib
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, List, Dict

import edge_tts

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_AUDIO_DIR = BASE_DIR / "cache" / "audio"
CACHE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_VOICE = os.getenv("JARVIS_VOICE", "en-GB-RyanNeural")
DEFAULT_RATE = os.getenv("JARVIS_SPEECH_RATE", "+0%")
DEFAULT_PITCH = os.getenv("JARVIS_PITCH", "+0Hz")

SUPPORTED_VOICES = [
    {"id": "en-GB-RyanNeural", "name": "J.A.R.V.I.S. (British Male - Paul Bettany Style - Recommended)", "accent": "British Male"},
    {"id": "en-GB-ThomasNeural", "name": "J.A.R.V.I.S. Classic (British Male - Thomas)", "accent": "British Male"},
    {"id": "en-GB-SoniaNeural", "name": "FRIDAY (British Female - Sonia)", "accent": "British Female"},
    {"id": "en-US-ChristopherNeural", "name": "Christopher (US Male - Tactical)", "accent": "American Male"},
    {"id": "en-GB-LibbyNeural", "name": "Libby (British Female - Polite)", "accent": "British Female"},
    {"id": "en-US-AriaNeural", "name": "Aria (US Female - Natural)", "accent": "American Female"},
]


class VoiceEngine:
    """Handles Edge Neural Voice generation, caching, and playback."""

    def __init__(self, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE, pitch: str = DEFAULT_PITCH):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch

    def _get_cache_path(self, text: str, voice: str, rate: str) -> Path:
        """Generates a deterministic cached filename for the text."""
        raw_key = f"{voice}_{rate}_{text.strip()}".encode("utf-8")
        hash_digest = hashlib.md5(raw_key).hexdigest()
        return CACHE_AUDIO_DIR / f"{hash_digest}.mp3"

    def _synthesize_sapi(self, text: str) -> Path:
        """Synthesizes text into a local WAV file using Windows native SAPI5 (100% offline)."""
        raw_key = f"sapi_jarvis_{text.strip()}".encode("utf-8")
        hash_digest = hashlib.md5(raw_key).hexdigest()
        wav_path = CACHE_AUDIO_DIR / f"{hash_digest}.wav"
        if wav_path.exists() and wav_path.stat().st_size > 0:
            return wav_path

        try:
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            # Select British male or David (male voice) for authentic J.A.R.V.I.S.
            for v in speaker.GetVoices():
                desc = v.GetDescription().lower()
                if any(m in desc for m in ["david", "george", "ryan", "richard", "male"]):
                    speaker.Voice = v
                    break
            file_stream = win32com.client.Dispatch("SAPI.SpFileStream")
            file_stream.Open(str(wav_path.resolve()), 3)  # 3 = SSFMCreateForWrite
            speaker.AudioOutputStream = file_stream
            speaker.Speak(text)
            file_stream.Close()
            return wav_path
        except Exception as e:
            print(f"[VoiceEngine] SAPI synthesis error: {e}")
            ps_script = f"""
            Add-Type -AssemblyName System.speech
            $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
            try {{ $speak.SelectVoice('Microsoft David Desktop') }} catch {{}}
            $speak.SetOutputToWaveFile('{wav_path.resolve()}')
            $speak.Speak('{text.replace("'", "''")}')
            $speak.Dispose()
            """
            subprocess.run(["powershell", "-c", ps_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return wav_path

    async def synthesize_async(self, text: str, voice: Optional[str] = None, rate: Optional[str] = None) -> Path:
        """Asynchronously synthesizes text into an audio file, utilizing disk cache and offline SAPI fallback."""
        v = voice or self.voice
        r = rate or self.rate
        cleaned_text = text.strip()

        if not cleaned_text:
            cleaned_text = "Yes, Boss."

        cache_path = self._get_cache_path(cleaned_text, v, r)
        if cache_path.exists() and cache_path.stat().st_size > 0:
            return cache_path

        # Primary: Microsoft Edge Neural TTS (Ultra realistic FRIDAY voice)
        try:
            communicate = edge_tts.Communicate(text=cleaned_text, voice=v, rate=r)
            await communicate.save(str(cache_path))
            return cache_path
        except Exception as e:
            print(f"[VoiceEngine] Edge-TTS offline or unavailable ({e}). Falling back to native Windows Zira SAPI5...")
            # Offline Fallback: Windows SAPI5 (Microsoft Zira Female)
            return self._synthesize_sapi(cleaned_text)

    def synthesize(self, text: str, voice: Optional[str] = None, rate: Optional[str] = None) -> Path:
        """Synchronous wrapper for speech synthesis."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If within an existing running loop (e.g. inside FastAPI)
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.synthesize_async(text, voice, rate)).result()
            else:
                return loop.run_until_complete(self.synthesize_async(text, voice, rate))
        except RuntimeError:
            return asyncio.run(self.synthesize_async(text, voice, rate))
        except Exception as e:
            print(f"[VoiceEngine] Synthesis error ({e}), invoking immediate SAPI offline fallback...")
            return self._synthesize_sapi(text)

    @staticmethod
    def play_audio_file(filepath: Path, non_blocking: bool = True):
        """Plays an audio file on Windows using winsound (WAV) or PowerShell MediaPlayer (MP3/WAV)."""
        filepath = Path(filepath)
        if filepath.suffix.lower() == ".wav":
            try:
                import winsound
                flags = winsound.SND_FILENAME
                if non_blocking:
                    flags |= winsound.SND_ASYNC
                winsound.PlaySound(str(filepath.resolve()), flags)
                return
            except Exception:
                pass

        ps_cmd = f"""
        Add-Type -AssemblyName presentationCore
        $player = New-Object System.Windows.Media.MediaPlayer
        $player.Open('{filepath.resolve()}')
        $player.Play()
        Start-Sleep -Milliseconds 300
        while ($player.NaturalDuration.HasTimeSpan -and $player.Position -lt $player.NaturalDuration.TimeSpan) {{
            Start-Sleep -Milliseconds 100
        }}
        $player.Close()
        """
        if non_blocking:
            subprocess.Popen(["powershell", "-c", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(["powershell", "-c", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @staticmethod
    def list_voices() -> List[Dict[str, str]]:
        """Returns the list of recommended Jarvis voices."""
        return SUPPORTED_VOICES


# Global singleton instance
voice_engine = VoiceEngine()
