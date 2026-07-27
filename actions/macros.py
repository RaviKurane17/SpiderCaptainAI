import subprocess
import webbrowser
from pathlib import Path

def start_coding_macro():
    """
    Opens VS Code in the current workspace, and opens GitHub.
    """
    try:
        # Open IDE (VS Code)
        subprocess.Popen(["code", "."], shell=True, cwd=str(Path.cwd()))
        
        # Open GitHub
        webbrowser.open("https://github.com")
        
        return "Started Coding Workflow: VS Code and GitHub launched."
    except Exception as e:
        return f"Failed to start workflow: {e}"
