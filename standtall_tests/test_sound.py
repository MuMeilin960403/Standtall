from __future__ import annotations

import sys
import wave

import pytest

from standtall.services.sound import ChimePlayer, ensure_chime, synthesise_chime


def test_synthesised_chime_is_valid_wav(tmp_path):
    path = synthesise_chime(tmp_path / "chime.wav")
    assert path.is_file()
    assert path.stat().st_size > 10_000
    with wave.open(str(path), "rb") as audio:
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
        assert audio.getframerate() == 22_050
        frames = audio.readframes(audio.getnframes())
        assert len(frames) > 0
        assert max(frames) > 0


def test_ensure_regenerates_missing_file(tmp_path):
    path = tmp_path / "chime.wav"
    path.write_bytes(b"too small")
    assert ensure_chime(path) == path
    assert path.stat().st_size > 10_000


def test_disabled_sound_does_not_create_file(tmp_path):
    player = ChimePlayer(tmp_path / "chime.wav")
    assert player.play(False) is False
    assert not player.path.exists()


def test_play_off_windows_is_safe(tmp_path, monkeypatch):
    player = ChimePlayer(tmp_path / "chime.wav")
    monkeypatch.setattr(sys, "platform", "linux")
    assert player.play(True) is False
