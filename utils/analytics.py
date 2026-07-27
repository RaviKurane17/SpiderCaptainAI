"""
Captain AI — Usage Analytics
==============================
Tracks tool usage, session duration, and command history.
Persists to memory/analytics.json for the Overview dashboard.
"""

import json
import time
import threading
from datetime import datetime

from utils.config import MEMORY_DIR


ANALYTICS_PATH = MEMORY_DIR / "analytics.json"
_lock = threading.RLock()
_analytics_cache = None
_write_counter = 0
_WRITE_INTERVAL = 5   # flush to disk every N track_tool() calls

def _load() -> dict:
    """Load analytics data from cache or disk."""
    global _analytics_cache
    with _lock:
        if _analytics_cache is not None:
            return _analytics_cache
            
        try:
            if ANALYTICS_PATH.exists():
                _analytics_cache = json.loads(ANALYTICS_PATH.read_text(encoding="utf-8"))
                return _analytics_cache
        except Exception:
            pass
            
        _analytics_cache = {
            "total_commands": 0,
            "total_sessions": 0,
            "tool_usage": {},
            "session_start": None,
            "total_session_seconds": 0,
            "daily_commands": {},
            "last_updated": None,
        }
        return _analytics_cache


def _save(data: dict) -> None:
    """Save analytics data to disk and update cache."""
    global _analytics_cache
    with _lock:
        try:
            _analytics_cache = data
            ANALYTICS_PATH.parent.mkdir(parents=True, exist_ok=True)
            data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ANALYTICS_PATH.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[Analytics] Save error: {e}")


def track_tool(tool_name: str) -> None:
    """Record a tool invocation. Batches disk writes every _WRITE_INTERVAL calls."""
    global _write_counter
    with _lock:
        data = _load()
        data["total_commands"] = data.get("total_commands", 0) + 1

        tools = data.get("tool_usage", {})
        tools[tool_name] = tools.get(tool_name, 0) + 1
        data["tool_usage"] = tools

        today = datetime.now().strftime("%Y-%m-%d")
        daily = data.get("daily_commands", {})
        daily[today] = daily.get(today, 0) + 1
        data["daily_commands"] = daily

        _analytics_cache = data   # always update in-memory cache
        _write_counter += 1
        if _write_counter >= _WRITE_INTERVAL:
            _write_counter = 0
            _save(data)


def start_session() -> None:
    """Mark the start of a new session."""
    with _lock:
        data = _load()
        data["total_sessions"] = data.get("total_sessions", 0) + 1
        data["session_start"] = time.time()
        _save(data)


def end_session() -> None:
    """Mark the end of the current session and flush any pending writes."""
    with _lock:
        data = _load()
        start = data.get("session_start")
        if start:
            elapsed = time.time() - start
            data["total_session_seconds"] = data.get("total_session_seconds", 0) + elapsed
            data["session_start"] = None
        _save(data)   # always flush on shutdown


def get_stats() -> dict:
    """Return a snapshot of analytics for the UI dashboard."""
    with _lock:
        # copy dict so we don't accidentally mutate the cache
        data = dict(_load())

    total_sec = data.get("total_session_seconds", 0)
    # Add current session time if active
    if data.get("session_start"):
        total_sec += time.time() - data["session_start"]

    hours = int(total_sec // 3600)
    minutes = int((total_sec % 3600) // 60)

    # Top 5 most used tools
    tools = data.get("tool_usage", {})
    top_tools = sorted(tools.items(), key=lambda x: x[1], reverse=True)[:8]

    return {
        "total_commands":  data.get("total_commands", 0),
        "total_sessions":  data.get("total_sessions", 0),
        "session_time":    f"{hours}h {minutes}m",
        "top_tools":       top_tools,
        "daily_commands":  data.get("daily_commands", {}),
        "last_updated":    data.get("last_updated", "Never"),
    }
