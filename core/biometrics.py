"""
J.A.R.V.I.S. Voice Biometrics & Speaker Verification Engine
Extracts Mel-Frequency Cepstral Coefficients (MFCCs) and acoustic voice signatures
using pure NumPy to authenticate Boss's voice offline with zero external cloud dependencies.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Tuple, Optional, List

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

VOICEPRINT_PATH = CACHE_DIR / "boss_voiceprint.npy"
METADATA_PATH = CACHE_DIR / "boss_voiceprint.json"

# Audio Settings
SAMPLE_RATE = 22050
NUM_MEL_FILTERS = 26
NUM_CEPS = 16
SIMILARITY_THRESHOLD = float(os.getenv("VOICE_MATCH_THRESHOLD", "0.68"))


def hz_to_mel(hz: float) -> float:
    return 2595.0 * np.log10(1.0 + hz / 700.0)


def mel_to_hz(mel: float) -> float:
    return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)


def get_mel_filterbanks(num_filters: int, nfft: int, sample_rate: int) -> np.ndarray:
    """Builds triangular Mel filterbank matrix."""
    low_mel = hz_to_mel(0)
    high_mel = hz_to_mel(sample_rate / 2.0)
    mel_points = np.linspace(low_mel, high_mel, num_filters + 2)
    hz_points = mel_to_hz(mel_points)
    bin_points = np.floor((nfft + 1) * hz_points / sample_rate).astype(int)

    fbank = np.zeros((num_filters, int(np.floor(nfft / 2 + 1))))
    for m in range(1, num_filters + 1):
        f_m_minus = bin_points[m - 1]
        f_m = bin_points[m]
        f_m_plus = bin_points[m + 1]

        for k in range(f_m_minus, f_m):
            if f_m != f_m_minus:
                fbank[m - 1, k] = (k - bin_points[m - 1]) / (f_m - f_m_minus)
        for k in range(f_m, f_m_plus):
            if f_m_plus != f_m:
                fbank[m - 1, k] = (bin_points[m + 1] - k) / (f_m_plus - f_m)

    return fbank


def dct_matrix(num_ceps: int, num_filters: int) -> np.ndarray:
    """Computes Discrete Cosine Transform type-II matrix."""
    n = np.arange(num_filters)
    m = np.arange(num_ceps)[:, None]
    return np.cos(np.pi * m * (2 * n + 1) / (2 * num_filters))


def extract_mfcc_voiceprint(signal: np.ndarray, sample_rate: int = SAMPLE_RATE) -> Optional[np.ndarray]:
    """Extracts a normalized acoustic voiceprint vector from an audio signal.
    Returns a 32-dimensional feature vector (16 MFCC means + 16 MFCC standard deviations).
    """
    if signal is None or len(signal) == 0:
        return None

    # Flatten & convert to float32
    sig = signal.flatten().astype(np.float32)
    raw_peak = float(np.max(np.abs(sig)))
    if raw_peak < 0.005:
        # Signal is silence or below microphone noise floor
        return None

    sig = sig / raw_peak

    # Pre-emphasis filter
    sig_emphasized = np.append(sig[0], sig[1:] - 0.97 * sig[:-1])

    # Framing: 512 samples frame (~23.2ms), 256 samples hop (~11.6ms)
    frame_len = 512
    frame_step = 256
    sig_len = len(sig_emphasized)

    if sig_len < frame_len:
        return None

    num_frames = 1 + int(np.floor((sig_len - frame_len) / frame_step))
    indices = np.tile(np.arange(0, frame_len), (num_frames, 1)) + np.tile(
        np.arange(0, num_frames * frame_step, frame_step), (frame_len, 1)
    ).T

    frames = sig_emphasized[indices.astype(np.int32, copy=False)]

    # Hamming window
    window = np.hamming(frame_len)
    frames = frames * window

    # FFT & Power spectrum (nfft = 512 matching frame_len)
    nfft = 512
    mag_frames = np.abs(np.fft.rfft(frames, nfft))
    pow_frames = (1.0 / nfft) * (mag_frames ** 2)

    # Mel filterbanks
    fbanks = get_mel_filterbanks(NUM_MEL_FILTERS, nfft, sample_rate)
    filter_banks = np.dot(pow_frames, fbanks.T)
    filter_banks = np.where(filter_banks == 0, np.finfo(float).eps, filter_banks)
    log_fbanks = np.log(filter_banks)

    # DCT to obtain MFCCs
    dct_m = dct_matrix(NUM_CEPS, NUM_MEL_FILTERS)
    mfcc = np.dot(log_fbanks, dct_m.T)

    # Voice signature vector: Mean + Std of MFCC coefficients over time
    mfcc_mean = np.mean(mfcc, axis=0)
    mfcc_std = np.std(mfcc, axis=0)
    voice_vector = np.concatenate([mfcc_mean, mfcc_std])

    # L2 normalize
    norm = np.linalg.norm(voice_vector)
    if norm > 0:
        voice_vector = voice_vector / norm

    return voice_vector


def audio_bytes_to_numpy(audio_bytes: bytes) -> Optional[np.ndarray]:
    """Converts WAV, WebM, or PCM audio bytes into a normalized float32 NumPy array."""
    if not audio_bytes:
        return None

    import io
    import wave

    try:
        with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
            nchannels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())

            if sampwidth == 2:
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            elif sampwidth == 4:
                audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
            elif sampwidth == 1:
                audio = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
            else:
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

            if nchannels > 1:
                audio = audio.reshape(-1, nchannels).mean(axis=1)

            if framerate != SAMPLE_RATE and len(audio) > 0:
                step = framerate / SAMPLE_RATE
                indices = np.round(np.arange(0, len(audio), step)).astype(int)
                indices = indices[indices < len(audio)]
                audio = audio[indices]

            return audio
    except Exception:
        pass

    # Fallback: raw 16-bit PCM
    try:
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if len(audio) > 100:
            return audio
    except Exception:
        pass

    return None


class VoiceBiometrics:
    """Manages speaker enrollment, storage, and live speaker verification."""

    def __init__(self, voiceprint_file: Path = VOICEPRINT_PATH):
        self.voiceprint_file = voiceprint_file
        self.boss_voiceprint: Optional[np.ndarray] = None
        self.load_voiceprint()

    def reset(self) -> bool:
        """Removes registered voiceprint to allow clean re-enrollment."""
        self.boss_voiceprint = None
        if self.voiceprint_file.exists():
            try:
                self.voiceprint_file.unlink()
            except Exception:
                pass
        if METADATA_PATH.exists():
            try:
                METADATA_PATH.unlink()
            except Exception:
                pass
        return True

    def is_enrolled(self) -> bool:
        """Returns True if Boss has registered their voice."""
        return self.boss_voiceprint is not None

    def get_metadata(self) -> dict:
        """Returns voiceprint metadata dictionary if available."""
        if METADATA_PATH.exists():
            try:
                return json.loads(METADATA_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def load_voiceprint(self) -> bool:
        """Loads the registered voiceprint from disk."""
        if self.voiceprint_file.exists():
            try:
                self.boss_voiceprint = np.load(str(self.voiceprint_file))
                return True
            except Exception as e:
                print(f"[Biometrics] Error loading voiceprint: {e}")
                self.boss_voiceprint = None
        return False

    def enroll(self, audio_samples: List[np.ndarray], user_name: str = "Boss") -> bool:
        """Enrolls Boss by averaging voice vectors from calibration samples."""
        vectors = []
        for sample in audio_samples:
            vec = extract_mfcc_voiceprint(sample)
            if vec is not None:
                vectors.append(vec)

        if not vectors:
            print("[Biometrics] Enrollment failed: No valid acoustic voice vectors could be extracted.")
            return False

        # Average acoustic vectors
        avg_vec = np.mean(vectors, axis=0)
        norm = np.linalg.norm(avg_vec)
        if norm > 0:
            avg_vec = avg_vec / norm

        self.boss_voiceprint = avg_vec
        np.save(str(self.voiceprint_file), self.boss_voiceprint)

        # Save metadata
        metadata = {
            "user_name": user_name,
            "enrolled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "samples_count": len(vectors),
            "vector_dimension": len(self.boss_voiceprint)
        }
        METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(f"[Biometrics] Voiceprint successfully enrolled for {user_name}! Saved to {self.voiceprint_file.name}")
        return True

    def verify(self, audio_sample: np.ndarray, threshold: float = SIMILARITY_THRESHOLD) -> Tuple[bool, float]:
        """Compares an incoming audio sample against Boss's voiceprint.
        Returns (is_authenticated, similarity_score).
        If no voiceprint has been enrolled yet, permits all audio (bootstrap mode).
        """
        if self.boss_voiceprint is None:
            # Not enrolled yet -> Allow by default until enrollment
            return True, 1.0

        sample_vec = extract_mfcc_voiceprint(audio_sample)
        if sample_vec is None:
            # Ambient noise / silence -> Cannot authenticate
            return False, 0.0

        # Cosine similarity
        similarity = float(np.dot(self.boss_voiceprint, sample_vec))
        is_authenticated = similarity >= threshold

        return is_authenticated, similarity


# Global Singleton
voice_biometrics = VoiceBiometrics()
