import sys
import time
import os
from datetime import datetime

from PyQt5.QtCore import Qt, QCoreApplication, QTimer, QSize
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QFont, QColor

import live2d.v3 as live2d

from config import get_config
import pets
from pet_widget import PetWidget
from settings_dialog import SettingsDialog
from reminder import SitReminder
from llm_service import LLMService
from logger import log, log_path
from i18n import set_language, t


def _make_tray_icon(glyph='🐾'):
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    f = QFont('Segoe UI Emoji')
    f.setPointSize(32)
    p.setFont(f)
    p.setPen(QColor(0, 0, 0))
    p.drawText(pix.rect(), Qt.AlignCenter, glyph)
    p.end()
    return QIcon(pix)


class App:
    def __init__(self):
        self.cfg = get_config()
        set_language(self.cfg.get('language') or 'zh')
        log.info('=== App starting ===')
        log.info('log file: %s', log_path())
        log.info('language=%s pet_kind=%s scale=%.2f opacity=%.2f',
                 self.cfg.get('language'),
                 self.cfg.get('pet_kind'),
                 float(self.cfg.get('pet_scale_factor')),
                 float(self.cfg.get('pet_opacity')))
        # Migrate legacy emoji pet kinds to haru
        if self.cfg.get('pet_kind') not in [k for k, _ in pets.list_kinds()]:
            self.cfg.set('pet_kind', pets.DEFAULT_KIND)

        QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        live2d.init()

        self.pet = PetWidget()
        self.pet.show()

        self.sit_reminder = SitReminder(self.cfg.get('sit_reminder_min'), parent=self.pet)
        if self.cfg.get('sit_reminder_min') > 0:
            self.sit_reminder.start()
        self.sit_reminder.ping.connect(self.pet.on_sit_reminder)

        self.llm = LLMService(self.cfg, parent=self.pet)
        self.llm.replied.connect(self.pet.on_llm_reply)
        self.llm.failed.connect(self.pet.on_llm_fail)

        self.pet.chatSubmitted.connect(self._on_chat_submitted)

        self.pet._ensure_panel()
        panel = self.pet.panel
        panel.alertTriggered.connect(self.pet.alert)
        panel.alertCleared.connect(self.pet.clear_alert)
        panel.pomodoro.phaseChanged.connect(self._on_pomo_phase)
        panel.pomodoro.tick.connect(self._on_pomo_tick)
        panel.pomodoro.completed.connect(
            lambda: self.cfg.bump_stat('pomodoros_completed')
        )
        panel.chatRequested.connect(self.pet.open_chat)
        panel.ipAlertTriggered.connect(self._on_ip_alert)
        panel.ipAlertCleared.connect(self._on_ip_alert_cleared)

        self.pet.settingsRequested.connect(self.show_settings)
        self.pet.quitRequested.connect(self.quit)

        self._tray = self._build_tray()
        self._tray.show()

        self._start_time = time.time()
        stats = self.cfg.get('stats') or {}
        stats['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        self.cfg.set('stats', stats)

        self._runtime_timer = QTimer()
        self._runtime_timer.setInterval(60000)
        self._runtime_timer.timeout.connect(self._save_runtime)
        self._runtime_timer.start()

        self.app.aboutToQuit.connect(self._on_quit)

    def _build_tray(self):
        tray = QSystemTrayIcon()
        tray.setIcon(_make_tray_icon('🐾'))
        tray.setToolTip("桌宠监视器")

        menu = QMenu()
        menu.setStyleSheet(
            "QMenu{background:#1e293b;color:#e2e8f0;border:1px solid #334155; padding:4px;}"
            "QMenu::item{padding:6px 20px;}"
            "QMenu::item:selected{background:#334155;}"
            "QMenu::separator{height:1px;background:#334155;margin:4px 0;}"
        )

        act_show = QAction(t('tray.show_pet'), menu)
        act_show.triggered.connect(self._toggle_pet)
        menu.addAction(act_show)

        act_panel = QAction(t('tray.show_panel'), menu)
        act_panel.triggered.connect(self.pet.toggle_panel)
        menu.addAction(act_panel)

        menu.addSeparator()

        pet_menu = menu.addMenu(t('tray.switch_pet'))
        self._tray_pet_menu = pet_menu
        self._rebuild_tray_pet_menu()

        menu.addSeparator()
        act_settings = QAction(t('tray.settings'), menu)
        act_settings.triggered.connect(self.show_settings)
        menu.addAction(act_settings)

        menu.addSeparator()
        act_quit = QAction(t('tray.quit'), menu)
        act_quit.triggered.connect(self.quit)
        menu.addAction(act_quit)

        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        return tray

    def _rebuild_tray_pet_menu(self):
        self._tray_pet_menu.clear()
        current = self.cfg.get('pet_kind')
        for kind, name, exists in pets.available_kinds():
            prefix = "✓ " if kind == current else "   "
            suffix = "" if exists else "  (未安装)"
            a = QAction(f"{prefix}{name}{suffix}", self._tray_pet_menu)
            a.setEnabled(exists)
            a.triggered.connect(lambda _, k=kind: self._switch_pet(k))
            self._tray_pet_menu.addAction(a)

    def _switch_pet(self, kind):
        self.pet.switch_pet(kind)
        self._rebuild_tray_pet_menu()

    def _toggle_pet(self):
        if self.pet.isVisible():
            self.pet.hide()
            self.pet.speech_bubble.hide()
            if self.pet.panel:
                self.pet.panel.hide()
        else:
            self.pet.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._toggle_pet()
        elif reason == QSystemTrayIcon.DoubleClick:
            self.pet.toggle_panel()

    def _on_pomo_phase(self, phase, remaining):
        if phase in ('work', 'break'):
            self.pet.on_pomodoro_start(phase)

    def _on_pomo_tick(self, phase, remaining):
        # Placeholder: coin accrual was removed with the state system. Kept
        # so the pomodoro signal still has a receiver if anything else needs
        # per-second ticks in the future.
        pass

    def _on_chat_submitted(self, text):
        preview = text[:80].replace('\n', ' ')
        log.info('chat submit: "%s" (len=%d)', preview, len(text))
        if self.llm.is_configured():
            self.pet.say(t('chat.thinking'), 1500)
            self.llm.ask(text)
        else:
            log.info('chat: LLM not configured, opening settings')
            self.pet.notice(t('chat.not_configured'), 3500)
            QTimer.singleShot(500, self.show_settings)

    def _on_ip_alert(self, got):
        log.warning('IP alert triggered: got=%s', got)
        self.pet.notice(t('notice.ip_alert', got=got), 9000)

    def _on_ip_alert_cleared(self):
        log.info('IP alert cleared')
        self.pet.notice(t('notice.ip_cleared'), 3500)

    def show_settings(self):
        dlg = SettingsDialog(self.cfg, parent=None)
        dlg.applied.connect(self._apply_settings)
        dlg.exec_()

    def _apply_settings(self, patch):
        # Log only keys — api keys are masked; useful diff of what changed.
        safe = {k: ('***' if 'key' in k.lower() else v) for k, v in patch.items()}
        log.info('settings applied: %s', safe)
        if 'language' in patch:
            set_language(patch['language'])
            # Existing widgets keep their old labels; show a one-liner hint.
            self.pet.notice(t('app.language_changed_restart'), 4000)
        if 'pet_kind' in patch:
            self._switch_pet(patch['pet_kind'])
        self.pet.apply_opacity()
        self.pet.apply_scale()
        self.pet.apply_fps()
        self.pet.apply_random_interval()
        if self.pet.panel:
            self.pet.panel.apply_refresh_interval()
        sit_min = self.cfg.get('sit_reminder_min')
        if sit_min > 0:
            self.sit_reminder.set_interval(sit_min)
            self.sit_reminder.start()
        else:
            self.sit_reminder.stop()

    def _save_runtime(self):
        delta = int(time.time() - self._start_time)
        self._start_time = time.time()
        self.cfg.bump_stat('runtime_sec', delta)

    def _on_quit(self):
        log.info('=== App quitting ===')
        self._save_runtime()
        try:
            live2d.dispose()
        except Exception:
            pass

    def quit(self):
        log.info('quit requested')
        self.app.quit()

    def run(self):
        return self.app.exec_()


def main():
    app = App()
    sys.exit(app.run())


if __name__ == '__main__':
    main()
