"""Soft chime synthesis and Windows playback."""

from __future__ import annotations

import logging
import math
import struct
import sys
import wave
from pathlib import Path

from standtall.services.paths import chime_path

log = logging.getLogger(__name__)
SAMPLE_RATE = 22_050
DURATION_SECONDS = 0.72


def synthesise_chime(target: Path) -> Path:
    """Create a gentle two-note bell without shipping an audio asset."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(SAMPLE_RATE * DURATION_SECONDS)
    note_one = 523.25
    note_two = 783.99
    frames = bytearray()
    for index in range(frame_count):
        t = index / SAMPLE_RATE
        envelope_one = math.exp(-6.5 * t) * (1 - math.exp(-80 * t))
        onset_two = max(0.0, t - 0.16)
        envelope_two = (
            math.exp(-6.5 * onset_two) * (1 - math.exp(-80 * onset_two))
            if t >= 0.16
            else 0.0
        )
        sample = 0.0
        sample += 0.20 * envelope_one * math.sin(2 * math.pi * note_one * t)
        sample += 0.06 * envelope_one * math.sin(2 * math.pi * note_one * 2.01 * t)
        sample += 0.13 * envelope_two * math.sin(2 * math.pi * note_two * onset_two)
        sample += 0.03 * envelope_two * math.sin(2 * math.pi * note_two * 2.01 * onset_two)
        fade = min(1.0, (frame_count - index) / 400.0)
        value = int(max(-1.0, min(1.0, sample * fade)) * 32767)
        frames.extend(struct.pack("<h", value))
    with wave.open(str(target), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(SAMPLE_RATE)
        audio.writeframes(bytes(frames))
    return target


def ensure_chime(target: Path | None = None) -> Path | None:
    path = Path(target) if target else chime_path()
    try:
        if not path.is_file() or path.stat().st_size < 1000:
            synthesise_chime(path)
    except OSError:
        log.warning("Could not prepare reminder chime", exc_info=True)
        return None
    return path


class ChimePlayer:
    """Plays the generated chime asynchronously; failures never block a reminder."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or chime_path()
        self._prepared = False

    @property
    def path(self) -> Path:
        return self._path

    def play(self, enabled: bool = True) -> bool:
        if not enabled:
            return False
        if sys.platform != "win32":
            return False
        try:
            import winsound
        except ImportError:
            return False
        if not self._prepared:
            if ensure_chime(self._path) is None:
                return False
            self._prepared = True
        try:
            winsound.PlaySound(
                str(self._path),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )
            return True
        except RuntimeError:
            log.warning("Could not play reminder chime", exc_info=True)
            return False
