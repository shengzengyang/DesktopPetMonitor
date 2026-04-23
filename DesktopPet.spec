# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for DesktopPetMonitor.
#
# Goals:
#  - Bundle assets/ so Live2D models ship inside the exe.
#  - Bundle MSVC 2015-2022 runtime DLLs so end-users don't need to install
#    VC++ Redistributable separately. Native deps (live2d.pyd, PyQt5) all
#    need these; Microsoft's EULA permits redistribution.
#  - No user data is embedded — config.json + doro.log live in %APPDATA%.

import os

block_cipher = None

# --- MSVC runtime DLLs -------------------------------------------------------
# Placed at the bundle root so every .pyd/.dll loaded from _MEIPASS can
# resolve them via the default Windows DLL search order.
_SYSTEM32 = r'C:\Windows\System32'
_MSVC_DLLS = [
    'msvcp140.dll',
    'msvcp140_1.dll',
    'msvcp140_2.dll',       # newer std lib (fp formatting, etc.)
    'vcruntime140.dll',
    'vcruntime140_1.dll',   # x64 exception dispatch
    'concrt140.dll',        # Microsoft Concurrency Runtime (live2d threads)
    'vccorlib140.dll',      # C++ CoreLib
]
_msvc_binaries = []
for _dll in _MSVC_DLLS:
    _src = os.path.join(_SYSTEM32, _dll)
    if os.path.isfile(_src):
        _msvc_binaries.append((_src, '.'))


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=_msvc_binaries,
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=['pynvml'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DesktopPet',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
)
