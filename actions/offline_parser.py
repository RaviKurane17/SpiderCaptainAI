import re
from actions.computer_settings import computer_settings

def parse_and_execute_offline(text: str, player=None) -> str:
    """Parses a text command in offline mode and maps it to system settings actions.
    
    Returns a response message to be spoken/shown.
    """
    text = text.lower().strip()
    if not text:
        return "Speak or type something, sir."

    # 1. Volume Controls
    if "volume" in text:
        if "up" in text or "increase" in text:
            computer_settings({"action": "volume_up"}, player=player)
            return "Volume increased."
        elif "down" in text or "decrease" in text:
            computer_settings({"action": "volume_down"}, player=player)
            return "Volume decreased."
        elif "mute" in text:
            computer_settings({"action": "mute"}, player=player)
            return "Volume muted."
        elif "unmute" in text:
            computer_settings({"action": "unmute"}, player=player)
            return "Volume unmuted."
        # Set volume percentage
        vol_match = re.search(r"(\d+)\s*%", text) or re.search(r"set volume to\s*(\d+)", text)
        if vol_match:
            val = int(vol_match.group(1))
            computer_settings({"action": "volume_set", "value": val}, player=player)
            return f"Volume set to {val} percent."

    # 2. Brightness Controls
    if "brightness" in text:
        if "up" in text or "increase" in text:
            computer_settings({"action": "brightness_up"}, player=player)
            return "Brightness increased."
        elif "down" in text or "decrease" in text:
            computer_settings({"action": "brightness_down"}, player=player)
            return "Brightness decreased."
        bright_match = re.search(r"(\d+)\s*%", text) or re.search(r"set brightness to\s*(\d+)", text)
        if bright_match:
            val = int(bright_match.group(1))
            computer_settings({"action": "brightness_set", "value": val}, player=player)
            return f"Brightness set to {val} percent."

    # 3. System stats
    if "battery" in text or "power" in text:
        return computer_settings({"action": "battery_status"}, player=player)
    
    if "cpu" in text or "ram" in text or "memory" in text or "system usage" in text:
        return computer_settings({"action": "system_usage"}, player=player)

    # 4. Utilities
    if "screenshot" in text:
        computer_settings({"action": "screenshot"}, player=player)
        return "Screenshot taken."

    if "lock" in text and ("screen" in text or "computer" in text):
        computer_settings({"action": "lock_screen", "confirmed": "yes"}, player=player)
        return "Locking the computer."

    if "recycle bin" in text and ("empty" in text or "clean" in text):
        return computer_settings({"action": "empty_recycle_bin", "confirmed": "yes"}, player=player)

    if "bluetooth" in text:
        if "enable" in text or "on" in text:
            return computer_settings({"action": "enable_bluetooth"}, player=player)
        elif "disable" in text or "off" in text:
            return computer_settings({"action": "disable_bluetooth"}, player=player)

    # 5. Open / Close App
    open_match = re.search(r"(?:open|launch|start)\s+(.+)", text)
    if open_match:
        app_name = open_match.group(1).strip()
        app_name = re.sub(r"\b(please|the|program|app)\b", "", app_name).strip()
        from actions.open_app import open_app
        res = open_app({"app_name": app_name}, player=player)
        return res or f"Opening {app_name}."

    close_match = re.search(r"(?:close|kill|quit|exit)\s+(.+)", text)
    if close_match:
        app_name = close_match.group(1).strip()
        app_name = re.sub(r"\b(please|the|program|app)\b", "", app_name).strip()
        if app_name in ("captain", "assistant", "yourself"):
            computer_settings({"action": "shutdown"}, player=player)
            return "Goodbye, sir."
        res = computer_settings({"action": "kill_process", "app_name": app_name}, player=player)
        return res

    # 6. Basic responses for offline greeting
    words = text.split()
    greetings = {"hello", "hi", "hii", "hiii", "hey", "heyy", "captain"}
    if any(w in greetings for w in words):
        return "I am Captain, sir. I am currently operating offline. How can I help you locally?"

    # 7. Fallback to local Ollama model if available
    ollama_res = _query_ollama(text)
    if ollama_res:
        return ollama_res

    return "I am offline, sir, and could not find a matching local command. Please check your connection."

def _query_ollama(prompt: str) -> str | None:
    import requests
    url = "http://127.0.0.1:11434/api/generate"
    payload = {
        "model": "qwen2.5-coder:7b",
        "prompt": (
            "You are CAPTAIN, Tony Stark's AI assistant. You are currently offline. "
            "Respond in a very concise, direct, helpful manner. "
            f"Question: {prompt}"
        ),
        "stream": False
        }
    try:
        response = requests.post(url, json=payload, timeout=45)
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception as e:
        print(f"[Ollama] Connection failed or model not ready: {e}")
    return None
