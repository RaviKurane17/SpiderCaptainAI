import sqlite3
import json
import time
from pathlib import Path
from utils.config import MEMORY_DIR
from utils.logger import log

COMMANDS_DB_PATH = MEMORY_DIR / "commands.db"

# Default seed commands for the UI
DEFAULT_COMMANDS = [
    {"title": "System Info", "cmd": "show system information", "desc": "Show operating system and specs", "category": "System", "icon": "MonitorCog", "color": "text-[var(--cyan)]"},
    {"title": "Set Reminder", "cmd": "remind me to complete coding in 10 minutes", "desc": "Schedule a notification timer", "category": "Productivity", "icon": "BellRing", "color": "text-[var(--violet)]"},
    {"title": "Take Screenshot", "cmd": "take a screenshot of the system", "desc": "Capture dashboard screenshot", "category": "System", "icon": "Camera", "color": "text-[var(--cyan)]"},
    {"title": "Firebase Status", "cmd": "check firebase db connection status", "desc": "Verify cloud listener sync", "category": "AI", "icon": "ShieldAlert", "color": "text-rose-400"},
    {"title": "Check Weather", "cmd": "what is the current weather forecast", "desc": "Show current meteorological readings", "category": "Productivity", "icon": "CloudRain", "color": "text-sky-400"},
    {"title": "Assistant Help", "cmd": "help", "desc": "List all custom plugin commands", "category": "AI", "icon": "HelpCircle", "color": "text-amber-400"},
    {"title": "Open VS Code", "cmd": "open vscode", "desc": "Launch code editor", "category": "Coding", "icon": "Terminal", "color": "text-blue-500"},
    {"title": "Clear Memory", "cmd": "clear my short term memory", "desc": "Wipes current session context", "category": "AI", "icon": "Database", "color": "text-red-500"},
]

def init_db():
    """Initializes the SQLite database and seeds default commands."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(COMMANDS_DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Table: commands (Registry of available commands)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                cmd TEXT UNIQUE,
                desc TEXT,
                category TEXT,
                icon TEXT,
                color TEXT,
                is_pinned BOOLEAN DEFAULT 0,
                created_at REAL
            )
        ''')
        
        # Table: command_history (Execution logs)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cmd TEXT,
                status TEXT,
                latency REAL,
                executed_at REAL
            )
        ''')
        
        # Seed default commands if empty
        cursor.execute("SELECT COUNT(*) FROM commands")
        if cursor.fetchone()[0] == 0:
            now = time.time()
            for cmd in DEFAULT_COMMANDS:
                cursor.execute('''
                    INSERT INTO commands (title, cmd, desc, category, icon, color, is_pinned, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (cmd['title'], cmd['cmd'], cmd['desc'], cmd['category'], cmd['icon'], cmd['color'], False, now))
        conn.commit()

def get_all_commands() -> list[dict]:
    """Returns all available commands with their pinned status."""
    init_db()
    with sqlite3.connect(COMMANDS_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM commands ORDER BY title ASC")
        return [dict(row) for row in cursor.fetchall()]

def toggle_pin_command(cmd_id: int, is_pinned: bool) -> bool:
    """Toggles the pinned status of a command."""
    with sqlite3.connect(COMMANDS_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE commands SET is_pinned = ? WHERE id = ?", (is_pinned, cmd_id))
        conn.commit()
        return cursor.rowcount > 0

def log_execution(cmd: str, status: str, latency: float):
    """Logs a command execution to history."""
    init_db()
    with sqlite3.connect(COMMANDS_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO command_history (cmd, status, latency, executed_at)
            VALUES (?, ?, ?, ?)
        ''', (cmd, status, latency, time.time()))
        conn.commit()

def get_command_history(limit: int = 50) -> list[dict]:
    """Fetches recent command execution history."""
    init_db()
    with sqlite3.connect(COMMANDS_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM command_history ORDER BY executed_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

# Ensure DB is initialized on import
init_db()
