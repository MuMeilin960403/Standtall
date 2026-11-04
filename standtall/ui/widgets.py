"""Custom-painted controls used by StandTall."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QAbstractButton, QPushButton, QSizePolicy, QWidget

from standtall.core.countdown import CountdownSnapshot, format_remaining
from standtall.ui import theme

_MONO_CANDIDATES = ("Cascadia Mono", "Consolas", "JetBrains Mono", "Courier New")


def _mono_font(size: float) -> QFont:
    families = set(QFontDatabase.families())
    family = next((name for name in _MONO_CANDIDATES if name in families), "Monospace")
    font = QFont(family)
    font.setPointSizeF(size)
    font.setWeight(QFont.Weight.DemiBold)
    return font


class WindowButton(QAbstractButton):
    def __init__(self, kind: str, tooltip: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.kind = kind
        self._hover = False
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setToolTip(tooltip)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(theme.PEACH_PALE if self.kind == "close" else theme.CARD_ALT))
            p.drawEllipse(QRectF(1, 1, self.width() - 2, self.height() - 2))
        color = QColor(theme.CORAL if self.kind == "close" and self._hover else theme.INK_SOFT)
        p.setPen(QPen(color, 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        cx, cy = self.width() / 2, self.height() / 2
        if self.kind == "close":
            p.drawLine(QPointF(cx - 4.5, cy - 4.5), QPointF(cx + 4.5, cy + 4.5))
            p.drawLine(QPointF(cx + 4.5, cy - 4.5), QPointF(cx - 4.5, cy + 4.5))
        else:
            p.drawLine(QPointF(cx - 5, cy + 4), QPointF(cx + 5, cy + 4))


class ToggleSwitch(QAbstractButton):
    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(44, 25)

    def sizeHint(self) -> QSize:
        return QSize(44, 25)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        track = QColor(theme.SAGE if self.isChecked() else "#D8D3C9")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        knob_x = self.width() - 22 if self.isChecked() else 3
        p.setBrush(QColor("#FFFDF8"))
        p.drawEllipse(QRectF(knob_x, 3, 19, 19))


class PresetButton(QPushButton):
    def __init__(self, minutes: int, parent: QWidget | None = None) -> None:
        super().__init__(f"{minutes} 分钟", parent)
        self.minutes = minutes
        self.setCheckable(True)
        self.setObjectName("preset")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedHeight(31)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class ProgressRing(QWidget):
    def __init__(self, parent: QWidget | None = None, diameter: int = 188) -> None:
        super().__init__(parent)
        self._snapshot: CountdownSnapshot | None = None
        self._render_key: tuple | None = None
        self.setFixedSize(diameter, diameter)

    def set_snapshot(self, snapshot: CountdownSnapshot) -> None:
        key = (snapshot.state, snapshot.remaining_seconds, snapshot.progress, snapshot.is_snooze)
        if key == self._render_key:
            return
        self._render_key = key
        self._snapshot = snapshot
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if self._snapshot is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        snapshot = self._snapshot
        size = min(self.width(), self.height())
        ring_width = max(8.0, size * 0.052)
        outer = QRectF(1.5, 1.5, size - 3, size - 3)
        inner = outer.adjusted(ring_width, ring_width, -ring_width, -ring_width)

        # A gentle lift under the dial keeps the light UI from feeling flat.
        for spread, alpha in ((5, 8), (3, 10), (1, 14)):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(83, 63, 45, alpha))
            p.drawEllipse(inner.adjusted(-spread, -spread + 2, spread, spread + 3))
        p.setBrush(QColor(theme.CARD))
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.drawEllipse(inner)

        track = QRectF(
            outer.left() + ring_width / 2,
            outer.top() + ring_width / 2,
            outer.width() - ring_width,
            outer.height() - ring_width,
        )
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(
            QPen(
                QColor(theme.SAGE_TRACK),
                ring_width,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        p.drawArc(track, 0, 360 * 16)

        if snapshot.is_waiting:
            progress = 1.0
            ring_color = QColor(theme.CORAL)
            p.setPen(
                QPen(ring_color, ring_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            )
            p.drawArc(track, 90 * 16, -360 * 16)
        else:
            progress = max(0.0, min(1.0, snapshot.progress))
            if snapshot.is_paused:
                dashed = QPen(
                    QColor("#9AA69D"),
                    ring_width,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
                dashed.setDashPattern([0.7, 1.2])
                p.setPen(dashed)
            else:
                gradient = QLinearGradient(track.topLeft(), track.bottomRight())
                gradient.setColorAt(0.0, QColor(theme.SAGE))
                gradient.setColorAt(0.65, QColor("#77A38A"))
                if snapshot.remaining_seconds <= 60:
                    gradient.setColorAt(1.0, QColor(theme.PEACH))
                else:
                    gradient.setColorAt(1.0, QColor("#97B9A2"))
                p.setPen(
                    QPen(
                        QBrush(gradient),
                        ring_width,
                        Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap,
                    )
                )
            if progress > 0.003:
                p.drawArc(track, 90 * 16, -int(progress * 360 * 16))

        # Center typography.
        if snapshot.is_waiting:
            caption = "等待你调整"
            accent = QColor(theme.CORAL)
        elif snapshot.is_paused:
            caption = "提醒已暂停"
            accent = QColor(theme.MUTED)
        elif snapshot.is_snooze:
            caption = "稍后提醒"
            accent = QColor(theme.PEACH)
        else:
            caption = "下一次提醒"
            accent = QColor(theme.SAGE_DARK)

        center = inner.center()
        p.setFont(theme.font(8.3, QFont.Weight.DemiBold))
        p.setPen(QColor(theme.MUTED))
        p.drawText(
            QRectF(inner.left(), center.y() - 57, inner.width(), 20),
            Qt.AlignmentFlag.AlignCenter,
            caption,
        )

        remaining_text = format_remaining(snapshot.remaining_seconds)
        number_font = _mono_font(27 if len(remaining_text) <= 5 else 23)
        p.setFont(number_font)
        p.setPen(accent)
        p.drawText(
            QRectF(inner.left(), center.y() - 34, inner.width(), 50),
            Qt.AlignmentFlag.AlignCenter,
            remaining_text,
        )

        p.setFont(theme.font(8.8))
        p.setPen(QColor(theme.MUTED))
        status_text = {
            "running": "保持脊柱中立",
            "paused": "点击继续，随时重新计时",
            "waiting": "该坐正啦",
        }[snapshot.state.value]
        p.drawText(
            QRectF(inner.left(), center.y() + 23, inner.width(), 22),
            Qt.AlignmentFlag.AlignCenter,
            status_text,
        )

        # Tiny alignment cue under the copy.
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.SAGE_PALE))
        p.drawRoundedRect(
            QRectF(center.x() - 22, center.y() + 51, 44, 3),
            1.5,
            1.5,
        )
        p.end()


class PostureMark(QWidget):
    """Quiet line-art of a seated person, used on the reminder card."""

    def __init__(self, parent: QWidget | None = None, size: int = 64) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        p.setBrush(QColor(theme.SAGE_PALE))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(0, 0, side, side))

        p.scale(side / 64.0, side / 64.0)
        p.setBrush(Qt.BrushStyle.NoBrush)
        pen = QPen(QColor(theme.SAGE_DARK), 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawEllipse(QRectF(27, 13, 10, 10))
        path = QPainterPath()
        path.moveTo(32, 25)
        path.cubicTo(31, 30, 31, 36, 33, 40)
        path.lineTo(45, 44)
        path.lineTo(45, 53)
        p.drawPath(path)
        p.drawLine(QPointF(45, 53), QPointF(51, 53))
        p.drawLine(QPointF(33, 31), QPointF(24, 40))
        p.setPen(QPen(QColor(theme.PEACH), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(20, 21, 30, 32), 130 * 16, 105 * 16)
        p.end()


class CheckBullet(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(18, 18)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.SAGE_PALE))
        p.drawEllipse(QRectF(0, 0, 18, 18))
        p.setPen(
            QPen(
                QColor(theme.SAGE_DARK),
                1.7,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        p.drawLine(QPointF(5, 9), QPointF(8, 12))
        p.drawLine(QPointF(8, 12), QPointF(13, 6))
        p.end()


class WalkMark(QWidget):
    """A small walking figure used by the forced-break surfaces."""

    def __init__(self, parent: QWidget | None = None, size: int = 64) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.PEACH_PALE))
        p.drawEllipse(QRectF(0, 0, side, side))
        p.scale(side / 64.0, side / 64.0)

        # Motion lines.
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(theme.PEACH), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(8, 19, 18, 24), 130 * 16, 90 * 16)
        p.drawArc(QRectF(6, 34, 14, 16), 140 * 16, 80 * 16)

        # Walking figure.
        p.setPen(QPen(QColor(theme.SAGE_DARK), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(QColor(theme.SAGE_DARK))
        p.drawEllipse(QRectF(31, 10, 11, 11))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(36, 23), QPointF(33, 36))
        p.drawLine(QPointF(35, 27), QPointF(44, 23))
        p.drawLine(QPointF(33, 30), QPointF(24, 35))
        p.drawLine(QPointF(33, 36), QPointF(43, 46))
        p.drawLine(QPointF(33, 36), QPointF(24, 47))
        p.drawLine(QPointF(43, 46), QPointF(46, 51))
        p.drawLine(QPointF(24, 47), QPointF(20, 52))
        p.end()

