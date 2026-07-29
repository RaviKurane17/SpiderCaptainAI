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
    
    global window, orb_window
    window = None
    orb_window = None
    class WindowAPI:
        def __init__(self):
            self.orb_process = None

        def close(self):
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
                import subprocess
                import sys
                import os
                import tempfile

                # --- Temp file IPC ---
                # stdout=PIPE is unreliable in windowed .exe (sys.stdout is None).
                # A temp file is the simplest & most reliable cross-process signal.
                signal_file = os.path.join(tempfile.gettempdir(), 'captain_orb_restore.tmp')
                try:
                    if os.path.exists(signal_file):
                        os.remove(signal_file)
                except Exception:
                    pass

                if window:
                    window.hide()

                # Build command
                if getattr(sys, 'frozen', False):
                    # Frozen .exe — re-launch self with --orb flag + signal file path
                    cmd = [sys.executable, '--orb', signal_file]
                else:
                    # Dev mode — launch orb.py directly
                    orb_script = os.path.join(os.path.dirname(__file__), 'orb.py')
                    cmd = [sys.executable, orb_script, signal_file]

                kwargs = {}
                if sys.platform == 'win32':
                    kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

                log.info(f"[Orb] Launching: {cmd}")
                self.orb_process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    **kwargs
                )
                log.info(f"[Orb] Process started with PID {self.orb_process.pid}")

                def monitor_orb():
                    import time
                    while True:
                        time.sleep(0.3)
                        # Check if restore was requested via signal file
                        if os.path.exists(signal_file):
                            try:
                                os.remove(signal_file)
                            except Exception:
                                pass
                            log.info("[Orb] Restore signal received")
                            self.restore_main()
                            break
                        # Check if orb process exited (crashed or closed)
                        if self.orb_process.poll() is not None:
                            log.info(f"[Orb] Process exited (code {self.orb_process.returncode}) — restoring")
                            self.restore_main()
                            break

                threading.Thread(target=monitor_orb, daemon=True, name="OrbMonitor").start()

            except Exception as e:
                log.error(f"[Orb] Failed to launch orb: {e}")
                # Always restore the window if orb fails to launch
                try:
                    if window:
                        window.show()
                except Exception:
                    pass

        def restore_main(self):
            try:
                if self.orb_process:
                    try:
                        self.orb_process.terminate()
                    except Exception:
                        pass
                    self.orb_process = None
                if window:
                    window.show()
                    log.info("[Orb] Main window restored")
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
