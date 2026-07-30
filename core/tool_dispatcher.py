import asyncio
import time as _time
from utils.logger import log
from utils import analytics as _analytics
from plugins import discover_plugins

TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": (
            "Opens any application on the computer. "
            "Use this whenever the user asks to open, launch, or start any app, "
            "website, or program. Always call this tool — never just say you opened it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": "Searches the web for any information.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":  {"type": "STRING", "description": "Search query"},
                "mode":   {"type": "STRING", "description": "search (default) or compare"},
                "items":  {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare"},
                "aspect": {"type": "STRING", "description": "price | specs | reviews"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "weather_report",
        "description": "Gives the weather report to user",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends a text message via WhatsApp, Telegram, or other messaging platform.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Recipient contact name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform":     {"type": "STRING", "description": "Platform: WhatsApp, Telegram, etc."}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time":    {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": (
            "Controls YouTube. Use for: playing videos, summarizing a video's content, "
            "getting video info, or showing trending videos."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"},
                "query":  {"type": "STRING", "description": "Search query for play action"},
                "save":   {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
                "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"},
                "url":    {"type": "STRING", "description": "Video URL for get_info action"},
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures and analyzes the screen or webcam image. "
            "MUST be called when user asks what is on screen, what you see, "
            "analyze my screen, look at camera, etc. "
            "You have NO visual ability without this tool. "
            "After calling this tool, stay SILENT — the vision module speaks directly."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text":  {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": (
            "Controls the computer: volume, brightness, window management, keyboard shortcuts, "
            "typing text on screen, closing apps, kill processes, empty recycle bin, battery status, "
            "system usage (CPU/RAM), Bluetooth, list open windows, read active window text, fullscreen, dark mode, WiFi, restart, shutdown, "
            "scrolling, tab management, zoom, screenshots, lock screen, refresh/reload page. "
            "Use for ANY single computer control command. NEVER route to agent_task."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "The action to perform (e.g., volume_set, brightness_set, list_open_windows, read_active_text, volume_up, sleep_display, battery_status, system_usage, empty_recycle_bin, kill_process, enable_bluetooth, disable_bluetooth)"},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value":       {"type": "STRING", "description": "Optional value: volume/brightness percentage (0-100), text to type, etc."},
                "app_name":    {"type": "STRING", "description": "The name of the application to kill or focus"}
            },
            "required": []
        }
    },

    {
        "name": "file_controller",
        "description": (
            "Manages files and folders. Actions: list, create_file, create_folder, delete, move, copy, rename, read, write, "
            "search, open, open_folder, reveal, find, largest, disk_usage, organize_desktop, info, rebuild_index, index_stats, benchmark. "
            "For 'search' and 'open': set 'name' to the search term. Optionally set 'drive' to a letter like C, D, F to limit search to that drive. "
            "Set 'search_type' to 'file' or 'folder' to filter results. "
            "For 'open': if only 1 result is found, the file/folder is opened automatically. If multiple matches exist, a list is shown for the user to choose. "
            "Use 'open_folder' to explicitly search for and open a folder. "
            "Use 'reveal' to open the parent folder and highlight the item. "
            "Use 'rebuild_index' to force re-scan of drives for faster future searches. "
            "Use 'benchmark' to run a speed test across all search providers for a given query."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | create_file | create_folder | delete | move | copy | rename | read | write | search | open | open_folder | reveal | find | largest | disk_usage | organize_desktop | info | rebuild_index | index_stats | benchmark"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home. For search/open with a drive, use the drive letter like C or D."},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File or folder name to search for / open"},
                "extension":   {"type": "STRING", "description": "File extension filter (e.g. .pdf, .java)"},
                "drive":       {"type": "STRING", "description": "Drive letter to search in (e.g. C, D, F). If omitted, searches all drives."},
                "search_type": {"type": "STRING", "description": "Filter: 'file' for files only, 'folder' for folders only. Omit for both."},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, list, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Image path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language desktop task"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": (
            "Writes, edits, explains, runs, or builds code files. "
            "IMPORTANT: This tool automatically opens the file in VS Code after writing or editing. "
            "Do NOT call open_app for VS Code when using code_helper — it is handled automatically."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the file"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do"},
                "language":     {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "agent_task",
        "description": (
            "Executes complex multi-step tasks requiring multiple different tools. "
            "Examples: 'research X and save to file', 'find and organize files'. "
            "DO NOT use for single commands. NEVER use for Steam/Epic — use game_updater."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal":     {"type": "STRING", "description": "Complete description of what to accomplish"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
                "text":        {"type": "STRING", "description": "Text to type or paste"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key":         {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction":   {"type": "STRING", "description": "up | down | left | right"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Seconds to wait"},
                "title":       {"type": "STRING",  "description": "Window title for focus_window"},
                "description": {"type": "STRING",  "description": "Element description for screen_find/screen_click"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path":        {"type": "STRING",  "description": "Save path for screenshot"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "shutdown_captain",
        "description": (
            "Shuts down the assistant completely. "
            "Call this when the user expresses intent to end the conversation, "
            "close the assistant, say goodbye, or stop Captain. "
            "The user can say this in ANY language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
    "name": "file_processor",
    "description": (
        "Processes any file that the user has uploaded or dropped onto the interface. "
        "Use this when the user refers to an uploaded file and wants an action on it. "
        "Supports: images (describe/ocr/resize/compress/convert), "
        "PDFs (summarize/extract_text/to_word), "
        "Word docs & text files (summarize/fix/reformat/translate), "
        "CSV/Excel (analyze/stats/filter/sort/convert), "
        "JSON/XML (validate/format/analyze), "
        "code files (explain/review/fix/optimize/run/document/test), "
        "audio (transcribe/trim/convert/info), "
        "video (trim/extract_audio/extract_frame/compress/transcribe/info), "
        "archives (list/extract), "
        "presentations (summarize/extract_text). "
        "ALWAYS call this tool when a file has been uploaded and the user gives a command about it. "
        "If the user's command is ambiguous, pick the most logical action for that file type."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {
                "type": "STRING",
                "description": "Full path to the uploaded file. Leave empty to use the currently uploaded file."
            },
            "action": {
                "type": "STRING",
                "description": (
                    "What to do with the file. Examples by type:\n"
                    "image: describe | ocr | resize | compress | convert | info\n"
                    "pdf: summarize | extract_text | to_word | info\n"
                    "docx/txt: summarize | fix | reformat | translate_hint | word_count | to_bullet\n"
                    "csv/excel: analyze | stats | filter | sort | convert | info\n"
                    "json: validate | format | analyze | to_csv\n"
                    "code: explain | review | fix | optimize | run | document | test\n"
                    "audio: transcribe | trim | convert | info\n"
                    "video: trim | extract_audio | extract_frame | compress | transcribe | info | convert\n"
                    "archive: list | extract\n"
                    "pptx: summarize | extract_text | analyze"
                )
            },
            "instruction": {
                "type": "STRING",
                "description": "Free-form instruction if action doesn't cover it. E.g. 'translate this to Turkish', 'find all email addresses'"
            },
            "format": {
                "type": "STRING",
                "description": "Target format for conversion. E.g. 'mp3', 'pdf', 'csv', 'png'"
            },
            "width":     {"type": "INTEGER", "description": "Target width for image resize"},
            "height":    {"type": "INTEGER", "description": "Target height for image resize"},
            "scale":     {"type": "NUMBER",  "description": "Scale factor for image resize (e.g. 0.5)"},
            "quality":   {"type": "INTEGER", "description": "Quality 1-100 for image/video compress"},
            "start":     {"type": "STRING",  "description": "Start time for trim: seconds or HH:MM:SS"},
            "end":       {"type": "STRING",  "description": "End time for trim: seconds or HH:MM:SS"},
            "timestamp": {"type": "STRING",  "description": "Timestamp for video frame extraction HH:MM:SS"},
            "column":    {"type": "STRING",  "description": "Column name for CSV filter/sort"},
            "value":     {"type": "STRING",  "description": "Filter value for CSV filter"},
            "condition": {"type": "STRING",  "description": "Filter condition: equals|contains|gt|lt"},
            "ascending": {"type": "BOOLEAN", "description": "Sort order for CSV sort (default: true)"},
            "save":      {"type": "BOOLEAN", "description": "Save result to file (default: true)"},
            "destination": {"type": "STRING", "description": "Output folder for archive extract"},
        },
        "required": []
    }
},
    {
        "name": "save_memory",
        "description": (
            "Save an important personal fact about the user to long-term memory. "
            "Call this silently whenever the user reveals something worth remembering: "
            "name, age, city, job, preferences, hobbies, relationships, projects, or future plans. "
            "Do NOT call for: weather, reminders, searches, or one-time commands. "
            "Do NOT announce that you are saving — just call it silently. "
            "Values must be in English regardless of the conversation language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": (
                        "identity — name, age, birthday, city, job, language, nationality | "
                        "preferences — favorite food/color/music/film/game/sport, hobbies | "
                        "projects — active projects, goals, things being built | "
                        "relationships — friends, family, partner, colleagues | "
                        "wishes — future plans, things to buy, travel dreams | "
                        "notes — habits, schedule, anything else worth remembering"
                    )
                },
                "key":   {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food, sister_name)"},
                "value": {"type": "STRING", "description": "Concise value in English (e.g. Fatih, pizza, older sister)"},
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "search_memory",
        "description": "Search the local vector database for past conversations and tasks. Call this when asked to recall past events or context.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "The search query."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "phone_agent",
        "description": "Sends commands to the user's Android phone. Use this to check phone battery, get phone location, search phone contacts, make calls from the phone, send SMS from the phone, send WhatsApp messages from the phone, open apps on the phone, go to the home screen (close apps) on the phone, control media volume, control screen brightness, set alarms on the phone, read the phone's recent notifications, lock the phone screen, take a screenshot, open the notification panel, toggle the flashlight (torch), toggle bluetooth, toggle wifi, check the phone's system info (storage/ram), read the phone's current screen content, trigger a loud siren (find phone), make the phone speak text (tts), play specific media/music, copy text to the phone clipboard, read recent SMS messages, read recent call logs, take a picture using the phone's camera, write a note on the phone, capture a vision screenshot (vision_capture), auto click on screen text (auto_click), auto scroll the screen (auto_scroll), auto type text (auto_type), unlock the phone screen (unlock_screen), reply to a notification (reply_notification), perform a fast web search on the phone (web_search), or read voice commands sent from the phone (read_voice_commands). IMPORTANT: Do NOT use the PC's send_message or open_app tools if the user specifies 'on my phone'.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "The action to perform on the phone (e.g., 'battery', 'call', 'sms', 'location', 'contact_search', 'whatsapp', 'open_app', 'home', 'volume', 'brightness', 'alarm', 'read_notifications', 'lock_screen', 'screenshot', 'open_notifications', 'torch', 'bluetooth', 'wifi', 'sys_info', 'read_screen', 'find_phone', 'speak', 'play_media', 'copy_to_phone', 'read_sms', 'read_calls', 'take_picture', 'write_note', 'vision_capture', 'auto_click', 'auto_scroll', 'auto_type', 'unlock_screen', 'reply_notification', 'web_search', 'read_voice_commands')"},
                "name": {"type": "STRING", "description": "Name of contact to search, App to open, Song to play, or Package Name for replying to notifications (e.g. 'whatsapp')"},
                "number": {"type": "STRING", "description": "Phone number to call or sms, or Notification Title (Sender Name) when replying to a notification"},
                "message": {"type": "STRING", "description": "Message to send via sms/whatsapp/notification reply, label for the alarm, text for TTS to speak, text to copy to clipboard, dictated text for a note, camera type ('front' or 'back'), text to auto click, text to auto type, direction to scroll ('up' or 'down'), or the lock screen PIN if not saved on the device."},
                "value": {"type": "INTEGER", "description": "Value for volume or brightness (0-100), or state for torch/bluetooth/wifi (1 for ON, 0 for OFF)"},
                "time": {"type": "STRING", "description": "Time for alarm in 24-hour HH:MM format (e.g., '07:30', '14:00')"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "computer_use",
        "description": "Performs intelligent GUI automation using screenshot analysis. Acts as an orchestration layer. Actions: click, double_click, right_click, move_mouse, drag, scroll, type, press_key, hotkey, wait, find_element, verify_element, describe_screen. Returns JSON with success/failure and reasons.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "click | double_click | right_click | move_mouse | drag | scroll | type | press_key | hotkey | wait | find_element | verify_element | describe_screen"},
                "target_description": {"type": "STRING", "description": "Natural language description of the UI element to interact with"},
                "text": {"type": "STRING", "description": "Text to type"},
                "keys": {"type": "STRING", "description": "Key or hotkey to press"},
                "x": {"type": "INTEGER", "description": "Optional explicit X coordinate (if not using vision)"},
                "y": {"type": "INTEGER", "description": "Optional explicit Y coordinate (if not using vision)"},
                "verify": {"type": "BOOLEAN", "description": "Capture a second screenshot to verify the action succeeded"},
                "verify_description": {"type": "STRING", "description": "Explicit description of the expected UI state after the action (e.g. 'Is the login dialog open?')"},
                "timeout": {"type": "NUMBER", "description": "Maximum time allowed for this automation in seconds."}
            },
            "required": ["action"]
        }
    }
]


_PLUGIN_HANDLERS: dict = {}   # name → handler function

def load_plugins():
    """Discover plugins and merge into TOOL_DECLARATIONS."""
    global _PLUGIN_HANDLERS
    try:
        plugins = discover_plugins()
        for plug in plugins:
            name = plug["name"]
            _PLUGIN_HANDLERS[name] = plug["handler"]
            TOOL_DECLARATIONS.append({
                "name":        name,
                "description": plug.get("description", f"Plugin: {name}"),
                "parameters":  plug.get("parameters", {"type": "OBJECT", "properties": {}}),
            })
            log.info(f"[Plugins] Registered tool: {name}")
    except Exception as e:
        log.warning(f"[Plugins] Failed to load: {e}")


async def execute_tool(fc, ui, speak_callback, speak_error_callback, perf_state) -> 'types.FunctionResponse':
    name = fc.name
    args = dict(fc.args or {})

    perf_state['tool_start'] = _time.perf_counter()
    perf_state['tool_active'] = True
    log.info(f"[CAPTAIN] 🔧 {name}  {args}")
    ui.set_state("THINKING")

    # Track analytics — fire-and-forget in executor so the disk write
    # in _save() never blocks the event loop between tool dispatch and
    # first audio. Zero impact on tool result or timing.
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, _analytics.track_tool, name)

    try:
        return await execute_tool_inner(fc, name, args, ui, speak_callback, speak_error_callback)
    finally:
        perf_state['tool_active'] = False
        perf_state['tool_end'] = _time.perf_counter()
        elapsed = perf_state['tool_end'] - perf_state['tool_start']
        log.info(f"[PERF] ⏱️ {name} executed in {elapsed:.2f}s")
        # Do NOT set LISTENING here — Gemini is about to stream the audio
        # response. Setting LISTENING now creates a flicker:
        #   THINKING → LISTENING (wrong) → SPEAKING → LISTENING
        # Instead let _play_audio / set_speaking handle the final transition.

async def execute_tool_inner(fc, name, args, ui, speak_callback, speak_error_callback):
    """Thin router: delegates save_memory inline, everything else to tool_handlers."""
    from google.genai import types
    if name == "save_memory":
        return await _do_save_memory(fc, args)

    from core.tool_handlers import dispatch_action
    result = await dispatch_action(name, args, ui, speak_callback, speak_error_callback)
    log.info(f"[CAPTAIN] 📤 {name} → {str(result)[:80]}")
    return types.FunctionResponse(
        id=fc.id, name=name,
        response={"result": result}
    )


async def _do_save_memory(fc, args):
    """Inline save_memory handler (no extra import round-trip needed)."""
    from google.genai import types
    from core import memory_manager
    import uuid
    category = args.get("category", "notes")
    key      = args.get("key", "")
    value    = args.get("value", "")
    if key and value:
        loop = asyncio.get_event_loop()
        memory_id = str(uuid.uuid4())
        await loop.run_in_executor(
            None,
            lambda: memory_manager.add_memory(
                memory_id=memory_id,
                layer="Long-Term",
                title=key,
                summary=value,
                category=category,
                tags=[key],
                source="AI Suggested"
            )
        )
        log.info(f"[Memory] save_memory: {category}/{key} = {value}")
    return types.FunctionResponse(
        id=fc.id, name=fc.name,
        response={"result": "ok", "silent": True}
    )