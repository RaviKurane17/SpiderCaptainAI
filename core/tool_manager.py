import sqlite3
import time
import json
import asyncio
from pathlib import Path
from utils.config import MEMORY_DIR
from utils.logger import log

TOOLS_DB_PATH = MEMORY_DIR / "tools.db"

import threading
_local = threading.local()

def get_db_conn():
    if not hasattr(_local, "conn"):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(TOOLS_DB_PATH, timeout=5.0)
        conn.row_factory = sqlite3.Row
        
        # High performance PRAGMAs for minimal CPU and I/O locking
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        
        _local.conn = conn
    return _local.conn

def init_tools_db():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tools (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            version TEXT DEFAULT '1.0.0',
            category TEXT,
            status TEXT DEFAULT 'Enabled', -- Enabled, Disabled, Running, Crashed
            health TEXT DEFAULT 'Operational',
            ai_callable TEXT DEFAULT 'Ask Every Time', -- Allowed, Blocked, Ask Every Time
            security_level TEXT DEFAULT 'Normal User', -- Normal User, Developer, Administrator, Boss Mode
            dependencies TEXT DEFAULT '',
            execution_count INTEGER DEFAULT 0,
            avg_runtime_ms INTEGER DEFAULT 0,
            last_used REAL DEFAULT 0,
            is_pinned INTEGER DEFAULT 0,
            is_favourite INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tool_execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id TEXT,
            timestamp REAL,
            user_request TEXT,
            execution_time_ms INTEGER,
            status TEXT,
            errors TEXT,
            logs TEXT,
            FOREIGN KEY(tool_id) REFERENCES tools(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tools_category ON tools(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tools_status ON tools(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tools_last_used ON tools(last_used DESC)")
    
    conn.commit()
    seed_core_tools(conn)

def seed_core_tools(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as c FROM tools")
    if cursor.fetchone()['c'] > 0:
        return # Already seeded
        
    core_tools = [
        # System Tools
        ("system_explorer", "Explorer", "Windows File Explorer integration", "System", "Normal User"),
        ("system_cmd", "Command Prompt", "Execute native CMD commands", "System", "Developer"),
        ("system_powershell", "PowerShell", "Execute PowerShell scripts", "System", "Administrator"),
        ("system_taskmgr", "Task Manager", "Manage system processes", "System", "Administrator"),
        ("system_regedit", "Registry Editor", "Modify Windows Registry", "System", "Boss Mode"),
        ("system_services", "Services", "Manage Windows Services", "System", "Administrator"),
        ("system_settings", "Settings", "Windows Settings Control", "System", "Normal User"),
        ("system_recycle", "Recycle Bin", "Manage deleted files", "System", "Normal User"),
        ("system_screenshot", "Screenshot", "Capture screen regions", "System", "Normal User"),
        
        # File Tools
        ("file_manager", "Folder Manager", "Advanced directory operations", "Files", "Normal User"),
        ("file_zip", "ZIP Extractor", "Compress and extract archives", "Files", "Normal User"),
        ("file_search", "Search Files", "Fast indexed file search", "Files", "Normal User"),
        ("file_duplicate", "Duplicate Finder", "Find and clean duplicate files", "Files", "Normal User"),
        
        # Browser Tools
        ("browser_chrome", "Google Chrome", "Chrome automation integration", "Browser", "Normal User"),
        ("browser_edge", "Microsoft Edge", "Edge automation integration", "Browser", "Normal User"),
        ("browser_search", "Search Web", "AI semantic web search", "Browser", "Normal User"),
        
        # Development Tools
        ("dev_vscode", "VS Code", "Code editor automation", "Development", "Developer"),
        ("dev_git", "Git", "Version control operations", "Development", "Developer"),
        ("dev_python", "Python", "Execute Python scripts", "Development", "Developer"),
        ("dev_java", "Java", "Java compilation and execution", "Development", "Developer"),
        ("dev_maven", "Maven", "Java dependency management", "Development", "Developer"),
        ("dev_docker", "Docker", "Container management", "Development", "Administrator"),
        ("dev_postman", "Postman", "API testing automation", "Development", "Developer"),
        
        # Automation Tools
        ("auto_scheduler", "Task Scheduler", "Schedule recurring tasks", "Automation", "Administrator"),
        ("auto_workflow", "Workflow Engine", "Multi-step AI workflows", "Automation", "Developer"),
        ("auto_reminder", "Reminder Engine", "Contextual user reminders", "Automation", "Normal User")
    ]
    
    now = time.time()
    for t in core_tools:
        cursor.execute('''
            INSERT INTO tools (id, name, description, category, security_level, last_used)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (t[0], t[1], t[2], t[3], t[4], now))
        
    conn.commit()

def get_tools_stats():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM tools")
    total = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM tools WHERE status = 'Enabled'")
    enabled = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM tools WHERE status = 'Running'")
    running = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM tools WHERE health != 'Operational'")
    errors = cursor.fetchone()['count']
    
    cursor.execute("SELECT name FROM tools ORDER BY last_used DESC LIMIT 1")
    last_exec_row = cursor.fetchone()
    last_executed = last_exec_row['name'] if last_exec_row else "None"
    
    return {
        "total_tools": total,
        "enabled_tools": enabled,
        "disabled_tools": total - enabled - running,
        "running_tools": running,
        "available_updates": 0,
        "tool_health": "Optimal" if errors == 0 else "Warning",
        "last_executed": last_executed,
        "permission_warnings": 0,
        "errors": errors,
        "execution_statistics": "Ready"
    }

def search_tools(query: str = "", category: str = "ALL", status: str = "ALL", limit: int = 50, offset: int = 0):
    conn = get_db_conn()
    cursor = conn.cursor()
    
    base_sql = "SELECT * FROM tools WHERE 1=1"
    params = []
    
    if query:
        base_sql += " AND (name LIKE ? OR description LIKE ?)"
        lk = f"%{query}%"
        params.extend([lk, lk])
        
    if category and category.upper() != "ALL":
        base_sql += " AND category = ?"
        params.append(category)
        
    if status and status.upper() != "ALL":
        base_sql += " AND status = ?"
        params.append(status)
        
    base_sql += " ORDER BY is_pinned DESC, name ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(base_sql, params)
    return [dict(r) for r in cursor.fetchall()]

def update_tool_permission(tool_id: str, new_permission: str):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE tools SET ai_callable = ? WHERE id = ?", (new_permission, tool_id))
    conn.commit()
    return {"success": True}

def toggle_tool_status(tool_id: str, enable: bool):
    conn = get_db_conn()
    cursor = conn.cursor()
    new_status = "Enabled" if enable else "Disabled"
    cursor.execute("UPDATE tools SET status = ? WHERE id = ?", (new_status, tool_id))
    conn.commit()
    return {"success": True, "status": new_status}

def toggle_pin_tool(tool_id: str):
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT is_pinned FROM tools WHERE id = ?", (tool_id,))
        row = cursor.fetchone()
        if row is None:
            return {"success": False, "error": "Tool not found"}
        
        current_pin = row['is_pinned'] if 'is_pinned' in row.keys() else 0
        new_pin = 1 if not current_pin else 0
        
        cursor.execute("UPDATE tools SET is_pinned = ? WHERE id = ?", (new_pin, tool_id))
        conn.commit()
        return {"success": True, "pinned": new_pin}
    except Exception as e:
        return {"success": False, "error": str(e)}

def run_health_check(tool_id: str):
    import random
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM tools WHERE id = ?", (tool_id,))
        if cursor.fetchone() is None:
            return {"success": False, "error": "Tool not found"}
            
        # Simulate health check logic
        is_healthy = random.random() > 0.1 # 90% chance of success
        health_status = "Operational" if is_healthy else "Warning"
        
        cursor.execute("UPDATE tools SET health = ? WHERE id = ?", (health_status, tool_id))
        conn.commit()
        return {"success": True, "health": health_status}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Initialize on import
init_tools_db()
