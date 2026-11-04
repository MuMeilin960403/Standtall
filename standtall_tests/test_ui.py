from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtTest import QSignalSpy

from standtall.core.countdown import CountdownSnapshot, CountdownState, PostureCountdown
from standtall.ui.break_settings import BreakSettingsDialog
from standtall.ui.icons import make_icon, make_pixmap
from standtall.ui.main_window import MainWindow
from standtall.ui.reminder_window import ReminderWindow
from standtall.ui.rest_window import RestWindow
from standtall.ui.status_bar import StatusBar


def running_snapshot() -> CountdownSnapshot:
    return CountdownSnapshot(
        state=CountdownState.RUNNING,
        remaining_seconds=1440,
        interval_seconds=1800,
        cycle_seconds=1800,
        progress=0.8,
        is_snooze=False,
    )


def waiting_snapshot() -> CountdownSnapshot:
    return CountdownSnapshot(
        state=CountdownState.WAITING,
        remaining_seconds=0,
        interval_seconds=1800,
        cycle_seconds=1800,
        progress=0.0,
        is_snooze=False,
    )


def test_icons_render(qapp):
    assert not make_icon("active").isNull()
    assert not make_pixmap(34, "paused").isNull()


def test_main_window_renders_and_exposes_signals(qtbot):
    window = MainWindow(30, True, running_snapshot())
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(120)

    assert not window.grab().isNull()
    assert window._primary_button.text() == "暂停提醒"
    assert window._minute_input.text() == "30"
    assert window._presets[1].isChecked()

    interval_spy = QSignalSpy(window.interval_change_requested)
    window._presets[2].click()
    assert interval_spy.count() == 1
    assert interval_spy.at(0)[0] == 45

    window._minute_input.setText("17")
    window._apply_button.click()
    assert interval_spy.count() == 2
    assert interval_spy.at(1)[0] == 17

    sound_spy = QSignalSpy(window.sound_toggle_requested)
    window._sound_toggle.click()
    assert sound_spy.count() == 1
    assert sound_spy.at(0)[0] is False


def test_waiting_state_controls(qtbot):
    window = MainWindow(30, True, waiting_snapshot())
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(60)
    assert window._primary_button.text() == "我已坐好，重新计时"
    assert window._secondary_button.text() == "5 分钟后提醒"
    assert not window._minute_input.isEnabled()
    assert not window._presets[0].isEnabled()
    assert window._remind_button.isHidden()


def test_break_controls_and_signal(qtbot):
    window = MainWindow(30, True, running_snapshot())
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(60)
    window.update_break_view(True, 42 * 60, False)
    assert window._break_status.text() == "42:00 后"
    assert window._break_toggle.isChecked() is True

    settings_spy = QSignalSpy(window.break_settings_requested)
    window._break_settings_button.click()
    assert settings_spy.count() == 1

    window.update_break_view(True, 42 * 60, False, 12, True, 45)
    assert "45 分钟" in window._break_caption.text()
    assert "12 分钟" in window._break_caption.text()
    assert "可关闭" in window._break_settings_button.toolTip()

    spy = QSignalSpy(window.break_toggle_requested)
    window._break_toggle.click()
    assert spy.count() == 1
    assert spy.at(0)[0] is False

    window.update_break_view(False, 0, False)
    assert window._break_status.text() == "已关闭"
    window.update_break_view(True, 0, True)
    assert window._break_status.text() == "休息中"


def test_rest_window_requires_countdown(qtbot):
    window = RestWindow()
    qtbot.addWidget(window)
    window.show_rest(1)
    qtbot.wait(250)
    assert window.isVisible()
    assert window._done.isEnabled() is False
    assert window._close_button.isHidden()
    assert window._clock.text() in {"00:01", "00:00"}

    qtbot.wait(950)
    assert window._done.isEnabled() is True
    assert window._clock.text() == "00:00"
    spy = QSignalSpy(window.completed)
    window._done.click()
    assert spy.count() == 1
    assert not window.isVisible()


def test_rest_window_can_close_when_enabled(qtbot):
    window = RestWindow()
    qtbot.addWidget(window)
    window.show_rest(60, allow_close=True)
    qtbot.wait(100)
    assert window._close_button.isVisible()
    assert "1 分钟" in window._subtitle.text()
    spy = QSignalSpy(window.dismissed)
    window._close_button.click()
    assert spy.count() == 1
    assert not window.isVisible()


def test_rest_window_close_event_is_ignored_when_locked(qtbot):
    window = RestWindow()
    qtbot.addWidget(window)
    window.show_rest(60, allow_close=False)
    qtbot.wait(80)
    assert window.isVisible()
    window.close()
    assert window.isVisible()


def test_status_bar_updates_and_exists(qtbot):
    bar = StatusBar()
    qtbot.addWidget(bar)
    bar.update_view(running_snapshot(), 30, True, 42 * 60, 8, False, False)
    assert bar._countdown.text() == "24:00"
    assert "42:00" in bar._break_label.text()
    bar.show_bar()
    qtbot.wait(60)
    assert bar.isVisible()
    assert not bar.grab().isNull()


def test_break_settings_dialog_values(qtbot):
    dialog = BreakSettingsDialog(45, 5, False, True)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.wait(60)
    dialog._interval_input.setText("30")
    dialog._duration_input.setText("12")
    dialog._allow_close_toggle.click()
    dialog._status_bar_toggle.click()
    dialog._save()
    assert dialog.result() == 1  # QDialog.DialogCode.Accepted
    assert dialog.values() == (30, 12, True, False)


def test_break_settings_rejects_invalid_duration(qtbot):
    dialog = BreakSettingsDialog(45, 5, False, True)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog._duration_input.setText("99")
    dialog._save()
    assert dialog.result() != 1
    assert dialog._error.text() != ""


def test_break_settings_rejects_invalid_interval(qtbot):
    dialog = BreakSettingsDialog(45, 5, False, True)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog._interval_input.setText("999")
    dialog._save()
    assert dialog.result() != 1
    assert "休息间隔" in dialog._error.text()


def test_main_window_pause_signal(qtbot):
    window = MainWindow(30, True, running_snapshot())
    qtbot.addWidget(window)
    window.show()
    spy = QSignalSpy(window.pause_requested)
    window._primary_button.click()
    assert spy.count() == 1


def test_reminder_renders_and_actions(qtbot):
    window = ReminderWindow()
    qtbot.addWidget(window)
    window.show_reminder(waiting_snapshot(), 30)
    qtbot.wait(260)
    assert window.isVisible()
    assert not window.grab().isNull()

    spy = QSignalSpy(window.done_requested)
    window._done.click()
    assert spy.count() == 1

    snooze_spy = QSignalSpy(window.snooze_requested)
    window._snooze.click()
    assert snooze_spy.count() == 1
    assert snooze_spy.at(0)[0] == 5
    window.hide()


def test_real_countdown_snapshot_feeds_window(qtbot):
    countdown = PostureCountdown(30)
    window = MainWindow(30, True, countdown.snapshot())
    qtbot.addWidget(window)
    window.update_view(countdown.snapshot(), 30, False)
    assert window._current_interval.text() == "当前 30 分钟"
