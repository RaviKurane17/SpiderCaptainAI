# config/__init__.py
import json, os, sys
from pathlib import Path

# Fix path resolution for PyInstaller
if getattr(sys, 'frozen', False):
    # If running as PyInstaller EXE, the config folder is placed next to the EXE
    _BASE_DIR = Path(sys.executable).parent
else:
    # If running normally, the base dir is the parent of the config folder
    _BASE_DIR = Path(__file__).parent.parent

_CONFIG_PATH = _BASE_DIR / "config" / "api_keys.json"

def get_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_os() -> str:
    """Returns: 'windows' | 'mac' | 'linux'"""
    return get_config().get("os_system", "windows").lower()

def is_windows() -> bool: return get_os() == "windows"
def is_mac()     -> bool: return get_os() == "mac"
def is_linux()   -> bool: return get_os() == "linux"