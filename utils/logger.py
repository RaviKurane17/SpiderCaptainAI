"""
Captain AI — Structured Logging
================================
Replaces raw print() calls with proper logging that writes to both
console and a rotating log file.
"""

import logging
import sys
import os
from colorama import init, Fore, Style

# Force UTF-8 on Windows before initializing colorama/logging
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

init(autoreset=True)
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils.config import LOGS_DIR


def setup_logger(name: str = "captain", level: int = logging.DEBUG) -> logging.Logger:
    """Create and return a configured logger with console + file handlers."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:                    # already set up
        return logger

    logger.setLevel(level)

    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler — INFO and above
    if sys.stdout and getattr(sys.stdout, 'name', '') != os.devnull:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    # File handler — DEBUG and above, 5 MB rotate, 3 backups
    fh = RotatingFileHandler(
        str(LOGS_DIR / "captain.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# Module-level logger — import this in other files
log = setup_logger()
