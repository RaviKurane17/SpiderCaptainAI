"""
CAPTAIN AI Plugin — UI Navigator
Allows the AI to switch tabs and pages in the frontend UI.
"""

def _handler(parameters: dict, player=None, speak=None) -> str:
    page = parameters.get("page", "").upper()
    
    # Valid pages based on index.tsx
    valid_pages = ["HOME", "COMMANDS", "FILES", "CHAT", "MEMORY", "TOOLS", "SETTINGS"]
    
    if page not in valid_pages:
        return f"Failed to navigate. Invalid page '{page}'. Valid pages are: {', '.join(valid_pages)}"
        
    try:
        from core.websocket_server import bridge_instance
        if bridge_instance:
            bridge_instance.broadcast({
                "type": "navigate",
                "page": page
            })
            return f"Successfully navigated the UI to {page}."
        else:
            return "Failed to navigate. WebSocket bridge is offline."
    except Exception as e:
        return f"Failed to navigate: {e}"

def register() -> dict:
    return {
        "name": "navigate_ui",
        "description": (
            "Navigates the user's dashboard UI to a specific page/tab. "
            "Use this when the user asks to 'go to chat', 'open settings', 'show me the dashboard', etc."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "page": {
                    "type": "STRING",
                    "description": "The name of the page to navigate to. MUST be one of: HOME, COMMANDS, FILES, CHAT, MEMORY, TOOLS, SETTINGS. (Use HOME for 'dashboard')"
                }
            },
            "required": ["page"]
        },
        "handler": _handler,
        "author": "Captain AI Core",
        "version": "1.0.0"
    }
