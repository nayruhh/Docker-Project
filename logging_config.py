"""Application logging configuration.

Console: readable logs at LOG_LEVEL (default INFO).
File:    logs/app.log, always captures DEBUG and above, rotated at 1 MB (3 backups).
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_FILE = LOG_DIR / "app.log"


def _resolve_level(value: str | None, default: int = logging.INFO) -> int:
    """Turn a level name like 'debug' into a logging level, falling back to default."""
    level = logging.getLevelName((value or "").upper())
    return level if isinstance(level, int) else default


def setup_logging() -> None:
    """Configure the root logger with a console handler and a rotating file handler."""
    console_level = _resolve_level(os.getenv("LOG_LEVEL"))
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(console_level)
    console.setFormatter(formatter)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # handlers decide what is actually emitted
    for old in root.handlers[:]:  # avoid duplicate lines if called twice
        root.removeHandler(old)
        old.close()
    root.addHandler(console)
    root.addHandler(file_handler)

    # Keep third-party libraries from flooding the logs with debug noise
    for noisy in ("httpx", "httpcore", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
