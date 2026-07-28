"""
Captain AI — Configuration Profiles
=====================================
Supports Performance, Balanced, and Accuracy modes for different hardware.
Profiles affect screenshot quality, cache sizes, diagnostics verbosity,
and CPU usage limits.
"""
import os
import enum
import threading
from utils.logger import log


class ProfileMode(enum.Enum):
    PERFORMANCE = "performance"
    BALANCED = "balanced"
    ACCURACY = "accuracy"


# Default profile settings for each mode
_PROFILE_DEFAULTS = {
    ProfileMode.PERFORMANCE: {
        "screenshot_quality": 40,       # JPEG quality (0-100)
        "screenshot_max_width": 480,    # Max screenshot width in pixels
        "screenshot_format": "JPEG",
        "cache_max_items": 500,
        "diagnostics_enabled": False,
        "search_max_results": 20,
        "health_check_interval": 60,    # seconds
        "analytics_flush_interval": 30, # seconds
        "maintenance_interval": 600,    # 10 minutes
        "description": "Lower quality, fewer diagnostics, minimal CPU usage",
    },
    ProfileMode.BALANCED: {
        "screenshot_quality": 70,
        "screenshot_max_width": 640,
        "screenshot_format": "JPEG",
        "cache_max_items": 1000,
        "diagnostics_enabled": False,
        "search_max_results": 30,
        "health_check_interval": 30,
        "analytics_flush_interval": 10,
        "maintenance_interval": 300,
        "description": "Default — good balance of quality and performance",
    },
    ProfileMode.ACCURACY: {
        "screenshot_quality": 95,
        "screenshot_max_width": 1280,
        "screenshot_format": "PNG",
        "cache_max_items": 2000,
        "diagnostics_enabled": True,
        "search_max_results": 50,
        "health_check_interval": 15,
        "analytics_flush_interval": 5,
        "maintenance_interval": 180,
        "description": "Higher quality screenshots, more OCR, more memory usage",
    },
}


_current_profile = ProfileMode.BALANCED
_profile_lock = threading.Lock()
_overrides: dict = {}


def get_profile() -> ProfileMode:
    """Return the active profile mode."""
    return _current_profile


def set_profile(mode: ProfileMode):
    """Switch to a different profile mode."""
    global _current_profile
    with _profile_lock:
        _current_profile = mode
        log.info(f"[Profile] Switched to {mode.value}")


def get_setting(key: str):
    """
    Get a profile setting. Override values take precedence over profile defaults.
    """
    with _profile_lock:
        if key in _overrides:
            return _overrides[key]
        defaults = _PROFILE_DEFAULTS.get(_current_profile, {})
        return defaults.get(key)


def set_override(key: str, value):
    """Override a specific setting regardless of active profile."""
    with _profile_lock:
        _overrides[key] = value


def get_all_settings() -> dict:
    """Return merged settings (profile defaults + overrides)."""
    with _profile_lock:
        defaults = dict(_PROFILE_DEFAULTS.get(_current_profile, {}))
        defaults.update(_overrides)
        defaults["active_profile"] = _current_profile.value
        return defaults


def detect_optimal_profile() -> ProfileMode:
    """
    Auto-detect the best profile based on system capabilities.
    Low-end: < 8 GB RAM or < 4 cores → Performance
    Mid-range: 8-16 GB RAM → Balanced
    High-end: > 16 GB RAM → Accuracy
    """
    try:
        import psutil
        total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        cpu_count = os.cpu_count() or 2

        if total_ram_gb < 8 or cpu_count < 4:
            return ProfileMode.PERFORMANCE
        elif total_ram_gb > 16 and cpu_count >= 8:
            return ProfileMode.ACCURACY
        else:
            return ProfileMode.BALANCED
    except ImportError:
        return ProfileMode.BALANCED
