"""Headless-ish diagnostic: load Doro, try to play every motion group,
report whether StartMotion raises, whether the model actually picks up
the motion, and sample a few parameters after playback starts."""
import sys, traceback, time
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QOpenGLWidget
from PyQt5.QtCore import QCoreApplication, Qt, QTimer
import live2d.v3 as live2d
from live2d.v3 import MotionPriority

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'assets' / 'dororong' / 'Doro' / 'Doro.model3.json'

GROUPS = ['Wave', 'Nod', 'Shake', 'Dance', 'Sleep', 'Surprised', 'Shy',
          'Run', 'Standup', 'Angry', 'Cry', 'Struggle', 'Peek', 'Idle']

QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)
live2d.setLogEnable(True) if hasattr(live2d, 'setLogEnable') else None
live2d.init()

results = []

class Probe(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        self.step = 0
        self.cur = None
        self.resize(200, 260)

    def initializeGL(self):
        live2d.glInit()
        try:
            self.model = live2d.LAppModel()
            self.model.LoadModelJson(str(MODEL))
            self.model.Resize(self.width(), self.height())
            print(f'[LOAD] OK  {MODEL}', flush=True)
        except Exception as e:
            print(f'[LOAD] FAIL: {e}', flush=True)
            traceback.print_exc()
            QTimer.singleShot(100, app.quit)
            return
        QTimer.singleShot(200, self.try_next)

    def try_next(self):
        if self.step >= len(GROUPS):
            QTimer.singleShot(100, app.quit)
            return
        g = GROUPS[self.step]
        self.cur = g
        try:
            self.model.StartMotion(g, 0, MotionPriority.FORCE)
            print(f'[CALL] StartMotion("{g}", 0)  no-exception', flush=True)
        except Exception as e:
            print(f'[CALL] StartMotion("{g}", 0)  EXC: {type(e).__name__}: {e}', flush=True)
            results.append((g, False, str(e)))
            self.step += 1
            QTimer.singleShot(50, self.try_next)
            return
        QTimer.singleShot(80, self.check_state)

    def check_state(self):
        try:
            self.model.Update()
            try:
                finished = self.model.IsMotionFinished()
            except Exception:
                finished = None
            sample_vals = {}
            for pid in ('ParamAngleX', 'ParamAngleY', 'ParamAngleZ',
                        'ParamBodyAngleZ', 'ParamMouthOpenY', 'ParamEyeSmile'):
                try:
                    sample_vals[pid] = round(self.model.GetParameterValue(pid), 3)
                except Exception:
                    pass
            print(f'       -> IsMotionFinished={finished}  params={sample_vals}', flush=True)
            results.append((self.cur, True, sample_vals))
        except Exception as e:
            print(f'       -> post-check EXC: {e}', flush=True)
        self.step += 1
        QTimer.singleShot(50, self.try_next)

    def paintGL(self):
        live2d.clearBuffer()
        if self.model:
            try:
                self.model.Update()
                self.model.Draw()
            except Exception:
                pass

w = Probe()
w.show()
app.exec()

print('\n=== Summary ===')
for g, ok, info in results:
    print(f'  {g:12s} ok={ok}  {info}')
try: live2d.dispose()
except: pass
