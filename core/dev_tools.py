import os
import subprocess
from utils.logger import log

def get_dev_info(path: str) -> dict:
    """Returns Git status and detected language for a directory."""
    if not os.path.exists(path) or not os.path.isdir(path):
        return {"is_git": False, "branch": "", "status": "Clean", "language": "Unknown"}

    info = {
        "is_git": False,
        "branch": "",
        "status": "Clean",
        "language": "Unknown"
    }

    # 1. Check Git
    git_dir = os.path.join(path, '.git')
    if os.path.exists(git_dir):
        info["is_git"] = True
        try:
            # Get branch
            branch_out = subprocess.check_output(
                ["git", "branch", "--show-current"], 
                cwd=path, stderr=subprocess.DEVNULL, text=True
            ).strip()
            info["branch"] = branch_out or "DETACHED"

            # Get dirty status
            status_out = subprocess.check_output(
                ["git", "status", "--porcelain"], 
                cwd=path, stderr=subprocess.DEVNULL, text=True
            ).strip()
            
            if status_out:
                info["status"] = "Dirty"
        except Exception as e:
            log.warning(f"[DevTools] Git check failed in {path}: {e}")

    # 2. Detect Language / Framework
    files_in_root = set(os.listdir(path))
    if 'package.json' in files_in_root:
        info["language"] = "Node.js (TypeScript/JavaScript)"
    elif 'requirements.txt' in files_in_root or 'setup.py' in files_in_root or 'pyproject.toml' in files_in_root:
        info["language"] = "Python"
    elif 'pom.xml' in files_in_root or 'build.gradle' in files_in_root:
        info["language"] = "Java"
    elif 'go.mod' in files_in_root:
        info["language"] = "Go"
    elif 'Cargo.toml' in files_in_root:
        info["language"] = "Rust"
    elif 'CMakeLists.txt' in files_in_root:
        info["language"] = "C/C++"
    
    return info

def execute_dev_command(command: str, path: str):
    """Executes IDE/Terminal shortcuts."""
    if not os.path.exists(path):
        return {"success": False, "error": "Path does not exist"}

    try:
        if command == "vscode":
            subprocess.Popen(["code", "."], cwd=path, shell=True)
            return {"success": True, "message": "Opened in VS Code"}
        
        elif command == "terminal":
            # For Windows
            subprocess.Popen(["start", "cmd", "/k"], cwd=path, shell=True)
            return {"success": True, "message": "Opened Terminal"}
            
        elif command == "powershell":
            subprocess.Popen(["start", "powershell"], cwd=path, shell=True)
            return {"success": True, "message": "Opened PowerShell"}
            
        return {"success": False, "error": f"Unknown command {command}"}
    except Exception as e:
        log.error(f"[DevTools] Failed to execute {command} in {path}: {e}")
        return {"success": False, "error": str(e)}
