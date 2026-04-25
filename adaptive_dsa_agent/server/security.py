"""JWT helpers and OTP hashing."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from .settings import get_api_settings


def hash_password(plain: str) -> str:
    """bcrypt hash of a password. Truncates to 72 bytes (bcrypt's input limit)."""
    import bcrypt

    pw = (plain or "").encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str | None) -> bool:
    """Constant-time bcrypt verify. False for missing/invalid hashes."""
    import bcrypt

    if not hashed:
        return False
    try:
        return bcrypt.checkpw((plain or "").encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def hash_otp(email: str, code: str) -> str:
    """Peppered SHA-256 of an OTP. The pepper is the server JWT secret so
    stolen DB rows are useless without the secret."""
    pepper = get_api_settings().jwt_secret
    raw = f"{pepper}:{email.strip().lower()}:{code}".encode()
    return hashlib.sha256(raw).hexdigest()


def otp_hashes_equal(a: str, b: str) -> bool:
    """Constant-time comparison of two OTP hash hex strings."""
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    return hmac.compare_digest(a, b)


def generate_otp_digits() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def create_access_token(*, sub: str, email: str) -> str:
    s = get_api_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=s.jwt_expire_minutes)
    payload = {
        "sub": sub,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_token(token: str) -> dict:
    s = get_api_settings()
    return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])


def safe_decode(token: str) -> dict | None:
    # Catch JWTError for signature/format issues and everything else for
    # defensive reasons (bytes, wrong type, etc.) — never let malformed
    # input from the wire crash an auth dependency.
    try:
        return decode_token(token)
    except (JWTError, ValueError, TypeError):
        return None
