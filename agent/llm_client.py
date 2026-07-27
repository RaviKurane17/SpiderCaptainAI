import threading
from typing import Any, Optional
import google.generativeai as genai
from utils.config import get_api_key

_configured = False
_lock = threading.Lock()
_models: dict[tuple[str, Optional[str]], Any] = {}

def _ensure_configured():
    global _configured
    if not _configured:
        with _lock:
            if not _configured:
                api_key = get_api_key()
                if not api_key:
                    raise ValueError("Gemini API key not found in configuration.")
                genai.configure(api_key=api_key)
                _configured = True

def get_model(model_name: str = "gemini-2.5-flash", system_instruction: Optional[str] = None) -> Any:
    """
    Returns a configured Gemini GenerativeModel instance.
    Utilizes a thread-safe singleton pattern and caches models to avoid repeated instantiation.
    """
    _ensure_configured()
    key = (model_name, system_instruction)
    
    if key not in _models:
        with _lock:
            if key not in _models:
                if system_instruction:
                    _models[key] = genai.GenerativeModel(model_name=model_name, system_instruction=system_instruction)
                else:
                    _models[key] = genai.GenerativeModel(model_name=model_name)
    
    return _models[key]
