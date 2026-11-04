from __future__ import annotations

from standtall.services import paths


def test_data_dir_uses_environment_override(monkeypatch, tmp_path):
    target = tmp_path / "custom-data"
    monkeypatch.setenv("STANDTALL_DATA_DIR", str(target))
    paths._CACHED_DATA_DIR = None  # noqa: SLF001 - deliberate test reset
    try:
        assert paths.data_dir() == target
        assert target.is_dir()
        assert (target / ".write-probe").exists() is False
    finally:
        paths._CACHED_DATA_DIR = None  # noqa: SLF001


def test_data_dir_caches_result(monkeypatch, tmp_path):
    target = tmp_path / "cached-data"
    monkeypatch.setenv("STANDTALL_DATA_DIR", str(target))
    paths._CACHED_DATA_DIR = None  # noqa: SLF001
    try:
        first = paths.data_dir()
        monkeypatch.setenv("STANDTALL_DATA_DIR", str(tmp_path / "other"))
        assert paths.data_dir() == first
    finally:
        paths._CACHED_DATA_DIR = None  # noqa: SLF001
