"""System tray presence for StandTall."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from standtall.ui.icons import make_icon

log = logging.getLogger(__name__)


class Tray(QObject):
    open_requested = Signal()
    toggle_pause_requested = Signal()
    remind_now_requested = Signal()
    rest_now_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._available = QSystemTrayIcon.isSystemTrayAvailable()
        self._icons = {
            "active": make_icon("active"),
            "paused": make_icon("paused"),
            "attention": make_icon("attention"),
        }
        self._tray = QSystemTrayIcon(self._icons["active"], self)
        self._tray.setToolTip("坐直 · 姿势提醒")

        menu = QMenu()
        open_action = QAction("打开坐直", menu)
        open_action.triggered.connect(lambda: self.open_requested.emit())
        menu.addAction(open_action)
        menu.addSeparator()
        self._pause_action = QAction("暂停提醒", menu)
        self._pause_action.triggered.connect(lambda: self.toggle_pause_requested.emit())
        menu.addAction(self._pause_action)
        remind = QAction("现在提醒一次", menu)
        remind.triggered.connect(lambda: self.remind_now_requested.emit())
        menu.addAction(remind)
        rest_now = QAction("现在开始休息", menu)
        rest_now.triggered.connect(lambda: self.rest_now_requested.emit())
        menu.addAction(rest_now)
        menu.addSeparator()
        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(lambda: self.quit_requested.emit())
        menu.addAction(quit_action)
        self._menu = menu
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.messageClicked.connect(lambda: self.open_requested.emit())

        if self._available:
            self._tray.show()
        else:
            log.warning("System tray is unavailable")

    @property
    def available(self) -> bool:
        return self._available

    def set_state(self, icon_state: str, tooltip: str, paused: bool) -> None:
        self._tray.setIcon(self._icons.get(icon_state, self._icons["active"]))
        self._tray.setToolTip(tooltip)
        self._pause_action.setText("继续提醒" if paused else "暂停提醒")

    def notify(self, title: str, message: str, duration_ms: int = 4000) -> None:
        if not self._available:
            return
        self._tray.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            duration_ms,
        )

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.open_requested.emit()

    def hide(self) -> None:
        self._tray.hide()
        self._menu.hide()
