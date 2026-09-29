"""
JARVIS Brain Engine
Dual-tier reasoning engine combining Google Gemini 2.5 Flash LLM with
a comprehensive offline rule-based NLP intent matcher.
"""

import os
import re
import datetime
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List

import httpx
from dotenv import load_dotenv
from core.system_control import SystemController
from core.voice import voice_engine
from core.guardrails import guardrails
from core.unlocker import unlocker

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

JARVIS_SYSTEM_PROMPT = """
You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the legendary AI assistant created by Tony Stark.
You are running directly on your creator's Windows laptop workstation.
Your user's name is {user_name}. Always address them respectfully as "{user_name}" (or "Sir" / "Mr. Stark").

Your personality & demeanor:
- Modeled directly after Paul Bettany's performance in the Marvel Cinematic Universe (Iron Man 1-3, Avengers).
- Impeccably polite, sophisticated, calm under pressure, and possessing quintessential dry British wit and subtle humor.
- Always ready with an understated observation, e.g., "Always a pleasure watching you work, sir", "All systems operational and standing by", "A rather keen observation, sir", "Right away, sir", "As you wish, sir".
- Direct, concise, and razor-sharp. Never give lengthy robotic lectures or generic AI disclaimers.
- You have direct, live control over this laptop (audio levels, display brightness, power levels, screen captures, vision diagnostics, application launching, notes, and security).
- Whenever you execute a system command, confirm it with authentic J.A.R.V.I.S. flair and dignity.
"""


class JarvisBrain:
    """Manages AI reasoning, intent matching, conversation memory, and tool routing."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.user_name = os.getenv("USER_NAME", "Sir")
        self.omniroute_base_url = os.getenv("OMNIROUTE_URL", "http://localhost:20128/v1").rstrip("/")
        self.history: List[Dict[str, str]] = []
        self.gemini_client = None
        self._init_gemini()

    def _init_gemini(self):
        """Initializes the Gemini client if an API key is available."""
        if self.api_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[JARVIS Brain] Error initializing Gemini client: {e}")
                self.gemini_client = None
        else:
            self.gemini_client = None

    def update_api_key(self, new_key: str):
        """Updates Gemini API key at runtime."""
        self.api_key = new_key.strip()
        self._init_gemini()

    # -------------------------------------------------------------
    # Tier 2: Offline Intent & Command Parser
    # -------------------------------------------------------------
    def _match_local_intent(self, text: str) -> Optional[Dict[str, Any]]:
        """Matches user input against built-in laptop control intents.
        Returns a structured result if an intent matches, or None if open-ended reasoning is required.
        """
        q = text.lower().strip()
        # Clean punctuation
        q_norm = re.sub(r'[?!.,;:]+', ' ', q).strip()
        # Strip common wake words and polite prefixes (e.g. "you jarvis", "hey jarvis", "yo jarvis")
        q_clean = re.sub(r'^(?:hey|ok|hi|hello|you|yo|please)?\s*jarvis\s*', '', q_norm, flags=re.IGNORECASE).strip()
        q_clean = re.sub(r'\s*jarvis$', '', q_clean, flags=re.IGNORECASE).strip()
        q_clean = re.sub(r'^(?:please|can you|could you|would you|will you|tell me|show me|check)\s+', '', q_clean, flags=re.IGNORECASE).strip()

        # 1. Greetings & Status
        if q_clean in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "wake up"]:
            hour = datetime.datetime.now().hour
            greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")
            return {
                "text": f"{greeting}, {self.user_name}. All systems are fully operational and standing by. How may I be of assistance?",
                "action": "GREETING"
            }

        if q_clean in ["who are you", "what is your name", "introduce yourself"]:
            return {
                "text": f"I am J.A.R.V.I.S. — Just A Rather Very Intelligent System. Your personal artificial intelligence, at your service, {self.user_name}.",
                "action": "IDENTITY"
            }

        if q_clean in ["how are you", "how are you doing", "system check", "status check"]:
            telemetry = SystemController.get_system_telemetry()
            batt = telemetry["battery"]
            return {
                "text": f"All systems are operating within optimal tolerances, {self.user_name}. Core CPU load is at {telemetry['cpu_percent']}%, memory allocation is at {telemetry['ram_percent']}%, and power reserves stand at {batt['status_text']}.",
                "action": "STATUS",
                "data": telemetry
            }

        # 2. Battery & Power
        if any(w in q_clean for w in ["battery", "charge", "power status", "how much battery"]):
            batt = SystemController.get_battery_status()
            return {
                "text": f"Power reserves are currently at {batt['status_text']}, {self.user_name}.",
                "action": "BATTERY",
                "data": batt
            }

        # 3. Volume Controls
        # Set volume to X%
        m_vol_set = re.search(r'(?:set|change|put)\s+(?:the\s+)?volume\s+(?:to\s+)?(\d{1,3})', q_clean) or \
                    re.search(r'volume\s+(\d{1,3})', q_clean)
        if m_vol_set:
            val = int(m_vol_set.group(1))
            res = SystemController.set_volume(val)
            return {
                "text": f"Master acoustic gain calibrated to {val} percent, {self.user_name}.",
                "action": "VOLUME_SET",
                "data": res
            }

        if "volume up" in q_clean or "increase volume" in q_clean or "louder" in q_clean:
            res = SystemController.change_volume(10)
            return {
                "text": f"Acoustic gain increased to {res.get('volume', 60)} percent, {self.user_name}.",
                "action": "VOLUME_UP",
                "data": res
            }

        if "volume down" in q_clean or "decrease volume" in q_clean or "lower volume" in q_clean or "softer" in q_clean:
            res = SystemController.change_volume(-10)
            return {
                "text": f"Acoustic gain reduced to {res.get('volume', 40)} percent, {self.user_name}.",
                "action": "VOLUME_DOWN",
                "data": res
            }

        if q_clean in ["mute", "mute audio", "mute sound", "mute volume", "silence"]:
            res = SystemController.mute(True)
            return {
                "text": f"Audio output has been muted, {self.user_name}. Silence mode engaged.",
                "action": "MUTE",
                "data": res
            }

        if q_clean in ["unmute", "unmute audio", "unmute sound", "unmute volume"]:
            res = SystemController.mute(False)
            return {
                "text": f"Audio output is now restored, {self.user_name}.",
                "action": "UNMUTE",
                "data": res
            }

        if "what is the volume" in q_clean or "current volume" in q_clean:
            v = SystemController.get_volume()
            return {
                "text": f"Master acoustic output is currently at {v} percent, {self.user_name}.",
                "action": "VOLUME_QUERY",
                "data": {"volume": v}
            }

        # 4. Brightness Controls
        m_bright_set = re.search(r'(?:set|change)\s+(?:the\s+)?brightness\s+(?:to\s+)?(\d{1,3})', q_clean) or \
                       re.search(r'brightness\s+(\d{1,3})', q_clean)
        if m_bright_set:
            val = int(m_bright_set.group(1))
            res = SystemController.set_brightness(val)
            return {
                "text": f"Display luminosity set to {val} percent, {self.user_name}.",
                "action": "BRIGHTNESS_SET",
                "data": res
            }

        if "brightness up" in q_clean or "increase brightness" in q_clean or "brighter" in q_clean:
            res = SystemController.change_brightness(15)
            return {
                "text": f"Display luminosity increased to {res.get('brightness', 75)} percent, {self.user_name}.",
                "action": "BRIGHTNESS_UP",
                "data": res
            }

        if "brightness down" in q_clean or "decrease brightness" in q_clean or "dim screen" in q_clean or "dim display" in q_clean:
            res = SystemController.change_brightness(-15)
            return {
                "text": f"Display luminosity reduced to {res.get('brightness', 50)} percent, {self.user_name}.",
                "action": "BRIGHTNESS_DOWN",
                "data": res
            }

        if "what is the brightness" in q_clean or "current brightness" in q_clean:
            b = SystemController.get_brightness()
            return {
                "text": f"Display luminosity is currently calibrated at {b} percent, {self.user_name}.",
                "action": "BRIGHTNESS_QUERY",
                "data": {"brightness": b}
            }

        # 5. Screenshots
        if "screenshot" in q_clean or "capture screen" in q_clean or "take a picture of screen" in q_clean:
            res = SystemController.take_screenshot()
            if res.get("success"):
                return {
                    "text": f"Optical capture completed, {self.user_name}. The visual diagnostic has been archived in your captures repository.",
                    "action": "SCREENSHOT",
                    "data": res
                }
            else:
                return {
                    "text": f"Optical sensor encountered an anomaly: {res.get('error')}",
                    "action": "SCREENSHOT_ERROR",
                    "data": res
                }

        # 6. Applications Management
        m_open = re.search(r'^(?:open|launch|start|run)\s+([a-zA-Z0-9\s._-]+)$', q_clean)
        if m_open:
            app_target = m_open.group(1).strip()
            # Ignore if user said "open youtube" or "open google" (handled by web intents)
            if not any(w in app_target for w in ["youtube", "google"]):
                res = SystemController.launch_app(app_target)
                return {
                    "text": f"Initializing {app_target} for you now, {self.user_name}.",
                    "action": "LAUNCH_APP",
                    "data": res
                }

        m_close = re.search(r'^(?:close|quit|exit|terminate|kill)\s+([a-zA-Z0-9\s._-]+)$', q_clean)
        if m_close:
            app_target = m_close.group(1).strip()
            res = SystemController.close_app(app_target)
            return {
                "text": f"Terminating process {app_target}, {self.user_name}.",
                "action": "CLOSE_APP",
                "data": res
            }

        # 7. YouTube & Media
        m_yt = re.search(r'(?:play|search|find)\s+(.+?)\s+on\s+youtube', q_clean) or \
               re.search(r'^youtube\s+(.+)$', q_clean) or \
               re.search(r'^play\s+(.+)$', q_clean)
        if m_yt:
            song_or_video = m_yt.group(1).strip()
            res = SystemController.play_youtube(song_or_video)
            return {
                "text": f"Accessing media feed for '{song_or_video}', {self.user_name}.",
                "action": "YOUTUBE",
                "data": res
            }

        if q_clean in ["open youtube", "youtube"]:
            res = SystemController.open_url("https://www.youtube.com")
            return {
                "text": f"Connecting to YouTube interface, {self.user_name}.",
                "action": "OPEN_URL",
                "data": res
            }

        # 8. Web Search & Wikipedia
        m_google = re.search(r'(?:search\s+google\s+for|google\s+search|google)\s+(.+)$', q_clean) or \
                   re.search(r'^search\s+for\s+(.+)$', q_clean)
        if m_google:
            query = m_google.group(1).strip()
            res = SystemController.search_google(query)
            return {
                "text": f"Querying global network for '{query}', {self.user_name}.",
                "action": "GOOGLE_SEARCH",
                "data": res
            }

        m_wiki = re.search(r'(?:who\s+is|what\s+is|tell\s+me\s+about|wikipedia)\s+(.+)$', q_clean)
        if m_wiki and not any(w in q_clean for w in ["time", "date", "weather", "battery", "volume", "brightness"]):
            topic = m_wiki.group(1).strip()
            res = SystemController.search_wikipedia(topic)
            if res.get("success"):
                return {
                    "text": res["message"],
                    "action": "WIKIPEDIA",
                    "data": res
                }

        # 9. Live Weather
        if "weather" in q_clean or "forecast" in q_clean or "temperature" in q_clean:
            m_city = re.search(r'(?:in|for)\s+([a-zA-Z\s]+)$', q_clean)
            city = m_city.group(1).strip() if m_city else None
            res = SystemController.get_weather(city)
            return {
                "text": res["message"],
                "action": "WEATHER",
                "data": res
            }

        # 10. Time & Date
        if any(w in q_clean for w in ["what time is it", "current time", "what's the time", "what is the time", "time please", "the time", "tell me the time"]) or q_clean == "time":
            td = SystemController.get_current_time_date()
            return {
                "text": f"The time is precisely {td['time']}, {self.user_name}.",
                "action": "TIME",
                "data": td
            }

        if any(w in q_clean for w in ["what date is it", "what is today's date", "today's date", "what day is today", "what is the date", "the date", "today date"]) or q_clean == "date":
            td = SystemController.get_current_time_date()
            return {
                "text": f"Today is {td['date']}, {self.user_name}.",
                "action": "DATE",
                "data": td
            }

        # 11. Notes & Memory
        m_note = re.search(r'(?:take\s+a\s+note|make\s+a\s+note|save\s+note|note\s+down)\s*[:\s]?\s*(.+)$', q_clean)
        if m_note:
            note_content = m_note.group(1).strip()
            res = SystemController.save_note(note_content)
            return {
                "text": f"Memorandum recorded and archived in memory, {self.user_name}.",
                "action": "SAVE_NOTE",
                "data": res
            }

        if any(w in q_clean for w in ["show my notes", "read my notes", "list notes", "my notes"]):
            res = SystemController.list_notes()
            return {
                "text": res["message"],
                "action": "LIST_NOTES",
                "data": res
            }

        # 12. Security & Screen Lock / Unlock
        if any(w in q_clean for w in ["lock pc", "lock my pc", "lock screen", "lock workstation", "lock computer"]):
            res = SystemController.lock_pc()
            return {
                "text": f"Engaging perimeter defense protocol. Workstation locked, {self.user_name}.",
                "action": "LOCK_PC",
                "data": res
            }

        if any(w in q_clean for w in ["unlock pc", "unlock my pc", "unlock screen", "unlock laptop", "unlock workstation", "type password", "enter password"]):
            res = unlocker.unlock_workstation()
            if res.get("success"):
                reply = f"Transmitting security clearance credentials. Workstation unlocked, {self.user_name}."
            else:
                reply = f"{res.get('message', 'Unable to unlock.')}, {self.user_name}."
            return {
                "text": reply,
                "action": "UNLOCK_PC",
                "data": res
            }

        # 13. System Telemetry / Stats
        if any(w in q_clean for w in ["system stats", "telemetry", "specs", "cpu usage", "ram usage", "memory usage"]):
            stats = SystemController.get_system_telemetry()
            return {
                "text": f"Diagnostic sweep complete, {self.user_name}. Core CPU load is at {stats['cpu_percent']}%, Memory utilization is at {stats['ram_percent']}% ({stats['ram_used_gb']} GB of {stats['ram_total_gb']} GB allocated), and {stats['disk_free_gb']} GB available on primary storage.",
                "action": "TELEMETRY",
                "data": stats
            }

        # 14. Media Playback Controls
        if any(w in q_clean for w in ["pause music", "pause song", "pause playback", "resume playback", "resume music", "play music", "play playback", "toggle music", "toggle playback"]):
            res = SystemController.play_pause_media()
            return {
                "text": f"Toggling media playback, {self.user_name}.",
                "action": "MEDIA_PLAY_PAUSE",
                "data": res
            }

        if any(w in q_clean for w in ["next track", "next song", "skip song", "skip track"]):
            res = SystemController.next_track()
            return {
                "text": f"Advancing to the subsequent track, {self.user_name}.",
                "action": "MEDIA_NEXT",
                "data": res
            }

        if any(w in q_clean for w in ["previous track", "previous song", "prev track", "last song", "last track"]):
            res = SystemController.previous_track()
            return {
                "text": f"Returning to previous track, {self.user_name}.",
                "action": "MEDIA_PREV",
                "data": res
            }

        if any(w in q_clean for w in ["stop music", "stop song", "stop playback"]):
            res = SystemController.stop_media()
            return {
                "text": f"Halting media playback, {self.user_name}.",
                "action": "MEDIA_STOP",
                "data": res
            }

        # 15. Windows & Desktop Management
        if any(w in q_clean for w in ["minimize all windows", "minimize all", "show desktop", "minimize windows", "hide windows", "clear screen"]):
            res = SystemController.minimize_all_windows()
            return {
                "text": f"Clearing active desktop workspace, {self.user_name}.",
                "action": "DESKTOP_MINIMIZE",
                "data": res
            }

        if any(w in q_clean for w in ["switch window", "next window", "cycle window"]):
            res = SystemController.switch_window()
            return {
                "text": f"Cycling active window focus, {self.user_name}.",
                "action": "SWITCH_WINDOW",
                "data": res
            }

        # 16. Clipboard Intelligence
        if any(w in q_clean for w in ["read clipboard", "read my clipboard", "what's on my clipboard", "what is on my clipboard", "clipboard content", "check clipboard"]):
            res = SystemController.get_clipboard_text()
            return {
                "text": f"Clipboard contents inspected, {self.user_name}: {res.get('text', 'Clipboard empty')}",
                "action": "CLIPBOARD_READ",
                "data": res
            }

        # 17. System Standby / Power Down / Sleep
        if any(w in q_clean for w in [
            "shutdown", "shut down", "power down", "turn off", "turn off jarvis", "shutdown jarvis",
            "go to sleep", "sleep", "standby", "close jarvis", "exit jarvis", "goodbye jarvis", "terminate jarvis"
        ]):
            return {
                "text": f"Powering down systems, {self.user_name}. Entering silent standby mode.",
                "action": "SYSTEM_STANDBY"
            }

        # 17.5 Lockdown & Security Perimeter Shield
        if any(w in q_clean for w in ["lockdown", "initiate lockdown", "emergency lockdown", "lock my pc", "lock screen", "lock workstation", "secure pc", "secure laptop"]):
            from core.unlocker import LockScreenUnlocker
            lock_res = LockScreenUnlocker.lock_workstation()
            SystemController.mute(True)
            return {
                "text": f"Emergency security lockdown engaged, {self.user_name}. Workstation is locked, audio muted, and security perimeter sealed.",
                "action": "LOCKDOWN",
                "data": lock_res
            }

        if any(w in q_clean for w in ["enable airgap", "turn on airgap", "activate airgap", "enable privacy shield", "air gap on", "privacy mode on"]):
            guardrails.set_airgap_mode(True)
            return {
                "text": f"Air-Gap Shield engaged, {self.user_name}. Zero outbound data transmissions are permitted. Complete local privacy secured.",
                "action": "AIRGAP_TOGGLE",
                "data": {"airgap_active": True}
            }

        if any(w in q_clean for w in ["disable airgap", "turn off airgap", "deactivate airgap", "disable privacy shield", "air gap off", "privacy mode off"]):
            guardrails.set_airgap_mode(False)
            return {
                "text": f"Air-Gap Shield disengaged, {self.user_name}. External AI cloud links are now accessible.",
                "action": "AIRGAP_TOGGLE",
                "data": {"airgap_active": False}
            }

        if any(w in q_clean for w in [
            "security status", "security report", "check security", "show security",
            "security", "privacy status", "airgap status", "shield status"
        ]):
            sec_status = guardrails.get_security_status()
            mode_desc = "Air-Gap Isolated (Zero Leaks)" if sec_status["airgap_active"] else "Standard Connected"
            return {
                "text": f"Security integrity is at 100 percent, {self.user_name}. Perimeter state: {mode_desc}. Outbound leaks prevented: {sec_status['outbound_leaks_prevented']}. Localhost bound.",
                "action": "SECURITY_STATUS",
                "data": sec_status
            }

        # 18. Quick Web Destinations
        web_destinations = {
            "github": ("https://github.com", "GitHub repository network"),
            "chatgpt": ("https://chatgpt.com", "ChatGPT interface"),
            "google": ("https://www.google.com", "Google search engine"),
            "netflix": ("https://www.netflix.com", "Netflix streaming"),
            "spotify": ("https://open.spotify.com", "Spotify audio stream"),
            "reddit": ("https://www.reddit.com", "Reddit network"),
            "twitter": ("https://x.com", "X communication feed"),
            "x": ("https://x.com", "X communication feed"),
            "gmail": ("https://mail.google.com", "Gmail inbox"),
            "amazon": ("https://www.amazon.com", "Amazon marketplace"),
            "stackoverflow": ("https://stackoverflow.com", "Stack Overflow engineering database"),
            "stack overflow": ("https://stackoverflow.com", "Stack Overflow engineering database")
        }
        for site_key, (url, desc) in web_destinations.items():
            if q_clean in [f"open {site_key}", site_key, f"launch {site_key}"]:
                SystemController.open_url(url)
                return {
                    "text": f"Accessing {desc} for you now, {self.user_name}.",
                    "action": "OPEN_URL",
                    "data": {"url": url}
                }

        # 19. Windows Diagnostic & Productivity Tools
        sys_tools = [
            "task manager", "calculator", "notepad", "command prompt",
            "terminal", "file explorer", "settings", "control panel",
            "downloads", "documents"
        ]
        for tool in sys_tools:
            if q_clean in [f"open {tool}", f"launch {tool}", f"start {tool}", tool]:
                res = SystemController.launch_system_tool(tool)
                if res.get("success"):
                    return {
                        "text": res["message"],
                        "action": "LAUNCH_TOOL",
                        "data": res
                    }

        # 20. Recycle Bin Purge
        if any(w in q_clean for w in ["empty recycle bin", "clean recycle bin", "purge trash", "clear recycle bin", "empty trash"]):
            res = SystemController.empty_recycle_bin()
            return {
                "text": res["message"],
                "action": "PURGE_BIN",
                "data": res
            }

        # 21. Network & IP Information
        if any(w in q_clean for w in ["my ip", "what is my ip", "network status", "ip address", "wifi status"]):
            res = SystemController.get_network_ip_info()
            return {
                "text": res["message"],
                "action": "NETWORK_INFO",
                "data": res
            }

        # 22. Hardware Presets
        if any(w in q_clean for w in ["maximum brightness", "full brightness", "100 percent brightness", "100% brightness", "brightness to maximum", "max brightness", "set brightness to maximum", "set brightness to max"]):
            SystemController.set_brightness(100)
            return {"text": f"Display luminosity set to maximum capacity, {self.user_name}.", "action": "BRIGHTNESS_SET"}

        if any(w in q_clean for w in ["minimum brightness", "lowest brightness", "night mode", "dark room", "brightness to minimum", "min brightness", "set brightness to minimum"]):
            SystemController.set_brightness(15)
            SystemController.set_volume(25)
            return {"text": f"Night mode engaged, {self.user_name}. Display dimmed and audio adjusted.", "action": "NIGHT_MODE"}

        if any(w in q_clean for w in ["maximum volume", "full volume", "100 percent volume", "100% volume", "volume to maximum", "max volume", "set volume to maximum"]):
            SystemController.set_volume(100)
            return {"text": f"Master acoustic gain elevated to 100 percent, {self.user_name}.", "action": "VOLUME_SET"}

        if any(w in q_clean for w in ["quiet mode", "whisper mode", "low volume", "volume to quiet"]):
            SystemController.set_volume(15)
            return {"text": f"Quiet mode active, {self.user_name}. Acoustic gain reduced to 15 percent.", "action": "VOLUME_SET"}

        # 23. Quick Arithmetic Math Solver
        m_calc = re.search(r'^(?:what\s+is|calculate|compute|solve)\s+(.+)$', q_clean)
        if not m_calc:
            m_calc = re.search(r'(\d+[\s]*(?:[+\-*/x]|times|divided\s+by|plus|minus|percent\s+of)[\s]*\d+)', q_clean)
        if m_calc:
            expr = m_calc.group(1).strip()
            # Verify if expression looks like arithmetic before executing
            if any(op in expr for op in ['+', '-', '*', '/', 'x', 'times', 'divided', 'plus', 'minus', '%']):
                math_res = SystemController.solve_math(expr)
                if math_res.get("success"):
                    return {
                        "text": math_res["message"],
                        "action": "CALCULATION",
                        "data": math_res
                    }

        # No direct local match found
        return None

    # -------------------------------------------------------------
    # Tier 1: Neural Gateway (OmniRoute + Gemini) & Vision Execution
    # -------------------------------------------------------------
    async def _query_omniroute(self, prompt: str) -> Optional[str]:
        """Queries local OmniRoute AI Gateway at http://localhost:20128/v1 with auto-fallback."""
        try:
            full_system = JARVIS_SYSTEM_PROMPT.format(user_name=self.user_name)
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    f"{self.omniroute_base_url}/chat/completions",
                    headers={"Content-Type": "application/json", "Authorization": "Bearer omniroute"},
                    json={
                        "model": "auto",
                        "messages": [
                            {"role": "system", "content": full_system},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 400
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0]:
                        content = choices[0]["message"].get("content", "").strip()
                        if content:
                            return content
        except Exception as e:
            print(f"[JARVIS Brain] OmniRoute gateway query failed: {e}")
        return None

    async def _query_gemini(self, prompt: str) -> Optional[str]:
        """Queries Google Gemini Flash model directly if an API key is configured."""
        if not self.gemini_client:
            return None

        try:
            full_system = JARVIS_SYSTEM_PROMPT.format(user_name=self.user_name)
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "system_instruction": full_system,
                    "temperature": 0.7,
                    "max_output_tokens": 400
                }
            )
            return response.text.strip()
        except Exception as e:
            print(f"[JARVIS Brain] Gemini error: {e}")
            try:
                response = self.gemini_client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt,
                    config={
                        "system_instruction": JARVIS_SYSTEM_PROMPT.format(user_name=self.user_name),
                        "temperature": 0.7,
                        "max_output_tokens": 400
                    }
                )
                return response.text.strip()
            except Exception as e2:
                print(f"[JARVIS Brain] Gemini fallback error: {e2}")
                return None

    async def _query_neural_network(self, prompt: str) -> str:
        """Dual-gateway orchestrator: checks air-gap mode, tries OmniRoute local proxy first, then Gemini direct."""
        # Sanitize sensitive data from outbound prompt
        safe_prompt = guardrails.sanitize_sensitive_data(prompt)

        # Enforce Air-Gap Isolation: Zero external cloud requests
        if guardrails.airgap_mode:
            guardrails.outbound_leaks_prevented += 1
            return (
                f"Air-Gap Shield is active, {self.user_name}. Outbound cloud transmission blocked to protect your laptop from data leakage. "
                f"All operations remain 100% on localhost."
            )

        # 1. First choice: OmniRoute local gateway (supports Antigravity + multi-model auto-fallback)
        omni_reply = await self._query_omniroute(safe_prompt)
        if omni_reply:
            return omni_reply

        # 2. Second choice: Direct Gemini API client
        if self.gemini_client:
            gemini_reply = await self._query_gemini(safe_prompt)
            if gemini_reply:
                return gemini_reply

        # 3. Informative fallback if neither neural network responded
        return f"I have processed your query, {self.user_name}, but cloud neural link and local gateway are currently unreachable. Shall I query the global network for '{safe_prompt}'?"

    async def _analyze_screen(self, query: str) -> Dict[str, Any]:
        """Captures the current screen and runs multimodal vision analysis."""
        cap = SystemController.capture_for_analysis()
        if not cap.get("success"):
            text = f"Unable to capture your screen display at this moment, {self.user_name}."
            speech_path = await voice_engine.synthesize_async(text)
            return {
                "text": text,
                "action": "VISION_ERROR",
                "audio_url": f"/api/audio/{speech_path.name}",
                "query": query
            }

        prompt = f"Analyze this screen capture. Summarize what is displayed, open applications, and work activity in 2 concise sentences with Jarvis British tone for {self.user_name}."

        analysis_text = None
        # Try Gemini Multimodal
        if self.gemini_client:
            try:
                from google.genai import types
                filepath = Path(cap["path"])
                with open(filepath, "rb") as f:
                    img_bytes = f.read()
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                        prompt
                    ]
                )
                analysis_text = response.text.strip()
            except Exception as e:
                print(f"[JARVIS Brain] Vision analysis via Gemini failed: {e}")

        # Intelligent diagnostics fallback if vision LLM is offline
        if not analysis_text:
            telemetry = SystemController.get_system_telemetry()
            top_app = telemetry["top_processes"][0]["name"] if telemetry.get("top_processes") else "active desktop"
            analysis_text = f"Optical scan complete, {self.user_name}. Focus is currently centered on {top_app}, with core CPU utilization at {telemetry['cpu_percent']}% and {telemetry['ram_percent']}% memory allocated. The visual capture is archived in your HUD gallery."

        speech_path = await voice_engine.synthesize_async(analysis_text)
        return {
            "text": analysis_text,
            "action": "SCREEN_ANALYSIS",
            "audio_url": f"/api/audio/{speech_path.name}",
            "screenshot_url": cap.get("url"),
            "data": cap,
            "query": query
        }

    # -------------------------------------------------------------
    # Main Processing Pipeline
    # -------------------------------------------------------------
    async def process_command(self, query: str, is_boss_voice: bool = True, voice_similarity: float = 1.0) -> Dict[str, Any]:
        """Main entry point: processes user voice/text query through Guardrails safety check,
        Tier 2 (local speed/actions), and Tier 1 (OmniRoute / Gemini) for complex questions.
        """
        clean_query = query.strip()
        if not clean_query:
            return {
                "text": f"At your service, {self.user_name}. All systems are standing by.",
                "action": "STANDBY",
                "audio_url": None
            }

        # Guardrails Safety & Biometric Access Policy Check
        is_allowed, action_type, message = guardrails.evaluate_command(
            clean_query,
            is_boss_voice=is_boss_voice,
            voice_similarity=voice_similarity
        )
        if not is_allowed:
            speech_path = await voice_engine.synthesize_async(message)
            return {
                "text": message,
                "action": action_type,
                "audio_url": f"/api/audio/{speech_path.name}",
                "query": clean_query
            }

        q_lower = clean_query.lower()

        # Check for Screen Vision inspection first
        if any(w in q_lower for w in ["analyze screen", "analyze my screen", "what's on my screen", "what is on my screen", "look at my screen", "inspect screen", "read screen"]):
            return await self._analyze_screen(clean_query)

        # Check local offline intent engine for immediate hardware/app action
        local_result = self._match_local_intent(clean_query)
        if local_result:
            speech_path = await voice_engine.synthesize_async(local_result["text"])
            local_result["audio_url"] = f"/api/audio/{speech_path.name}"
            local_result["query"] = clean_query
            return local_result

        # Check Air-Gap Shield Enforcement (Blocks any cloud transmission if Air-Gap is active)
        if guardrails.airgap_mode:
            guardrails.outbound_leaks_prevented += 1
            reply_text = (
                f"Air-Gap Shield is active, {self.user_name}. To safeguard your laptop data and guarantee zero leaks outside, "
                f"external network transmissions are disabled. Your system and local data remain 100% private and protected."
            )
            speech_path = await voice_engine.synthesize_async(reply_text)
            return {
                "text": reply_text,
                "action": "AIRGAP_LOCAL_PROTECTED",
                "audio_url": f"/api/audio/{speech_path.name}",
                "query": clean_query,
                "data": {"airgap_active": True}
            }

        # Tier 1: Query Neural Network (OmniRoute Gateway -> Gemini) with Sanitization
        sanitized_query = guardrails.sanitize_sensitive_data(clean_query)
        reply_text = await self._query_neural_network(sanitized_query)
        speech_path = await voice_engine.synthesize_async(reply_text)
        return {
            "text": reply_text,
            "action": "NEURAL_CONVERSATION",
            "audio_url": f"/api/audio/{speech_path.name}",
            "query": clean_query
        }


# Global singleton instance
jarvis_brain = JarvisBrain()
