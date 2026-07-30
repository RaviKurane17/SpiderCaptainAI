"""
config.py — Centralized configuration for the file search engine.

WHY: All tunable constants in one place. Every module imports from here
instead of hardcoding values. Makes the engine configurable without
touching business logic.
"""

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
# Cache DB lives alongside the memory DB
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = PROJECT_ROOT / "memory"
CACHE_DB_PATH = CACHE_DIR / "file_index.db"

# ── Indexer Settings ───────────────────────────────────────────────────────
MAX_CRAWL_DEPTH = 15          # Max recursion depth for directory crawling
CRAWL_BATCH_SIZE = 5000       # Items buffered before flushing to SQLite during live scan
INDEX_BATCH_SIZE = 10000      # Items buffered before flushing during background index

# Folders to skip during crawling (lowercase). System/noise folders that
# bloat the index without user value.
SKIP_FOLDERS: frozenset[str] = frozenset({
    "$recycle.bin", "$windows.~bt", "$windows.~ws",
    "system volume information", "recovery",
    "windows", "windows.old",
    "programdata",
    "appdata",
    "program files", "program files (x86)",
    ".git", ".svn", ".hg",
    "node_modules", "__pycache__", ".tox", ".nox",
    ".vs", ".idea", ".vscode",
    "config.msi", "msocache",
    "boot", "efi",
})

# Prefixes on filenames to skip (hidden/system items)
SKIP_PREFIXES: tuple[str, ...] = (".", "$")

# ── Search Settings ────────────────────────────────────────────────────────
SEARCH_TIMEOUT_SEC = 5.0      # Max seconds for a live scan before returning partial results
DEFAULT_MAX_RESULTS = 30      # Default number of results returned
FUZZY_THRESHOLD = 0.50        # Minimum fuzzy score to include a result (0–1)
HIGH_CONFIDENCE = 0.95        # Auto-open threshold — single result above this score

# ── Cache / SQLite Settings ────────────────────────────────────────────────
STALE_HOURS = 24              # Hours before cache is considered stale
SQLITE_TIMEOUT = 15           # Seconds to wait for SQLite lock
SQLITE_CACHE_SIZE = -8000     # Negative = KiB. 8 MB page cache
SQLITE_MMAP_SIZE = 64 * 1024 * 1024  # 64 MB memory-mapped I/O

# ── Ranking Weights ────────────────────────────────────────────────────────
# Higher = better. Used by _rank_results in engine.py.
RANK_EXACT = 1.00
RANK_EXACT_NO_EXT = 0.98
RANK_STARTS_WITH = 0.90
RANK_WHOLE_WORD = 0.85
RANK_CONTAINS = 0.75
RANK_FUZZY_BONUS = 0.0        # Added to raw fuzzy score (0–1)

# User folders are boosted by this amount to rank above system paths
USER_FOLDER_BOOST = 0.05

# Paths considered "user folders" — results here are ranked higher
USER_FOLDERS: tuple[str, ...] = (
    str(Path.home() / "Desktop"),
    str(Path.home() / "Documents"),
    str(Path.home() / "Downloads"),
    str(Path.home() / "Pictures"),
    str(Path.home() / "Music"),
    str(Path.home() / "Videos"),
    str(Path.home()),
)

# ── Explorer Settings ─────────────────────────────────────────────────────
EXPLORER_SUBPROCESS_TIMEOUT = 10  # Seconds before subprocess.Popen times out (network paths)

# ── Long Path Prefix (Windows) ────────────────────────────────────────────
# Windows paths > 260 chars need this prefix for API calls
WIN_LONG_PATH_PREFIX = "\\\\?\\"
