"""Windows auto-start (HKCU Run registry).

Per-user, no admin required. Writes / deletes a single REG_SZ value at
HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\DesktopPetMonitor.

Handles both modes:
  - Frozen exe    → registers sys.executable directly
  - From source   → registers `"<python.exe>" "<project>/main.py"`

All three public functions are idempotent and swallow missing-value
errors, so they're safe to call on every settings apply.
"""
import os
import sys
from pathlib import Path

try:
    import winreg  # Windows only
except ImportError:
    winreg = None

from logger import log


_REG_PATH = r'Software\Microsoft\Windows\CurrentVersion\Run'
_APP_NAME = 'DesktopPetMonitor'


def _launch_command():
    """Return the command Windows should execute at login."""
    if getattr(sys, 'frozen', False):
        # Packaged exe — just the path, quoted to survive spaces.
        return f'"{os.path.abspath(sys.executable)}"'
    # Running from source — relaunch with the same interpreter + main.py.
    python = os.path.abspath(sys.executable)
    script = Path(__file__).resolve().parent / 'main.py'
    return f'"{python}" "{script}"'


def is_enabled():
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, _APP_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        return False
    except Exception as e:
        log.warning('autostart: is_enabled query failed: %s', e)
        return False


def enable():
    if winreg is None:
        log.warning('autostart.enable: winreg not available on this platform')
        return False
    cmd = _launch_command()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, cmd)
        log.info('autostart: enabled → %s', cmd)
        return True
    except Exception:
        log.exception('autostart.enable failed')
        return False


def disable():
    if winreg is None:
        return True
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, _APP_NAME)
        log.info('autostart: disabled')
        return True
    except FileNotFoundError:
        return True  # already gone — treat as success
    except OSError as e:
        # ERROR_FILE_NOT_FOUND (2) surfaces this way on some Windows builds
        if getattr(e, 'winerror', None) == 2:
            return True
        log.warning('autostart.disable OSError: %s', e)
        return False
    except Exception:
        log.exception('autostart.disable failed')
        return False


def sync(should_enable: bool):
    """Idempotent: apply the desired state without duplicating registry writes."""
    current = is_enabled()
    if bool(should_enable) == current:
        return True
    return enable() if should_enable else disable()
