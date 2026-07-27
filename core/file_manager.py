import os
import shutil
import time
import zipfile
import hashlib
from pathlib import Path
from send2trash import send2trash
from utils.logger import log

def get_file_info(path: str) -> dict:
    try:
        stat = os.stat(path)
        is_dir = os.path.isdir(path)
        return {
            "name": os.path.basename(path),
            "path": path,
            "is_dir": is_dir,
            "size": stat.st_size if not is_dir else 0,
            "ext": os.path.splitext(path)[1].lower() if not is_dir else "",
            "modified": stat.st_mtime,
            "created": stat.st_ctime
        }
    except Exception as e:
        return {"error": str(e), "path": path}

def list_directory(dir_path: str) -> list:
    """Lists files and folders in a directory."""
    if not os.path.exists(dir_path):
        return []
    
    items = []
    try:
        for entry in os.scandir(dir_path):
            try:
                items.append({
                    "name": entry.name,
                    "path": entry.path,
                    "is_dir": entry.is_dir(),
                    "size": entry.stat().st_size if not entry.is_dir() else 0,
                    "ext": os.path.splitext(entry.name)[1].lower() if not entry.is_dir() else "",
                    "modified": entry.stat().st_mtime
                })
            except OSError:
                pass
    except Exception as e:
        log.error(f"[FileManager] Failed to list directory {dir_path}: {e}")
    
    # Sort: folders first, then files alphabetically
    items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
    return items

def file_operation(op: str, source: str, dest: str = None) -> dict:
    """Performs OS file operations with security checks."""
    try:
        from core.system_manager import is_safe_path
        
        if not os.path.exists(source):
            return {"success": False, "error": "Source does not exist"}

        # SECURITY CHECK
        if op in ["delete", "move", "rename"]:
            if not is_safe_path(source):
                return {"success": False, "error": f"SECURITY ALERT: Modifying {source} is restricted to prevent system corruption."}
            if dest and not is_safe_path(dest):
                return {"success": False, "error": f"SECURITY ALERT: Cannot write to restricted path {dest}."}

        if op == "delete":
            send2trash(source)
            return {"success": True, "message": f"Moved {os.path.basename(source)} to Recycle Bin"}
        
        elif op == "rename":
            if not dest: return {"success": False, "error": "Destination required for rename"}
            new_path = os.path.join(os.path.dirname(source), dest)
            os.rename(source, new_path)
            return {"success": True, "message": f"Renamed to {dest}", "new_path": new_path}
            
        elif op == "move":
            if not dest: return {"success": False, "error": "Destination required for move"}
            shutil.move(source, dest)
            return {"success": True, "message": f"Moved to {dest}"}
            
        elif op == "copy":
            if not dest: return {"success": False, "error": "Destination required for copy"}
            if os.path.isdir(source):
                shutil.copytree(source, dest)
            else:
                shutil.copy2(source, dest)
            return {"success": True, "message": f"Copied to {dest}"}
            
        elif op == "compress":
            zip_path = source + ".zip"
            if os.path.isdir(source):
                shutil.make_archive(source, 'zip', source)
            else:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(source, os.path.basename(source))
            return {"success": True, "message": f"Compressed to {zip_path}"}
            
        elif op == "extract":
            if not source.endswith(".zip"):
                return {"success": False, "error": "Only .zip files can be extracted"}
            dest_dir = dest or os.path.splitext(source)[0]
            with zipfile.ZipFile(source, 'r') as zf:
                zf.extractall(dest_dir)
            return {"success": True, "message": f"Extracted to {dest_dir}"}
            
        return {"success": False, "error": "Unknown operation"}
    except Exception as e:
        log.error(f"[FileManager] Operation {op} failed on {source}: {e}")
        return {"success": False, "error": str(e)}

def search_files(root_dir: str, query: str) -> list:
    """Basic fuzzy search by name."""
    results = []
    query = query.lower()
    try:
        for root, _, files in os.walk(root_dir):
            for file in files:
                if query in file.lower():
                    path = os.path.join(root, file)
                    results.append(get_file_info(path))
                    if len(results) >= 100:  # Cap results
                        return results
    except Exception as e:
        log.error(f"[FileManager] Search failed: {e}")
    return results

def get_file_preview(path: str) -> dict:
    """Reads a chunk of a text file for preview."""
    try:
        if not os.path.exists(path) or os.path.isdir(path):
            return {"success": False, "error": "File not found or is a directory"}
        
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            return {"success": True, "type": "image", "path": path}
            
        # Try reading as text
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(4000) # Read first 4KB
        return {"success": True, "type": "text", "content": content}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def get_ai_summary(path: str, ai_service) -> dict:
    """Uses the AI service to summarize a file's contents."""
    try:
        preview = get_file_preview(path)
        if not preview.get("success") or preview.get("type") != "text":
            return {"success": False, "error": "File cannot be summarized (unsupported format or too large)."}
            
        content = preview["content"]
        prompt = f"Summarize the following file content. Keep it concise, highlighting the main purpose, key variables or classes if it's code, or the main idea if it's text:\n\n{content}"
        
        # We need a synchronous-friendly or async way to call Gemini.
        # For simplicity, we'll assume the frontend will send a normal chat message 
        # or we can use a dedicated prompt. 
        # Here we just prepare the prompt, the caller handles the AI part if needed.
        return {"success": True, "prompt": prompt}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
