"""Application logging configuration."""

import logging
import os
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _resolve_level(value: str | None, default: int = logging.INFO) -> int:
    """Turn a level name like 'debug' into a logging level, falling back to default."""
    level = logging.getLevelName((value or "").upper())
    return level if isinstance(level, int) else default


def setup_logging() -> None:
    """Send logs to the console. The level comes from the LOG_LEVEL env var (default INFO)."""
    level = _resolve_level(os.getenv("LOG_LEVEL"))

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()  # avoid duplicate lines if called twice
    root.addHandler(handler)
