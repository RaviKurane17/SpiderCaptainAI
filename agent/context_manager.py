"""
context_manager.py — Context injection and optional translation for agent steps.
Language detection is done locally (no LLM call) using a lightweight heuristic.
Only one LLM call is made when translation is actually needed.
"""
import re
from typing import Dict, Any
from utils.logger import log

# ── Fast local language detection ─────────────────────────────────────────────
# Covers the most common scripts. Falls back to English for anything ambiguous.
_SCRIPT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"[\u0600-\u06FF]"), "Arabic"),
    (re.compile(r"[\u0900-\u097F]"), "Hindi"),
    (re.compile(r"[\u4E00-\u9FFF]"), "Chinese"),
    (re.compile(r"[\u3040-\u30FF]"), "Japanese"),
    (re.compile(r"[\uAC00-\uD7AF]"), "Korean"),
    (re.compile(r"[\u0400-\u04FF]"), "Russian"),
    (re.compile(r"[\u0370-\u03FF]"), "Greek"),
    (re.compile(r"[\u0E00-\u0E7F]"), "Thai"),
    (re.compile(r"[\u0590-\u05FF]"), "Hebrew"),
]

# Common Turkish-specific characters that don't appear in other Latin scripts
_TURKISH_RE = re.compile(r"[çğıöşüÇĞİÖŞÜ]")


def detect_language_fast(text: str) -> str:
    """
    Detect language from the first 300 chars using script heuristics.
    Zero network calls, < 1ms.
    """
    if not text:
        return "English"
    sample = text[:300]
    for pattern, lang in _SCRIPT_PATTERNS:
        if pattern.search(sample):
            return lang
    if _TURKISH_RE.search(sample):
        return "Turkish"
    return "English"


def translate_to_goal_language(content: str, goal: str) -> str:
    """
    Translate content into the language of `goal`.
    Skips translation entirely if goal appears to be English.
    Makes exactly ONE LLM call.
    """
    if not goal or not content:
        return content

    target_lang = detect_language_fast(goal)
    if target_lang == "English":
        return content   # no translation needed

    log.info(f"[Context] 🌐 Translating to: {target_lang}")
    try:
        from agent.llm_client import get_model
        model = get_model(model_name="gemini-2.5-flash")
        prompt = (
            f"Translate the following text into {target_lang}.\n"
            f"IMPORTANT: Translate EVERYTHING. Keep all facts, numbers and structure intact.\n"
            f"Output ONLY the translated text.\n\n"
            f"{content[:4000]}"
        )
        response = model.generate_content(prompt)
        translated = response.text.strip()
        log.info(f"[Context] ✅ Translation done ({target_lang})")
        return translated
    except Exception as exc:
        log.warning(f"[Context] ⚠️ Translation failed: {exc}")
        return content


def inject_context(params: Dict[str, Any], tool: str,
                   step_results: Dict[Any, Any], goal: str = "") -> Dict[str, Any]:
    """
    For file_controller write steps with no content, inject the combined
    results from previous steps (and translate if needed).
    """
    if not step_results:
        return params

    params_copy = dict(params)

    if tool == "file_controller" and params_copy.get("action") in ("write", "create_file"):
        content = params_copy.get("content", "")
        if not content or len(content) < 50:
            all_results = [
                v for v in step_results.values()
                if v and isinstance(v, str) and len(v) > 100
                and v not in ("Done.", "Completed.")
            ]
            if all_results:
                combined = "\n\n---\n\n".join(all_results)
                translated = translate_to_goal_language(combined, goal)
                params_copy["content"] = translated
                log.info("[Context] 💉 Injected + translated content")

    return params_copy
