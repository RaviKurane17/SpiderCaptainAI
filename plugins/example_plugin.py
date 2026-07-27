"""
Example CAPTAIN Plugin — System Info

This plugin demonstrates how to create a custom tool for CAPTAIN AI.
It returns basic system info when called.
"""

import platform
import psutil


def _handler(parameters: dict, player=None, speak=None) -> str:
    """Handler function called when the tool is invoked."""
    detail = (parameters.get("detail") or "basic").lower()

    info_lines = [
        f"OS: {platform.system()} {platform.release()}",
        f"Machine: {platform.machine()}",
        f"Python: {platform.python_version()}",
        f"CPU Cores: {psutil.cpu_count(logical=False)} physical, {psutil.cpu_count()} logical",
    ]

    if detail == "full":
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        info_lines.extend([
            f"RAM: {mem.total / (1024**3):.1f} GB total, {mem.percent}% used",
            f"Disk: {disk.total / (1024**3):.0f} GB total, {disk.percent}% used",
            f"Boot Time: {psutil.boot_time()}",
        ])

    return "\\n".join(info_lines)


def register() -> dict:
    return {
        "name": "system_info",
        "description": (
            "Returns detailed system information about the computer. "
            "Use when the user asks about their system specs, hardware, or OS details."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "detail": {
                    "type": "STRING",
                    "description": "Level of detail: 'basic' or 'full' (default: basic)"
                }
            },
            "required": []
        },
        "handler": _handler,
        "author": "Captain AI Core",
        "version": "1.1.0",
        "permissions": ["system_read"]
    }
