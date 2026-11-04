"""Persisted user preferences. No secrets are involved in this app."""

from __future__ import annotations

from PySide6.QtCore import QSettings

ORGANIZATION = "StandTall"
APPLICATION = "StandTall"
DEFAULT_INTERVAL_MINUTES = 30
MIN_INTERVAL_MINUTES = 1
MAX_INTERVAL_MINUTES = 240
DEFAULT_BREAK_DURATION_MINUTES = 5
MIN_BREAK_DURATION_MINUTES = 1
MAX_BREAK_DURATION_MINUTES = 30
DEFAULT_BREAK_INTERVAL_MINUTES = 60
MIN_BREAK_INTERVAL_MINUTES = 5
MAX_BREAK_INTERVAL_MINUTES = 240


def clamp_interval(minutes: int) -> int:
    return min(max(int(minutes), MIN_INTERVAL_MINUTES), MAX_INTERVAL_MINUTES)


def clamp_break_interval(minutes: int) -> int:
    return min(
        max(int(minutes), MIN_BREAK_INTERVAL_MINUTES),
        MAX_BREAK_INTERVAL_MINUTES,
    )


def clamp_break_duration(minutes: int) -> int:
    return min(
        max(int(minutes), MIN_BREAK_DURATION_MINUTES),
        MAX_BREAK_DURATION_MINUTES,
    )


class Settings:
    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings(ORGANIZATION, APPLICATION)

    @property
    def raw(self) -> QSettings:
        return self._settings

    def interval_minutes(self) -> int:
        try:
            value = int(self._settings.value("reminder/interval_minutes", DEFAULT_INTERVAL_MINUTES))
        except (TypeError, ValueError):
            value = DEFAULT_INTERVAL_MINUTES
        return clamp_interval(value)

    def set_interval_minutes(self, minutes: int) -> None:
        self._settings.setValue("reminder/interval_minutes", clamp_interval(minutes))
        self._settings.sync()

    def sound_enabled(self) -> bool:
        return bool(self._settings.value("reminder/sound_enabled", True, type=bool))

    def set_sound_enabled(self, enabled: bool) -> None:
        self._settings.setValue("reminder/sound_enabled", bool(enabled))
        self._settings.sync()

    def break_reminder_enabled(self) -> bool:
        return bool(self._settings.value("reminder/break_enabled", True, type=bool))

    def set_break_reminder_enabled(self, enabled: bool) -> None:
        self._settings.setValue("reminder/break_enabled", bool(enabled))
        self._settings.sync()

    def break_duration_minutes(self) -> int:
        try:
            value = int(
                self._settings.value(
                    "reminder/break_duration_minutes",
                    DEFAULT_BREAK_DURATION_MINUTES,
                )
            )
        except (TypeError, ValueError):
            value = DEFAULT_BREAK_DURATION_MINUTES
        return clamp_break_duration(value)

    def set_break_duration_minutes(self, minutes: int) -> None:
        self._settings.setValue("reminder/break_duration_minutes", clamp_break_duration(minutes))
        self._settings.sync()

    def break_interval_minutes(self) -> int:
        try:
            value = int(
                self._settings.value(
                    "reminder/break_interval_minutes",
                    DEFAULT_BREAK_INTERVAL_MINUTES,
                )
            )
        except (TypeError, ValueError):
            value = DEFAULT_BREAK_INTERVAL_MINUTES
        return clamp_break_interval(value)

    def set_break_interval_minutes(self, minutes: int) -> None:
        self._settings.setValue("reminder/break_interval_minutes", clamp_break_interval(minutes))
        self._settings.sync()

    def break_allow_close(self) -> bool:
        return bool(self._settings.value("reminder/break_allow_close", False, type=bool))

    def set_break_allow_close(self, allowed: bool) -> None:
        self._settings.setValue("reminder/break_allow_close", bool(allowed))
        self._settings.sync()

    def status_bar_enabled(self) -> bool:
        return bool(self._settings.value("ui/status_bar_enabled", True, type=bool))

    def set_status_bar_enabled(self, enabled: bool) -> None:
        self._settings.setValue("ui/status_bar_enabled", bool(enabled))
        self._settings.sync()

    def hide_hint_shown(self) -> bool:
        return bool(self._settings.value("ui/hide_hint_shown", False, type=bool))

    def mark_hide_hint_shown(self) -> None:
        self._settings.setValue("ui/hide_hint_shown", True)
        self._settings.sync()
