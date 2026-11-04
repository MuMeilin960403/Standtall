"""Hand-painted application icon: an upright figure in a calm green tile."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from standtall.ui import theme

ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def _draw_mark(painter: QPainter, color: QColor) -> None:
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QRectF(27.5, 11.5, 9.0, 9.0))

    pen = QPen(color, 5.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    # Upright spine.
    painter.drawLine(32, 24, 32, 37)
    # Shoulders, seated thigh and lower leg.
    painter.drawLine(26, 30, 38, 30)
    painter.drawLine(32, 37, 43, 42)
    painter.drawLine(43, 42, 43, 52)


def _pixmap_for_size(size: int, state: str) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / 64.0, size / 64.0)

    background = {
        "active": QColor(theme.SAGE),
        "paused": QColor("#8A948D"),
        "attention": QColor(theme.CORAL),
    }.get(state, QColor(theme.SAGE))

    path = QPainterPath()
    path.addRoundedRect(QRectF(2, 2, 60, 60), 17, 17)
    painter.fillPath(path, background)
    painter.setPen(QPen(QColor(255, 255, 255, 24), 1))
    painter.drawPath(path)

    if state == "paused":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFDF7"))
        painter.drawRoundedRect(QRectF(23, 22, 6, 21), 3, 3)
        painter.drawRoundedRect(QRectF(35, 22, 6, 21), 3, 3)
    else:
        _draw_mark(painter, QColor("#FFFDF7"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.PEACH_PALE))
        painter.drawEllipse(QRectF(46, 9, 7, 7))

    painter.end()
    return pixmap


def make_icon(state: str = "active") -> QIcon:
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(_pixmap_for_size(size, state))
    return icon


def make_pixmap(size: int = 36, state: str = "active") -> QPixmap:
    return _pixmap_for_size(max(8, int(size)), state)
