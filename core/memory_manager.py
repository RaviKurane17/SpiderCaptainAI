import sqlite3
import time
import json
import asyncio
from pathlib import Path
from utils.config import MEMORY_DIR
from utils.logger import log

MEMORY_DB_PATH = MEMORY_DIR / "memory.db"

# We use thread-local storage for connection pooling in a multi-threaded asyncio app
import threading
_local = threading.local()

def get_db_conn():
    if not hasattr(_local, "conn"):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(MEMORY_DB_PATH, timeout=5.0)
        conn.row_factory = sqlite3.Row
        
        # High performance PRAGMAs for minimal CPU and I/O locking
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA cache_size=-64000") # 64MB cache
        
        _local.conn = conn
    return _local.conn

def init_memory_db():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Core memories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            layer TEXT DEFAULT 'Long-Term',
            title TEXT,
            summary TEXT,
            category TEXT,
            tags TEXT DEFAULT '',
            importance_score REAL DEFAULT 0.5,
            created_at REAL,
            updated_at REAL
        )
    ''')
    
    # Schema Migrations (Phase 6b: Personal Memory)
    try:
        cursor.execute("ALTER TABLE memories ADD COLUMN priority TEXT DEFAULT 'Normal'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE memories ADD COLUMN privacy TEXT DEFAULT 'Normal'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE memories ADD COLUMN source TEXT DEFAULT 'Manual'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE memories ADD COLUMN expires_at REAL")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE memories ADD COLUMN pinned INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    # Optimize search and filtering
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_layer ON memories(layer)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_updated ON memories(updated_at DESC)")
    
    # Embeddings table (separated to keep `memories` table scans extremely fast)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS embeddings (
            memory_id TEXT PRIMARY KEY,
            vector BLOB,
            FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()

def add_memory(memory_id: str, layer: str, title: str, summary: str, category: str, tags: list = None, importance_score: float = 0.5, privacy: str = 'Normal', source: str = 'Manual', expires_at: float = None):
    conn = get_db_conn()
    cursor = conn.cursor()
    now = time.time()
    
    tags_str = ",".join(tags) if tags else ""
    
    cursor.execute('''
        INSERT INTO memories (id, layer, title, summary, category, tags, importance_score, privacy, source, expires_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET 
            summary=excluded.summary,
            updated_at=excluded.updated_at,
            importance_score=excluded.importance_score,
            tags=excluded.tags,
            privacy=excluded.privacy,
            source=excluded.source,
            expires_at=excluded.expires_at
    ''', (memory_id, layer, title, summary, category, tags_str, importance_score, privacy, source, expires_at, now, now))
    
    conn.commit()
    
    # TODO: Kick off async embedding generation
    return {"success": True, "id": memory_id}

def update_memory(memory_id: str, title: str, summary: str, category: str, tags: list = None, priority: str = 'Normal', privacy: str = 'Normal'):
    conn = get_db_conn()
    cursor = conn.cursor()
    now = time.time()
    
    tags_str = ",".join(tags) if tags else ""
    
    cursor.execute('''
        UPDATE memories 
        SET title = ?, summary = ?, category = ?, tags = ?, priority = ?, privacy = ?, updated_at = ?
        WHERE id = ?
    ''', (title, summary, category, tags_str, priority, privacy, now, memory_id))
    
    conn.commit()
    
    # TODO: Kick off async embedding generation
    return {"success": True, "id": memory_id}

def search_memories(query: str = "", category: str = "", privacy: str = "ALL", limit: int = 50, offset: int = 0):
    """Extremely fast paginated search. In a real production system, use FTS5."""
    conn = get_db_conn()
    cursor = conn.cursor()
    
    base_sql = "SELECT * FROM memories WHERE 1=1"
    params = []
    
    if query:
        base_sql += " AND (title LIKE ? OR summary LIKE ? OR tags LIKE ?)"
        lk = f"%{query}%"
        params.extend([lk, lk, lk])
        
    if category and category.upper() != "ALL":
        base_sql += " AND category COLLATE NOCASE = ?"
        params.append(category)
        
    if privacy and privacy.upper() != "ALL":
        base_sql += " AND privacy COLLATE NOCASE = ?"
        params.append(privacy)
        
    base_sql += " ORDER BY pinned DESC, updated_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(base_sql, params)
    rows = cursor.fetchall()
    
    return [dict(r) for r in rows]

def get_memory_stats():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # 1. Total
    cursor.execute("SELECT COUNT(*) as count FROM memories")
    total = cursor.fetchone()['count']
    
    # 2. Source break down
    cursor.execute("SELECT COUNT(*) as count FROM memories WHERE source = 'Manual'")
    manual_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM memories WHERE source = 'AI Suggested'")
    ai_count = cursor.fetchone()['count']
    
    # 3. Expiry breakdown
    cursor.execute("SELECT COUNT(*) as count FROM memories WHERE expires_at IS NULL")
    permanent_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM memories WHERE expires_at IS NOT NULL")
    temp_count = cursor.fetchone()['count']
    
    # 4. Layer / Category breakdown
    cursor.execute("SELECT COUNT(*) as count FROM memories WHERE layer = 'Project'")
    project_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM memories WHERE layer = 'Session'")
    session_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM memories WHERE category = 'Personal'")
    personal_count = cursor.fetchone()['count']
    
    # 5. Timestamps
    cursor.execute("SELECT MAX(updated_at) as last_updated FROM memories")
    last_up_row = cursor.fetchone()
    last_updated = last_up_row['last_updated'] if last_up_row and last_up_row['last_updated'] else 0
    
    now = time.time()
    cursor.execute("SELECT COUNT(*) as count FROM memories WHERE updated_at >= ?", (now - 86400,)) # Last 24h
    recent_count = cursor.fetchone()['count']
    
    # 6. Pinned
    try:
        cursor.execute("SELECT COUNT(*) as count FROM memories WHERE pinned = 1")
        pinned_count = cursor.fetchone()['count']
    except sqlite3.OperationalError:
        pinned_count = 0
    
    # Categories
    cursor.execute("SELECT category, COUNT(*) as count FROM memories GROUP BY category")
    categories = {row['category']: row['count'] for row in cursor.fetchall()}
    
    # Get DB size
    db_size = 0
    if MEMORY_DB_PATH.exists():
        db_size = MEMORY_DB_PATH.stat().st_size
        
    return {
        "total_memories": total,
        "manual_memories": manual_count,
        "ai_suggested_memories": ai_count,
        "permanent_memories": permanent_count,
        "temporary_memories": temp_count,
        "project_memories": project_count,
        "conversation_memories": session_count,
        "personal_memories": personal_count,
        "recent_memories": recent_count,
        "pinned_memories": pinned_count,
        "favourite_memories": 0, # Placeholder for favourites
        "db_size_bytes": db_size,
        "categories": categories,
        "last_updated": last_updated,
        "last_backup": "Never",
        "search_statistics": "Ready",
        "health": "Optimal"
    }

def delete_memory(memory_id: str):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    cursor.execute("DELETE FROM embeddings WHERE memory_id = ?", (memory_id,))
    conn.commit()
    return {"success": True}

def toggle_pin_memory(memory_id: str):
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT pinned FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        if row is None:
            return {"success": False, "error": "Memory not found"}
        
        current_pin = row['pinned'] if 'pinned' in row.keys() else 0
        new_pin = 1 if not current_pin else 0
        
        cursor.execute("UPDATE memories SET pinned = ? WHERE id = ?", (new_pin, memory_id))
        conn.commit()
        return {"success": True, "pinned": new_pin}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Initialize on import
init_memory_db()
