"""Application controller for the StandTall posture reminder."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QDialog

from standtall.core.countdown import CountdownSnapshot, CountdownState, PostureCountdown
from standtall.core.rest import BreakSchedule
from standtall.services.settings import Settings, clamp_interval
from standtall.services.sound import ChimePlayer
from standtall.ui.break_settings import BreakSettingsDialog
from standtall.ui.icons import make_icon
from standtall.ui.main_window import MainWindow
from standtall.ui.reminder_window import ReminderWindow
from standtall.ui.rest_window import RestWindow
from standtall.ui.status_bar import StatusBar
from standtall.ui.tray import Tray

log = logging.getLogger(__name__)

TICK_MS = 250


def clock_label(seconds: int) -> str:
    due = datetime.now() + timedelta(seconds=max(0, seconds))
    now = datetime.now()
    if due.date() != now.date():
        return f"明天 {due:%H:%M}"
    return f"{due:%H:%M}"


class StandTallApp(QObject):
    def __init__(self, qapp: QApplication, *, smoke_test: bool = False) -> None:
        super().__init__()
        self.qapp = qapp
        self._smoke_test = smoke_test
        self._shutting_down = False
        self._last_main_signature: tuple | None = None
        self._last_tray_signature: tuple | None = None

        self.settings = Settings()
        self.sound = ChimePlayer()
        self.countdown = PostureCountdown(self.settings.interval_minutes())
        self.break_interval_minutes = self.settings.break_interval_minutes()
        self.break_schedule = BreakSchedule(
            self.break_interval_minutes,
            enabled=self.settings.break_reminder_enabled(),
        )
        self.break_duration_minutes = self.settings.break_duration_minutes()
        self.break_allow_close = self.settings.break_allow_close()
        self._status_bar_enabled = self.settings.status_bar_enabled()
        self._break_active = False
        self._break_keep_posture_paused = False
        snapshot = self.countdown.snapshot()

        self.main_window = MainWindow(
            self.settings.interval_minutes(),
            self.settings.sound_enabled(),
            snapshot,
        )
        self.reminder_window = ReminderWindow()
        self.rest_window = RestWindow()
        self.status_bar = StatusBar()
        self.tray = Tray(self)
        self._wire_signals()

        self._position_main()
        self.main_window.show()
        if self._status_bar_enabled:
            self.status_bar.show_bar()
        self._refresh(force=True)

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self.qapp.aboutToQuit.connect(self.shutdown)
        log.info(
            "StandTall started: interval=%s min, sound=%s",
            self.settings.interval_minutes(),
            self.settings.sound_enabled(),
        )

    # ------------------------------------------------------------------ setup
    def _wire_signals(self) -> None:
        mw = self.main_window
        mw.pause_requested.connect(self.pause)
        mw.resume_requested.connect(self.resume)
        mw.acknowledge_requested.connect(self.acknowledge)
        mw.snooze_requested.connect(self.snooze)
        mw.reset_requested.connect(self.reset)
        mw.remind_now_requested.connect(self.remind_now)
        mw.interval_change_requested.connect(self.set_interval)
        mw.sound_toggle_requested.connect(self.set_sound_enabled)
        mw.break_toggle_requested.connect(self.set_break_enabled)
        mw.break_settings_requested.connect(self.open_break_settings)
        mw.hide_requested.connect(self.hide_main)

        rw = self.reminder_window
        rw.done_requested.connect(self.acknowledge)
        rw.snooze_requested.connect(self.snooze)
        rw.pause_requested.connect(self.pause)
        self.rest_window.completed.connect(self._on_break_completed)
        self.rest_window.dismissed.connect(self._on_break_dismissed)

        self.status_bar.open_requested.connect(self.show_main)
        self.status_bar.toggle_pause_requested.connect(self.toggle_pause)
        self.status_bar.rest_now_requested.connect(self.start_break_now)
        self.status_bar.settings_requested.connect(self.open_break_settings)
        self.status_bar.quit_requested.connect(self.quit_application)

        self.tray.open_requested.connect(self.show_main)
        self.tray.toggle_pause_requested.connect(self.toggle_pause)
        self.tray.remind_now_requested.connect(self.remind_now)
        self.tray.rest_now_requested.connect(self.start_break_now)
        self.tray.quit_requested.connect(self.quit_application)

    def _position_main(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        x = area.center().x() - self.main_window.width() // 2
        y = area.center().y() - self.main_window.height() // 2
        x = max(area.left() + 12, min(x, area.right() - self.main_window.width() - 12))
        y = max(area.top() + 12, min(y, area.bottom() - self.main_window.height() - 12))
        self.main_window.move(x, y)

    # ------------------------------------------------------------------ timing
    def _tick(self) -> None:
        if self._shutting_down:
            return
        posture_due = False
        if not self._break_active:
            if self.break_schedule.poll():
                self._begin_break()
            else:
                posture_due = self.countdown.poll()
        self._refresh()
        if posture_due and not self._break_active:
            self._present_reminder(scheduled=True)

    def _refresh(self, force: bool = False) -> None:
        snapshot = self.countdown.snapshot()
        sound = self.settings.sound_enabled()
        break_enabled = self.break_schedule.enabled
        break_remaining = self.break_schedule.remaining_seconds()
        signature = (
            snapshot.state,
            snapshot.remaining_seconds,
            snapshot.interval_seconds,
            snapshot.is_snooze,
            sound,
            break_enabled,
            break_remaining,
            self._break_active,
            self.break_duration_minutes,
            self.break_allow_close,
            self.break_interval_minutes,
        )
        if force or signature != self._last_main_signature:
            self._last_main_signature = signature
            self.main_window.update_view(
                snapshot,
                self.countdown.interval_minutes,
                sound,
            )
            self.main_window.update_break_view(
                break_enabled,
                break_remaining,
                self._break_active,
                self.break_duration_minutes,
                self.break_allow_close,
                self.break_interval_minutes,
            )
            self.status_bar.update_view(
                snapshot,
                self.countdown.interval_minutes,
                break_enabled,
                break_remaining,
                self.break_duration_minutes,
                self.break_allow_close,
                self._break_active,
                self.break_interval_minutes,
            )
        self._update_tray(snapshot)

    def _update_tray(self, snapshot: CountdownSnapshot) -> None:
        icon_state = {
            CountdownState.RUNNING: "active",
            CountdownState.PAUSED: "paused",
            CountdownState.WAITING: "attention",
        }[snapshot.state]
        if snapshot.state == CountdownState.WAITING:
            tooltip = "坐直 · 该坐正啦"
            next_text = ""
        elif snapshot.state == CountdownState.PAUSED:
            tooltip = "坐直 · 提醒已暂停"
            next_text = ""
        else:
            next_text = clock_label(snapshot.remaining_seconds)
            tooltip = f"坐直 · 下次提醒 {next_text}"
        signature = (icon_state, tooltip, snapshot.is_paused, next_text)
        if signature != self._last_tray_signature:
            self._last_tray_signature = signature
            self.tray.set_state(icon_state, tooltip, snapshot.is_paused)

    # ------------------------------------------------------------------ actions
    def pause(self) -> None:
        self.countdown.pause()
        self.reminder_window.hide_card()
        self._refresh(force=True)

    def resume(self) -> None:
        self.countdown.resume()
        self._refresh(force=True)

    def toggle_pause(self) -> None:
        if self.countdown.state == CountdownState.PAUSED:
            self.resume()
        else:
            self.pause()

    def acknowledge(self) -> None:
        self.countdown.acknowledge()
        self.reminder_window.hide_card()
        self._refresh(force=True)

    def snooze(self, minutes: int = 5) -> None:
        self.countdown.snooze(minutes)
        self.reminder_window.hide_card()
        self._refresh(force=True)

    def reset(self) -> None:
        self.countdown.reset()
        self.reminder_window.hide_card()
        self._refresh(force=True)

    def remind_now(self) -> None:
        if self.countdown.state != CountdownState.WAITING:
            self.countdown.trigger_now()
        self._refresh(force=True)
        self._present_reminder(scheduled=False)

    def _present_reminder(self, *, scheduled: bool) -> None:
        snapshot = self.countdown.snapshot()
        self.reminder_window.show_reminder(snapshot, self.countdown.interval_minutes)
        self.sound.play(self.settings.sound_enabled())
        if scheduled:
            if snapshot.is_snooze:
                self.tray.notify("坐直", "5 分钟到了，顺便把肩膀放下来。")
            else:
                self.tray.notify("坐直", "该坐正啦。双脚踩稳，肩膀放松。")
        self._update_tray(snapshot)

    def set_interval(self, minutes: int) -> None:
        minutes = clamp_interval(minutes)
        self.countdown.set_interval(minutes)
        self.settings.set_interval_minutes(minutes)
        self._refresh(force=True)
        self.main_window.set_interval_display(minutes)
        self.main_window.show_feedback(f"已改为每 {minutes} 分钟提醒。")
        log.info("Reminder interval changed to %s minutes", minutes)

    def set_sound_enabled(self, enabled: bool) -> None:
        self.settings.set_sound_enabled(enabled)
        self._refresh(force=True)
        if enabled:
            self.sound.play(True)

    def set_break_enabled(self, enabled: bool) -> None:
        self.settings.set_break_reminder_enabled(enabled)
        self.break_schedule.set_enabled(enabled)
        if not enabled and self._break_active:
            # The modal normally prevents this path, but keep the application
            # consistent if an external caller disables breaks mid-rest.
            self.rest_window.hide_rest()
            self._break_active = False
            self.countdown.acknowledge()
        self._refresh(force=True)
        log.info("Forced break reminders enabled=%s", enabled)

    def start_break_now(self) -> None:
        if self._break_active:
            self.rest_window.raise_()
            self.rest_window.activateWindow()
            return
        self._begin_break(manual=True)

    def _begin_break(self, *, manual: bool = False) -> None:
        if self._break_active or self._shutting_down:
            return
        self._break_active = True
        self._break_keep_posture_paused = self.countdown.state == CountdownState.PAUSED
        self.reminder_window.hide_card()
        self.countdown.pause()
        self.rest_window.show_rest(
            self.break_duration_minutes * 60,
            scheduled=not manual,
            allow_close=self.break_allow_close,
        )
        self.sound.play(self.settings.sound_enabled())
        self.tray.notify(
            "坐直 · 休息时间",
            f"离开屏幕，走动或远眺 {self.break_duration_minutes} 分钟。",
            6500,
        )
        self._refresh(force=True)
        log.info(
            "Forced break started%s (%s min, closable=%s)",
            " manually" if manual else "",
            self.break_duration_minutes,
            self.break_allow_close,
        )

    def _on_break_completed(self) -> None:
        self._finish_break(completed=True)

    def _on_break_dismissed(self) -> None:
        self._finish_break(completed=False)

    def _finish_break(self, *, completed: bool) -> None:
        if not self._break_active:
            return
        self._break_active = False
        self.rest_window.hide_rest()
        self.break_schedule.mark_completed()
        if self._break_keep_posture_paused:
            # The user had paused posture reminders; keep that preference and
            # only reset the paused interval.
            self.countdown.reset()
        else:
            # A completed walk resets both schedules: fresh posture hour and
            # the next forced break an hour away.
            self.countdown.acknowledge()
        self.tray.notify(
            "休息完成" if completed else "已结束本次休息",
            f"下一次强制休息在 {self.break_interval_minutes} 分钟后。",
            4000,
        )
        self._refresh(force=True)
        log.info("Forced break %s", "completed" if completed else "dismissed")

    def open_break_settings(self) -> None:
        parent = self.main_window if self.main_window.isVisible() else None
        dialog = BreakSettingsDialog(
            self.break_interval_minutes,
            self.break_duration_minutes,
            self.break_allow_close,
            self._status_bar_enabled,
            parent,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        interval, duration, allow_close, status_bar_enabled = dialog.values()
        self.settings.set_break_interval_minutes(interval)
        self.settings.set_break_duration_minutes(duration)
        self.settings.set_break_allow_close(allow_close)
        self.break_interval_minutes = interval
        self.break_duration_minutes = duration
        self.break_allow_close = allow_close
        self.break_schedule.set_interval_minutes(interval)
        self._set_status_bar_enabled(status_bar_enabled)
        self._refresh(force=True)
        log.info(
            "Break settings: interval=%s min, duration=%s min, allow_close=%s, status_bar=%s",
            interval,
            duration,
            allow_close,
            status_bar_enabled,
        )

    def _set_status_bar_enabled(self, enabled: bool) -> None:
        self._status_bar_enabled = bool(enabled)
        self.settings.set_status_bar_enabled(self._status_bar_enabled)
        if self._status_bar_enabled:
            self.status_bar.show_bar()
        else:
            # Do not leave a hidden main window with neither tray nor status
            # bar reachable.  Bring the window back before hiding the bar.
            if not self.main_window.isVisible():
                self.main_window.show_and_raise()
            self.status_bar.hide()

    # ------------------------------------------------------------------ windows
    def show_main(self) -> None:
        self.main_window.show_and_raise()

    def hide_main(self) -> None:
        if not self.tray.available and not self._status_bar_enabled:
            self.quit_application()
            return
        self.main_window.hide()
        if self._status_bar_enabled:
            self.status_bar.show_bar()
        if not self.settings.hide_hint_shown():
            self.tray.notify(
                "坐直会继续提醒",
                "关闭窗口不会停止计时。桌面状态条或托盘里都能回来。",
                5200,
            )
            self.settings.mark_hide_hint_shown()

    def quit_application(self) -> None:
        """Quit without letting the main window's close-to-tray handler
        cancel the application exit."""
        if self._shutting_down:
            self.qapp.exit(0)
            return
        self.status_bar.hide()
        self.reminder_window.hide()
        self.rest_window.hide_rest()
        self.main_window.hide()
        self.qapp.exit(0)

    # ------------------------------------------------------------------ shutdown
    def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        self._timer.stop()
        self.reminder_window.hide()
        self.rest_window.hide_rest()
        self.status_bar.hide()
        self.main_window.hide()
        self.tray.hide()
        log.info("StandTall stopped")


def configure_application(app: QApplication) -> None:
    """Shared visual setup used by main and preview tooling."""
    from standtall.ui import theme

    app.setStyle("Fusion")
    app.setFont(theme.app_font(10))
    app.setStyleSheet(theme.global_qss())
    app.setWindowIcon(make_icon("active"))
