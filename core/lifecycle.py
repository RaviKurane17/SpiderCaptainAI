import threading
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, Any, List

from utils.logger import log

class ServiceState(Enum):
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    RESTARTING = "RESTARTING"


@dataclass
class RestartPolicy:
    restartable: bool = True
    max_retries: int = 5
    backoff_initial_sec: float = 1.0
    backoff_max_sec: float = 30.0
    critical: bool = False
    heartbeat_timeout_sec: float = 30.0

@dataclass
class ServiceMetrics:
    last_start: float = 0.0
    last_stop: float = 0.0
    last_restart: float = 0.0
    total_runtime: float = 0.0
    restart_count: int = 0
    crash_count: int = 0
    last_crash_time: float = 0.0
    last_exception: str = ""

    @property
    def uptime_sec(self) -> float:
        if self.last_start > self.last_stop:
            return time.time() - self.last_start
        return 0.0


class Service:
    def __init__(self, name: str, run_func: Callable, policy: RestartPolicy):
        self.name = name
        self.run_func = run_func
        self.policy = policy
        
        self.state = ServiceState.STOPPED
        self.metrics = ServiceMetrics()
        self.stop_event = threading.Event()
        self._thread = None
        
        self.last_heartbeat_time = time.time()
        self._lock = threading.RLock()

    def beat(self):
        """Service should call this periodically to prove it's not hung."""
        with self._lock:
            self.last_heartbeat_time = time.time()
        
    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                log.warning(f"[Service] {self.name} start() called but already running.")
                return

            self.stop_event.clear()
            self.state = ServiceState.STARTING
            self.metrics.last_start = time.time()
            self.last_heartbeat_time = time.time()
            
            self._thread = threading.Thread(target=self._runner, name=self.name, daemon=False)
            self._thread.start()

    def _runner(self):
        bus = get_lifecycle().event_bus
        try:
            with self._lock:
                self.state = ServiceState.RUNNING
            bus.publish("SERVICE_STARTED", {"name": self.name})
            
            self.run_func(self.stop_event, self.beat)
        except Exception as e:
            with self._lock:
                self.state = ServiceState.FAILED
                self.metrics.crash_count += 1
                self.metrics.last_crash_time = time.time()
                self.metrics.last_exception = traceback.format_exc()
            log.error(f"[Supervisor] Service {self.name} crashed:\n{self.metrics.last_exception}")
            bus.publish("SERVICE_FAILED", {"name": self.name, "error": self.metrics.last_exception})
        finally:
            with self._lock:
                if self.state != ServiceState.FAILED:
                    self.state = ServiceState.STOPPED
                self.metrics.last_stop = time.time()
                self.metrics.total_runtime += (self.metrics.last_stop - self.metrics.last_start)
            if self.state == ServiceState.STOPPED:
                bus.publish("SERVICE_STOPPED", {"name": self.name})


    def stop(self):
        with self._lock:
            if self.state in (ServiceState.STOPPED, ServiceState.FAILED):
                return
            self.state = ServiceState.STOPPING
        
        self.stop_event.set()
        
        if self._thread and self._thread.is_alive():
            if threading.current_thread() != self._thread:
                self._thread.join(timeout=5.0)
                
        with self._lock:
            if self._thread and self._thread.is_alive():
                log.error(f"[Service] {self.name} ignored stop_event and zombie'd. Marking FAILED.")
                self.state = ServiceState.FAILED
                self.metrics.last_stop = time.time()


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callable):
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        with self._lock:
            if event_type in self._subscribers:
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)

    def publish(self, event_type: str, data: Any = None):
        with self._lock:
            subs = self._subscribers.get(event_type, []).copy()
            
        def _dispatch():
            for cb in subs:
                try:
                    cb(data)
                except Exception as e:
                    log.error(f"[EventBus] Error in subscriber for {event_type}:\n{traceback.format_exc()}")
                    
        # Dispatch asynchronously to avoid blocking the publisher
        threading.Thread(target=_dispatch, daemon=True, name=f"EventBus_{event_type}").start()


class LifecycleManager:
    """
    Central manager for Service Registry, Supervisor, Shutdown, and Event Bus.
    """
    _instance = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = LifecycleManager()
            return cls._instance

    def __init__(self):
        self.services: Dict[str, Service] = {}
        self.event_bus = EventBus()
        self._shutdown_hooks: List[Dict[str, Any]] = []
        self._supervisor_thread = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()

    def register_service(self, name: str, run_func: Callable, policy: RestartPolicy) -> Service:
        with self._lock:
            svc = Service(name, run_func, policy)
            self.services[name] = svc
            return svc

    def register_shutdown_hook(self, name: str, hook: Callable):
        with self._lock:
            self._shutdown_hooks.append({"name": name, "callback": hook})

    def start_all(self):
        self._stop_event.clear()
        with self._lock:
            svcs = list(self.services.values())
            
        for svc in svcs:
            svc.start()
            
        self._supervisor_thread = threading.Thread(target=self._supervise_loop, name="Supervisor", daemon=False)
        self._supervisor_thread.start()

    def _supervise_loop(self):
        """Watches for crashes and hangs, applying restart policies."""
        while not self._stop_event.wait(2.0):
            now = time.time()
            
            with self._lock:
                svcs = list(self.services.values())
                
            for svc in svcs:
                with svc._lock:
                    state = svc.state
                    last_beat = svc.last_heartbeat_time
                    uptime = svc.metrics.uptime_sec
                    
                if state == ServiceState.RUNNING:
                    # Reset restart count if it's been healthy for > 5 minutes
                    if uptime > 300 and svc.metrics.restart_count > 0:
                        with svc._lock:
                            svc.metrics.restart_count = 0
                            
                    # Check heartbeat watchdog
                    if (now - last_beat) > svc.policy.heartbeat_timeout_sec:
                        log.warning(f"[Supervisor] Service {svc.name} hung (no heartbeat > {svc.policy.heartbeat_timeout_sec}s). Restarting.")
                        self._handle_failure(svc)
                        
                elif state == ServiceState.FAILED:
                    self._handle_failure(svc)

    def _handle_failure(self, svc: Service):
        svc.stop() # Ensure it's cleanly shut down if it was hung
        
        if self._stop_event.is_set():
            return
            
        if not svc.policy.restartable:
            log.info(f"[Supervisor] Service {svc.name} is not restartable. Leaving FAILED.")
            with svc._lock:
                svc.state = ServiceState.FAILED
            if svc.policy.critical:
                log.critical(f"[Supervisor] CRITICAL SERVICE {svc.name} FAILED. SHUTTING DOWN APP.")
                self.shutdown_all()
            return

        with svc._lock:
            if svc.policy.max_retries > 0 and svc.metrics.restart_count >= svc.policy.max_retries:
                log.error(f"[Supervisor] Service {svc.name} hit max retries ({svc.policy.max_retries}). Marking FAILED.")
                svc.state = ServiceState.FAILED
                if svc.policy.critical:
                    log.critical(f"[Supervisor] CRITICAL SERVICE {svc.name} FAILED AFTER RETRIES. SHUTTING DOWN APP.")
                    # Trigger shutdown async so we don't block supervisor
                    threading.Thread(target=self.shutdown_all, daemon=True).start()
                return

            svc.state = ServiceState.RESTARTING
            svc.metrics.restart_count += 1
            svc.metrics.last_restart = time.time()
            restart_count = svc.metrics.restart_count
            
        # Exponential backoff
        backoff = min(
            svc.policy.backoff_initial_sec * (2 ** (restart_count - 1)),
            svc.policy.backoff_max_sec
        )
        
        log.info(f"[Supervisor] Restart #{restart_count} for {svc.name}. Waiting {backoff:.1f} sec...")
        self.event_bus.publish("SERVICE_RESTARTED", {"name": svc.name, "count": restart_count})
        
        def _delayed_restart():
            if self._stop_event.wait(timeout=backoff):
                return # Abort restart if global shutdown happens
            log.info(f"[Supervisor] Restarting {svc.name} now.")
            svc.start()

        threading.Thread(target=_delayed_restart, name=f"{svc.name}_RestartTimer", daemon=True).start()

    def shutdown_all(self):
        if self._stop_event.is_set():
            return
        log.info("\n🔴 [ShutdownManager] Initiating central shutdown...")
        self._stop_event.set()
        
        # 1. Stop all managed services
        with self._lock:
            svcs = list(self.services.values())
            
        for svc in svcs:
            try:
                log.info(f"[ShutdownManager] Stopping service {svc.name}...")
                svc.stop()
            except Exception as e:
                log.error(f"[ShutdownManager] Error stopping {svc.name}:\n{traceback.format_exc()}")

        # 2. Run explicit hooks
        with self._lock:
            hooks = list(self._shutdown_hooks)
            
        for hook_data in hooks:
            name = hook_data["name"]
            hook = hook_data["callback"]
            try:
                log.info(f"[ShutdownManager] Running hook: {name}")
                hook()
            except Exception as e:
                log.error(f"[ShutdownManager] Error in hook {name}:\n{traceback.format_exc()}")

        if self._supervisor_thread and self._supervisor_thread.is_alive():
            if threading.current_thread() != self._supervisor_thread:
                self._supervisor_thread.join(timeout=5.0)
            
        log.info("[ShutdownManager] Shutdown complete.")

# Global shorthand
def get_lifecycle() -> LifecycleManager:
    return LifecycleManager.get_instance()
