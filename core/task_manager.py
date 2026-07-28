"""
Captain AI — Unified Task Manager
==================================
Central authority for managing all background operations.
Every background task registers itself here for monitoring, 
cancellation, and diagnostics.
"""
import threading
import time
import uuid
import enum
from typing import Optional, Callable, Any
from collections import OrderedDict
from utils.logger import log


class TaskPriority(enum.IntEnum):
    LOW = 0         # Analytics, Benchmarks, Diagnostics
    MEDIUM = 1      # Web Search, File Search, OCR
    HIGH = 2        # Open App, Calculator, Volume
    CRITICAL = 3    # Voice, Shutdown, Authentication


class TaskStatus(enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class ManagedTask:
    """Represents a single tracked background task."""
    __slots__ = (
        "task_id", "name", "task_type", "priority", "status",
        "progress", "start_time", "end_time", "cancel_event",
        "exception", "_future",
    )

    def __init__(self, name: str, task_type: str = "general",
                 priority: TaskPriority = TaskPriority.MEDIUM):
        self.task_id = uuid.uuid4().hex[:8]
        self.name = name
        self.task_type = task_type
        self.priority = priority
        self.status = TaskStatus.QUEUED
        self.progress: float = 0.0
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.cancel_event = threading.Event()
        self.exception: Optional[Exception] = None
        self._future: Any = None

    @property
    def elapsed(self) -> float:
        if self.start_time == 0:
            return 0.0
        end = self.end_time if self.end_time > 0 else time.time()
        return end - self.start_time

    def cancel(self):
        self.cancel_event.set()
        self.status = TaskStatus.CANCELLED
        self.end_time = time.time()

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "type": self.task_type,
            "priority": self.priority.name,
            "status": self.status.value,
            "progress": self.progress,
            "elapsed": round(self.elapsed, 2),
            "error": str(self.exception) if self.exception else None,
        }


# Max tasks to keep in history (prevents unbounded memory growth)
_MAX_HISTORY = 200


class TaskManager:
    """
    Singleton task manager. All background operations should register through
    this class for unified tracking, cancellation, and diagnostics.
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
        self._lock = threading.RLock()
        self._tasks: OrderedDict[str, ManagedTask] = OrderedDict()
        self._initialized = True

    def register(self, name: str, task_type: str = "general",
                 priority: TaskPriority = TaskPriority.MEDIUM) -> ManagedTask:
        """Register a new task and return its ManagedTask handle."""
        task = ManagedTask(name, task_type, priority)
        with self._lock:
            self._tasks[task.task_id] = task
            self._trim_history()
        return task

    def start(self, task: ManagedTask):
        """Mark a task as running."""
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()

    def complete(self, task: ManagedTask):
        """Mark a task as completed."""
        task.status = TaskStatus.COMPLETED
        task.end_time = time.time()
        task.progress = 1.0

    def fail(self, task: ManagedTask, exception: Exception):
        """Mark a task as failed."""
        task.status = TaskStatus.FAILED
        task.exception = exception
        task.end_time = time.time()
        log.warning(f"[TaskManager] Task '{task.name}' failed: {exception}")

    def timeout(self, task: ManagedTask):
        """Mark a task as timed out."""
        task.status = TaskStatus.TIMED_OUT
        task.cancel_event.set()
        task.end_time = time.time()
        log.warning(f"[TaskManager] Task '{task.name}' timed out after {task.elapsed:.1f}s")

    def cancel(self, task_id: str) -> bool:
        """Cancel a task by ID. Returns True if found and cancelled."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.RUNNING:
                task.cancel()
                return True
        return False

    def get_active(self) -> list[dict]:
        """Return all currently running tasks as dicts."""
        with self._lock:
            return [
                t.to_dict() for t in self._tasks.values()
                if t.status in (TaskStatus.QUEUED, TaskStatus.RUNNING)
            ]

    def get_all(self) -> list[dict]:
        """Return all tasks (including completed) as dicts."""
        with self._lock:
            return [t.to_dict() for t in self._tasks.values()]

    def get_stats(self) -> dict:
        """Return summary statistics for health monitoring."""
        with self._lock:
            tasks = list(self._tasks.values())
        running = sum(1 for t in tasks if t.status == TaskStatus.RUNNING)
        queued = sum(1 for t in tasks if t.status == TaskStatus.QUEUED)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        timed_out = sum(1 for t in tasks if t.status == TaskStatus.TIMED_OUT)
        return {
            "running": running,
            "queued": queued,
            "completed": completed,
            "failed": failed,
            "timed_out": timed_out,
            "total_tracked": len(tasks),
        }

    def cleanup_completed(self, max_age_seconds: float = 300):
        """Remove completed/failed/cancelled tasks older than max_age_seconds."""
        cutoff = time.time() - max_age_seconds
        with self._lock:
            to_remove = [
                tid for tid, t in self._tasks.items()
                if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED,
                                TaskStatus.CANCELLED, TaskStatus.TIMED_OUT)
                and t.end_time > 0 and t.end_time < cutoff
            ]
            for tid in to_remove:
                del self._tasks[tid]

    def _trim_history(self):
        """Keep task history bounded."""
        while len(self._tasks) > _MAX_HISTORY:
            # Remove oldest completed task first
            oldest_done = None
            for tid, t in self._tasks.items():
                if t.status not in (TaskStatus.QUEUED, TaskStatus.RUNNING):
                    oldest_done = tid
                    break
            if oldest_done:
                del self._tasks[oldest_done]
            else:
                # All tasks are active — pop the oldest regardless
                self._tasks.popitem(last=False)


def get_task_manager() -> TaskManager:
    """Return the global TaskManager singleton."""
    return TaskManager()
