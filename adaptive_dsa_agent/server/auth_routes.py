"""Auth: OTP email, Google ID token, JWT issuance."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete
from sqlalchemy.orm import Session

from .database import get_session
from .deps import ensure_learning_row
from .email_service import SmtpNotConfiguredError, send_otp_email
from .models import OtpCode, User
from .security import (
    create_access_token,
    generate_otp_digits,
    hash_otp,
    hash_password,
    otp_hashes_equal,
    verify_password,
)
from .settings import get_api_settings

log = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

# In-process brute-force / abuse shields. These reset on restart, which is
# acceptable for this app — a real deployment should additionally put a
# rate-limiter (nginx, Cloudflare, slowapi, etc.) in front.
_VERIFY_ATTEMPTS: dict[str, int] = {}
_SEND_HISTORY: dict[str, deque[float]] = {}
_RATE_LOCK = threading.Lock()


def _verify_attempts_key(email: str, code_hash: str) -> str:
    # Bucket attempts to the specific outstanding OTP so a fresh /send-otp
    # naturally clears the counter (the hash changes on every code).
    return f"{email}:{code_hash}"


def _check_send_rate(email: str) -> None:
    """Raise 429 if this email is sending OTPs too aggressively."""
    s = get_api_settings()
    now = time.time()
    with _RATE_LOCK:
        hist = _SEND_HISTORY.setdefault(email, deque())
        # Drop entries older than 24h
        cutoff = now - 86400
        while hist and hist[0] < cutoff:
            hist.popleft()
        if hist and (now - hist[-1]) < s.otp_send_cooldown_seconds:
            retry_in = int(s.otp_send_cooldown_seconds - (now - hist[-1]))
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {max(1, retry_in)}s before requesting another code.",
            )
        if len(hist) >= s.otp_send_daily_max:
            raise HTTPException(
                status_code=429,
                detail="Too many sign-in codes requested for this email today. Try again tomorrow.",
            )
        hist.append(now)


class SendOtpBody(BaseModel):
    email: EmailStr


class VerifyOtpBody(BaseModel):
    email: EmailStr
    otp: str


class GoogleBody(BaseModel):
    credential: str


class SignupBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=80)


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


def _user_response(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "name": u.name or u.email.split("@")[0],
        "joinedAt": u.created_at.isoformat() if u.created_at else datetime.now(timezone.utc).isoformat(),
    }


def _issue(user: User) -> dict:
    token = create_access_token(sub=user.id, email=user.email)
    return {"token": token, "user": _user_response(user)}


def _as_utc(dt: datetime) -> datetime:
    """Treat tz-naive datetimes as UTC. SQLite drops tzinfo on read."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _issue_otp(db: Session, email: str) -> tuple[str, str, str | None]:
    """Create + persist a fresh OTP for ``email`` and try to deliver it.

    Returns ``(message, delivery, dev_code_or_None)`` — callers embed the
    three values into their HTTP response.
    """
    settings_ = get_api_settings()
    code = generate_otp_digits()
    chash = hash_otp(email, code)
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings_.otp_ttl_minutes)

    db.execute(delete(OtpCode).where(OtpCode.email == email))
    db.add(OtpCode(email=email, code_hash=chash, expires_at=exp))
    db.commit()

    try:
        send_otp_email(email, code)
        return "OTP sent to your email.", "smtp", None
    except SmtpNotConfiguredError:
        log.warning("SMTP not configured; OTP for %s is %s (dev only)", email, code)
        if settings_.is_prod():
            return (
                "Email delivery is not configured. Ask an administrator to set "
                "GMAIL_USER and GMAIL_APP_PASSWORD in the server environment.",
                "dev_inline",
                None,
            )
        return (
            "SMTP is not configured (APP_ENV=dev). Use the one-time code "
            "shown in the app to sign in.",
            "dev_inline",
            code,
        )
    except Exception as exc:
        log.exception("Failed to send OTP email")
        raise HTTPException(
            status_code=500,
            detail="Could not send the sign-in code right now. Please try again.",
        ) from exc


@router.post("/send-otp")
def send_otp(body: SendOtpBody, db: Session = Depends(get_session)):
    """Passwordless / account-recovery magic-link flow. Independent of /signup."""
    email = body.email.strip().lower()
    _check_send_rate(email)
    msg, delivery, dev_code = _issue_otp(db, email)
    out: dict = {"ok": True, "message": msg, "email": email, "delivery": delivery}
    if dev_code is not None:
        out["devCode"] = dev_code
    return out


@router.post("/signup")
def signup(body: SignupBody, db: Session = Depends(get_session)):
    """Start an email+password account. Sends an OTP to prove email ownership.

    - If the email is unknown → create an unverified user w/ password_hash, send OTP.
    - If the email exists but is unverified → update the password_hash, resend OTP.
    - If the email exists and IS verified → 409 (ask them to log in or reset).
    """
    email = body.email.strip().lower()

    # Fast-path the "already signed up" case before rate-limiting so legitimate
    # returning users get a clear "please sign in" instead of "too many requests".
    user = db.query(User).filter(User.email == email).first()
    if user and getattr(user, "email_verified", False) and user.password_hash:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists. Please sign in.",
        )

    _check_send_rate(email)
    pwd_hash = hash_password(body.password)
    name = (body.name or "").strip() or email.split("@")[0]
    if user is None:
        user = User(email=email, name=name, password_hash=pwd_hash, email_verified=False)
        db.add(user)
    else:
        user.name = user.name or name
        user.password_hash = pwd_hash
        user.email_verified = False
        db.add(user)
    db.commit()

    msg, delivery, dev_code = _issue_otp(db, email)
    out: dict = {
        "ok": True,
        "message": "Account created. " + msg,
        "email": email,
        "delivery": delivery,
    }
    if dev_code is not None:
        out["devCode"] = dev_code
    return out


@router.post("/signup/verify")
def signup_verify(body: VerifyOtpBody, db: Session = Depends(get_session)):
    """Complete signup: check the OTP, mark email_verified, issue JWT."""
    email = body.email.strip().lower()
    code = (body.otp or "").strip()

    if not code.isdigit() or not (4 <= len(code) <= 10):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    row = db.query(OtpCode).filter(OtpCode.email == email).order_by(OtpCode.id.desc()).first()
    if row is None or _as_utc(row.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="OTP expired or not found")

    settings_ = get_api_settings()
    attempts_key = _verify_attempts_key(email, row.code_hash)
    with _RATE_LOCK:
        attempts = _VERIFY_ATTEMPTS.get(attempts_key, 0)
    if attempts >= settings_.otp_max_attempts:
        db.delete(row)
        db.commit()
        with _RATE_LOCK:
            _VERIFY_ATTEMPTS.pop(attempts_key, None)
        raise HTTPException(
            status_code=429,
            detail="Too many incorrect attempts. Please request a new code.",
        )

    if not otp_hashes_equal(row.code_hash, hash_otp(email, code)):
        with _RATE_LOCK:
            _VERIFY_ATTEMPTS[attempts_key] = attempts + 1
        raise HTTPException(status_code=401, detail="Invalid OTP")

    db.delete(row)
    with _RATE_LOCK:
        _VERIFY_ATTEMPTS.pop(attempts_key, None)

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        # Edge case: signup row was wiped but OTP still present.
        raise HTTPException(status_code=400, detail="Please start signup again.")
    user.email_verified = True
    db.add(user)
    db.commit()
    db.refresh(user)
    ensure_learning_row(db, user)
    return _issue(user)


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_session)):
    """Password login. Only works for accounts that completed /signup/verify."""
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    # Uniform-latency failure: always run the bcrypt verify even when the user
    # doesn't exist, so attackers can't distinguish "unknown email" from
    # "wrong password" via timing.
    stored = user.password_hash if user else None
    ok_password = verify_password(body.password, stored)

    if not user or not ok_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.password_hash:
        raise HTTPException(
            status_code=401,
            detail="This account has no password set. Use 'Email me a code' to sign in.",
        )
    if not getattr(user, "email_verified", False):
        raise HTTPException(
            status_code=403,
            detail="Please verify your email. Check your inbox for the one-time code.",
        )

    ensure_learning_row(db, user)
    return _issue(user)


@router.post("/verify-otp")
def verify_otp(body: VerifyOtpBody, db: Session = Depends(get_session)):
    email = body.email.strip().lower()
    code = (body.otp or "").strip()

    # Defense in depth: numeric-only, fixed-length. An attacker who can send
    # arbitrary bodies (e.g. long strings) shouldn't even reach the hash step.
    if not code.isdigit() or not (4 <= len(code) <= 10):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    row = db.query(OtpCode).filter(OtpCode.email == email).order_by(OtpCode.id.desc()).first()
    if row is None or _as_utc(row.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="OTP expired or not found")

    settings_ = get_api_settings()
    attempts_key = _verify_attempts_key(email, row.code_hash)

    # Invalidate the code after too many wrong tries (brute-force defense:
    # 6-digit OTP = 10^6 values, so 5 attempts ≈ 5e-6 probability per code).
    with _RATE_LOCK:
        attempts = _VERIFY_ATTEMPTS.get(attempts_key, 0)
    if attempts >= settings_.otp_max_attempts:
        db.delete(row)
        db.commit()
        with _RATE_LOCK:
            _VERIFY_ATTEMPTS.pop(attempts_key, None)
        raise HTTPException(
            status_code=429,
            detail="Too many incorrect attempts. Please request a new code.",
        )

    expected = hash_otp(email, code)
    if not otp_hashes_equal(row.code_hash, expected):
        with _RATE_LOCK:
            _VERIFY_ATTEMPTS[attempts_key] = attempts + 1
        raise HTTPException(status_code=401, detail="Invalid OTP")

    # Success — consume the OTP and clear the attempt counter.
    db.delete(row)
    db.commit()
    with _RATE_LOCK:
        _VERIFY_ATTEMPTS.pop(attempts_key, None)

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email, name=email.split("@")[0], email_verified=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not getattr(user, "email_verified", False):
        user.email_verified = True
        db.add(user)
        db.commit()
        db.refresh(user)
    ensure_learning_row(db, user)
    return _issue(user)


@router.post("/auth/google")
def auth_google(body: GoogleBody, db: Session = Depends(get_session)):
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    cid = get_api_settings().google_client_id
    if not cid:
        raise HTTPException(status_code=503, detail="Google Sign-In is not configured on the server")

    try:
        info = google_id_token.verify_oauth2_token(
            body.credential,
            google_requests.Request(),
            cid,
        )
    except ValueError as exc:
        # Log the detail; return a generic message so we don't leak internals.
        log.warning("Google token verification failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid Google credential") from exc

    # Google's library already verifies signature, audience and expiry. We
    # additionally enforce: (1) a trusted issuer, (2) verified email — without
    # these, an attacker with an unverified Google account claiming any email
    # could impersonate users.
    iss = info.get("iss")
    if iss not in ("https://accounts.google.com", "accounts.google.com"):
        raise HTTPException(status_code=401, detail="Invalid Google credential")
    if not info.get("email_verified", False):
        raise HTTPException(status_code=401, detail="Google email is not verified")

    email = (info.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Google token missing email")

    sub = info.get("sub")
    name = info.get("name") or email.split("@")[0]
    picture = info.get("picture")

    user = None
    if sub:
        user = db.query(User).filter(User.google_sub == sub).first()
    if user is None:
        user = db.query(User).filter(User.email == email).first()

    if user is None:
        user = User(email=email, name=name, picture=picture, google_sub=sub)
        db.add(user)
        db.commit()
        db.refresh(user)
        ensure_learning_row(db, user)
    else:
        user.name = name or user.name
        user.picture = picture or user.picture
        if sub and not user.google_sub:
            user.google_sub = sub
        db.add(user)
        db.commit()
        db.refresh(user)

    return _issue(user)
