import time
import threading
from utils.logger import log

class AutomationEngine:
    """
    Background engine for executing AI-scheduled tasks.
    Example: "Clean Downloads folder every day"
    """
    def __init__(self):
        self.tasks = []
        self.running = False
        self._thread = None

    def add_task(self, name: str, interval_seconds: int, action_callback):
        self.tasks.append({
            "name": name,
            "interval": interval_seconds,
            "action": action_callback,
            "last_run": 0
        })
        log.info(f"[Automation] Task added: {name} (Interval: {interval_seconds}s)")

    def _loop(self):
        while self.running:
            now = time.time()
            for task in self.tasks:
                if now - task["last_run"] >= task["interval"]:
                    try:
                        log.info(f"[Automation] Executing task: {task['name']}")
                        task["action"]()
                        task["last_run"] = now
                    except Exception as e:
                        log.error(f"[Automation] Task {task['name']} failed: {e}")
            time.sleep(60) # Check every minute

    def start(self):
        if self.running: return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("[Automation] Engine started")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2.0)

# Global instance
engine = AutomationEngine()
