"""
monitor.py — Real-time filesystem monitoring.

WHY: Keeps the SQLite cache instantly up to date without requiring full
re-indexes.

Design:
- If `watchdog` is installed, uses it for instant event-based updates.
- Otherwise, falls back to a low-impact periodic incremental scanner.
- Both push changes to the central SearchCache.
- Operates on a dedicated background thread.
"""

import os
import time
import logging
import threading
from pathlib import Path
from typing import Optional

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    _HAS_WATCHDOG = True
except ImportError:
    _HAS_WATCHDOG = False

from actions.files.cache import SearchCache
from actions.files.config import SKIP_FOLDERS, SKIP_PREFIXES

log = logging.getLogger("FileMonitor")


class FileMonitor:
    """
    Monitors drives for file changes and updates the SearchCache.
    """

    def __init__(self, cache: SearchCache):
        self._cache = cache
        self._lock = threading.Lock()
        self._running = False
        
        if _HAS_WATCHDOG:
            self._observer = Observer()
            self._handler = _CacheUpdateHandler(cache)
        else:
            self._worker_thread: Optional[threading.Thread] = None
            self._cancel_event = threading.Event()

    def start(self, roots: list[str]):
        """Start monitoring the specified roots (e.g. ['C:\\'])."""
        with self._lock:
            if self._running:
                return
            self._running = True

            if _HAS_WATCHDOG:
                log.info("Starting Watchdog filesystem monitor...")
                for root in roots:
                    if os.path.exists(root):
                        try:
                            self._observer.schedule(self._handler, root, recursive=True)
                        except Exception as e:
                            log.error(f"Failed to schedule watchdog on {root}: {e}")
                self._observer.start()
            else:
                log.info("Watchdog not found. Starting periodic incremental monitor...")
                self._cancel_event.clear()
                self._worker_thread = threading.Thread(
                    target=self._periodic_worker,
                    args=(roots,),
                    daemon=True,
                    name="PeriodicFileMonitor"
                )
                self._worker_thread.start()

    def stop(self):
        """Stop monitoring."""
        with self._lock:
            if not self._running:
                return
            self._running = False

            if _HAS_WATCHDOG:
                self._observer.stop()
                self._observer.join(timeout=2.0)
            else:
                self._cancel_event.set()
                if self._worker_thread:
                    self._worker_thread.join(timeout=2.0)

    def _periodic_worker(self, roots: list[str]):
        """
        Fallback periodic scanner.
        Runs every 10 minutes to clean up stale entries and process recent files.
        """
        while not self._cancel_event.is_set():
            try:
                # 1. Clean stale paths
                self._cache.remove_missing(sample_size=5000)
                
                # 2. Quick scan for new/modified files (shallow)
                # (A full deep scan is too expensive, so we just do a quick
                # check of common user folders where files change often)
                user_dirs = [Path.home() / d for d in ["Desktop", "Downloads", "Documents"]]
                buffer = []
                now = time.time()
                
                for udir in user_dirs:
                    if self._cancel_event.is_set():
                        break
                    if not udir.exists():
                        continue
                        
                    for root, dirs, files in os.walk(udir):
                        if self._cancel_event.is_set():
                            break
                            
                        # Filter dirs
                        dirs[:] = [d for d in dirs if d.lower() not in SKIP_FOLDERS and not d.startswith(SKIP_PREFIXES)]
                        
                        # Process files modified in the last 10 minutes
                        for f in files:
                            if f.startswith(SKIP_PREFIXES):
                                continue
                            try:
                                full_path = os.path.join(root, f)
                                stat = os.stat(full_path)
                                if now - stat.st_mtime < 600:  # 10 minutes
                                    buffer.append((full_path, False, f.lower(), stat.st_size, stat.st_mtime))
                            except Exception:
                                pass
                                
                if buffer:
                    self._cache.bulk_upsert(buffer)
                    log.debug(f"Periodic monitor updated {len(buffer)} recent files.")
                    
            except Exception as e:
                log.error(f"Periodic monitor error: {e}", exc_info=True)
                
            # Sleep for 10 minutes, but check cancel event frequently
            for _ in range(600):
                if self._cancel_event.is_set():
                    break
                time.sleep(1.0)


if _HAS_WATCHDOG:
    class _CacheUpdateHandler(FileSystemEventHandler):
        """Watchdog handler that pushes events directly to the SearchCache."""
        
        def __init__(self, cache: SearchCache):
            self._cache = cache
            # Buffer for batching updates to avoid SQLite thrashing
            self._buffer: list[tuple] = []
            self._buffer_lock = threading.Lock()
            self._last_flush = time.time()
            self._flush_timer: Optional[threading.Timer] = None

        def _is_skipped(self, path_str: str) -> bool:
            """Check if path contains skipped folders/prefixes."""
            name = os.path.basename(path_str).lower()
            if name in SKIP_FOLDERS or name.startswith(SKIP_PREFIXES):
                return True
            parts = Path(path_str).parts
            for p in parts:
                if p.lower() in SKIP_FOLDERS:
                    return True
            return False

        def _schedule_flush(self):
            with self._buffer_lock:
                if self._flush_timer:
                    self._flush_timer.cancel()
                self._flush_timer = threading.Timer(1.0, self._flush)
                self._flush_timer.start()

        def _flush(self):
            with self._buffer_lock:
                if not self._buffer:
                    return
                to_insert = list(self._buffer)
                self._buffer.clear()
            
            try:
                self._cache.bulk_upsert(to_insert)
                log.debug(f"Watchdog flushed {len(to_insert)} updates to cache.")
            except Exception as e:
                log.error(f"Watchdog flush error: {e}")

        def on_created(self, event: FileSystemEvent):
            if self._is_skipped(event.src_path):
                return
            self._add_to_buffer(event.src_path, event.is_directory)

        def on_modified(self, event: FileSystemEvent):
            if self._is_skipped(event.src_path):
                return
            self._add_to_buffer(event.src_path, event.is_directory)

        def on_moved(self, event: FileSystemEvent):
            # Treat as delete + create
            self.on_deleted(event)
            if hasattr(event, 'dest_path') and not self._is_skipped(event.dest_path): # type: ignore
                self._add_to_buffer(event.dest_path, event.is_directory) # type: ignore

        def on_deleted(self, event: FileSystemEvent):
            # We handle deletes lazily via cache.remove_missing() or 
            # we could run a targeted DELETE query here. For performance,
            # we'll let remove_missing handle it, but for instant UI response
            # we do a targeted delete.
            try:
                conn = self._cache._get_conn()
                with self._cache._lock:
                    if event.is_directory:
                        conn.execute("DELETE FROM file_index WHERE path LIKE ?", (f"{event.src_path}%",))
                    else:
                        conn.execute("DELETE FROM file_index WHERE path = ?", (event.src_path,))
                    conn.commit()
            except Exception as e:
                log.error(f"Watchdog delete error: {e}")

        def _add_to_buffer(self, path_str: str, is_dir: bool):
            try:
                stat_res = os.stat(path_str)
                size = stat_res.st_size
                mtime = stat_res.st_mtime
            except OSError:
                size, mtime = 0, 0.0
                
            name_lower = os.path.basename(path_str).lower()
            
            with self._buffer_lock:
                self._buffer.append((path_str, is_dir, name_lower, size, mtime))
                if len(self._buffer) >= 100:
                    self._flush()
                else:
                    self._schedule_flush()
