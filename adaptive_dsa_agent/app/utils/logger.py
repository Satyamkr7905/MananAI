"""
Thin logging wrapper.

Keeps every module on the same configuration and avoids the repetition of
``logging.basicConfig`` all over the codebase.
"""

from __future__ import annotations

import logging
import sys

from ..config import settings


_CONFIGURED = False


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger with project-wide formatting applied once."""
    global _CONFIGURED
    if not _CONFIGURED:
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper(), logging.INFO),
            format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
            stream=sys.stdout,
        )
        _CONFIGURED = True
    return logging.getLogger(name)
