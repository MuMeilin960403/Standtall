"""Main window for StandTall."""

from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIntValidator,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from standtall.core.countdown import CountdownSnapshot, format_remaining
from standtall.services.settings import (
    MAX_INTERVAL_MINUTES,
    MIN_INTERVAL_MINUTES,
    clamp_interval,
)
from standtall.ui import theme
from standtall.ui.icons import make_icon, make_pixmap
from standtall.ui.widgets import (
    PresetButton,
    ProgressRing,
    ToggleSwitch,
    WalkMark,
    WindowButton,
)


class DragArea(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._offset: QPoint | None = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._offset = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._offset = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


class MainWindow(QWidget):
    pause_requested = Signal()
    resume_requested = Signal()
    acknowledge_requested = Signal()
    snooze_requested = Signal(int)
    reset_requested = Signal()
    remind_now_requested = Signal()
    interval_change_requested = Signal(int)
    sound_toggle_requested = Signal(bool)
    break_toggle_requested = Signal(bool)
    break_settings_requested = Signal()
    hide_requested = Signal()

    def __init__(
        self,
        interval_minutes: int,
        sound_enabled: bool,
        snapshot: CountdownSnapshot,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._snapshot = snapshot
        self._interval_minutes = clamp_interval(interval_minutes)
        self._ui_interval = self._interval_minutes
        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(self._restore_tagline)

        self.setWindowTitle("坐直 · 姿势提醒")
        self.setWindowIcon(make_icon("active"))
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(472, 600)

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 26, 32, 20)
        root.setSpacing(0)

        header = DragArea(self)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        logo = QLabel(header)
        logo.setPixmap(make_pixmap(34, "active"))
        logo.setFixedSize(34, 34)
        logo.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        header_layout.addWidget(logo)

        brand = QVBoxLayout()
        brand.setContentsMargins(0, 0, 0, 0)
        brand.setSpacing(-1)
        title = QLabel("坐直", header)
        title.setFont(theme.font(13, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {theme.INK};")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        brand.addWidget(title)
        tag = QLabel("STAND TALL  ·  POSTURE REMINDER", header)
        tag_font = theme.font(6.6, QFont.Weight.DemiBold)
        tag_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.9)
        tag.setFont(tag_font)
        tag.setStyleSheet(f"color: {theme.FAINT};")
        tag.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        brand.addWidget(tag)
        header_layout.addLayout(brand)
        header_layout.addStretch(1)

        self._minimize_button = WindowButton("minimize", "收起到托盘", header)
        self._minimize_button.clicked.connect(lambda: self.hide_requested.emit())
        header_layout.addWidget(self._minimize_button)
        self._close_button = WindowButton("close", "收起到托盘", header)
        self._close_button.clicked.connect(lambda: self.hide_requested.emit())
        header_layout.addWidget(self._close_button)
        header.setFixedHeight(36)
        root.addWidget(header)
        root.addSpacing(2)

        ring_row = QHBoxLayout()
        ring_row.setContentsMargins(0, 0, 0, 0)
        self._ring = ProgressRing(self, 176)
        ring_row.addStretch(1)
        ring_row.addWidget(self._ring)
        ring_row.addStretch(1)
        root.addLayout(ring_row)
        root.addSpacing(2)

        self._tagline = QLabel(self)
        self._tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tagline.setFont(theme.font(9.2))
        self._tagline.setStyleSheet(f"color: {theme.MUTED};")
        self._tagline.setWordWrap(True)
        self._tagline.setFixedHeight(20)
        root.addWidget(self._tagline)
        root.addSpacing(9)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        controls.addStretch(1)
        self._primary_button = QPushButton(self)
        self._primary_button.setObjectName("primary")
        self._primary_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._primary_button.setFixedHeight(38)
        self._primary_button.setMinimumWidth(130)
        self._primary_button.clicked.connect(self._on_primary)
        controls.addWidget(self._primary_button)
        self._secondary_button = QPushButton(self)
        self._secondary_button.setObjectName("secondary")
        self._secondary_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._secondary_button.setFixedHeight(38)
        self._secondary_button.clicked.connect(self._on_secondary)
        controls.addWidget(self._secondary_button)
        self._remind_button = QPushButton("现在提醒一次", self)
        self._remind_button.setObjectName("textButton")
        self._remind_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remind_button.clicked.connect(self.remind_now_requested)
        controls.addWidget(self._remind_button)
        controls.addStretch(1)
        root.addLayout(controls)
        root.addSpacing(11)

        interval_card = QFrame(self)
        interval_card.setObjectName("card")
        interval_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card_layout = QVBoxLayout(interval_card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(7)
        card_header = QHBoxLayout()
        card_header.setContentsMargins(0, 0, 0, 0)
        section = QLabel("提醒间隔", interval_card)
        section.setObjectName("sectionTitle")
        card_header.addWidget(section)
        card_header.addStretch(1)
        self._current_interval = QLabel(interval_card)
        self._current_interval.setObjectName("caption")
        card_header.addWidget(self._current_interval)
        card_layout.addLayout(card_header)

        preset_row = QHBoxLayout()
        preset_row.setContentsMargins(0, 0, 0, 0)
        preset_row.setSpacing(6)
        self._preset_group = QButtonGroup(self)
        self._preset_group.setExclusive(True)
        self._presets: list[PresetButton] = []
        for minutes in (20, 30, 45, 60):
            button = PresetButton(minutes, interval_card)
            self._preset_group.addButton(button)
            self._presets.append(button)
            button.clicked.connect(lambda checked=False, m=minutes: self._apply_interval(m))
            preset_row.addWidget(button, 1)
        card_layout.addLayout(preset_row)

        custom_row = QHBoxLayout()
        custom_row.setContentsMargins(0, 0, 0, 0)
        custom_row.setSpacing(7)
        custom_label = QLabel("自定义", interval_card)
        custom_label.setObjectName("caption")
        custom_row.addWidget(custom_label)
        self._minute_input = QLineEdit(interval_card)
        self._minute_input.setObjectName("minuteInput")
        self._minute_input.setValidator(QIntValidator(MIN_INTERVAL_MINUTES, MAX_INTERVAL_MINUTES, self))
        self._minute_input.setText(str(self._interval_minutes))
        self._minute_input.setMaxLength(3)
        self._minute_input.setFixedWidth(76)
        self._minute_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._minute_input.setToolTip(f"{MIN_INTERVAL_MINUTES}–{MAX_INTERVAL_MINUTES} 分钟")
        self._minute_input.returnPressed.connect(self._apply_custom_interval)
        custom_row.addWidget(self._minute_input)
        unit = QLabel("分钟", interval_card)
        unit.setObjectName("caption")
        custom_row.addWidget(unit)
        custom_row.addStretch(1)
        self._apply_button = QPushButton("应用", interval_card)
        self._apply_button.setObjectName("compactButton")
        self._apply_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_button.setFixedHeight(32)
        self._apply_button.clicked.connect(self._apply_custom_interval)
        custom_row.addWidget(self._apply_button)
        card_layout.addLayout(custom_row)
        root.addWidget(interval_card)
        root.addSpacing(9)

        sound_row = QHBoxLayout()
        sound_row.setContentsMargins(4, 0, 4, 0)
        sound_row.setSpacing(8)
        sound_text = QVBoxLayout()
        sound_text.setContentsMargins(0, 0, 0, 0)
        sound_text.setSpacing(0)
        sound_label = QLabel("提示音", self)
        sound_label.setFont(theme.font(9.8, QFont.Weight.DemiBold))
        sound_label.setStyleSheet(f"color: {theme.INK_SOFT};")
        sound_text.addWidget(sound_label)
        sound_caption = QLabel("轻柔的两音提示，不会打断工作", self)
        sound_caption.setObjectName("tiny")
        sound_text.addWidget(sound_caption)
        sound_row.addLayout(sound_text)
        sound_row.addStretch(1)
        self._sound_toggle = ToggleSwitch(sound_enabled, self)
        self._sound_toggle.toggled.connect(self.sound_toggle_requested)
        sound_row.addWidget(self._sound_toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(sound_row)
        root.addSpacing(8)

        break_card = QFrame(self)
        break_card.setObjectName("restCard")
        break_card.setFixedHeight(48)
        break_layout = QHBoxLayout(break_card)
        break_layout.setContentsMargins(11, 6, 9, 6)
        break_layout.setSpacing(9)
        break_layout.addWidget(WalkMark(break_card, 30), 0, Qt.AlignmentFlag.AlignVCenter)
        break_text = QVBoxLayout()
        break_text.setContentsMargins(0, 0, 0, 0)
        break_text.setSpacing(0)
        self._break_title = QLabel("休息提醒", break_card)
        self._break_title.setFont(theme.font(9.7, QFont.Weight.DemiBold))
        self._break_title.setStyleSheet(f"color: {theme.INK_SOFT};")
        break_text.addWidget(self._break_title)
        self._break_caption = QLabel("每小时强制走动 · 5 分钟", break_card)
        self._break_caption.setObjectName("tiny")
        break_text.addWidget(self._break_caption)
        break_layout.addLayout(break_text)
        break_layout.addStretch(1)
        self._break_settings_button = QPushButton("设置", break_card)
        self._break_settings_button.setObjectName("textButton")
        self._break_settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._break_settings_button.setFixedHeight(22)
        self._break_settings_button.setToolTip("调整休息时长、是否允许关闭弹窗和状态条")
        self._break_settings_button.clicked.connect(self.break_settings_requested)
        break_layout.addWidget(self._break_settings_button, 0, Qt.AlignmentFlag.AlignVCenter)
        self._break_status = QLabel("60:00 后", break_card)
        self._break_status.setFont(theme.font(8.5, QFont.Weight.DemiBold))
        self._break_status.setStyleSheet(f"color: {theme.MUTED};")
        break_layout.addWidget(self._break_status, 0, Qt.AlignmentFlag.AlignVCenter)
        self._break_toggle = ToggleSwitch(True, break_card)
        self._break_toggle.setToolTip("开启后每小时弹出一次休息提醒")
        self._break_toggle.toggled.connect(self.break_toggle_requested)
        break_layout.addWidget(self._break_toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(break_card)
        root.addStretch(1)

        footer = QHBoxLayout()
        footer.setContentsMargins(4, 0, 4, 0)
        footer.setSpacing(6)
        self._status_dot = QLabel(self)
        self._status_dot.setFixedSize(7, 7)
        footer.addWidget(self._status_dot)
        self._next_label = QLabel(self)
        self._next_label.setObjectName("tiny")
        footer.addWidget(self._next_label)
        footer.addStretch(1)
        tray_hint = QLabel("关闭窗口后仍会继续提醒", self)
        tray_hint.setObjectName("tiny")
        footer.addWidget(tray_hint)
        root.addLayout(footer)

        self._set_interval_ui(self._interval_minutes)
        self.update_view(snapshot, self._interval_minutes, sound_enabled)
        self.update_break_view(True, 60 * 60)

    # ------------------------------------------------------------------ public
    def update_break_view(
        self,
        enabled: bool,
        remaining_seconds: int,
        resting: bool = False,
        duration_minutes: int = 5,
        allow_close: bool = False,
        interval_minutes: int = 60,
    ) -> None:
        duration_minutes = max(1, int(duration_minutes))
        interval_minutes = max(1, int(interval_minutes))
        self._break_caption.setText(
            f"每 {interval_minutes} 分钟 · 休息 {duration_minutes} 分钟"
        )
        self._break_settings_button.setToolTip(
            f"每 {interval_minutes} 分钟触发，休息 {duration_minutes} 分钟；"
            + ("弹窗可关闭" if allow_close else "弹窗不可关闭")
        )
        self._break_toggle.blockSignals(True)
        self._break_toggle.setChecked(enabled)
        self._break_toggle.blockSignals(False)
        if not enabled:
            self._break_status.setText("已关闭")
            self._break_status.setStyleSheet(f"color: {theme.FAINT};")
            self._break_title.setStyleSheet(f"color: {theme.MUTED};")
            self._break_toggle.setToolTip("开启每小时强制休息")
            return
        self._break_title.setStyleSheet(f"color: {theme.INK_SOFT};")
        self._break_toggle.setToolTip(
            f"关闭后将不再自动弹出强制休息（当前 {duration_minutes} 分钟）"
        )
        if resting:
            self._break_status.setText("休息中")
            self._break_status.setStyleSheet(f"color: {theme.PEACH};")
            return
        self._break_status.setText(f"{format_remaining(remaining_seconds)} 后")
        self._break_status.setStyleSheet(f"color: {theme.MUTED};")

    def update_view(
        self,
        snapshot: CountdownSnapshot,
        interval_minutes: int,
        sound_enabled: bool,
    ) -> None:
        previous_state = self._snapshot.state
        self._snapshot = snapshot
        self._interval_minutes = clamp_interval(interval_minutes)
        self._ring.set_snapshot(snapshot)
        self._current_interval.setText(f"当前 {self._interval_minutes} 分钟")
        self._sound_toggle.blockSignals(True)
        self._sound_toggle.setChecked(sound_enabled)
        self._sound_toggle.blockSignals(False)
        if self._interval_minutes != self._ui_interval:
            self._ui_interval = self._interval_minutes
            self._set_interval_ui(self._interval_minutes)

        waiting = snapshot.is_waiting
        paused = snapshot.is_paused
        if waiting:
            self._primary_button.setText("我已坐好，重新计时")
            self._secondary_button.setText("5 分钟后提醒")
            self._remind_button.hide()
            self._primary_button.setEnabled(True)
            self._secondary_button.setEnabled(True)
        elif paused:
            self._primary_button.setText("继续提醒")
            self._secondary_button.setText("重新计时")
            self._remind_button.show()
            self._primary_button.setEnabled(True)
            self._secondary_button.setEnabled(True)
        else:
            self._primary_button.setText("暂停提醒")
            self._secondary_button.setText("重新计时")
            self._remind_button.show()
            self._primary_button.setEnabled(True)
            self._secondary_button.setEnabled(True)

        self._minute_input.setEnabled(not waiting)
        self._apply_button.setEnabled(not waiting)
        for button in self._presets:
            button.setEnabled(not waiting)
        if previous_state != snapshot.state:
            self._feedback_timer.stop()
            self._restore_tagline_style()
        if not self._feedback_timer.isActive():
            self._tagline.setText(self._tagline_for(snapshot))
        self._update_footer(snapshot)

    def set_interval_display(self, minutes: int) -> None:
        self._set_interval_ui(clamp_interval(minutes))

    def show_feedback(self, text: str, duration_ms: int = 2400) -> None:
        self._tagline.setText(text)
        self._tagline.setStyleSheet(f"color: {theme.SAGE_DARK};")
        self._feedback_timer.start(duration_ms)

    def show_and_raise(self) -> None:
        self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    # ------------------------------------------------------------------ internals
    def _set_interval_ui(self, minutes: int) -> None:
        self._current_interval.setText(f"当前 {minutes} 分钟")
        self._minute_input.setText(str(minutes))
        self._preset_group.setExclusive(False)
        for button in self._presets:
            button.setChecked(button.minutes == minutes)
        self._preset_group.setExclusive(True)

    def _tagline_for(self, snapshot: CountdownSnapshot) -> str:
        if snapshot.is_waiting:
            return "慢慢调整，准备好后点「我已坐好」。"
        if snapshot.is_paused:
            return "提醒暂停中。想继续时，点上方按钮。"
        if snapshot.is_snooze:
            return "这次先休息一下，稍后再提醒你。"
        return f"每 {self._interval_minutes} 分钟，给身体一次复位。"

    def _restore_tagline(self) -> None:
        self._restore_tagline_style()
        self._tagline.setText(self._tagline_for(self._snapshot))

    def _restore_tagline_style(self) -> None:
        self._tagline.setStyleSheet(f"color: {theme.MUTED};")

    def _update_footer(self, snapshot: CountdownSnapshot) -> None:
        dot_color = {
            "running": theme.SAGE,
            "paused": theme.FAINT,
            "waiting": theme.CORAL,
        }[snapshot.state.value]
        if snapshot.is_snooze and snapshot.is_running:
            dot_color = theme.PEACH
        self._status_dot.setStyleSheet(
            f"background: {dot_color}; border-radius: 3px;"
        )
        if snapshot.is_waiting:
            self._next_label.setText("等待你调整坐姿")
            return
        if snapshot.is_paused:
            self._next_label.setText("提醒已暂停")
            return
        due = datetime.now() + timedelta(seconds=snapshot.remaining_seconds)
        prefix = "稍后提醒" if snapshot.is_snooze else "下次提醒"
        if due.date() != datetime.now().date():
            self._next_label.setText(f"{prefix} · 明天 {due:%H:%M}")
        else:
            self._next_label.setText(f"{prefix} · {due:%H:%M}")

    def _on_primary(self) -> None:
        if self._snapshot.is_waiting:
            self.acknowledge_requested.emit()
        elif self._snapshot.is_paused:
            self.resume_requested.emit()
        else:
            self.pause_requested.emit()

    def _on_secondary(self) -> None:
        if self._snapshot.is_waiting:
            self.snooze_requested.emit(5)
        else:
            self.reset_requested.emit()

    def _apply_interval(self, minutes: int) -> None:
        self.interval_change_requested.emit(int(minutes))

    def _apply_custom_interval(self) -> None:
        raw = self._minute_input.text().strip()
        if not raw:
            self._minute_input.setText(str(self._interval_minutes))
            return
        try:
            minutes = int(raw)
        except ValueError:
            self._minute_input.setText(str(self._interval_minutes))
            return
        self._apply_interval(clamp_interval(minutes))

    def closeEvent(self, event) -> None:  # noqa: N802
        event.ignore()
        self.hide_requested.emit()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        panel = QRectF(12, 12, self.width() - 24, self.height() - 24)
        # Layered shadow, then the warm paper surface.
        for spread in range(10, 0, -1):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(51, 36, 27, 3))
            p.drawRoundedRect(
                panel.adjusted(-spread * 0.42, -spread * 0.15, spread * 0.42, spread * 0.8),
                24 + spread * 0.35,
                24 + spread * 0.35,
            )
        path = QPainterPath()
        path.addRoundedRect(panel, 25, 25)
        gradient = QLinearGradient(panel.topLeft(), panel.bottomLeft())
        gradient.setColorAt(0, theme.PANEL_TOP)
        gradient.setColorAt(1, theme.PANEL_BOTTOM)
        p.setBrush(QBrush(gradient))
        p.setPen(QPen(QColor(255, 255, 255, 110), 1))
        p.drawPath(path)

        p.save()
        p.setClipPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(233, 145, 110, 26))
        p.drawEllipse(QRectF(panel.right() - 150, panel.top() - 80, 260, 260))
        p.setBrush(QColor(93, 137, 113, 18))
        p.drawEllipse(QRectF(panel.left() - 120, panel.bottom() - 140, 260, 260))
        p.setBrush(QColor(255, 255, 255, 55))
        p.drawEllipse(QRectF(panel.left() + 54, panel.top() + 60, 5, 5))
        p.setBrush(QColor(255, 255, 255, 38))
        p.drawEllipse(QRectF(panel.right() - 70, panel.bottom() - 70, 8, 8))
        p.restore()

        p.setPen(QPen(QColor(255, 255, 255, 120), 1))
        p.drawLine(
            int(panel.left()) + 28,
            int(panel.top()) + 1,
            int(panel.right()) - 28,
            int(panel.top()) + 1,
        )
        p.end()
