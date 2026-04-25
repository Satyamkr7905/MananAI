"""Environment-driven settings for the API server (separate from ``app.config``)."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_AGENT_ROOT = Path(__file__).resolve().parent.parent
_log = logging.getLogger(__name__)

# Historical default that shipped in repo docs/templates — treated as
# "unset" so we never start a production server trusting this value.
_INSECURE_JWT_DEFAULTS: frozenset[str] = frozenset(
    {
        "",
        "change-me-in-production-use-openssl-rand-hex-32",
        "generate-a-long-random-string",
        "your-secret",
        "secret",
        "dev",
    }
)


def _default_postgres_url() -> str:
    """Local dev default; override with ``DATABASE_URL`` in ``.env``."""
    return "postgresql+psycopg://adaptive:adaptive@127.0.0.1:5432/adaptive_dsa_tutor"


class ApiSettings(BaseSettings):
    """Load from ``.env`` in the project root (``adaptive_dsa_agent/.env``)."""

    # ``dev`` relaxes production safety rails (allows default JWT secret and
    # returns the OTP in the /send-otp response when SMTP isn't configured).
    # ``prod`` is strict and refuses to start with an insecure secret.
    app_env: str = "dev"

    # SQLAlchemy URL. For PostgreSQL use postgresql+psycopg:// (requires psycopg3).
    # For SQLite, set e.g. sqlite:///./data/tutor_api.db
    database_url: str = Field(default_factory=_default_postgres_url)
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Google Sign-In (GIS) — Web client ID from Google Cloud Console
    google_client_id: str = ""

    # Gmail SMTP (for OTP). Use an App Password: https://support.google.com/accounts/answer/185833
    # Use port 465 (implicit SSL) if your network blocks STARTTLS on 587.
    gmail_smtp_host: str = "smtp.gmail.com"
    gmail_smtp_port: int = 587
    gmail_smtp_timeout_seconds: int = 20
    gmail_user: str = ""  # your@gmail.com
    gmail_app_password: str = ""  # 16-char app password, not your login password

    otp_ttl_minutes: int = 10

    # Brute-force protection on /verify-otp. A single OTP is invalidated after
    # this many wrong attempts (the user must request a fresh code).
    otp_max_attempts: int = 5

    # Rate limiting (in-process, per-email) for /send-otp. Requests beyond
    # this window return 429. This is a best-effort shield — behind a reverse
    # proxy you should also have IP-level limits.
    otp_send_cooldown_seconds: int = 30
    otp_send_daily_max: int = 20

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(
        env_file=str(_AGENT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("app_env")
    @classmethod
    def _norm_env(cls, v: str) -> str:
        v = (v or "").strip().lower()
        return v if v in {"dev", "prod", "test"} else "dev"

    def is_prod(self) -> bool:
        return self.app_env == "prod"

    def jwt_secret_is_insecure(self) -> bool:
        s = (self.jwt_secret or "").strip()
        return s in _INSECURE_JWT_DEFAULTS or len(s) < 32


@lru_cache
def get_api_settings() -> ApiSettings:
    s = ApiSettings()
    if s.jwt_secret_is_insecure():
        msg = (
            "JWT_SECRET is unset or insecure (must be a random string of at "
            "least 32 chars — e.g. `python -c \"import secrets;print(secrets.token_hex(32))\"`)."
        )
        if s.is_prod():
            # Fail closed in production — a known/short secret lets anyone
            # forge admin tokens.
            raise RuntimeError(msg)
        _log.warning("%s Running in APP_ENV=dev so we'll continue, but do NOT deploy this.", msg)
    return s


def cors_list() -> list[str]:
    """Return the allow-list for CORS. Strips the '*' wildcard which is unsafe
    when combined with ``allow_credentials=True``."""
    raw = get_api_settings().cors_origins
    items = [o.strip() for o in raw.split(",") if o.strip()]
    safe = [o for o in items if o != "*"]
    if len(safe) != len(items):
        _log.warning(
            "CORS_ORIGINS contained '*' — ignored. Credentialed CORS requires an explicit origin list."
        )
    return safe
