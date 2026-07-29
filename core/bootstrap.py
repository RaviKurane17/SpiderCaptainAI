"""
CAPTAIN AI — Bootstrap
Handles early initialization, PyInstaller fixes, and main script entry.
"""
import sys
import os
import subprocess
import multiprocessing
import runpy

def init_environment():
    """Apply PyInstaller Windows fixes before any other imports."""
    if sys.platform == "win32":
        _orig_init = subprocess.Popen.__init__
        def _patched_init(self, *args, **kwargs):
            if "creationflags" not in kwargs:
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            _orig_init(self, *args, **kwargs)
        subprocess.Popen.__init__ = _patched_init

    import traceback
    # Redirect stdout and stderr to files with utf-8 encoding to prevent UnicodeEncodeError in windowed .exe
    sys.stdout = open("captain_out.log", "w", encoding="utf-8", buffering=1)
    sys.stderr = open("crash_debug.log", "w", encoding="utf-8", buffering=1)

def run_app():
    """Main entry point."""
    multiprocessing.freeze_support()

    # ── Orb mode: MUST be checked before init_environment() ───────────────
    # init_environment() redirects sys.stdout to a log file, which would
    # break the stdout pipe used by the parent process to detect RESTORE signal.
    if len(sys.argv) > 1 and sys.argv[1] == '--orb':
        # signal_file path is passed as argv[2] for cross-process restore signal
        signal_file = sys.argv[2] if len(sys.argv) > 2 else None
        from PyQt6.QtWidgets import QApplication
        from core.orb import OrbWindow
        app = QApplication(sys.argv)
        orb = OrbWindow(signal_file=signal_file)
        orb.show()
        sys.exit(app.exec())

    init_environment()

    if len(sys.argv) > 1 and sys.argv[1].endswith('.py'):
        try:
            runpy.run_path(sys.argv[1], run_name="__main__")
        except Exception as e:
            print(f"Error running script {sys.argv[1]}: {e}")
            sys.exit(1)
        sys.exit(0)
        
    # Import the actual application setup logic
    import traceback
    def custom_excepthook(exc_type, exc_value, exc_traceback):
        with open("FATAL_CRASH.log", "a", encoding="utf-8") as f:
            f.write("SYS EXCEPTHOOK:\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    sys.excepthook = custom_excepthook

    def custom_thread_excepthook(args):
        with open("FATAL_CRASH.log", "a", encoding="utf-8") as f:
            f.write(f"THREAD EXCEPTHOOK in thread {args.thread.name if args.thread else 'Unknown'}:\n")
            traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback, file=f)
    import threading
    threading.excepthook = custom_thread_excepthook

    from core.captain_app import start_ui
    start_ui()
