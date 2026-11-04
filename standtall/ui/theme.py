"""Light, calm visual language for StandTall."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase

INK = "#293B32"
INK_SOFT = "#506158"
MUTED = "#7E8B82"
FAINT = "#A6AFA8"
SAGE = "#5D8971"
SAGE_DARK = "#426A54"
SAGE_PALE = "#E0ECE3"
SAGE_TRACK = "#E7DED1"
PEACH = "#E9916E"
PEACH_PALE = "#FBE6DA"
CORAL = "#D67C5F"
CARD = "#FFFCF6"
CARD_ALT = "#F8F2E8"
BORDER = "#E9DFD1"
BORDER_STRONG = "#DACBBB"
PANEL_TOP = QColor(249, 245, 237, 253)
PANEL_BOTTOM = QColor(243, 236, 226, 253)
SHADOW = QColor(53, 38, 28, 18)

FONT_CANDIDATES = (
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "PingFang SC",
    "Noto Sans CJK SC",
    "Segoe UI",
)


def font_family() -> str:
    families = set(QFontDatabase.families())
    for candidate in FONT_CANDIDATES:
        if candidate in families:
            return candidate
    return "Sans Serif"


def font(size: float, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    result = QFont(font_family())
    result.setPointSizeF(size)
    result.setWeight(weight)
    return result


def app_font(size: float = 10.0) -> QFont:
    return font(size)


def global_qss() -> str:
    family = font_family()
    return f"""
    QWidget {{
        color: {INK};
    }}
    QLabel {{ background: transparent; }}
    QToolTip {{
        background: #2F3E35;
        color: #FFF8ED;
        border: 1px solid #4A5D50;
        border-radius: 7px;
        padding: 5px 8px;
        font-size: 9pt;
    }}
    QMenu {{
        background: #FFFCF6;
        color: {INK};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 8px 28px 8px 14px;
        border-radius: 6px;
        font-size: 9.5pt;
    }}
    QMenu::item:selected {{
        background: {SAGE_PALE};
        color: {SAGE_DARK};
    }}
    QMenu::separator {{
        height: 1px;
        background: {BORDER};
        margin: 5px 8px;
    }}
    QFrame#card {{
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: 18px;
    }}
    QPushButton#primary {{
        background: {SAGE};
        color: #FFFDF8;
        border: none;
        border-radius: 15px;
        padding: 8px 20px;
        font-size: 10.5pt;
        font-weight: 600;
    }}
    QPushButton#primary:hover {{ background: {SAGE_DARK}; }}
    QPushButton#primary:pressed {{ background: #355943; }}
    QPushButton#primary:disabled {{ background: #B8C8BC; color: #F2F4F1; }}
    QPushButton#secondary {{
        background: transparent;
        color: {INK_SOFT};
        border: 1px solid {BORDER_STRONG};
        border-radius: 15px;
        padding: 8px 16px;
        font-size: 10pt;
    }}
    QPushButton#secondary:hover {{
        background: {CARD_ALT};
        border-color: {MUTED};
        color: {INK};
    }}
    QPushButton#secondary:disabled {{ color: {FAINT}; border-color: {BORDER}; }}
    QPushButton#compactButton {{
        background: {SAGE_PALE};
        color: {SAGE_DARK};
        border: none;
        border-radius: 11px;
        padding: 6px 14px;
        font-size: 9pt;
        font-weight: 600;
    }}
    QPushButton#compactButton:hover {{ background: #D2E3D7; }}
    QPushButton#compactButton:disabled {{ background: #EFEBE4; color: {FAINT}; }}
    QPushButton#textButton {{
        background: transparent;
        color: {SAGE_DARK};
        border: none;
        padding: 4px 2px;
        font-size: 9pt;
    }}
    QPushButton#textButton:hover {{ color: {SAGE}; text-decoration: underline; }}
    QPushButton#preset {{
        background: #F3EDE3;
        color: #6C796F;
        border: 1px solid transparent;
        border-radius: 13px;
        padding: 7px 4px;
        font-size: 9pt;
    }}
    QPushButton#preset:hover {{ background: #EEE6D9; }}
    QPushButton#preset:checked {{
        background: {SAGE_PALE};
        color: {SAGE_DARK};
        border: 1px solid #BFD4C5;
        font-weight: 600;
    }}
    QSpinBox {{
        background: #F3EEE5;
        color: {INK};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 8px 12px;
        font-size: 12pt;
        selection-background-color: {SAGE};
    }}
    QSpinBox:focus {{ border: 1px solid {SAGE}; background: #FFFCF7; }}
    QSpinBox::up-button, QSpinBox::down-button {{
        width: 0; height: 0; border: none;
    }}
    QLineEdit#minuteInput {{
        background: #F3EEE5;
        color: {INK};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 7px 6px;
        font-size: 12pt;
        selection-background-color: {SAGE};
    }}
    QLineEdit#minuteInput:focus {{
        border: 1px solid {SAGE};
        background: #FFFCF7;
    }}
    QLineEdit#minuteInput:disabled {{
        background: #EFEAE1;
        color: {FAINT};
    }}
    QLabel#sectionTitle {{
        color: {INK};
        font-size: 11pt;
        font-weight: 600;
    }}
    QLabel#muted {{ color: {MUTED}; font-size: 9.3pt; }}
    QLabel#tiny {{ color: {FAINT}; font-size: 8.4pt; }}
    QLabel#caption {{ color: {MUTED}; font-size: 9pt; }}
    QLabel#postureTip {{
        background: rgba(255, 252, 246, 160);
        border: 1px solid {BORDER};
        border-radius: 11px;
        padding: 7px 12px;
        color: {MUTED};
        font-size: 8.6pt;
    }}
    QFrame#restCard {{
        background: #FBF0E5;
        border: 1px solid #F0DBC8;
        border-radius: 14px;
    }}
    """
