"""Filesystem locations used by the app."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

APP_FOLDER = "StandTall"
_CACHED_DATA_DIR: Path | None = None


def _candidate_paths() -> list[Path]:
    candidates: list[Path] = []
    override = os.environ.get("STANDTALL_DATA_DIR")
    if override:
        candidates.append(Path(override).expanduser())
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(Path(local) / APP_FOLDER)
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parents[2]
    candidates.append(base / "StandTallData")
    candidates.append(Path(tempfile.gettempdir()) / APP_FOLDER)
    return candidates


def _is_writable(path: Path) -> bool:
    probe = path / ".write-probe"
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def data_dir() -> Path:
    """Return the first writable data folder.

    Normal installs use LOCALAPPDATA. Portable copies on machines where that
    directory is unavailable fall back to a folder next to the executable.
    """
    global _CACHED_DATA_DIR
    if _CACHED_DATA_DIR is not None:
        return _CACHED_DATA_DIR
    candidates = _candidate_paths()
    for candidate in candidates:
        if _is_writable(candidate):
            _CACHED_DATA_DIR = candidate
            return candidate
    # Keep the app alive even in a fully read-only setup; callers that write
    # logs or audio handle their own I/O errors.
    _CACHED_DATA_DIR = candidates[0] if candidates else Path.cwd()
    return _CACHED_DATA_DIR


def logs_dir() -> Path:
    path = data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def chime_path() -> Path:
    return data_dir() / "chime.wav"
