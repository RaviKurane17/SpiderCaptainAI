"""
providers.py — Pluggable search providers for the FileSearchEngine.

Architecture:
- Defines a standard SearchProvider interface.
- Implements:
  1. EverythingProvider (uses Voidtools Everything SDK if available)
  2. WindowsSearchProvider (uses Windows Search API via OLEDB if available)
  3. SQLiteProvider (our persistent cache)
  4. LiveScannerProvider (our real-time fallback)
- Engine iterates through them in priority order and uses the first one
  that successfully returns results.
"""

import os
import ctypes
import logging
import threading
from abc import ABC, abstractmethod
from typing import Optional, Callable

from actions.files.cache import SearchCache
from actions.files.indexer import FileIndexer
from actions.files.config import CRAWL_BATCH_SIZE

log = logging.getLogger("SearchProviders")


class SearchProvider(ABC):
    """Base interface for all search providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider's dependencies/services are running."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        drive: Optional[str] = None,
        is_dir: Optional[bool] = None,
        extension: Optional[str] = None,
        max_results: int = 50,
    ) -> Optional[list[dict]]:
        """
        Execute search.
        Return None if the provider failed or cannot handle the query.
        Return list of result dicts if successful.
        """
        pass


class EverythingProvider(SearchProvider):
    """
    Integrates with Voidtools Everything SDK (Everything32.dll / Everything64.dll).
    Highest performance on Windows if installed.
    """
    
    def __init__(self):
        self._dll = None
        self._available = False
        self._init_sdk()

    @property
    def name(self) -> str:
        return "Everything SDK"

    @property
    def is_available(self) -> bool:
        return self._available

    def _init_sdk(self):
        if os.name != "nt":
            return
            
        try:
            # Look for DLL in system path or project root
            dll_name = "Everything64.dll" if ctypes.sizeof(ctypes.c_voidp) == 8 else "Everything32.dll"
            # Try to load it (it must be available in PATH or same dir)
            try:
                self._dll = ctypes.WinDLL(dll_name)
                # Quick test to see if IPC is running
                self._dll.Everything_GetMajorVersion.restype = ctypes.c_uint32
                if self._dll.Everything_GetMajorVersion() > 0:
                    self._available = True
            except OSError:
                pass
        except Exception as e:
            log.debug(f"EverythingProvider init failed: {e}")

    def search(self, query, drive=None, is_dir=None, extension=None, max_results=50, on_partial=None) -> Optional[list[dict]]:
        if not self._available or not self._dll:
            return None
            
        try:
            # Build query string
            q = query
            if drive:
                q = f"{drive}:\\ {q}"
            if is_dir is True:
                q = f"folder: {q}"
            elif is_dir is False:
                q = f"file: {q}"
            if extension:
                ext = extension if extension.startswith(".") else f".{extension}"
                q = f"ext:{ext.lstrip('.')} {q}"

            self._dll.Everything_SetSearchW(ctypes.c_wchar_p(q))
            self._dll.Everything_SetMax(ctypes.c_uint32(max_results))
            self._dll.Everything_SetRequestFlags(ctypes.c_uint32(
                0x00000001 | 0x00000002 | 0x00000004 | 0x00000010 | 0x00000040 # Name, Path, Size, Extension, DateModified
            ))
            
            # Execute
            success = self._dll.Everything_QueryW(ctypes.c_bool(True))
            if not success:
                return None

            num_results = self._dll.Everything_GetNumResults()
            results = []
            
            # Setup return types
            self._dll.Everything_GetResultFullPathNameW.argtypes = [ctypes.c_uint32, ctypes.c_wchar_p, ctypes.c_uint32]
            buf = ctypes.create_unicode_buffer(32768) # Max path

            for i in range(min(num_results, max_results)):
                self._dll.Everything_GetResultFullPathNameW(i, buf, 32768)
                path_str = buf.value
                name = os.path.basename(path_str)
                is_folder = self._dll.Everything_IsFolderResult(i) != 0
                ext = os.path.splitext(name)[1].lower()
                drv = path_str[0].upper() if len(path_str) >= 2 and path_str[1] == ":" else ""
                
                # Size and date (simplified for stub)
                size, mtime = 0, 0.0
                
                results.append({
                    "path": path_str,
                    "name": name,
                    "is_dir": is_folder,
                    "extension": ext,
                    "drive": drv,
                    "size": size,
                    "modified_at": mtime
                })
                
            return results
        except Exception as e:
            log.error(f"Everything SDK search failed: {e}")
            return None


class WindowsSearchProvider(SearchProvider):
    """
    Integrates with Windows Search API (WDS) via ADO/OLEDB.
    Built into Windows, but often incomplete index.
    """
    
    def __init__(self):
        self._available = False
        if os.name == "nt":
            try:
                # Requires pywin32 to actually work, we'll gracefully disable if missing
                import win32com.client # type: ignore
                self._available = True
            except ImportError:
                pass

    @property
    def name(self) -> str:
        return "Windows Search API"

    @property
    def is_available(self) -> bool:
        return self._available

    def search(self, query, drive=None, is_dir=None, extension=None, max_results=50, on_partial=None) -> Optional[list[dict]]:
        if not self._available:
            return None
            
        try:
            import win32com.client # type: ignore
            conn = win32com.client.Dispatch("ADODB.Connection")
            conn.Open("Provider=Search.CollatorDSO;Extended Properties='Application=Windows';")
            
            # Build SQL for WDS
            # Note: this is a basic query, WDS syntax can be very complex.
            sql = f"SELECT System.ItemPathDisplay, System.ItemNameDisplay, System.ItemType, System.Size, System.DateModified FROM SystemIndex WHERE CONTAINS(System.ItemNameDisplay, '\"{query}*\"')"
            if drive:
                sql += f" AND System.ItemPathDisplay LIKE '{drive}:\\\\%'"
                
            rs, _ = conn.Execute(sql)
            
            results = []
            count = 0
            while not rs.EOF and count < max_results:
                path_str = rs.Fields.Item("System.ItemPathDisplay").Value
                name = rs.Fields.Item("System.ItemNameDisplay").Value
                item_type = rs.Fields.Item("System.ItemType").Value
                size = rs.Fields.Item("System.Size").Value or 0
                
                if path_str and name:
                    is_folder = (item_type == "File folder")
                    ext = os.path.splitext(name)[1].lower()
                    drv = path_str[0].upper() if len(path_str) >= 2 and path_str[1] == ":" else ""
                    
                    if is_dir is not None and is_folder != is_dir:
                        rs.MoveNext()
                        continue
                        
                    if extension and not name.lower().endswith(extension.lower()):
                        rs.MoveNext()
                        continue
                        
                    results.append({
                        "path": path_str,
                        "name": name,
                        "is_dir": is_folder,
                        "extension": ext,
                        "drive": drv,
                        "size": int(size),
                        "modified_at": 0.0 # ADO dates need parsing
                    })
                    count += 1
                    
                rs.MoveNext()
                
            conn.Close()
            # If WDS finds nothing, it might just be unindexed. Fall back to SQLite.
            return results if results else None
        except Exception as e:
            log.debug(f"Windows Search API failed (likely index off or syntax): {e}")
            return None


class SQLiteProvider(SearchProvider):
    """Our robust SQLite cache provider."""
    
    def __init__(self, cache: SearchCache):
        self._cache = cache

    @property
    def name(self) -> str:
        return "SQLite Cache"

    @property
    def is_available(self) -> bool:
        return self._cache.get_total_count() > 0

    def search(self, query, drive=None, is_dir=None, extension=None, max_results=50, on_partial=None) -> Optional[list[dict]]:
        try:
            return self._cache.search(
                query=query,
                drive=drive,
                is_dir=is_dir,
                extension=extension,
                limit=max_results * 3 # Fetch extra for engine's fuzzy re-ranking
            )
        except Exception as e:
            log.error(f"SQLite search failed: {e}")
            return None


class LiveScannerProvider(SearchProvider):
    """Real-time os.scandir fallback."""
    
    def __init__(self, cache: SearchCache, cancel_event: threading.Event, on_progress: Callable[[str], None], timeout_sec: float):
        self._cache = cache
        self._cancel_event = cancel_event
        self._on_progress = on_progress
        self._timeout = timeout_sec
        # We need the matches_query function from engine, but to avoid circular import,
        # we will let the engine inject it or we duplicate the fast-path check here.
        # For clean architecture, we'll store a reference to the match function.
        self.match_func = None 

    @property
    def name(self) -> str:
        return "Live Scanner"

    @property
    def is_available(self) -> bool:
        return True # Always available

    def search(self, query, drive=None, is_dir=None, extension=None, max_results=50, on_partial=None) -> Optional[list[dict]]:
        import time
        from actions.files.config import USER_FOLDERS
        self._cancel_event.clear()
        
        results = []
        buffer = []
        partial_batch = []
        start_time = time.time()
        
        indexer = FileIndexer(
            cancel_event=self._cancel_event,
            on_progress=self._on_progress,
            skip_system=True
        )
        
        roots = None
        if drive:
            drv_clean = drive.strip().upper().rstrip(":\\")
            roots = [f"{drv_clean}:\\"]
        else:
            # Intent-Aware Search: If looking for documents, scan user folders first.
            query_lower = query.lower()
            doc_exts = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".txt", ".csv"}
            doc_keywords = {"resume", "marksheet", "invoice", "receipt", "document", "letter"}
            
            is_document = False
            if extension and extension.lower() in doc_exts:
                is_document = True
            elif any(kw in query_lower for kw in doc_keywords):
                is_document = True
                
            if is_document:
                # Add USER_FOLDERS first, then the rest of the drives
                roots = list(USER_FOLDERS)
                # Avoid duplicating if detection crawls everything, but indexer.crawl() accepts lists
                # C:\ and D:\ can be appended but it might re-scan. We'll just let it scan USER_FOLDERS first.

        generator = indexer.crawl(roots=roots)
        
        # If we supplied custom roots (USER_FOLDERS) but don't find it, we should fallback to all drives.
        # But we can just chain generators.
        if roots and roots == list(USER_FOLDERS):
            import itertools
            generator = itertools.chain(generator, indexer.crawl(roots=None))
            
        for item in generator:
            if self._cancel_event.is_set():
                break
                
            path_str, item_is_dir, name_lower, size, mtime = item
            elapsed = time.time() - start_time

            buffer.append(item)
            if len(buffer) >= CRAWL_BATCH_SIZE:
                self._cache.bulk_upsert(buffer)
                buffer.clear()

            is_match = False
            if self.match_func:
                is_match = self.match_func(query, name_lower, is_dir, item_is_dir, extension)
            else:
                if query.lower() in name_lower:
                    is_match = True
                    if is_dir is not None and item_is_dir != is_dir: is_match = False
                    if extension and not name_lower.endswith(extension.lower()): is_match = False
                    
            if is_match:
                name = os.path.basename(path_str)
                ext = os.path.splitext(name)[1].lower()
                drv = path_str[0].upper() if len(path_str) >= 2 and path_str[1] == ":" else ""
                res_obj = {
                    "path": path_str, "name": name,
                    "is_dir": item_is_dir, "extension": ext,
                    "drive": drv, "size": size, "modified_at": mtime,
                }
                results.append(res_obj)
                partial_batch.append(res_obj)
                
                if on_partial and len(partial_batch) >= 5:
                    on_partial(list(partial_batch))
                    partial_batch.clear()

            if len(results) >= max_results * 2:
                break

        if partial_batch and on_partial:
            on_partial(list(partial_batch))

        if buffer:
            self._cache.bulk_upsert(buffer)

        return results
