"""
J.A.R.V.I.S. Secure Lock Screen Password Setup
Encrypts your Windows PIN/Password with Windows DPAPI so Jarvis can unlock your screen upon voice command.
"""

import sys
import getpass
from pathlib import Path

# Add project root
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.unlocker import LockScreenUnlocker
from core.voice import voice_engine

def main():
    print("=" * 60)
    print("   J.A.R.V.I.S. SECURE LOCK SCREEN CREDENTIAL VAULT   ")
    print("=" * 60)
    print("\nThis utility securely stores your Windows password or PIN into a")
    print("Windows DPAPI (Data Protection API) hardware-bound encrypted vault.")
    print("Your password is NEVER stored in plain text.")
    print("Jarvis will use this ONLY when you say 'Jarvis, unlock laptop' or clap twice.\n")

    pw1 = getpass.getpass("Enter your Windows lock screen password or PIN: ").strip()
    if not pw1:
        print("[!] No password entered. Aborted.")
        return

    pw2 = getpass.getpass("Confirm your Windows password or PIN: ").strip()
    if pw1 != pw2:
        print("[!] Passwords do not match. Aborted.")
        return

    success = LockScreenUnlocker.save_password(pw1)
    if success:
        print("\n" + "=" * 60)
        print("   ✅ PASSWORD ENCRYPTED & SAVED TO DPAPI VAULT!      ")
        print("=" * 60)
        print("[*] Storage: cache/auth.vault (AES-256 DPAPI Encrypted)")
        print("[*] Ready for voice unlock: Say 'Jarvis, unlock laptop'")

        try:
            audio = voice_engine.synthesize("Lock screen credentials secured in DPAPI vault, Sir.")
            voice_engine.play_audio_file(audio, non_blocking=True)
        except Exception:
            pass
    else:
        print("[!] Failed to encrypt credentials.")

if __name__ == "__main__":
    main()
