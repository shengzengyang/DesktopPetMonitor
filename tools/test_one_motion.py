import sys, json
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QOpenGLWidget
from PyQt5.QtCore import QCoreApplication, Qt, QTimer
import live2d.v3 as live2d

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / 'assets' / 'dororong' / 'Doro'

motion_rel = sys.argv[1]

BASE_MODEL = {
    "Version": 3,
    "FileReferences": {
        "Moc": "Doro.moc3",
        "Textures": ["Doro.2048/texture_00.png"],
        "Physics": "Doro.physics3.json",
        "DisplayInfo": "Doro.cdi3.json",
        "Motions": {"Test": [{"File": motion_rel, "FadeInTime": 0.3, "FadeOutTime": 0.3}]}
    },
    "Groups": [
        {"Target": "Parameter", "Name": "EyeBlink", "Ids": []},
        {"Target": "Parameter", "Name": "LipSync", "Ids": []}
    ]
}

tmp = MODEL_DIR / '_test_model.model3.json'
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(BASE_MODEL, f)

QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)
live2d.init()

class Probe(QOpenGLWidget):
    def initializeGL(self):
        live2d.glInit()
        m = live2d.LAppModel()
        m.LoadModelJson(str(tmp))
        print('LOAD_OK', flush=True)
        QTimer.singleShot(80, app.quit)

w = Probe()
w.show()
app.exec()
try: live2d.dispose()
except: pass
tmp.unlink(missing_ok=True)
