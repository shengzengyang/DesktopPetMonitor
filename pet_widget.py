import os
import random
from PyQt5.QtWidgets import QOpenGLWidget, QApplication, QMenu, QShortcut
from PyQt5.QtCore import Qt, QTimer, QRect, pyqtSignal
from PyQt5.QtGui import QCursor, QKeySequence

import live2d.v3 as live2d
from live2d.v3 import MotionPriority

# Motions whose motion3.json was authored as Loop:true. live2d-py does NOT
# honor the Loop flag automatically — we have to detect IsMotionFinished and
# re-trigger. Keep this list in sync with tools/generate_motions.py.
LOOPING_GROUPS = {'Idle', 'Dance', 'Run'}

import pets
from logger import log
from i18n import t
from config import get_config
from info_panel import InfoPanel
from speech_bubble import SpeechBubble
from chat_input import ChatInput


class PetWidget(QOpenGLWidget):
    quitRequested = pyqtSignal()
    settingsRequested = pyqtSignal()
    chatSubmitted = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.cfg = get_config()

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_AlwaysStackOnTop)

        self.pet_def = pets.get(self.cfg.get('pet_kind'))
        base_w, base_h = self.pet_def['size']
        scale = max(0.4, min(2.5, float(self.cfg.get('pet_scale_factor'))))
        self._base_size = (base_w, base_h)
        self._w, self._h = int(base_w * scale), int(base_h * scale)
        self.resize(self._w, self._h)
        self._place_initial()

        op = float(self.cfg.get('pet_opacity'))
        if op < 1.0:
            self.setWindowOpacity(max(0.3, op))

        self.model = None
        self.state = 'idle'
        self.facing = 1
        self._load_failed = False

        # Parent both windows to self so Qt tracks ownership and doesn't
        # auto-hide the pet when the chat input closes (Qt.Tool quirk on Win).
        self.speech_bubble = SpeechBubble(parent=self)
        self.chat_input = ChatInput(parent=self)
        self.chat_input.submitted.connect(self.chatSubmitted.emit)
        self.panel = None

        self._chat_shortcut = QShortcut(QKeySequence("Ctrl+Space"), self)
        self._chat_shortcut.setContext(Qt.ApplicationShortcut)
        self._chat_shortcut.activated.connect(self.open_chat)

        self._drag_offset = None
        self._press_global = None
        self._drag_moved = False
        self._click_pending_timer = None

        self._save_pos_timer = QTimer(self)
        self._save_pos_timer.setSingleShot(True)
        self._save_pos_timer.timeout.connect(self._persist_pos)

        self._random_timer = QTimer(self)
        self._random_timer.timeout.connect(self._random_behavior)
        self._random_timer.start(int(self.cfg.get('random_behavior_sec')) * 1000)

        self._wander_target_x = None
        self._wander_target_y = None
        self._wander_timer = QTimer(self)
        self._wander_timer.setInterval(33)
        self._wander_timer.timeout.connect(self._wander_step)

        # Last-started looping motion. Auto-retriggered when it finishes so
        # Loop:true motions actually loop (live2d-py doesn't honor the flag).
        self._loop_motion = None

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._anim_tick)
        fps = max(15, min(60, int(self.cfg.get('animate_fps'))))
        self._anim_timer.start(int(1000 / fps))

    # ---------- window placement ----------
    def _place_initial(self):
        geo = QApplication.primaryScreen().availableGeometry()
        pos = self.cfg.get('pet_pos')
        if isinstance(pos, list) and len(pos) == 2:
            x, y = pos
            x = max(geo.left(), min(x, geo.right() - self._w))
            y = max(geo.top(), min(y, geo.bottom() - self._h))
            self.move(x, y)
        else:
            self.move(geo.width() - self._w - 40, geo.height() - self._h - 60)

    def _persist_pos(self):
        self.cfg.set('pet_pos', [self.x(), self.y()])

    def _schedule_save_pos(self):
        self._save_pos_timer.start(800)

    # ---------- GL lifecycle ----------
    def initializeGL(self):
        live2d.glInit()
        self._load_model(self.cfg.get('pet_kind'))

    def _load_model(self, kind):
        path = pets.resolve_model_path(kind)
        log.info('pet: loading model kind=%s path=%s', kind, path)
        if not path:
            log.error('pet: model path missing for kind=%s', kind)
            self._load_failed = True
            return
        self.pet_def = pets.get(kind)
        base_w, base_h = self.pet_def['size']
        scale = max(0.4, min(2.5, float(self.cfg.get('pet_scale_factor'))))
        self._base_size = (base_w, base_h)
        self._w, self._h = int(base_w * scale), int(base_h * scale)
        self.resize(self._w, self._h)
        try:
            self.model = live2d.LAppModel()
            self.model.LoadModelJson(path)
            self.model.Resize(self.width(), self.height())
            self._load_failed = False
            log.info('pet: model loaded OK (%dx%d)', self.width(), self.height())
            # Start idle breathing so doro is visually alive right away.
            # _anim_tick will keep re-triggering it (live2d-py doesn't loop).
            self._play_motion_for_state('idle_random')
        except Exception as e:
            log.exception('pet: model load crashed: %s', e)
            self._load_failed = True
            self.model = None

    def resizeGL(self, w, h):
        if self.model:
            self.model.Resize(w, h)

    def paintGL(self):
        live2d.clearBuffer()
        if self.model is None:
            return
        self.model.Update()
        self.model.Draw()

    # ---------- public API ----------
    def switch_pet(self, kind):
        log.info('switch_pet: kind=%s', kind)
        if not pets.resolve_model_path(kind):
            log.warning('switch_pet: model not installed for kind=%s', kind)
            self.say(t('pet.not_ready', name=pets.get(kind)['name']), 2500)
            return
        self.makeCurrent()
        self._load_model(kind)
        self.cfg.set('pet_kind', kind)
        self.say(t('pet.i_am', name=self.pet_def['name']), 2500)
        self._play_motion_for_state('happy')

    def apply_opacity(self):
        target = max(0.3, float(self.cfg.get('pet_opacity')))
        log.info('apply_opacity: %.2f', target)
        # Qt on Windows won't repaint the translucent buffer if the delta is
        # very small; briefly bouncing via 1.0 forces WS_EX_LAYERED rebuild.
        self.setWindowOpacity(1.0)
        self.setWindowOpacity(target)
        wh = self.windowHandle()
        if wh is not None:
            wh.setOpacity(target)
        self.update()

    def apply_scale(self):
        scale = max(0.4, min(2.5, float(self.cfg.get('pet_scale_factor'))))
        base_w, base_h = self._base_size
        new_w, new_h = int(base_w * scale), int(base_h * scale)
        cx = self.x() + self._w // 2
        cy = self.y() + self._h // 2
        self._w, self._h = new_w, new_h
        self.resize(new_w, new_h)
        self.move(cx - new_w // 2, cy - new_h // 2)
        self._schedule_save_pos()

    def scale_by(self, delta):
        cur = float(self.cfg.get('pet_scale_factor'))
        new_scale = max(0.4, min(2.5, round(cur + delta, 2)))
        if abs(new_scale - cur) < 0.001:
            return
        self.cfg.set('pet_scale_factor', new_scale)
        self.apply_scale()
        self.say(t('pet.size_set', pct=int(new_scale * 100)), 1200)

    def apply_fps(self):
        fps = max(15, min(60, int(self.cfg.get('animate_fps'))))
        self._anim_timer.start(int(1000 / fps))

    def apply_random_interval(self):
        self._random_timer.start(int(self.cfg.get('random_behavior_sec')) * 1000)

    def say(self, text, duration_ms=2500, style='normal'):
        # Safety net: if anything caused pet to hide (Qt.Tool focus quirks),
        # force it visible again before we anchor a speech bubble to it.
        if not self.isVisible():
            self.show()
        self.raise_()
        self.speech_bubble.show_message(text, duration_ms, self.frameGeometry(), style)

    def notice(self, text, duration_ms=4000):
        self.say(text, duration_ms, style='notice')

    def alert(self, reason):
        self.state = 'alert'
        self._play_expression('alert')
        chats = self.pet_def['chats'].get('alert', ["警报!"])
        self.notice(f"{random.choice(chats)} ({reason})", 5000)

    def clear_alert(self):
        if self.state == 'alert':
            self.state = 'idle'
            self._reset_expression()

    def on_pomodoro_start(self, phase):
        if phase == 'work':
            self.say(random.choice(self.pet_def['chats'].get('pomodoro_start', ["开始!"])))
            self._play_motion_for_state('work')
        elif phase == 'break':
            self.say(random.choice(self.pet_def['chats'].get('pomodoro_break', ["休息~"])))
            self._play_motion_for_state('happy')

    def on_sit_reminder(self):
        text = random.choice(self.pet_def['chats'].get('sit', ["起来动动吧~"]))
        self.notice(text, 5000)
        if self._pet_has_cheer():
            self._play_named_motion('Cheer', 0)
        else:
            self._play_motion_for_state('happy')

    def open_chat(self):
        self.chat_input.open_above(self.frameGeometry())

    def on_llm_reply(self, text):
        # Defensive: ensure pet window stays visible on async replies.
        log.info('on_llm_reply len=%d visible=%s', len(text or ''), self.isVisible())
        if not self.isVisible():
            self.show()
        self.raise_()
        try:
            dur = max(2000, min(8000, len(text) * 120)) if text else 2500
            self.say(text or "...", duration_ms=dur)
            self._play_motion_for_state('happy')
        except Exception:
            log.exception('on_llm_reply handler failed')

    def on_llm_fail(self, msg):
        log.warning('on_llm_fail: %s  visible=%s', msg, self.isVisible())
        if not self.isVisible():
            self.show()
        self.raise_()
        try:
            self.notice(f"{t('chat.llm_fail_prefix')} {msg}", 4000)
        except Exception:
            log.exception('on_llm_fail notice handler failed')

    def _pet_has_cheer(self):
        """Dororong defines a Cheer motion group; Haru doesn't. Keep this
        simple instead of querying the loaded model.
        """
        return bool(self.pet_def.get('named_expressions'))


    # ---------- motion/expression helpers ----------
    def _play_motion_for_state(self, key):
        if not self.model:
            return
        try:
            group, idx = self._motion_for(key)
            log.debug('motion: state=%s → group=%s idx=%s', key, group, idx)
            if idx is None:
                self.model.StartRandomMotion(group, MotionPriority.FORCE)
                # Random picks within a group; still flag as loopable if group is.
                self._loop_motion = (group, 0) if group in LOOPING_GROUPS else None
            else:
                self.model.StartMotion(group, idx, MotionPriority.FORCE)
                self._loop_motion = (group, idx) if group in LOOPING_GROUPS else None
        except Exception:
            log.exception('motion(%s) failed', key)

    def _play_named_motion(self, group, idx=0):
        if not self.model:
            return
        try:
            log.debug('motion: named group=%s idx=%s', group, idx)
            self.model.StartMotion(group, idx, MotionPriority.FORCE)
            self._loop_motion = (group, idx) if group in LOOPING_GROUPS else None
        except Exception:
            log.exception('named_motion(%s,%s) failed', group, idx)

    def _begin_exclusive_motion(self):
        """Prepare for a user-triggered motion: stop wander, clear any
        applied expression, and cancel pending expression auto-reset so
        exactly one visual state is active afterwards.
        """
        self._stop_wander()
        self._reset_expression()
        t = getattr(self, '_expr_reset_timer', None)
        if t is not None:
            t.stop()

    def _anim_tick(self):
        """Paint tick + universal motion-loop enforcement.

        Two rules when the current motion ends:
          1. If a looping motion is active (Run during wander, Dance, Idle),
             restart it so it actually loops (live2d-py ignores Loop flag).
          2. Otherwise if the pet is idle, fall back to Idle group so doro
             keeps breathing instead of freezing after a one-shot like Nod.
        """
        self.update()
        if not self.model:
            return
        try:
            if not self.model.IsMotionFinished():
                return
        except Exception:
            return
        try:
            if self._loop_motion:
                group, idx = self._loop_motion
                self.model.StartMotion(group, idx, MotionPriority.FORCE)
            elif self.state == 'idle':
                self.model.StartRandomMotion('Idle', MotionPriority.FORCE)
                self._loop_motion = ('Idle', 0)
        except Exception:
            pass

    def _motion_for(self, key):
        pd = self.pet_def
        if key == 'tap_head':
            return pd.get('hit_head_motion', (pd.get('idle_group', 'Idle'), 0))
        if key == 'tap_body':
            return pd.get('hit_body_motion', (pd.get('idle_group', 'Idle'), 0))
        if key == 'happy':
            tap = pd.get('tap_motions')
            if tap:
                group, count = tap
                return (group, random.randint(0, max(0, count - 1)))
        return (pd.get('idle_group', 'Idle'), None)

    def _play_expression(self, key):
        if not self.model:
            return
        name = self.pet_def.get('expressions', {}).get(key)
        if not name:
            return
        self._apply_expression_name(name)

    def _apply_expression_name(self, name, auto_reset_ms=0):
        """Apply a named expression overlay. If auto_reset_ms > 0, schedule a
        timer to clear it — useful for reaction overlays (star eyes, cookie)
        that shouldn't stick forever.
        """
        if not self.model or not name:
            return
        try:
            log.debug('expression: apply=%s auto_reset=%dms', name, auto_reset_ms)
            self.model.SetExpression(name)
        except Exception:
            log.exception('expression(%s) failed', name)
            return
        if auto_reset_ms > 0:
            if getattr(self, '_expr_reset_timer', None) is None:
                self._expr_reset_timer = QTimer(self)
                self._expr_reset_timer.setSingleShot(True)
                self._expr_reset_timer.timeout.connect(self._reset_expression)
            self._expr_reset_timer.start(int(auto_reset_ms))

    def _reset_expression(self):
        if not self.model:
            return
        try:
            self.model.ResetExpression()
        except Exception:
            try:
                self.model.SetExpression("")
            except Exception:
                pass

    # ---------- timers ----------
    def _random_behavior(self):
        if self.state != 'idle' or not self.model:
            return
        r = random.random()
        if self.cfg.get('wander_enable') and r < float(self.cfg.get('wander_chance')):
            self._start_wander()
            return
        r2 = random.random()
        if r2 < 0.45:
            self.say(random.choice(self.pet_def['chats']['idle']))
        elif r2 < 0.75 and self.cfg.get('follow_mouse'):
            cursor = QCursor.pos()
            x = cursor.x() - self.x()
            y = cursor.y() - self.y()
            try:
                self.model.Drag(x, y)
            except Exception:
                pass
        else:
            self._play_motion_for_state('idle_random')

    def _start_wander(self):
        if self._wander_timer.isActive():
            return
        log.info('wander: start')
        geo = QApplication.primaryScreen().availableGeometry()
        min_d = int(self.cfg.get('wander_min_dist'))
        left = geo.left() + 4
        right = geo.right() - self._w - 4
        top = geo.top() + 4
        bottom = geo.bottom() - self._h - 4
        cx, cy = self.x(), self.y()
        # Pick a random point anywhere in the usable screen area,
        # but at least min_d pixels away so the trip is worth it.
        for _ in range(8):
            tx = random.randint(left, max(left, right))
            ty = random.randint(top, max(top, bottom))
            if ((tx - cx) ** 2 + (ty - cy) ** 2) ** 0.5 >= min_d:
                break
        else:
            tx = left if cx > (left + right) // 2 else right
            ty = top if cy > (top + bottom) // 2 else bottom
        self._wander_target_x = tx
        self._wander_target_y = ty
        self.state = 'walk'
        self._play_named_motion('Run', 0)
        self._wander_timer.start()

    def _wander_step(self):
        if self._wander_target_x is None or not self.model:
            self._stop_wander()
            return
        # (Loop enforcement is now centralized in _anim_tick; Run was set as
        # the _loop_motion when _start_wander called _play_named_motion.)
        speed = max(1, int(self.cfg.get('wander_speed_px')))
        dx = self._wander_target_x - self.x()
        dy = self._wander_target_y - self.y()
        dist = (dx * dx + dy * dy) ** 0.5
        if dist <= speed:
            self.move(self._wander_target_x, self._wander_target_y)
            self._stop_wander()
            return
        step_x = int(round(speed * dx / dist))
        step_y = int(round(speed * dy / dist))
        self.move(self.x() + step_x, self.y() + step_y)
        try:
            # Head looks toward direction of motion: normalize to (0..1) range.
            look_x = self._w * (0.5 + 0.4 * (dx / dist))
            look_y = self._h * (0.5 + 0.4 * (dy / dist))
            self.model.Drag(int(look_x), int(look_y))
        except Exception:
            pass

    def _stop_wander(self):
        was_walking = self._wander_timer.isActive() or self.state == 'walk'
        if was_walking:
            log.info('wander: stop')
        self._wander_timer.stop()
        self._wander_target_x = None
        self._wander_target_y = None
        if self.state == 'walk':
            self.state = 'idle'
        self._schedule_save_pos()
        try:
            if self.model:
                self.model.Drag(self._w / 2, self._h / 2)
        except Exception:
            pass
        if was_walking:
            self._play_motion_for_state('idle_random')

    # ---------- events ----------
    def wheelEvent(self, event):
        mods = event.modifiers()
        steps = event.angleDelta().y() / 120.0
        delta = 0.05 * steps
        if mods & Qt.ShiftModifier:
            delta *= 0.4
        self.scale_by(delta)
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            self._press_global = event.globalPos()
            self._drag_moved = False
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset and (event.buttons() & Qt.LeftButton):
            delta = (event.globalPos() - self._press_global).manhattanLength()
            if delta > 5:
                if not self._drag_moved:
                    self._drag_moved = True
                    log.debug('drag: started')
                    self._stop_wander()
                    self.say(random.choice(self.pet_def['chats']['drag']), 1500)
                    # One-shot "grabbed" reaction; triggers exactly once per drag
                    # because _drag_moved gates it, and Struggle is loop=False
                    # now so it won't repeat on its own.
                    self._play_named_motion('Struggle', 0)
                self.move(event.globalPos() - self._drag_offset)
        elif self.cfg.get('follow_mouse') and self.model:
            x = event.pos().x()
            y = event.pos().y()
            try:
                self.model.Drag(x, y)
            except Exception:
                pass

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._press_global is not None:
            if self._drag_moved:
                self._apply_edge_snap()
                self._schedule_save_pos()
            else:
                self._click_pending_timer = QTimer(self)
                self._click_pending_timer.setSingleShot(True)
                self._click_pending_timer.timeout.connect(
                    lambda: self._on_single_click(event.pos())
                )
                self._click_pending_timer.start(QApplication.doubleClickInterval())
        self._drag_offset = None
        self._press_global = None
        self._drag_moved = False

    def _apply_edge_snap(self):
        if not self.cfg.get('edge_snap'):
            return
        geo = QApplication.primaryScreen().availableGeometry()
        dist = self.cfg.get('edge_snap_dist')
        x, y = self.x(), self.y()
        if abs(x - geo.left()) < dist:
            x = geo.left()
        elif abs(x + self._w - geo.right()) < dist:
            x = geo.right() - self._w
        if abs(y - geo.top()) < dist:
            y = geo.top()
        elif abs(y + self._h - geo.bottom()) < dist:
            y = geo.bottom() - self._h
        self.move(x, y)

    def _on_single_click(self, pos):
        self.cfg.bump_stat('interactions')
        area = None
        if self.model:
            try:
                area = self.model.HitTest(pos.x(), pos.y())
            except Exception:
                area = None
        if area == 'Head':
            self._play_motion_for_state('tap_head')
            self.say(random.choice(self.pet_def['chats']['happy']))
        elif area == 'Body':
            self._play_motion_for_state('tap_body')
            self.say(random.choice(self.pet_def['chats']['happy']))
        else:
            self._play_motion_for_state('happy')
            self.say(random.choice(self.pet_def['chats']['happy']))
        self.toggle_panel()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._click_pending_timer and self._click_pending_timer.isActive():
                self._click_pending_timer.stop()
            self.cfg.bump_stat('interactions')
            self._play_expression('happy')
            self._play_motion_for_state('happy')
            self.say(random.choice(self.pet_def['chats']['love']))

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#1e293b;color:#e2e8f0;border:1px solid #334155; padding:4px;}"
            "QMenu::item{padding:6px 22px;}"
            "QMenu::item:selected{background:#334155;}"
            "QMenu::item:disabled{color:#64748b;}"
            "QMenu::separator{height:1px;background:#334155;margin:4px 0;}"
        )

        act_chat = menu.addAction(t('menu.chat'))
        act_panel = menu.addAction(t('menu.panel'))
        privacy_on = bool(self.cfg.get('privacy_mode'))
        act_privacy = menu.addAction(
            t('menu.privacy_off') if privacy_on else t('menu.privacy_on')
        )
        menu.addSeparator()

        expr_menu = menu.addMenu(t('menu.expressions'))
        expr_actions = {}
        named = self.pet_def.get('named_expressions') or []
        if named:
            for key, label, exp_name in named:
                a = expr_menu.addAction(label)
                expr_actions[a] = ('named', key, exp_name)
        else:
            exprs = self.pet_def.get('expressions', {}) or {}
            label_map = {
                'happy': '开心', 'smile': '微笑', 'wink': '眨眼', 'blush': '害羞',
                'sad': '伤心', 'cry': '哭哭', 'alert': '警觉', 'angry': '生气',
                'tongue': '吐舌',
            }
            for key, _name in exprs.items():
                a = expr_menu.addAction(label_map.get(key, key))
                expr_actions[a] = ('key', key, None)
            if not exprs:
                na = expr_menu.addAction(t('menu.no_expression'))
                na.setEnabled(False)

        motion_menu = menu.addMenu(t('menu.motions'))
        motion_actions = {}
        for key, label, group, idx in self.pet_def.get('named_motions', []):
            a = motion_menu.addAction(label)
            motion_actions[a] = (group, idx)
        if motion_actions:
            motion_menu.addSeparator()
        act_motion_random = motion_menu.addAction(t('menu.motion_random'))
        act_motion_idle = motion_menu.addAction(t('menu.motion_idle'))
        motion_menu.addSeparator()
        act_wander = motion_menu.addAction(t('menu.wander'))
        act_stop_wander = motion_menu.addAction(t('menu.stop_wander'))
        act_stop_wander.setEnabled(self._wander_timer.isActive())

        menu.addSeparator()

        size_menu = menu.addMenu(t('menu.sizes'))
        current_scale = float(self.cfg.get('pet_scale_factor'))
        size_actions = {}
        for label_key, val in [('menu.size_xs', 0.5), ('menu.size_s', 0.75),
                               ('menu.size_m', 1.0), ('menu.size_l', 1.25),
                               ('menu.size_xl', 1.5)]:
            mark = "✓ " if abs(current_scale - val) < 0.03 else "   "
            a = size_menu.addAction(f"{mark}{t(label_key)}")
            size_actions[a] = val
        size_menu.addSeparator()
        act_shrink = size_menu.addAction(t('menu.size_shrink'))
        act_grow = size_menu.addAction(t('menu.size_grow'))

        kind_menu = menu.addMenu(t('menu.switch_pet'))
        current = self.cfg.get('pet_kind')
        kind_actions = {}
        for kind, name, exists in pets.available_kinds():
            mark = "✓ " if kind == current else "   "
            suffix = "" if exists else "  (未安装)"
            a = kind_menu.addAction(f"{mark}{name}{suffix}")
            a.setEnabled(exists)
            kind_actions[a] = kind

        menu.addSeparator()
        act_settings = menu.addAction(t('menu.settings'))
        act_quit = menu.addAction(t('menu.quit'))

        chosen = menu.exec_(event.globalPos())
        if chosen == act_chat:
            self.open_chat()
        elif chosen == act_panel:
            self.toggle_panel()
        elif chosen == act_privacy:
            new_state = not bool(self.cfg.get('privacy_mode'))
            self.cfg.set('privacy_mode', new_state)
            self.notice(t('notice.privacy_on' if new_state else 'notice.privacy_off'), 2500)
        elif chosen in expr_actions:
            kind, key, exp_name = expr_actions[chosen]
            if kind == 'named':
                if key == '__reset__' or not exp_name:
                    self._reset_expression()
                else:
                    self._apply_expression_name(exp_name)
            else:
                self._play_expression(key)
            self.say(random.choice(self.pet_def['chats'].get('happy', ["~"])), 1500)
        elif chosen == act_motion_random:
            self._begin_exclusive_motion()
            self._play_motion_for_state('idle_random')
        elif chosen == act_motion_idle:
            self._begin_exclusive_motion()
            self._play_motion_for_state('idle_random')
        elif chosen in motion_actions:
            group, idx = motion_actions[chosen]
            # Stop wander + clear expression + cancel pending expr reset so
            # exactly one visual state is active per motion selection. (Run
            # from menu is a special case: still clear expression but don't
            # trigger wander.)
            self._begin_exclusive_motion()
            self._play_named_motion(group, idx)
        elif chosen == act_wander:
            self._start_wander()
            self.say(t('pet.wander_out'))
        elif chosen == act_stop_wander:
            self._stop_wander()
        elif chosen in size_actions:
            self.cfg.set('pet_scale_factor', size_actions[chosen])
            self.apply_scale()
            self.say(t('pet.size_set', pct=int(size_actions[chosen] * 100)), 1200)
        elif chosen == act_shrink:
            self.scale_by(-0.1)
        elif chosen == act_grow:
            self.scale_by(0.1)
        elif chosen == act_settings:
            self.settingsRequested.emit()
        elif chosen == act_quit:
            self.quitRequested.emit()
        elif chosen in kind_actions:
            self.switch_pet(kind_actions[chosen])

    def _ensure_panel(self):
        if self.panel is None:
            self.panel = InfoPanel(self.cfg)

    def toggle_panel(self):
        self._ensure_panel()
        if self.panel.isVisible():
            self.panel.hide()
        else:
            self.panel.show()
            self._align_panel()

    def _align_panel(self):
        if not self.panel:
            return
        screen = QApplication.primaryScreen().availableGeometry()
        pw, ph = self.panel.width(), self.panel.height()
        x = self.x() + self.width() // 2 - pw // 2
        y = self.y() - ph - 8
        if y < screen.top() + 4:
            y = self.y() + self.height() + 8
        x = max(screen.left() + 4, min(x, screen.right() - pw - 4))
        self.panel.move(x, y)

    def moveEvent(self, event):
        super().moveEvent(event)
        self._schedule_save_pos()
        if self.panel and self.panel.isVisible():
            self._align_panel()

    def closeEvent(self, event):
        self._persist_pos()
        self.speech_bubble.close()
        self.chat_input.close()
        super().closeEvent(event)
