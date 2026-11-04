"""Small settings dialog for forced-break behavior."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIntValidator,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from standtall.services.settings import (
    DEFAULT_BREAK_INTERVAL_MINUTES,
    MAX_BREAK_DURATION_MINUTES,
    MAX_BREAK_INTERVAL_MINUTES,
    MIN_BREAK_DURATION_MINUTES,
    MIN_BREAK_INTERVAL_MINUTES,
    clamp_break_duration,
    clamp_break_interval,
)
from standtall.ui import theme
from standtall.ui.widgets import ToggleSwitch


class BreakSettingsDialog(QDialog):
    def __init__(
        self,
        interval_minutes: int,
        duration_minutes: int,
        allow_close: bool,
        status_bar_enabled: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("休息设置")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(392, 455)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        title = QLabel("休息设置", self)
        title.setFont(theme.font(17, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {theme.INK}; background: transparent;")
        header.addWidget(title)
        header.addStretch(1)
        close = QPushButton("×", self)
        close.setFixedSize(26, 26)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setStyleSheet(
            "QPushButton { border: 0; background: transparent; color: #7E8B82;"
            " font-size: 20px; padding: 0; }"
            "QPushButton:hover { background: rgba(80,97,88,0.08); border-radius: 13px; }"
        )
        close.clicked.connect(self.reject)
        header.addWidget(close)
        root.addLayout(header)
        root.addSpacing(4)
        caption = QLabel("调整休息间隔、每次休息时长与弹窗行为。", self)
        caption.setFont(theme.font(9.2))
        caption.setStyleSheet(f"color: {theme.MUTED}; background: transparent;")
        root.addWidget(caption)
        root.addSpacing(14)

        interval_title = QLabel("休息间隔", self)
        interval_title.setFont(theme.font(10.2, QFont.Weight.DemiBold))
        interval_title.setStyleSheet(f"color: {theme.INK_SOFT}; background: transparent;")
        root.addWidget(interval_title)
        root.addSpacing(4)

        interval_row = QHBoxLayout()
        interval_row.setContentsMargins(0, 0, 0, 0)
        interval_row.setSpacing(8)
        self._interval_input = QLineEdit(
            str(clamp_break_interval(interval_minutes)),
            self,
        )
        self._interval_input.setObjectName("minuteInput")
        self._interval_input.setValidator(
            QIntValidator(MIN_BREAK_INTERVAL_MINUTES, MAX_BREAK_INTERVAL_MINUTES, self)
        )
        self._interval_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._interval_input.setFixedWidth(68)
        interval_row.addWidget(self._interval_input)
        interval_unit = QLabel("分钟", self)
        interval_unit.setFont(theme.font(9.8))
        interval_unit.setStyleSheet(f"color: {theme.INK_SOFT}; background: transparent;")
        interval_row.addWidget(interval_unit)
        interval_row.addStretch(1)
        interval_hint = QLabel(
            f"{MIN_BREAK_INTERVAL_MINUTES}–{MAX_BREAK_INTERVAL_MINUTES} 分钟，保存后从现在重新计时",
            self,
        )
        interval_hint.setFont(theme.font(8.2))
        interval_hint.setStyleSheet(f"color: {theme.FAINT}; background: transparent;")
        interval_hint.setMinimumHeight(16)
        interval_row.addWidget(interval_hint)
        root.addLayout(interval_row)
        root.addSpacing(12)

        duration_title = QLabel("强制休息时长", self)
        duration_title.setFont(theme.font(10.2, QFont.Weight.DemiBold))
        duration_title.setStyleSheet(f"color: {theme.INK_SOFT}; background: transparent;")
        root.addWidget(duration_title)
        root.addSpacing(4)

        duration_row = QHBoxLayout()
        duration_row.setContentsMargins(0, 0, 0, 0)
        duration_row.setSpacing(8)
        self._duration_input = QLineEdit(str(clamp_break_duration(duration_minutes)), self)
        self._duration_input.setObjectName("minuteInput")
        self._duration_input.setValidator(
            QIntValidator(MIN_BREAK_DURATION_MINUTES, MAX_BREAK_DURATION_MINUTES, self)
        )
        self._duration_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._duration_input.setFixedWidth(68)
        duration_row.addWidget(self._duration_input)
        unit = QLabel("分钟", self)
        unit.setFont(theme.font(9.8))
        unit.setStyleSheet(f"color: {theme.INK_SOFT}; background: transparent;")
        duration_row.addWidget(unit)
        duration_row.addStretch(1)
        duration_hint = QLabel(
            f"{MIN_BREAK_DURATION_MINUTES}–{MAX_BREAK_DURATION_MINUTES} 分钟，修改后从下一次休息生效",
            self,
        )
        duration_hint.setFont(theme.font(8.2))
        duration_hint.setStyleSheet(f"color: {theme.FAINT}; background: transparent;")
        duration_hint.setMinimumHeight(16)
        duration_row.addWidget(duration_hint)
        root.addLayout(duration_row)
        root.addSpacing(13)

        close_row = QHBoxLayout()
        close_row.setContentsMargins(0, 0, 0, 0)
        close_text = QVBoxLayout()
        close_text.setContentsMargins(0, 0, 0, 0)
        close_text.setSpacing(1)
        close_title = QLabel("允许关闭休息弹窗", self)
        close_title.setFont(theme.font(10.0, QFont.Weight.DemiBold))
        close_title.setStyleSheet(f"color: {theme.INK_SOFT}; background: transparent;")
        close_text.addWidget(close_title)
        close_hint = QLabel("开启后右上角出现 ×，可提前关闭；关闭后必须走完倒计时。", self)
        close_hint.setWordWrap(True)
        close_hint.setFont(theme.font(8.2))
        close_hint.setStyleSheet(f"color: {theme.FAINT}; background: transparent;")
        close_hint.setMinimumHeight(30)
        close_text.addWidget(close_hint)
        close_row.addLayout(close_text, 1)
        close_row.addSpacing(10)
        self._allow_close_toggle = ToggleSwitch(bool(allow_close), self)
        close_row.addWidget(self._allow_close_toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(close_row)
        root.addSpacing(13)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_text = QVBoxLayout()
        status_text.setContentsMargins(0, 0, 0, 0)
        status_text.setSpacing(1)
        status_title = QLabel("显示桌面状态条", self)
        status_title.setFont(theme.font(10.0, QFont.Weight.DemiBold))
        status_title.setStyleSheet(f"color: {theme.INK_SOFT}; background: transparent;")
        status_text.addWidget(status_title)
        status_hint = QLabel("即使系统托盘不可用，也能看到倒计时、打开主界面和退出。", self)
        status_hint.setWordWrap(True)
        status_hint.setFont(theme.font(8.2))
        status_hint.setStyleSheet(f"color: {theme.FAINT}; background: transparent;")
        status_hint.setMinimumHeight(30)
        status_text.addWidget(status_hint)
        status_row.addLayout(status_text, 1)
        status_row.addSpacing(10)
        self._status_bar_toggle = ToggleSwitch(bool(status_bar_enabled), self)
        status_row.addWidget(self._status_bar_toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(status_row)
        root.addSpacing(8)

        self._error = QLabel("", self)
        self._error.setFont(theme.font(8.5))
        self._error.setStyleSheet(f"color: {theme.CORAL}; background: transparent;")
        self._error.setMinimumHeight(16)
        root.addWidget(self._error)
        root.addStretch(1)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        buttons.addStretch(1)
        cancel = QPushButton("取消", self)
        cancel.setObjectName("textButton")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        save = QPushButton("保存", self)
        save.setObjectName("primary")
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.setFixedHeight(34)
        save.setMinimumWidth(82)
        save.clicked.connect(self._save)
        buttons.addWidget(save)
        root.addLayout(buttons)

    def values(self) -> tuple[int, int, bool, bool]:
        return (
            clamp_break_interval(
                int(self._interval_input.text() or DEFAULT_BREAK_INTERVAL_MINUTES)
            ),
            clamp_break_duration(int(self._duration_input.text() or 5)),
            self._allow_close_toggle.isChecked(),
            self._status_bar_toggle.isChecked(),
        )

    def _save(self) -> None:
        try:
            interval = int(self._interval_input.text().strip())
        except ValueError:
            self._error.setText(
                f"休息间隔请输入 {MIN_BREAK_INTERVAL_MINUTES}–{MAX_BREAK_INTERVAL_MINUTES} 分钟。"
            )
            return
        if not (MIN_BREAK_INTERVAL_MINUTES <= interval <= MAX_BREAK_INTERVAL_MINUTES):
            self._error.setText(
                f"休息间隔请输入 {MIN_BREAK_INTERVAL_MINUTES}–{MAX_BREAK_INTERVAL_MINUTES} 分钟。"
            )
            return
        text = self._duration_input.text().strip()
        try:
            duration = int(text)
        except ValueError:
            self._error.setText(f"请输入 {MIN_BREAK_DURATION_MINUTES}–{MAX_BREAK_DURATION_MINUTES} 之间的分钟数。")
            return
        if not (MIN_BREAK_DURATION_MINUTES <= duration <= MAX_BREAK_DURATION_MINUTES):
            self._error.setText(f"请输入 {MIN_BREAK_DURATION_MINUTES}–{MAX_BREAK_DURATION_MINUTES} 之间的分钟数。")
            return
        self.accept()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is not None and parent.isVisible():
            center = parent.frameGeometry().center()
            self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)
        else:
            from PySide6.QtGui import QGuiApplication

            screen = QGuiApplication.primaryScreen()
            if screen is not None:
                area = screen.availableGeometry()
                self.move(
                    area.center().x() - self.width() // 2,
                    area.center().y() - self.height() // 2,
                )

    def closeEvent(self, event) -> None:  # noqa: N802
        super().closeEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        panel = QRectF(10, 9, self.width() - 20, self.height() - 19)
        for spread in range(9, 0, -1):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(44, 30, 21, 4))
            p.drawRoundedRect(
                panel.adjusted(-spread * 0.45, -spread * 0.1, spread * 0.45, spread * 0.9),
                18 + spread * 0.4,
                18 + spread * 0.4,
            )
        path = QPainterPath()
        path.addRoundedRect(panel, 21, 21)
        gradient = QLinearGradient(panel.topLeft(), panel.bottomLeft())
        gradient.setColorAt(0, QColor("#FFFCF7"))
        gradient.setColorAt(1, QColor("#F9F1E7"))
        p.setBrush(gradient)
        p.setPen(QPen(QColor(233, 223, 209), 1))
        p.drawPath(path)

        p.save()
        p.setClipPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(233, 145, 110, 26))
        p.drawEllipse(QRectF(panel.right() - 120, panel.top() - 70, 210, 210))
        p.setBrush(QColor(93, 137, 113, 11))
        p.drawEllipse(QRectF(panel.left() - 80, panel.bottom() - 100, 180, 180))
        p.restore()
        p.end()
