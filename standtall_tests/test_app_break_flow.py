from __future__ import annotations

import standtall.app as app_module
from standtall.app import StandTallApp


class FakeSettings:
    def __init__(self) -> None:
        self.interval = 30
        self.sound = False
        self.breaks = True
        self.hidden_hint = False
        self.break_duration = 5
        self.break_interval = 60
        self.allow_close = False
        self.status_bar = True

    def interval_minutes(self) -> int:
        return self.interval

    def sound_enabled(self) -> bool:
        return self.sound

    def break_reminder_enabled(self) -> bool:
        return self.breaks

    def break_duration_minutes(self) -> int:
        return self.break_duration

    def break_interval_minutes(self) -> int:
        return self.break_interval

    def break_allow_close(self) -> bool:
        return self.allow_close

    def status_bar_enabled(self) -> bool:
        return self.status_bar

    def set_interval_minutes(self, minutes: int) -> None:
        self.interval = minutes

    def set_sound_enabled(self, enabled: bool) -> None:
        self.sound = enabled

    def set_break_reminder_enabled(self, enabled: bool) -> None:
        self.breaks = enabled

    def set_break_duration_minutes(self, minutes: int) -> None:
        self.break_duration = minutes

    def set_break_interval_minutes(self, minutes: int) -> None:
        self.break_interval = minutes

    def set_break_allow_close(self, allowed: bool) -> None:
        self.allow_close = allowed

    def set_status_bar_enabled(self, enabled: bool) -> None:
        self.status_bar = enabled

    def hide_hint_shown(self) -> bool:
        return self.hidden_hint

    def mark_hide_hint_shown(self) -> None:
        self.hidden_hint = True


class FakeSound:
    def play(self, enabled: bool = True) -> bool:
        return False


def test_app_forced_break_flow(qapp, qtbot, monkeypatch):
    fake_settings = FakeSettings()
    monkeypatch.setattr(app_module, "Settings", lambda: fake_settings)
    monkeypatch.setattr(app_module, "ChimePlayer", lambda: FakeSound())

    app = StandTallApp(qapp, smoke_test=True)
    app._timer.stop()  # noqa: SLF001 - this test drives transitions explicitly
    try:
        assert app.break_schedule.enabled is True
        assert app.break_interval_minutes == 60
        assert app.break_schedule.interval_minutes == 60
        assert app.main_window.isVisible()
        assert app.status_bar.isVisible()
        app.hide_main()
        assert not app.main_window.isVisible()
        assert app.status_bar.isVisible()
        app.show_main()
        assert app.main_window.isVisible()
        assert app.status_bar.isVisible()
        app.start_break_now()
        assert app._break_active is True  # noqa: SLF001
        assert app.rest_window.isVisible()
        assert app.countdown.state.value == "paused"

        # Fast-forward the modal card instead of waiting five real minutes.
        app.rest_window._finish_countdown()  # noqa: SLF001
        assert app.rest_window._done.isEnabled()  # noqa: SLF001
        app.rest_window._done.click()  # noqa: SLF001

        assert app._break_active is False  # noqa: SLF001
        assert not app.rest_window.isVisible()
        assert app.countdown.state.value == "running"
        assert 3590 <= app.break_schedule.remaining_seconds() <= 3600
        assert app.main_window._break_status.text() == "1:00:00 后"  # noqa: SLF001
        assert "5 分钟" in app.main_window._break_caption.text()  # noqa: SLF001
    finally:
        app.shutdown()


def test_closable_break_uses_configured_duration(qapp, qtbot, monkeypatch):
    fake_settings = FakeSettings()
    fake_settings.allow_close = True
    fake_settings.break_duration = 9
    monkeypatch.setattr(app_module, "Settings", lambda: fake_settings)
    monkeypatch.setattr(app_module, "ChimePlayer", lambda: FakeSound())

    app = StandTallApp(qapp, smoke_test=True)
    app._timer.stop()  # noqa: SLF001
    try:
        app.start_break_now()
        assert app.rest_window.isVisible()
        assert app.rest_window._done.isEnabled() is False  # noqa: SLF001
        assert app.rest_window._close_button.isVisible()  # noqa: SLF001
        assert "9 分钟" in app.rest_window._subtitle.text()  # noqa: SLF001
        app.rest_window._dismiss()  # noqa: SLF001
        assert app._break_active is False  # noqa: SLF001
        assert not app.rest_window.isVisible()
        assert app.countdown.state.value == "running"
    finally:
        app.shutdown()
