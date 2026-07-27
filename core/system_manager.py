import os
import psutil
from pathlib import Path
from utils.logger import log

def get_drives() -> list:
    """Returns a list of all mounted disk partitions and their usage stats."""
    drives = []
    try:
        partitions = psutil.disk_partitions(all=False)
        for partition in partitions:
            # Skip CD-ROM or unmounted drives
            if 'cdrom' in partition.opts or partition.fstype == '':
                continue
            
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                drives.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                })
            except PermissionError:
                # Some drives (like recovery partitions) deny access
                pass
    except Exception as e:
        log.error(f"[SystemManager] Failed to get drives: {e}")
        
    return drives

def get_special_folders() -> dict:
    """Returns absolute paths for Windows special folders."""
    home = str(Path.home())
    return {
        "Home": home,
        "Desktop": os.path.join(home, "Desktop"),
        "Documents": os.path.join(home, "Documents"),
        "Downloads": os.path.join(home, "Downloads"),
        "Pictures": os.path.join(home, "Pictures"),
        "Videos": os.path.join(home, "Videos"),
        "Music": os.path.join(home, "Music")
    }

def is_safe_path(path: str) -> bool:
    """
    SECURITY GUARD: Prevents destructive operations on critical Windows directories.
    Returns True if safe to modify/delete, False if protected.
    """
    path_lower = path.lower().replace('/', '\\')
    
    protected_dirs = [
        "c:\\windows",
        "c:\\program files",
        "c:\\program files (x86)",
        "c:\\programdata",
        "\\appdata\\roaming",
        "\\appdata\\local",
        "\\appdata\\locallow",
        "system32",
        "syswow64"
    ]
    
    # Check if the path is exactly a root drive (e.g. "C:\")
    if len(path_lower) <= 3 and path_lower.endswith(":\\"):
        return False
        
    for p_dir in protected_dirs:
        if p_dir in path_lower:
            return False
            
    return True

def get_recycle_bin_stats() -> dict:
    """Requires winshell to be installed. Returns item count and total size."""
    try:
        import winshell
        items = list(winshell.recycle_bin())
        total_size = sum(item.size() for item in items if hasattr(item, 'size') and callable(item.size))
        return {
            "count": len(items),
            "size": total_size,
            "success": True
        }
    except ImportError:
        return {"success": False, "error": "winshell not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def empty_recycle_bin():
    try:
        import winshell
        winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
        return {"success": True, "message": "Recycle Bin emptied"}
    except Exception as e:
        return {"success": False, "error": str(e)}
