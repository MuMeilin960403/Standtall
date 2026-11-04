"""Forced five-minute screen break dialog."""

from __future__ import annotations

import math
import time

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QFontDatabase,
    QGuiApplication,
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

from standtall.core.rest import BREAK_DURATION_SECONDS
from standtall.ui import theme
from standtall.ui.widgets import CheckBullet, WalkMark


class RestWindow(QWidget):
    """A topmost, application-modal break card."""

    completed = Signal()
    dismissed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._finished = False
        self._deadline = 0.0
        self._allow_close = False
        self._duration_minutes = 5
        self.setWindowTitle("该起来走走了")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(460, 440)

        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._tick)

        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 24)
        root.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(15)
        header.addWidget(WalkMark(self, 64), 0, Qt.AlignmentFlag.AlignTop)
        header_text = QVBoxLayout()
        header_text.setContentsMargins(0, 3, 0, 0)
        header_text.setSpacing(4)
        self._title = QLabel("该起来走走了", self)
        self._title.setFont(theme.font(21, QFont.Weight.DemiBold))
        self._title.setStyleSheet(f"color: {theme.INK};")
        header_text.addWidget(self._title)
        self._subtitle = QLabel("已经坐了一个小时。站起来，离开屏幕，走动或远眺 5 分钟。", self)
        self._subtitle.setWordWrap(True)
        self._subtitle.setFont(theme.font(9.4))
        self._subtitle.setStyleSheet(f"color: {theme.MUTED};")
        header_text.addWidget(self._subtitle)
        header.addLayout(header_text, 1)
        self._close_button = QPushButton("×", self)
        self._close_button.setFixedSize(26, 26)
        self._close_button.setToolTip("关闭本次休息")
        self._close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_button.setStyleSheet(
            "QPushButton { border: 0; background: transparent; color: #A6AFA8;"
            " font-size: 20px; padding: 0; }"
            "QPushButton:hover { background: rgba(80,97,88,0.08); border-radius: 13px; }"
        )
        self._close_button.clicked.connect(self._dismiss)
        self._close_button.hide()
        header.addWidget(self._close_button, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header)
        root.addSpacing(12)

        divider = QWidget(self)
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {theme.BORDER};")
        root.addWidget(divider)
        root.addSpacing(12)

        self._clock = QLabel("05:00", self)
        self._clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mono_family = next(
            (name for name in ("Cascadia Mono", "Consolas", "Courier New") if name in QFontDatabase.families()),
            "Monospace",
        )
        clock_font = QFont(mono_family)
        clock_font.setPointSizeF(40)
        clock_font.setWeight(QFont.Weight.DemiBold)
        self._clock.setFont(clock_font)
        self._clock.setMinimumHeight(58)
        self._clock.setStyleSheet(f"color: {theme.PEACH}; background: transparent;")
        root.addWidget(self._clock)
        self._clock_caption = QLabel("强制休息倒计时 · 结束前不能关闭", self)
        self._clock_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._clock_caption.setFont(theme.font(8.7))
        self._clock_caption.setStyleSheet(f"color: {theme.MUTED};")
        root.addWidget(self._clock_caption)
        root.addSpacing(12)

        tips = (
            "站起来，离开座位，别只是伸个懒腰。",
            "走到窗边看看远处，让眼睛离开屏幕。",
            "接杯水，活动一下肩颈；倒计时结束再回来。",
        )
        for tip in tips:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(9)
            row.addWidget(CheckBullet(self), 0, Qt.AlignmentFlag.AlignTop)
            label = QLabel(tip, self)
            label.setFont(theme.font(9.3))
            label.setStyleSheet(f"color: {theme.INK_SOFT}; background: transparent;")
            label.setWordWrap(False)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            label.setMinimumHeight(21)
            row.addWidget(label, 1)
            root.addLayout(row)
            root.addSpacing(6)

        root.addStretch(1)
        self._done = QPushButton("休息中…", self)
        self._done.setObjectName("primary")
        self._done.setCursor(Qt.CursorShape.PointingHandCursor)
        self._done.setFixedHeight(42)
        self._done.setEnabled(False)
        self._done.clicked.connect(self._on_done)
        root.addWidget(self._done)
        root.addSpacing(7)
        footer = QLabel("起身活动是这次提醒的一部分；倒计时结束后再继续。", self)
        self._footer = footer
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setFont(theme.font(8.1))
        footer.setStyleSheet(f"color: {theme.FAINT}; background: transparent;")
        footer.setWordWrap(False)
        footer.setMinimumHeight(16)
        root.addWidget(footer)

    def show_rest(
        self,
        duration_seconds: int = BREAK_DURATION_SECONDS,
        *,
        scheduled: bool = True,
        allow_close: bool = False,
    ) -> None:
        self._finished = False
        self._allow_close = bool(allow_close)
        self._duration_minutes = max(1, int(round(duration_seconds / 60)))
        self._deadline = time.time() + max(1, int(duration_seconds))
        self._title.setText("该起来走走了")
        if scheduled:
            self._subtitle.setText(
                f"已经坐了一小时。离开屏幕，走动或远眺 {self._duration_minutes} 分钟。"
            )
        else:
            self._subtitle.setText(
                f"给自己 {self._duration_minutes} 分钟。离开屏幕，走动或远眺，倒计时结束后再回来。"
            )
        self._clock_caption.setText(
            "强制休息倒计时 · 可提前关闭"
            if self._allow_close
            else "强制休息倒计时 · 结束前不能关闭"
        )
        self._footer.setText(
            "允许提前关闭；如果已休息好，也可以点下方按钮继续。"
            if self._allow_close
            else "起身活动是这次提醒的一部分；倒计时结束后再继续。"
        )
        self._close_button.setVisible(self._allow_close)
        self._done.setText("休息中…")
        self._done.setEnabled(False)
        self._update_clock()
        self._position_centered()
        self.show()
        self.raise_()
        self.activateWindow()
        self._timer.start()

    def hide_rest(self) -> None:
        self._timer.stop()
        self.hide()

    def _tick(self) -> None:
        if self._finished:
            return
        self._update_clock()
        if self._remaining() <= 0:
            self._finish_countdown()

    def _remaining(self) -> int:
        return max(0, int(math.ceil(self._deadline - time.time())))

    def _update_clock(self) -> None:
        remaining = self._remaining()
        minutes, seconds = divmod(remaining, 60)
        self._clock.setText(f"{minutes:02d}:{seconds:02d}")

    def _finish_countdown(self) -> None:
        self._finished = True
        self._timer.stop()
        self._clock.setText("00:00")
        self._clock_caption.setText("休息完成 · 可以回到工作")
        self._done.setText("休息完成，继续工作")
        self._done.setEnabled(True)
        self._done.setFocus(Qt.FocusReason.OtherFocusReason)

    def _on_done(self) -> None:
        if not self._finished:
            return
        self.hide_rest()
        self.completed.emit()

    def _dismiss(self) -> None:
        if not self._allow_close or not self.isVisible():
            return
        self.hide_rest()
        self.dismissed.emit()

    def _position_centered(self) -> None:
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(
            max(area.left() + 10, area.center().x() - self.width() // 2),
            max(area.top() + 10, area.center().y() - self.height() // 2),
        )

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._allow_close:
            self._timer.stop()
            event.accept()
            self.dismissed.emit()
            return
        event.ignore()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            if self._allow_close:
                self._dismiss()
            event.accept()
            return
        super().keyPressEvent(event)

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
        gradient.setColorAt(1, QColor("#FAF1E7"))
        p.setBrush(QBrush(gradient))
        p.setPen(QPen(QColor(255, 255, 255, 130), 1))
        p.drawPath(path)

        p.save()
        p.setClipPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(233, 145, 110, 30))
        p.drawEllipse(QRectF(panel.right() - 125, panel.top() - 65, 220, 220))
        p.setBrush(QColor(93, 137, 113, 12))
        p.drawEllipse(QRectF(panel.left() - 80, panel.bottom() - 105, 190, 190))
        p.restore()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.PEACH))
        p.drawRoundedRect(QRectF(panel.left() + 1, panel.top() + 38, 3, 36), 1.5, 1.5)
        p.end()
