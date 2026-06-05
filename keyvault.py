"""
keyvault.py - Encrypted key storage using Fernet (AES-128 + HMAC).

Provides encrypt/decrypt for sensitive values like VirusTotal API keys.
The encryption key is generated on first run and stored in keyvault.key (gitignored).
If the key file is lost, encrypted data cannot be recovered.

Used by: safety/virustotal.py (per-server VT API keys)
"""

import os
import base64

from cryptography.fernet import Fernet

KEY_FILE = "keyvault.key"


def _get_or_create_key() -> bytes:
    """Get the Fernet key from disk, or generate and save a new one.
    Uses exclusive create (xb) to prevent race conditions."""
    try:
        with open(KEY_FILE, "rb") as f:
            return f.read()
    except FileNotFoundError:
        pass
    try:
        key = Fernet.generate_key()
        with open(KEY_FILE, "xb") as f:
            f.write(key)
        return key
    except FileExistsError:
        with open(KEY_FILE, "rb") as f:
            return f.read()


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value. Returns base64-encoded ciphertext."""
    if not plaintext:
        return ""
    fernet = Fernet(_get_or_create_key())
    return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a previously encrypted value. Returns original plaintext."""
    if not ciphertext:
        return ""
    fernet = Fernet(_get_or_create_key())
    return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
