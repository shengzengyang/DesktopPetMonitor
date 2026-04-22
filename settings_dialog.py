from PyQt5.QtWidgets import (QDialog, QFormLayout, QComboBox, QSlider, QCheckBox,
                             QSpinBox, QDoubleSpinBox, QHBoxLayout, QVBoxLayout,
                             QLabel, QPushButton, QWidget, QTabWidget, QFrame,
                             QLineEdit, QPlainTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal

import pets
from i18n import t, available_languages, current_language


_STYLE = """
QDialog { background: #0f172a; color: #e2e8f0; }
QLabel { color: #e2e8f0; font-size: 12px; }
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QPlainTextEdit {
    background: #1e293b; color: #e2e8f0; border: 1px solid #334155;
    border-radius: 4px; padding: 4px 8px; min-width: 120px;
}
QComboBox::drop-down { border: 0; }
QCheckBox { color: #e2e8f0; spacing: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 3px;
    border: 1px solid #475569; background: #1e293b; }
QCheckBox::indicator:checked { background: #60a5fa; border-color: #60a5fa; }
QPushButton {
    background: #1e293b; color: #e2e8f0; border: 1px solid #334155;
    border-radius: 6px; padding: 6px 18px; font-size: 12px;
}
QPushButton:hover { background: #334155; }
QPushButton[primary="true"] {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #60a5fa, stop:1 #a78bfa);
    color: white; border: none;
}
QPushButton[primary="true"]:hover { opacity: 0.9; }
QTabWidget::pane { border: 1px solid #334155; border-radius: 6px; top: -1px; }
QTabBar::tab { background: #1e293b; color: #94a3b8; padding: 6px 14px;
    border: 1px solid #334155; border-bottom: none;
    border-top-left-radius: 4px; border-top-right-radius: 4px; }
QTabBar::tab:selected { background: #0f172a; color: #e2e8f0; }
QSlider::groove:horizontal { height: 4px; background: #334155; border-radius: 2px; }
QSlider::handle:horizontal { background: #60a5fa; width: 14px; margin: -6px 0;
    border-radius: 7px; }
"""


class SettingsDialog(QDialog):
    applied = pyqtSignal(dict)

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle(t('settings.title'))
        self.setStyleSheet(_STYLE)
        self.setMinimumWidth(380)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._build_general(), t('settings.tab_general'))
        tabs.addTab(self._build_behavior(), t('settings.tab_behavior'))
        tabs.addTab(self._build_llm(), t('settings.tab_llm'))
        tabs.addTab(self._build_monitor(), t('settings.tab_monitor'))
        tabs.addTab(self._build_stats(), t('settings.tab_stats'))
        root.addWidget(tabs)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.cancel_btn = QPushButton(t('settings.cancel'))
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn = QPushButton(t('settings.ok'))
        self.ok_btn.setProperty("primary", True)
        self.ok_btn.clicked.connect(self._save)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.ok_btn)
        root.addLayout(btn_row)

    def _build_general(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(10)

        self.lang_combo = QComboBox()
        for code, display in available_languages():
            self.lang_combo.addItem(display, code)
        idx = self.lang_combo.findData(current_language())
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        form.addRow(t('settings.language'), self.lang_combo)

        self.pet_combo = QComboBox()
        for kind, name, exists in pets.available_kinds():
            label = name if exists else f"{name}{t('settings.pet_not_installed')}"
            self.pet_combo.addItem(label, kind)
            if not exists:
                idx = self.pet_combo.count() - 1
                self.pet_combo.model().item(idx).setEnabled(False)
        idx = self.pet_combo.findData(self.cfg.get('pet_kind'))
        if idx >= 0:
            self.pet_combo.setCurrentIndex(idx)
        form.addRow(t('settings.pet_model'), self.pet_combo)

        self.opacity_slider, opacity_wrap = self._slider_with_label(
            30, 100, int(self.cfg.get('pet_opacity') * 100), suffix='%')
        form.addRow(t('settings.opacity'), opacity_wrap)

        self.scale_slider, scale_wrap = self._slider_with_label(
            40, 250, int(self.cfg.get('pet_scale_factor') * 100), suffix='%')
        form.addRow(t('settings.scale'), scale_wrap)

        self.panel_opacity_slider, panel_opacity_wrap = self._slider_with_label(
            50, 100, int(self.cfg.get('panel_opacity') * 100), suffix='%')
        form.addRow(t('settings.panel_opacity'), panel_opacity_wrap)

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(10, 60)
        self.fps_spin.setValue(int(self.cfg.get('animate_fps')))
        form.addRow(t('settings.animate_fps'), self.fps_spin)

        self.particles_check = QCheckBox(t('settings.show_particles'))
        self.particles_check.setChecked(bool(self.cfg.get('show_particles')))
        form.addRow("", self.particles_check)

        return w

    def _build_behavior(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(10)

        self.edge_snap_check = QCheckBox(t('settings.edge_snap'))
        self.edge_snap_check.setChecked(bool(self.cfg.get('edge_snap')))
        form.addRow("", self.edge_snap_check)

        self.follow_mouse_check = QCheckBox(t('settings.follow_mouse'))
        self.follow_mouse_check.setChecked(bool(self.cfg.get('follow_mouse')))
        form.addRow("", self.follow_mouse_check)

        self.wander_check = QCheckBox(t('settings.wander_enable'))
        self.wander_check.setChecked(bool(self.cfg.get('wander_enable')))
        form.addRow("", self.wander_check)

        self.wander_speed_spin = QSpinBox()
        self.wander_speed_spin.setRange(1, 10)
        self.wander_speed_spin.setSuffix(t('settings.suffix_px_per_frame'))
        self.wander_speed_spin.setValue(int(self.cfg.get('wander_speed_px')))
        form.addRow(t('settings.wander_speed'), self.wander_speed_spin)

        self.wander_chance_slider, wander_chance_wrap = self._slider_with_label(
            0, 100, int(float(self.cfg.get('wander_chance')) * 100), suffix='%')
        form.addRow(t('settings.wander_chance'), wander_chance_wrap)

        self.random_spin = QSpinBox()
        self.random_spin.setRange(3, 60)
        self.random_spin.setSuffix(t('settings.suffix_seconds'))
        self.random_spin.setValue(int(self.cfg.get('random_behavior_sec')))
        form.addRow(t('settings.random_interval'), self.random_spin)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#334155;")
        form.addRow(sep)

        self.pomo_work_spin = QSpinBox()
        self.pomo_work_spin.setRange(5, 120)
        self.pomo_work_spin.setSuffix(t('settings.suffix_minutes'))
        self.pomo_work_spin.setValue(int(self.cfg.get('pomodoro_work_min')))
        form.addRow(t('settings.pomo_work'), self.pomo_work_spin)

        self.pomo_break_spin = QSpinBox()
        self.pomo_break_spin.setRange(1, 30)
        self.pomo_break_spin.setSuffix(t('settings.suffix_minutes'))
        self.pomo_break_spin.setValue(int(self.cfg.get('pomodoro_break_min')))
        form.addRow(t('settings.pomo_break'), self.pomo_break_spin)

        self.sit_spin = QSpinBox()
        self.sit_spin.setRange(0, 180)
        self.sit_spin.setSuffix(t('settings.suffix_minutes_zero_off'))
        self.sit_spin.setValue(int(self.cfg.get('sit_reminder_min')))
        form.addRow(t('settings.sit_reminder'), self.sit_spin)

        return w

    def _build_llm(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(10)

        self.llm_enable_check = QCheckBox(t('settings.llm_enable'))
        self.llm_enable_check.setChecked(bool(self.cfg.get('llm_enabled')))
        form.addRow("", self.llm_enable_check)

        self.llm_key_edit = QLineEdit()
        self.llm_key_edit.setEchoMode(QLineEdit.Password)
        self.llm_key_edit.setText(self.cfg.get('llm_api_key') or '')
        self.llm_key_edit.setPlaceholderText("sk-...")
        form.addRow(t('settings.llm_api_key'), self.llm_key_edit)

        self.llm_url_edit = QLineEdit()
        self.llm_url_edit.setText(self.cfg.get('llm_base_url') or '')
        self.llm_url_edit.setPlaceholderText("https://api.openai.com/v1")
        form.addRow(t('settings.llm_base_url'), self.llm_url_edit)

        self.llm_model_edit = QLineEdit()
        self.llm_model_edit.setText(self.cfg.get('llm_model') or '')
        self.llm_model_edit.setPlaceholderText("gpt-4o-mini")
        form.addRow(t('settings.llm_model'), self.llm_model_edit)

        self.llm_maxtok_spin = QSpinBox()
        self.llm_maxtok_spin.setRange(50, 2000)
        self.llm_maxtok_spin.setSingleStep(50)
        self.llm_maxtok_spin.setValue(int(self.cfg.get('llm_max_tokens')))
        form.addRow(t('settings.llm_max_tokens'), self.llm_maxtok_spin)

        self.llm_hist_spin = QSpinBox()
        self.llm_hist_spin.setRange(0, 50)
        self.llm_hist_spin.setValue(int(self.cfg.get('llm_history_limit')))
        form.addRow(t('settings.llm_history'), self.llm_hist_spin)

        self.llm_prompt_edit = QPlainTextEdit()
        self.llm_prompt_edit.setPlainText(self.cfg.get('llm_system_prompt') or '')
        self.llm_prompt_edit.setFixedHeight(100)
        form.addRow(t('settings.llm_system_prompt'), self.llm_prompt_edit)

        return w

    def _build_monitor(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(10)

        self.ip_interval_spin = QSpinBox()
        self.ip_interval_spin.setRange(30, 3600)
        self.ip_interval_spin.setSuffix(t('settings.suffix_seconds'))
        self.ip_interval_spin.setValue(int(self.cfg.get('ip_refresh_sec')))
        form.addRow(t('settings.ip_refresh'), self.ip_interval_spin)

        self.panel_refresh_spin = QSpinBox()
        self.panel_refresh_spin.setRange(500, 5000)
        self.panel_refresh_spin.setSingleStep(100)
        self.panel_refresh_spin.setSuffix(t('settings.suffix_ms'))
        self.panel_refresh_spin.setValue(int(self.cfg.get('panel_refresh_ms')))
        form.addRow(t('settings.panel_refresh'), self.panel_refresh_spin)

        self.alert_enable_check = QCheckBox(t('settings.alert_enable'))
        self.alert_enable_check.setChecked(bool(self.cfg.get('alert_enable')))
        form.addRow("", self.alert_enable_check)

        self.cpu_alert_spin = QSpinBox()
        self.cpu_alert_spin.setRange(50, 100)
        self.cpu_alert_spin.setSuffix(t('settings.suffix_pct'))
        self.cpu_alert_spin.setValue(int(self.cfg.get('alert_cpu_percent')))
        form.addRow(t('settings.cpu_alert'), self.cpu_alert_spin)

        self.mem_alert_spin = QSpinBox()
        self.mem_alert_spin.setRange(50, 100)
        self.mem_alert_spin.setSuffix(t('settings.suffix_pct'))
        self.mem_alert_spin.setValue(int(self.cfg.get('alert_mem_percent')))
        form.addRow(t('settings.mem_alert'), self.mem_alert_spin)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#334155;")
        form.addRow(sep)

        self.ip_alert_enable_check = QCheckBox(t('settings.ip_alert_enable'))
        self.ip_alert_enable_check.setChecked(bool(self.cfg.get('ip_alert_enable')))
        form.addRow("", self.ip_alert_enable_check)

        self.ip_alert_1_edit = QLineEdit()
        self.ip_alert_1_edit.setText(self.cfg.get('ip_alert_expected_1') or '')
        self.ip_alert_1_edit.setPlaceholderText("203.0.113.42")
        form.addRow(t('settings.ip_alert_expected_1'), self.ip_alert_1_edit)

        self.ip_alert_2_edit = QLineEdit()
        self.ip_alert_2_edit.setText(self.cfg.get('ip_alert_expected_2') or '')
        self.ip_alert_2_edit.setPlaceholderText("198.51.100.")
        form.addRow(t('settings.ip_alert_expected_2'), self.ip_alert_2_edit)

        hint = QLabel(t('settings.ip_alert_hint'))
        hint.setStyleSheet("color:#64748b; font-size:10px;")
        hint.setWordWrap(True)
        form.addRow("", hint)

        return w

    def _build_stats(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        stats = self.cfg.get('stats') or {}
        rows = [
            (t('settings.stats_interactions'), f"{stats.get('interactions', 0)}"),
            (t('settings.stats_pomodoros'), f"{stats.get('pomodoros_completed', 0)}"),
            (t('settings.stats_runtime'), f"{int(stats.get('runtime_sec', 0) / 60)}{t('settings.suffix_minutes')}"),
            (t('settings.stats_last_run'), str(stats.get('last_run') or t('settings.stats_first_run'))),
        ]
        for title, val in rows:
            row = QHBoxLayout()
            lbl = QLabel(title)
            lbl.setStyleSheet("color:#94a3b8;")
            v = QLabel(val)
            v.setStyleSheet("color:#fbbf24; font-weight: bold;")
            v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(lbl)
            row.addStretch(1)
            row.addWidget(v)
            layout.addLayout(row)

        layout.addStretch(1)
        return w

    def _slider_with_label(self, lo, hi, value, suffix=''):
        wrap = QWidget()
        h = QHBoxLayout(wrap)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        s = QSlider(Qt.Horizontal)
        s.setRange(lo, hi)
        s.setValue(value)
        lbl = QLabel(f"{value}{suffix}")
        lbl.setFixedWidth(42)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        s.valueChanged.connect(lambda v: lbl.setText(f"{v}{suffix}"))
        h.addWidget(s)
        h.addWidget(lbl)
        return s, wrap

    def _save(self):
        patch = {
            'pet_kind': self.pet_combo.currentData(),
            'pet_opacity': self.opacity_slider.value() / 100.0,
            'pet_scale_factor': self.scale_slider.value() / 100.0,
            'panel_opacity': self.panel_opacity_slider.value() / 100.0,
            'animate_fps': self.fps_spin.value(),
            'show_particles': self.particles_check.isChecked(),
            'edge_snap': self.edge_snap_check.isChecked(),
            'follow_mouse': self.follow_mouse_check.isChecked(),
            'random_behavior_sec': self.random_spin.value(),
            'pomodoro_work_min': self.pomo_work_spin.value(),
            'pomodoro_break_min': self.pomo_break_spin.value(),
            'sit_reminder_min': self.sit_spin.value(),
            'ip_refresh_sec': self.ip_interval_spin.value(),
            'panel_refresh_ms': self.panel_refresh_spin.value(),
            'alert_enable': self.alert_enable_check.isChecked(),
            'alert_cpu_percent': self.cpu_alert_spin.value(),
            'alert_mem_percent': self.mem_alert_spin.value(),
            'llm_enabled': self.llm_enable_check.isChecked(),
            'llm_api_key': self.llm_key_edit.text().strip(),
            'llm_base_url': self.llm_url_edit.text().strip() or 'https://api.openai.com/v1',
            'llm_model': self.llm_model_edit.text().strip() or 'gpt-4o-mini',
            'llm_max_tokens': self.llm_maxtok_spin.value(),
            'llm_history_limit': self.llm_hist_spin.value(),
            'llm_system_prompt': self.llm_prompt_edit.toPlainText().strip(),
            'wander_enable': self.wander_check.isChecked(),
            'wander_speed_px': self.wander_speed_spin.value(),
            'wander_chance': self.wander_chance_slider.value() / 100.0,
            'language': self.lang_combo.currentData(),
            'ip_alert_enable': self.ip_alert_enable_check.isChecked(),
            'ip_alert_expected_1': self.ip_alert_1_edit.text().strip(),
            'ip_alert_expected_2': self.ip_alert_2_edit.text().strip(),
        }
        self.cfg.update(patch)
        self.applied.emit(patch)
        self.accept()
