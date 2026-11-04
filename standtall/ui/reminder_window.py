"""A gentle, focus-preserving posture reminder card."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QGuiApplication,
    QCursor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from standtall.core.countdown import CountdownSnapshot
from standtall.ui import theme
from standtall.ui.widgets import CheckBullet, PostureMark


class ReminderWindow(QWidget):
    done_requested = Signal()
    snooze_requested = Signal(int)
    pause_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._interval_minutes = 30
        self._fade: QPropertyAnimation | None = None

        self.setWindowTitle("该坐正啦")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(432, 346)

        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 24)
        root.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(14)
        mark = PostureMark(self, 62)
        header.addWidget(mark, 0, Qt.AlignmentFlag.AlignTop)
        header_text = QVBoxLayout()
        header_text.setContentsMargins(0, 2, 0, 0)
        header_text.setSpacing(3)
        title = QLabel("该坐正啦", self)
        title.setFont(theme.font(20, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {theme.INK};")
        header_text.addWidget(title)
        self._subtitle = QLabel(self)
        self._subtitle.setFont(theme.font(9.2))
        self._subtitle.setStyleSheet(f"color: {theme.MUTED};")
        self._subtitle.setWordWrap(True)
        header_text.addWidget(self._subtitle)
        header.addLayout(header_text, 1)
        root.addLayout(header)
        root.addSpacing(15)

        divider = QWidget(self)
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {theme.BORDER};")
        root.addWidget(divider)
        root.addSpacing(12)

        tips = (
            "双脚踩稳，膝盖略低于髋部。",
            "屏幕上沿与视线齐平，别低头。",
            "肩膀向后向下，做三次慢呼吸。",
        )
        for tip in tips:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(9)
            row.addWidget(CheckBullet(self), 0, Qt.AlignmentFlag.AlignTop)
            label = QLabel(tip, self)
            label.setFont(theme.font(9.5))
            label.setStyleSheet(f"color: {theme.INK_SOFT};")
            label.setWordWrap(True)
            row.addWidget(label, 1)
            root.addLayout(row)
            root.addSpacing(7)
        root.addSpacing(5)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        self._done = QPushButton("坐好啦，重新计时", self)
        self._done.setObjectName("primary")
        self._done.setCursor(Qt.CursorShape.PointingHandCursor)
        self._done.setFixedHeight(40)
        self._done.clicked.connect(lambda: self.done_requested.emit())
        buttons.addWidget(self._done, 1)
        self._snooze = QPushButton("5 分钟后", self)
        self._snooze.setObjectName("secondary")
        self._snooze.setCursor(Qt.CursorShape.PointingHandCursor)
        self._snooze.setFixedHeight(40)
        self._snooze.clicked.connect(lambda: self.snooze_requested.emit(5))
        buttons.addWidget(self._snooze, 0)
        root.addLayout(buttons)
        root.addSpacing(7)

        footer = QHBoxLayout()
        footer.setContentsMargins(2, 0, 2, 0)
        self._pause_link = QPushButton("暂停提醒", self)
        self._pause_link.setObjectName("textButton")
        self._pause_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pause_link.clicked.connect(lambda: self.pause_requested.emit())
        footer.addWidget(self._pause_link)
        footer.addStretch(1)
        self._cadence = QLabel(self)
        self._cadence.setObjectName("tiny")
        footer.addWidget(self._cadence)
        root.addLayout(footer)
        root.addStretch(1)

    def show_reminder(self, snapshot: CountdownSnapshot, interval_minutes: int) -> None:
        self._interval_minutes = interval_minutes
        if snapshot.is_snooze:
            self._subtitle.setText("5 分钟到了，顺便把肩膀放下来。")
        else:
            self._subtitle.setText(
                f"{interval_minutes} 分钟到了，给身体一次复位。"
            )
        self._cadence.setText(f"提醒间隔 {interval_minutes} 分钟")
        self._position_card()
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
            self.raise_()
            self._animate_opacity(1.0, 180)
        else:
            self.raise_()

    def hide_card(self) -> None:
        if not self.isVisible():
            return
        if self._fade is not None:
            self._fade.stop()
        self._animate_opacity(0.0, 150)

    def _animate_opacity(self, target: float, duration: int) -> None:
        animation = QPropertyAnimation(self, b"windowOpacity", self)
        animation.setDuration(duration)
        animation.setStartValue(self.windowOpacity())
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        if target <= 0.01:
            animation.finished.connect(self.hide)
        self._fade = animation
        animation.start()

    def _position_card(self) -> None:
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        x = area.right() - self.width() - 24
        y = area.bottom() - self.height() - 24
        self.move(QPoint(max(area.left() + 8, x), max(area.top() + 8, y)))

    def closeEvent(self, event) -> None:  # noqa: N802
        # A topmost nudge should never vanish without recording an action.
        event.ignore()
        self.snooze_requested.emit(5)
        self.hide_card()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        panel = QRectF(12, 12, self.width() - 24, self.height() - 24)
        for spread in range(9, 0, -1):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(44, 30, 21, 4))
            p.drawRoundedRect(
                panel.adjusted(-spread * 0.45, -spread * 0.1, spread * 0.45, spread * 0.9),
                22 + spread * 0.4,
                22 + spread * 0.4,
            )
        path = QPainterPath()
        path.addRoundedRect(panel, 23, 23)
        gradient = QLinearGradient(panel.topLeft(), panel.bottomLeft())
        gradient.setColorAt(0, QColor("#FFFCF6"))
        gradient.setColorAt(1, QColor("#FAF3E9"))
        p.setBrush(QBrush(gradient))
        p.setPen(QPen(QColor(255, 255, 255, 120), 1))
        p.drawPath(path)

        p.save()
        p.setClipPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(233, 145, 110, 28))
        p.drawEllipse(QRectF(panel.right() - 130, panel.top() - 70, 220, 220))
        p.setBrush(QColor(93, 137, 113, 14))
        p.drawEllipse(QRectF(panel.left() - 80, panel.bottom() - 100, 180, 180))
        p.restore()

        # Warm accent tab on the left, a small visual signature.
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.PEACH))
        p.drawRoundedRect(QRectF(panel.left() + 1, panel.top() + 36, 3, 36), 1.5, 1.5)
        p.end()
