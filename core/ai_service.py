from core.tool_dispatcher import TOOL_DECLARATIONS
from utils.config import PROMPT_PATH, get_user_paths
from core.memory_manager import search_memories

LIVE_MODEL          = "models/gemini-3.1-flash-live-preview"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024

def _load_system_prompt() -> str:
    """Load system prompt and interpolate dynamic user paths."""
    try:
        raw = PROMPT_PATH.read_text(encoding="utf-8")
        # Replace hardcoded path placeholders with real user paths
        paths = get_user_paths()
        for key, val in paths.items():
            raw = raw.replace(f"{{{key}}}", val)
        return raw
    except Exception:
        return (
            "You are CAPTAIN, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

def get_voice_name() -> str:
    """Read voice from config, default to Aoede."""
    from utils.config import get_voice
    return get_voice()

_cached_sys_prompt = None
_cached_mem_str = None
_last_cache_time = 0.0

def build_config(resumption_handle: str | None = None) -> 'types.LiveConnectConfig':
    """
    Build the Live API connection config.

    resumption_handle: if the server previously gave us a resumable session
    handle (captured from `session_resumption_update` in _receive_audio),
    pass it here on reconnect. This tells the server to RESUME the prior
    session instead of starting a brand-new one — meaning it does NOT need
    to re-process the full system_instruction/tools payload and does NOT
    reset conversation context. Without this, every reconnect is a cold
    start (slow + the assistant "forgets" what was just discussed).
    """
    from google.genai import types
    from datetime import datetime
    import time

    global _cached_sys_prompt, _cached_mem_str, _last_cache_time
    now_ts = time.time()
    
    if _cached_sys_prompt is None or (now_ts - _last_cache_time) > 60.0:
        memories = search_memories(limit=5)
        if memories:
            lines = ["[RECENT MEMORIES (May not be relevant to the current topic) — use naturally, never recite like a list]"]
            for m in memories:
                lines.append(f"- {m.get('category', 'Note').title()} / {m.get('title', 'Fact')}: {m.get('summary', '')}")
            _cached_mem_str = "\n".join(lines) + "\n"
        else:
            _cached_mem_str = ""
            
        _cached_sys_prompt = _load_system_prompt()
        _last_cache_time = now_ts

    now      = datetime.now()
    time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
    time_ctx = (
        f"[CURRENT DATE & TIME]\n"
        f"Right now it is: {time_str} (India Standard Time - IST)\n"
        f"Use this to calculate exact times for reminders.\n"
        f"CRITICAL RULE: When asked about the time, ALWAYS reply with the time in India (IST).\n\n"
    )

    parts = [time_ctx]
    if _cached_mem_str:
        parts.append(_cached_mem_str)
    parts.append(_cached_sys_prompt)

    resumption_cfg = (
        types.SessionResumptionConfig(handle=resumption_handle)
        if resumption_handle else
        types.SessionResumptionConfig()
    )

    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        output_audio_transcription={},
        input_audio_transcription={},
        system_instruction="\n".join(parts),
        tools=[{"function_declarations": TOOL_DECLARATIONS}],
        session_resumption=resumption_cfg,
        # Minimize reasoning delay before audio output starts streaming
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.MINIMAL
        ),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=get_voice_name()
                )
            )
        ),
    )