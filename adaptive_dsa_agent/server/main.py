"""FastAPI entrypoint: CORS, auth, tutor routes."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .auth_routes import router as auth_router
from .database import init_db
from .settings import cors_list, get_api_settings
from .tutor_routes import router as tutor_router

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Force settings validation on startup so misconfiguration (e.g. insecure
    # JWT secret in prod) fails fast instead of silently booting.
    get_api_settings()
    init_db()
    yield


app = FastAPI(title="Adaptive DSA Tutor API", lifespan=lifespan)

_origins = cors_list()
if not _origins:
    log.warning("CORS_ORIGINS produced an empty allow-list — browsers will block the app.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    # Only the headers we actually use — avoids reflecting arbitrary request
    # headers back to the browser in preflights.
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


@app.middleware("http")
async def _security_headers(request: Request, call_next) -> Response:
    """Conservative security headers for JSON API responses."""
    resp: Response = await call_next(request)
    # These are cheap and safe for an API.
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    resp.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    return resp


@app.exception_handler(HTTPException)
async def http_message_handler(_request, exc: HTTPException):
    d = exc.detail
    msg = d if isinstance(d, str) else str(d)
    if isinstance(d, dict) and "message" in d:
        msg = d["message"]
    return JSONResponse(status_code=exc.status_code, content={"message": msg})


app.include_router(auth_router)
app.include_router(tutor_router)


@app.get("/health")
def health():
    return {"ok": True}
