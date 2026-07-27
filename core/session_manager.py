"""
session_manager.py — Network monitoring and offline command handling.
monitor_connection runs in a background thread with a threading.Event stop signal.
"""
import time
import socket
import threading
from utils.logger import log

_STOP_EVENT = threading.Event()


def monitor_connection(state_dict: dict, tts_speak_callback, ui=None,
                        stop_event: threading.Event | None = None):
    """
    Polls 1.1.1.1:53 every 5 seconds to detect connectivity changes.
    Uses a stop_event so it can be cleanly shut down.
    Reuses a single socket attempt per cycle (no persistent socket held open).
    """
    stopper = stop_event or _STOP_EVENT

    if ui:
        try:
            ui.set_network_status(state_dict["online"])
        except Exception:
            pass

    while not stopper.wait(timeout=5.0):   # waits 5s or returns True if stopped
        was_online = state_dict["online"]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                t0 = time.perf_counter()
                s.connect(("1.1.1.1", 53))
                latency_ms = int((time.perf_counter() - t0) * 1000)
            state_dict["online"] = True
        except OSError:
            state_dict["online"] = False
            latency_ms = 0

        if was_online != state_dict["online"]:
            status = "ONLINE" if state_dict["online"] else "OFFLINE"
            log.info(f"[Connection] 🌐 Network → {status}")
            if ui:
                try:
                    ui.set_network_status(state_dict["online"])
                except Exception:
                    pass
            if not state_dict["online"]:
                tts_speak_callback("Connection lost. Operating in offline mode, sir.")
            else:
                tts_speak_callback("Connection restored. Reconnecting to satellite, sir.")
        elif latency_ms > 0 and ui:
            # Silently update latency on the UI without TTS
            try:
                ui.set_network_status(True)
            except Exception:
                pass


def stop_monitor():
    """Call on shutdown to stop the monitor thread."""
    _STOP_EVENT.set()


def handle_offline_command(text: str, ui, tts_speak_callback):
    ui.write_log(f"You: {text}")
    ui.set_state("THINKING")
    try:
        from actions.offline_parser import parse_and_execute_offline
        res = parse_and_execute_offline(text, player=ui)
        tts_speak_callback(res)
        ui.write_log(f"Captain (Offline): {res}")
    except ImportError:
        msg = "Offline parser not available."
        ui.write_log(f"ERR: {msg}")
        tts_speak_callback("Offline mode is not available, sir.")
    except Exception as exc:
        log.warning(f"[Offline] Command failed: {exc}")
        ui.write_log(f"ERR: {exc}")
        tts_speak_callback("I encountered an error executing offline, sir.")
    finally:
        ui.set_state("LISTENING")
