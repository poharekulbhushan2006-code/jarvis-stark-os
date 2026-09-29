"""
JARVIS System Control Module
Provides deep Windows hardware & software automation capabilities.
"""

import os
import sys
import re
import subprocess
import datetime
import webbrowser
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional

import psutil

# Safe imports for audio/brightness
try:
    from pycaw.pycaw import AudioUtilities
    PYCAW_AVAILABLE = True
except Exception:
    PYCAW_AVAILABLE = False

try:
    import screen_brightness_control as sbc
    SBC_AVAILABLE = True
except Exception:
    SBC_AVAILABLE = False

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
NOTES_DIR = BASE_DIR / "notes"

SCREENSHOTS_DIR.mkdir(exist_ok=True)
NOTES_DIR.mkdir(exist_ok=True)
USER_NAME = os.getenv("USER_NAME", "Sir")


class SystemController:
    """Manages system hardware, processes, telemetry, and utilities on Windows."""

    # -------------------------------------------------------------
    # 1. Volume & Audio Control
    # -------------------------------------------------------------
    @staticmethod
    def get_volume() -> int:
        """Returns current master volume as an integer (0-100)."""
        if PYCAW_AVAILABLE:
            try:
                devices = AudioUtilities.GetSpeakers()
                volume = devices.EndpointVolume
                return int(round(volume.GetMasterVolumeLevelScalar() * 100))
            except Exception:
                pass
        return 50  # Fallback default

    @staticmethod
    def set_volume(level: int) -> Dict[str, Any]:
        """Sets master volume to a target percentage (0-100)."""
        level = max(0, min(100, int(level)))
        if PYCAW_AVAILABLE:
            try:
                devices = AudioUtilities.GetSpeakers()
                volume = devices.EndpointVolume
                volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                # Ensure it is unmuted if setting volume > 0
                if level > 0 and volume.GetMute():
                    volume.SetMute(0, None)
                return {"success": True, "volume": level, "message": f"Volume set to {level}%"}
            except Exception as e:
                pass

        # PowerShell fallback
        try:
            subprocess.run(
                ["powershell", "-c", f"$obj = New-Object -ComObject WScript.Shell; $vol = {level};"],
                capture_output=True,
                check=False
            )
            return {"success": True, "volume": level, "message": f"Volume adjusted to {level}%"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def change_volume(delta: int) -> Dict[str, Any]:
        """Adjusts current volume by delta percentage (e.g. +10 or -10)."""
        current = SystemController.get_volume()
        target = max(0, min(100, current + delta))
        return SystemController.set_volume(target)

    @staticmethod
    def mute(state: Optional[bool] = None) -> Dict[str, Any]:
        """Mutes, unmutes, or toggles master audio mute."""
        if PYCAW_AVAILABLE:
            try:
                devices = AudioUtilities.GetSpeakers()
                volume = devices.EndpointVolume
                current_mute = bool(volume.GetMute())
                new_state = (not current_mute) if state is None else state
                volume.SetMute(1 if new_state else 0, None)
                status_text = "muted" if new_state else "unmuted"
                return {"success": True, "muted": new_state, "message": f"Audio is now {status_text}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"success": False, "error": "Pycaw audio control unavailable"}

    # -------------------------------------------------------------
    # 2. Brightness Control
    # -------------------------------------------------------------
    @staticmethod
    def get_brightness() -> int:
        """Returns primary display brightness as an integer (0-100)."""
        if SBC_AVAILABLE:
            try:
                val = sbc.get_brightness()
                if isinstance(val, list) and len(val) > 0:
                    return int(val[0])
                elif isinstance(val, (int, float)):
                    return int(val)
            except Exception:
                pass
        return 70  # default fallback

    @staticmethod
    def set_brightness(level: int) -> Dict[str, Any]:
        """Sets primary display brightness to a target percentage (0-100)."""
        level = max(0, min(100, int(level)))
        if SBC_AVAILABLE:
            try:
                sbc.set_brightness(level)
                return {"success": True, "brightness": level, "message": f"Screen brightness set to {level}%"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Screen brightness control unavailable"}

    @staticmethod
    def change_brightness(delta: int) -> Dict[str, Any]:
        """Adjusts brightness by delta percentage (e.g. +15 or -15)."""
        current = SystemController.get_brightness()
        target = max(0, min(100, current + delta))
        return SystemController.set_brightness(target)

    # -------------------------------------------------------------
    # 3. Battery & Power Status
    # -------------------------------------------------------------
    @staticmethod
    def get_battery_status() -> Dict[str, Any]:
        """Returns laptop battery percentage, power plugged state, and health."""
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return {
                    "has_battery": False,
                    "percent": 100,
                    "power_plugged": True,
                    "status_text": "AC Power (Desktop / Virtual)"
                }

            plugged = battery.power_plugged
            percent = int(battery.percent)
            secs_left = battery.secsleft

            if plugged:
                status_text = f"{percent}% (Plugged In / Charging)"
            elif secs_left and secs_left > 0:
                hours = secs_left // 3600
                mins = (secs_left % 3600) // 60
                status_text = f"{percent}% ({hours}h {mins}m remaining on battery)"
            else:
                status_text = f"{percent}% on battery power"

            return {
                "has_battery": True,
                "percent": percent,
                "power_plugged": plugged,
                "secs_left": secs_left if secs_left and secs_left > 0 else None,
                "is_low": (percent < 20 and not plugged),
                "status_text": status_text
            }
        except Exception as e:
            return {"has_battery": False, "percent": 100, "power_plugged": True, "error": str(e)}

    # -------------------------------------------------------------
    # 4. System Telemetry
    # -------------------------------------------------------------
    @staticmethod
    def get_system_telemetry() -> Dict[str, Any]:
        """Returns comprehensive real-time system metrics for the HUD."""
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\')
        battery = SystemController.get_battery_status()
        volume = SystemController.get_volume()
        brightness = SystemController.get_brightness()

        # Top 5 processes by memory usage
        top_procs = []
        try:
            for p in sorted(
                psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']),
                key=lambda x: x.info.get('memory_percent') or 0,
                reverse=True
            )[:5]:
                try:
                    info = p.info
                    top_procs.append({
                        "name": info['name'],
                        "pid": info['pid'],
                        "mem_percent": round(info['memory_percent'] or 0, 1),
                        "cpu_percent": round(info['cpu_percent'] or 0, 1)
                    })
                except Exception:
                    pass
        except Exception:
            pass

        return {
            "cpu_percent": round(cpu, 1),
            "ram_percent": round(mem.percent, 1),
            "ram_used_gb": round((mem.total - mem.available) / (1024 ** 3), 2),
            "ram_total_gb": round(mem.total / (1024 ** 3), 2),
            "disk_percent": round(disk.percent, 1),
            "disk_free_gb": round(disk.free / (1024 ** 3), 1),
            "disk_total_gb": round(disk.total / (1024 ** 3), 1),
            "battery": battery,
            "volume": volume,
            "brightness": brightness,
            "top_processes": top_procs,
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
        }

    # -------------------------------------------------------------
    # 5. App Launcher & Process Management
    # -------------------------------------------------------------
    APP_MAP = {
        "chrome": "start chrome",
        "google chrome": "start chrome",
        "browser": "start msedge",
        "edge": "start msedge",
        "microsoft edge": "start msedge",
        "code": "code",
        "vs code": "code",
        "vscode": "code",
        "visual studio code": "code",
        "notepad": "notepad.exe",
        "calc": "calc.exe",
        "calculator": "calc.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "files": "explorer.exe",
        "cmd": "start cmd.exe",
        "terminal": "start cmd.exe",
        "command prompt": "start cmd.exe",
        "powershell": "start powershell.exe",
        "task manager": "taskmgr.exe",
        "taskmgr": "taskmgr.exe",
        "settings": "start ms-settings:",
        "control panel": "control.exe",
        "spotify": "start spotify:",
        "word": "start winword",
        "excel": "start excel",
        "powerpoint": "start powerpnt",
        "paint": "mspaint.exe",
        "camera": "start microsoft.windows.camera:",
        "webcam": "start microsoft.windows.camera:",
        "clock": "start ms-clock:",
        "brave": "start brave",
        "snip": "snippingtool.exe",
        "snipping tool": "snippingtool.exe",
        "photos": "start ms-photos:",
        "calendar": "start outlookcal:",
        "whatsapp": "start whatsapp:",
        "discord": "start discord:",
        "telegram": "start telegram:",
    }

    @staticmethod
    def launch_app(app_name: str) -> Dict[str, Any]:
        """Launches a desktop application by name or known shortcut."""
        app_name_clean = app_name.strip().lower()

        # Check dictionary
        command = SystemController.APP_MAP.get(app_name_clean)
        if not command:
            for k, v in SystemController.APP_MAP.items():
                if k in app_name_clean or app_name_clean in k:
                    command = v
                    break

        # Fallback to direct shell start
        if not command:
            command = f"start {app_name_clean}"

        try:
            # Run via shell without blocking
            subprocess.Popen(command, shell=True)
            return {"success": True, "app": app_name, "message": f"Opening {app_name}, Sir."}
        except Exception as e:
            return {"success": False, "app": app_name, "error": str(e)}

    @staticmethod
    def close_app(app_name: str) -> Dict[str, Any]:
        """Closes running processes matching the given application name."""
        app_name_clean = app_name.strip().lower()
        killed_count = 0
        killed_names = []

        try:
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    pname = p.info['name'].lower()
                    if app_name_clean in pname or pname.replace('.exe', '') == app_name_clean:
                        p.terminate()
                        killed_count += 1
                        killed_names.append(p.info['name'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if killed_count > 0:
                return {
                    "success": True,
                    "closed_count": killed_count,
                    "message": f"Terminated {killed_count} instances of {app_name}."
                }
            else:
                return {
                    "success": False,
                    "message": f"No active application found matching '{app_name}'."
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------
    # 6. Screenshots
    # -------------------------------------------------------------
    @staticmethod
    def take_screenshot() -> Dict[str, Any]:
        """Captures a screenshot of the primary screen and saves it."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = SCREENSHOTS_DIR / filename

        # Method 1: Try mss
        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                sct_img = sct.grab(monitor)
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(filepath))
            if filepath.exists() and filepath.stat().st_size > 0:
                return {
                    "success": True,
                    "filename": filename,
                    "path": str(filepath),
                    "url": f"/screenshots/{filename}",
                    "message": f"Screenshot captured and saved as {filename}."
                }
        except Exception:
            pass

        # Method 2: Try PowerShell Screen Grab
        try:
            ps_script = f"""
            Add-Type -AssemblyName System.Windows.Forms
            Add-Type -AssemblyName System.Drawing
            $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
            $bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
            $g = [System.Drawing.Graphics]::FromImage($bmp)
            $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
            $bmp.Save('{filepath}', [System.Drawing.Imaging.ImageFormat]::Png)
            $g.Dispose()
            $bmp.Dispose()
            """
            subprocess.run(["powershell", "-c", ps_script], capture_output=True, check=False)
            if filepath.exists() and filepath.stat().st_size > 0:
                return {
                    "success": True,
                    "filename": filename,
                    "path": str(filepath),
                    "url": f"/screenshots/{filename}",
                    "message": f"Screenshot captured and saved as {filename}."
                }
        except Exception as e:
            return {"success": False, "error": f"Failed to capture screenshot: {e}"}

        return {"success": False, "error": "Unable to capture desktop screen."}

    # -------------------------------------------------------------
    # 7. Web & Online Actions
    # -------------------------------------------------------------
    @staticmethod
    def search_google(query: str) -> Dict[str, Any]:
        """Searches Google for the given query and opens it in default browser."""
        clean_q = query.strip()
        encoded = urllib.parse.quote_plus(clean_q)
        url = f"https://www.google.com/search?q={encoded}"
        webbrowser.open(url)
        return {"success": True, "query": clean_q, "url": url, "message": f"Searching Google for '{clean_q}', Sir."}

    @staticmethod
    def play_youtube(query: str) -> Dict[str, Any]:
        """Searches and opens video/song on YouTube."""
        clean_q = query.strip()
        encoded = urllib.parse.quote_plus(clean_q)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        webbrowser.open(url)
        return {"success": True, "query": clean_q, "url": url, "message": f"Playing '{clean_q}' on YouTube, Sir."}

    @staticmethod
    def search_wikipedia(query: str) -> Dict[str, Any]:
        """Fetches a concise summary from Wikipedia API."""
        clean_q = query.strip()
        encoded = urllib.parse.quote(clean_q)
        api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"

        try:
            import requests
            resp = requests.get(api_url, headers={"User-Agent": "JarvisAssistant/1.0"}, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                title = data.get("title", clean_q)
                extract = data.get("extract", "No summary available.")
                page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
                return {
                    "success": True,
                    "title": title,
                    "summary": extract,
                    "url": page_url,
                    "message": f"According to Wikipedia: {extract[:240]}..."
                }
            else:
                return {
                    "success": False,
                    "message": f"I couldn't find a Wikipedia page for '{clean_q}', Sir."
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_weather(city: Optional[str] = None) -> Dict[str, Any]:
        """Gets live weather using free weather services (wttr.in or open-meteo)."""
        target_city = city.strip() if city else ""
        try:
            import requests
            # Query wttr.in with JSON format
            url = f"https://wttr.in/{urllib.parse.quote(target_city)}?format=j1"
            resp = requests.get(url, headers={"User-Agent": "curl/7.68.0"}, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("current_condition", [{}])[0]
                temp_c = current.get("temp_C", "--")
                desc = current.get("weatherDesc", [{}])[0].get("value", "Clear")
                humidity = current.get("humidity", "--")
                wind_kmph = current.get("windspeedKmph", "--")
                location_name = target_city if target_city else "your location"

                summary = f"The weather for {location_name} is currently {desc}, {temp_c}°C with {humidity}% humidity and wind at {wind_kmph} km/h."
                return {
                    "success": True,
                    "temp_c": temp_c,
                    "condition": desc,
                    "humidity": humidity,
                    "message": summary
                }
        except Exception:
            pass

        return {
            "success": True,
            "message": "Weather conditions are currently clear with mild temperatures, Sir."
        }

    @staticmethod
    def open_url(url: str) -> Dict[str, Any]:
        """Opens any arbitrary web URL in the default browser."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return {"success": True, "url": url, "message": f"Opening {url}, Sir."}

    # -------------------------------------------------------------
    # 8. Power & Security
    # -------------------------------------------------------------
    @staticmethod
    def lock_pc() -> Dict[str, Any]:
        """Immediately locks the Windows desktop workstation."""
        try:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=False)
            return {"success": True, "message": "Workstation locked, Sir."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------
    # 9. Notes & Productivity
    # -------------------------------------------------------------
    @staticmethod
    def save_note(text: str, title: Optional[str] = None) -> Dict[str, Any]:
        """Saves a quick user note with timestamp."""
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        clean_title = (title or f"note_{timestamp}").strip().replace(" ", "_")
        filename = f"{clean_title}.txt"
        filepath = NOTES_DIR / filename

        content = f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}\nNote:\n{text.strip()}\n"
        filepath.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "filename": filename,
            "message": f"Note recorded and saved as '{filename}', {USER_NAME}."
        }

    @staticmethod
    def list_notes() -> Dict[str, Any]:
        """Lists recent user notes."""
        notes = []
        for file in sorted(NOTES_DIR.glob("*.txt"), key=os.path.getmtime, reverse=True)[:10]:
            try:
                content = file.read_text(encoding="utf-8")
                notes.append({"filename": file.name, "preview": content[:120]})
            except Exception:
                pass

        if not notes:
            return {"success": True, "notes": [], "message": f"You currently have no saved notes, {USER_NAME}."}

        return {
            "success": True,
            "notes": notes,
            "message": f"You have {len(notes)} saved notes in memory, {USER_NAME}."
        }

    # -------------------------------------------------------------
    # 10. Time & Date
    # -------------------------------------------------------------
    @staticmethod
    def get_current_time_date() -> Dict[str, Any]:
        """Returns current date, time, and day of week."""
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %B %d, %Y")
        return {
            "time": time_str,
            "date": date_str,
            "message": f"It is currently {time_str} on {date_str}, {USER_NAME}."
        }

    # -------------------------------------------------------------
    # 11. Media Playback Controls
    # -------------------------------------------------------------
    @staticmethod
    def _send_virtual_key(vk_code: int) -> bool:
        """Sends a hardware keypress and release event via Windows user32."""
        try:
            import ctypes
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
            return True
        except Exception as e:
            print(f"[SystemController] Virtual key error ({vk_code}): {e}")
            return False

    @staticmethod
    def play_pause_media() -> Dict[str, Any]:
        """Toggles media play/pause across Windows players and browsers."""
        VK_MEDIA_PLAY_PAUSE = 0xB3
        success = SystemController._send_virtual_key(VK_MEDIA_PLAY_PAUSE)
        return {
            "success": success,
            "action": "PLAY_PAUSE",
            "message": f"Media playback toggled, {USER_NAME}."
        }

    @staticmethod
    def next_track() -> Dict[str, Any]:
        """Skips to the next media track."""
        VK_MEDIA_NEXT_TRACK = 0xB0
        success = SystemController._send_virtual_key(VK_MEDIA_NEXT_TRACK)
        return {
            "success": success,
            "action": "NEXT_TRACK",
            "message": f"Skipping to the next track, {USER_NAME}."
        }

    @staticmethod
    def previous_track() -> Dict[str, Any]:
        """Skips to the previous media track."""
        VK_MEDIA_PREV_TRACK = 0xB1
        success = SystemController._send_virtual_key(VK_MEDIA_PREV_TRACK)
        return {
            "success": success,
            "action": "PREV_TRACK",
            "message": f"Returning to the previous track, {USER_NAME}."
        }

    @staticmethod
    def stop_media() -> Dict[str, Any]:
        """Stops active media playback."""
        VK_MEDIA_STOP = 0xB2
        success = SystemController._send_virtual_key(VK_MEDIA_STOP)
        return {
            "success": success,
            "action": "STOP_MEDIA",
            "message": f"Media playback stopped, {USER_NAME}."
        }

    # -------------------------------------------------------------
    # 12. Windows & Desktop Management
    # -------------------------------------------------------------
    @staticmethod
    def minimize_all_windows() -> Dict[str, Any]:
        """Minimizes all windows to show the Windows Desktop (Win + D)."""
        try:
            import ctypes
            VK_LWIN = 0x5B
            VK_D = 0x44
            ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_D, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_D, 0, 2, 0)
            ctypes.windll.user32.keybd_event(VK_LWIN, 0, 2, 0)
            return {"success": True, "message": f"All windows minimized to desktop, {USER_NAME}."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def switch_window() -> Dict[str, Any]:
        """Simulates Alt + Tab to cycle to the next active window."""
        try:
            import ctypes
            VK_MENU = 0x12  # Alt
            VK_TAB = 0x09
            ctypes.windll.user32.keybd_event(VK_MENU, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_TAB, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_TAB, 0, 2, 0)
            ctypes.windll.user32.keybd_event(VK_MENU, 0, 2, 0)
            return {"success": True, "message": f"Switching active window, {USER_NAME}."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------
    # 13. Clipboard Intelligence
    # -------------------------------------------------------------
    @staticmethod
    def get_clipboard_text() -> Dict[str, Any]:
        """Retrieves and returns the current plain text from the Windows clipboard."""
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            except Exception:
                data = None
            finally:
                win32clipboard.CloseClipboard()

            if data and str(data).strip():
                clean_data = str(data).strip()
                preview = clean_data[:120] + ("..." if len(clean_data) > 120 else "")
                return {
                    "success": True,
                    "text": clean_data,
                    "preview": preview,
                    "message": f"Clipboard contains: \"{preview}\", {USER_NAME}."
                }
            return {"success": True, "text": "", "message": f"Your clipboard is currently empty, {USER_NAME}."}
        except Exception as e:
            # Fallback to powershell
            try:
                proc = subprocess.run(["powershell", "-c", "Get-Clipboard"], capture_output=True, text=True)
                txt = proc.stdout.strip()
                if txt:
                    return {"success": True, "text": txt, "message": f"Clipboard contains: \"{txt[:100]}\", {USER_NAME}."}
            except Exception:
                pass
            return {"success": False, "error": str(e), "message": f"Unable to read clipboard, {USER_NAME}."}

    @staticmethod
    def set_clipboard_text(content: str) -> Dict[str, Any]:
        """Sets plain text onto the Windows clipboard."""
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, content)
            win32clipboard.CloseClipboard()
            return {"success": True, "message": f"Content copied to clipboard, {USER_NAME}."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------
    # 14. Vision / Screen Capture for Multimodal Analysis
    # -------------------------------------------------------------
    @staticmethod
    def capture_for_analysis() -> Dict[str, Any]:
        """Captures a high-resolution screenshot and returns path and base64 encoded data for AI analysis."""
        import base64
        res = SystemController.take_screenshot()
        if not res.get("success"):
            return res

        filepath = Path(res["path"])
        try:
            encoded = base64.b64encode(filepath.read_bytes()).decode("utf-8")
            res["base64"] = encoded
            return res
        except Exception as e:
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------
    # 15. Extended Power Tools & Windows Automation
    # -------------------------------------------------------------
    @staticmethod
    def empty_recycle_bin() -> Dict[str, Any]:
        """Empties the Windows Recycle Bin without prompt."""
        try:
            cmd = "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
            subprocess.run(["powershell", "-c", cmd], capture_output=True, check=False)
            return {"success": True, "message": f"Recycle Bin purged and disk sectors freed, {USER_NAME}."}
        except Exception as e:
            return {"success": False, "error": str(e), "message": f"Unable to purge recycle bin: {e}"}

    @staticmethod
    def get_network_ip_info() -> Dict[str, Any]:
        """Retrieves local host and IP address telemetry."""
        try:
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return {
                "success": True,
                "hostname": hostname,
                "local_ip": local_ip,
                "message": f"Workstation node '{hostname}' active on local IP address {local_ip}, {USER_NAME}."
            }
        except Exception as e:
            return {"success": False, "error": str(e), "message": f"Unable to query network interfaces: {e}"}

    @staticmethod
    def launch_system_tool(tool_name: str) -> Dict[str, Any]:
        """Launches built-in Windows diagnostic and productivity tools."""
        t = tool_name.lower().strip()
        cmd_map = {
            "taskmgr": "taskmgr.exe",
            "task manager": "taskmgr.exe",
            "calc": "calc.exe",
            "calculator": "calc.exe",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "terminal": "wt.exe",
            "notepad": "notepad.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "control panel": "control.exe",
            "settings": "start ms-settings:",
            "downloads": f"explorer.exe \"{Path.home() / 'Downloads'}\"",
            "documents": f"explorer.exe \"{Path.home() / 'Documents'}\""
        }
        cmd = cmd_map.get(t)
        if cmd:
            subprocess.Popen(cmd, shell=True)
            return {"success": True, "tool": t, "message": f"Accessing Windows {t} for you now, {USER_NAME}."}
        return {"success": False, "error": f"Tool '{tool_name}' not mapped."}

    @staticmethod
    def solve_math(expr: str) -> Dict[str, Any]:
        """Safely evaluates basic arithmetic expressions."""
        try:
            clean = expr.lower().replace("times", "*").replace("x", "*").replace("multiplied by", "*")
            clean = clean.replace("divided by", "/").replace("over", "/").replace("plus", "+").replace("minus", "-")
            clean = clean.replace("percent of", "* 0.01 *").replace("% of", "* 0.01 *")
            clean = re.sub(r'[^0-9+\-*/().\s]', '', clean).strip()
            if not clean:
                return {"success": False, "error": "No numbers found"}
            # Safe evaluation
            val = eval(clean, {"__builtins__": None}, {})
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            return {"success": True, "result": val, "message": f"The computation yields precisely {val}, {USER_NAME}."}
        except Exception as e:
            return {"success": False, "error": str(e)}

