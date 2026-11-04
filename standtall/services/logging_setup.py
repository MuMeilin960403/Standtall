"""Local logging for a small, private desktop utility."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from standtall.services.paths import logs_dir


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        handler = RotatingFileHandler(
            logs_dir() / "standtall.log",
            maxBytes=512_000,
            backupCount=2,
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)
    except OSError:
        # A reminder utility should still run if its data folder is unavailable.
        pass
    if sys.stderr is not None:
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(formatter)
        root.addHandler(stream)
