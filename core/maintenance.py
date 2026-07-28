"""
Captain AI — Session Maintenance Daemon
=========================================
Runs every 5 minutes to explicitly clean up expired caches, completed tasks,
old websocket events, image/audio buffers, and temporary files.
Does NOT rely on Python GC alone.
"""
import threading
import time
import gc
import os
import glob
from utils.logger import log
from utils.config import BASE_DIR


_MAINTENANCE_INTERVAL = 300  # 5 minutes


class MaintenanceDaemon:
    """Periodic cleanup daemon for long-running sessions (8+ hours)."""
    _instance = None
    _init_lock = threading.Lock()

    def __new__(cls):
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._cycle_count = 0

    def start(self):
        """Start the maintenance daemon."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True,
                                         name="MaintenanceDaemon")
        self._thread.start()
        log.info("[Maintenance] Daemon started (interval=5min)")

    def stop(self):
        """Stop the maintenance daemon."""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _run_loop(self):
        """Main maintenance loop — runs every 5 minutes."""
        while not self._stop_event.wait(_MAINTENANCE_INTERVAL):
            self._cycle_count += 1
            t0 = time.time()
            try:
                self._run_cleanup()
            except Exception as e:
                log.warning(f"[Maintenance] Cycle {self._cycle_count} failed: {e}")
            elapsed = time.time() - t0
            log.debug(f"[Maintenance] Cycle {self._cycle_count} completed in {elapsed:.2f}s")

    def _run_cleanup(self):
        """Execute all cleanup tasks."""
        # 1. Clean up completed tasks from TaskManager
        self._cleanup_tasks()

        # 2. Clean up temporary screenshot files
        self._cleanup_temp_files()

        # 3. Force Python garbage collection
        gc.collect()

        # 4. Flush analytics to disk
        self._flush_analytics()

        # 5. Trim log files if they're getting too large
        self._check_log_rotation()

    def _cleanup_tasks(self):
        """Remove completed/failed tasks older than 5 minutes."""
        try:
            from core.task_manager import get_task_manager
            tm = get_task_manager()
            tm.cleanup_completed(max_age_seconds=300)
        except Exception as e:
            log.debug(f"[Maintenance] Task cleanup error: {e}")

    def _cleanup_temp_files(self):
        """Remove temporary screenshots and audio buffers."""
        temp_patterns = [
            str(BASE_DIR / "*.tmp"),
            str(BASE_DIR / "temp_screenshot*.png"),
            str(BASE_DIR / "temp_screenshot*.jpg"),
        ]
        removed = 0
        for pattern in temp_patterns:
            for f in glob.glob(pattern):
                try:
                    age = time.time() - os.path.getmtime(f)
                    if age > 120:  # older than 2 minutes
                        os.remove(f)
                        removed += 1
                except Exception:
                    pass
        if removed:
            log.debug(f"[Maintenance] Removed {removed} temp files")

    def _flush_analytics(self):
        """Ensure analytics data is flushed to disk."""
        try:
            from utils import analytics
            data = analytics._load()
            if analytics._write_counter > 0:
                analytics._save(data)
                analytics._write_counter = 0
        except Exception:
            pass

    def _check_log_rotation(self):
        """Check if captain_out.log or crash_debug.log are too large and truncate."""
        for logfile in ["captain_out.log", "crash_debug.log"]:
            path = BASE_DIR / logfile
            try:
                if path.exists() and path.stat().st_size > 10 * 1024 * 1024:  # 10 MB
                    # Keep only the last 1 MB
                    content = path.read_text(encoding="utf-8", errors="replace")
                    truncated = content[-1024 * 1024:]
                    path.write_text(truncated, encoding="utf-8")
                    log.info(f"[Maintenance] Truncated {logfile} (was >10MB)")
            except Exception:
                pass


def get_maintenance_daemon() -> MaintenanceDaemon:
    """Return the global MaintenanceDaemon singleton."""
    return MaintenanceDaemon()
