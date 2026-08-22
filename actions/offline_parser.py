import re
import datetime
from actions.computer_settings import computer_settings


def _media_control(action, seconds=20):
    try:
        from actions.browser_agent import get_browser_manager, _PLAYWRIGHT_AVAILABLE
        if _PLAYWRIGHT_AVAILABLE:
            manager = get_browser_manager()
            v = "document.querySelector('video')"
            if action == "play_pause":
                manager.execute_js(f"if(!{v}.paused){{{v}.pause();}}else{{{v}.play();}}")
                return "Toggled media playback."
            elif action == "next":
                manager.execute_js("document.querySelector('.ytp-next-button').click()")
                return "Skipping to next."
            elif action == "previous":
                manager.execute_js("window.history.back()")
                return "Going back."
            elif action == "seek_forward":
                manager.execute_js(f"{v}.currentTime += {seconds}")
                return f"Skipped forward {seconds} seconds."
            elif action == "seek_backward":
                manager.execute_js(f"{v}.currentTime -= {seconds}")
                return f"Skipped backward {seconds} seconds."
    except Exception:
        pass
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        if action == "play_pause":
            pyautogui.press("playpause")
            return "Toggled media playback."
        elif action == "next":
            pyautogui.press("nexttrack")
            return "Skipping to next."
        elif action == "previous":
            pyautogui.press("prevtrack")
            return "Going back."
    except Exception:
        pass
    return "Media control unavailable offline."


def parse_and_execute_offline(text, player=None):
    text = text.lower().strip()
    if not text:
        return "Speak or type something, sir."

    # 1. Volume
    if "volume" in text or "vol" in text:
        if "mute" in text:
            computer_settings({"action": "mute"}, player=player)
            return "Volume muted."
        if "unmute" in text:
            computer_settings({"action": "unmute"}, player=player)
            return "Volume unmuted."
        if "up" in text or "increase" in text or "louder" in text:
            computer_settings({"action": "volume_up"}, player=player)
            return "Volume increased."
        if "down" in text or "decrease" in text or "lower" in text or "quiet" in text:
            computer_settings({"action": "volume_down"}, player=player)
            return "Volume decreased."
        m = re.search(r"(?:volume|vol)[\w\s]*?(\d+)|(\d+)\s*%", text)
        if m:
            val = max(0, min(100, int(next(g for g in m.groups() if g is not None))))
            computer_settings({"action": "volume_set", "value": val}, player=player)
            return f"Volume set to {val} percent."

    # 2. Brightness
    if "brightness" in text:
        if "up" in text or "increase" in text or "brighter" in text:
            computer_settings({"action": "brightness_up"}, player=player)
            return "Brightness increased."
        if "down" in text or "decrease" in text or "dim" in text:
            computer_settings({"action": "brightness_down"}, player=player)
            return "Brightness decreased."
        m = re.search(r"(\d+)", text)
        if m:
            val = max(0, min(100, int(m.group(1))))
            computer_settings({"action": "brightness_set", "value": val}, player=player)
            return f"Brightness set to {val} percent."

    # 3. System Stats
    if "battery" in text or "charging" in text:
        return computer_settings({"action": "battery_status"}, player=player) or "Battery status retrieved."
    if "cpu" in text or "ram" in text or "system usage" in text:
        return computer_settings({"action": "system_usage"}, player=player) or "System usage retrieved."

    # 4. Utilities
    if "screenshot" in text:
        computer_settings({"action": "screenshot"}, player=player)
        return "Screenshot taken."
    if "lock" in text and ("screen" in text or "computer" in text or "pc" in text):
        computer_settings({"action": "lock_screen", "confirmed": "yes"}, player=player)
        return "Locking the computer."
    if ("recycle bin" in text or "trash" in text) and ("empty" in text or "clean" in text):
        return computer_settings({"action": "empty_recycle_bin", "confirmed": "yes"}, player=player) or "Recycle bin emptied."
    if "bluetooth" in text:
        if "on" in text or "enable" in text:
            return computer_settings({"action": "enable_bluetooth"}, player=player) or "Bluetooth enabled."
        if "off" in text or "disable" in text:
            return computer_settings({"action": "disable_bluetooth"}, player=player) or "Bluetooth disabled."

    # 5. Media Controls
    if "pause" in text and "unpause" not in text:
        return _media_control("play_pause")
    if "unpause" in text or ("resume" in text and ("music" in text or "video" in text)):
        return _media_control("play_pause")
    if "next track" in text or "next song" in text or "skip song" in text:
        return _media_control("next")
    if "previous track" in text or "previous song" in text or "last song" in text:
        return _media_control("previous")
    m = re.search(r"skip (?:forward\s*)?(\d+)\s*(?:seconds?|secs?|s)\b", text)
    if m:
        return _media_control("seek_forward", int(m.group(1)))
    m = re.search(r"skip (?:backward|back)\s*(\d+)\s*(?:seconds?|secs?|s)\b", text)
    if m:
        return _media_control("seek_backward", int(m.group(1)))
    if "skip forward" in text:
        return _media_control("seek_forward", 20)
    if "skip backward" in text or "skip back" in text:
        return _media_control("seek_backward", 20)

    # 6. Keyboard Shortcuts & Clipboard
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        shortcuts = {
            "copy": ("ctrl", "c"), "paste": ("ctrl", "v"), "cut": ("ctrl", "x"),
            "undo": ("ctrl", "z"), "redo": ("ctrl", "y"), "select all": ("ctrl", "a"),
            "new tab": ("ctrl", "t"), "close tab": ("ctrl", "w"),
            "switch tab": ("ctrl", "tab"), "next tab": ("ctrl", "tab"),
            "switch window": ("alt", "tab"), "alt tab": ("alt", "tab"),
            "run dialog": ("win", "r"), "win r": ("win", "r"), "windows r": ("win", "r"),
            "task manager": ("ctrl", "shift", "esc"),
            "zoom in": ("ctrl", "+"), "zoom out": ("ctrl", "-"),
            "minimize": ("win", "down"), "maximize": ("win", "up"),
            "show desktop": ("win", "d"),
        }
        for phrase, keys in shortcuts.items():
            if phrase in text:
                pyautogui.hotkey(*keys)
                return f"Done."
        if "save" in text and "file" not in text and "search" not in text:
            pyautogui.hotkey("ctrl", "s")
            return "Saved."
        if "fullscreen" in text or "full screen" in text:
            pyautogui.press("f11")
            return "Toggled fullscreen."
        if "find" in text and "file" not in text:
            pyautogui.hotkey("ctrl", "f")
            return "Find opened."
        m = re.search(r"press\s+([\w\+\s]+)", text)
        if m:
            keys = [k.strip() for k in re.split(r"[\+\s]+", m.group(1).strip()) if k.strip()]
            if keys:
                pyautogui.hotkey(*keys)
                return f"Pressed {'+'.join(keys)}."
    except ImportError:
        pass

    # 7. Extended System Controls
    if "restart" in text and ("computer" in text or "pc" in text):
        computer_settings({"action": "restart"}, player=player)
        return "Restarting computer."
    if "shut down" in text or "shutdown" in text or "power off" in text:
        computer_settings({"action": "shutdown"}, player=player)
        return "Shutting down computer."
    if "sleep" in text and ("display" in text or "screen" in text):
        computer_settings({"action": "sleep_display"}, player=player)
        return "Sleeping display."
    if "wifi" in text or "wi-fi" in text:
        if "on" in text or "enable" in text:
            return computer_settings({"action": "enable_wifi"}, player=player) or "WiFi enabled."
        if "off" in text or "disable" in text:
            return computer_settings({"action": "disable_wifi"}, player=player) or "WiFi disabled."
    if "dark mode" in text:
        if "on" in text or "enable" in text:
            return computer_settings({"action": "dark_mode_on"}, player=player) or "Dark mode on."
        if "off" in text or "disable" in text:
            return computer_settings({"action": "dark_mode_off"}, player=player) or "Dark mode off."
    if "list open windows" in text or "what is open" in text or "open windows" in text:
        return computer_settings({"action": "list_open_windows"}, player=player) or "Listed windows."
    if "read active window" in text or "read this" in text:
        return computer_settings({"action": "read_active_text"}, player=player) or "Reading window."

    # 8. File and Folder Controls
    m = re.search(r"search (?:for )?(?:file |folder )?(.+)", text)
    if m:
        from actions.file_controller import file_controller
        return file_controller({"action": "search", "name": m.group(1).strip()}, player=player, speak=None) or "Search done."
    m = re.search(r"open (?:the )?(.+) folder", text) or re.search(r"open folder (.+)", text)
    if m:
        from actions.file_controller import file_controller
        return file_controller({"action": "open_folder", "name": m.group(1).strip()}, player=player, speak=None) or "Folder opened."
    m = re.search(r"open (?:the )?file (.+)", text)
    if m:
        from actions.file_controller import file_controller
        return file_controller({"action": "open", "name": m.group(1).strip()}, player=player, speak=None) or "File opened."

    # 9. Open / Close App
    m = re.search(r"(?:open|launch|start)\s+(.+)", text)
    if m:
        app = re.sub(r"\b(please|the|program|app)\b", "", m.group(1)).strip()
        from actions.open_app import open_app
        return open_app({"app_name": app}, player=player) or f"Opening {app}."
    m = re.search(r"(?:close|kill|quit|exit)\s+(.+)", text)
    if m:
        app = re.sub(r"\b(please|the|program|app)\b", "", m.group(1)).strip()
        if app in ("captain", "assistant", "yourself"):
            computer_settings({"action": "shutdown"}, player=player)
            return "Goodbye, sir."
        return computer_settings({"action": "kill_process", "app_name": app}, player=player) or f"Closed {app}."

    # 10. Greetings
    if set(text.split()) & {"hello", "hi", "hey", "captain", "yo"}:
        return "I am Captain, sir. Operating offline. How can I help you locally?"

    # 11. Lightweight Conversational Fallback
    if "time" in text:
        return f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}."
    if "date" in text or ("what" in text and "day" in text):
        return f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."
    if "how are you" in text:
        return "Fully operational offline, sir."
    if "who are you" in text or "what are you" in text:
        return "I am Captain, your personal AI assistant. Currently in offline mode."
    if "thank" in text:
        return "You're welcome, sir."

    return "I am offline, sir, and could not find a matching command. Connect to the internet for full AI capabilities."
