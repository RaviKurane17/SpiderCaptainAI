"""
FileIndexer — Crawls drives/directories and yields every file and folder path.

Design decisions:
- Uses os.scandir() instead of Path.rglob() for 3-5x faster crawling.
- Skips system/protected folders by default to avoid Permission errors and
  massive scan times (e.g. Windows, $Recycle.Bin, Program Files internals).
- Cancellable via a threading.Event so the UI can abort long scans.
- Reports progress via an optional callback so the engine can relay
  "Searching C drive..." messages to the user.
"""

import os
import string
import logging
import threading
from pathlib import Path
from typing import Callable, Optional, Generator

log = logging.getLogger("FileIndexer")

# ── Folders we skip by default (case-insensitive) ──────────────────────────
_SKIP_FOLDERS: set[str] = {
    "$recycle.bin", "$windows.~bt", "$windows.~ws",
    "system volume information", "recovery",
    "windows", "windows.old",
    "programdata",
    "appdata",                         # user-level noise
    ".git", ".svn", ".hg",            # VCS internals
    "node_modules", "__pycache__",    # dev noise
    ".vs", ".idea", ".vscode",        # IDE caches
    "config.msi", "msocache",
}

# Top-level Program Files are kept (user may search for installed apps)
# but we skip deep internals of them — controlled by max depth per root.

_SKIP_PREFIXES = (".", "$")


class FileIndexer:
    """
    Crawls one or more directories and yields (path_str, is_dir, name_lower)
    tuples for every discovered item.

    Usage:
        indexer = FileIndexer(cancel_event=evt, on_progress=callback)
        for path_str, is_dir, name_lower in indexer.crawl(roots=["C:\\"]):
            ...
    """

    def __init__(
        self,
        cancel_event: Optional[threading.Event] = None,
        on_progress: Optional[Callable[[str], None]] = None,
        max_depth: int = 12,
        skip_system: bool = True,
    ):
        self._cancel = cancel_event or threading.Event()
        self._on_progress = on_progress or (lambda msg: None)
        self._max_depth = max_depth
        self._skip_system = skip_system

    # ── Public API ─────────────────────────────────────────────────────────

    def crawl(
        self,
        roots: Optional[list[str]] = None,
    ) -> Generator[tuple[str, bool, str], None, None]:
        """
        Yield (full_path, is_directory, lowercase_name) for every item found.
        If roots is None, auto-detect all available Windows drive letters.
        """
        if roots is None:
            roots = self._detect_drives()

        for root in roots:
            if self._cancel.is_set():
                return
            root_path = Path(root)
            if not root_path.exists():
                continue
            self._on_progress(f"Scanning {root_path}...")
            yield from self._walk(str(root_path), depth=0)

    def cancel(self):
        """Signal the crawler to stop as soon as possible."""
        self._cancel.set()

    # ── Internal ───────────────────────────────────────────────────────────

    def _walk(
        self, directory: str, depth: int
    ) -> Generator[tuple[str, bool, str], None, None]:
        """Recursive os.scandir walk with depth limiting and cancellation."""
        if self._cancel.is_set() or depth > self._max_depth:
            return

        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if self._cancel.is_set():
                        return

                    name = entry.name
                    name_lower = name.lower()

                    # Skip hidden / system prefixes
                    if self._skip_system and name_lower[:1] in _SKIP_PREFIXES:
                        continue

                    try:
                        is_dir = entry.is_dir(follow_symlinks=False)
                    except (OSError, PermissionError):
                        continue

                    if is_dir:
                        # Skip known system folders
                        if self._skip_system and name_lower in _SKIP_FOLDERS:
                            continue

                        # Yield the directory itself (users want to find folders!)
                        yield (entry.path, True, name_lower)

                        # Report progress for top-level directories
                        if depth <= 1:
                            self._on_progress(f"Scanning {entry.path}...")

                        # Recurse
                        yield from self._walk(entry.path, depth + 1)
                    else:
                        # Yield the file
                        yield (entry.path, False, name_lower)

        except PermissionError:
            pass  # Silently skip permission-denied directories
        except OSError as e:
            log.debug(f"OS error scanning {directory}: {e}")

    @staticmethod
    def _detect_drives() -> list[str]:
        """Return all available Windows drive letters (e.g. ['C:\\', 'D:\\'])."""
        drives = []
        if os.name == "nt":
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.isdir(drive):
                    drives.append(drive)
        else:
            # On Linux/Mac, just use home
            drives.append(str(Path.home()))
        return drives
