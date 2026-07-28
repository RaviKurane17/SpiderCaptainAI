"""
ExplorerManager — Opens files and folders using native Windows APIs.

Design decisions:
- Uses os.startfile() on Windows for maximum compatibility with all file types.
- Falls back to subprocess for Linux/Mac.
- Opens folders in Windows Explorer.
- Opens files in their default associated program.
- Separate from the search logic (Single Responsibility).
"""

import os
import subprocess
import platform
import logging
from pathlib import Path

log = logging.getLogger("ExplorerManager")


class ExplorerManager:
    """
    Responsible solely for opening files and folders via the OS.
    
    Usage:
        mgr = ExplorerManager()
        result = mgr.open("C:\\Users\\ravi\\Desktop\\demo")
    """

    _OS = platform.system()

    @classmethod
    def open(cls, path_str: str) -> str:
        """
        Open a file or folder using the OS default handler.
        Returns a user-friendly status message.
        """
        target = Path(path_str)

        if not target.exists():
            return f"Path not found: {path_str}"

        try:
            if cls._OS == "Windows":
                os.startfile(str(target))
            elif cls._OS == "Darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])

            kind = "folder" if target.is_dir() else "file"
            log.info(f"Opened {kind}: {target}")
            return f"Opened {kind}: {target.name}"

        except OSError as e:
            log.error(f"Failed to open {path_str}: {e}")
            return f"Could not open {target.name}: {e}"
        except Exception as e:
            log.error(f"Unexpected error opening {path_str}: {e}")
            return f"Error opening {target.name}: {e}"

    @classmethod
    def open_in_explorer(cls, path_str: str) -> str:
        """
        Open a folder in Windows Explorer (or equivalent).
        If path is a file, opens its parent folder and selects the file.
        """
        target = Path(path_str)

        if not target.exists():
            return f"Path not found: {path_str}"

        try:
            if cls._OS == "Windows":
                if target.is_file():
                    # Open explorer and highlight the file
                    subprocess.Popen(["explorer", "/select,", str(target)])
                else:
                    subprocess.Popen(["explorer", str(target)])
            elif cls._OS == "Darwin":
                if target.is_file():
                    subprocess.Popen(["open", "-R", str(target)])
                else:
                    subprocess.Popen(["open", str(target)])
            else:
                folder = str(target) if target.is_dir() else str(target.parent)
                subprocess.Popen(["xdg-open", folder])

            log.info(f"Opened in explorer: {target}")
            return f"Opened in Explorer: {target.name}"

        except Exception as e:
            log.error(f"Failed to open in explorer: {e}")
            return f"Error: {e}"

    @classmethod
    def reveal(cls, path_str: str) -> str:
        """Alias for open_in_explorer — reveals the item in file manager."""
        return cls.open_in_explorer(path_str)
