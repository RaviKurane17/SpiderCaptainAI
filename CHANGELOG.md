# Changelog

All notable changes to **Captain AI** are documented here.

---

## [v2.2.0] - 2026-08-22

### Added
- **Playwright AI Browser Engine** (rowser_agent.py): A persistent, stateful Chromium session runs in the background. Saves cookies and login sessions across restarts. Falls back to bundled Chromium if Chrome is not installed.
- **True Background YouTube Media Control**: Captain now injects JavaScript directly into the Playwright browser to play/pause/seek YouTube videos — works even when the window is minimized or behind a game. No more window focus switching.
- **Offline Mode Expansion** (offline_parser.py): Added 40+ new hardcoded offline commands:
  - Full keyboard shortcut support: Ctrl+C, Ctrl+V, Win+R, Alt+Tab, Ctrl+Z/Y, F11, etc.
  - Clipboard operations: copy, paste, cut, undo, redo, select all
  - Extended system controls: restart, shutdown, sleep display, WiFi, dark mode
  - File/folder open and search commands
  - Smart media control with Playwright-first, PyAutoGUI fallback
- **Wake Word Safety Improvement**: equires_captain guard now uses safe default behavior — only blocks tool execution when AI explicitly signals background noise, preventing false rejections of valid commands.
- **PyAutoGUI Fail-Safe Disabled**: Captain no longer crashes when your mouse is resting in a screen corner.

### Fixed
- youtube_video tool schema was missing pause, unpause, 
ext, previous, seek_forward, seek_backward actions — Gemini could not use them.
- computer_control schema was missing screen_double_click action — Gemini never used it.
- Prompt incorrectly instructed Gemini to skip YouTube using arrow keys instead of the youtube_video tool.
- BrowserAgent crashed if Google Chrome was not installed (channel='chrome' hard-coded).

### Removed
- **Ollama local LLM fallback** from offline mode: Removed due to excessive CPU/RAM usage causing laptop freezes. Replaced with a zero-cost regex/datetime conversational engine.

---

## [v2.1.0] - 2026-08-21

### Added
- Session resumption support for Gemini Live Audio (reconnects instantly, preserving context)
- Barge-in detection: Captain stops speaking immediately when interrupted
- Local VAD (Voice Activity Detection): Filters out background noise before sending to Gemini
- Pre-roll audio buffer: Prevents the start of words from being clipped
- equires_captain wake-word guard on tool dispatcher

### Fixed
- Commands executing on background conversations/TV audio
- Skip 20s requiring window focus (now uses JS injection)
- win+r crashing due to PyAutoGUI failsafe

---

## [v2.0.0] - 2026-07-30

### Added
- PyQt6 holographic HUD UI with animated orb
- Gemini 2.5 Flash Live Audio streaming
- Firebase mobile link (phone agent)
- Plugin system for extensible tools
- Deep file indexing engine
- Screen processor with OCR and visual context
