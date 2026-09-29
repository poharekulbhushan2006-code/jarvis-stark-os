"""
Automated Test Suite for J.A.R.V.I.S. Core
"""

import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.system_control import SystemController
from core.voice import voice_engine
from core.brain import jarvis_brain

def test_system_controller():
    print("\n--- [1] Testing SystemController ---")
    # Volume
    vol = SystemController.get_volume()
    print(f"[*] Initial Volume: {vol}%")
    res = SystemController.set_volume(50)
    assert res["success"] is True, f"Failed to set volume: {res}"
    print(f"[+] Volume test passed: {res}")

    # Brightness
    bright = SystemController.get_brightness()
    print(f"[*] Display Brightness: {bright}%")

    # Battery
    batt = SystemController.get_battery_status()
    print(f"[*] Battery: {batt['status_text']}")
    assert "percent" in batt, "Battery test failed"
    print(f"[+] Battery test passed.")

    # Time/Date
    td = SystemController.get_current_time_date()
    print(f"[*] Time/Date: {td['message']}")
    assert "time" in td and "date" in td, "Time/date test failed"
    print(f"[+] Time/Date test passed.")

    # Notes
    note_res = SystemController.save_note("Unit test verification note", "test_note")
    print(f"[*] Note Saved: {note_res['filename']}")
    notes = SystemController.list_notes()
    assert len(notes["notes"]) > 0, "Note list test failed"
    print(f"[+] Notes test passed ({len(notes['notes'])} notes found).")

    # Telemetry
    telemetry = SystemController.get_system_telemetry()
    print(f"[*] Telemetry: CPU={telemetry['cpu_percent']}%, RAM={telemetry['ram_percent']}%, Disk Free={telemetry['disk_free_gb']}GB")
    assert "cpu_percent" in telemetry and "ram_percent" in telemetry
    print(f"[+] Telemetry test passed.")

    # Media Controls
    media_res = SystemController.play_pause_media()
    assert media_res.get("success") is True
    print(f"[+] Media key test passed: {media_res['message']}")

    # Clipboard
    SystemController.set_clipboard_text("Stark Industries Jarvis Test")
    clip = SystemController.get_clipboard_text()
    assert "Stark Industries" in clip.get("text", "")
    print(f"[+] Clipboard test passed: {clip['preview']}")

    # Screen Capture for Analysis
    cap = SystemController.capture_for_analysis()
    assert cap.get("success") is True and "base64" in cap
    print(f"[+] Screen capture for vision analysis passed.")

def test_voice_engine():
    print("\n--- [2] Testing VoiceEngine (Edge-TTS) ---")
    audio_path = voice_engine.synthesize("Jarvis diagnostic test complete, Sir.")
    assert audio_path.exists(), f"Audio file not found at {audio_path}"
    assert audio_path.stat().st_size > 0, "Audio file is empty"
    print(f"[+] Voice synthesis passed. Generated {audio_path.name} ({audio_path.stat().st_size} bytes)")

async def test_brain():
    print("\n--- [3] Testing JarvisBrain Intent Processing ---")
    test_queries = [
        ("what is my battery level", "BATTERY"),
        ("set volume to 65", "VOLUME_SET"),
        ("what time is it", "TIME"),
        ("system check", "STATUS"),
        ("who are you", "IDENTITY"),
        ("pause music", "MEDIA_PLAY_PAUSE"),
        ("next track", "MEDIA_NEXT"),
        ("read my clipboard", "CLIPBOARD_READ"),
    ]

    for query, expected_action in test_queries:
        res = await jarvis_brain.process_command(query)
        print(f"[*] Query: '{query}' -> Action: {res.get('action')} | Audio: {res.get('audio_url')}")
        print(f"    Jarvis: \"{res.get('text')}\"")
        assert res.get("action") == expected_action, f"Expected {expected_action}, got {res.get('action')}"
        assert res.get("audio_url") is not None, "Audio URL was not generated"

    print("[+] All brain intent tests passed successfully!")

async def test_security_and_offline():
    print("\n--- [4] Testing Security Guardrails, Biometrics & DPAPI Vault ---")
    from core.guardrails import guardrails, AUDIT_LOG_PATH
    from core.biometrics import voice_biometrics, extract_mfcc_voiceprint
    from core.unlocker import LockScreenUnlocker
    import numpy as np

    # A. Guardrails Hard Blacklist Test
    is_allowed, action, msg = guardrails.evaluate_command("format c: /fs:NTFS")
    assert is_allowed is False, "Dangerous format command was not blocked!"
    assert action == "SECURITY_ALERT"
    print(f"[+] Blacklist Test Passed: 'format c:' blocked with reason: {msg}")

    # B. Elevated Command Unauthorized Voice Test
    is_allowed_del, action_del, msg_del = guardrails.evaluate_command("delete system files", is_boss_voice=False, voice_similarity=0.4)
    assert is_allowed_del is False, "Elevated command without Boss voice was not blocked!"
    assert action_del == "ACCESS_DENIED"
    print(f"[+] Biometric Gate Test Passed: Elevated command rejected for unauthorized voice ({msg_del})")

    # C. Audit Log Verification
    assert AUDIT_LOG_PATH.exists(), "Audit log was not written!"
    log_content = AUDIT_LOG_PATH.read_text(encoding="utf-8")
    assert "BLACKLIST_VIOLATION" in log_content
    print(f"[+] Tamper-Evident Audit Log Test Passed (Contains logged security events)")

    # D. Biometrics MFCC Feature Extraction Test
    dummy_audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 22050)).astype(np.float32)
    voice_vec = extract_mfcc_voiceprint(dummy_audio)
    assert voice_vec is not None, "MFCC voiceprint extraction failed"
    assert len(voice_vec) == 32, f"Expected 32-dim voice vector, got {len(voice_vec)}"
    print(f"[+] Voice Biometrics Test Passed: 32-dimensional acoustic voiceprint generated successfully")

    # E. DPAPI Workstation Lock Check
    is_locked = LockScreenUnlocker.is_workstation_locked()
    print(f"[*] Current Workstation Lock State: {'LOCKED' if is_locked else 'UNLOCKED'}")
    assert isinstance(is_locked, bool)

    # F. Offline SAPI5 Voice Fallback Test
    sapi_path = voice_engine._synthesize_sapi("Offline test Sir")
    assert sapi_path.exists() and sapi_path.stat().st_size > 0
    print(f"[+] SAPI5 100% Offline Voice Test Passed: Generated {sapi_path.name} ({sapi_path.stat().st_size} bytes)")

def main():
    print("====================================================")
    print("      RUNNING J.A.R.V.I.S. AUTOMATED TEST SUITE     ")
    print("====================================================")
    test_system_controller()
    test_voice_engine()
    asyncio.run(test_brain())
    asyncio.run(test_security_and_offline())
    print("\n====================================================")
    print("       ALL SYSTEM TESTS PASSED SUCCESSFULLY!        ")
    print("====================================================")

if __name__ == "__main__":
    main()

