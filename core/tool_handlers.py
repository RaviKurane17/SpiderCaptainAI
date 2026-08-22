"""
tool_handlers.py — Pure async execution handlers for every Captain tool.
Imported by tool_dispatcher.execute_tool_inner().
"""
import asyncio
import traceback
import threading

from utils.logger import log
from utils.concurrency import run_in_background


async def handle_save_memory(fc, args, memory_fn):
    """Save a key/value pair to long-term memory."""
    from google.genai import types
    category = args.get("category", "notes")
    key      = args.get("key", "")
    value    = args.get("value", "")
    if key and value:
        memory_fn({category: {key: {"value": value}}})
        log.info(f"[Memory] save_memory: {category}/{key} = {value}")
    return types.FunctionResponse(
        id=fc.id, name=fc.name,
        response={"result": "ok", "silent": True}
    )


async def _run_sync(loop, fn, pool=None):
    """Run a blocking function in the specific executor pool."""
    from utils.concurrency import get_fast_pool
    pool = pool or get_fast_pool()
    return await loop.run_in_executor(pool, fn)


async def _background_tool(name, fn, speak_cb, pool=None):
    """Fire a function in a background thread, register in TaskRegistry, and return an immediate ack."""
    import uuid
    task_id = uuid.uuid4().hex[:8]
    cancel_event = threading.Event()

    def _run():
        from core.task_registry import get_registry
        registry = get_registry()
        registry.register(task_id, name, cancel_event.set)

        # Heartbeat: remind user every 15s that we're still working
        heartbeat_stop = threading.Event()
        def _heartbeat():
            count = 0
            while not heartbeat_stop.wait(15.0):
                count += 1
                if cancel_event.is_set():
                    break
                if speak_cb:
                    speak_cb(f"Still working on {name}, boss...")
        import threading as _t
        hb = _t.Thread(target=_heartbeat, daemon=True)
        hb.start()

        try:
            if cancel_event.is_set():
                if speak_cb:
                    speak_cb(f"{name} was cancelled.")
                return
            res = fn()
            if not cancel_event.is_set() and res:
                speak_cb(f"[System: {name} finished] {res}")
        except Exception as exc:
            log.error(f"[{name}] background error: {exc}")
        finally:
            heartbeat_stop.set()
            registry.deregister(task_id)
    
    from utils.concurrency import get_fast_pool
    pool = pool or get_fast_pool()
    run_in_background(_run, pool=pool)
    return f"{name} started in background. I will notify you when done."


async def dispatch_action(name: str, args: dict, ui, speak_callback, speak_error_callback) -> str:
    """
    Route a tool call to the correct action module.
    Returns a result string (may be empty/Done for fire-and-forget tools).
    Raises on unrecoverable errors so the caller can wrap in FunctionResponse.
    """
    loop = asyncio.get_event_loop()
    result = "Done."

    from utils.concurrency import get_fast_pool, get_io_pool, get_network_pool
    fast_pool = get_fast_pool()
    io_pool = get_io_pool()
    net_pool = get_network_pool()

    try:
        if name == "open_app":
            from actions.open_app import open_app
            r = await _run_sync(loop, lambda: open_app(parameters=args, response=None, player=ui), pool=fast_pool)
            result = r or f"Opened {args.get('app_name')}."

        elif name == "weather_report":
            from actions.weather_report import weather_action
            r = await _run_sync(loop, lambda: weather_action(parameters=args, player=ui), pool=net_pool)
            result = r or "Weather delivered."


        elif name == "file_controller":
            from actions.file_controller import file_controller
            r = await _run_sync(loop, lambda: file_controller(parameters=args, player=ui, speak=speak_callback), pool=io_pool)
            result = r or "Done."

        elif name == "phone_agent":
            from actions.phone_agent import phone_agent
            r = await _run_sync(loop, lambda: phone_agent(parameters=args, player=ui), pool=net_pool)
            result = r or "Done."

        elif name == "send_message":
            from actions.send_message import send_message
            r = await _run_sync(loop, lambda: send_message(parameters=args, response=None, player=ui, session_memory=None), pool=fast_pool)
            result = r or f"Message sent to {args.get('receiver')}."

        elif name == "reminder":
            from actions.reminder import reminder
            r = await _run_sync(loop, lambda: reminder(parameters=args, response=None, player=ui), pool=fast_pool)
            result = r or "Reminder set."

        elif name == "youtube_video":
            from actions.youtube_video import youtube_video
            r = await _run_sync(loop, lambda: youtube_video(parameters=args, response=None, player=ui), pool=net_pool)
            result = r or "Done."

        elif name == "screen_process":
            from actions.screen_processor import screen_process
            r = await _run_sync(loop, lambda: screen_process(
                parameters=args, response=None,
                player=ui, session_memory=None
            ), pool=io_pool)
            result = r or "No screen data could be captured."

        elif name == "computer_settings":
            from actions.computer_settings import computer_settings
            r = await _run_sync(loop, lambda: computer_settings(parameters=args, response=None, player=ui), pool=fast_pool)
            result = r or "Done."

        elif name == "desktop_control":
            from actions.desktop import desktop_control
            r = await _run_sync(loop, lambda: desktop_control(parameters=args, player=ui), pool=fast_pool)
            result = r or "Done."

        elif name == "code_helper":
            from actions.code_helper import code_helper
            action = (args.get("action") or "auto").lower().strip()
            if action in ("build", "screen_debug"):
                result = await _background_tool(
                    "Code task",
                    lambda: code_helper(parameters=args, player=ui, speak=speak_callback),
                    speak_callback,
                    pool=io_pool
                )
            else:
                r = await _run_sync(loop, lambda: code_helper(parameters=args, player=ui, speak=speak_callback), pool=io_pool)
                result = r or "Done."

        elif name == "dev_agent":
            from actions.dev_agent import dev_agent
            result = await _background_tool(
                "Development task",
                lambda: dev_agent(parameters=args, player=ui, speak=speak_callback),
                speak_callback,
                pool=io_pool
            )

        elif name == "agent_task":
            from agent.task_queue import get_queue, TaskPriority
            priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
            priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
            task_id  = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=speak_callback)
            result   = f"Task started (ID: {task_id})."

        elif name == "web_search":
            from actions.web_search import web_search as web_search_action
            r = await _run_sync(loop, lambda: web_search_action(parameters=args, player=ui), pool=net_pool)
            result = r or "Done."

        elif name == "file_processor":
            from actions.file_processor import file_processor
            if not args.get("file_path") and getattr(ui, "current_file", None):
                args["file_path"] = ui.current_file
            result = await _background_tool(
                "File processing",
                lambda: file_processor(parameters=args, player=ui, speak=speak_callback),
                speak_callback,
                pool=io_pool
            )

        elif name == "computer_control":
            from actions.computer_control import computer_control
            r = await _run_sync(loop, lambda: computer_control(parameters=args, player=ui), pool=fast_pool)
            result = r or "Done."

        elif name == "computer_use":
            from actions.computer_use import computer_use_action
            # Running in io_pool because it may do network calls to Vision API
            r = await _run_sync(loop, lambda: computer_use_action(parameters=args, player=ui), pool=io_pool)
            result = r or "Done."

        elif name == "browser_control":
            from actions.browser_agent import browser_agent
            # Running in io_pool; browser_agent has its own background thread for the event loop
            r = await _run_sync(loop, lambda: browser_agent(parameters=args, player=ui), pool=io_pool)
            result = r or "Done."

        elif name == "shutdown_captain":
            from utils import analytics as _analytics
            ui.write_log("SYS: Shutdown requested.")
            speak_callback("Goodbye, sir.")
            _analytics.end_session()
            def _shutdown():
                import time, os
                time.sleep(1.5)
                os._exit(0)
            run_in_background(_shutdown, pool=fast_pool)

        elif name == "search_memory":
            from core import memory_manager
            query = args.get("query", "")
            def _do_search():
                rows = memory_manager.search_memories(query=query, limit=5)
                if not rows:
                    return "No relevant memories found."
                resp = "Here is what I remember:\n"
                for r in rows:
                    resp += f"- {r.get('title', 'Fact')}: {r.get('summary', '')}\n"
                return resp
            r = await _run_sync(loop, _do_search, pool=io_pool)
            result = r or "Done."

        elif name == "cancel_task":
            from core.task_registry import get_registry
            registry = get_registry()
            count = registry.cancel_all()
            # Also cancel file search/indexing specifically
            try:
                from actions.files.engine import get_engine
                get_engine().cancel_search()
                get_engine().cancel_indexing()
            except Exception:
                pass
            # Also cancel any queued agent tasks
            try:
                from agent.task_queue import get_queue
                for status in get_queue().get_all_statuses():
                    if status["status"] in ("pending", "running"):
                        get_queue().cancel(status["task_id"])
            except Exception:
                pass
            result = f"Cancelled {count} background tasks." if count else "All background tasks have been cancelled."

        else:
            # Plugin handlers registered at load time
            from core.tool_dispatcher import _PLUGIN_HANDLERS
            handler = _PLUGIN_HANDLERS.get(name)
            if handler:
                r = await _run_sync(loop, lambda: handler(parameters=args, player=ui), pool=io_pool)
                result = r or "Done."
            else:
                result = f"Unknown tool: {name}"

    except Exception as exc:
        traceback.print_exc()
        speak_error_callback(name, exc)
        raise  # Bubble up to dispatcher so it can be wrapped as {"error": ...}

    return result