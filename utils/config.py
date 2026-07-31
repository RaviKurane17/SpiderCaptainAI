"""
Captain AI — Centralised Configuration
=======================================
Single source of truth for base directories, API keys, and env-specific settings.
Replaces the duplicated get_base_dir() / _get_api_key() scattered across 6+ files.

Priority: .env file  →  config/api_keys.json  →  raise error
"""

import json
import os
import sys
import threading
from pathlib import Path
from functools import lru_cache

# ---------------------------------------------------------------------------
#  Base directory (works both in dev and PyInstaller frozen builds)
# ---------------------------------------------------------------------------

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def get_assets_dir() -> Path:
    """In frozen builds, bundled files live in _MEIPASS. In dev, same as BASE_DIR."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


BASE_DIR        = get_base_dir()          # runtime writable dir (config, memory, .env)
ASSETS_DIR      = get_assets_dir()        # bundled read-only assets (_internal in exe)
CONFIG_DIR      = BASE_DIR / "config"
API_CONFIG_PATH = CONFIG_DIR / "api_keys.json"
PROMPT_PATH     = ASSETS_DIR / "core" / "prompt.txt"   # bundled asset → use ASSETS_DIR
MEMORY_DIR      = BASE_DIR / "memory"
LOGS_DIR        = BASE_DIR / "logs"

_config_cache = None
_config_lock = threading.RLock()
_env_loaded = False


# ---------------------------------------------------------------------------
#  .env loader (zero-dependency — no python-dotenv required at runtime)
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    """Load .env from project root if it exists.  No external deps needed."""
    global _env_loaded
    with _config_lock:
        if _env_loaded:
            return
        _env_loaded = True
        env_path = BASE_DIR / ".env"
        if not env_path.exists():
            return
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("\"'")
                if key and key not in os.environ:       # don't override real env vars
                    os.environ[key] = value
        except Exception as e:
            print(f"[Config] ⚠️ Failed to load .env: {e}")


# ---------------------------------------------------------------------------
#  Config getters and setters
# ---------------------------------------------------------------------------

def _read_json_config() -> dict:
    """Read config/api_keys.json with in-memory caching."""
    global _config_cache
    with _config_lock:
        if _config_cache is not None:
            return _config_cache
            
        try:
            if API_CONFIG_PATH.exists():
                _config_cache = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
                return _config_cache
        except Exception:
            pass
            
        _config_cache = {}
        return _config_cache


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def config_exists() -> bool:
    return API_CONFIG_PATH.exists()


def save_api_keys(gemini_api_key: str) -> None:
    """Saves the API keys and updates the cache."""
    ensure_config_dir()
    global _config_cache
    
    with _config_lock:
        data = _read_json_config()
        data["gemini_api_key"] = gemini_api_key.strip()
        
        API_CONFIG_PATH.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )
        _config_cache = data


def is_configured() -> bool:
    """Checks if the API key is configured."""
    key = get_api_key(safe=True)
    return bool(key and len(key) > 15)


def get_api_key(safe: bool = False) -> str:
    """Return the Gemini API key.  .env > api_keys.json > error."""
    _load_dotenv()
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    key = _read_json_config().get("gemini_api_key", "").strip()
    if key:
        return key
        
    if safe:
        return ""
        
    raise RuntimeError(
        "No Gemini API key found.  Set GEMINI_API_KEY in .env or config/api_keys.json"
    )


def get_voice() -> str:
    """Return the configured TTS voice name."""
    _load_dotenv()
    voice = os.environ.get("CAPTAIN_VOICE", "").strip()
    if voice:
        return voice
        
    try:
        from core.settings_manager import get_all_settings
        settings = get_all_settings()
        v = settings.get("voice_personality") or settings.get("voice_selection")
        if v:
            # Map friendly names to actual Gemini voices
            voice_map = {
                "Professional": "Charon",
                "Friendly": "Kore",
                "Cyberpunk": "Fenrir",
                "Jarvis": "Puck",
                "Friday": "Aoede",
                "Aoede": "Aoede",
                "Puck": "Puck",
                "Charon": "Charon",
                "Kore": "Kore",
                "Fenrir": "Fenrir",
            }
            return voice_map.get(v, v)
    except Exception as e:
        print(f"[Config] Failed to read voice from settings: {e}")

    return _read_json_config().get("voice", "Aoede")


def get_os_system() -> str:
    """Return the configured OS string (windows / mac / linux)."""
    return _read_json_config().get("os_system", "windows").lower()


def get_firebase_key_path() -> Path:
    """Return the path to the Firebase Admin SDK JSON key."""
    _load_dotenv()
    p = os.environ.get("FIREBASE_KEY_PATH", "").strip()
    if p:
        return Path(p)
    # Default: look for any firebase admin sdk json in project root
    for f in BASE_DIR.glob("*firebase*adminsdk*.json"):
        return f
    return BASE_DIR / "firebase-key.json"       # fallback name


def get_phone_device_id() -> str:
    """Return the phone device ID for Firebase commands."""
    _load_dotenv()
    did = os.environ.get("PHONE_DEVICE_ID", "").strip()
    if did:
        return did
    return _read_json_config().get("phone_device_id", "")


def get_firebase_db_url() -> str:
    """Return the Firebase Realtime Database URL."""
    _load_dotenv()
    url = os.environ.get("FIREBASE_DB_URL", "").strip()
    if url:
        return url
    return _read_json_config().get(
        "firebase_db_url",
        "https://ai-phone-agent-controls-default-rtdb.firebaseio.com/"
    )


# ---------------------------------------------------------------------------
#  User-path helpers (for prompt interpolation)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_user_paths() -> dict[str, str]:
    """Return common user directories for prompt interpolation."""
    home = Path.home()
    desktop = home / "Desktop"
    documents = home / "Documents"
    downloads = home / "Downloads"
    onedrive  = home / "OneDrive"

    # Windows OneDrive redirect
    if not desktop.exists() and (onedrive / "Desktop").exists():
        desktop = onedrive / "Desktop"
    if not documents.exists() and (onedrive / "Documents").exists():
        documents = onedrive / "Documents"

    return {
        "HOME":      str(home),
        "DESKTOP":   str(desktop),
        "DOCUMENTS": str(documents),
        "DOWNLOADS": str(downloads),
        "ONEDRIVE":  str(onedrive),
        "USERNAME":  home.name,
    }

