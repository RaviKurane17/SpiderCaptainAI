"""
SearchCache — Persistent SQLite-based file index cache.

Design decisions:
- Uses a local SQLite DB so that the first full scan is slow but every
  subsequent search returns results in <10ms.
- Stores path, name, lowercase name, is_directory, extension, and drive letter.
- Supports automatic staleness detection: if the cache is older than N hours,
  a background refresh is triggered.
- Thread-safe via SQLite's WAL mode and Python's threading lock.
"""

import os
import sqlite3
import logging
import threading
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger("SearchCache")

# Cache DB lives next to the memory DB
_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "memory"
_CACHE_DB = _CACHE_DIR / "file_index.db"

# Cache staleness threshold (hours)
_STALE_HOURS = 24


class SearchCache:
    """
    Persistent file index backed by SQLite.
    
    Usage:
        cache = SearchCache()
        cache.bulk_insert([(path, is_dir, name_lower), ...])
        results = cache.search("demo", drive="C", is_dir=None)
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or _CACHE_DB
        self._lock = threading.Lock()
        self._ensure_db()

    # ── Database Setup ─────────────────────────────────────────────────────

    def _ensure_db(self):
        """Create the cache table if it doesn't exist."""
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with self._get_conn() as conn:
            conn.executescript("""
                PRAGMA journal_mode = WAL;
                PRAGMA synchronous = NORMAL;
                
                CREATE TABLE IF NOT EXISTS file_index (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    path        TEXT NOT NULL UNIQUE,
                    name        TEXT NOT NULL,
                    name_lower  TEXT NOT NULL,
                    is_dir      INTEGER NOT NULL DEFAULT 0,
                    extension   TEXT NOT NULL DEFAULT '',
                    drive       TEXT NOT NULL DEFAULT '',
                    indexed_at  REAL NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_name_lower 
                    ON file_index(name_lower);
                CREATE INDEX IF NOT EXISTS idx_drive 
                    ON file_index(drive);
                CREATE INDEX IF NOT EXISTS idx_is_dir 
                    ON file_index(is_dir);
                CREATE INDEX IF NOT EXISTS idx_extension
                    ON file_index(extension);
                    
                CREATE TABLE IF NOT EXISTS cache_meta (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                );
            """)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Cache Population ───────────────────────────────────────────────────

    def clear(self, drive: Optional[str] = None):
        """Clear the entire cache or just a specific drive."""
        with self._lock:
            with self._get_conn() as conn:
                if drive:
                    conn.execute(
                        "DELETE FROM file_index WHERE drive = ?",
                        (drive.upper(),)
                    )
                else:
                    conn.execute("DELETE FROM file_index")

    def bulk_insert(self, items: list[tuple[str, bool, str]], batch_size: int = 5000):
        """
        Insert a batch of (path, is_dir, name_lower) tuples into the cache.
        Uses INSERT OR IGNORE to handle duplicates gracefully.
        """
        now = time.time()
        rows = []
        for path_str, is_dir, name_lower in items:
            name = os.path.basename(path_str)
            ext = os.path.splitext(name)[1].lower()
            drive = path_str[0].upper() if len(path_str) >= 2 and path_str[1] == ":" else ""
            rows.append((path_str, name, name_lower, int(is_dir), ext, drive, now))

        with self._lock:
            with self._get_conn() as conn:
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    conn.executemany(
                        """INSERT OR IGNORE INTO file_index 
                           (path, name, name_lower, is_dir, extension, drive, indexed_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        batch
                    )

    def mark_indexed(self, drive: Optional[str] = None):
        """Record the timestamp of the last successful index."""
        key = f"last_indexed_{drive}" if drive else "last_indexed_all"
        with self._lock:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache_meta (key, value) VALUES (?, ?)",
                    (key, str(time.time()))
                )

    # ── Cache Queries ──────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        drive: Optional[str] = None,
        is_dir: Optional[bool] = None,
        extension: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Search the cache for files/folders matching the query.
        Returns list of dicts with keys: path, name, is_dir, extension, drive.
        
        Search strategy:
          1. Exact match on name_lower
          2. LIKE match (contains) on name_lower
        """
        query_lower = query.strip().lower()
        if not query_lower:
            return []

        conditions = []
        params = []

        # Name matching — exact first, then contains
        conditions.append("name_lower LIKE ?")
        params.append(f"%{query_lower}%")

        if drive:
            conditions.append("drive = ?")
            params.append(drive.upper())

        if is_dir is not None:
            conditions.append("is_dir = ?")
            params.append(int(is_dir))

        if extension:
            ext = extension if extension.startswith(".") else f".{extension}"
            conditions.append("extension = ?")
            params.append(ext.lower())

        where = " AND ".join(conditions)
        params.append(limit)

        # Sort: exact matches first, then by name length (shorter = more relevant)
        sql = f"""
            SELECT path, name, is_dir, extension, drive
            FROM file_index
            WHERE {where}
            ORDER BY 
                CASE WHEN name_lower = ? THEN 0 ELSE 1 END,
                length(name_lower),
                name_lower
            LIMIT ?
        """
        # Insert the exact-match parameter for ORDER BY
        params.insert(-1, query_lower)

        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            {
                "path": row["path"],
                "name": row["name"],
                "is_dir": bool(row["is_dir"]),
                "extension": row["extension"],
                "drive": row["drive"],
            }
            for row in rows
        ]

    def get_total_count(self) -> int:
        """Return total number of indexed items."""
        with self._get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM file_index").fetchone()
            return row["cnt"] if row else 0

    def is_stale(self, drive: Optional[str] = None) -> bool:
        """Check if the cache needs refreshing."""
        key = f"last_indexed_{drive}" if drive else "last_indexed_all"
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT value FROM cache_meta WHERE key = ?", (key,)
            ).fetchone()
            if not row:
                return True
            try:
                last_time = float(row["value"])
                hours_ago = (time.time() - last_time) / 3600
                return hours_ago > _STALE_HOURS
            except (ValueError, TypeError):
                return True

    def get_indexed_drives(self) -> list[str]:
        """Return list of drive letters that have been indexed."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT drive FROM file_index WHERE drive != ''"
            ).fetchall()
            return [row["drive"] for row in rows]
