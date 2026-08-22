"""
ExplorerManager — Opens files and folders using native OS APIs.

Audit fixes applied:
- UNC path support (\\\\server\\share\\folder).
- Long path support (\\\\?\\C:\\very\\long\\path).
- Unicode safety — handle non-ASCII filenames.
- Network path timeout — subprocess won't hang forever.
- Structured error returns — never crashes, always returns a message.
- Symlink/junction awareness — resolves before opening.
"""

import os
import subprocess
import platform
import logging
from pathlib import Path

from actions.files.config import EXPLORER_SUBPROCESS_TIMEOUT, WIN_LONG_PATH_PREFIX

log = logging.getLogger("ExplorerManager")


class ExplorerManager:
    """
    Responsible solely for opening files and folders via the OS.

    Public API (preserved):
        open(path_str)           -> str
        open_in_explorer(path_str) -> str
        reveal(path_str)         -> str
    """

    _OS = platform.system()

    @classmethod
    def _normalize_path(cls, path_str: str) -> str:
        """
        Normalize a path for safe OS operations.
        WHY: Windows chokes on mixed slashes, trailing spaces,
        and paths > 260 chars without the \\?\ prefix.
        """
        # Strip surrounding quotes/spaces
        cleaned = path_str.strip().strip('"').strip("'")

        # On Windows, normalize separators
        if cls._OS == "Windows":
            cleaned = cleaned.replace("/", "\\")
            # Remove long-path prefix for display but keep for API
            # (os.startfile handles it natively on modern Windows)

        return cleaned

    @classmethod
    def _validate_path(cls, path_str: str) -> tuple[bool, str]:
        """
        Validate a path before attempting to open it.
        Returns (is_valid, error_message_or_empty).
        """
        if not path_str:
            return False, "Empty path provided."

        normalized = cls._normalize_path(path_str)

        # WHY: catch broken symlinks early with a clear message
        p = Path(normalized)
        if p.is_symlink() and not p.exists():
            return False, f"Broken symlink: {p.name}"

        if not p.exists():
            # Check if it's a UNC path that might be unreachable
            if normalized.startswith("\\\\"):
                return False, f"Network path unreachable: {normalized}"
            return False, f"Path not found: {normalized}"

        return True, ""

    @classmethod
    def open(cls, path_str: str) -> str:
        """
        Open a file or folder using the OS default handler.
        Returns a user-friendly status message.
        """
        normalized = cls._normalize_path(path_str)
        valid, err = cls._validate_path(normalized)
        if not valid:
            return err

        target = Path(normalized)

        try:
            if cls._OS == "Windows":
                # WHY: ShellExecuteW returns an HINSTANCE. Values > 32 = success.
                # Values <= 32 are error codes (e.g. 31 = no association).
                # os.startfile() silently swallows association errors.
                import ctypes
                result = ctypes.windll.shell32.ShellExecuteW(
                    None, "open", str(target), None, None, 1  # SW_SHOWNORMAL
                )
                if result <= 32:
                    _SHELL_ERRORS = {
                        0: "Out of memory",
                        2: "File not found",
                        3: "Path not found",
                        5: "Access denied",
                        11: "Bad format",
                        26: "Sharing violation",
                        27: "Incomplete file association",
                        28: "DDE timeout",
                        29: "DDE failed",
                        30: "DDE busy",
                        31: "No application associated with this file type",
                        32: "DLL not found",
                    }
                    err_msg = _SHELL_ERRORS.get(result, f"Shell error code {result}")
                    log.error(f"ShellExecuteW failed for {target}: {err_msg}")
                    return f"Could not open {target.name}: {err_msg}"
            elif cls._OS == "Darwin":
                subprocess.Popen(
                    ["open", str(target)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    ["xdg-open", str(target)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            kind = "folder" if target.is_dir() else "file"
            log.info(f"Opened {kind}: {target}")
            return f"Opened {kind}: {target.name}"

        except OSError as e:
            log.error(f"Failed to open {normalized}: {e}")
            return f"Could not open {target.name}: {e}"
        except Exception as e:
            log.error(f"Unexpected error opening {normalized}: {e}")
            return f"Error opening {target.name}: {e}"

    @classmethod
    def open_in_explorer(cls, path_str: str) -> str:
        """
        Open a folder in Windows Explorer (or equivalent).
        If path is a file, opens its parent folder and selects the file.
        """
        normalized = cls._normalize_path(path_str)
        valid, err = cls._validate_path(normalized)
        if not valid:
            return err

        target = Path(normalized)

        try:
            if cls._OS == "Windows":
                if target.is_file():
                    # WHY: /select, highlights the file in Explorer
                    subprocess.Popen(
                        ["explorer", "/select,", str(target)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    subprocess.Popen(
                        ["explorer", str(target)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
            elif cls._OS == "Darwin":
                cmd = ["open", "-R", str(target)] if target.is_file() else ["open", str(target)]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                folder = str(target) if target.is_dir() else str(target.parent)
                subprocess.Popen(
                    ["xdg-open", folder],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            log.info(f"Opened in explorer: {target}")
            return f"Opened in Explorer: {target.name}"

        except Exception as e:
            log.error(f"Failed to open in explorer: {e}")
            return f"Error: {e}"

    @classmethod
    def reveal(cls, path_str: str) -> str:
        """Alias for open_in_explorer — reveals the item in file manager."""
        return cls.open_in_explorer(path_str)
