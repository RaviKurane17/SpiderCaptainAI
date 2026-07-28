"""
FileIndexer — Production-grade drive crawler.

Audit fixes applied:
- Yields (path, is_dir, name_lower, size, mtime) — 5-tuple for richer cache.
- Junction/symlink recursion guard via inode tracking.
- Long path support (\\\\?\\ prefix) on Windows for paths > 260 chars.
- Configurable skip folders from config.py instead of hardcoded set.
- Improved error handling — never crashes, always continues.
"""

import os
import stat
import string
import logging
import threading
from pathlib import Path
from typing import Callable, Optional, Generator

from actions.files.config import (
    MAX_CRAWL_DEPTH, SKIP_FOLDERS, SKIP_PREFIXES, WIN_LONG_PATH_PREFIX,
)

log = logging.getLogger("FileIndexer")


class FileIndexer:
    """
    Crawls directories and yields (path_str, is_dir, name_lower, size, mtime)
    tuples for every discovered item.

    Public API (preserved):
        crawl(roots) -> Generator
        cancel()
    """

    def __init__(
        self,
        cancel_event: Optional[threading.Event] = None,
        on_progress: Optional[Callable[[str], None]] = None,
        max_depth: int = MAX_CRAWL_DEPTH,
        skip_system: bool = True,
    ):
        self._cancel = cancel_event or threading.Event()
        self._on_progress = on_progress or (lambda msg: None)
        self._max_depth = max_depth
        self._skip_system = skip_system
        # WHY: track visited device+inode pairs to prevent infinite loops
        # caused by junction points or symbolic link cycles.
        self._visited: set[tuple[int, int]] = set()

    # ── Public API ─────────────────────────────────────────────────────────

    def crawl(
        self,
        roots: Optional[list[str]] = None,
    ) -> Generator[tuple[str, bool, str, int, float], None, None]:
        """
        Yield (full_path, is_directory, lowercase_name, size_bytes, mtime)
        for every item found.
        If roots is None, auto-detect all available Windows drive letters.
        """
        if roots is None:
            roots = self._detect_drives()

        self._visited.clear()

        for root in roots:
            if self._cancel.is_set():
                return
            root_path = root
            if not os.path.isdir(root_path):
                continue
            self._on_progress(f"Scanning {root_path}...")
            yield from self._walk(root_path, depth=0)

    def cancel(self):
        """Signal the crawler to stop as soon as possible."""
        self._cancel.set()

    # ── Internal ───────────────────────────────────────────────────────────

    def _walk(
        self, directory: str, depth: int
    ) -> Generator[tuple[str, bool, str, int, float], None, None]:
        """Recursive os.scandir walk with depth limiting, cancellation,
        and junction/symlink recursion protection."""
        if self._cancel.is_set() or depth > self._max_depth:
            return

        # WHY: on Windows, prefix long paths with \\?\ to bypass 260-char limit
        scan_dir = directory
        if os.name == "nt" and len(directory) > 240 and not directory.startswith(WIN_LONG_PATH_PREFIX):
            scan_dir = WIN_LONG_PATH_PREFIX + directory

        try:
            with os.scandir(scan_dir) as entries:
                for entry in entries:
                    if self._cancel.is_set():
                        return

                    name = entry.name
                    name_lower = name.lower()

                    # Skip hidden / system prefixes
                    if self._skip_system and name_lower[:1] in SKIP_PREFIXES:
                        continue

                    try:
                        is_dir = entry.is_dir(follow_symlinks=False)
                    except (OSError, PermissionError):
                        continue

                    if is_dir:
                        # Skip known system/noise folders
                        if self._skip_system and name_lower in SKIP_FOLDERS:
                            continue

                        # WHY: junction/symlink recursion guard.
                        # On Windows, junctions can create infinite loops
                        # (e.g. C:\Users\All Users -> C:\ProgramData).
                        try:
                            entry_stat = entry.stat(follow_symlinks=False)
                            inode_key = (entry_stat.st_dev, entry_stat.st_ino)
                            # st_ino is 0 on some Windows FS — skip dedup for those
                            if inode_key[1] != 0:
                                if inode_key in self._visited:
                                    continue
                                self._visited.add(inode_key)

                            # Check if it's a reparse point (junction/symlink)
                            if os.name == "nt" and (entry_stat.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                                # Still yield the directory name but limit recursion depth
                                yield (entry.path, True, name_lower, 0, entry_stat.st_mtime)
                                if depth < 2:  # Only shallow-follow reparse points
                                    yield from self._walk(entry.path, depth + 1)
                                continue
                        except (OSError, AttributeError):
                            pass

                        # Yield the directory itself
                        try:
                            dir_stat = entry.stat(follow_symlinks=False)
                            yield (entry.path, True, name_lower, 0, dir_stat.st_mtime)
                        except (OSError, PermissionError):
                            yield (entry.path, True, name_lower, 0, 0.0)

                        # Report progress for top-level directories
                        if depth <= 1:
                            self._on_progress(f"Scanning {entry.path}...")

                        # Recurse into subdirectory
                        yield from self._walk(entry.path, depth + 1)
                    else:
                        # Yield the file with size and mtime
                        try:
                            file_stat = entry.stat(follow_symlinks=False)
                            yield (entry.path, False, name_lower, file_stat.st_size, file_stat.st_mtime)
                        except (OSError, PermissionError):
                            yield (entry.path, False, name_lower, 0, 0.0)

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
            drives.append(str(Path.home()))
        return drives
