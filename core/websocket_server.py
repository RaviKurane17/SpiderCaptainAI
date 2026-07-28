"""
CAPTAIN AI — WebSocket Server
Bridges Python AI Core with React Frontend over local WebSocket channel.
"""
import asyncio
import json
import threading
import time
import psutil
import websockets
from utils.logger import log

class WebSocketUIBridge:
    def __init__(self, original_ui=None):
        self.original_ui = original_ui
        self.clients = set()
        self.on_text_command = None
        self.on_mic_toggle = None
        self._muted = False
        self.volume_muted = False
        self.state = "LISTENING"
        self.loop = None

    @property
    def muted(self) -> bool:
        return self._muted

    @muted.setter
    def muted(self, v: bool):
        self._muted = v
        self.broadcast({"type": "muted", "muted": v})
        # Keep client state consistent
        self.set_state("MUTED" if v else "LISTENING")
        if self.original_ui:
            self.original_ui.muted = v

    def write_log(self, message: str):
        # Parse who and text to map to React's dynamic structures
        who = "SYSTEM"
        text = message
        role = "system"
        if message.startswith("You:"):
            who = "YOU"
            text = message[4:].strip()
            role = "user"
        elif message.startswith("Captain:"):
            who = "CAPTAIN"
            text = message[8:].strip()
            role = "ai"
        elif message.startswith("ERR:"):
            who = "SYSTEM"
            text = message[4:].strip()
            role = "error"
        
        import datetime
        import time
        now = datetime.datetime.now().strftime("%I:%M %p")
        
        # Broadcast to legacy ActivityCard
        self.broadcast({
            "type": "log",
            "log": {
                "id": str(time.time()),
                "who": who,
                "text": text,
                "time": now
            }
        })
        
        # Save to Chat Panel History (Phase 4)
        if role in ["user", "ai"]:
            active_session = getattr(self, "active_chat_session", "default_session")
            try:
                from core.chat_manager import add_chat_message
                latency = 0.0
                if hasattr(self, 'perf_state') and role == 'ai':
                    latency = getattr(self, 'last_latency', 0.0)
                
                add_chat_message(active_session, role, text, 0, latency)
                
                # Broadcast the specific message event so the chat panel updates instantly
                self.broadcast({
                    "type": "new_chat_message",
                    "session_id": active_session,
                    "message": {
                        "role": role,
                        "content": text,
                        "timestamp": time.time()
                    }
                })
            except Exception as e:
                log.error(f"[WS SERVER] Chat log error: {e}")

        if self.original_ui:
            self.original_ui.write_log(message)

    def set_state(self, state: str):
        self.state = state
        self.broadcast({"type": "state", "state": state})
        if self.original_ui:
            self.original_ui.set_state(state)

    def set_network_status(self, is_online: bool):
        self.broadcast({"type": "network", "online": is_online})
        if self.original_ui:
            self.original_ui.set_network_status(is_online)

    def wait_for_api_key(self):
        if self.original_ui:
            self.original_ui.wait_for_api_key()

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if self.muted:
            self.set_state("MUTED")
        else:
            self.set_state("LISTENING")

    def broadcast(self, data):
        if not self.loop or not self.clients:
            return
        msg = json.dumps(data)
        asyncio.run_coroutine_threadsafe(self._send_to_all(msg), self.loop)

    async def _send_to_all(self, msg):
        if self.clients:
            # Gather message sends safely
            await asyncio.gather(*[client.send(msg) for client in list(self.clients)], return_exceptions=True)

# Global bridge instance
bridge_instance = None

# File scan cache — refreshed at most once every 30 seconds
_file_scan_cache: list | None = None
_file_scan_ts: float = 0.0
_FILE_SCAN_TTL: float = 30.0


async def ws_handler(websocket, path=None):
    global bridge_instance
    if bridge_instance:
        bridge_instance.clients.add(websocket)
        # Send current state snapshot so the reconnecting client stays in sync.
        # We send the *actual* current state — not hardcoded defaults.
        # This means if we're mid-command (THINKING/SPEAKING), the frontend
        # will restore to that state rather than flashing LISTENING.
        await websocket.send(json.dumps({
            "type": "state",
            "state": bridge_instance.state   # real current state
        }))
        await websocket.send(json.dumps({
            "type": "muted",
            "muted": bridge_instance.muted
        }))
        await websocket.send(json.dumps({
            "type": "volume_muted",
            "muted": getattr(bridge_instance, "volume_muted", False)
        }))
    
    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "command" and bridge_instance and bridge_instance.on_text_command:
                text = data.get("text", "")
                file_data = data.get("file")
                if file_data:
                    import os, base64
                    uploads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "memory", "uploads"))
                    os.makedirs(uploads_dir, exist_ok=True)
                    file_path = os.path.join(uploads_dir, file_data.get("name", "uploaded_file"))
                    try:
                        with open(file_path, "wb") as f:
                            f.write(base64.b64decode(file_data.get("data", "")))
                        # Ensure the text indicates the file is attached and gives the path to the AI
                        if not text.startswith("[Attached File:"):
                            text = f"[Attached File: {file_path}]\n" + text
                        else:
                            # Replace just the filename with the full path if the frontend already added it
                            text = text.replace(f"[Attached File: {file_data.get('name')}]", f"[Attached File: {file_path}]")
                    except Exception as e:
                        log.error(f"[WS SERVER] Error saving uploaded file: {e}")

                bridge_instance.on_text_command(text)
                
            elif msg_type == "mic_toggle" and bridge_instance:
                bridge_instance.muted = not bridge_instance.muted
                if bridge_instance.on_mic_toggle:
                    bridge_instance.on_mic_toggle()
                    
            elif msg_type == "volume_toggle" and bridge_instance:
                bridge_instance.volume_muted = not getattr(bridge_instance, "volume_muted", False)
                # Broadcast the state change to all clients
                bridge_instance.broadcast({
                    "type": "volume_muted",
                    "muted": bridge_instance.volume_muted
                })
                try:
                    from actions.computer_settings import volume_mute
                    volume_mute()
                except Exception as e:
                    log.error(f"[WS SERVER] Failed to toggle system volume: {e}")
                    
            elif msg_type == "brightness_toggle" and bridge_instance:
                if bridge_instance.original_ui:
                    bridge_instance.original_ui._toggle_brightness()
                    
            elif msg_type == "power_click" and bridge_instance:
                if bridge_instance.original_ui:
                    bridge_instance.original_ui._real_quit()
                else:
                    import os
                    os._exit(0)

            elif msg_type == "get_commands":
                try:
                    from core.command_manager import get_all_commands
                    cmds = await asyncio.to_thread(get_all_commands)
                    await websocket.send(json.dumps({
                        "type": "commands_data",
                        "data": cmds
                    }))
                except Exception as e:
                    log.warning(f"[WS SERVER] Error getting commands: {e}")

            elif msg_type == "get_command_history":
                try:
                    from core.command_manager import get_command_history
                    hist = await asyncio.to_thread(get_command_history)
                    await websocket.send(json.dumps({
                        "type": "command_history_data",
                        "data": hist
                    }))
                except Exception as e:
                    log.warning(f"[WS SERVER] Error getting command history: {e}")

            elif msg_type == "toggle_pin_command":
                try:
                    cmd_id = data.get("id")
                    is_pinned = data.get("is_pinned")
                    if cmd_id is not None and is_pinned is not None:
                        from core.command_manager import toggle_pin_command
                        await asyncio.to_thread(toggle_pin_command, cmd_id, is_pinned)
                except Exception as e:
                    log.warning(f"[WS SERVER] Error toggling pin command: {e}")

            elif msg_type == "get_memory":
                import os
                mem_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../memory/long_term.json"))
                def read_mem(path):
                    if os.path.exists(path):
                        with open(path, "r", encoding="utf-8") as f:
                            return json.load(f)
                    return {}
                try:
                    mem_data = await asyncio.to_thread(read_mem, mem_path)
                    await websocket.send(json.dumps({
                        "type": "memory_data",
                        "data": mem_data
                    }))
                except Exception as e:
                    log.warning(f"[WS SERVER] Error reading memory file: {e}")

            elif msg_type == "get_files":
                try:
                    from core.file_manager import list_directory
                    import os
                    # By default, use workspace root if no path provided
                    req_path = data.get("path")
                    if not req_path:
                        req_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                    
                    files = await asyncio.to_thread(list_directory, req_path)
                    await websocket.send(json.dumps({
                        "type": "files_data",
                        "path": req_path,
                        "files": files
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error in get_files: {e}")

            elif msg_type == "file_operation":
                try:
                    from core.file_manager import file_operation
                    op = data.get("operation")
                    source = data.get("source")
                    dest = data.get("dest")
                    result = await asyncio.to_thread(file_operation, op, source, dest)
                    await websocket.send(json.dumps({
                        "type": "file_op_result",
                        "operation": op,
                        "source": source,
                        "result": result
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error in file_op: {e}")

            elif msg_type == "get_file_preview":
                try:
                    from core.file_manager import get_file_preview
                    path = data.get("path")
                    preview = await asyncio.to_thread(get_file_preview, path)
                    await websocket.send(json.dumps({
                        "type": "file_preview_data",
                        "path": path,
                        "preview": preview
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error in get_file_preview: {e}")

            elif msg_type == "search_files":
                try:
                    from core.file_manager import search_files
                    import os
                    query = data.get("query", "")
                    root_dir = data.get("path") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                    results = await asyncio.to_thread(search_files, root_dir, query)
                    await websocket.send(json.dumps({
                        "type": "file_search_results",
                        "query": query,
                        "files": results
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error in search_files: {e}")

            elif msg_type == "get_workspace_state":
                try:
                    from core.workspace_manager import get_workspace_state
                    import os
                    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                    state = await asyncio.to_thread(get_workspace_state, root_dir)
                    await websocket.send(json.dumps({
                        "type": "workspace_state_data",
                        "data": state
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error in get_workspace_state: {e}")

            elif msg_type == "get_system_info":
                try:
                    from core.system_manager import get_drives, get_special_folders, get_recycle_bin_stats
                    drives = await asyncio.to_thread(get_drives)
                    folders = await asyncio.to_thread(get_special_folders)
                    recycle = await asyncio.to_thread(get_recycle_bin_stats)
                    await websocket.send(json.dumps({
                        "type": "system_info_data",
                        "drives": drives,
                        "special_folders": folders,
                        "recycle_bin": recycle
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error getting system info: {e}")
                    
            elif msg_type == "empty_recycle_bin":
                try:
                    from core.system_manager import empty_recycle_bin
                    result = await asyncio.to_thread(empty_recycle_bin)
                    await websocket.send(json.dumps({
                        "type": "recycle_bin_result",
                        "result": result
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error emptying recycle bin: {e}")
            
            # --- Chat Panel Endpoints ---
            
            elif msg_type == "get_chat_sessions":
                try:
                    from core.chat_manager import get_chat_sessions
                    sessions = await asyncio.to_thread(get_chat_sessions)
                    await websocket.send(json.dumps({
                        "type": "chat_sessions_data",
                        "sessions": sessions
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error getting chat sessions: {e}")
                    
            elif msg_type == "get_chat_messages":
                try:
                    session_id = data.get("session_id")
                    # Update active session in bridge so incoming voice logs go here
                    if bridge_instance:
                        bridge_instance.active_chat_session = session_id
                        
                    from core.chat_manager import get_chat_messages
                    msgs = await asyncio.to_thread(get_chat_messages, session_id)
                    await websocket.send(json.dumps({
                        "type": "chat_messages_data",
                        "session_id": session_id,
                        "messages": msgs
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error getting chat msgs: {e}")
                    
            elif msg_type == "create_chat_session":
                try:
                    session_id = data.get("session_id")
                    title = data.get("title", "New Chat")
                    from core.chat_manager import create_chat_session
                    res = await asyncio.to_thread(create_chat_session, session_id, title)
                    if res["success"] and bridge_instance:
                        bridge_instance.active_chat_session = session_id
                    await websocket.send(json.dumps({
                        "type": "chat_action_result",
                        "action": "create",
                        "result": res
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error creating chat: {e}")
                    
            elif msg_type == "delete_chat_session":
                try:
                    session_id = data.get("session_id")
                    from core.chat_manager import delete_chat_session
                    res = await asyncio.to_thread(delete_chat_session, session_id)
                    await websocket.send(json.dumps({
                        "type": "chat_action_result",
                        "action": "delete",
                        "result": res
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error deleting chat: {e}")

            elif msg_type == "toggle_pin_session":
                try:
                    session_id = data.get("session_id")
                    is_pinned = data.get("is_pinned")
                    from core.chat_manager import toggle_pin_session
                    res = await asyncio.to_thread(toggle_pin_session, session_id, is_pinned)
                    await websocket.send(json.dumps({
                        "type": "chat_action_result",
                        "action": "pin",
                        "result": res
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error pinning chat: {e}")

            elif msg_type == "send_chat_message":
                try:
                    session_id = data.get("session_id")
                    text = data.get("text")
                    if bridge_instance:
                        bridge_instance.active_chat_session = session_id
                        # Hand over text to Gemini
                        if bridge_instance.on_text_command:
                            bridge_instance.on_text_command(text)
                except Exception as e:
                    log.error(f"[WS SERVER] Error handling chat message: {e}")

            # --- Phase 6: Memory Panel Endpoints ---
            
            elif msg_type == "get_memory_stats":
                try:
                    from core.memory_manager import get_memory_stats
                    stats = await asyncio.to_thread(get_memory_stats)
                    await websocket.send(json.dumps({
                        "type": "memory_stats_data",
                        "stats": stats
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error getting memory stats: {e}")

            elif msg_type == "search_memories":
                try:
                    query = data.get("query", "")
                    category = data.get("category", "")
                    privacy = data.get("privacy", "ALL")
                    limit = data.get("limit", 50)
                    offset = data.get("offset", 0)
                    
                    from core.memory_manager import search_memories
                    results = await asyncio.to_thread(search_memories, query, category, privacy, limit, offset)
                    
                    await websocket.send(json.dumps({
                        "type": "memory_search_results",
                        "results": results,
                        "query": query,
                        "offset": offset
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error searching memories: {e}")

            elif msg_type == "delete_memory":
                try:
                    memory_id = data.get("memory_id")
                    from core.memory_manager import delete_memory
                    res = await asyncio.to_thread(delete_memory, memory_id)
                    await websocket.send(json.dumps({
                        "type": "memory_action_result",
                        "action": "delete",
                        "result": res
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error deleting memory: {e}")

            elif msg_type == "toggle_pin_memory":
                try:
                    memory_id = data.get("memory_id")
                    from core.memory_manager import toggle_pin_memory
                    res = await asyncio.to_thread(toggle_pin_memory, memory_id)
                    await websocket.send(json.dumps({
                        "type": "memory_action_result",
                        "action": "pin",
                        "result": res
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error pinning memory: {e}")

            elif msg_type == "add_test_memory":
                try:
                    from core.memory_manager import add_memory
                    import uuid
                    uid = str(uuid.uuid4())
                    res = await asyncio.to_thread(add_memory, uid, "Long-Term", "Test Memory", "This is a test generated from the UI.", "Custom")
                    await websocket.send(json.dumps({
                        "type": "memory_action_result",
                        "action": "add",
                        "result": res
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error adding memory: {e}")

            elif msg_type == "add_memory_direct":
                try:
                    title = data.get("title")
                    summary = data.get("summary")
                    category = data.get("category")
                    source = data.get("source", "Manual")
                    privacy = data.get("privacy", "Normal")
                    priority = data.get("priority", "Normal")
                    tags = data.get("tags", "").split(",") if data.get("tags") else []
                    
                    from core.memory_manager import add_memory
                    import uuid
                    uid = str(uuid.uuid4())
                    res = await asyncio.to_thread(add_memory, uid, "Long-Term", title, summary, category, tags, 0.8, privacy, source, None)
                    await websocket.send(json.dumps({
                        "type": "memory_action_result",
                        "action": "add",
                        "result": res
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error adding memory directly: {e}")

            elif msg_type == "edit_memory_direct":
                try:
                    memory_id = data.get("id")
                    title = data.get("title")
                    summary = data.get("summary")
                    category = data.get("category")
                    privacy = data.get("privacy", "Normal")
                    priority = data.get("priority", "Normal")
                    tags = data.get("tags", "").split(",") if data.get("tags") else []
                    
                    from core.memory_manager import update_memory
                    res = await asyncio.to_thread(update_memory, memory_id, title, summary, category, tags, priority, privacy)
                    await websocket.send(json.dumps({
                        "type": "memory_action_result",
                        "action": "edit",
                        "result": res
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error editing memory directly: {e}")

            # --- Phase 7: Tools Panel Endpoints ---
            
            elif msg_type == "get_tools_stats":
                try:
                    from core.tool_manager import get_tools_stats
                    stats = await asyncio.to_thread(get_tools_stats)
                    await websocket.send(json.dumps({
                        "type": "tools_stats_data",
                        "stats": stats
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error getting tools stats: {e}")

            elif msg_type == "search_tools":
                try:
                    query = data.get("query", "")
                    category = data.get("category", "ALL")
                    status = data.get("status", "ALL")
                    limit = data.get("limit", 50)
                    offset = data.get("offset", 0)
                    
                    from core.tool_manager import search_tools
                    results = await asyncio.to_thread(search_tools, query, category, status, limit, offset)
                    
                    await websocket.send(json.dumps({
                        "type": "tools_search_results",
                        "results": results,
                        "query": query,
                        "offset": offset
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error searching tools: {e}")

            elif msg_type in ["tool_action_run", "tool_action_stop"]:
                try:
                    tool_id = data.get("tool_id")
                    enable = msg_type == "tool_action_run"
                    from core.tool_manager import toggle_tool_status
                    res = await asyncio.to_thread(toggle_tool_status, tool_id, enable)
                    await websocket.send(json.dumps({
                        "type": "tool_action_result",
                        "action": "status_toggle",
                        "result": res
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error toggling tool status: {e}")

            elif msg_type == "tool_action_pin":
                try:
                    tool_id = data.get("tool_id")
                    from core.tool_manager import toggle_pin_tool
                    res = await asyncio.to_thread(toggle_pin_tool, tool_id)
                    await websocket.send(json.dumps({
                        "type": "tool_action_result",
                        "action": "pin",
                        "result": res
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error pinning tool: {e}")

            elif msg_type == "tool_action_health":
                try:
                    tool_id = data.get("tool_id")
                    from core.tool_manager import run_health_check
                    res = await asyncio.to_thread(run_health_check, tool_id)
                    await websocket.send(json.dumps({
                        "type": "tool_action_result",
                        "action": "health",
                        "result": res
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error running tool health check: {e}")

            elif msg_type == "update_tool_permission":
                try:
                    tool_id = data.get("tool_id")
                    permission = data.get("permission")
                    from core.tool_manager import update_tool_permission
                    res = await asyncio.to_thread(update_tool_permission, tool_id, permission)
                    await websocket.send(json.dumps({
                        "type": "tool_action_result",
                        "action": "update_permission",
                        "result": res
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error updating tool permission: {e}")

            # --- Phase 8: Settings Panel Endpoints ---

            elif msg_type == "get_all_settings":
                try:
                    from core.settings_manager import get_all_settings, get_api_providers_status
                    settings = await asyncio.to_thread(get_all_settings)
                    
                    # Mask security hash before sending to UI
                    if "security_hash" in settings:
                        settings["security_hash"] = "********" if settings["security_hash"] else ""
                        
                    api_status = await asyncio.to_thread(get_api_providers_status)
                    await websocket.send(json.dumps({
                        "type": "all_settings_data",
                        "settings": settings,
                        "api_status": api_status
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error getting settings: {e}")
                    
            elif msg_type == "update_setting":
                try:
                    key = data.get("key")
                    val = data.get("value")
                    from core.settings_manager import update_setting
                    res = await asyncio.to_thread(update_setting, key, val)
                    await websocket.send(json.dumps({
                        "type": "setting_updated",
                        "result": res
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error updating setting: {e}")

            elif msg_type == "verify_lock":
                try:
                    pin = data.get("pin", "")
                    from core.settings_manager import get_all_settings
                    settings = await asyncio.to_thread(get_all_settings)
                    saved_hash = settings.get("security_hash", "")
                    
                    if pin == saved_hash or not saved_hash:
                        await websocket.send(json.dumps({
                            "type": "lock_verified",
                            "success": True
                        }))
                    else:
                        await websocket.send(json.dumps({
                            "type": "lock_verified",
                            "success": False
                        }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error verifying lock: {e}")
                    
            elif msg_type == "set_api_key":
                try:
                    provider = data.get("provider")
                    api_key = data.get("api_key")
                    from core.settings_manager import set_api_key, get_api_providers_status
                    await asyncio.to_thread(set_api_key, provider, api_key)
                    
                    # Return fresh status
                    api_status = await asyncio.to_thread(get_api_providers_status)
                    await websocket.send(json.dumps({
                        "type": "api_key_updated",
                        "api_status": api_status
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error setting API key: {e}")
                    
            elif msg_type == "factory_reset":
                try:
                    from core.settings_manager import factory_reset
                    res = await asyncio.to_thread(factory_reset)
                    await websocket.send(json.dumps({"type": "action_result", "action": "factory_reset", "result": res}))
                except Exception as e:
                    log.error(f"[WS SERVER] Error factory reset: {e}")

            elif msg_type == "export_config":
                try:
                    from core.settings_manager import export_config
                    res = await asyncio.to_thread(export_config)
                    await websocket.send(json.dumps({"type": "action_result", "action": "export_config", "result": res}))
                except Exception as e:
                    log.error(f"[WS SERVER] Error export config: {e}")

            elif msg_type == "import_config":
                try:
                    from core.settings_manager import import_config
                    res = await asyncio.to_thread(import_config)
                    await websocket.send(json.dumps({"type": "action_result", "action": "import_config", "result": res}))
                except Exception as e:
                    log.error(f"[WS SERVER] Error import config: {e}")

            elif msg_type == "get_reminders":
                try:
                    import os
                    mem_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../memory/reminders.json"))
                    def read_reminders(path):
                        if os.path.exists(path):
                            with open(path, "r", encoding="utf-8") as f:
                                return json.load(f)
                        return []
                    reminders_data = await asyncio.to_thread(read_reminders, mem_path)
                    await websocket.send(json.dumps({
                        "type": "reminders_data",
                        "data": reminders_data
                    }))
                except Exception as e:
                    log.warning(f"[WS SERVER] Error reading reminders file: {e}")

            elif msg_type == "delete_reminder":
                try:
                    import os
                    reminder_id = data.get("id")
                    mem_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../memory/reminders.json"))
                    def delete_rem(path, r_id):
                        if not os.path.exists(path): return []
                        with open(path, "r", encoding="utf-8") as f:
                            rems = json.load(f)
                        rems = [r for r in rems if r.get("id") != r_id]
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(rems, f, indent=2)
                        return rems
                    reminders_data = await asyncio.to_thread(delete_rem, mem_path, reminder_id)
                    await websocket.send(json.dumps({
                        "type": "reminders_data",
                        "data": reminders_data
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error deleting reminder: {e}")

            elif msg_type == "edit_reminder":
                try:
                    import os
                    mem_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../memory/reminders.json"))
                    edited_task = data.get("task")
                    def edit_rem(path, task):
                        if not os.path.exists(path): return []
                        with open(path, "r", encoding="utf-8") as f:
                            rems = json.load(f)
                        for i, r in enumerate(rems):
                            if r.get("id") == task.get("id"):
                                rems[i] = task
                                break
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(rems, f, indent=2)
                        return rems
                    reminders_data = await asyncio.to_thread(edit_rem, mem_path, edited_task)
                    await websocket.send(json.dumps({
                        "type": "reminders_data",
                        "data": reminders_data
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error editing reminder: {e}")

            elif msg_type == "add_reminder":
                try:
                    import os
                    mem_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../memory/reminders.json"))
                    new_task = data.get("task")
                    def add_rem(path, task):
                        rems = []
                        if os.path.exists(path):
                            with open(path, "r", encoding="utf-8") as f:
                                rems = json.load(f)
                        rems.append(task)
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(rems, f, indent=2)
                        return rems
                    reminders_data = await asyncio.to_thread(add_rem, mem_path, new_task)
                    await websocket.send(json.dumps({
                        "type": "reminders_data",
                        "data": reminders_data
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error adding reminder: {e}")

            elif msg_type == "ping":
                try:
                    await websocket.send(json.dumps({
                        "type": "pong",
                        "timestamp": data.get("timestamp")
                    }))
                except Exception as e:
                    pass

            elif msg_type == "create_project":
                try:
                    from core.workspace_manager import create_project
                    import os
                    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                    name = data.get("name")
                    result = await asyncio.to_thread(create_project, root_dir, name)
                    await websocket.send(json.dumps({
                        "type": "project_action_result",
                        "action": "create",
                        "result": result
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error creating project: {e}")

            elif msg_type == "archive_project":
                try:
                    from core.workspace_manager import archive_project
                    name = data.get("name")
                    result = await asyncio.to_thread(archive_project, name)
                    await websocket.send(json.dumps({
                        "type": "project_action_result",
                        "action": "archive",
                        "result": result
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error archiving project: {e}")
                    
            elif msg_type == "get_dev_info":
                try:
                    from core.dev_tools import get_dev_info
                    path = data.get("path")
                    info = await asyncio.to_thread(get_dev_info, path)
                    await websocket.send(json.dumps({
                        "type": "dev_info_data",
                        "path": path,
                        "info": info
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error in get_dev_info: {e}")

            elif msg_type == "execute_dev_command":
                try:
                    from core.dev_tools import execute_dev_command
                    command = data.get("command")
                    path = data.get("path")
                    result = await asyncio.to_thread(execute_dev_command, command, path)
                    await websocket.send(json.dumps({
                        "type": "dev_command_result",
                        "command": command,
                        "result": result
                    }))
                except Exception as e:
                    log.error(f"[WS SERVER] Error executing dev command: {e}")

            elif msg_type == "get_settings":
                from utils.config import _read_json_config
                try:
                    config_data = await asyncio.to_thread(_read_json_config)
                    key = config_data.get("gemini_api_key", "")
                    masked_key = key[:6] + "..." + key[-4:] if len(key) > 10 else key
                    await websocket.send(json.dumps({
                        "type": "settings_data",
                        "api_key": masked_key,
                        "voice": config_data.get("voice", "Aoede")
                    }))
                except Exception as e:
                    log.warning(f"[WS SERVER] Error get settings: {e}")

            elif msg_type == "save_settings":
                api_key = data.get("api_key", "").strip()
                voice = data.get("voice", "").strip()
                
                from utils.config import ensure_config_dir, API_CONFIG_PATH, _read_json_config, _config_lock
                ensure_config_dir()
                def write_settings(key, vc):
                    with _config_lock:
                        config_data = _read_json_config()
                        if key and not key.endswith("..."):
                            config_data["gemini_api_key"] = key
                            import os
                            os.environ["GEMINI_API_KEY"] = key
                        if vc:
                            config_data["voice"] = vc
                            import os
                            os.environ["CAPTAIN_VOICE"] = vc
                        API_CONFIG_PATH.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
                try:
                    await asyncio.to_thread(write_settings, api_key, voice)
                    
                    await websocket.send(json.dumps({
                        "type": "save_settings_result",
                        "success": True,
                        "voice": voice or config_data.get("voice", "Aoede")
                    }))
                except Exception as e:
                    log.warning(f"[WS SERVER] Error saving settings: {e}")
                    await websocket.send(json.dumps({
                        "type": "save_settings_result",
                        "success": False,
                        "error": str(e)
                    }))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if bridge_instance:
            bridge_instance.clients.discard(websocket)

# Thread-count is expensive (iterates all processes). Cache it and refresh every 10s.
_cached_threads: int = 0
_cached_threads_ts: float = 0.0
_THREADS_TTL: float = 10.0


def _collect_thread_count() -> int:
    """Run in a thread via asyncio.to_thread — never blocks the event loop."""
    try:
        return sum(
            p.info["num_threads"] or 0
            for p in psutil.process_iter(["num_threads"])
        )
    except Exception:
        return _cached_threads  # return stale value rather than lying


async def metrics_broadcaster():
    global bridge_instance, _cached_threads, _cached_threads_ts
    log.info("[WS SERVER] metrics_broadcaster task starting...")
    _boot_time = psutil.boot_time()   # read once; boot time never changes
    _last_net_io = psutil.net_io_counters()

    while True:
        await asyncio.sleep(3.0)
        if not bridge_instance or not bridge_instance.clients:
            continue

        try:
            # Gather fresh metrics locally instead of relying on the old Tkinter widget
            cpu  = psutil.cpu_percent(interval=None)
            mem  = psutil.virtual_memory().percent
            gpu  = 0
            disk = psutil.disk_usage("/").percent

            uptime_s = time.time() - _boot_time
            h, rem   = divmod(int(uptime_s), 3600)
            m, s     = divmod(rem, 60)
            uptime_str = f"{h}h {m}m {s}s"

            processes_count = len(psutil.pids())

            now = time.monotonic()
            if (now - _cached_threads_ts) > _THREADS_TTL:
                _cached_threads    = await asyncio.to_thread(_collect_thread_count)
                _cached_threads_ts = now

            current_net_io = psutil.net_io_counters()
            bytes_recv = current_net_io.bytes_recv - _last_net_io.bytes_recv
            bytes_sent = current_net_io.bytes_sent - _last_net_io.bytes_sent
            _last_net_io = current_net_io

            down_rate = int(bytes_recv / 1024 / 3.0)
            up_rate   = int(bytes_sent / 1024 / 3.0)
            net_str   = f"↓ {down_rate} KB/s   ↑ {up_rate} KB/s"

            bridge_instance.broadcast({
                "type": "metrics",
                "cpu": cpu, "ram": mem, "gpu": gpu, "disk": disk,
                "uptime": uptime_str, "processes": str(processes_count),
                "threads": f"{_cached_threads:,}", "network": net_str,
            })
        except Exception as exc:
            log.warning(f"[WS SERVER] Error in metrics loop: {exc}")

async def ws_main():
    global bridge_instance
    stop_signal = asyncio.Event()
    async with websockets.serve(ws_handler, "127.0.0.1", 8765):
        log.info("[WS SERVER] WebSocket Server listening on ws://127.0.0.1:8765")
        asyncio.create_task(metrics_broadcaster())
        await stop_signal.wait()   # blocks until stop() is called; replaces asyncio.Future()

def start_ws_server():
    global bridge_instance
    loop = asyncio.new_event_loop()
    bridge_instance.loop = loop
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(ws_main())
    except Exception as exc:
        log.error(f"[WS SERVER] Error in server event loop: {exc}")

def init_bridge(original_ui=None):
    global bridge_instance
    bridge_instance = WebSocketUIBridge(original_ui)
    
    t = threading.Thread(target=start_ws_server, daemon=True)
    t.start()
    return bridge_instance
