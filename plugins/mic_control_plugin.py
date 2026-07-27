"""
CAPTAIN AI Plugin — Mic Control
Allows the AI to mute itself or stop listening when commanded by the user.
"""

def _handler(parameters: dict, player=None, speak=None) -> str:
    try:
        from core.websocket_server import bridge_instance
        if bridge_instance:
            bridge_instance.muted = True
            if bridge_instance.on_mic_toggle:
                bridge_instance.on_mic_toggle()
            
            # Ensure the UI gets the update
            bridge_instance.broadcast({
                "type": "muted",
                "muted": True
            })
            
            return "Microphone has been muted. I will stop listening now."
        else:
            return "Failed to mute. WebSocket bridge is offline."
    except Exception as e:
        return f"Failed to mute microphone: {e}"

def register() -> dict:
    return {
        "name": "mute_microphone",
        "description": (
            "Mutes the assistant's microphone so it stops listening to the user. "
            "Call this immediately and silently when the user says 'mute yourself', 'stop listening', 'silent', 'tumara mic mute karo', etc."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": _handler,
        "author": "Captain AI Core",
        "version": "1.0.0"
    }
