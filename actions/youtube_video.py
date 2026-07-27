#youtube_video.py
import logging
import traceback
import re
import threading
from datetime import datetime
from urllib.parse import quote_plus
from pathlib import Path
from typing import Optional, Any, Callable, Dict, List

# Setup detailed logging to captain.log for windowed EXE debugging
logger = logging.getLogger("YouTubeAction")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    fh = logging.FileHandler("captain.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

from config import is_windows, is_mac, is_linux

# Lazy load flags
try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    _TRANSCRIPT_OK = True
except ImportError:
    _TRANSCRIPT_OK = False


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_YT_VIDEO_FILTER = "EgIQAQ%3D%3D"

# Thread-safe caching for Gemini Model
_gemini_model = None
_gemini_lock = threading.Lock()

def _get_gemini_model() -> Any:
    global _gemini_model
    if _gemini_model is None:
        with _gemini_lock:
            if _gemini_model is None:
                from utils.config import get_api_key
                import google.generativeai as genai
                genai.configure(api_key=get_api_key())
                _gemini_model = genai.GenerativeModel(
                    model_name="gemini-2.5-flash",
                    system_instruction=(
                        "You are CAPTAIN, an AI assistant. "
                        "Summarize YouTube video transcripts clearly and concisely. "
                        "Structure: 1-sentence overview, then 3-5 key points. "
                        "Be direct. Address the user as 'sir'. "
                        "Match the language of the transcript."
                    )
                )
    return _gemini_model


def _launch_browser_process(paths: List[str], url: str) -> bool:
    """Helper to launch a browser from specific executable paths."""
    import subprocess
    import os
    for b in paths:
        if os.path.exists(b):
            try:
                logger.info(f"Trying subprocess with browser: {b}")
                subprocess.Popen(
                    [b, url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW | getattr(subprocess, 'DETACHED_PROCESS', 0x00000008)
                )
                logger.info(f"Successfully launched {b}")
                return True
            except (OSError, subprocess.SubprocessError) as e:
                logger.error(f"Failed to launch {b}: {e}")
    return False

def _try_os_startfile(url: str) -> bool:
    """Helper to launch URL via os.startfile on Windows."""
    import os
    try:
        os.startfile(url)
        logger.info("os.startfile succeeded.")
        return True
    except OSError as e:
        logger.error(f"os.startfile failed: {e}")
    return False

def _try_webbrowser(url: str) -> bool:
    """Helper to launch URL via Python's webbrowser module."""
    import webbrowser
    try:
        if webbrowser.open(url):
            logger.info("webbrowser.open succeeded.")
            return True
        logger.warning("webbrowser.open returned False.")
    except Exception as e:
        logger.error(f"webbrowser.open failed: {e}")
    return False

def _try_windows_start(url: str) -> bool:
    """Helper to launch URL via Windows shell start command."""
    import subprocess
    try:
        subprocess.Popen(
            f'start "" "{url}"',
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        logger.info("subprocess 'start' succeeded.")
        return True
    except (OSError, subprocess.SubprocessError) as e:
        logger.error(f"subprocess 'start' failed: {e}")
    return False


def _open_url(url: str) -> None:
    """Open URL robustly, with fallbacks for PyInstaller --windowed executables."""
    import os
    
    logger.info(f"Attempting to open URL: {url}")
    
    # 0. Prioritize Brave browser for YouTube playback
    if is_windows():
        brave_paths = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe")
        ]
        if _launch_browser_process(brave_paths, url):
            return

    # 1. Try os.startfile (Windows default handler)
    if is_windows() and _try_os_startfile(url):
        return

    # 2. Try webbrowser module
    if _try_webbrowser(url):
        return

    # 3. Try subprocess with Windows 'start' command, explicitly redirecting standard handles
    if is_windows():
        if _try_windows_start(url):
            return

        # 4. Try subprocess with known browsers as final fallback
        browsers = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", 
        ]
        if _launch_browser_process(browsers, url):
            return

    logger.error("All URL opening methods failed.")
    print(f"[YouTube] ⚠️ All open_url methods failed for {url}")


def _scrape_first_video_url(query: str) -> Optional[str]:
    import urllib.request
    import urllib.error
    import ssl
    
    search_url = (
        f"https://www.youtube.com/results"
        f"?search_query={quote_plus(query)}"
        f"&sp={_YT_VIDEO_FILTER}"
    )
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(search_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            html = response.read().decode('utf-8')
        
        video_ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
        seen = set()
        for vid in video_ids:
            if vid in seen: continue
            seen.add(vid)
            if f'/shorts/{vid}' in html: continue
            return f"https://www.youtube.com/watch?v={vid}"
    except (urllib.error.URLError, OSError) as e:
        logger.error(f"scrape_first_video_url failed: {e}")
        print(f"[YouTube] ⚠️ scrape_first_video_url failed: {e}")
    except Exception as e:
        logger.error(f"scrape_first_video_url unexpected error: {e}", exc_info=True)
    return None

def _extract_video_id(url: str) -> Optional[str]:
    match = re.search(
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([A-Za-z0-9_-]{11})", url
    )
    return match.group(1) if match else None


def _is_valid_youtube_url(url: Optional[str]) -> bool:
    if not url:
        return False
    return bool(re.search(r"(youtube\.com|youtu\.be)", url))


def _ask_for_url(prompt_text: str = "YouTube video URL:") -> Optional[str]:
    try:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk._default_root
        if root is None:
            root = tk.Tk()
            root.withdraw()

        url = simpledialog.askstring("C.A.P.T.A.I.N", prompt_text, parent=root)
        return url.strip() if url else None
    except Exception as e:
        print(f"[YouTube] ⚠️ URL dialog failed: {e}")
        return None


def _get_transcript(video_id: str) -> Optional[str]:
    if not _TRANSCRIPT_OK:
        return None
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript      = None

        lang_priority = ["en", "tr", "de", "fr", "es", "it", "pt", "ru", "ja", "ko", "ar", "zh"]

        try:
            transcript = transcript_list.find_manually_created_transcript(lang_priority)
        except Exception:
            pass

        if transcript is None:
            try:
                transcript = transcript_list.find_generated_transcript(lang_priority)
            except Exception:
                for t in transcript_list:
                    transcript = t
                    break

        if transcript is None:
            return None

        fetched = transcript.fetch()
        return " ".join(entry["text"] for entry in fetched)

    except Exception as e:
        print(f"[YouTube] ⚠️ Transcript fetch failed: {e}")
        return None


def _summarize_with_gemini(transcript: str, video_url: str) -> str:
    model = _get_gemini_model()

    max_chars = 80000
    truncated = transcript[:max_chars] + ("..." if len(transcript) > max_chars else "")
    try:
        response = model.generate_content(
            f"Please summarize this YouTube video transcript:\n\n{truncated}"
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API failure: {e}")
        raise


def _save_summary(content: str, video_url: str) -> str:
    import subprocess
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"youtube_summary_{ts}.txt"
    desktop  = Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    filepath = desktop / filename

    header = (
        f"CAPTAIN — YouTube Summary\n"
        f"{'─' * 50}\n"
        f"URL    : {video_url}\n"
        f"Date   : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"{'─' * 50}\n\n"
    )
    filepath.write_text(header + content, encoding="utf-8")

    try:
        if is_windows():
            subprocess.Popen(["notepad.exe", str(filepath)])
        elif is_mac():
            subprocess.Popen(["open", "-t", str(filepath)])
        else:
            subprocess.Popen(["xdg-open", str(filepath)])
    except (OSError, subprocess.SubprocessError) as e:
        print(f"[YouTube] ⚠️ Could not open text editor: {e}")

    return str(filepath)


def _scrape_video_info(video_id: str) -> Dict[str, str]:
    if not _REQUESTS_OK:
        return {}
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        html = r.text
        info = {}

        patterns = {
            "title":    r'"title":\{"runs":\[\{"text":"([^"]+)"',
            "channel":  r'"ownerChannelName":"([^"]+)"',
            "views":    r'"viewCount":"(\d+)"',
            "duration": r'"lengthSeconds":"(\d+)"',
            "likes":    r'"label":"([0-9,]+ likes)"',
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, html)
            if match:
                raw = match.group(1)
                if key == "views":
                    info[key] = f"{int(raw):,}"
                elif key == "duration":
                    secs = int(raw)
                    info[key] = f"{secs // 60}:{secs % 60:02d}"
                else:
                    info[key] = raw

        return info
    except requests.RequestException as e:
        print(f"[YouTube] ⚠️ Info scrape HTTP error: {e}")
    except Exception as e:
        print(f"[YouTube] ⚠️ Info scrape unexpected error: {e}")
    return {}


def _scrape_trending(region: str = "TR", max_results: int = 8) -> List[Dict[str, Any]]:
    if not _REQUESTS_OK:
        return []
    url = f"https://www.youtube.com/feed/trending?gl={region.upper()}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        html = r.text

        titles   = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}\]', html)
        channels = re.findall(r'"ownerText":\{"runs":\[\{"text":"([^"]+)"', html)

        results = []
        seen = set()
        for i, title in enumerate(titles):
            if title in seen or len(title) < 5:
                continue
            seen.add(title)
            channel = channels[i] if i < len(channels) else "Unknown"
            results.append({"rank": len(results) + 1, "title": title, "channel": channel})
            if len(results) >= max_results:
                break

        return results
    except requests.RequestException as e:
        print(f"[YouTube] ⚠️ Trending scrape HTTP error: {e}")
    except Exception as e:
        print(f"[YouTube] ⚠️ Trending scrape unexpected error: {e}")
    return []

def _handle_play(parameters: Dict[str, Any], player: Any) -> str:
    query = parameters.get("query", "").strip()
    if not query:
        return "Please tell me what you'd like to watch, sir."

    if player:
        player.write_log(f"[YouTube] Searching: {query}")

    print(f"[YouTube] 🔍 Scraping first non-Shorts video for: {query}")

    video_url = _scrape_first_video_url(query)

    if video_url:
        if not _is_valid_youtube_url(video_url):
            logger.error(f"Generated YouTube URL is invalid: {video_url}")
            video_url = None
        else:
            logger.info(f"Opening YouTube URL: {video_url}")
            print(f"[YouTube] ▶️ Opening: {video_url}")
            _open_url(video_url)
            return f"Playing: {query}"

    print(f"[YouTube] ⚠️ Scrape failed, opening filtered search page")
    fallback_url = (
        f"https://www.youtube.com/results"
        f"?search_query={quote_plus(query)}"
        f"&sp={_YT_VIDEO_FILTER}"
    )
    _open_url(fallback_url)
    return f"Opened YouTube search for: {query} (manual selection required)"


def _handle_summarize(parameters: Dict[str, Any], player: Any, speak: Any) -> str:
    if not _TRANSCRIPT_OK:
        return "youtube-transcript-api is not installed. Run: pip install youtube-transcript-api"

    url = _ask_for_url("Please paste the YouTube video URL:")
    if not url:
        return "No URL provided, sir. Summary cancelled."
    if not _is_valid_youtube_url(url):
        return "That doesn't appear to be a valid YouTube URL, sir."

    video_id = _extract_video_id(url)
    if not video_id:
        return "Could not extract video ID from that URL, sir."

    if player:
        player.write_log(f"[YouTube] Summarizing: {url}")
    if speak:
        speak("Fetching the transcript now, sir. One moment.")

    transcript = _get_transcript(video_id)
    if not transcript:
        return "I couldn't retrieve a transcript for that video, sir."

    if speak:
        speak("Transcript retrieved. Generating summary now.")

    try:
        summary = _summarize_with_gemini(transcript, url)
    except Exception as e:
        return f"Summary generation failed, sir: {e}"

    if speak:
        speak(summary)

    if parameters.get("save", False):
        saved_path = _save_summary(summary, url)
        return f"Summary complete and saved to Desktop: {saved_path}"

    return summary


def _handle_get_info(parameters: Dict[str, Any], player: Any, speak: Any) -> str:
    url = parameters.get("url", "").strip()
    if not url:
        url = _ask_for_url("Please paste the YouTube video URL:")
    if not url or not _is_valid_youtube_url(url):
        return "Please provide a valid YouTube URL, sir."

    video_id = _extract_video_id(url)
    if not video_id:
        return "Could not extract video ID, sir."

    if player:
        player.write_log(f"[YouTube] Getting info: {url}")

    info = _scrape_video_info(video_id)
    if not info:
        return "Could not retrieve video information, sir."

    lines = [
        f"{key.capitalize()}: {info[key]}"
        for key in ("title", "channel", "views", "duration", "likes")
        if key in info
    ]
    result = "\n".join(lines)

    if speak:
        speak(f"Here's the video info, sir. {result.replace(chr(10), '. ')}")

    return result


def _handle_trending(parameters: Dict[str, Any], player: Any, speak: Any) -> str:
    region = parameters.get("region", "TR").upper()

    if player:
        player.write_log(f"[YouTube] Trending: {region}")

    trending = _scrape_trending(region=region, max_results=8)
    if not trending:
        return f"Could not fetch trending videos for region {region}, sir."

    lines  = [f"Top trending videos in {region}:"]
    lines += [f"{v['rank']}. {v['title']} — {v['channel']}" for v in trending]
    result = "\n".join(lines)

    if speak:
        top3   = trending[:3]
        spoken = "Here are the top trending videos, sir. " + ". ".join(
            f"Number {v['rank']}: {v['title']} by {v['channel']}" for v in top3
        )
        speak(spoken)

    return result

_ACTION_MAP = {
    "play":      _handle_play,
    "summarize": _handle_summarize,
    "get_info":  _handle_get_info,
    "trending":  _handle_trending,
}


def youtube_video(
    parameters:     Dict[str, Any],
    response:       Any = None,
    player:         Any = None,
    session_memory: Any = None,
    speak:          Any = None,
) -> str:
    params = parameters or {}
    action = params.get("action", "play").lower().strip()

    if player:
        player.write_log(f"[YouTube] Action: {action}")
    print(f"[YouTube] ▶️  Action: {action}  Params: {params}")

    handler = _ACTION_MAP.get(action)
    if handler is None:
        return (
            f"Unknown YouTube action: '{action}'. "
            "Available: play, summarize, get_info, trending."
        )

    try:
        if action == "play":
            return handler(params, player) or "Done."
        return handler(params, player, speak) or "Done."
    except Exception as e:
        logger.error(f"Error in {action}: {e}", exc_info=True)
        print(f"[YouTube] ❌ Error in {action}: {e}")
        return f"YouTube {action} failed, sir: {e}"