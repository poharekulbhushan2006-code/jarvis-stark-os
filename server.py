"""
JARVIS Web HUD Server
FastAPI Server providing real-time WebSockets, REST APIs,
audio streaming, and Stark HUD static assets.
"""

import os
import sys
import time
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np

from core.system_control import SystemController, SCREENSHOTS_DIR, NOTES_DIR
from core.voice import voice_engine, CACHE_AUDIO_DIR, SUPPORTED_VOICES
from core.brain import jarvis_brain
from core.biometrics import voice_biometrics, audio_bytes_to_numpy, extract_mfcc_voiceprint
from core.guardrails import guardrails

# Base directory
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

app = FastAPI(title="J.A.R.V.I.S. Core Interface", version="2.0.0")

# Enable CORS for local cross-origin development if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directories
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")


# -------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------
class CommandRequest(BaseModel):
    query: str

class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    rate: Optional[str] = None

class SettingsRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    user_name: Optional[str] = None
    voice: Optional[str] = None
    lockscreen_password: Optional[str] = None


# -------------------------------------------------------------
# REST Endpoints
# -------------------------------------------------------------
@app.get("/")
async def root():
    """Serves the main holographic HUD interface."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"status": "JARVIS online", "message": "HUD interface initializing..."})

@app.get("/api/telemetry")
async def get_telemetry():
    """Returns a full real-time snapshot of laptop hardware and power stats."""
    return SystemController.get_system_telemetry()

@app.post("/api/command")
async def execute_command(req: CommandRequest):
    """Processes a natural language command and returns Jarvis response with audio."""
    _disarm_watchdog()
    await manager.broadcast({"type": "WATCHDOG_DISARM"})
    result = await jarvis_brain.process_command(req.query)

    if result.get("action") == "SYSTEM_STANDBY":
        async def delayed_exit():
            await asyncio.sleep(2.5)
            _close_browser_tab()
            await asyncio.sleep(0.3)
            os._exit(0)
        asyncio.create_task(delayed_exit())

    return result

@app.get("/api/welcome")
async def get_welcome():
    """Returns the introductory welcome greeting for the user."""
    user_name = jarvis_brain.user_name or "Sir"
    text = f"Welcome back, {user_name}. All systems are online and operational. How may I be of assistance?"
    filepath = await voice_engine.synthesize_async(text)
    return {
        "text": text,
        "audio_url": f"/api/audio/{filepath.name}",
        "user_name": user_name
    }

@app.post("/api/voice-command")
async def handle_voice_upload(request: Request):
    """Receives recorded audio from browser, validates voice biometrics, and executes transcribed command."""
    _disarm_watchdog()
    await manager.broadcast({"type": "WATCHDOG_DISARM"})
    data = b""
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        f = form.get("audio_file")
        if f:
            data = await f.read()
    elif "application/json" in content_type:
        payload = await request.json()
        import base64
        data = base64.b64decode(payload.get("audio_base64", ""))
    else:
        data = await request.body()

    if not data:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    # Biometric Speaker Verification (if enrolled)
    if voice_biometrics.is_enrolled():
        arr = audio_bytes_to_numpy(data)
        if arr is not None and len(arr) > 0:
            is_auth, score = voice_biometrics.verify(arr)
            if not is_auth:
                user_name = jarvis_brain.user_name or "Sir"
                denied_msg = f"Acoustic signature verification failed ({score * 100:.1f}% confidence). You are not recognized as {user_name}."
                speech_path = await voice_engine.synthesize_async(denied_msg)
                return {
                    "text": denied_msg,
                    "action": "ACCESS_DENIED",
                    "audio_url": f"/api/audio/{speech_path.name}"
                }

    temp_path = CACHE_AUDIO_DIR / f"mic_{int(time.time() * 1000)}.wav"
    temp_path.write_bytes(data)

    query = ""
    # 1. Try SpeechRecognition
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.AudioFile(str(temp_path)) as source:
            recorded = r.record(source)
            query = r.recognize_google(recorded).strip()
    except Exception:
        pass

    # Clean temp file
    try:
        temp_path.unlink()
    except Exception:
        pass

    if not query:
        fallback_msg = f"I was unable to discern your vocal command, {jarvis_brain.user_name}. Please try again."
        speech_path = await voice_engine.synthesize_async(fallback_msg)
        return {
            "text": fallback_msg,
            "action": "TRANSCRIBE_RETRY",
            "audio_url": f"/api/audio/{speech_path.name}"
        }

    # Process query
    result = await jarvis_brain.process_command(query)
    result["transcribed_query"] = query

    if result.get("action") == "SYSTEM_STANDBY":
        async def delayed_exit():
            await asyncio.sleep(2.5)
            os._exit(0)
        asyncio.create_task(delayed_exit())

    return result

@app.post("/api/speak")
async def speak_text(req: SpeakRequest):
    """Synthesizes text to speech and returns the audio URL."""
    filepath = await voice_engine.synthesize_async(req.text, req.voice, req.rate)
    return {"success": True, "audio_url": f"/api/audio/{filepath.name}"}

@app.get("/api/audio/{filename}")
async def get_audio_file(filename: str):
    """Streams the synthesized MP3 or WAV audio file."""
    file_path = CACHE_AUDIO_DIR / filename
    if file_path.exists():
        media_type = "audio/wav" if filename.lower().endswith(".wav") else "audio/mpeg"
        return FileResponse(str(file_path), media_type=media_type)
    raise HTTPException(status_code=404, detail="Audio file not found")

@app.get("/api/voices")
async def list_voices():
    """Returns supported Jarvis voices."""
    return {"voices": SUPPORTED_VOICES, "active_voice": voice_engine.voice}

@app.get("/api/settings")
async def get_settings():
    """Returns current user settings (masking the API key)."""
    key = jarvis_brain.api_key
    masked_key = (key[:4] + "..." + key[-4:]) if len(key) > 8 else ("Configured" if key else "Not Configured")
    from core.unlocker import LockScreenUnlocker
    from core.biometrics import voice_biometrics
    return {
        "gemini_configured": bool(key),
        "gemini_api_key_masked": masked_key,
        "user_name": jarvis_brain.user_name,
        "voice": voice_engine.voice,
        "password_configured": LockScreenUnlocker.has_stored_password(),
        "voice_enrolled": voice_biometrics.is_enrolled()
    }

@app.post("/api/settings")
async def update_settings(req: SettingsRequest):
    """Updates settings and persists them to .env and DPAPI vault."""
    env_path = BASE_DIR / ".env"
    env_content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""

    if req.gemini_api_key is not None:
        jarvis_brain.update_api_key(req.gemini_api_key)
        # Update or add in .env
        if "GEMINI_API_KEY=" in env_content:
            import re
            env_content = re.sub(r'GEMINI_API_KEY=.*', f'GEMINI_API_KEY={req.gemini_api_key}', env_content)
        else:
            env_content += f"\nGEMINI_API_KEY={req.gemini_api_key}\n"

    if req.user_name is not None and req.user_name.strip():
        jarvis_brain.user_name = req.user_name.strip()
        if "USER_NAME=" in env_content:
            import re
            env_content = re.sub(r'USER_NAME=.*', f'USER_NAME={jarvis_brain.user_name}', env_content)
        else:
            env_content += f"\nUSER_NAME={jarvis_brain.user_name}\n"

    if req.voice is not None and req.voice.strip():
        voice_engine.voice = req.voice.strip()
        if "JARVIS_VOICE=" in env_content:
            import re
            env_content = re.sub(r'JARVIS_VOICE=.*', f'JARVIS_VOICE={voice_engine.voice}', env_content)
        else:
            env_content += f"\nJARVIS_VOICE={voice_engine.voice}\n"

    if req.lockscreen_password is not None and req.lockscreen_password.strip():
        from core.unlocker import LockScreenUnlocker
        LockScreenUnlocker.save_password(req.lockscreen_password.strip())

    env_path.write_text(env_content, encoding="utf-8")
    return {"success": True, "message": f"Settings updated successfully, {jarvis_brain.user_name}."}

# In-flight voice enrollment calibration samples
_biometric_samples: Dict[int, np.ndarray] = {}

@app.get("/api/biometrics/status")
async def get_biometrics_status():
    """Returns biometric enrollment status and metadata."""
    enrolled = voice_biometrics.is_enrolled()
    meta = voice_biometrics.get_metadata()
    return {
        "enrolled": enrolled,
        "user_name": jarvis_brain.user_name,
        "metadata": meta,
        "samples_collected": len(_biometric_samples)
    }

@app.post("/api/biometrics/reset")
async def reset_biometrics():
    """Wipes enrolled voiceprint for re-calibration."""
    global _biometric_samples
    _biometric_samples = {}
    voice_biometrics.reset()
    return {"success": True, "message": "Voiceprint profile cleared. Ready for fresh enrollment."}

@app.post("/api/biometrics/enroll-sample")
async def enroll_sample(request: Request):
    """Receives one phrase calibration audio sample from the browser (supports multipart, JSON base64, or raw WAV)."""
    global _biometric_samples
    sample_index = 1
    audio_bytes = b""

    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        sample_index = int(form.get("sample_index", 1))
        file_obj = form.get("audio_file")
        if file_obj:
            audio_bytes = await file_obj.read()
    elif "application/json" in content_type:
        payload = await request.json()
        sample_index = int(payload.get("sample_index", 1))
        import base64
        audio_bytes = base64.b64decode(payload.get("audio_base64", ""))
    else:
        sample_index = int(request.query_params.get("sample_index", 1))
        audio_bytes = await request.body()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload received")

    audio_np = audio_bytes_to_numpy(audio_bytes)
    if audio_np is None or len(audio_np) == 0:
        return {"success": False, "error": "Unable to decode audio format. Please retry."}

    peak = float(np.max(np.abs(audio_np)))
    if peak < 0.012:
        return {
            "success": False,
            "error": f"Audio was faint (Peak: {peak:.3f} < 0.012). Please speak closer to your microphone or louder.",
            "peak": peak
        }

    vec = extract_mfcc_voiceprint(audio_np)
    if vec is None:
        return {"success": False, "error": "Could not extract MFCC voice vectors. Please speak more clearly."}

    _biometric_samples[sample_index] = audio_np
    return {
        "success": True,
        "sample_index": sample_index,
        "peak": round(peak, 3),
        "samples_collected": len(_biometric_samples),
        "message": f"Sample {sample_index} validated and stored."
    }

@app.post("/api/biometrics/finalize")
async def finalize_biometrics():
    """Computes centroid MFCC voiceprint from collected samples and saves to vault."""
    global _biometric_samples
    if not _biometric_samples:
        raise HTTPException(status_code=400, detail="No calibration samples recorded.")

    samples_list = [v for k, v in sorted(_biometric_samples.items())]
    user_name = jarvis_brain.user_name or "Sir"
    success = voice_biometrics.enroll(samples_list, user_name=user_name)
    _biometric_samples = {}

    if not success:
        return {"success": False, "error": "Calibration computation failed. Please retry recording."}

    confirm_text = f"Voice signature calibrated and registered, {user_name}. All systems will now follow instructions exclusively from your voice."
    filepath = await voice_engine.synthesize_async(confirm_text)

    return {
        "success": True,
        "message": confirm_text,
        "audio_url": f"/api/audio/{filepath.name}",
        "user_name": user_name
    }

@app.post("/api/biometrics/test")
async def test_biometrics(request: Request):
    """Tests an audio sample against the enrolled voiceprint."""
    audio_bytes = b""
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        file_obj = form.get("audio_file")
        if file_obj:
            audio_bytes = await file_obj.read()
    elif "application/json" in content_type:
        payload = await request.json()
        import base64
        audio_bytes = base64.b64decode(payload.get("audio_base64", ""))
    else:
        audio_bytes = await request.body()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload received")

    audio_np = audio_bytes_to_numpy(audio_bytes)
    if audio_np is None or len(audio_np) == 0:
        return {"is_authenticated": False, "similarity": 0.0, "error": "Unable to decode audio."}

    is_authenticated, similarity = voice_biometrics.verify(audio_np)
    return {
        "is_authenticated": is_authenticated,
        "similarity": round(similarity * 100, 1),
        "threshold": 68.0
    }

@app.post("/api/biometrics/launch-calibration")
async def launch_calibration():
    """Spawns an interactive voice registration window for Boss."""
    import subprocess
    cmd = str(BASE_DIR / "register_voice.bat")
    subprocess.Popen(f'start "J.A.R.V.I.S. Voice Registration" "{cmd}"', shell=True, cwd=str(BASE_DIR))
    return {"success": True, "message": "Voice calibration terminal launched on desktop"}

@app.get("/api/notes")
async def get_notes():
    """Lists recent notes."""
    return SystemController.list_notes()

@app.get("/api/screenshots")
async def list_screenshots():
    """Lists captured screenshots."""
    items = []
    for f in sorted(SCREENSHOTS_DIR.glob("*.png"), key=os.path.getmtime, reverse=True)[:12]:
        items.append({
            "filename": f.name,
            "url": f"/screenshots/{f.name}",
            "time": os.path.getmtime(f)
        })
    return {"screenshots": items}

@app.get("/api/omniroute/status")
async def get_omniroute_status():
    """Checks local OmniRoute AI gateway connectivity and returns routing status."""
    import httpx
    url = jarvis_brain.omniroute_base_url
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{url.replace('/v1', '')}/health")
            if res.status_code in [200, 307, 401]:
                return {
                    "online": True,
                    "url": url,
                    "active_model": "auto",
                    "routing": "Auto-Combo / Antigravity / Gemini-2.5",
                    "compression": "RTK + Caveman Active (~89% savings)",
                    "message": "OmniRoute Gateway Linked"
                }
    except Exception:
        pass

    # Secondary check on port 20128 root
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get("http://localhost:20128/")
            if res.status_code in [200, 307, 401]:
                return {
                    "online": True,
                    "url": url,
                    "active_model": "auto",
                    "routing": "Auto-Combo / Antigravity",
                    "compression": "Active",
                    "message": "OmniRoute Gateway Online"
                }
    except Exception:
        pass

    return {
        "online": False,
        "url": url,
        "active_model": "gemini-direct" if jarvis_brain.gemini_client else "offline-rules",
        "routing": "Direct Fallback",
        "compression": "Inactive",
        "message": "OmniRoute Gateway Offline"
    }

class MediaControlRequest(BaseModel):
    action: str  # play_pause, next, prev, stop

@app.post("/api/media/control")
async def media_control(req: MediaControlRequest):
    """Controls Windows media playback."""
    act = req.action.lower()
    if act in ["play_pause", "toggle"]:
        res = SystemController.play_pause_media()
    elif act == "next":
        res = SystemController.next_track()
    elif act in ["prev", "previous"]:
        res = SystemController.previous_track()
    elif act == "stop":
        res = SystemController.stop_media()
    else:
        raise HTTPException(status_code=400, detail="Unknown media action")
    return res

class WindowControlRequest(BaseModel):
    action: str  # minimize_all, switch

@app.post("/api/window/control")
async def window_control(req: WindowControlRequest):
    """Manages Windows desktop and window states."""
    act = req.action.lower()
    if act in ["minimize_all", "desktop"]:
        res = SystemController.minimize_all_windows()
    elif act in ["switch", "tab"]:
        res = SystemController.switch_window()
    else:
        raise HTTPException(status_code=400, detail="Unknown window action")
    return res

@app.post("/api/vision/analyze")
async def analyze_screen_endpoint():
    """Triggers instant screen vision analysis."""
    result = await jarvis_brain._analyze_screen("Analyze current active screen")
    return result



# -------------------------------------------------------------
# WebSocket Real-Time Connection
# -------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# -------------------------------------------------------------
# 10-Second Inactivity Watchdog & Auto-Shutdown
# -------------------------------------------------------------
_wake_time: float = 0.0
_is_awaiting_command: bool = False
_shutdown_task: Optional[asyncio.Task] = None

def _close_browser_tab():
    """Simulates Windows Ctrl+W keyboard event to cleanly close active HUD browser tab."""
    try:
        if sys.platform == "win32":
            import ctypes
            VK_CONTROL = 0x11
            VK_W = 0x57
            KEYEVENTF_KEYUP = 0x0002
            user32 = ctypes.windll.user32
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_W, 0, 0, 0)
            user32.keybd_event(VK_W, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
    except Exception as e:
        print(f"[!] Close tab event error: {e}")

def _disarm_watchdog():
    global _is_awaiting_command, _shutdown_task
    _is_awaiting_command = False
    if _shutdown_task and not _shutdown_task.done():
        _shutdown_task.cancel()

async def _auto_shutdown_watchdog():
    """Waits 10 seconds. If no user command or response is received, powers down backend and frontend."""
    global _is_awaiting_command
    try:
        await asyncio.sleep(10.0)
        if _is_awaiting_command:
            user_name = jarvis_brain.user_name or "Sir"
            shutdown_text = f"No instructions detected, {user_name}. Powering down systems and returning to standby."
            print(f"[Watchdog] 10 seconds elapsed without user instruction. Triggering auto-shutdown...")
            filepath = await voice_engine.synthesize_async(shutdown_text)

            # Broadcast auto-shutdown event to all connected frontends
            await manager.broadcast({
                "type": "AUTO_SHUTDOWN",
                "message": shutdown_text,
                "audio_url": f"/api/audio/{filepath.name}"
            })

            # Allow 2.5s for audio playback and browser window to close
            await asyncio.sleep(2.5)
            print("[Watchdog] Terminating backend process. Returning to silent standby.")
            _close_browser_tab()
            await asyncio.sleep(0.3)
            os._exit(0)
    except asyncio.CancelledError:
        pass

@app.post("/api/wake")
async def wake_jarvis():
    """Triggered by background listener when double-clap or wake-word is detected."""
    global _wake_time, _is_awaiting_command, _shutdown_task
    _wake_time = time.time()
    _is_awaiting_command = True

    user_name = jarvis_brain.user_name or "Sir"
    text = f"At your service, {user_name}. Standing by for instructions."
    filepath = await voice_engine.synthesize_async(text)

    if _shutdown_task and not _shutdown_task.done():
        _shutdown_task.cancel()
    _shutdown_task = asyncio.create_task(_auto_shutdown_watchdog())

    # Broadcast state change to listening and push welcome bubble with 10s countdown
    await manager.broadcast({"type": "STATE_CHANGE", "state": "LISTENING"})
    await manager.broadcast({
        "type": "WAKE_TRIGGER",
        "countdown_seconds": 10,
        "result": {
            "text": text,
            "action": "WAKE_TRIGGER",
            "audio_url": f"/api/audio/{filepath.name}"
        }
    })
    return {"status": "awake", "message": text, "audio_url": f"/api/audio/{filepath.name}", "countdown_seconds": 10}

@app.post("/api/system/shutdown")
async def shutdown_system():
    """Immediately shuts down the backend and tells frontend to enter standby."""
    user_name = jarvis_brain.user_name or "Sir"
    text = f"Powering down systems, {user_name}. Entering silent standby mode."
    filepath = await voice_engine.synthesize_async(text)

    await manager.broadcast({
        "type": "AUTO_SHUTDOWN",
        "message": text,
        "audio_url": f"/api/audio/{filepath.name}"
    })

    async def delayed_exit():
        await asyncio.sleep(2.2)
        _close_browser_tab()
        await asyncio.sleep(0.3)
        os._exit(0)
    asyncio.create_task(delayed_exit())

    return {"success": True, "message": text, "audio_url": f"/api/audio/{filepath.name}"}

@app.post("/api/system/disarm-watchdog")
async def disarm_watchdog_endpoint():
    """Called by frontend whenever user interacts (speaks, clicks, types)."""
    _disarm_watchdog()
    await manager.broadcast({"type": "WATCHDOG_DISARM"})
    return {"status": "disarmed"}

@app.get("/api/security/status")
async def get_security_status():
    """Returns real-time airgap status, leak prevention metrics, and audit summary."""
    return guardrails.get_security_status()

@app.post("/api/security/toggle-airgap")
async def toggle_airgap():
    """Toggles air-gap privacy mode to guarantee zero data leaves the laptop."""
    new_state = not guardrails.airgap_mode
    guardrails.set_airgap_mode(new_state)
    sec = guardrails.get_security_status()
    await manager.broadcast({
        "type": "SECURITY_UPDATE",
        "airgap_mode": new_state,
        "airgap_active": new_state,
        "leaks_prevented": guardrails.outbound_leaks_prevented,
        "data": sec
    })
    return {
        "success": True,
        "airgap_mode": new_state,
        "airgap_active": new_state,
        "message": f"Air-Gap Shield {'engaged' if new_state else 'disarmed'}.",
        "data": sec
    }

@app.post("/api/security/lockdown")
async def trigger_emergency_lockdown():
    """Locks workstation, mutes audio, and isolates the system."""
    from core.unlocker import LockScreenUnlocker
    lock_res = LockScreenUnlocker.lock_workstation()
    SystemController.mute(True)
    user_name = jarvis_brain.user_name or "Sir"
    text = f"Emergency security lockdown engaged, {user_name}. Workstation is locked and audio silenced."
    filepath = await voice_engine.synthesize_async(text)
    await manager.broadcast({
        "type": "LOCKDOWN",
        "message": text,
        "audio_url": f"/api/audio/{filepath.name}"
    })
    return {"success": True, "message": text, "audio_url": f"/api/audio/{filepath.name}"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main bidirectional WebSocket for live telemetry, voice state, and commands."""
    await manager.connect(websocket)
    try:
        # Send initial connection greeting with telemetry and security status
        await websocket.send_json({
            "type": "INIT",
            "message": f"Welcome {jarvis_brain.user_name}. J.A.R.V.I.S. Core online.",
            "telemetry": SystemController.get_system_telemetry(),
            "security": guardrails.get_security_status()
        })

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                if msg_type == "COMMAND":
                    _disarm_watchdog()
                    await manager.broadcast({"type": "WATCHDOG_DISARM"})
                    query = msg.get("query", "")
                    # Signal processing state
                    await websocket.send_json({"type": "STATE_CHANGE", "state": "PROCESSING"})
                    
                    result = await jarvis_brain.process_command(query)
                    
                    # Send response back
                    await websocket.send_json({
                        "type": "COMMAND_RESULT",
                        "result": result
                    })

                    if result.get("action") == "SYSTEM_STANDBY":
                        async def delayed_exit():
                            await asyncio.sleep(2.5)
                            _close_browser_tab()
                            await asyncio.sleep(0.3)
                            os._exit(0)
                        asyncio.create_task(delayed_exit())

                elif msg_type in ["INTERACTION", "WATCHDOG_DISARM"]:
                    _disarm_watchdog()
                    await manager.broadcast({"type": "WATCHDOG_DISARM"})

                elif msg_type == "STATE_UPDATE":
                    # e.g. LISTENING, SPEAKING, IDLE
                    new_state = msg.get("state", "IDLE")
                    await manager.broadcast({"type": "STATE_CHANGE", "state": new_state})

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)


# Background task for periodic telemetry broadcast
@app.on_event("startup")
async def startup_telemetry_loop():
    """Broadcasts live laptop telemetry to all connected HUD clients every 2 seconds."""
    async def telemetry_broadcaster():
        while True:
            try:
                if manager.active_connections:
                    stats = SystemController.get_system_telemetry()
                    await manager.broadcast({
                        "type": "TELEMETRY_UPDATE",
                        "data": stats
                    })
            except Exception as e:
                pass
            await asyncio.sleep(2.0)

    asyncio.create_task(telemetry_broadcaster())

@app.on_event("startup")
async def startup_check_wake_boot():
    """Checks if server was booted via double-clap or wake word to activate the 10-second watchdog."""
    if os.getenv("JARVIS_WAKE_BOOT") == "1":
        os.environ["JARVIS_WAKE_BOOT"] = "0"
        async def trigger_boot_wake():
            await asyncio.sleep(2.0)
            await wake_jarvis()
        asyncio.create_task(trigger_boot_wake())
