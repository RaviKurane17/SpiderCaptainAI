import sqlite3
import time
from utils.config import MEMORY_DIR
from utils.logger import log

CHAT_DB_PATH = MEMORY_DIR / "chat_history.db"

def init_chat_db():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(CHAT_DB_PATH) as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                is_pinned INTEGER DEFAULT 0,
                folder TEXT DEFAULT '',
                tags TEXT DEFAULT '',
                created_at REAL,
                updated_at REAL
            )
        ''')
        
        # Schema migration (if upgrading from V1)
        try:
            cursor.execute("ALTER TABLE chat_sessions ADD COLUMN folder TEXT DEFAULT ''")
            cursor.execute("ALTER TABLE chat_sessions ADD COLUMN tags TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass # Columns already exist
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                attachments TEXT DEFAULT '',
                tokens INTEGER DEFAULT 0,
                latency REAL DEFAULT 0,
                timestamp REAL,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            )
        ''')
        
        try:
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN attachments TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass # Column already exists
            
        conn.commit()

def get_chat_sessions():
    init_chat_db()
    try:
        with sqlite3.connect(CHAT_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chat_sessions ORDER BY is_pinned DESC, updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        log.error(f"[ChatManager] Failed to get sessions: {e}")
        return []

def create_chat_session(session_id: str, title: str = "New Chat"):
    init_chat_db()
    try:
        now = time.time()
        with sqlite3.connect(CHAT_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chat_sessions (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (session_id, title, now, now))
            conn.commit()
        return {"success": True, "session_id": session_id}
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_chat_session(session_id: str):
    try:
        with sqlite3.connect(CHAT_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def toggle_pin_session(session_id: str, is_pinned: bool):
    try:
        with sqlite3.connect(CHAT_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE chat_sessions SET is_pinned = ?, updated_at = ? WHERE id = ?", 
                           (1 if is_pinned else 0, time.time(), session_id))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_chat_messages(session_id: str):
    init_chat_db()
    try:
        with sqlite3.connect(CHAT_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chat_messages WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        log.error(f"[ChatManager] Failed to get messages: {e}")
        return []

def add_chat_message(session_id: str, role: str, content: str, tokens: int = 0, latency: float = 0.0, attachments: str = ''):
    try:
        now = time.time()
        with sqlite3.connect(CHAT_DB_PATH) as conn:
            cursor = conn.cursor()
            # Ensure session exists (auto-create if it doesn't)
            cursor.execute("SELECT id FROM chat_sessions WHERE id = ?", (session_id,))
            if not cursor.fetchone():
                title = content[:30] + "..." if role == "user" else "New Chat"
                cursor.execute("INSERT INTO chat_sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)", 
                               (session_id, title, now, now))
            
            cursor.execute('''
                INSERT INTO chat_messages (session_id, role, content, attachments, tokens, latency, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session_id, role, content, attachments, tokens, latency, now))
            
            # Update session timestamp & auto title if needed
            if role == "user":
                cursor.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now, session_id))
                
            conn.commit()
        return {"success": True}
    except Exception as e:
        log.error(f"[ChatManager] Failed to add message: {e}")
        return {"success": False, "error": str(e)}

init_chat_db()
