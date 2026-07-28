import os
import shutil
import platform
from pathlib import Path
from datetime import datetime

try:
    import send2trash
    _SEND2TRASH = True
except ImportError:
    _SEND2TRASH = False

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"

_SAFE_ROOTS: list[Path] = [
    Path.home(),
]

def _is_safe_path(target: Path) -> bool:
    # Allow all paths. The OS will enforce its own file permissions.
    return True

def _get_desktop() -> Path:
    if _OS == "Linux":
        xdg = os.environ.get("XDG_DESKTOP_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Desktop"

def _get_downloads() -> Path:
    if _OS == "Linux":
        xdg = os.environ.get("XDG_DOWNLOAD_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Downloads"

def _get_documents() -> Path:
    if _OS == "Linux":
        xdg = os.environ.get("XDG_DOCUMENTS_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Documents"

def _get_pictures() -> Path:
    if _OS == "Linux":
        xdg = os.environ.get("XDG_PICTURES_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Pictures"

def _get_music() -> Path:
    if _OS == "Linux":
        xdg = os.environ.get("XDG_MUSIC_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Music"

def _get_videos() -> Path:
    if _OS == "Linux":
        xdg = os.environ.get("XDG_VIDEOS_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Videos"


def _resolve_path(raw: str) -> Path:
    shortcuts: dict[str, Path] = {
        "desktop":   _get_desktop(),
        "downloads": _get_downloads(),
        "documents": _get_documents(),
        "pictures":  _get_pictures(),
        "music":     _get_music(),
        "videos":    _get_videos(),
        "home":      Path.home(),
    }
    lower = raw.strip().lower()
    if lower in shortcuts:
        return shortcuts[lower]
    return Path(raw).expanduser()

def _format_size(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"

def _safe_trash(target: Path) -> str:

    if not _SEND2TRASH:
        return (
            "send2trash is not installed. "
            "Run: pip install send2trash — "
            "Permanent deletion is disabled for safety."
        )
    send2trash.send2trash(str(target))
    return f"Moved to Trash: {target.name}"


def list_files(path: str = "desktop", show_hidden: bool = False) -> str:
    try:
        target = _resolve_path(path)
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        if not target.exists():
            return f"Path not found: {target}"
        if not target.is_dir():
            return f"Not a directory: {target}"

        items = []
        for item in sorted(target.iterdir()):
            if not show_hidden and item.name.startswith("."):
                continue
            if item.is_dir():
                items.append(f"📁 {item.name}/")
            else:
                size = _format_size(item.stat().st_size)
                items.append(f"📄 {item.name} ({size})")

        if not items:
            return f"Directory is empty: {target.name}/"

        return f"Contents of {target.name}/ ({len(items)} items):\n" + "\n".join(items)

    except PermissionError:
        return f"Permission denied: {path}"
    except Exception as e:
        return f"Error listing files: {e}"


def create_file(path: str, name: str = "", content: str = "") -> str:
    try:
        base   = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"File created: {target.name}"
    except Exception as e:
        return f"Could not create file: {e}"


def create_folder(path: str, name: str = "") -> str:
    try:
        base   = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        target.mkdir(parents=True, exist_ok=True)
        return f"Folder created: {target.name}"
    except Exception as e:
        return f"Could not create folder: {e}"


def delete_file(path: str, name: str = "") -> str:
    try:
        base   = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        if not target.exists():
            return f"Not found: {target.name}"

        # Güvenli dizin kontrolü — kritik kullanıcı klasörlerini koru
        protected = {
            _get_desktop(), _get_downloads(), _get_documents(),
            _get_pictures(), _get_music(), _get_videos(), Path.home()
        }
        if target.resolve() in {p.resolve() for p in protected}:
            return f"Protected directory, cannot delete: {target.name}"

        return _safe_trash(target)

    except PermissionError:
        return f"Permission denied: {path}"
    except Exception as e:
        return f"Could not delete: {e}"


def move_file(path: str, name: str = "", destination: str = "") -> str:
    try:
        base   = _resolve_path(path)
        src    = (base / name) if name else base
        dst    = _resolve_path(destination) if destination else None

        if not src.exists():
            return f"Source not found: {src.name}"
        if dst is None:
            return "No destination specified."
        if not _is_safe_path(src):
            return f"Access denied (source): {src}"
        if not _is_safe_path(dst):
            return f"Access denied (destination): {dst}"

        if dst.is_dir():
            dst = dst / src.name

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return f"Moved: {src.name} → {dst.parent.name}/"

    except Exception as e:
        return f"Could not move: {e}"


def copy_file(path: str, name: str = "", destination: str = "") -> str:
    try:
        base = _resolve_path(path)
        src  = (base / name) if name else base
        dst  = _resolve_path(destination) if destination else None

        if not src.exists():
            return f"Source not found: {src.name}"
        if dst is None:
            return "No destination specified."
        if not _is_safe_path(src):
            return f"Access denied (source): {src}"
        if not _is_safe_path(dst):
            return f"Access denied (destination): {dst}"

        if dst.is_dir():
            dst = dst / src.name

        dst.parent.mkdir(parents=True, exist_ok=True)

        if src.is_dir():
            shutil.copytree(str(src), str(dst))
        else:
            shutil.copy2(str(src), str(dst))

        return f"Copied: {src.name} → {dst.parent.name}/"

    except Exception as e:
        return f"Could not copy: {e}"


def rename_file(path: str, name: str = "", new_name: str = "") -> str:
    try:
        base     = _resolve_path(path)
        target   = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        if not target.exists():
            return f"Not found: {target.name}"
        if not new_name:
            return "No new name provided."

        new_path = target.parent / new_name
        if new_path.exists():
            return f"A file named '{new_name}' already exists here."

        target.rename(new_path)
        return f"Renamed: {target.name} → {new_name}"

    except Exception as e:
        return f"Could not rename: {e}"


def read_file(path: str, name: str = "", max_chars: int = 4000) -> str:
    try:
        base   = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        if not target.exists():
            return f"File not found: {target.name}"
        if not target.is_file():
            return f"Not a file: {target.name}"

        content = target.read_text(encoding="utf-8", errors="ignore")
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n[Truncated — {len(content)} total chars]"
        return content

    except Exception as e:
        return f"Could not read file: {e}"


def write_file(path: str, name: str = "", content: str = "",
               append: bool = False) -> str:
    try:
        base   = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(target, mode, encoding="utf-8") as f:
            f.write(content)
        action = "Appended to" if append else "Written to"
        return f"{action}: {target.name}"
    except Exception as e:
        return f"Could not write file: {e}"


def find_files(name: str = "", extension: str = "",
               path: str = "home", max_results: int = 20) -> str:
    try:
        search_path = _resolve_path(path)
        if not _is_safe_path(search_path):
            return f"Access denied: {search_path}"
        if not search_path.exists():
            return f"Search path not found: {path}"

        results    = []
        dir_count  = 0
        max_dirs   = 500  # performans + güvenlik limiti

        for item in search_path.rglob("*"):
            if item.is_dir():
                dir_count += 1
                if dir_count > max_dirs:
                    break
                continue
            if not item.is_file():
                continue
            if extension and item.suffix.lower() != extension.lower():
                continue
            if name and name.lower() not in item.name.lower():
                continue
            size = _format_size(item.stat().st_size)
            results.append(f"📄 {item.name} ({size}) — {item.parent}")
            if len(results) >= max_results:
                break

        if not results:
            query = name or extension or "files"
            return f"No {query} found in {search_path.name}/"

        return f"Found {len(results)} file(s):\n" + "\n".join(results)

    except Exception as e:
        return f"Search error: {e}"


def get_largest_files(path: str = "downloads", count: int = 10) -> str:
    count = min(count, 50)  # maksimum 50
    try:
        search_path = _resolve_path(path)
        if not _is_safe_path(search_path):
            return f"Access denied: {search_path}"
        if not search_path.exists():
            return f"Path not found: {path}"

        files = []
        for item in search_path.rglob("*"):
            if item.is_file():
                try:
                    files.append((item.stat().st_size, item))
                except Exception:
                    continue

        files.sort(reverse=True)
        top = files[:count]

        if not top:
            return "No files found."

        lines = [f"Top {len(top)} largest files in {search_path.name}/:"]
        for size, f in top:
            lines.append(f"  {_format_size(size):>10}  {f.name}  ({f.parent})")

        return "\n".join(lines)

    except Exception as e:
        return f"Error: {e}"


def get_disk_usage(path: str = "home") -> str:
    try:
        target = _resolve_path(path)
        usage  = shutil.disk_usage(target)
        pct    = usage.used / usage.total * 100
        return (
            f"Disk usage ({target}):\n"
            f"  Total : {_format_size(usage.total)}\n"
            f"  Used  : {_format_size(usage.used)} ({pct:.1f}%)\n"
            f"  Free  : {_format_size(usage.free)}"
        )
    except Exception as e:
        return f"Could not get disk usage: {e}"


def organize_desktop() -> str:
    type_map = {
        "Images":    {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".heic"},
        "Documents": {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx",
                      ".ppt", ".pptx", ".csv", ".odt", ".ods", ".odp"},
        "Videos":    {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
        "Music":     {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
        "Archives":  {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
        "Code":      {".py", ".js", ".ts", ".html", ".css", ".json", ".xml",
                      ".cpp", ".java", ".cs", ".go", ".rs", ".sh"},
    }

    desktop = _get_desktop()
    moved, skipped = [], []

    try:
        for item in desktop.iterdir():
            # Klasörlere, gizli dosyalara ve organize klasörlerine dokunma
            if item.is_dir() or item.name.startswith("."):
                continue
            if item.name in {k for k in type_map}:
                continue

            ext        = item.suffix.lower()
            target_dir = desktop / "Others"
            for folder, exts in type_map.items():
                if ext in exts:
                    target_dir = desktop / folder
                    break

            target_dir.mkdir(exist_ok=True)
            new_path = target_dir / item.name

            if new_path.exists():
                skipped.append(item.name)
                continue

            shutil.move(str(item), str(new_path))
            moved.append(f"{item.name} → {target_dir.name}/")

        result = f"Desktop organized: {len(moved)} files moved."
        if moved:
            preview = moved[:8]
            result += "\n" + "\n".join(preview)
            if len(moved) > 8:
                result += f"\n... and {len(moved) - 8} more."
        if skipped:
            result += f"\n{len(skipped)} file(s) skipped (name conflict)."
        return result

    except Exception as e:
        return f"Could not organize desktop: {e}"


def get_file_info(path: str, name: str = "") -> str:
    try:
        base   = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        if not target.exists():
            return f"Not found: {target.name}"

        stat = target.stat()
        info = {
            "Name":      target.name,
            "Type":      "Folder" if target.is_dir() else "File",
            "Size":      _format_size(stat.st_size),
            "Location":  str(target.parent),
            "Created":   datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M"),
            "Modified":  datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "Extension": target.suffix or "—",
        }
        return "\n".join(f"  {k}: {v}" for k, v in info.items())

    except Exception as e:
        return f"Could not get file info: {e}"

def file_controller(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    action = params.get("action", "").lower().strip()
    path   = params.get("path", "desktop")
    name   = params.get("name", "")

    if player:
        player.write_log(f"[file] {action} {name or path}")

    try:
        if action == "list":
            return list_files(path)

        elif action == "create_file":
            return create_file(path, name=name, content=params.get("content", ""))

        elif action == "create_folder":
            return create_folder(path, name=name)

        elif action == "delete":
            return delete_file(path, name=name)

        elif action == "move":
            return move_file(path, name=name, destination=params.get("destination", ""))

        elif action == "copy":
            return copy_file(path, name=name, destination=params.get("destination", ""))

        elif action == "rename":
            return rename_file(path, name=name, new_name=params.get("new_name", ""))

        elif action == "read":
            return read_file(path, name=name)

        elif action == "write":
            return write_file(
                path, name=name,
                content=params.get("content", ""),
                append=params.get("append", False)
            )

        elif action == "find":
            # Legacy find — still works but now uses the new engine
            return _smart_search(params, player)

        elif action == "search":
            # New advanced search action
            return _smart_search(params, player)

        elif action == "open":
            # Open a file or folder — searches if no full path given
            return _smart_open(params, player)

        elif action == "open_folder":
            # Explicitly open a folder
            return _smart_open(params, player, force_folder=True)

        elif action == "reveal":
            # Open parent folder and highlight the file
            from actions.files.explorer import ExplorerManager
            target = _resolve_path(path)
            if name:
                target = target / name
            return ExplorerManager.reveal(str(target))

        elif action == "rebuild_index":
            # Force rebuild the file index cache
            from actions.files.engine import get_engine
            drive = params.get("drive", None)
            drives = [drive] if drive else None
            engine = get_engine()
            engine.rebuild_index(drives=drives)
            return "File index rebuild started in background. Future searches will be much faster."

        elif action == "index_stats":
            from actions.files.engine import get_engine
            stats = get_engine().get_index_stats()
            return (
                f"File Index Stats:\n"
                f"  Total indexed: {stats['total_indexed']:,}\n"
                f"  Indexed drives: {', '.join(stats['indexed_drives']) or 'None'}\n"
                f"  Currently indexing: {'Yes' if stats['is_indexing'] else 'No'}"
            )

        elif action == "largest":
            return get_largest_files(
                path=path,
                count=int(params.get("count", 10)),
            )

        elif action == "disk_usage":
            return get_disk_usage(path)

        elif action == "organize_desktop":
            return organize_desktop()

        elif action == "benchmark":
            return _smart_benchmark(params, player)

        elif action == "info":
            return get_file_info(path, name=name)

        else:
            return f"Unknown action: '{action}'"

    except Exception as e:
        return f"File controller error ({action}): {e}"


# ── New Search/Open Helpers (delegate to FileSearchEngine) ─────────────────

def _smart_benchmark(params: dict, player=None) -> str:
    from actions.files.engine import get_engine
    query = params.get("name", "") or params.get("query", "")
    if not query:
        return "Please specify a query to benchmark."
        
    engine = get_engine()
    return engine.benchmark_providers(query)

def _smart_search(params: dict, player=None) -> str:
    """
    Advanced search using FileSearchEngine.
    Supports: name, drive, search_type (file/folder), extension.
    """
    from actions.files.engine import get_engine

    query = params.get("name", "") or params.get("query", "")
    drive = params.get("drive", None)
    search_type = params.get("search_type", None)  # "file", "folder", or None
    extension = params.get("extension", None)
    path = params.get("path", "")

    # If path looks like a drive letter, extract it
    if path and len(path) <= 3 and path[0].isalpha():
        drive = path[0].upper()

    ui = getattr(player, "ui", player) if player else None
    
    progress_msgs = []
    def on_progress(msg: str):
        progress_msgs.append(msg)
        if player:
            player.write_log(f"[search] {msg}")

    accumulated_results = []
    def on_partial(batch: list):
        accumulated_results.extend(batch)
        if ui and hasattr(ui, "broadcast"):
            ui.broadcast({
                "type": "chat_search_results",
                "query": query,
                "results": accumulated_results
            })
            
    def on_diagnostics(diag_data: dict):
        if ui and hasattr(ui, "broadcast"):
            ui.broadcast({
                "type": "diagnostics_update",
                "data": diag_data
            })
            
    def on_complete(result: dict):
        if ui and hasattr(ui, "broadcast") and result.get("status") == "multiple":
            ui.broadcast({
                "type": "chat_search_results",
                "query": query,
                "results": result.get("results", [])
            })

    engine = get_engine()
    engine.search_async(
        query=query,
        drive=drive,
        search_type=search_type,
        extension=extension,
        on_progress=on_progress,
        on_partial=on_partial,
        on_diagnostics=on_diagnostics,
        on_complete=on_complete,
        max_results=30,
    )

    return f"Initiated search for '{query}'. Results will stream into the UI shortly."


def _smart_open(params: dict, player=None, force_folder: bool = False) -> str:
    """
    Smart open: if a full path is given, open it directly.
    If only a name is given, search for it first, then:
      - If 1 result: auto-open
      - If multiple: ask the user which one
    """
    from actions.files.engine import get_engine
    from actions.files.explorer import ExplorerManager

    name = params.get("name", "") or params.get("query", "")
    path = params.get("path", "")
    drive = params.get("drive", None)

    # If a full absolute path is given, open directly
    if path and (Path(path).is_absolute() or (len(path) >= 2 and path[1] == ":")):
        target = Path(path)
        if name:
            target = target / name
        if target.exists():
            return ExplorerManager.open(str(target))
        # Path doesn't exist — fall through to search

    # If path is a shortcut like "desktop", "downloads", try resolving
    if path and not drive:
        resolved = _resolve_path(path)
        if name:
            candidate = resolved / name
            if candidate.exists():
                return ExplorerManager.open(str(candidate))

    # Extract drive from path if it looks like a drive letter
    if path and len(path) <= 3 and path[0].isalpha():
        drive = path[0].upper()

    # Fall back to search
    search_type = "folder" if force_folder else None
    
    ui = getattr(player, "ui", player) if player else None
    
    progress_msgs = []
    def on_progress(msg: str):
        progress_msgs.append(msg)
        if player:
            player.write_log(f"[open] {msg}")

    engine = get_engine()
    
    if name:
        cached_match = engine.select_from_last_search(name)
        if cached_match:
            target_path = cached_match["path"]
            engine.record_open(name, target_path)
            open_msg = ExplorerManager.open(target_path)
            if ui and hasattr(ui, "broadcast"):
                ui.broadcast({"type": "tts", "text": "I found it in the cache and opened it."})
            return f"Opened from recent search: {cached_match['name']}\n{open_msg}"
            
    accumulated_results = []
    def on_partial(batch: list):
        accumulated_results.extend(batch)
        if ui and hasattr(ui, "broadcast"):
            ui.broadcast({
                "type": "chat_search_results",
                "query": name,
                "results": accumulated_results
            })
            
    def on_diagnostics(diag_data: dict):
        if ui and hasattr(ui, "broadcast"):
            ui.broadcast({
                "type": "diagnostics_update",
                "data": diag_data
            })
            
    def on_complete(result: dict):
        if result["status"] == "found" and result["count"] == 1:
            target_path = result["results"][0]["path"]
            engine.record_open(name, target_path)
            ExplorerManager.open(target_path)
            if ui and hasattr(ui, "broadcast"):
                ui.broadcast({"type": "tts", "text": "I found your file and opened it."})
        elif result["status"] == "multiple":
            if ui and hasattr(ui, "broadcast"):
                ui.broadcast({
                    "type": "chat_search_results",
                    "query": name,
                    "results": result.get("results", [])
                })

    engine.search_async(
        query=name,
        drive=drive,
        search_type=search_type,
        on_progress=on_progress,
        on_partial=on_partial,
        on_diagnostics=on_diagnostics,
        on_complete=on_complete,
        max_results=20,
    )

    return f"Searching for '{name}' in the background. I will open it as soon as I find it."