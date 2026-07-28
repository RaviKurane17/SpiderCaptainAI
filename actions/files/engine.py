"""
FileSearchEngine — Production-grade search orchestrator.

Audit fixes applied:
- RapidFuzz for fuzzy matching (falls back to difflib if unavailable).
- 10-tier ranking: exact → starts-with → whole-word → contains → fuzzy →
  path relevance → user folders first.
- Single background worker guarantee — thread object tracked, no duplicates.
- Pause/Resume/Cancel for background indexing.
- Result deduplication by path.
- High-confidence auto-open (score ≥ 0.95 and single result).
- User folder priority (Desktop/Documents/Downloads ranked above system).
- Stale path cleanup during search — dead entries are auto-purged.
- Incremental re-index — only purge the specific drive being re-indexed.
- Structured logging with search timing.
- Provider-based architecture: Everything SDK → Windows Search → SQLite → Live
- Filesystem monitoring (Watchdog + periodic fallback).
"""

import os
import re
import time
import logging
import threading
from pathlib import Path
from typing import Optional, Callable
from collections import deque

# WHY: rapidfuzz is 10-100x faster than difflib and handles
# token permutations (e.g. "Spring Boot" ↔ "spring_boot") natively.
try:
    from rapidfuzz import fuzz as rf_fuzz
    _HAS_RAPIDFUZZ = True
except ImportError:
    import difflib
    _HAS_RAPIDFUZZ = False

from actions.files.indexer import FileIndexer
from actions.files.cache import SearchCache
from actions.files.explorer import ExplorerManager
from actions.files.monitor import FileMonitor
from actions.files.providers import (
    EverythingProvider, WindowsSearchProvider, SQLiteProvider, LiveScannerProvider
)
from actions.files.config import (
    SEARCH_TIMEOUT_SEC, DEFAULT_MAX_RESULTS, FUZZY_THRESHOLD,
    HIGH_CONFIDENCE, CRAWL_BATCH_SIZE, INDEX_BATCH_SIZE,
    RANK_EXACT, RANK_EXACT_NO_EXT, RANK_STARTS_WITH,
    RANK_WHOLE_WORD, RANK_CONTAINS, USER_FOLDER_BOOST, USER_FOLDERS,
)

log = logging.getLogger("FileSearchEngine")

# ── Singleton ──────────────────────────────────────────────────────────────
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


# ── Fuzzy helpers ──────────────────────────────────────────────────────────

def _normalize_for_fuzzy(text: str) -> str:
    """
    Normalize text for exact comparison of variants.
    Strips spaces, underscores, hyphens, dots.
    e.g., "Iris AI", "Iris_AI", "iris.ai" -> "irisai"
    """
    return re.sub(r'[_\-\.\s]+', '', text.lower()).strip()


def _fuzzy_score(query: str, candidate: str) -> float:
    """Return a 0–1 similarity score between query and candidate."""
    if _HAS_RAPIDFUZZ:
        # WHY: token_sort_ratio handles word-order differences
        # e.g. "java project" vs "Project Java" scores high.
        score = rf_fuzz.token_sort_ratio(query, candidate) / 100.0
        # Also try partial ratio for substring matches
        partial = rf_fuzz.partial_ratio(query, candidate) / 100.0
        return max(score, partial)
    else:
        return difflib.SequenceMatcher(None, query, candidate).ratio()


class FileSearchEngine:
    """
    High-level search engine that combines the indexer, cache, and explorer.
    """

    def __init__(self):
        self._cache = SearchCache()
        # WHY: verify integrity on startup to catch corruption early
        self._cache.verify_integrity()
        
        # Buffer of last 5 searches
        self.search_history = deque(maxlen=5)

        self._indexing = False
        self._index_lock = threading.Lock()
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        # WHY: track the actual thread object to prevent duplicate workers
        self._index_thread: Optional[threading.Thread] = None
        
        # Search Queue Manager
        self._search_thread: Optional[threading.Thread] = None
        self._search_cancel_event = threading.Event()
        self._search_lock = threading.Lock()
        
        self._monitor = FileMonitor(self._cache)
        
        # Setup providers
        self._providers = [
            EverythingProvider(),
            WindowsSearchProvider(),
            SQLiteProvider(self._cache),
            # LiveScannerProvider requires runtime args, will be instantiated in search()
        ]
        
        # Start monitoring existing indexed drives
        indexed_drives = self._cache.get_indexed_drives()
        if indexed_drives:
            roots = [f"{d}:\\" for d in indexed_drives]
            self._monitor.start(roots)

    def _get_live_scanner(self, on_progress: Callable[[str], None]) -> LiveScannerProvider:
        scanner = LiveScannerProvider(self._cache, self._cancel_event, on_progress, SEARCH_TIMEOUT_SEC)
        # Inject match func to avoid circular imports
        scanner.match_func = self._matches_query
        return scanner

    # ── Analytics & User Behavior ──────────────────────────────────────────
    
    def record_open(self, query: str, path: str):
        """Pass through to cache to record open event."""
        if hasattr(self._cache, "record_open"):
            self._cache.record_open(query, path)

    # ── Public Search API ──────────────────────────────────────────────────

    def search_async(
        self,
        query: str,
        drive: Optional[str] = None,
        search_type: Optional[str] = None,
        extension: Optional[str] = None,
        on_progress: Optional[Callable[[str], None]] = None,
        on_partial: Optional[Callable[[list], None]] = None,
        on_diagnostics: Optional[Callable[[dict], None]] = None,
        on_complete: Optional[Callable[[dict], None]] = None,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> None:
        """
        Search Queue Manager: Launch a background search.
        If a search is already running, it is cancelled.
        Newest search wins.
        """
        with self._search_lock:
            if self._search_thread and self._search_thread.is_alive():
                self._search_cancel_event.set()
                # We do not join, we let the old thread die naturally.
                
            self._search_cancel_event.clear()
            
            def worker():
                diag_stop = threading.Event()
                def diag_worker():
                    while not diag_stop.wait(0.5):
                        if on_diagnostics:
                            try:
                                import psutil
                                import os
                                process = psutil.Process(os.getpid())
                                mem = process.memory_info().rss / (1024 * 1024)
                            except ImportError:
                                mem = 0.0
                            on_diagnostics({
                                "query": query,
                                "memory_mb": round(mem, 1),
                                "threads": threading.active_count(),
                                "cancelled": self._search_cancel_event.is_set()
                            })
                
                dt = threading.Thread(target=diag_worker, daemon=True)
                dt.start()
                
                try:
                    res = self.search(
                        query=query, drive=drive, search_type=search_type,
                        extension=extension, on_progress=on_progress, on_partial=on_partial,
                        max_results=max_results, is_async=True
                    )
                finally:
                    diag_stop.set()
                    
                if not self._search_cancel_event.is_set():
                    if on_complete:
                        on_complete(res)
            
            self._search_thread = threading.Thread(target=worker, daemon=True)
            self._search_thread.start()

    def search(
        self,
        query: str,
        drive: Optional[str] = None,
        search_type: Optional[str] = None,
        extension: Optional[str] = None,
        on_progress: Optional[Callable[[str], None]] = None,
        on_partial: Optional[Callable[[list], None]] = None,
        max_results: int = DEFAULT_MAX_RESULTS,
        fuzzy_threshold: float = FUZZY_THRESHOLD,
        is_async: bool = False,
    ) -> dict:
        """
        Search for files/folders matching query using a Provider-Based Architecture.
        """
        search_start = time.perf_counter()
        query = query.strip()
        if not query:
            return {
                "status": "not_found", "results": [],
                "message": "No search query provided.", "count": 0,
            }

        progress = on_progress or (lambda msg: None)
        is_dir = None
        if search_type == "folder":
            is_dir = True
        elif search_type == "file":
            is_dir = False

        if not is_async:
            self._search_cancel_event.clear()
            self._cancel_event.clear()
        
        query_norm = _normalize_for_fuzzy(query)
        results = None
        used_provider = None

        all_providers = self._providers + [self._get_live_scanner(progress)]
        
        provider_logs = []

        for provider in all_providers:
            if self._search_cancel_event.is_set() or self._cancel_event.is_set():
                break
                
            provider_start = time.perf_counter()

            if provider.is_available:
                progress(f"Searching via {provider.name}...")
                
                try:
                    res = provider.search(
                        query=query,
                        drive=drive,
                        is_dir=is_dir,
                        extension=extension,
                        max_results=max_results * 5,
                        on_partial=on_partial
                    )
                except Exception as e:
                    log.error(f"Provider {provider.name} failed: {e}")
                    res = None

                elapsed_provider = (time.perf_counter() - provider_start) * 1000
                
                if res is not None:
                    valid_results = []
                    dead_paths = []
                    
                    for r in res:
                        p = r.get("path", "")
                        if os.path.exists(p):
                            valid_results.append(r)
                        else:
                            dead_paths.append(p)
                            
                    if dead_paths and provider.name == "SQLite Cache":
                        try:
                            conn = self._cache._get_conn()
                            with self._cache._lock:
                                placeholders = ",".join("?" * len(dead_paths))
                                conn.execute(f"DELETE FROM file_index WHERE path IN ({placeholders})", dead_paths)
                                conn.commit()
                        except Exception as e:
                            log.error(f"Error purging stale paths: {e}")

                    provider_logs.append(
                        f"Provider:\n{provider.name}\nResults:\n{len(valid_results)}\nTime:\n{elapsed_provider:.1f} ms\n--------------------------------"
                    )

                    if valid_results:
                        results = valid_results
                        used_provider = provider.name
                        
                        # Early-exit optimization for Exact Matches
                        ranked = self._rank_results(query, results, fuzzy_threshold)
                        if ranked and ranked[0].get("confidence_score", 0) == 100:
                            results = ranked
                            break
                        
                        if provider.name != "Live Scanner":
                            break
                else:
                    provider_logs.append(
                        f"Provider:\n{provider.name}\nResults:\n0 (Failed/Unavailable)\nTime:\n{elapsed_provider:.1f} ms\n--------------------------------"
                    )

        if self._cache.is_stale(drive):
            roots = None
            if drive:
                drive_letter = drive.strip().upper().rstrip(":\\")
                roots = [f"{drive_letter}:\\"]
            self._start_background_index(roots, progress)

        if results:
            # Re-rank if we didn't already
            if not results[0].get("confidence_score"):
                results = self._rank_results(query, results, fuzzy_threshold)
            final = self._deduplicate(results)[:max_results]

            elapsed_ms = (time.perf_counter() - search_start) * 1000
            log.info(f"[{used_provider}] Search for '{query}': {len(final)} results in {elapsed_ms:.1f}ms")

            resp = self._format_response(query, final, provider_logs)
            import uuid
            search_id = uuid.uuid4().hex[:8]
            resp["search_id"] = search_id
            resp["query"] = query
            resp["timestamp"] = int(time.time())
            self.search_history.append(resp)
            if hasattr(self._cache, "insert_analytic"):
                self._cache.insert_analytic(query, used_provider, elapsed_ms, len(final), "found")
            return resp

        # Fix #6: Output debug logs if nothing was found
        debug_output = "\n".join(provider_logs)
        elapsed_ms = (time.perf_counter() - search_start) * 1000
        msg = f"No files or folders matching '{query}' were found after {(elapsed_ms/1000):.1f}s.\n\nProvider Logs:\n{debug_output}"
        
        if hasattr(self._cache, "insert_analytic"):
            self._cache.insert_analytic(query, "none", elapsed_ms, 0, "not_found")
            
        return {
            "status": "not_found",
            "results": [],
            "message": msg,
            "count": 0,
        }

    def benchmark_providers(self, query: str) -> str:
        """Run a query across all providers to measure latency independently."""
        import time
        results_str = []
        total_start = time.perf_counter()
        
        all_providers = self._providers + [self._get_live_scanner(lambda m: None)]
        for provider in all_providers:
            if not provider.is_available:
                results_str.append(f"{provider.name}: Unavailable")
                continue
                
            start = time.perf_counter()
            try:
                # Limit max_results for benchmark and disable background streaming
                res = provider.search(query=query, max_results=50)
                elapsed = (time.perf_counter() - start) * 1000
                count = len(res) if res else 0
                results_str.append(f"{provider.name}: {elapsed:.1f} ms (Found {count})")
            except Exception as e:
                results_str.append(f"{provider.name}: Failed ({e})")
                
        total_elapsed = (time.perf_counter() - total_start) * 1000
        results_str.append(f"Total Benchmark Time: {total_elapsed:.1f} ms")
        return "\n".join(results_str)

    def select_from_last_search(self, query: str) -> Optional[dict]:
        """Attempt to map a natural language selection or exact name to a recent search result."""
        if not self.search_history:
            return None
            
        q_lower = query.strip().lower()
        
        # Check natural language indices
        index_map = {
            "first": 0, "1st": 0, "1": 0, "one": 0,
            "second": 1, "2nd": 1, "2": 1, "two": 1,
            "third": 2, "3rd": 2, "3": 2, "three": 2,
            "fourth": 3, "4th": 3, "4": 3, "four": 3,
            "fifth": 4, "5th": 4, "5": 4, "five": 4,
            "last": -1
        }
        
        target_idx = None
        for key, val in index_map.items():
            if q_lower == key or q_lower == f"open {key}" or q_lower == f"open number {key}" or q_lower == f"open the {key} one" or q_lower == f"{key} one":
                target_idx = val
                break
                
        # Look in the most recent search first
        for search_data in reversed(self.search_history):
            results = search_data["results"]
            if not results:
                continue
                
            if target_idx is not None:
                idx = target_idx if target_idx >= 0 else len(results) - 1
                if 0 <= idx < len(results):
                    return results[idx]
                    
            # Try to match the name natively
            for item in results:
                if item["name"].lower() == q_lower or _normalize_for_fuzzy(item["name"]) == _normalize_for_fuzzy(q_lower):
                    return item
                    
            # Try a Contains match
            for item in results:
                if q_lower in item["name"].lower():
                    return item

        return None

    def open_result(self, path_str: str) -> str:
        """Open a search result using the ExplorerManager."""
        return ExplorerManager.open(path_str)

    def cancel_search(self):
        """Cancel any ongoing live search."""
        self._cancel_event.set()
        log.info("Search cancelled by user.")

    def pause_indexing(self):
        """Pause background indexing."""
        self._pause_event.clear()
        log.info("Background indexing paused.")

    def resume_indexing(self):
        """Resume background indexing."""
        self._pause_event.set()
        log.info("Background indexing resumed.")

    def cancel_indexing(self):
        """Cancel background indexing entirely."""
        self._cancel_event.set()
        log.info("Background indexing cancelled.")

    def rebuild_index(
        self,
        drives: Optional[list[str]] = None,
        on_progress: Optional[Callable[[str], None]] = None,
    ):
        """Force a full re-index of specified drives/paths (or all drives)."""
        progress = on_progress or (lambda msg: None)
        roots = None
        if drives:
            roots = []
            for d in drives:
                d = d.strip()
                # If it's just a drive letter (C or C:), format it properly
                if len(d) <= 2 and d[0].isalpha():
                    roots.append(f"{d[0].upper()}:\\")
                else:
                    # It's a full path, pass it as is
                    roots.append(d)
        self._start_background_index(roots, progress, force=True)

    def get_index_stats(self) -> dict:
        """Return cache statistics."""
        return {
            "total_indexed": self._cache.get_total_count(),
            "indexed_drives": self._cache.get_indexed_drives(),
            "is_indexing": self._indexing,
            "has_rapidfuzz": _HAS_RAPIDFUZZ,
            "providers": [p.name for p in self._providers if p.is_available]
        }
        
    def _matches_query(
        self,
        query_raw: str,
        name_lower: str,
        filter_is_dir: Optional[bool],
        item_is_dir: bool,
        extension: Optional[str],
    ) -> bool:
        """Check if an item matches the search criteria (used by LiveScanner)."""
        query_norm = _normalize_for_fuzzy(query_raw)
        
        if filter_is_dir is not None and item_is_dir != filter_is_dir:
            return False
        if extension:
            ext = extension if extension.startswith(".") else f".{extension}"
            if not name_lower.endswith(ext.lower()):
                return False

        # Contains check (fast path)
        if query_norm in name_lower:
            return True

        # Normalized fuzzy check (handles camelCase, underscores, etc.)
        name_norm = _normalize_for_fuzzy(name_lower)
        if query_norm in name_norm:
            return True

        score = _fuzzy_score(query_norm, name_norm)
        return score >= 0.60

    # ── 10-Tier Ranking ────────────────────────────────────────────────────

    def _rank_results(
        self, query: str, results: list[dict], threshold: float
    ) -> list[dict]:
        """
        Re-rank results with 10-tier scoring:
          1. Exact path match
          2. Exact filename match
          3. Exact normalized name
          4. Prefix match
          5. Word boundary match
          6. Contains match
          7. RapidFuzz score
          8. Parent folder priority
          9. User folders priority
          10. Name length / alphabetical tiebreakers
        """
        query_lower = query.lower()
        query_norm = _normalize_for_fuzzy(query)
        scored: list[tuple[float, dict]] = []
        
        user_boosts = {}
        if hasattr(self._cache, "get_user_behavior_boost"):
            user_boosts = self._cache.get_user_behavior_boost(query)

        for r in results:
            name_lower = r["name"].lower()
            name_norm = _normalize_for_fuzzy(name_lower)
            path_str = r.get("path", "")
            path_lower = path_str.lower()
            
            match_type = "Unknown"
            
            # 1. Exact path match
            if path_lower == query_lower:
                score = 1000.0
                match_type = "Exact Path"
            # 2. Exact folder name
            elif name_lower == query_lower:
                score = 900.0
                match_type = "Exact Name"
            # 3. Exact normalized name
            elif name_norm == query_norm:
                score = 800.0
                match_type = "Normalized Name"
            # 4. Prefix match
            elif name_lower.startswith(query_lower) or name_norm.startswith(query_norm):
                score = 700.0
                match_type = "Prefix Match"
            # 5. Word boundary match
            elif re.search(r'\b' + re.escape(query_lower) + r'\b', name_lower) or \
                 re.search(r'\b' + re.escape(query_norm) + r'\b', name_norm):
                score = 600.0
                match_type = "Word Boundary"
            # 6. Contains match
            elif query_lower in name_lower or query_norm in name_norm:
                score = 500.0
                match_type = "Contains Match"
            # 7. RapidFuzz score
            else:
                fuzz = _fuzzy_score(query_norm, name_norm)
                score = 400.0 + (fuzz * 100.0) # Map 0-1 to 400-500
                match_type = "Fuzzy Match"

            # Only proceed if we met the fuzzy threshold (for tier 7). Exact matches always pass.
            if score < 400.0 + (threshold * 100.0) and score < 500.0:
                continue

            # 8. Parent folder priority
            if os.path.basename(os.path.dirname(path_lower)) == query_lower:
                score += 10.0

            # 9. User folders priority
            for uf in USER_FOLDERS:
                if path_str.startswith(uf):
                    score += 5.0
                    break

            # 9.5 User Behavior Learning Boost
            if path_str in user_boosts:
                # Massive artificial boost for previously opened items
                score += 5000.0 + (user_boosts[path_str] * 100.0)

            # 10. (Tiebreakers handled in sorting below)
            r["_score"] = score
            
            # Compute confidence score (0-100)
            if score >= 900:
                conf = 100
            elif score >= 800:
                conf = 95
            elif score >= 700:
                conf = 90
            elif score >= 600:
                conf = 85
            elif score >= 500:
                conf = 80
            else:
                # 400-500 is fuzzy mapping
                conf = int((score - 400) * 0.8) # up to 80
                
            r["confidence_score"] = min(100, max(0, conf))
            r["match_type"] = match_type
            
            scored.append((score, r))

        # Sort: highest score first, then shortest name, then alphabetical
        scored.sort(key=lambda x: (-x[0], len(x[1]["name"]), x[1]["name"].lower()))
        return [r for _, r in scored]

    # ── Deduplication ──────────────────────────────────────────────────────

    @staticmethod
    def _deduplicate(results: list[dict]) -> list[dict]:
        """Remove duplicate paths from results using path normalization."""
        seen: set[str] = set()
        deduped: list[dict] = []
        for r in results:
            p = os.path.normcase(os.path.normpath(r["path"]))
            if p not in seen:
                seen.add(p)
                deduped.append(r)
        return deduped

    # ── Response Formatting ────────────────────────────────────────────────

    def _format_response(self, query: str, results: list[dict], provider_logs: list[str]) -> dict:
        """Format results into a structured response dict."""
        count = len(results)
        debug_output = "\n".join(provider_logs)

        if count == 0:
            return {
                "status": "not_found", "results": [],
                "message": f"No files or folders matching '{query}' were found.\n\nProvider Logs:\n{debug_output}",
                "count": 0,
            }

        # High-confidence auto-open: if top result is a strong match (>= 0.95)
        # and there isn't a tie for first place, pretend we only found one.
        if count > 1:
            top_score = results[0].get("_score", 0)
            second_score = results[1].get("_score", 0)
            if top_score >= HIGH_CONFIDENCE and second_score < top_score:
                count = 1
                results = [results[0]]

        if count == 1:
            r = results[0]
            kind = "folder" if r["is_dir"] else "file"
            return {
                "status": "found", "results": results,
                "message": f"Found 1 {kind}: {r['name']} at {r['path']}\n\nProvider Logs:\n{debug_output}",
                "count": 1,
            }

        # Multiple results
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
            
        lines.append(f"\nProvider Logs:\n{debug_output}")

        return {
            "status": "multiple", "results": results,
            "message": "\n".join(lines), "count": count,
        }

    # ── Background Indexing (hardened) ─────────────────────────────────────

    def _start_background_index(
        self,
        roots: Optional[list[str]],
        on_progress: Callable[[str], None],
        force: bool = False,
    ):
        """
        Start a background thread to index drives into the cache.
        WHY single-worker guarantee: we track the thread object and check
        is_alive() instead of just a boolean flag, preventing race conditions
        where the flag gets stuck True after a crash.
        """
        with self._index_lock:
            # WHY: check is_alive() not just self._indexing — the thread
            # may have died without resetting the flag.
            if self._index_thread is not None and self._index_thread.is_alive():
                if not force:
                    log.info("Background indexing already in progress — skipping.")
                    return
                else:
                    # Force: cancel old, wait briefly, then start new
                    self._cancel_event.set()
                    self._index_thread.join(timeout=2.0)

            self._cancel_event.clear()
            self._pause_event.set()
            self._indexing = True

        def _index_worker():
            try:
                log.info(f"Background indexing started. Roots: {roots or 'all drives'}")

                cancel = self._cancel_event
                indexer = FileIndexer(
                    cancel_event=cancel,
                    on_progress=lambda msg: log.debug(msg),
                    skip_system=True,
                )

                # WHY incremental: purge only the drives being re-indexed,
                # not the whole cache. Other drives stay searchable.
                if roots:
                    for root in roots:
                        drv = root[0].upper() if len(root) >= 2 else ""
                        if drv:
                            self._cache.purge_drive(drv)

                buffer: list[tuple] = []
                total = 0
                start = time.time()

                for item in indexer.crawl(roots=roots):
                    # Pause support
                    self._pause_event.wait()
                    if cancel.is_set():
                        break

                    buffer.append(item)
                    if len(buffer) >= INDEX_BATCH_SIZE:
                        self._cache.bulk_upsert(buffer)
                        total += len(buffer)
                        buffer.clear()
                        elapsed = time.time() - start
                        rate = total / elapsed if elapsed > 0 else 0
                        log.debug(f"Indexed {total:,} items ({rate:,.0f}/s)...")

                if buffer:
                    self._cache.bulk_upsert(buffer)
                    total += len(buffer)

                # Mark drives as indexed
                if roots:
                    for root in roots:
                        drv = root[0].upper() if len(root) >= 2 else ""
                        if drv:
                            self._cache.mark_indexed(drv)
                else:
                    self._cache.mark_indexed()

                # Start monitoring the newly indexed drives
                new_indexed = self._cache.get_indexed_drives()
                self._monitor.start([f"{d}:\\" for d in new_indexed])

                elapsed = time.time() - start
                log.info(f"Background indexing complete. {total:,} items in {elapsed:.1f}s.")

            except Exception as e:
                log.error(f"Background indexing error: {e}", exc_info=True)
            finally:
                with self._index_lock:
                    self._indexing = False

        thread = threading.Thread(target=_index_worker, daemon=True, name="FileIndexWorker")
        with self._index_lock:
            self._index_thread = thread
        thread.start()
