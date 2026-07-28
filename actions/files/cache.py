"""
SearchCache — Production-grade persistent SQLite file index.

Audit fixes applied:
- UPSERT (INSERT OR REPLACE) instead of INSERT OR IGNORE — moved/renamed files
  get updated instead of leaving stale ghost entries.
- Thread-local connection pool — no new connection per call.
- Stale path cleanup — remove_missing() validates paths exist.
- Compound indexes for fast filtered queries.
- Integrity check + auto-rebuild on corruption.
- Added size + modified_at columns for richer search (newest, largest).
- PRAGMA hardening: cache_size, mmap_size, temp_store.
- VACUUM / ANALYZE on demand.
"""

import os
import sqlite3
import logging
import threading
import time
from pathlib import Path
from typing import Optional

from actions.files.config import (
    CACHE_DIR, CACHE_DB_PATH, STALE_HOURS,
    SQLITE_TIMEOUT, SQLITE_CACHE_SIZE, SQLITE_MMAP_SIZE,
)

log = logging.getLogger("SearchCache")


class SearchCache:
    """
    Persistent file index backed by SQLite.

    Public API (preserved from v1):
        bulk_insert(items)
        search(query, drive, is_dir, extension, limit)
        clear(drive)
        mark_indexed(drive)
        get_total_count()
        is_stale(drive)
        get_indexed_drives()

    New in v2:
        bulk_upsert(items)        — update-or-insert
        remove_missing(paths)     — purge dead entries
        purge_drive(drive)        — wipe before re-index
        optimize()                — VACUUM + ANALYZE
        verify_integrity()        — corruption check + auto-repair
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or CACHE_DB_PATH
        self._lock = threading.Lock()
        # Thread-local storage for connection reuse — WHY: avoids opening
        # a new connection on every call, which is expensive for SQLite.
        self._local = threading.local()
        self._ensure_db()

    # ── Database Setup ─────────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """Return a thread-local connection, creating one if needed."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(
                str(self._db_path),
                timeout=SQLITE_TIMEOUT,
                check_same_thread=False,  # safe with our lock
            )
            conn.row_factory = sqlite3.Row
            # WHY: WAL allows concurrent reads during writes
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            # WHY: larger page cache = fewer disk reads during search
            conn.execute(f"PRAGMA cache_size = {SQLITE_CACHE_SIZE}")
            # WHY: memory-mapped I/O gives near-RAM speed for reads
            conn.execute(f"PRAGMA mmap_size = {SQLITE_MMAP_SIZE}")
            # WHY: temp tables in memory instead of disk
            conn.execute("PRAGMA temp_store = MEMORY")
            self._local.conn = conn
        return conn

    def _ensure_db(self):
        """Create tables and indexes if they don't exist. Migrate old schema."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS file_index (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                path        TEXT NOT NULL UNIQUE,
                name        TEXT NOT NULL,
                name_lower  TEXT NOT NULL,
                is_dir      INTEGER NOT NULL DEFAULT 0,
                extension   TEXT NOT NULL DEFAULT '',
                drive       TEXT NOT NULL DEFAULT '',
                size        INTEGER NOT NULL DEFAULT 0,
                modified_at REAL NOT NULL DEFAULT 0,
                indexed_at  REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS cache_meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            
            CREATE TABLE IF NOT EXISTS search_analytics (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp        REAL NOT NULL,
                query            TEXT NOT NULL,
                provider         TEXT NOT NULL,
                elapsed_ms       REAL NOT NULL,
                results_count    INTEGER NOT NULL,
                status           TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS user_behavior (
                query TEXT NOT NULL,
                path  TEXT NOT NULL,
                open_count INTEGER NOT NULL DEFAULT 1,
                last_opened REAL NOT NULL,
                PRIMARY KEY (query, path)
            );
        """)

        # WHY: migrate old v1 tables that lack size/modified_at columns.
        # ALTER TABLE ADD COLUMN is safe — it does nothing if column exists.
        for col, col_type, default in [
            ("size", "INTEGER", "0"),
            ("modified_at", "REAL", "0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE file_index ADD COLUMN {col} {col_type} NOT NULL DEFAULT {default}")
                conn.commit()
                log.info(f"Migrated: added column '{col}' to file_index.")
            except sqlite3.OperationalError:
                pass  # Column already exists — expected

        # Create indexes (safe to run if they already exist)
        conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_name_drive_dir
                ON file_index(name_lower, drive, is_dir);
            CREATE INDEX IF NOT EXISTS idx_extension
                ON file_index(extension);
            CREATE INDEX IF NOT EXISTS idx_drive
                ON file_index(drive);
            CREATE INDEX IF NOT EXISTS idx_modified
                ON file_index(modified_at);
            CREATE INDEX IF NOT EXISTS idx_size
                ON file_index(size DESC);
        """)
        conn.commit()

    # ── Cache Population ───────────────────────────────────────────────────

    def clear(self, drive: Optional[str] = None):
        """Clear the entire cache or just a specific drive."""
        with self._lock:
            conn = self._get_conn()
            if drive:
                conn.execute("DELETE FROM file_index WHERE drive = ?", (drive.upper(),))
            else:
                conn.execute("DELETE FROM file_index")
            conn.commit()

    def purge_drive(self, drive: str):
        """
        Wipe all entries for a drive before re-indexing.
        WHY: prevents stale ghost entries from accumulating across re-indexes.
        """
        with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM file_index WHERE drive = ?", (drive.upper(),))
            conn.commit()
            log.info(f"Purged drive {drive.upper()} from cache.")

    def bulk_upsert(self, items: list[tuple], batch_size: int = 5000):
        """
        Insert-or-update a batch of items into the cache.
        
        Each item is: (path_str, is_dir, name_lower, size, mtime)
        
        WHY UPSERT: INSERT OR IGNORE leaves stale data for moved/renamed files.
        INSERT OR REPLACE updates the row if the path already exists, keeping
        the cache consistent with the real filesystem.
        """
        now = time.time()
        rows = []
        for item in items:
            # Support both old 3-tuple and new 5-tuple format
            if len(item) == 5:
                path_str, is_dir, name_lower, size, mtime = item
            else:
                path_str, is_dir, name_lower = item[:3]
                size, mtime = 0, 0.0

            name = os.path.basename(path_str)
            ext = os.path.splitext(name)[1].lower()
            drive = path_str[0].upper() if len(path_str) >= 2 and path_str[1] == ":" else ""
            rows.append((path_str, name, name_lower, int(is_dir), ext, drive, size, mtime, now))

        with self._lock:
            conn = self._get_conn()
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                conn.executemany(
                    """INSERT OR REPLACE INTO file_index 
                       (path, name, name_lower, is_dir, extension, drive, size, modified_at, indexed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    batch
                )
            conn.commit()

    def bulk_insert(self, items: list[tuple], batch_size: int = 5000):
        """
        Backward-compatible alias for bulk_upsert.
        Accepts old 3-tuple format: (path, is_dir, name_lower)
        and new 5-tuple format: (path, is_dir, name_lower, size, mtime)
        """
        self.bulk_upsert(items, batch_size)

    def remove_missing(self, sample_size: int = 1000) -> int:
        """
        Validate a random sample of cached paths and remove those that
        no longer exist on disk.
        
        WHY: deleted/moved/renamed files leave ghost entries. This cleans them.
        Returns the number of entries removed.
        """
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, path FROM file_index ORDER BY RANDOM() LIMIT ?",
            (sample_size,)
        ).fetchall()

        dead_ids = []
        for row in rows:
            if not os.path.exists(row["path"]):
                dead_ids.append(row["id"])

        if dead_ids:
            with self._lock:
                placeholders = ",".join("?" * len(dead_ids))
                conn.execute(f"DELETE FROM file_index WHERE id IN ({placeholders})", dead_ids)
                conn.commit()
            log.info(f"Removed {len(dead_ids)} stale entries from cache.")

        return len(dead_ids)

    def mark_indexed(self, drive: Optional[str] = None):
        """Record the timestamp of the last successful index."""
        key = f"last_indexed_{drive}" if drive else "last_indexed_all"
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO cache_meta (key, value) VALUES (?, ?)",
                (key, str(time.time()))
            )
            conn.commit()

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
        Returns list of dicts: path, name, is_dir, extension, drive, size, modified_at.
        """
        query_lower = query.strip().lower()
        if not query_lower:
            return []

        conditions = []
        params = []

        import re
        query_tokens = [t for t in re.split(r'[_\-\.\s]+', query_lower) if t]
        if not query_tokens:
            return []
            
        fuzzy_pattern = f"%{'%'.join(query_tokens)}%"
        conditions.append("name_lower LIKE ?")
        params.append(fuzzy_pattern)

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

        # WHY this ORDER BY: exact name matches first, then shorter names
        # (shorter = more likely what the user wants), then alphabetical.
        sql = f"""
            SELECT path, name, is_dir, extension, drive, size, modified_at
            FROM file_index
            WHERE {where}
            ORDER BY 
                CASE WHEN name_lower = ? THEN 0 ELSE 1 END,
                length(name_lower),
                name_lower
            LIMIT ?
        """
        params.append(query_lower)  # for ORDER BY exact match
        params.append(limit)

        conn = self._get_conn()
        rows = conn.execute(sql, params).fetchall()

        return [
            {
                "path": row["path"],
                "name": row["name"],
                "is_dir": bool(row["is_dir"]),
                "extension": row["extension"],
                "drive": row["drive"],
                "size": row["size"],
                "modified_at": row["modified_at"],
            }
            for row in rows
        ]

    def get_total_count(self) -> int:
        """Return total number of indexed items."""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) as cnt FROM file_index").fetchone()
        return row["cnt"] if row else 0

    def is_stale(self, drive: Optional[str] = None) -> bool:
        """Check if the cache needs refreshing."""
        key = f"last_indexed_{drive}" if drive else "last_indexed_all"
        conn = self._get_conn()
        row = conn.execute(
            "SELECT value FROM cache_meta WHERE key = ?", (key,)
        ).fetchone()
        if not row:
            return True
        try:
            last_time = float(row["value"])
            hours_ago = (time.time() - last_time) / 3600
            return hours_ago > STALE_HOURS
        except (ValueError, TypeError):
            return True

    def get_indexed_drives(self) -> list[str]:
        """Return list of drive letters that have been indexed."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT DISTINCT drive FROM file_index WHERE drive != ''"
        ).fetchall()
        return [row["drive"] for row in rows]

    # ── Maintenance ────────────────────────────────────────────────────────

    def optimize(self):
        """
        Run VACUUM + ANALYZE to reclaim space and update query planner stats.
        WHY: after bulk deletes or large inserts, SQLite's internal stats
        become inaccurate, leading to slow queries.
        """
        conn = self._get_conn()
        conn.execute("ANALYZE")
        conn.execute("VACUUM")
        log.info("Cache optimized (ANALYZE + VACUUM).")

    def verify_integrity(self) -> bool:
        """
        Check SQLite integrity. If corrupt, delete and recreate.
        WHY: SQLite can corrupt on power loss or disk errors. Better to
        rebuild the index than crash on every search.
        """
        try:
            conn = self._get_conn()
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result and result[0] == "ok":
                return True

            log.error(f"Cache integrity check FAILED: {result}")
            self._rebuild_db()
            return False

        except sqlite3.DatabaseError as e:
            log.error(f"Cache database error: {e}")
            self._rebuild_db()
            return False

    def _rebuild_db(self):
        """Delete corrupt DB and recreate it."""
        log.warning("Rebuilding file index database...")
        # Close thread-local connection
        conn = getattr(self._local, "conn", None)
        if conn:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

        # Delete corrupt file
        try:
            if self._db_path.exists():
                self._db_path.unlink()
            # Also remove WAL and SHM files
            for suffix in ("-wal", "-shm"):
                sidecar = Path(str(self._db_path) + suffix)
                if sidecar.exists():
                    sidecar.unlink()
        except OSError as e:
            log.error(f"Failed to delete corrupt DB: {e}")

        # Recreate
        self._ensure_db()
        log.info("File index database rebuilt successfully.")

    # ── Analytics & User Behavior ──────────────────────────────────────────

    def insert_analytic(self, query: str, provider: str, elapsed_ms: float, results_count: int, status: str):
        """Log search performance."""
        try:
            conn = self._get_conn()
            with self._lock:
                conn.execute(
                    "INSERT INTO search_analytics (timestamp, query, provider, elapsed_ms, results_count, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (time.time(), query, provider, elapsed_ms, results_count, status)
                )
                conn.commit()
        except Exception as e:
            log.error(f"Error inserting analytic: {e}")

    def record_open(self, query: str, path: str):
        """Learn that a user opened a specific path for a given query."""
        try:
            conn = self._get_conn()
            with self._lock:
                conn.execute("""
                    INSERT INTO user_behavior (query, path, open_count, last_opened)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(query, path) DO UPDATE SET 
                        open_count = open_count + 1,
                        last_opened = excluded.last_opened
                """, (query.lower(), path, time.time()))
                conn.commit()
        except Exception as e:
            log.error(f"Error recording user behavior: {e}")

    def get_user_behavior_boost(self, query: str) -> dict:
        """Return a mapping of path -> open_count for the query."""
        try:
            conn = self._get_conn()
            cursor = conn.execute(
                "SELECT path, open_count FROM user_behavior WHERE query = ?",
                (query.lower(),)
            )
            return {row["path"]: row["open_count"] for row in cursor}
        except Exception as e:
            log.error(f"Error reading user behavior: {e}")
            return {}
