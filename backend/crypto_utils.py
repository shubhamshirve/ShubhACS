"""
crypto_utils.py — Symmetric encryption for sensitive credential storage.

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the `cryptography` package.
The encryption key is derived from JWT_SECRET so no extra env var is needed
in most deployments. Set ENCRYPTION_KEY explicitly in production if you want
key-rotation independence from the JWT secret.

Backward-compatible: decrypt_value() gracefully falls back to plaintext
for any record that was stored before encryption was introduced.
"""
from cryptography.fernet import Fernet, InvalidToken
import os
import base64
import hashlib
import logging

logger = logging.getLogger(__name__)


def _build_fernet_key() -> bytes:
    """
    Build a 32-byte Fernet-compatible key.

    Priority:
      1. ENCRYPTION_KEY env var (must be a valid URL-safe base64 key, 44 chars)
      2. Derived from JWT_SECRET via SHA-256  (stable across restarts)
    """
    raw = os.environ.get("ENCRYPTION_KEY", "").strip()
    if raw:
        try:
            # Validate that it is a proper Fernet key
            Fernet(raw.encode())
            return raw.encode()
        except Exception:
            logger.warning("ENCRYPTION_KEY is set but is not a valid Fernet key; falling back to JWT_SECRET derivation.")

    jwt_secret = os.environ.get("JWT_SECRET", "dev-fallback-do-not-use-in-production")
    derived = hashlib.sha256(jwt_secret.encode()).digest()   # 32 bytes
    return base64.urlsafe_b64encode(derived)                 # 44-char Fernet key


def _fernet() -> Fernet:
    return Fernet(_build_fernet_key())


def encrypt_value(value: str) -> str:
    """
    Encrypt a plaintext string.  Returns a Fernet token string.
    Empty / None values are returned unchanged.
    """
    if not value:
        return value
    return _fernet().encrypt(value.encode()).decode()


def decrypt_value(value: str) -> str:
    """
    Decrypt a Fernet token back to plaintext.

    If the value is NOT a valid Fernet token (e.g. a legacy plaintext record),
    it is returned as-is so existing data keeps working without a migration.
    """
    if not value:
        return value
    try:
        return _fernet().decrypt(value.encode()).decode()
    except (InvalidToken, Exception):
        # Not encrypted — legacy plaintext record; return as-is
        return value


def mask_credential(value: str, visible: int = 4) -> str:
    """
    Return a masked version of a credential for safe display in API responses.
    Shows the first `visible` characters and replaces the rest with ****
    """
    if not value:
        return ""
    plain = decrypt_value(value)   # decrypt first so we mask the real value
    if len(plain) <= visible:
        return "****"
    return plain[:visible] + "****"
