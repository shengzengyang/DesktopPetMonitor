import sys, os, json, traceback
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QOpenGLWidget
from PyQt5.QtCore import QCoreApplication, Qt, QTimer
import live2d.v3 as live2d

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / 'assets' / 'dororong' / 'Doro'
MOTIONS_DIR = MODEL_DIR / 'Motions'

BASE_MODEL = {
    "Version": 3,
    "FileReferences": {
        "Moc": "Doro.moc3",
        "Textures": ["Doro.2048/texture_00.png"],
        "Physics": "Doro.physics3.json",
        "DisplayInfo": "Doro.cdi3.json",
        "Motions": {
            "Test": [{"File": "", "FadeInTime": 0.3, "FadeOutTime": 0.3}]
        }
    },
    "Groups": [
        {"Target": "Parameter", "Name": "EyeBlink", "Ids": []},
        {"Target": "Parameter", "Name": "LipSync", "Ids": []}
    ]
}


def try_motion(motion_relpath):
    test_model = json.loads(json.dumps(BASE_MODEL))
    test_model['FileReferences']['Motions']['Test'][0]['File'] = motion_relpath
    tmp = MODEL_DIR / '_test_model.model3.json'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(test_model, f)

    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication.instance() or QApplication(sys.argv)

    class Probe(QOpenGLWidget):
        ok = False
        def initializeGL(self):
            try:
                live2d.glInit()
                m = live2d.LAppModel()
                m.LoadModelJson(str(tmp))
                Probe.ok = True
            except Exception as e:
                print(f"  EXC: {e}")
            finally:
                QTimer.singleShot(100, app.quit)

    live2d.init()
    w = Probe()
    w.show()
    app.exec()
    try:
        live2d.dispose()
    except: pass
    tmp.unlink(missing_ok=True)
    return Probe.ok


for m in sorted(MOTIONS_DIR.glob('*.motion3.json')):
    rel = f'Motions/{m.name}'
    print(f'Testing {rel}...')
    try:
        ok = try_motion(rel)
        print(f'  {"OK" if ok else "FAIL"}')
    except Exception as e:
        print(f'  CRASH: {type(e).__name__}: {e}')
        traceback.print_exc()
