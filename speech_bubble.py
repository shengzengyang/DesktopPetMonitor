from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect
from PyQt5.QtGui import (QPainter, QColor, QPainterPath, QPen, QBrush,
                         QPolygon, QFont)


class SpeechBubble(QWidget):
    STYLE_NORMAL = 'normal'
    STYLE_NOTICE = 'notice'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_NoSystemBackground)

        self._text = ""
        self._style = self.STYLE_NORMAL
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        self.setFixedSize(260, 56)

    def show_message(self, text, duration_ms, anchor_rect, style='normal'):
        self._text = text
        self._style = style
        self._resize_to_text()
        self._position_above(anchor_rect)
        self.show()
        self.raise_()
        self._hide_timer.start(max(500, int(duration_ms)))
        self.update()

    def _resize_to_text(self):
        font = QFont('Microsoft YaHei', 10, QFont.Bold)
        fm = self.fontMetrics()
        self.setFont(font)
        fm = self.fontMetrics()
        w = min(fm.horizontalAdvance(self._text) + 32, 420)
        h = fm.height() + 22
        self.setFixedSize(max(80, w), max(40, h))

    def _position_above(self, anchor_rect):
        screen = QApplication.primaryScreen().availableGeometry()
        bw, bh = self.width(), self.height()
        x = anchor_rect.x() + anchor_rect.width() // 2 - bw // 2
        y = anchor_rect.y() - bh - 4
        if y < screen.top() + 4:
            y = anchor_rect.y() + anchor_rect.height() + 4
        x = max(screen.left() + 4, min(x, screen.right() - bw - 4))
        self.move(x, y)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        w, h = self.width(), self.height()

        if self._style == self.STYLE_NOTICE:
            fill = QColor(254, 243, 199, 245)
            border = QColor(245, 158, 11, 230)
            text_col = QColor(120, 53, 15)
        else:
            fill = QColor(255, 255, 255, 248)
            border = QColor(200, 200, 200, 220)
            text_col = QColor(50, 50, 50)

        bubble_h = h - 10
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, bubble_h, 12, 12)
        tri = QPolygon([
            QPoint(w // 2 - 7, bubble_h),
            QPoint(w // 2, bubble_h + 9),
            QPoint(w // 2 + 7, bubble_h),
        ])
        p.setBrush(QBrush(fill))
        p.setPen(QPen(border, 1.2))
        p.drawPath(path)
        p.drawPolygon(tri)

        p.setPen(text_col)
        p.setFont(QFont('Microsoft YaHei', 10, QFont.Bold))
        p.drawText(QRect(0, 0, w, bubble_h), Qt.AlignCenter, self._text)
