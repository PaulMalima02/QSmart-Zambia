"""
Field-level encryption at rest for sensitive values (phone).
Uses Fernet; key from env FIELD_ENCRYPTION_KEY or derived from SECRET_KEY.
Transit encryption = HTTPS (terminate at reverse proxy in production).
"""
import base64
import hashlib
import os
from functools import lru_cache


@lru_cache(maxsize=1)
def _fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return None
    key = os.environ.get('FIELD_ENCRYPTION_KEY', '').strip()
    if not key:
        # Derive stable key from SECRET_KEY (dev); set FIELD_ENCRYPTION_KEY in production
        secret = os.environ.get('SECRET_KEY', 'dev-only-change-in-production-qsmart-zm')
        dig = hashlib.sha256(secret.encode()).digest()
        key = base64.urlsafe_b64encode(dig)
    else:
        if len(key) != 44:
            dig = hashlib.sha256(key.encode()).digest()
            key = base64.urlsafe_b64encode(dig)
        else:
            key = key.encode() if isinstance(key, str) else key
    return Fernet(key)


def encrypt_value(plain):
    if plain is None or plain == '':
        return plain
    f = _fernet()
    if f is None:
        return plain  # cryptography not installed
    token = f.encrypt(str(plain).encode())
    return 'enc:' + token.decode()


def decrypt_value(stored):
    if not stored or not str(stored).startswith('enc:'):
        return stored
    f = _fernet()
    if f is None:
        return stored
    try:
        return f.decrypt(str(stored)[4:].encode()).decode()
    except Exception:
        return stored
