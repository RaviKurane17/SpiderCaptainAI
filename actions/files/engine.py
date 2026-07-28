"""
FileSearchEngine — The core search orchestrator.

Design decisions:
- Searches the persistent cache first (millisecond results).
- If cache is empty/stale, triggers a background index crawl automatically.
- Uses difflib.SequenceMatcher for fuzzy matching with configurable threshold.
- Exact matches are always prioritized before fuzzy matches.
- Runs heavy crawling on a background thread — never blocks the AI.
- 5-second timeout: if live search exceeds 5s, returns partial results
  and continues indexing in the background for future queries.
- Progress callback lets the AI relay "Searching C drive..." to the user.
- Thread-safe and cancellable.
"""

import os
import re
import time
import logging
import threading
import difflib
from pathlib import Path
from typing import Optional, Callable

from actions.files.indexer import FileIndexer
from actions.files.cache import SearchCache
from actions.files.explorer import ExplorerManager

log = logging.getLogger("FileSearchEngine")

# ── Singleton engine instance ──────────────────────────────────────────────
_engine_instance: Optional["FileSearchEngine"] = None
_engine_lock = threading.Lock()


def get_engine() -> "FileSearchEngine":
    """Return the global FileSearchEngine singleton."""
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = FileSearchEngine()
    return _engine_instance


class FileSearchEngine:
    """
    High-level search engine that combines the indexer, cache, and explorer.

    Usage:
        engine = get_engine()
        result = engine.search("demo", drive="C")
        # result is a dict with keys: status, results, message, count
    """

    def __init__(self):
        self._cache = SearchCache()
        self._indexing = False
        self._index_lock = threading.Lock()
        self._cancel_event = threading.Event()
        self._progress_messages: list[str] = []

    # ── Public Search API ──────────────────────────────────────────────────

    def search(
        self,
        query: str,
        drive: Optional[str] = None,
        search_type: Optional[str] = None,  # "file", "folder", or None for both
        extension: Optional[str] = None,
        on_progress: Optional[Callable[[str], None]] = None,
        max_results: int = 30,
        fuzzy_threshold: float = 0.55,
    ) -> dict:
        """
        Search for files/folders matching query.
        
        Args:
            query: Search term (name, partial name, etc.)
            drive: Optional drive letter to search (e.g. "C", "D")
            search_type: "file", "folder", or None for both
            extension: Optional file extension filter (e.g. ".pdf")
            on_progress: Callback for progress messages
            max_results: Maximum results to return
            fuzzy_threshold: Minimum similarity score for fuzzy matches (0-1)
            
        Returns:
            dict with keys:
                status: "found" | "not_found" | "multiple" | "indexing"
                results: list of result dicts
                message: User-friendly message
                count: Number of results
        """
        query = query.strip()
        if not query:
            return {
                "status": "not_found",
                "results": [],
                "message": "No search query provided.",
                "count": 0,
            }

        progress = on_progress or (lambda msg: None)
        is_dir = None
        if search_type == "folder":
            is_dir = True
        elif search_type == "file":
            is_dir = False

        # ── Step 1: Try cached search first (fast path) ───────────────────
        cache_count = self._cache.get_total_count()
        if cache_count > 0:
            progress("Searching index...")
            cached_results = self._cache.search(
                query=query,
                drive=drive,
                is_dir=is_dir,
                extension=extension,
                limit=max_results * 2,  # grab extra for fuzzy re-ranking
            )

            if cached_results:
                # Re-rank with fuzzy scoring
                ranked = self._rank_results(query, cached_results, fuzzy_threshold)
                final = ranked[:max_results]
                return self._format_response(query, final)

        # ── Step 2: Cache miss or empty — do a live scan ──────────────────
        progress("Index empty. Starting live search...")

        # Determine roots to scan
        roots = None
        if drive:
            drive_letter = drive.strip().upper().rstrip(":\\")
            roots = [f"{drive_letter}:\\"]

        # Live scan with 5-second timeout
        results = self._live_search(
            query=query,
            roots=roots,
            is_dir=is_dir,
            extension=extension,
            on_progress=progress,
            timeout_sec=5.0,
            max_results=max_results,
        )

        # Trigger background full index for future searches
        if self._cache.is_stale(drive):
            self._start_background_index(roots, progress)

        if results:
            ranked = self._rank_results(query, results, fuzzy_threshold)
            final = ranked[:max_results]
            return self._format_response(query, final)

        return {
            "status": "not_found",
            "results": [],
            "message": f"No files or folders matching '{query}' were found.",
            "count": 0,
        }

    def open_result(self, path_str: str) -> str:
        """Open a search result using the ExplorerManager."""
        return ExplorerManager.open(path_str)

    def cancel_search(self):
        """Cancel any ongoing live search or indexing."""
        self._cancel_event.set()
        log.info("Search cancelled by user.")

    def rebuild_index(
        self,
        drives: Optional[list[str]] = None,
        on_progress: Optional[Callable[[str], None]] = None,
    ):
        """Force a full re-index of specified drives (or all drives)."""
        progress = on_progress or (lambda msg: None)
        roots = None
        if drives:
            roots = [f"{d.strip().upper().rstrip(':')}:\\" for d in drives]
        self._start_background_index(roots, progress, force=True)

    def get_index_stats(self) -> dict:
        """Return cache statistics."""
        return {
            "total_indexed": self._cache.get_total_count(),
            "indexed_drives": self._cache.get_indexed_drives(),
            "is_indexing": self._indexing,
        }

    # ── Live Scan (with timeout) ───────────────────────────────────────────

    def _live_search(
        self,
        query: str,
        roots: Optional[list[str]],
        is_dir: Optional[bool],
        extension: Optional[str],
        on_progress: Callable[[str], None],
        timeout_sec: float,
        max_results: int,
    ) -> list[dict]:
        """
        Perform a real-time filesystem scan with a timeout.
        Returns results found within the timeout window.
        Items discovered are also inserted into the cache for future use.
        """
        self._cancel_event.clear()
        query_lower = query.strip().lower()
        results: list[dict] = []
        buffer: list[tuple[str, bool, str]] = []
        start_time = time.time()

        indexer = FileIndexer(
            cancel_event=self._cancel_event,
            on_progress=on_progress,
            skip_system=True,
        )

        for path_str, item_is_dir, name_lower in indexer.crawl(roots=roots):
            elapsed = time.time() - start_time

            # Buffer items for cache insertion
            buffer.append((path_str, item_is_dir, name_lower))

            # Flush buffer every 5000 items
            if len(buffer) >= 5000:
                self._cache.bulk_insert(buffer)
                buffer.clear()

            # Check if this item matches
            if self._matches_query(query_lower, name_lower, path_str, is_dir, item_is_dir, extension):
                name = os.path.basename(path_str)
                ext = os.path.splitext(name)[1].lower()
                drive = path_str[0].upper() if len(path_str) >= 2 and path_str[1] == ":" else ""
                results.append({
                    "path": path_str,
                    "name": name,
                    "is_dir": item_is_dir,
                    "extension": ext,
                    "drive": drive,
                })

            # Timeout — return what we have, let background finish
            if elapsed > timeout_sec and len(results) > 0:
                on_progress(f"Found {len(results)} results in {elapsed:.1f}s. Continuing indexing in background...")
                break

            # Early exit if we have plenty of results
            if len(results) >= max_results * 2:
                break

        # Flush remaining buffer
        if buffer:
            self._cache.bulk_insert(buffer)

        return results

    def _matches_query(
        self,
        query_lower: str,
        name_lower: str,
        path_str: str,
        filter_is_dir: Optional[bool],
        item_is_dir: bool,
        extension: Optional[str],
    ) -> bool:
        """Check if an item matches the search criteria."""
        # Type filter
        if filter_is_dir is not None and item_is_dir != filter_is_dir:
            return False

        # Extension filter
        if extension:
            ext = extension if extension.startswith(".") else f".{extension}"
            if not name_lower.endswith(ext.lower()):
                return False

        # Name matching — contains check
        if query_lower in name_lower:
            return True

        # Fuzzy match for close names (e.g. "dmo" matching "demo")
        ratio = difflib.SequenceMatcher(None, query_lower, name_lower).ratio()
        if ratio >= 0.6:
            return True

        return False

    # ── Result Ranking ─────────────────────────────────────────────────────

    def _rank_results(
        self, query: str, results: list[dict], threshold: float
    ) -> list[dict]:
        """
        Re-rank results by relevance:
          1. Exact name match (case-insensitive)
          2. Name starts with query
          3. Name contains query
          4. Fuzzy similarity score
        Results below the threshold are dropped.
        """
        query_lower = query.lower()
        scored: list[tuple[float, dict]] = []

        for r in results:
            name_lower = r["name"].lower()
            name_no_ext = os.path.splitext(name_lower)[0]

            # Score calculation (higher = better)
            if name_lower == query_lower or name_no_ext == query_lower:
                score = 1.0  # Exact match
            elif name_lower.startswith(query_lower) or name_no_ext.startswith(query_lower):
                score = 0.9  # Starts with
            elif query_lower in name_lower:
                score = 0.8  # Contains
            else:
                # Fuzzy
                score = difflib.SequenceMatcher(None, query_lower, name_no_ext).ratio()

            if score >= threshold:
                scored.append((score, r))

        # Sort by score descending, then by name length (shorter = more relevant)
        scored.sort(key=lambda x: (-x[0], len(x[1]["name"])))
        return [r for _, r in scored]

    # ── Response Formatting ────────────────────────────────────────────────

    def _format_response(self, query: str, results: list[dict]) -> dict:
        """Format results into a structured response dict."""
        count = len(results)

        if count == 0:
            return {
                "status": "not_found",
                "results": [],
                "message": f"No files or folders matching '{query}' were found.",
                "count": 0,
            }

        if count == 1:
            r = results[0]
            kind = "folder" if r["is_dir"] else "file"
            return {
                "status": "found",
                "results": results,
                "message": f"Found 1 {kind}: {r['name']} at {r['path']}",
                "count": 1,
            }

        # Multiple results
        # Group by type for a nice message
        folders = [r for r in results if r["is_dir"]]
        files = [r for r in results if not r["is_dir"]]
        
        parts = []
        if folders:
            parts.append(f"{len(folders)} folder(s)")
        if files:
            parts.append(f"{len(files)} file(s)")
        summary = " and ".join(parts)

        lines = [f"I found {summary} matching '{query}'. Which one would you like to open?\n"]
        for i, r in enumerate(results[:15], 1):
            icon = "📁" if r["is_dir"] else "📄"
            lines.append(f"  {i}. {icon} {r['name']}  —  {r['path']}")

        if count > 15:
            lines.append(f"\n  ... and {count - 15} more results.")

        return {
            "status": "multiple",
            "results": results,
            "message": "\n".join(lines),
            "count": count,
        }

    # ── Background Indexing ────────────────────────────────────────────────

    def _start_background_index(
        self,
        roots: Optional[list[str]],
        on_progress: Callable[[str], None],
        force: bool = False,
    ):
        """Start a background thread to index drives into the cache."""
        with self._index_lock:
            if self._indexing and not force:
                log.info("Background indexing already in progress.")
                return
            self._indexing = True

        def _index_worker():
            try:
                log.info(f"Background indexing started. Roots: {roots or 'all drives'}")
                on_progress("Background indexing started...")

                cancel = threading.Event()
                indexer = FileIndexer(
                    cancel_event=cancel,
                    on_progress=lambda msg: log.debug(msg),
                    skip_system=True,
                )

                buffer: list[tuple[str, bool, str]] = []
                total = 0

                for item in indexer.crawl(roots=roots):
                    buffer.append(item)
                    if len(buffer) >= 10000:
                        self._cache.bulk_insert(buffer)
                        total += len(buffer)
                        buffer.clear()
                        log.debug(f"Indexed {total} items so far...")

                if buffer:
                    self._cache.bulk_insert(buffer)
                    total += len(buffer)

                # Mark drives as indexed
                if roots:
                    for root in roots:
                        drive = root[0].upper() if len(root) >= 2 else ""
                        if drive:
                            self._cache.mark_indexed(drive)
                else:
                    self._cache.mark_indexed()

                log.info(f"Background indexing complete. {total} items indexed.")

            except Exception as e:
                log.error(f"Background indexing error: {e}")
            finally:
                with self._index_lock:
                    self._indexing = False

        thread = threading.Thread(target=_index_worker, daemon=True, name="FileIndexWorker")
        thread.start()
