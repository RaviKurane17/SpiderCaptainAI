"""
CAPTAIN AI — Plugin System

Drop .py files into this folder to add custom tools.
Each plugin must define a `register()` function that returns a dict conforming to PluginManifest.
"""

import importlib
import sys
import traceback
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Any, Dict, List


@dataclass
class PluginManifest:
    name: str
    description: str
    handler: Callable
    parameters: Dict[str, Any] = field(default_factory=lambda: {"type": "OBJECT", "properties": {}, "required": []})
    author: str = "Unknown"
    version: str = "1.0.0"
    permissions: List[str] = field(default_factory=list)

_plugin_cache: List[PluginManifest] = []
_plugins_loaded: bool = False
_lock = threading.RLock()


def discover_plugins(force_reload: bool = False) -> List[Dict[str, Any]]:
    """
    Scans the plugins/ directory for .py files with a register() function.
    Returns a list of raw plugin dicts for the AI executor.
    Uses an in-memory cache to prevent redundant disk scanning.
    """
    global _plugins_loaded, _plugin_cache
    
    with _lock:
        if _plugins_loaded and not force_reload:
            return [vars(p) for p in _plugin_cache]
            
        plugins_dir = Path(__file__).parent
        loaded_manifests: List[PluginManifest] = []

        for py_file in sorted(plugins_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue

            module_name = f"plugins.{py_file.stem}"
            try:
                if module_name in sys.modules:
                    mod = importlib.reload(sys.modules[module_name])
                else:
                    mod = importlib.import_module(module_name)

                if not hasattr(mod, "register"):
                    print(f"[Plugins] ⚠️ {py_file.name} has no register() — skipped")
                    continue

                info = mod.register()
                
                # Validation
                if not isinstance(info, dict):
                    print(f"[Plugins] ⚠️ {py_file.name} register() returned invalid data type — skipped")
                    continue
                    
                if "name" not in info or "handler" not in info:
                    print(f"[Plugins] ⚠️ {py_file.name} missing 'name' or 'handler' — skipped")
                    continue
                    
                if not callable(info["handler"]):
                    print(f"[Plugins] ⚠️ {py_file.name} 'handler' is not callable — skipped")
                    continue

                # Ensure required keys exist gracefully
                info.setdefault("description", f"Plugin: {info['name']}")
                
                manifest = PluginManifest(
                    name=info["name"],
                    description=info["description"],
                    handler=info["handler"],
                    parameters=info.get("parameters", {"type": "OBJECT", "properties": {}, "required": []}),
                    author=info.get("author", "Unknown"),
                    version=info.get("version", "1.0.0"),
                    permissions=info.get("permissions", [])
                )

                loaded_manifests.append(manifest)
                print(f"[Plugins] ✅ Loaded: {manifest.name} v{manifest.version} by {manifest.author} ({py_file.name})")

            except Exception as e:
                print(f"[Plugins] ❌ Failed to load {py_file.name}: {e}")
                traceback.print_exc()

        _plugin_cache = loaded_manifests
        _plugins_loaded = True
        
        print(f"[Plugins] 📦 {len(_plugin_cache)} plugin(s) loaded safely")
        return [vars(p) for p in _plugin_cache]
