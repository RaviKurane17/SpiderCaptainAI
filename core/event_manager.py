import threading
from utils.logger import log
from utils.config import get_firebase_key_path, get_firebase_db_url
from utils.concurrency import run_in_background

def start_firebase_listener(ui, reply_state_dict):
    """Set up Firebase listener for phone voice commands (event-driven, not polling)."""
    import firebase_admin
    from firebase_admin import credentials, db

    log.info("[Firebase] Setting up Phone Listener...")
    if not firebase_admin._apps:
        try:
            fb_key = get_firebase_key_path()
            if not fb_key.exists():
                log.warning(f"[Firebase] Key not found: {fb_key} — phone agent disabled")
                return
            cred = credentials.Certificate(str(fb_key))
            firebase_admin.initialize_app(cred, {
                'databaseURL': get_firebase_db_url()
            })
        except Exception as e:
            log.error(f"[Firebase] Init Error: {e}")
            return

    def _on_command(event):
        """Firebase listener callback — fires on every child change."""
        try:
            if event.data is None or not isinstance(event.data, dict):
                return
            cmd = event.data
            if (cmd.get("action") == "voice_command"
                    and cmd.get("status") == "pending"
                    and cmd.get("targetDeviceId") == "PC"):
                text = cmd.get("message", "")
                key  = event.path.strip("/")
                log.info(f"[Phone Voice Command] {text}")

                # Mark as completed
                db.reference(f'commands/{key}').update({"status": "completed"})

                # Route to AI
                reply_state_dict['reply_to_phone'] = True
                if ui.on_text_command:
                    run_in_background(ui.on_text_command, text)
        except Exception as e:
            log.debug(f"[Firebase] Listener event error: {e}")

    try:
        db.reference('commands').listen(_on_command)
        log.info("[Firebase] ✅ Event-driven listener active")
    except Exception as exc:
        log.error(f"[Firebase] Listener failed: {exc} — falling back to polling")
        # Fallback: poll with exponential backoff (starts at 2s, caps at 30s)
        def _poll():
            import time
            delay = 2.0
            max_delay = 30.0
            while True:
                try:
                    results = db.reference('commands').order_by_key().limit_to_last(5).get()
                    if results:
                        for key, cmd in results.items():
                            if (isinstance(cmd, dict)
                                    and cmd.get("action") == "voice_command"
                                    and cmd.get("status") == "pending"
                                    and cmd.get("targetDeviceId") == "PC"):
                                text = cmd.get("message", "")
                                db.reference(f'commands/{key}').update({"status": "completed"})
                                reply_state_dict['reply_to_phone'] = True
                                if ui.on_text_command:
                                    run_in_background(ui.on_text_command, text)
                    delay = 2.0   # reset on success
                except Exception:
                    delay = min(delay * 2, max_delay)
                time.sleep(delay)
        run_in_background(_poll)