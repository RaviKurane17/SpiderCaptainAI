"""
Captain AI — Structured Logging
================================
Replaces raw print() calls with proper logging that writes to both
console and a rotating log file.

Production: INFO / WARNING / ERROR only.
Developer Mode: DEBUG / TRACE enabled via CAPTAIN_DEV_MODE=1 env var.
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


def _is_dev_mode() -> bool:
    """Check if developer mode is enabled."""
    return os.environ.get("CAPTAIN_DEV_MODE", "0").strip() in ("1", "true", "yes")


def setup_logger(name: str = "captain", level: int = None) -> logging.Logger:
    """Create and return a configured logger with console + file handlers."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:                    # already set up
        return logger

    # Determine log level based on mode
    if level is None:
        level = logging.DEBUG if _is_dev_mode() else logging.INFO

    logger.setLevel(level)

    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler — INFO in production, DEBUG in dev
    if sys.stdout and getattr(sys.stdout, 'name', '') != os.devnull:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG if _is_dev_mode() else logging.INFO)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    # File handler — DEBUG in dev, INFO in production. 5 MB rotate, 3 backups
    fh = RotatingFileHandler(
        str(LOGS_DIR / "captain.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG if _is_dev_mode() else logging.INFO)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# Module-level logger — import this in other files
log = setup_logger()
