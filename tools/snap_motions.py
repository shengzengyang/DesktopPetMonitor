"""Snapshot each motion at a few time offsets to inspect visually.

Output: <project>/build/motion_frames/<group>_t<ms>.png
(Override via DORO_MOTION_FRAMES_OUT env var.)
"""
import os, sys, time
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QOpenGLWidget
from PyQt5.QtCore import QCoreApplication, Qt, QTimer
import live2d.v3 as live2d
from live2d.v3 import MotionPriority

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'assets' / 'dororong' / 'Doro' / 'Doro.model3.json'
OUT = Path(os.environ.get('DORO_MOTION_FRAMES_OUT') or (ROOT / 'build' / 'motion_frames'))
OUT.mkdir(parents=True, exist_ok=True)

W, H = 480, 640

# (group, idx, display_duration_ms, sample_times_ms)
# sample_times are ms offsets from motion start to screenshot at.
JOBS = [
    ('Idle',      0, 6000, [500, 1500, 3000, 4500]),   # idle_breath
    ('Nod',       0, 1400, [200, 500, 900, 1200]),
    ('Shake',     0, 1600, [200, 500, 900, 1300]),
    ('Dance',     0, 3000, [400, 1000, 1800, 2500]),
    ('Surprised', 0, 1400, [150, 400, 800, 1200]),
    ('Run',       0, 1000, [100, 300, 500, 800]),      # run_plus
    ('Standup',   0, 2600, [400, 900, 1600, 2300]),
    ('Struggle',  0, 1300, [150, 400, 800, 1100]),
    ('Cheer',     0, 1600, [200, 500, 1000, 1400]),
]

QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)
live2d.init()


class Capture(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        self.job_idx = -1
        self.sample_idx = 0
        self.motion_start = 0
        self.resize(W, H)

    def initializeGL(self):
        live2d.glInit()
        self.model = live2d.LAppModel()
        self.model.LoadModelJson(str(MODEL))
        self.model.Resize(W, H)
        QTimer.singleShot(300, self.next_job)

    def paintGL(self):
        live2d.clearBuffer()
        if self.model:
            self.model.Update()
            self.model.Draw()

    def next_job(self):
        self.job_idx += 1
        self.sample_idx = 0
        if self.job_idx >= len(JOBS):
            QTimer.singleShot(150, app.quit)
            return
        group, idx, dur, samples = JOBS[self.job_idx]
        try:
            self.model.StartMotion(group, idx, MotionPriority.FORCE)
            self.motion_start = time.monotonic() * 1000
        except Exception as e:
            print(f'  StartMotion({group}) EXC: {e}', flush=True)
            QTimer.singleShot(30, self.next_job)
            return
        # Schedule first sample
        self._schedule_next_sample()

    def _schedule_next_sample(self):
        group, idx, dur, samples = JOBS[self.job_idx]
        if self.sample_idx >= len(samples):
            # move to next motion
            QTimer.singleShot(120, self.next_job)
            return
        target_ms = samples[self.sample_idx]
        elapsed = time.monotonic() * 1000 - self.motion_start
        wait = max(20, int(target_ms - elapsed))
        QTimer.singleShot(wait, self.grab_sample)

    def grab_sample(self):
        self.update()  # ensure a fresh paint before grab
        QTimer.singleShot(30, self._do_grab)

    def _do_grab(self):
        group, idx, dur, samples = JOBS[self.job_idx]
        t_ms = samples[self.sample_idx]
        img = self.grabFramebuffer()
        path = OUT / f'{group}_t{t_ms:04d}.png'
        img.save(str(path))
        print(f'  -> {path.name}', flush=True)
        self.sample_idx += 1
        self._schedule_next_sample()


w = Capture()
w.show()
app.exec()
try: live2d.dispose()
except: pass
print('Done.')
