"""Render a README preview on a fictional desktop, without capturing the desktop."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QRadialGradient,
)
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from standtall.app import configure_application
from standtall.core.countdown import CountdownSnapshot, CountdownState
from standtall.ui import theme
from standtall.ui.break_settings import BreakSettingsDialog
from standtall.ui.main_window import MainWindow
from standtall.ui.reminder_window import ReminderWindow
from standtall.ui.rest_window import RestWindow
from standtall.ui.status_bar import StatusBar

DOCS = ROOT / "docs"


def snapshot_running() -> CountdownSnapshot:
    return CountdownSnapshot(
        state=CountdownState.RUNNING,
        remaining_seconds=24 * 60 + 36,
        interval_seconds=30 * 60,
        cycle_seconds=30 * 60,
        progress=(24 * 60 + 36) / (30 * 60),
        is_snooze=False,
    )


def snapshot_waiting() -> CountdownSnapshot:
    return CountdownSnapshot(
        state=CountdownState.WAITING,
        remaining_seconds=0,
        interval_seconds=30 * 60,
        cycle_seconds=30 * 60,
        progress=0.0,
        is_snooze=False,
    )


def wallpaper(width: int = 1440, height: int = 900) -> QImage:
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor("#EEE6D9"))
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    base = QLinearGradient(0, 0, width, height)
    base.setColorAt(0, QColor("#F3ECE1"))
    base.setColorAt(0.52, QColor("#EAE3D8"))
    base.setColorAt(1, QColor("#DEE9E1"))
    p.fillRect(0, 0, width, height, QBrush(base))

    glow = QRadialGradient(QPointF(width * 0.82, height * 0.18), width * 0.48)
    glow.setColorAt(0, QColor(233, 145, 110, 70))
    glow.setColorAt(1, QColor(233, 145, 110, 0))
    p.fillRect(0, 0, width, height, QBrush(glow))

    sage = QRadialGradient(QPointF(width * 0.18, height * 0.85), width * 0.5)
    sage.setColorAt(0, QColor(93, 137, 113, 58))
    sage.setColorAt(1, QColor(93, 137, 113, 0))
    p.fillRect(0, 0, width, height, QBrush(sage))

    # Abstract soft geometry instead of a fake screenshot.
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 27))
    p.drawEllipse(QPointF(width * 0.22, height * 0.28), 235, 235)
    p.setBrush(QColor(255, 255, 255, 18))
    p.drawEllipse(QPointF(width * 0.78, height * 0.7), 310, 310)
    p.setBrush(QColor(66, 106, 84, 16))
    p.drawEllipse(QPointF(width * 0.52, height * 1.03), 520, 170)

    # Light typographic desktop detail.
    p.setPen(QColor(93, 137, 113, 140))
    p.setFont(theme.font(9.0, QFont.Weight.DemiBold))
    p.drawText(QRectF(54, 44, 420, 26), Qt.AlignmentFlag.AlignLeft, "STAND TALL  ·  TAKE A BREATH")
    p.setPen(QColor(41, 59, 50, 65))
    p.setFont(theme.font(9.0))
    p.drawText(
        QRectF(width - 270, 44, 216, 26),
        Qt.AlignmentFlag.AlignRight,
        "桌面 · 专注中",
    )
    p.end()
    return image


def render_main() -> QImage:
    window = MainWindow(30, True, snapshot_running())
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.update_view(snapshot_running(), 30, True)
    window.update_break_view(True, 32 * 60, False, 8, True, 45)
    window.show()
    QTest.qWait(200)
    pixmap = window.grab()
    window.hide()
    return pixmap.toImage()


def render_reminder() -> QImage:
    window = ReminderWindow()
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show_reminder(snapshot_waiting(), 30)
    QTest.qWait(260)
    window.setWindowOpacity(1.0)
    pixmap = window.grab()
    window.hide()
    return pixmap.toImage()


def render_rest() -> QImage:
    window = RestWindow()
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show_rest(8 * 60, allow_close=True)
    QTest.qWait(220)
    pixmap = window.grab()
    window.hide_rest()
    return pixmap.toImage()


def render_status() -> QImage:
    bar = StatusBar()
    bar.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    bar.update_view(
        snapshot_running(),
        30,
        True,
        32 * 60,
        8,
        True,
        False,
        45,
    )
    bar.show_bar()
    QTest.qWait(160)
    pixmap = bar.grab()
    bar.hide()
    return pixmap.toImage()


def render_settings() -> QImage:
    dialog = BreakSettingsDialog(45, 8, True, True)
    dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    dialog.show()
    QTest.qWait(180)
    pixmap = dialog.grab()
    dialog.hide()
    return pixmap.toImage()


def compose(main: QImage, reminder: QImage, width: int = 1440, height: int = 900) -> QImage:
    canvas = wallpaper(width, height)
    p = QPainter(canvas)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    main_x, main_y = 300, 144
    p.drawImage(main_x, main_y, main)
    reminder_x, reminder_y = 818, 472
    p.drawImage(reminder_x, reminder_y, reminder)
    p.setPen(QColor(41, 59, 50, 90))
    p.setFont(theme.font(8.8))
    p.drawText(
        QRectF(54, height - 62, 600, 24),
        Qt.AlignmentFlag.AlignLeft,
        "一个安静的倒计时，替你记得起身、放松、再坐直。",
    )
    p.end()
    return canvas


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    app = QApplication([])
    configure_application(app)
    main_image = render_main()
    reminder_image = render_reminder()
    rest_image = render_rest()
    status_image = render_status()
    settings_image = render_settings()
    main_canvas = compose(main_image, reminder_image)
    p = QPainter(main_canvas)
    p.drawImage(1094, 74, status_image)
    p.end()
    main_canvas.save(str(DOCS / "screenshot-main.png"))

    canvas = wallpaper(1000, 760)
    p = QPainter(canvas)
    x = (1000 - reminder_image.width()) // 2
    y = (760 - reminder_image.height()) // 2
    p.drawImage(x, y, reminder_image)
    p.end()
    canvas.save(str(DOCS / "screenshot-reminder.png"))

    rest_canvas = wallpaper(1000, 760)
    p = QPainter(rest_canvas)
    x = (1000 - rest_image.width()) // 2
    y = (760 - rest_image.height()) // 2
    p.drawImage(x, y, rest_image)
    p.end()
    rest_canvas.save(str(DOCS / "screenshot-rest.png"))

    status_canvas = wallpaper(700, 280)
    p = QPainter(status_canvas)
    p.drawImage((700 - status_image.width()) // 2, (280 - status_image.height()) // 2, status_image)
    p.end()
    status_canvas.save(str(DOCS / "screenshot-status.png"))

    settings_canvas = wallpaper(900, 700)
    p = QPainter(settings_canvas)
    p.drawImage(
        (900 - settings_image.width()) // 2,
        (700 - settings_image.height()) // 2,
        settings_image,
    )
    p.end()
    settings_canvas.save(str(DOCS / "screenshot-settings.png"))
    print("Saved previews to", DOCS)


if __name__ == "__main__":
    main()
