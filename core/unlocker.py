"""
J.A.R.V.I.S. Windows Lock Screen Security & Voice Unlocker
Manages DPAPI encrypted credential storage and automated workstation unlock.
Only triggers when Boss's voice biometric or verified trigger is confirmed.
"""

import os
import sys
import time
import ctypes
from pathlib import Path
from typing import Optional, Dict, Any

import win32crypt

BASE_DIR = Path(__file__).resolve().parent.parent
VAULT_PATH = BASE_DIR / "cache" / "auth.vault"
VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)

user32 = ctypes.windll.user32

# Virtual Key Codes
VK_SPACE = 0x20
VK_RETURN = 0x0D
VK_SHIFT = 0x10


class LockScreenUnlocker:
    """Handles secure credential storage via Windows DPAPI and lock screen automation."""

    @staticmethod
    def is_workstation_locked() -> bool:
        """Returns True if Windows is locked (Secure Desktop / Winlogon active)."""
        DESKTOP_SWITCHDESKTOP = 0x0100
        hdesk = user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
        if not hdesk:
            return True
        user32.CloseDesktop(hdesk)
        return False

    @staticmethod
    def save_password(password: str) -> bool:
        """Encrypts and securely saves the Windows lock screen password using DPAPI."""
        try:
            pw_bytes = password.encode("utf-8")
            encrypted = win32crypt.CryptProtectData(
                pw_bytes,
                "JarvisCredentialVault",
                None,
                None,
                None,
                0
            )
            VAULT_PATH.write_bytes(encrypted)
            print("[Vault] Password encrypted with Windows DPAPI and saved safely.")
            return True
        except Exception as e:
            print(f"[Vault] Failed to encrypt password: {e}")
            return False

    @staticmethod
    def has_stored_password() -> bool:
        """Returns True if a password vault exists on disk."""
        return VAULT_PATH.exists() and VAULT_PATH.stat().st_size > 0

    @staticmethod
    def get_password() -> Optional[str]:
        """Decrypts and retrieves the stored password using DPAPI."""
        if not LockScreenUnlocker.has_stored_password():
            return None
        try:
            encrypted = VAULT_PATH.read_bytes()
            decrypted = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1]
            return decrypted.decode("utf-8")
        except Exception as e:
            print(f"[Vault] Decryption failed: {e}")
            return None

    @staticmethod
    def _send_key(vk: int, is_shift: bool = False):
        """Simulates keypress and release with optional Shift modifier."""
        if is_shift:
            user32.keybd_event(VK_SHIFT, 0, 0, 0)
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.015)
        user32.keybd_event(vk, 0, 2, 0)  # KEYEVENTF_KEYUP = 2
        if is_shift:
            user32.keybd_event(VK_SHIFT, 0, 2, 0)
        time.sleep(0.015)

    @staticmethod
    def _type_string(text: str):
        """Types string into active input field using Windows virtual key mapping."""
        for char in text:
            # VkKeyScanW maps unicode character to virtual-key code and shift state
            vkey_info = user32.VkKeyScanW(ord(char))
            if vkey_info == -1:
                continue
            vk_code = vkey_info & 0xFF
            shift_state = (vkey_info >> 8) & 0xFF
            need_shift = (shift_state & 1) != 0
            LockScreenUnlocker._send_key(vk_code, is_shift=need_shift)

    @classmethod
    def unlock_workstation(cls) -> Dict[str, Any]:
        """Executes the lock screen unlock sequence using the encrypted DPAPI password."""
        if not cls.has_stored_password():
            return {
                "success": False,
                "message": "No lock screen password configured in DPAPI vault. Run setup_lockscreen.bat first."
            }

        password = cls.get_password()
        if not password:
            return {"success": False, "message": "Failed to decrypt lock screen password."}

        print("[Unlocker] Initiating Windows Lock Screen unlock sequence...")

        # 1. Wake screen & bring up password box
        user32.keybd_event(VK_SPACE, 0, 0, 0)
        user32.keybd_event(VK_SPACE, 0, 2, 0)
        time.sleep(0.6)

        # 2. Type password
        cls._type_string(password)
        time.sleep(0.1)

        # 3. Submit password (Enter key)
        user32.keybd_event(VK_RETURN, 0, 0, 0)
        user32.keybd_event(VK_RETURN, 0, 2, 0)
        time.sleep(0.5)

        return {
            "success": True,
            "message": "Password transmitted to Windows lock screen."
        }

    @staticmethod
    def lock_workstation() -> Dict[str, Any]:
        """Immediately locks the Windows workstation using user32.LockWorkStation."""
        try:
            success = user32.LockWorkStation() != 0
            return {
                "success": success,
                "message": "Workstation locked and display secured."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


unlocker = LockScreenUnlocker()
