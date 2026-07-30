"""
CAPTAIN AI — Captain App
Handles UI initialization and three-phase background thread startup.
"""
import asyncio
import threading
import time
from utils.logger import log


# ──────────────────────────────────────────────────────────────────────────
#  Startup Readiness States
# ──────────────────────────────────────────────────────────────────────────
class StartupState:
    STARTING = "STARTING"
    CORE_INITIALIZING = "CORE_INITIALIZING"
    CORE_READY = "CORE_READY"
    BACKGROUND_LOADING = "BACKGROUND_LOADING"
    FULLY_READY = "FULLY_READY"

_current_state = StartupState.STARTING
_state_lock = threading.Lock()

def _set_startup_state(state: str, bridge=None):
    """Update startup state and broadcast to frontend."""
    global _current_state
    with _state_lock:
        _current_state = state
    log.info(f"[Startup] State → {state}")
    if bridge and hasattr(bridge, 'broadcast'):
        bridge.broadcast({"type": "startup_state", "state": state})


# ──────────────────────────────────────────────────────────────────────────
#  Crash Recovery — runs before anything else
# ──────────────────────────────────────────────────────────────────────────
def _crash_recovery():
    """
    Clean up orphan state from a previous abnormal shutdown.
    Runs synchronously before Phase 1.
    """
    import glob
    import os
    from utils.config import BASE_DIR

    # 1. Remove stale lock files
    for lockfile in glob.glob(str(BASE_DIR / "*.lock")):
        try:
            os.remove(lockfile)
            log.info(f"[Recovery] Removed stale lock: {lockfile}")
        except Exception:
            pass

    # 2. Clean up temp screenshots/audio from a crash
    for pattern in ["temp_screenshot*.png", "temp_screenshot*.jpg", "*.tmp"]:
        for f in glob.glob(str(BASE_DIR / pattern)):
            try:
                os.remove(f)
            except Exception:
                pass
    # 3. Kill lingering orb processes (they all poll this file)
    import tempfile
    import time
    state_file = os.path.join(tempfile.gettempdir(), 'captain_orb_state.tmp')
    try:
        tmp = state_file + ".new"
        with open(tmp, 'w') as f:
            f.write('EXIT')
        os.replace(tmp, state_file)
        time.sleep(0.3)  # Give them time to read it and die
    except Exception:
        pass

    log.info("[Recovery] Crash recovery complete")


# ──────────────────────────────────────────────────────────────────────────
#  Phase 1: Critical Core (MUST finish before "I'm ready")
# ──────────────────────────────────────────────────────────────────────────
def _phase1_core(bridge):
    """
    Initialize everything the assistant needs to function:
    - Tool Dispatcher + Core Tool Registry
    - Settings Manager
    - Command Dispatcher
    - Basic File Search Engine
    """
    _set_startup_state(StartupState.CORE_INITIALIZING, bridge)

    # Load core tool declarations and plugins
    from core.tool_dispatcher import load_plugins
    load_plugins()

    # Pre-warm the file search engine (creates SQLite index if needed)
    try:
        from actions.files.engine import get_engine
        get_engine()
        log.info("[Phase1] File search engine initialized")
    except Exception as e:
        log.warning(f"[Phase1] File search engine init failed (non-fatal): {e}")

    _set_startup_state(StartupState.CORE_READY, bridge)
    log.info("[Phase1] ✅ Core initialization complete")


# ──────────────────────────────────────────────────────────────────────────
#  Phase 2: Background Initialization (non-blocking)
# ──────────────────────────────────────────────────────────────────────────
def _phase2_background(bridge):
    """
    Initialize services that can load while the user is already interacting.
    Runs in a background thread.
    """
    _set_startup_state(StartupState.BACKGROUND_LOADING, bridge)
    t0 = time.time()

    # Analytics session
    try:
        from utils import analytics as _analytics
        _analytics.start_session()
        log.info("[Phase2] Analytics started")
    except Exception as e:
        log.warning(f"[Phase2] Analytics failed: {e}")

    # Firebase listeners
    try:
        from core.event_manager import start_firebase_listener
        log.info("[Phase2] Firebase listener ready")
    except Exception as e:
        log.warning(f"[Phase2] Firebase failed: {e}")

    # Health Monitor
    try:
        from core.health import get_health_monitor
        get_health_monitor().start(interval=30)
        log.info("[Phase2] Health monitor started")
    except Exception as e:
        log.warning(f"[Phase2] Health monitor failed: {e}")

    # Maintenance Daemon (5-minute cleanup cycle)
    try:
        from core.maintenance import get_maintenance_daemon
        get_maintenance_daemon().start()
        log.info("[Phase2] Maintenance daemon started")
    except Exception as e:
        log.warning(f"[Phase2] Maintenance daemon failed: {e}")

    # Pre-warm OCR engine runtime (not the heavy AI models)
    try:
        import pytesseract
        # Just validate that tesseract is accessible — don't run OCR yet
        pytesseract.get_tesseract_version()
        log.info("[Phase2] OCR engine (Tesseract) pre-warmed")
    except Exception:
        log.debug("[Phase2] OCR engine not available (will load on demand)")

    elapsed = time.time() - t0
    _set_startup_state(StartupState.FULLY_READY, bridge)
    log.info(f"[Phase2] ✅ Background initialization complete in {elapsed:.2f}s")


# ──────────────────────────────────────────────────────────────────────────
#  Main Entry Point
# ──────────────────────────────────────────────────────────────────────────
def start_ui():
    """Start the UI application and AI session runner."""
    global window, orb_window
    import sys
    import os

    _set_startup_state(StartupState.STARTING)

    # ── Crash Recovery ─────────────────────────────────────────────────
    _crash_recovery()

    # ── WebSocket Bridge ───────────────────────────────────────────────
    from core.websocket_server import init_bridge
    bridge = init_bridge(None)

    # ── Phase 1: Critical Core (blocking) ──────────────────────────────
    _phase1_core(bridge)

    # ── Phase 2: Background Init (non-blocking) ───────────────────────
    threading.Thread(target=_phase2_background, args=(bridge,),
                     daemon=True, name="Phase2Init").start()

    # ── AI Session Runner ──────────────────────────────────────────────
    def runner():
        from core.live_session import CaptainLive
        captain = CaptainLive(bridge)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(captain.run())
        except KeyboardInterrupt:
            log.info("\n🔴 Shutting down...")
            try:
                from utils import analytics as _analytics
                _analytics.end_session()
            except Exception:
                pass
            try:
                from core.health import get_health_monitor
                get_health_monitor().stop()
            except Exception:
                pass
            try:
                from core.maintenance import get_maintenance_daemon
                get_maintenance_daemon().stop()
            except Exception:
                pass

    threading.Thread(target=runner, daemon=True).start()

    # ── Launch pywebview ───────────────────────────────────────────────
    import webview

    window = None
    orb_window = None
    class WindowAPI:
        def _write_state(self, state_str):
            try:
                import os
                tmp = self.state_file + ".new"
                with open(tmp, 'w') as f:
                    f.write(state_str)
                os.replace(tmp, self.state_file)
            except Exception:
                pass

        def __init__(self):
            import os
            import tempfile
            self.orb_process = None
            self.state_file = os.path.join(tempfile.gettempdir(), 'captain_orb_state.tmp')
            self._write_state('HIDE')
            self.orb_restored = False
            
            self.preload_orb()
            threading.Thread(target=self.monitor_state, daemon=True, name="OrbMonitor").start()

        def preload_orb(self):
            try:
                import subprocess
                import sys
                import os
                
                if getattr(sys, 'frozen', False):
                    cmd = [sys.executable, '--orb', self.state_file]
                else:
                    orb_script = os.path.join(os.path.dirname(__file__), 'orb.py')
                    cmd = [sys.executable, orb_script, self.state_file]

                kwargs = {}
                if sys.platform == 'win32':
                    kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

                log.info(f"[Orb] Preloading orb process...")
                self.orb_process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    **kwargs
                )
                log.info(f"[Orb] Process preloaded with PID {self.orb_process.pid}")
            except Exception as e:
                log.error(f"[Orb] Failed to preload orb: {e}")

        def monitor_state(self):
            import time
            import os
            while True:
                time.sleep(0.1)
                try:
                    if os.path.exists(self.state_file):
                        with open(self.state_file, 'r') as f:
                            state = f.read().strip()
                        
                        if state == 'RESTORE_MAIN':
                            if not getattr(self, 'orb_restored', False):
                                self.orb_restored = True
                                log.info("[Orb] Restore signal received via state file")
                                self.restore_main()
                except Exception:
                    pass

                # Check if orb process crashed
                if self.orb_process and self.orb_process.poll() is not None:
                    log.info(f"[Orb] Process exited (code {self.orb_process.returncode}) — restarting in background")
                    self.preload_orb()

        def close(self):
            self._write_state('EXIT')
            import os
            os._exit(0)

        def minimize(self):
            try:
                if window:
                    window.minimize()
            except Exception:
                pass

        def maximize(self):
            try:
                if window:
                    window.toggle_fullscreen()
            except Exception:
                pass

        def orb_mode(self):
            try:
                self.orb_restored = False
                self._write_state('SHOW')
                if window:
                    window.hide()
            except Exception as e:
                log.error(f"[Orb] Failed to transition to orb mode: {e}")
                self.restore_main()

        def restore_main(self):
            try:
                self._write_state('HIDE')
                if window:
                    window.show()
                    window.restore()
                    # Trick to force window to front on Windows
                    window.on_top = True
                    window.on_top = False
                    log.info("[Orb] Main window restored to foreground")
            except Exception as e:
                log.error(f"[Orb] Failed to restore main window: {e}")

    api_instance = WindowAPI()

    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
        frontend_url = os.path.join(base_dir, 'frontend', 'dist', 'index.html')
    else:
        frontend_url = "http://127.0.0.1:8080"

    window = webview.create_window(
        title="Captain AI",
        url=frontend_url,
        width=1360,
        height=720,
        min_size=(1100, 700),
        background_color="#050a14",
        frameless=True,
        js_api=api_instance
    )

    
    try:
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass

    webview.start()
