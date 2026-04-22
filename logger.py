"""Centralized logging.

All modules should `from logger import log` and call `log.info(...)` etc.
Output goes to both stderr and a rotating file at the project root so you
can tail it during testing or paste it when reporting bugs.

File: doro.log (5 MB rotation, keep 3 backups)
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
_LOG_PATH = _PROJECT_ROOT / 'doro.log'

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
