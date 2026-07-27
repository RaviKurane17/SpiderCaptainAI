import os
import sqlite3
import time
import shutil
from pathlib import Path
from utils.config import MEMORY_DIR
from utils.logger import log

WORKSPACE_DB_PATH = MEMORY_DIR / "workspace.db"

def init_db():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(WORKSPACE_DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Projects Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                path TEXT UNIQUE,
                status TEXT DEFAULT 'active',
                created_at REAL,
                last_accessed REAL
            )
        ''')
        
        # Pinned Folders Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pinned_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                path TEXT UNIQUE
            )
        ''')
        conn.commit()

def get_workspace_state(root_dir: str):
    """Returns the current state of the workspace (Active Projects, Archived, Pinned)."""
    init_db()
    with sqlite3.connect(WORKSPACE_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM projects ORDER BY last_accessed DESC")
        projects = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM pinned_folders ORDER BY name ASC")
        pinned = [dict(row) for row in cursor.fetchall()]

    return {
        "projects": projects,
        "pinned": pinned,
        "root": root_dir
    }

def create_project(root_dir: str, name: str):
    """Creates a new project directory and registers it."""
    try:
        path = os.path.join(root_dir, name)
        os.makedirs(path, exist_ok=True)
        
        init_db()
        with sqlite3.connect(WORKSPACE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO projects (name, path, status, created_at, last_accessed)
                VALUES (?, ?, 'active', ?, ?)
            ''', (name, path, time.time(), time.time()))
            conn.commit()
        return {"success": True, "message": f"Project {name} created", "path": path}
    except Exception as e:
        return {"success": False, "error": str(e)}

def archive_project(name: str):
    """Marks a project as archived (could also zip it up)."""
    try:
        with sqlite3.connect(WORKSPACE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE projects SET status = 'archived' WHERE name = ?", (name,))
            conn.commit()
        return {"success": True, "message": f"Project {name} archived"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def pin_folder(name: str, path: str):
    try:
        with sqlite3.connect(WORKSPACE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO pinned_folders (name, path)
                VALUES (?, ?)
            ''', (name, path))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def unpin_folder(path: str):
    try:
        with sqlite3.connect(WORKSPACE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pinned_folders WHERE path = ?", (path,))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def record_access(path: str):
    """Update last accessed timestamp for a project if it matches."""
    try:
        with sqlite3.connect(WORKSPACE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE projects SET last_accessed = ? WHERE path = ?", (time.time(), path))
            conn.commit()
    except:
        pass

# Ensure DB is initialized
init_db()
