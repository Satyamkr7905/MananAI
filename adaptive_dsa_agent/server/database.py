# SQLAlchemy engine + session factory + light additive migrations.

from __future__ import annotations

import logging
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base
from .settings import get_api_settings

log = logging.getLogger(__name__)


def _ensure_sqlite_parent(url: str) -> None:
    if not url.startswith("sqlite"):
        return
    # sqlite:///relative/path or sqlite:////C:/abs/path
    path = url.split("sqlite:///", 1)[-1].lstrip("/")
    if path and path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)


def _normalize_pg_url(url: str) -> str:
    # force SQLAlchemy onto psycopg v3 for Postgres.
    # render/heroku/neon hand out `postgres://` or `postgresql://` URLs and
    # SQLAlchemy picks psycopg2 by default — which we don't install, so it
    # crashes on boot. rewriting to `postgresql+psycopg://` picks v3 explicitly.
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg" not in url.split("://", 1)[0]:
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


_url = _normalize_pg_url(get_api_settings().database_url)
_ensure_sqlite_parent(_url)

_engine_kw: dict = {"pool_pre_ping": True}
if "sqlite" in _url:
    _engine_kw["connect_args"] = {"check_same_thread": False}
else:
    _engine_kw.setdefault("pool_size", 5)
    _engine_kw.setdefault("max_overflow", 10)

engine = create_engine(_url, **_engine_kw)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# tiny additive "migrations" so adding a column to an existing dev DB
# doesn't need a drop+recreate. only runs DDL if the column is missing.
# types kept loose (VARCHAR / BOOLEAN) so it works on both sqlite and pg.
# not a replacement for alembic in real prod.
_ADDITIVE_MIGRATIONS: list[tuple[str, str, str]] = [
    # (table, column, ddl_type)
    ("users", "password_hash", "VARCHAR(255)"),
    ("users", "email_verified", "BOOLEAN"),
]


def _run_additive_migrations(eng: Engine) -> None:
    try:
        insp = inspect(eng)
    except Exception as exc:  # pragma: no cover
        log.warning("DB inspector unavailable, skipping additive migrations: %s", exc)
        return
    if not insp.has_table("users"):
        return  # table will be made by metadata.create_all
    existing = {c["name"] for c in insp.get_columns("users")}
    with eng.begin() as conn:
        for table, column, ddl_type in _ADDITIVE_MIGRATIONS:
            if table != "users" or column in existing:
                continue
            default_clause = ""
            if column == "email_verified":
                # backfill old rows as verified — legacy OTP-only users
                # shouldn't get locked out by the new signup flow.
                default_clause = " DEFAULT TRUE"
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}{default_clause}"))
                log.info("Migrated: added %s.%s", table, column)
            except Exception as exc:  # noqa: BLE001 - dialect-dependent errors
                log.warning("Could not add column %s.%s (%s) — continuing.", table, column, exc)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _run_additive_migrations(engine)


def get_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
