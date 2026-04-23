from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                             QProgressBar, QFrame, QPushButton)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QPen

from monitors import SystemMonitor
from ip_fetcher import IPFetcher
from reminder import Pomodoro
from i18n import t


_BAR_STYLE_OK = """
QProgressBar { background: rgba(255,255,255,0.08); border: none; border-radius: 4px; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #60a5fa, stop:1 #a78bfa); border-radius: 4px; }
"""
_BAR_STYLE_WARN = """
QProgressBar { background: rgba(255,255,255,0.08); border: none; border-radius: 4px; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #fbbf24, stop:1 #f97316); border-radius: 4px; }
"""
_BAR_STYLE_ALERT = """
QProgressBar { background: rgba(255,255,255,0.08); border: none; border-radius: 4px; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #f87171, stop:1 #ef4444); border-radius: 4px; }
"""

_BTN_STYLE = """
QPushButton { background:#1e293b; color:#e2e8f0; border:1px solid #334155;
    border-radius:6px; padding:4px 10px; font-size:11px; }
QPushButton:hover { background:#334155; }
QPushButton:pressed { background:#475569; }
"""


class StatRow(QWidget):
    def __init__(self, title):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(3)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel(title)
        self.title.setStyleSheet("color:#cbd5e1; font-size:11px;")
        self.value = QLabel("--")
        self.value.setStyleSheet("color:#e0f2fe; font-size:11px;")
        self.value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addWidget(self.title)
        top.addStretch(1)
        top.addWidget(self.value)

        self.bar = QProgressBar()
        self.bar.setFixedHeight(7)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet(_BAR_STYLE_OK)
        self.bar.setRange(0, 100)

        layout.addLayout(top)
        layout.addWidget(self.bar)
        self._level = 'ok'

    def update_row(self, value_text, percent, alert_pct=None):
        self.value.setText(value_text)
        p = max(0, min(100, int(percent)))
        self.bar.setValue(p)
        level = 'ok'
        if alert_pct is not None:
            if p >= alert_pct:
                level = 'alert'
            elif p >= alert_pct - 15:
                level = 'warn'
        if level != self._level:
            self._level = level
            if level == 'alert':
                self.bar.setStyleSheet(_BAR_STYLE_ALERT)
            elif level == 'warn':
                self.bar.setStyleSheet(_BAR_STYLE_WARN)
            else:
                self.bar.setStyleSheet(_BAR_STYLE_OK)


def _sep():
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet("background: rgba(255,255,255,0.12);")
    return line


def _mask_ip(ip):
    """Mask the last two octets of an IPv4 for display in privacy mode.
    Returns unchanged input if it doesn't look like IPv4 or is empty.
    """
    if not ip or ip in ('--', 'N/A', 'unknown', ''):
        return ip
    parts = str(ip).split('.')
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        return f"{parts[0]}.{parts[1]}.***.***"
    # IPv6 or other format — mask aggressively
    return '***.***.***.***'


class InfoPanel(QWidget):
    alertTriggered = pyqtSignal(str)
    alertCleared = pyqtSignal()
    chatRequested = pyqtSignal()
    ipAlertTriggered = pyqtSignal(str)  # emits "direct / proxy" string
    ipAlertCleared = pyqtSignal()

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(320)

        self.monitor = SystemMonitor()
        self.ip_fetcher = IPFetcher()
        self.pomodoro = Pomodoro(
            cfg.get('pomodoro_work_min'),
            cfg.get('pomodoro_break_min'),
            parent=self,
        )
        self.pomodoro.tick.connect(self._on_pomo_tick)
        self.pomodoro.phaseChanged.connect(self._on_pomo_phase)

        self._build_ui()

        self._tick_counter = 0
        self._ip_refresh_ticks = max(10, int(cfg.get('ip_refresh_sec')))
        self._alerting = False
        self._ip_alerting = False
        self.ip_fetcher.refresh()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self._tick()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(8)

        title_row = QHBoxLayout()
        title = QLabel(t('panel.title'))
        title.setStyleSheet(
            "color:white; font-weight:bold; font-size:14px;"
            "font-family:'Microsoft YaHei','Segoe UI',sans-serif;"
        )
        title_row.addWidget(title)
        title_row.addStretch(1)
        self.pomo_label = QLabel("")
        self.pomo_label.setStyleSheet("color:#fbbf24; font-size:11px; font-weight:bold;")
        title_row.addWidget(self.pomo_label)
        outer.addLayout(title_row)
        outer.addWidget(_sep())

        self.direct_ip_label = QLabel()
        self.direct_ip_label.setTextFormat(Qt.RichText)
        self.direct_ip_label.setStyleSheet("color:#e2e8f0; font-size:11px;")
        self.direct_ip_label.setWordWrap(True)
        outer.addWidget(self.direct_ip_label)

        self.proxy_ip_label = QLabel()
        self.proxy_ip_label.setTextFormat(Qt.RichText)
        self.proxy_ip_label.setStyleSheet("color:#e2e8f0; font-size:11px;")
        self.proxy_ip_label.setWordWrap(True)
        outer.addWidget(self.proxy_ip_label)

        self.net_label = QLabel()
        self.net_label.setTextFormat(Qt.RichText)
        self.net_label.setStyleSheet("color:#e2e8f0; font-size:11px;")
        outer.addWidget(self.net_label)

        outer.addWidget(_sep())

        self.cpu_row = StatRow(t('panel.cpu'))
        self.mem_row = StatRow(t('panel.memory'))
        self.gpu_row = StatRow(t('panel.gpu'))
        self.vram_row = StatRow(t('panel.vram'))
        outer.addWidget(self.cpu_row)
        outer.addWidget(self.mem_row)
        outer.addWidget(self.gpu_row)
        outer.addWidget(self.vram_row)

        outer.addWidget(_sep())

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.pomo_btn = QPushButton(t('panel.pomodoro_btn_start'))
        self.pomo_btn.setStyleSheet(_BTN_STYLE)
        self.pomo_btn.clicked.connect(self._toggle_pomodoro)
        btn_row.addWidget(self.pomo_btn)

        self.chat_btn = QPushButton(t('panel.chat_btn'))
        self.chat_btn.setStyleSheet(_BTN_STYLE)
        self.chat_btn.clicked.connect(self.chatRequested.emit)
        btn_row.addWidget(self.chat_btn)

        self.ip_btn = QPushButton(t('panel.refresh_ip_btn'))
        self.ip_btn.setStyleSheet(_BTN_STYLE)
        self.ip_btn.clicked.connect(self.ip_fetcher.refresh)
        btn_row.addWidget(self.ip_btn)
        outer.addLayout(btn_row)

        tip = QLabel(t('panel.tip'))
        tip.setStyleSheet("color:#64748b; font-size:10px;")
        tip.setAlignment(Qt.AlignCenter)
        outer.addWidget(tip)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 14, 14)
        alpha = int(255 * max(0.5, min(1.0, self.cfg.get('panel_opacity'))))
        p.fillPath(path, QColor(15, 23, 42, alpha))
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.drawPath(path)

    def showEvent(self, event):
        interval = max(300, int(self.cfg.get('panel_refresh_ms')))
        self.timer.start(interval)
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def _tick(self):
        self._tick_counter += 1
        sec_per_tick = max(0.3, self.cfg.get('panel_refresh_ms') / 1000.0)
        ip_every = max(1, int(self._ip_refresh_ticks / sec_per_tick))
        if self._tick_counter % ip_every == 1:
            self.ip_fetcher.refresh()

        direct_ip, proxy_ip = self.ip_fetcher.get()
        # Alert check uses the REAL IPs (we always want mismatch detection
        # to work, privacy mode is UI-only).
        self._check_ip_alert(direct_ip, proxy_ip)
        # Mask for display if privacy mode is on.
        if self.cfg.get('privacy_mode'):
            direct_ip_disp, proxy_ip_disp = _mask_ip(direct_ip), _mask_ip(proxy_ip)
        else:
            direct_ip_disp, proxy_ip_disp = direct_ip, proxy_ip
        self.direct_ip_label.setText(
            f"<span style='color:#94a3b8'>{t('panel.direct_ip')}</span> "
            f"<b style='color:#fbbf24'>{direct_ip_disp}</b>"
        )
        self.proxy_ip_label.setText(
            f"<span style='color:#94a3b8'>{t('panel.proxy_ip')}</span> "
            f"<b style='color:#34d399'>{proxy_ip_disp}</b>"
        )

        net = self.monitor.network()
        self.net_label.setText(
            f"<span style='color:#94a3b8'>{t('panel.network')}</span> "
            f"<b style='color:#38bdf8'>↑ {SystemMonitor.fmt_speed(net['up'])}</b>"
            f" &nbsp; "
            f"<b style='color:#f472b6'>↓ {SystemMonitor.fmt_speed(net['down'])}</b>"
        )

        cpu_alert = self.cfg.get('alert_cpu_percent')
        mem_alert = self.cfg.get('alert_mem_percent')

        cpu = self.monitor.cpu()
        self.cpu_row.update_row(
            f"{cpu['percent']:.0f}% · {cpu['cores']}核 · {cpu['freq_ghz']:.2f}GHz",
            cpu['percent'], cpu_alert,
        )

        mem = self.monitor.memory()
        self.mem_row.update_row(
            f"{mem['used_gb']:.1f} / {mem['total_gb']:.1f} GB · {mem['percent']:.0f}%",
            mem['percent'], mem_alert,
        )

        gpu = self.monitor.gpu()
        if gpu:
            temp = f" · {gpu['temp']}°C" if gpu['temp'] is not None else ""
            self.gpu_row.update_row(f"{gpu['percent']:.0f}%{temp}", gpu['percent'])
            self.vram_row.update_row(
                f"{gpu['mem_used_gb']:.1f} / {gpu['mem_total_gb']:.1f} GB",
                gpu['mem_percent'],
            )
        else:
            self.gpu_row.update_row(t('panel.no_gpu'), 0)
            self.vram_row.update_row("N/A", 0)

        if self.cfg.get('alert_enable'):
            reason = None
            if cpu['percent'] >= cpu_alert:
                reason = f"CPU {cpu['percent']:.0f}%"
            elif mem['percent'] >= mem_alert:
                reason = f"内存 {mem['percent']:.0f}%"
            if reason and not self._alerting:
                self._alerting = True
                self.alertTriggered.emit(reason)
            elif not reason and self._alerting:
                self._alerting = False
                self.alertCleared.emit()

        self.adjustSize()

    def _toggle_pomodoro(self):
        if self.pomodoro.is_running():
            self.pomodoro.stop()
            self.pomo_btn.setText(t('panel.pomodoro_btn_start'))
        else:
            self.pomodoro.configure(
                self.cfg.get('pomodoro_work_min'),
                self.cfg.get('pomodoro_break_min'),
            )
            self.pomodoro.start_work()

    def _on_pomo_tick(self, phase, remaining):
        label = t('panel.pomo_work') if phase == 'work' else t('panel.pomo_break')
        self.pomo_label.setText(f"{label} {Pomodoro.fmt(remaining)}")
        self.pomo_btn.setText(t('panel.pomodoro_btn_stop'))

    def _on_pomo_phase(self, phase, remaining):
        if phase == 'idle':
            self.pomo_label.setText("")
            self.pomo_btn.setText(t('panel.pomodoro_btn_start'))
        else:
            self._on_pomo_tick(phase, remaining)

    def _check_ip_alert(self, direct_ip, proxy_ip):
        if not self.cfg.get('ip_alert_enable'):
            if self._ip_alerting:
                self._ip_alerting = False
                self.ipAlertCleared.emit()
            return
        expected = [
            (self.cfg.get('ip_alert_expected_1') or '').strip(),
            (self.cfg.get('ip_alert_expected_2') or '').strip(),
        ]
        expected = [e for e in expected if e]
        if not expected:
            return  # no expected IPs configured → silent
        got = [(direct_ip or '').strip(), (proxy_ip or '').strip()]
        # Skip if we haven't actually fetched yet (both empty/placeholder)
        if not any(g and g not in ('--', 'N/A', 'unknown') for g in got):
            return
        matched = any(
            g and (g == e or g.startswith(e))
            for g in got for e in expected
        )
        if not matched and not self._ip_alerting:
            self._ip_alerting = True
            self.ipAlertTriggered.emit(f"{direct_ip} / {proxy_ip}")
        elif matched and self._ip_alerting:
            self._ip_alerting = False
            self.ipAlertCleared.emit()

    def apply_refresh_interval(self):
        self._ip_refresh_ticks = max(10, int(self.cfg.get('ip_refresh_sec')))
        if self.isVisible():
            interval = max(300, int(self.cfg.get('panel_refresh_ms')))
            self.timer.start(interval)
