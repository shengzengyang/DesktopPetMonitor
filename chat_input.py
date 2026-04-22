from PyQt5.QtWidgets import (QWidget, QLineEdit, QHBoxLayout, QPushButton,
                             QApplication, QLabel, QVBoxLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QPen, QBrush, QFont

from i18n import t


_STYLE = """
QLineEdit { background: #1e293b; color: #f1f5f9; border: 1px solid #475569;
    border-radius: 6px; padding: 6px 10px; font-size: 13px;
    font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; }
QLineEdit:focus { border: 1px solid #60a5fa; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #60a5fa, stop:1 #a78bfa);
    color: white; border: none; border-radius: 6px; padding: 6px 14px;
    font-size: 12px; font-weight: bold; }
QPushButton:hover { background: #60a5fa; }
QLabel { color: #94a3b8; font-size: 11px; }
"""


class ChatInput(QWidget):
    submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Deliberately NOT using Qt.Tool — on Windows, hiding a Qt.Tool window
        # that owns another Qt.Tool window (the pet) can cause the owner to
        # disappear. Use Popup instead: it's always-on-top, frameless, and
        # auto-closes on outside click (nice UX).
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Popup
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setStyleSheet(_STYLE)
        self.setFixedSize(360, 66)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(4)

        hint = QLabel(t('chat.hint'))
        root.addWidget(hint)

        row = QHBoxLayout()
        row.setSpacing(6)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(t('chat.placeholder'))
        self.edit.returnPressed.connect(self._submit)
        row.addWidget(self.edit, 1)

        self.send_btn = QPushButton(t('chat.send'))
        self.send_btn.clicked.connect(self._submit)
        row.addWidget(self.send_btn)
        root.addLayout(row)

    def open_above(self, anchor_rect):
        screen = QApplication.primaryScreen().availableGeometry()
        bw, bh = self.width(), self.height()
        x = anchor_rect.x() + anchor_rect.width() // 2 - bw // 2
        y = anchor_rect.y() - bh - 10
        if y < screen.top() + 4:
            y = anchor_rect.y() + anchor_rect.height() + 10
        x = max(screen.left() + 4, min(x, screen.right() - bw - 4))
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        self.edit.setFocus()
        self.edit.selectAll()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 10, 10)
        p.fillPath(path, QColor(15, 23, 42, 245))
        p.setPen(QPen(QColor(96, 165, 250, 180), 1.2))
        p.drawPath(path)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    def _submit(self):
        text = self.edit.text().strip()
        if not text:
            return
        self.edit.clear()
        self.hide()
        self.submitted.emit(text)
