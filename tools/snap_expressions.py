"""Load Doro and capture a PNG of every expression for visual inspection.

Output: <project>/build/expression_screenshots/<name>.png
(Override via DORO_EXPR_OUT env var.)
"""
import os
import sys
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QOpenGLWidget
from PyQt5.QtCore import QCoreApplication, Qt, QTimer
import live2d.v3 as live2d

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'assets' / 'dororong' / 'Doro' / 'Doro.model3.json'
OUT = Path(os.environ.get('DORO_EXPR_OUT') or (ROOT / 'build' / 'expression_screenshots'))
OUT.mkdir(parents=True, exist_ok=True)

W, H = 480, 640

# Matches the names in Doro.model3.json (expression IDs we load by SetExpression).
TARGETS = [
    ('00_baseline',      None),
    ('01_Exp1',          'Exp1'),
    ('02_Exp2',          'Exp2'),
    ('03_Exp3',          'Exp3'),
    ('04_Exp4',          'Exp4'),
    ('05_Exp5',          'Exp5'),
    ('06_Exp6',          'Exp6'),
    ('07_Exp7',          'Exp7'),
    ('08_Exp8',          'Exp8'),
    ('09_TongueOut',     'TongueOut'),
    ('10_HighlightOff',  'HighlightOff'),
    ('11_RunningOff',    'RunningOff'),
]

QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)
live2d.init()


class Capture(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        self.idx = -1
        self.resize(W, H)

    def initializeGL(self):
        live2d.glInit()
        self.model = live2d.LAppModel()
        self.model.LoadModelJson(str(MODEL))
        self.model.Resize(W, H)
        QTimer.singleShot(400, self.next_target)

    def paintGL(self):
        live2d.clearBuffer()
        if self.model:
            self.model.Update()
            self.model.Draw()

    def next_target(self):
        self.idx += 1
        if self.idx >= len(TARGETS):
            QTimer.singleShot(150, app.quit)
            return
        name, exp = TARGETS[self.idx]
        try:
            self.model.ResetExpression()
        except Exception:
            try: self.model.SetExpression('')
            except Exception: pass
        if exp:
            try:
                self.model.SetExpression(exp)
            except Exception as e:
                print(f'  SetExpression({exp}) EXC: {e}', flush=True)
        # Drive a few frames so SetExpression fade-in completes + physics settles.
        self._tick = 0
        self._settle = QTimer(self)
        self._settle.timeout.connect(self.tick_settle)
        self._settle.start(30)

    def tick_settle(self):
        self.update()
        self._tick += 1
        if self._tick >= 25:  # ~750ms of frames
            self._settle.stop()
            QTimer.singleShot(40, self.grab_now)

    def grab_now(self):
        name, _ = TARGETS[self.idx]
        path = OUT / f'{name}.png'
        img = self.grabFramebuffer()
        img.save(str(path))
        print(f'  -> {path}', flush=True)
        QTimer.singleShot(50, self.next_target)


w = Capture()
w.show()
app.exec()
try: live2d.dispose()
except: pass
print('Done.')
