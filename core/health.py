"""
Captain AI — Runtime Health Monitor
=====================================
Lightweight daemon that runs every 30-60 seconds to track system health,
detect degraded states, and perform automated recovery.
"""
import threading
import time
import os
from utils.logger import log


# Maximum restart attempts before marking a worker as permanently failed
_MAX_RESTART_ATTEMPTS = 3
_RESTART_BACKOFF_BASE = 2.0  # seconds — exponential backoff multiplier


class HealthMonitor:
    """
    Periodic health checker. Tracks CPU, RAM, thread count, queue lengths,
    and latencies. Implements bounded restart logic with exponential backoff.
    """
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
        self._check_interval = 30  # seconds
        self._restart_counts: dict[str, int] = {}
        self._last_snapshot: dict = {}
        self._lock = threading.RLock()

    def start(self, interval: int = 30):
        """Start the health monitor daemon."""
        if self._running:
            return
        self._check_interval = interval
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, 
                                         name="HealthMonitor")
        self._thread.start()
        log.info(f"[Health] Monitor started (interval={interval}s)")

    def stop(self):
        """Stop the health monitor."""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        log.info("[Health] Monitor stopped")

    def get_snapshot(self) -> dict:
        """Return the latest health snapshot."""
        with self._lock:
            return dict(self._last_snapshot)

    def _run_loop(self):
        """Main monitoring loop."""
        while not self._stop_event.wait(self._check_interval):
            try:
                snapshot = self._collect_metrics()
                with self._lock:
                    self._last_snapshot = snapshot

                # Check for unhealthy conditions
                self._evaluate_health(snapshot)
            except Exception as e:
                log.warning(f"[Health] Monitor check failed: {e}")

    def _collect_metrics(self) -> dict:
        """Collect system metrics."""
        metrics = {
            "timestamp": time.time(),
            "threads": threading.active_count(),
        }

        try:
            import psutil
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            metrics["cpu_percent"] = process.cpu_percent(interval=0.5)
            metrics["ram_mb"] = round(mem_info.rss / (1024 * 1024), 1)
            metrics["ram_percent"] = process.memory_percent()
            metrics["open_files"] = len(process.open_files())
            metrics["thread_count_os"] = process.num_threads()
        except ImportError:
            metrics["cpu_percent"] = 0.0
            metrics["ram_mb"] = 0.0
            metrics["ram_percent"] = 0.0
            metrics["open_files"] = 0
            metrics["thread_count_os"] = 0
        except Exception as e:
            log.debug(f"[Health] psutil error: {e}")

        # Task Manager stats
        try:
            from core.task_manager import get_task_manager
            tm = get_task_manager()
            metrics["task_stats"] = tm.get_stats()
        except Exception:
            metrics["task_stats"] = {}

        metrics["status"] = "healthy"
        return metrics

    def _evaluate_health(self, snapshot: dict):
        """Evaluate health and take corrective action if needed."""
        issues = []

        # High memory warning (> 500 MB for this process)
        ram = snapshot.get("ram_mb", 0)
        if ram > 500:
            issues.append(f"High memory: {ram}MB")
            self._try_memory_cleanup()

        # High CPU warning (> 80% sustained)
        cpu = snapshot.get("cpu_percent", 0)
        if cpu > 80:
            issues.append(f"High CPU: {cpu}%")

        # Too many threads (> 50 is suspicious)
        threads = snapshot.get("threads", 0)
        if threads > 50:
            issues.append(f"High thread count: {threads}")

        # Too many open files (> 100)
        open_files = snapshot.get("open_files", 0)
        if open_files > 100:
            issues.append(f"Too many open files: {open_files}")

        if issues:
            snapshot["status"] = "degraded"
            for issue in issues:
                log.warning(f"[Health] ⚠️ {issue}")
        else:
            snapshot["status"] = "healthy"

    def _try_memory_cleanup(self):
        """Attempt to free memory by cleaning up caches and running GC."""
        import gc
        gc.collect()

        # Clean up completed tasks from the TaskManager
        try:
            from core.task_manager import get_task_manager
            get_task_manager().cleanup_completed(max_age_seconds=60)
        except Exception:
            pass

        log.info("[Health] Memory cleanup triggered")

    def can_restart_worker(self, worker_name: str) -> bool:
        """
        Check if a worker can be restarted (max 3 attempts with backoff).
        Returns True if restart is allowed.
        """
        with self._lock:
            count = self._restart_counts.get(worker_name, 0)
            if count >= _MAX_RESTART_ATTEMPTS:
                log.error(f"[Health] Worker '{worker_name}' exceeded max restarts ({_MAX_RESTART_ATTEMPTS}). Marking as failed.")
                return False
            self._restart_counts[worker_name] = count + 1

        # Exponential backoff
        backoff = _RESTART_BACKOFF_BASE ** count
        log.info(f"[Health] Restarting '{worker_name}' (attempt {count + 1}/{_MAX_RESTART_ATTEMPTS}, backoff={backoff:.1f}s)")
        time.sleep(backoff)
        return True

    def reset_restart_count(self, worker_name: str):
        """Reset restart counter for a worker after successful recovery."""
        with self._lock:
            self._restart_counts.pop(worker_name, None)


def get_health_monitor() -> HealthMonitor:
    """Return the global HealthMonitor singleton."""
    return HealthMonitor()
