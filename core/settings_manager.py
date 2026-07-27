import json
import sqlite3
import base64
import os
import threading
from pathlib import Path
from utils.config import CONFIG_DIR
from utils.logger import log

SETTINGS_FILE = CONFIG_DIR / "settings.json"
VAULT_DB = CONFIG_DIR / "vault.db"
KEY_FILE = CONFIG_DIR / ".vault_key"

_local = threading.local()

# Default settings matching the user's requirements
DEFAULT_SETTINGS = {
    # AI Settings
    "ai_provider": "Gemini",
    "ai_model": "gemini-1.5-pro",
    "ai_temperature": 0.7,
    "ai_max_tokens": 8192,
    "ai_response_style": "Balanced",
    "ai_reasoning_mode": False,
    "ai_enable_tool_calling": True,
    "ai_enable_memory": True,
    "ai_enable_vision": True,
    
    # System Lifecycle
    "setup_complete": False,
    
    # Voice & Personality
    "voice_wake_word": "Captain",
    "voice_selection": "Aoede",
    "voice_speed": 1.0,
    "voice_pitch": 1.0,
    "voice_language": "English",
    "voice_interrupt": False,
    "voice_personality": "Jarvis",
    
    # Security
    "security_lock_type": "No Lock",
    "security_lock_on_startup": False,
    "security_lock_idle_min": 0,
    
    # Memory
    "memory_enabled": True,
    "memory_manual_only": False,
    "memory_ai_suggestions": True,
    
    # Automation
    "auto_enabled": True,
    "auto_startup_tasks": False,
    
    # Workspace
    "workspace_default": "Desktop",
    "workspace_auto_open": True,
    
    # Appearance
    "theme": "Dark",
    "accent_color": "Cyan",
    "font_size": "Medium",
    "animation_speed": "Normal",
    "transparency": True,
    
    # Performance
    "perf_mode": "Balanced",
    "perf_lazy_loading": True,
    
    # Notifications
    "notify_desktop": True,
    "notify_sound": True
}

def get_vault_key():
    if not KEY_FILE.exists():
        # Generate a random 32-byte key
        key = base64.b64encode(os.urandom(32))
        KEY_FILE.write_bytes(key)
    return base64.b64decode(KEY_FILE.read_bytes())

def encrypt_val(val: str) -> str:
    if not val:
        return ""
    key = get_vault_key()
    val_bytes = val.encode('utf-8')
    # Basic XOR cipher for obfuscation without adding heavy cryptography deps
    encrypted = bytearray()
    for i in range(len(val_bytes)):
        encrypted.append(val_bytes[i] ^ key[i % len(key)])
    return base64.b64encode(encrypted).decode('utf-8')

def decrypt_val(val: str) -> str:
    if not val:
        return ""
    try:
        key = get_vault_key()
        val_bytes = base64.b64decode(val.encode('utf-8'))
        decrypted = bytearray()
        for i in range(len(val_bytes)):
            decrypted.append(val_bytes[i] ^ key[i % len(key)])
        return decrypted.decode('utf-8')
    except Exception:
        return ""

def init_vault():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(VAULT_DB)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            provider TEXT PRIMARY KEY,
            key_data TEXT,
            is_enabled INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

def get_all_settings():
    """Reads settings.json, merging with defaults"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    settings = DEFAULT_SETTINGS.copy()
    
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
                settings.update(saved)
        except Exception as e:
            log.error(f"Failed to read settings: {e}")
            
    return settings

def update_setting(key: str, value):
    settings = get_all_settings()
    settings[key] = value
    
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)
        
    return {"success": True, "key": key}

def set_api_key(provider: str, api_key: str):
    conn = sqlite3.connect(VAULT_DB)
    enc = encrypt_val(api_key)
    conn.execute('''
        INSERT INTO api_keys (provider, key_data) 
        VALUES (?, ?) 
        ON CONFLICT(provider) DO UPDATE SET key_data = excluded.key_data
    ''', (provider, enc))
    conn.commit()
    conn.close()
    return {"success": True}

def get_api_key(provider: str):
    conn = sqlite3.connect(VAULT_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT key_data FROM api_keys WHERE provider = ?", (provider,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return decrypt_val(row[0])
    return ""

def get_api_providers_status():
    conn = sqlite3.connect(VAULT_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT provider, is_enabled FROM api_keys")
    rows = cursor.fetchall()
    conn.close()
    
    status = []
    configured = {r[0] for r in rows}
    
    for p in ["Gemini", "OpenAI", "Anthropic", "Groq", "Ollama"]:
        is_conf = p in configured
        status.append({
            "provider": p,
            "configured": is_conf,
            "enabled": True # would read from DB
        })
    return status

def factory_reset():
    if SETTINGS_FILE.exists():
        SETTINGS_FILE.unlink()
    if VAULT_DB.exists():
        VAULT_DB.unlink()
    if KEY_FILE.exists():
        KEY_FILE.unlink()
    init_vault()
    return {"success": True, "message": "Factory reset complete"}

def export_config():
    BACKUP_DIR = CONFIG_DIR / "backups"
    BACKUP_DIR.mkdir(exist_ok=True)
    backup_file = BACKUP_DIR / "settings_backup.json"
    
    settings = get_all_settings()
    with open(backup_file, "w") as f:
        json.dump(settings, f, indent=4)
    return {"success": True, "path": str(backup_file)}

def import_config():
    BACKUP_DIR = CONFIG_DIR / "backups"
    backup_file = BACKUP_DIR / "settings_backup.json"
    
    if not backup_file.exists():
        return {"success": False, "message": "No backup found"}
        
    try:
        with open(backup_file, "r") as f:
            data = json.load(f)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=4)
        return {"success": True, "message": "Configuration restored"}
    except Exception as e:
        return {"success": False, "message": str(e)}

init_vault()
