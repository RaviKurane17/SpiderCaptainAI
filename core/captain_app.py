"""
CAPTAIN AI — Captain App
Handles UI initialization and background thread startup.
"""
import asyncio
import threading
from core.live_session import CaptainLive
from core.tool_dispatcher import load_plugins
from utils import analytics as _analytics
from utils.logger import log

def start_ui():
    """Start the UI application and AI session runner."""
    import sys
    import os

    # Load plugins at startup
    load_plugins()

    # Start analytics session
    _analytics.start_session()

    # Initialize WebSocket bridge for React communications (headless mode)
    from core.websocket_server import init_bridge
    bridge = init_bridge(None)

    def runner():
        captain = CaptainLive(bridge)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(captain.run())
        except KeyboardInterrupt:
            log.info("\n🔴 Shutting down...")
            _analytics.end_session()

    threading.Thread(target=runner, daemon=True).start()

    # Launch pywebview to display the Vite React frontend
    import webview
    
    window = None

    # Expose control hooks to JavaScript (using lexical scope to avoid circular references)
    class WindowAPI:
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

    api_instance = WindowAPI()

    # Determine if running as executable or in development
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
        # Webview's local HTTP server will serve this file
        frontend_url = os.path.join(base_dir, 'frontend', 'dist', 'index.html')
    else:
        frontend_url = "http://127.0.0.1:8080"

    # Create the borderless desktop window
    window = webview.create_window(
        title="Captain AI",
        url=frontend_url,
        width=1360,
        height=720,
        min_size=(1100, 700),
        background_color="#050a14",
        frameless=True, # Frameless border matching user constraints
        js_api=api_instance
    )
    
    try:
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass

    webview.start()
