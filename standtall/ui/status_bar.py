"""Always-visible compact desktop status bar.

This is deliberately independent of QSystemTrayIcon.  Some Windows sessions
(especially low-integrity processes on a high-integrity taskbar) reject tray
registration with ERROR_ACCESS_DENIED, so the status bar is the reliable way
to keep the timer visible and reachable.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QGuiApplication,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from standtall.core.countdown import CountdownSnapshot, format_remaining
from standtall.ui import theme
from standtall.ui.icons import make_pixmap


class StatusBar(QWidget):
    open_requested = Signal()
    toggle_pause_requested = Signal()
    rest_now_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._drag_offset: QPoint | None = None
        self._moved = False
        self._positioned = False
        self._progress = 0.0
        self._accent = QColor(theme.SAGE)
        self._countdown_state = "running"
        self._resting = False

        self.setWindowTitle("坐直 · 状态")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(252, 46)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("坐直 · 点击打开主界面，右键更多操作")

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 6, 13, 9)
        root.setSpacing(8)

        self._logo = QLabel(self)
        self._logo.setPixmap(make_pixmap(24, "active"))
        self._logo.setFixedSize(24, 24)
        self._logo.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        root.addWidget(self._logo, 0, Qt.AlignmentFlag.AlignVCenter)

        text_box = QVBoxLayout()
        text_box.setContentsMargins(0, 0, 0, 0)
        text_box.setSpacing(0)
        self._title = QLabel("坐直", self)
        self._title.setFont(theme.font(8.3, QFont.Weight.DemiBold))
        self._title.setStyleSheet(f"color: {theme.MUTED}; background: transparent;")
        self._title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text_box.addWidget(self._title)
        self._countdown = QLabel("30:00", self)
        self._countdown.setFont(theme.font(12.8, QFont.Weight.DemiBold))
        self._countdown.setStyleSheet(f"color: {theme.INK}; background: transparent;")
        self._countdown.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text_box.addWidget(self._countdown)
        root.addLayout(text_box)
        root.addStretch(1)

        self._break_label = QLabel("休 60:00", self)
        self._break_label.setFont(theme.font(8.2, QFont.Weight.DemiBold))
        self._break_label.setStyleSheet(f"color: {theme.PEACH}; background: transparent;")
        self._break_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._break_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(self._break_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self._menu = QMenu(self)
        self._open_action = self._menu.addAction("打开坐直")
        self._open_action.triggered.connect(lambda: self.open_requested.emit())
        self._menu.addSeparator()
        self._pause_action = self._menu.addAction("暂停提醒")
        self._pause_action.triggered.connect(lambda: self.toggle_pause_requested.emit())
        self._rest_action = self._menu.addAction("现在开始休息")
        self._rest_action.triggered.connect(lambda: self.rest_now_requested.emit())
        self._settings_action = self._menu.addAction("休息设置…")
        self._settings_action.triggered.connect(lambda: self.settings_requested.emit())
        self._menu.addSeparator()
        self._quit_action = self._menu.addAction("退出")
        self._quit_action.triggered.connect(lambda: self.quit_requested.emit())

    # ------------------------------------------------------------------ updates
    def update_view(
        self,
        snapshot: CountdownSnapshot,
        interval_minutes: int,
        break_enabled: bool,
        break_remaining_seconds: int,
        break_duration_minutes: int,
        allow_close: bool,
        resting: bool = False,
        break_interval_minutes: int = 60,
    ) -> None:
        self._resting = resting
        if snapshot.is_waiting:
            countdown = "该坐直了"
            color = theme.CORAL
            accent = QColor(theme.CORAL)
            self._countdown_state = "waiting"
        elif snapshot.is_paused:
            countdown = "已暂停"
            color = theme.MUTED
            accent = QColor(theme.FAINT)
            self._countdown_state = "paused"
        else:
            countdown = format_remaining(snapshot.remaining_seconds)
            color = theme.INK
            accent = QColor(theme.SAGE)
            self._countdown_state = "running"

        self._countdown.setText(countdown)
        self._countdown.setStyleSheet(f"color: {color}; background: transparent;")
        self._accent = accent

        if not break_enabled:
            self._break_label.setText("休 已关")
            self._break_label.setStyleSheet(f"color: {theme.FAINT}; background: transparent;")
        elif resting:
            self._break_label.setText("休息中")
            self._break_label.setStyleSheet(f"color: {theme.PEACH}; background: transparent;")
        else:
            self._break_label.setText(f"休 {format_remaining(break_remaining_seconds)}")
            self._break_label.setStyleSheet(f"color: {theme.PEACH}; background: transparent;")

        if interval_minutes > 0:
            self._progress = max(
                0.0,
                min(1.0, snapshot.remaining_seconds / (interval_minutes * 60)),
            )
        else:
            self._progress = 0.0
        self._pause_action.setText("继续提醒" if snapshot.is_paused else "暂停提醒")
        self._rest_action.setText("现在开始休息")
        self._break_label.setToolTip(
            f"每 {break_interval_minutes} 分钟强制休息 {break_duration_minutes} 分钟"
            + ("，允许关闭弹窗" if allow_close else "，弹窗不可关闭")
        )
        self.update()

    def show_bar(self) -> None:
        if not self._positioned:
            self._move_to_default()
            self._positioned = True
        self.show()
        self.raise_()
        self.update()

    def _move_to_default(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(
            max(area.left() + 8, area.right() - self.width() - 22),
            max(area.top() + 8, area.top() + 20),
        )

    # ------------------------------------------------------------------ events
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            )
            self._moved = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._menu.exec(event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            target = event.globalPosition().toPoint() - self._drag_offset
            if (target - self.pos()).manhattanLength() > 3:
                self._moved = True
            self.move(target)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self._clamp_to_screen()
            if not self._moved:
                self.open_requested.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _clamp_to_screen(self) -> None:
        screen = QGuiApplication.screenAt(self.frameGeometry().center())
        screen = screen or QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        x = min(max(self.x(), area.left()), area.right() - self.width())
        y = min(max(self.y(), area.top()), area.bottom() - self.height())
        self.move(x, y)

    # ------------------------------------------------------------------ painting
    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        panel = QRectF(5, 4, self.width() - 10, self.height() - 10)
        for spread in range(7, 0, -1):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(44, 30, 21, 5))
            p.drawRoundedRect(
                panel.adjusted(-spread * 0.45, -spread * 0.1, spread * 0.45, spread * 0.8),
                14 + spread * 0.3,
                14 + spread * 0.3,
            )
        path = QPainterPath()
        path.addRoundedRect(panel, 15, 15)
        gradient = QLinearGradient(panel.topLeft(), panel.bottomLeft())
        gradient.setColorAt(0, QColor(255, 252, 246, 247))
        gradient.setColorAt(1, QColor(247, 240, 230, 247))
        p.setBrush(gradient)
        p.setPen(QPen(QColor(233, 223, 209, 230), 1))
        p.drawPath(path)

        p.save()
        p.setClipPath(path)
        track = QRectF(panel.left() + 12, panel.bottom() - 3.5, panel.width() - 24, 2.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.SAGE_TRACK))
        p.drawRoundedRect(track, 1.25, 1.25)
        if self._progress > 0:
            fill = QRectF(track)
            fill.setWidth(track.width() * self._progress)
            p.setBrush(self._accent)
            p.drawRoundedRect(fill, 1.25, 1.25)
        p.restore()
        p.end()
