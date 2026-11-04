from __future__ import annotations

from PySide6.QtCore import QSettings

from standtall.services.settings import Settings


def make_settings(tmp_path) -> Settings:
    return Settings(QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat))


def test_defaults(tmp_path):
    settings = make_settings(tmp_path)
    assert settings.interval_minutes() == 30
    assert settings.sound_enabled() is True
    assert settings.break_reminder_enabled() is True
    assert settings.break_duration_minutes() == 5
    assert settings.break_interval_minutes() == 60
    assert settings.break_allow_close() is False
    assert settings.status_bar_enabled() is True
    assert settings.hide_hint_shown() is False


def test_persist_interval_sound_and_hint(tmp_path):
    settings = make_settings(tmp_path)
    settings.set_interval_minutes(45)
    settings.set_sound_enabled(False)
    settings.set_break_reminder_enabled(False)
    settings.set_break_duration_minutes(12)
    settings.set_break_interval_minutes(45)
    settings.set_break_allow_close(True)
    settings.set_status_bar_enabled(False)
    settings.mark_hide_hint_shown()

    reopened = make_settings(tmp_path)
    assert reopened.interval_minutes() == 45
    assert reopened.sound_enabled() is False
    assert reopened.break_reminder_enabled() is False
    assert reopened.break_duration_minutes() == 12
    assert reopened.break_interval_minutes() == 45
    assert reopened.break_allow_close() is True
    assert reopened.status_bar_enabled() is False
    assert reopened.hide_hint_shown() is True


def test_interval_is_clamped_on_read_and_write(tmp_path):
    settings = make_settings(tmp_path)
    settings.set_interval_minutes(600)
    assert settings.interval_minutes() == 240
    settings.set_interval_minutes(-4)
    assert settings.interval_minutes() == 1


def test_invalid_stored_value_falls_back(tmp_path):
    raw = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    raw.setValue("reminder/interval_minutes", "not-a-number")
    raw.sync()
    assert Settings(raw).interval_minutes() == 30
