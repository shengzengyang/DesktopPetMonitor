"""Screenshot every drivable parameter at multiple values to build a visual
reference of what each Live2D parameter does.

Output: <project>/build/param_screenshots/<param>__<value>.png
(Override via DORO_PARAM_OUT env var if you want it elsewhere.)
"""
import os
import sys
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QOpenGLWidget
from PyQt5.QtCore import QCoreApplication, Qt, QTimer
import live2d.v3 as live2d
from live2d.v3 import MotionPriority

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'assets' / 'dororong' / 'Doro' / 'Doro.model3.json'
OUT = Path(os.environ.get('DORO_PARAM_OUT') or (ROOT / 'build' / 'param_screenshots'))
OUT.mkdir(parents=True, exist_ok=True)

W, H = 480, 640

# (param_id, [test_values, ...])
# Skipped: physics params (PhyAngleX/Y, PhyHair*, PhyIris*, PhyBounce — not
# user-drivable, they're driven by physics sim from other params) and the
# marker/watermark param Live2Dby0x4682B4 (not a real visual knob).
TESTS = [
    # --- Expression overlay flags ---
    ('ParamExpEyeHighlights', [-1.0, 0.0, 1.0]),
    ('ParamExpEyeStar',       [0.0, 1.0]),
    ('ParamExp1',             [0.0, 1.0]),
    ('ParamExp2',             [0.0, 1.0]),
    ('ParamExp3',             [0.0, 1.0]),
    ('ParamExp4',             [0.0, 1.0]),
    ('ParamExp5',             [0.0, 1.0]),
    ('ParamExp6',             [0.0, 1.0]),
    ('ParamExp7',             [0.0, 1.0]),
    ('AnimLine',              [0.0, 1.0]),
    ('AnimLoading1',          [-1.0, 0.0, 1.0]),
    ('AnimLoading2',          [0.0, 1.0]),
    # --- Head angles ---
    ('ParamAngleX',           [-30.0, -15.0, 15.0, 30.0]),
    ('ParamAngleY',           [-30.0, -15.0, 15.0, 30.0]),
    ('ParamAngleZ',           [-30.0, -15.0, 15.0, 30.0]),
    # --- Body angles ---
    ('ParamBodyAngleY',       [-10.0, 10.0]),
    ('ParamBodyAngleZ',       [-10.0, 10.0]),
    # --- Step / bounce system ---
    ('ParamStep',             [-10.0, 0.0, 10.0]),
    ('ParamBreath',           [0.0, 1.0]),
    ('ParamBounceInput1',     [-1.0, 0.0, 1.0]),
    ('ParamBounceInput2',     [-1.0, 0.0, 1.0]),
    ('ParamBounceInput3',     [-1.0, 0.0, 1.0]),
    ('ParamBounceInput4',     [-1.0, 0.0, 1.0]),
    # --- Eyes ---
    ('ParamEyeLOpen',         [0.0, 0.5, 1.0, 1.5]),
    ('ParamEyeROpen',         [0.0, 0.5, 1.0, 1.5]),
    ('ParamEyeSmile',         [0.0, 0.5, 1.0]),
    ('ParamEyeAngle',         [-1.0, 1.0]),
    # --- Brows ---
    ('ParamBrowLY',           [-1.0, 1.0]),
    ('ParamBrowRY',           [-1.0, 1.0]),
    # --- Mouth ---
    ('ParamMouthForm',        [-1.0, -0.5, 0.5, 1.0]),
    ('ParamMouthOpenY',       [0.0, 0.5, 1.0]),
    ('ParamTongueOut',        [0.0, 1.0]),
    ('ParamMouthX',           [-1.0, 1.0]),
    ('ParamMouthY',           [-1.0, 1.0]),
]


def flatten():
    jobs = [('00_baseline', None, None)]
    idx = 1
    for pid, values in TESTS:
        for v in values:
            tag = f'{idx:03d}_{pid}_{_fmt(v)}'
            jobs.append((tag, pid, v))
            idx += 1
    return jobs


def _fmt(v):
    s = f'{v:+.2f}'.replace('+', 'p').replace('-', 'n').replace('.', '_')
    return s


QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)
live2d.init()


class Capture(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        self.jobs = flatten()
        self.idx = -1
        self.resize(W, H)

    def initializeGL(self):
        live2d.glInit()
        self.model = live2d.LAppModel()
        self.model.LoadModelJson(str(MODEL))
        self.model.Resize(W, H)
        # Kill any auto-playing motion so params aren't overwritten each frame.
        try: self.model.StopAllMotions()
        except Exception: pass
        QTimer.singleShot(300, self.next_job)

    def paintGL(self):
        live2d.clearBuffer()
        if self.model:
            # Do NOT call Update(); Update() re-applies motion curves which
            # would overwrite our explicit SetParameterValue each frame.
            # Directly calling Draw uses whatever params were last set.
            self.model.Draw()

    def next_job(self):
        self.idx += 1
        if self.idx >= len(self.jobs):
            QTimer.singleShot(150, app.quit)
            return
        tag, pid, v = self.jobs[self.idx]
        # Reset every param to 0 as a clean baseline between shots.
        self._reset_all()
        if pid is not None:
            try:
                self.model.SetParameterValue(pid, float(v))
            except Exception as e:
                print(f'  SetParameterValue({pid}={v}) EXC: {e}', flush=True)
        # Let a few paint cycles run then grab.
        QTimer.singleShot(120, self.grab_now)

    def _reset_all(self):
        for pid, _vals in TESTS:
            try:
                self.model.SetParameterValue(pid, 0.0)
            except Exception:
                pass
        # A handful of params look broken at 0 (e.g. eyes closed), nudge:
        for pid, v in [('ParamEyeLOpen', 1.0), ('ParamEyeROpen', 1.0)]:
            try:
                self.model.SetParameterValue(pid, v)
            except Exception:
                pass

    def grab_now(self):
        tag, _, _ = self.jobs[self.idx]
        path = OUT / f'{tag}.png'
        img = self.grabFramebuffer()
        img.save(str(path))
        print(f'  -> {path.name}', flush=True)
        QTimer.singleShot(30, self.next_job)


w = Capture()
w.show()
app.exec()
try: live2d.dispose()
except: pass
print('Done.')
