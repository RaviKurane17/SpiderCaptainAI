"""
task_registry.py — Global Task Registry for Captain AI.

Every background operation (agent_task, dev_agent, file_processor, file search)
registers itself here so that:
  1. The user can cancel ANY running task via voice ("stop that task").
  2. The system can list what's currently running.
  3. Completed tasks are auto-cleaned.

Thread-safe singleton — all methods are guarded by a lock.
"""

import threading
import time
import logging
from typing import Callable, Optional, Dict

log = logging.getLogger("TaskRegistry")

_registry_instance: Optional["TaskRegistry"] = None
_registry_lock = threading.Lock()


def get_registry() -> "TaskRegistry":
    """Return the global TaskRegistry singleton."""
    global _registry_instance
    if _registry_instance is None:
        with _registry_lock:
            if _registry_instance is None:
                _registry_instance = TaskRegistry()
    return _registry_instance


class _RegisteredTask:
    __slots__ = ("task_id", "name", "cancel_fn", "started_at", "status")

    def __init__(self, task_id: str, name: str, cancel_fn: Callable):
        self.task_id = task_id
        self.name = name
        self.cancel_fn = cancel_fn
        self.started_at = time.time()
        self.status = "running"


class TaskRegistry:
    """
    Central registry for all background work in Captain AI.

    Usage:
        registry = get_registry()
        registry.register("abc123", "File Search", lambda: engine.cancel_search())
        ...
        registry.cancel_all()   # user said "stop that task"
        registry.deregister("abc123")  # task finished normally
    """

    def __init__(self):
        self._tasks: Dict[str, _RegisteredTask] = {}
        self._lock = threading.Lock()

    def register(self, task_id: str, name: str, cancel_fn: Callable) -> None:
        """Register a running task with its cancel callback."""
        with self._lock:
            self._tasks[task_id] = _RegisteredTask(task_id, name, cancel_fn)
        log.info(f"[TaskRegistry] ✅ Registered: [{task_id}] {name}")

    def deregister(self, task_id: str) -> None:
        """Remove a task after it completes or fails."""
        with self._lock:
            removed = self._tasks.pop(task_id, None)
        if removed:
            log.info(f"[TaskRegistry] 🗑️ Deregistered: [{task_id}] {removed.name}")

    def cancel(self, task_id: str) -> bool:
        """Cancel a specific task by ID. Returns True if found and cancelled."""
        with self._lock:
            task = self._tasks.get(task_id)
        if not task:
            return False
        try:
            task.cancel_fn()
            task.status = "cancelled"
            log.info(f"[TaskRegistry] 🛑 Cancelled: [{task_id}] {task.name}")
            return True
        except Exception as e:
            log.error(f"[TaskRegistry] ❌ Cancel failed for [{task_id}]: {e}")
            return False

    def cancel_all(self) -> int:
        """Cancel ALL running tasks. Returns the number of tasks cancelled."""
        with self._lock:
            tasks = list(self._tasks.values())
        cancelled = 0
        for task in tasks:
            try:
                task.cancel_fn()
                task.status = "cancelled"
                cancelled += 1
                log.info(f"[TaskRegistry] 🛑 Cancelled: [{task.task_id}] {task.name}")
            except Exception as e:
                log.error(f"[TaskRegistry] ❌ Cancel failed for [{task.task_id}]: {e}")
        return cancelled

    def list_active(self) -> list[dict]:
        """Return a list of all currently registered (running) tasks."""
        with self._lock:
            return [
                {
                    "task_id": t.task_id,
                    "name": t.name,
                    "status": t.status,
                    "running_for": f"{time.time() - t.started_at:.1f}s",
                }
                for t in self._tasks.values()
                if t.status == "running"
            ]

    def has_active_tasks(self) -> bool:
        """Check if any tasks are currently running."""
        with self._lock:
            return any(t.status == "running" for t in self._tasks.values())

    def cleanup_stale(self, max_age_seconds: float = 300.0) -> None:
        """Remove tasks that have been registered for too long (likely orphaned)."""
        now = time.time()
        with self._lock:
            stale = [
                tid for tid, t in self._tasks.items()
                if (now - t.started_at) > max_age_seconds and t.status != "running"
            ]
            for tid in stale:
                del self._tasks[tid]
        if stale:
            log.info(f"[TaskRegistry] 🧹 Cleaned {len(stale)} stale tasks")
