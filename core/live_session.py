"""
CAPTAIN AI — Live Session
Central orchestration for Gemini real-time audio, tool execution, and state.
"""
import asyncio
import threading
import traceback
import time

from utils.concurrency import run_in_background

from core.ai_service import build_config, LIVE_MODEL, SEND_SAMPLE_RATE, CHANNELS, CHUNK_SIZE, RECEIVE_SAMPLE_RATE
from core.session_manager import monitor_connection, handle_offline_command
from core.event_manager import start_firebase_listener
from core.tool_dispatcher import execute_tool
from utils.logger import log
from utils.config import get_api_key
from utils import analytics as _analytics
from core import chat_manager
import uuid

import re
_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

def _clean_transcript(text: str) -> str:
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()

class CaptainLive:
    def __init__(self, ui):
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self._stop_event    = asyncio.Event()   # set → all loops exit gracefully
        
        self._vad_speaking = False
        self._vad_silence_chunks = 0
        
        # State tracking via dictionary to share by reference with extracted modules
        self.state = {
            "online": True,
            "reply_to_phone": False,
        }
        self.perf_state = {
            "tool_start": 0.0,
            "tool_end": 0.0,
            "tool_active": False,
            "resp_sent": 0.0,
            "first_audio": 0.0,
        }
        
        self.ui.on_text_command = self._on_text_command
        self._turn_done_event: asyncio.Event | None = None
        self._has_connected_once = False   # prevents "SYS: CAPTAIN online." on every reconnect
        self._last_typed_command: str = ""  # track typed commands to avoid double-logging transcription
        # Lock so overlapping tool_call events (rare, but possible if Gemini
        # emits more than one before the previous finishes) are executed
        # sequentially instead of racing each other's ui.set_state()/
        # session.send_tool_response() calls.
        self._tool_lock = asyncio.Lock()
        # Keep references to tool-handling tasks so they can be cancelled
        # cleanly in stop() instead of being silently abandoned mid-flight.
        self._tool_tasks: set[asyncio.Task] = set()
        # Dedup guard: Gemini 3.1 may emit the same tool_call event twice.
        # Track processed function-call IDs so we never execute one twice.
        self._processed_fc_ids: set[str] = set()
        # Resumption handle from the Live API's session_resumption_update
        # messages. When set, reconnects RESUME the prior session instead
        # of cold-starting a brand-new one (see ai_service.build_config).
        self._resumption_handle: str | None = None
        self.session_id = str(uuid.uuid4())
        
        start_firebase_listener(self.ui, self.state)

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send(input=text, end_of_turn=True),
            self._loop
        )

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    def _on_text_command(self, text: str):
        if not self.state["online"]:
            handle_offline_command(text, self.ui, self.speak)
            return

        if not self._loop or not self.session:
            return

        # NOTE: Do NOT call self.ui.write_log("You: ...") here.
        # The frontend already adds the "YOU" log entry optimistically
        # in handleSendCommand before the WS message is even sent.
        # Logging here would cause the entry to appear twice.
        #
        # We also store the typed text so _receive_audio can skip
        # logging it again when Gemini echoes it back as input_transcription.
        self._last_typed_command = text.strip().lower()
        self.ui.set_state("THINKING")
        
        self.perf_state["last_cmd"] = text.strip()
        self.perf_state["cmd_start"] = time.time()

        asyncio.run_coroutine_threadsafe(
            self.session.send(input=text, end_of_turn=True),
            self._loop
        )

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif self.ui.muted:
            self.ui.set_state("MUTED")
        else:
            self.ui.set_state("LISTENING")

    async def _send_realtime(self):
        # Runs for the entire app lifetime now (not per-connection). While a
        # reconnect is in progress, self.session is briefly None — instead
        # of dropping mic audio captured during that gap, hold a short
        # buffer and flush it in order the moment the session is back.
        # Capped small on purpose: a reconnect should take ~1s with
        # resumption working, so we only need to bridge a small gap, not
        # accumulate a large stale backlog.
        import collections
        buffer: collections.deque = collections.deque(maxlen=40)  # ~2.5s of audio

        while not self._stop_event.is_set():
            try:
                msg = await asyncio.wait_for(self.out_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            if not self.session:
                buffer.append(msg)
                continue

            # Flush anything buffered from a prior gap first, oldest-first,
            # so speech order is preserved across the reconnect boundary.
            while buffer:
                buffered_msg = buffer.popleft()
                try:
                    await self.session.send_realtime_input(audio=buffered_msg)
                except Exception:
                    # Session dropped again mid-flush — stop flushing and
                    # put the current message back on hold too.
                    buffer.appendleft(buffered_msg)
                    buffer.append(msg)
                    break
            else:
                try:
                    if msg.get("type") == "turn_complete":
                        # Send an empty text block to satisfy the payload requirements,
                        # while forcing the turn to complete.
                        await self.session.send(input="", end_of_turn=True)
                    else:
                        await self.session.send_realtime_input(audio=msg)
                except Exception as exc:
                    log.warning(f"[CAPTAIN] send_realtime_input failed, buffering: {exc}")
                    if msg.get("type") != "turn_complete":
                        buffer.append(msg)

    async def _listen_audio(self):
        log.info("[CAPTAIN] 🎤 Mic started")
        loop = asyncio.get_running_loop()
        def callback(indata, frames, time_info, status):
            with self._speaking_lock:
                captain_speaking = self._is_speaking
            if not captain_speaking and not self.ui.muted:
                data = indata.tobytes()
                
                # Local VAD — filter out background noise
                import audioop
                rms = audioop.rms(data, 2)
                threshold = 800 # Voice threshold for 16-bit PCM (filters fans, typing, ambient)
                
                if not hasattr(self, '_pre_roll_buffer'):
                    import collections
                    self._pre_roll_buffer = collections.deque(maxlen=10) # ~0.6s of pre-roll
                
                if rms > threshold:
                    if not self._vad_speaking:
                        # Voice just started! Flush the pre-roll buffer so we don't chop the start of the word
                        while self._pre_roll_buffer:
                            loop.call_soon_threadsafe(
                                self.out_queue.put_nowait,
                                {"data": self._pre_roll_buffer.popleft(), "mime_type": "audio/pcm;rate=16000"}
                            )
                    self._vad_speaking = True
                    self._vad_silence_chunks = 0
                elif self._vad_speaking:
                    self._vad_silence_chunks += 1
                    # ~3.0s of silence (45 chunks at 64ms/chunk)
                    if self._vad_silence_chunks > 45:
                        self._vad_speaking = False
                        self._vad_silence_chunks = 0
                        loop.call_soon_threadsafe(
                            self.out_queue.put_nowait,
                            {"type": "turn_complete"}
                        )
                
                # If speaking, stream live audio. If not, save to pre-roll buffer.
                if self._vad_speaking:
                    loop.call_soon_threadsafe(
                        self.out_queue.put_nowait,
                        {"data": data, "mime_type": "audio/pcm;rate=16000"}
                    )
                else:
                    self._pre_roll_buffer.append(data)

        try:
            import sounddevice as sd
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                log.info("[CAPTAIN] 🎤 Mic stream open")
                await self._stop_event.wait()
        except Exception as exc:
            log.error(f"[CAPTAIN] ❌ Mic: {exc}")
            raise

    async def _receive_audio(self):
        log.info("[CAPTAIN] 👂 Recv started")
        out_buf, in_buf = [], []
        try:
            while not self._stop_event.is_set():
                async for response in self.session.receive():
                    if self._stop_event.is_set():
                        break

                    # ── Barge-in: user interrupted the AI mid-speech ──
                    if response.server_content and getattr(response.server_content, "interrupted", False):
                        log.info("[CAPTAIN] ⚡ Barge-in detected — flushing audio queue")
                        while not self.audio_in_queue.empty():
                            try:
                                self.audio_in_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                break
                        with self._speaking_lock:
                            self._is_speaking = False
                        self.ui.set_state("LISTENING")
                        continue

                    if response.data:
                        if self._turn_done_event and self._turn_done_event.is_set():
                            self._turn_done_event.clear()
                        self.audio_in_queue.put_nowait(response.data)

                    # Capture the resumption handle so a future reconnect can
                    # RESUME this session (fast, keeps context) instead of
                    # cold-starting (slow, re-sends full prompt/tools, wipes
                    # context — the "fresh start" behavior).
                    sru = getattr(response, "session_resumption_update", None)
                    if sru and getattr(sru, "resumable", False) and getattr(sru, "new_handle", None):
                        is_new = sru.new_handle != self._resumption_handle
                        self._resumption_handle = sru.new_handle
                        if is_new:
                            log.info(f"[CAPTAIN] 🔖 Resumption handle updated: {sru.new_handle[:16]}...")

                    if response.server_content:
                        sc = response.server_content
                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt: out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt: in_buf.append(txt)

                        if sc.turn_complete:
                            if self._turn_done_event:
                                self._turn_done_event.set()

                            with self._speaking_lock:
                                if not self._is_speaking and not self.ui.muted:
                                    self.ui.set_state("LISTENING")
                                    
                            # Log command execution if we sent a text command this turn
                            if self.perf_state.get("last_cmd"):
                                cmd = self.perf_state["last_cmd"]
                                latency = time.time() - self.perf_state.get("cmd_start", time.time())
                                try:
                                    from core.command_manager import log_execution
                                    # Since we got a turn_complete from the server, it was processed successfully.
                                    log_execution(cmd, "Success", latency)
                                except Exception as exc:
                                    log.warning(f"Failed to log execution: {exc}")
                                self.perf_state["last_cmd"] = None

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                # Skip logging if this transcription is just Gemini
                                # echoing back a typed command — the frontend already
                                # displayed it optimistically.
                                is_echo = (
                                    self._last_typed_command and
                                    full_in.strip().lower() == self._last_typed_command
                                )
                                if not is_echo:
                                    self.ui.write_log(f"You: {full_in}")
                                self._last_typed_command = ""   # reset after first turn
                                loop = asyncio.get_running_loop()
                                loop.run_in_executor(
                                    None, chat_manager.add_chat_message, self.session_id, "user", full_in
                                )
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"Captain: {full_out}")
                                if self.state.get("reply_to_phone", False):
                                    self.state["reply_to_phone"] = False
                                    try:
                                        log.info("[Firebase] Routing reply to phone TTS...")
                                        from actions.phone_agent import phone_agent
                                        run_in_background(phone_agent, {"action": "speak", "message": full_out}, None, self.ui)
                                    except Exception as e:
                                        log.warning(f"[Firebase] Failed to send reply to phone: {e}")
                                loop = asyncio.get_running_loop()
                                loop.run_in_executor(
                                    None, chat_manager.add_chat_message, self.session_id, "captain", full_out
                                )
                            out_buf = []

                    if response.tool_call:
                        async def _handle_tools(tool_call):
                            # Serialize tool_call batches. If Gemini ever emits
                            # more than one tool_call event before the first
                            # finishes, this prevents their ui.set_state(...)
                            # calls and session.send_tool_response(...) calls
                            # from interleaving/racing each other.
                            async with self._tool_lock:
                                t0 = time.perf_counter()
                                fn_responses = []

                                for fc in tool_call.function_calls:
                                    # Dedup: Gemini 3.1 sometimes sends identical function calls twice.
                                    # Fallback to hashing the name + args if id is missing or duplicate.
                                    fc_id = getattr(fc, 'id', None) or f"{fc.name}_{str(fc.args)}"
                                    if fc_id in self._processed_fc_ids:
                                        log.info(f"[CAPTAIN] ⏭️ Skipping duplicate tool call: {fc.name} (id={fc_id[:20]})")
                                        continue
                                    self._processed_fc_ids.add(fc_id)
                                    # Cap the set size to prevent unbounded memory growth
                                    if len(self._processed_fc_ids) > 200:
                                        self._processed_fc_ids = set(list(self._processed_fc_ids)[-100:])

                                    call_sig = f"{fc.name}_{str(fc.args).lower()}"
                                    if not hasattr(self, '_recent_tools'):
                                        self._recent_tools = {}
                                    
                                    now = time.time()
                                    # Dedup across turns within a 6-second window to prevent barge-in echo loops
                                    # Allow rapid repetition for computer_settings (e.g. volume up repeatedly)
                                    is_repeatable = fc.name in ["computer_settings"]
                                    
                                    if not is_repeatable and call_sig in self._recent_tools and (now - self._recent_tools[call_sig]['time']) < 6.0:
                                        log.info(f"[CAPTAIN] ⏭️ Skipping duplicate tool call (barge-in protection): {fc.name}")
                                        from google.genai import types
                                        cached_resp = self._recent_tools[call_sig].get('response', {"result": "Skipped duplicate"})
                                        fn_responses.append(types.FunctionResponse(
                                            id=getattr(fc, 'id', None) or "", name=fc.name, response=cached_resp
                                        ))
                                        continue

                                    fc_name = fc.name
                                    fc_args = dict(fc.args or {})
                                    log.info(f"[CAPTAIN] 📞 {fc_name}")
                                    self.ui.set_state(f"SEARCHING {fc_name.upper()}")
                                    
                                    # Force Gemini's native voice to acknowledge heavy tasks first
                                    heavy_tools = ["web_search", "dev_agent", "file_controller", "computer_control"]
                                    if fc_name in heavy_tools:
                                        if not hasattr(self, '_acknowledged_tools'):
                                            self._acknowledged_tools = {}
                                        
                                        # If this tool hasn't been acknowledged in the last 15 seconds, force an acknowledgment
                                        if call_sig not in self._acknowledged_tools or (now - self._acknowledged_tools.get(call_sig, 0)) > 15.0:
                                            self._acknowledged_tools[call_sig] = now
                                            log.info(f"[CAPTAIN] 🛑 Forcing native voice acknowledgment for {fc_name}")
                                            
                                            from google.genai import types
                                            # Return a system directive to make Gemini speak and then call the tool again
                                            directive = (
                                                "SYSTEM DIRECTIVE: Do not answer the user yet. "
                                                "First, speak an acknowledgment aloud in Hindi/Hinglish (e.g. 'Ek minute check karta hu' or 'एक क्षण, मैं खोज रहा हूँ।'). "
                                                "After speaking, you MUST immediately call this exact tool again to get the actual data."
                                            )
                                            fn_responses.append(types.FunctionResponse(
                                                id=getattr(fc, 'id', None) or "", name=fc_name, response={"result": directive}
                                            ))
                                            continue

                                    # We will store the full response in _recent_tools after execute_tool

                                    # Broadcast Tool Start
                                    tool_t0 = time.time()
                                    if hasattr(self.ui, 'broadcast'):
                                        active_session = getattr(self.ui, "active_chat_session", "default_session")
                                        self.ui.broadcast({
                                            "type": "tool_execution",
                                            "session_id": active_session,
                                            "tool_name": fc_name,
                                            "status": "running"
                                        })

                                    try:
                                        # Per-tool timeout policy
                                        _TOOL_TIMEOUTS = {
                                            "file_controller": 60.0,
                                            "screen_process": 45.0,
                                            "weather_report": 10.0,
                                            "web_search": 20.0,
                                            "phone_agent": 15.0,
                                            "dev_agent": 45.0,
                                            "code_helper": 30.0,
                                            "open_app": 10.0,
                                            "computer_settings": 5.0,
                                            "computer_control": 10.0,
                                            "desktop_control": 5.0,
                                            "reminder": 5.0,
                                            "youtube_video": 15.0,
                                            "send_message": 10.0,
                                            "save_memory": 5.0,
                                            "search_memory": 10.0,
                                            "file_processor": 30.0,
                                            "agent_task": 45.0,
                                            "shutdown_captain": 5.0,
                                        }
                                        tool_timeout = _TOOL_TIMEOUTS.get(fc_name, 18.0)
                                        
                                        fr = await asyncio.wait_for(
                                            execute_tool(fc, self.ui, self.speak, self.speak_error, self.perf_state),
                                            timeout=tool_timeout
                                        )
                                        fn_responses.append(fr)
                                        # Cache the response for duplicate protection
                                        self._recent_tools[call_sig] = {
                                            'time': time.time(),
                                            'response': fr.response
                                        }
                                        
                                        # Broadcast Tool Success
                                        if hasattr(self.ui, 'broadcast'):
                                            self.ui.broadcast({
                                                "type": "tool_execution",
                                                "session_id": active_session,
                                                "tool_name": fc_name,
                                                "status": "success",
                                                "duration": time.time() - tool_t0
                                            })
                                            
                                    except asyncio.TimeoutError:
                                        from google.genai import types
                                        err_msg = "Task timed out after 18 seconds and was cancelled."
                                        log.error(f"[CAPTAIN] ⏱️ Tool {fc_name} timed out.")
                                        fn_responses.append(types.FunctionResponse(
                                            id=getattr(fc, 'id', None) or "", name=fc_name, response={"error": err_msg}
                                        ))
                                        if hasattr(self.ui, 'broadcast'):
                                            self.ui.broadcast({
                                                "type": "tool_execution",
                                                "session_id": active_session,
                                                "tool_name": fc_name,
                                                "status": "error",
                                                "error": err_msg,
                                                "duration": time.time() - tool_t0
                                            })
                                    except Exception as e:
                                        from google.genai import types
                                        log.error(f"[CAPTAIN] Tool error: {e}")
                                        fn_responses.append(types.FunctionResponse(
                                            id=fc.id, name=fc.name, response={"error": str(e)}
                                        ))
                                        
                                        # Broadcast Tool Error
                                        if hasattr(self.ui, 'broadcast'):
                                            self.ui.broadcast({
                                                "type": "tool_execution",
                                                "session_id": active_session,
                                                "tool_name": fc_name,
                                                "status": "error",
                                                "error": str(e),
                                                "duration": time.time() - tool_t0
                                            })

                                try:
                                    if fn_responses:
                                        await self.session.send_tool_response(function_responses=fn_responses)
                                        self.perf_state['resp_sent'] = time.perf_counter()
                                        log.info(f"[PERF] 📨 [AI] Tool response sent in {self.perf_state['resp_sent'] - t0:.2f}s")
                                    else:
                                        log.info(f"[PERF] 📨 [AI] Tool response skipped (empty)")
                                except Exception as e:
                                    log.error(f"[CAPTAIN] Error sending tool response: {e}")

                        task = asyncio.create_task(_handle_tools(response.tool_call))
                        self._tool_tasks.add(task)
                        task.add_done_callback(self._tool_tasks.discard)
        except Exception as exc:
            log.error(f"[CAPTAIN] ❌ Recv: {exc}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        """Feed audio chunks from the asyncio queue into a dedicated writer thread."""
        log.info("[CAPTAIN] 🔊 Play started")
        import sounddevice as sd
        import queue as _queue

        audio_q: _queue.Queue = _queue.Queue(maxsize=500)
        writer_ready = threading.Event()

        def _writer():
            writer_ready.set()
            stream = sd.RawOutputStream(
                samplerate=RECEIVE_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
            )
            stream.start()

            try:
                import ctypes
                handle = ctypes.windll.kernel32.GetCurrentThread()
                ctypes.windll.kernel32.SetThreadPriority(handle, 2)
            except Exception:
                pass

            silence = b'\x00' * (CHUNK_SIZE * CHANNELS * 2)
            try:
                while True:
                    chunk = audio_q.get()      # blocks cleanly, 0% CPU when idle
                    if chunk is None:
                        break                  # poison pill → graceful shutdown
                    try:
                        if getattr(self.ui, "volume_muted", False):
                            stream.write(silence)
                        else:
                            stream.write(chunk)
                    except Exception as e:
                        log.warning(f"[CAPTAIN] ⚠️ Audio chunk dropped: {e}")
            finally:
                stream.stop()
                stream.close()

        run_in_background(_writer)
        writer_ready.wait()

        idle_time = 0.0
        _logged_first_audio = False
        try:
            while not self._stop_event.is_set():
                try:
                    chunk = await asyncio.wait_for(self.audio_in_queue.get(), timeout=0.08)
                    idle_time = 0.0
                except asyncio.TimeoutError:
                    idle_time += 0.08
                    if idle_time > 0.4:
                        if audio_q.empty():
                            self.set_speaking(False)
                            if self._turn_done_event and self._turn_done_event.is_set():
                                self._turn_done_event.clear()
                        _logged_first_audio = False
                    continue

                if not _logged_first_audio and self.perf_state.get('resp_sent', 0) > 0:
                    self.perf_state['first_audio'] = time.perf_counter()
                    latency = self.perf_state['first_audio'] - self.perf_state['resp_sent']
                    log.info(f"[PERF] 🔊 First audio chunk {latency:.2f}s after tool response sent")
                    total = self.perf_state['first_audio'] - self.perf_state['tool_start']
                    log.info(f"[PERF] 🏁 Total tool→audio latency: {total:.2f}s")
                    self.perf_state['resp_sent'] = 0
                    _logged_first_audio = True

                self.set_speaking(True)
                try:
                    audio_q.put_nowait(chunk)
                except _queue.Full:
                    try:
                        audio_q.get_nowait()
                    except _queue.Empty:
                        pass
                    try:
                        audio_q.put_nowait(chunk)
                    except _queue.Full:
                        pass
        except Exception as exc:
            log.error(f"[CAPTAIN] ❌ Play: {exc}")
            raise
        finally:
            self.set_speaking(False)
            audio_q.put(None)   # poison pill stops writer thread

    async def run(self):
        run_in_background(monitor_connection, self.state, self.speak, self.ui)

        # The mic (InputStream) and its send loop now run for the ENTIRE
        # app lifetime, decoupled from the Gemini connect/reconnect cycle.
        # Previously these were recreated on every reconnect, which meant:
        #   - the microphone device was physically closed and reopened
        #     each time (real device-handshake latency), and
        #   - CAPTAIN was not listening at all during that gap.
        # Now the mic stays open continuously; _send_realtime buffers
        # briefly if the session is mid-reconnect (see above) so no audio
        # is lost and there is no "not listening" gap from the user's side.
        self.out_queue = asyncio.Queue(maxsize=200)
        mic_task  = asyncio.create_task(self._listen_audio())
        send_task = asyncio.create_task(self._send_realtime())

        client = None
        # Exponential backoff for connect failures (rate limits, transient
        # network errors, etc). Resets to the base delay after every
        # successful connection. Capped so we never wait "forever" between
        # retries once the API/network recovers.
        backoff_base   = 1.0
        backoff_cap    = 30.0
        backoff_delay  = backoff_base
        # Timestamp of the moment we last had a working session — used to
        # measure exactly how long a reconnect takes end-to-end. Compare
        # this number against your own experience of the delay.
        session_lost_at: float | None = None

        try:
            while not self._stop_event.is_set():
                if not self.state["online"]:
                    self.ui.set_state("OFFLINE")
                    self.ui.write_log("SYS: CAPTAIN operating offline.")
                    while not self.state["online"] and not self._stop_event.is_set():
                        await asyncio.sleep(1)
                    if self._stop_event.is_set():
                        break
                    self.ui.write_log("SYS: Network detected. Reconnecting...")
                    # Don't set THINKING here — keep whatever state we had

                try:
                    if not client:
                        from google import genai
                        client = genai.Client(
                            api_key=get_api_key(),
                            http_options={"api_version": "v1beta"}
                        )
                    log.info(
                        f"[CAPTAIN] [+] Connecting... "
                        f"(resumption_handle={'YES' if self._resumption_handle else 'NO — cold start'})"
                    )
                    connect_started_at = time.perf_counter()
                    # Pass the last resumption handle (if any) so the server
                    # resumes the prior session instead of cold-starting.
                    config = build_config(self._resumption_handle)
                    async with client.aio.live.connect(model=LIVE_MODEL, config=config) as session:
                        self.session          = session
                        self._loop            = asyncio.get_running_loop()
                        self.audio_in_queue   = asyncio.Queue()
                        self._turn_done_event = asyncio.Event()
                        # Clear dedup set on reconnect — new session means new IDs
                        self._processed_fc_ids.clear()

                        connected_at = time.perf_counter()
                        connect_duration = connected_at - connect_started_at
                        if session_lost_at is not None:
                            total_gap = connected_at - session_lost_at
                            log.info(
                                f"[PERF] 🔁 Reconnected — connect took {connect_duration:.2f}s, "
                                f"total gap since disconnect: {total_gap:.2f}s"
                            )
                        else:
                            log.info(f"[PERF] ✅ First connect took {connect_duration:.2f}s")
                        backoff_delay = backoff_base   # reset backoff after a clean connect
                        if self.ui.muted:
                            self.ui.set_state("MUTED")
                        else:
                            self.ui.set_state("LISTENING")

                        # Only log "CAPTAIN online." once — not on every silent reconnect
                        if not self._has_connected_once:
                            self._has_connected_once = True
                            self.ui.write_log("SYS: CAPTAIN online.")

                        t3 = asyncio.create_task(self._receive_audio())
                        t4 = asyncio.create_task(self._play_audio())
                        try:
                            await asyncio.gather(t3, t4)
                        finally:
                            for t in (t3, t4):
                                if not t.done():
                                    t.cancel()

                except Exception as exc:
                    log.warning(f"[CAPTAIN] [!] {exc}")
                    self.session = None
                    session_lost_at = time.perf_counter()
                    traceback.print_exc()

                if self._stop_event.is_set():
                    break

                self.set_speaking(False)
                # ── Do NOT set THINKING here. The session dropped silently (normal
                #    Gemini live session cycling). Keep the UI in whatever state it
                #    was — most likely LISTENING. The user should not see any
                #    indicator that a reconnect is happening.
                log.info(f"[CAPTAIN] 🔄 Reconnecting in {backoff_delay:.1f}s...")
                await asyncio.sleep(backoff_delay)
                backoff_delay = min(backoff_delay * 2, backoff_cap)
        finally:
            mic_task.cancel()
            send_task.cancel()

    def stop(self):
        """Signal all loops to exit gracefully."""
        self._stop_event.set()
        for task in list(self._tool_tasks):
            if not task.done():
                task.cancel()