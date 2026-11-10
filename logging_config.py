"""Application logging configuration."""

import logging
import sys


def setup_logging() -> None:
    """Send INFO-and-above logs to the console."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
