"""Centralized logging.

All modules should `from logger import log` and call `log.info(...)` etc.
Output goes to both stderr and a rotating file so you can tail it during
testing or paste it when reporting bugs.

Log location:
  - Running from source  : <project>/doro.log
  - Running as frozen exe: <user>/AppData/Roaming/DesktopPetMonitor/doro.log
    (next to config.json — otherwise PyInstaller's temp dir eats the log
    when the app exits)

File: doro.log (5 MB rotation, keep 3 backups)
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _resolve_log_path():
    if getattr(sys, 'frozen', False):
        base = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / 'DesktopPetMonitor'
        base.mkdir(parents=True, exist_ok=True)
        return base / 'doro.log'
    return Path(__file__).resolve().parent / 'doro.log'


_LOG_PATH = _resolve_log_path()

_FMT = '%(asctime)s.%(msecs)03d %(levelname)-5s [%(name)s] %(message)s'
_DATEFMT = '%H:%M:%S'


def _build_logger():
    logger = logging.getLogger('doro')
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(_FMT, datefmt=_DATEFMT)

    fh = RotatingFileHandler(
        _LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8'
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.propagate = False
    return logger


log = _build_logger()


def log_path():
    return str(_LOG_PATH)
