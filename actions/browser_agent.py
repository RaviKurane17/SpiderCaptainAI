"""
browser_agent.py — Playwright-based browser automation.
Uses a dedicated background thread with an asyncio event loop to keep a stateful
browser session alive across multiple tool calls without blocking the main app.
"""
import asyncio
import threading
import json
from typing import Dict, Any, Optional

from utils.logger import log

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


class BrowserManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(BrowserManager, cls).__new__(cls)
                cls._instance.initialized = False
            return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.initialized = True
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._start_thread()

    def _start_thread(self):
        self.ready_event = threading.Event()
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="BrowserAgentThread")
        self.thread.start()
        self.ready_event.wait(timeout=5.0)

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        async def init_playwright():
            try:
                self.playwright = await async_playwright().start()
                import os
                
                # First try to connect to an existing browser with remote debugging enabled
                try:
                    self.browser = await self.playwright.chromium.connect_over_cdp("http://localhost:9222")
                    self.context = self.browser.contexts[0]
                    log.info("[BrowserAgent] Successfully connected to existing browser via CDP on port 9222.")
                except Exception:
                    # Fallback to launching a new persistent context
                    user_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "browser_data")
                    os.makedirs(user_data_dir, exist_ok=True)
                    
                    try:
                        self.context = await self.playwright.chromium.launch_persistent_context(
                            user_data_dir=user_data_dir,
                            headless=False,
                            channel="chrome",
                            viewport={"width": 1280, "height": 720},
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        )
                        log.info("[BrowserAgent] Launched with Google Chrome.")
                    except Exception:
                        try:
                            self.context = await self.playwright.chromium.launch_persistent_context(
                                user_data_dir=user_data_dir,
                                headless=False,
                                channel="msedge",
                                viewport={"width": 1280, "height": 720},
                                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                            )
                            log.info("[BrowserAgent] Chrome not found, launched with MS Edge.")
                        except Exception:
                            log.warning("[BrowserAgent] Chrome/Edge not found, falling back to bundled Chromium.")
                            self.context = await self.playwright.chromium.launch_persistent_context(
                                user_data_dir=user_data_dir,
                                headless=False,
                                viewport={"width": 1280, "height": 720}
                            )
                            log.info("[BrowserAgent] Launched with bundled Chromium.")

                self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
                log.info("[BrowserAgent] Playwright session initialized successfully.")
            except Exception as e:
                log.error(f"[BrowserAgent] Failed to initialize Playwright: {e}")
                
        self.loop.run_until_complete(init_playwright())
        self.ready_event.set()
        
        # Run the event loop forever to process submitted coroutines
        self.loop.run_forever()

    def submit_task(self, coro) -> Any:
        """Submit an async task to the dedicated browser thread and wait for result."""
        if not self.loop or not self.loop.is_running():
            raise RuntimeError("Browser event loop is not running.")
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=30.0)

    async def _do_action(self, action: str, params: Dict[str, Any]) -> str:
        if not self.page:
            return "Error: Browser page not initialized. Check if Playwright browsers are installed."
            
        try:
            if action == "navigate":
                url = params.get("url", "")
                if not url.startswith("http"):
                    url = "https://" + url
                await self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
                return f"Navigated to {url}. Title: {await self.page.title()}"

            elif action == "search":
                # Smart search: go to site + fill search box + submit
                site = params.get("site", "google").lower()
                query = params.get("query", params.get("text", ""))
                search_urls = {
                    "google": "https://www.google.com/search?q=",
                    "youtube": "https://www.youtube.com/results?search_query=",
                    "bing": "https://www.bing.com/search?q=",
                    "amazon": "https://www.amazon.com/s?k=",
                    "github": "https://github.com/search?q=",
                }
                if site in search_urls:
                    from urllib.parse import quote_plus
                    url = search_urls[site] + quote_plus(query)
                    await self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    return f"Searched '{query}' on {site.title()}. Title: {await self.page.title()}"
                return f"Unknown site: {site}"

            elif action == "click":
                selector = params.get("selector", "")
                text = params.get("text", "")
                if text:
                    # Find by visible text first
                    try:
                        await self.page.get_by_text(text, exact=False).first.click(timeout=5000)
                        return f"Clicked element with text: {text}"
                    except Exception:
                        pass
                await self.page.click(selector, timeout=5000)
                return f"Clicked: {selector}"

            elif action == "find_and_click":
                # Fuzzy click by text or aria label
                text = params.get("text", params.get("selector", ""))
                try:
                    await self.page.get_by_role("button", name=text).first.click(timeout=4000)
                    return f"Clicked button: {text}"
                except Exception:
                    pass
                try:
                    await self.page.get_by_text(text, exact=False).first.click(timeout=4000)
                    return f"Clicked element: {text}"
                except Exception as e:
                    return f"Could not find clickable element '{text}': {e}"

            elif action == "fill":
                selector = params.get("selector", "input")
                text = params.get("text", "")
                await self.page.fill(selector, text, timeout=5000)
                return f"Filled '{text}' into {selector}"

            elif action == "submit":
                selector = params.get("selector", "button[type=submit]")
                try:
                    await self.page.click(selector, timeout=5000)
                    return "Form submitted."
                except Exception:
                    await self.page.keyboard.press("Enter")
                    return "Pressed Enter to submit."

            elif action == "extract_text":
                selector = params.get("selector", "body")
                text = await self.page.inner_text(selector, timeout=5000)
                if len(text) > 3000:
                    text = text[:3000] + "\n...[truncated]"
                return f"Page content:\n{text}"

            elif action == "get_url":
                return f"Current URL: {self.page.url}"

            elif action == "scroll_to":
                selector = params.get("selector", "")
                text = params.get("text", "")
                if text:
                    await self.page.get_by_text(text, exact=False).first.scroll_into_view_if_needed()
                    return f"Scrolled to: {text}"
                if selector:
                    await self.page.locator(selector).scroll_into_view_if_needed()
                    return f"Scrolled to: {selector}"
                await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
                return "Scrolled down one page."

            elif action == "scroll_down":
                await self.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
                return "Scrolled down."

            elif action == "scroll_up":
                await self.page.evaluate("window.scrollBy(0, -window.innerHeight * 0.8)")
                return "Scrolled up."

            elif action == "wait_for":
                selector = params.get("selector", "")
                seconds = params.get("seconds", 2)
                if selector:
                    await self.page.wait_for_selector(selector, timeout=int(seconds)*1000)
                    return f"Element appeared: {selector}"
                import asyncio as _asyncio
                await _asyncio.sleep(float(seconds))
                return f"Waited {seconds} seconds."

            elif action == "screenshot":
                path = params.get("path", "browser_screenshot.png")
                await self.page.screenshot(path=path)
                return f"Screenshot saved to {path}"

            elif action == "close":
                if self.context:
                    await self.context.close()
                if self.playwright:
                    await self.playwright.stop()
                self.loop.stop()
                return "Browser closed."

            else:
                return f"Unknown action: {action}"

        except Exception as e:
            return f"Action '{action}' failed: {str(e)}"

    def run_action(self, action: str, params: Dict[str, Any]) -> str:
        if not _PLAYWRIGHT_AVAILABLE:
            return "Playwright is not installed. Please run: pip install playwright && playwright install chromium"
        return self.submit_task(self._do_action(action, params))

    def execute_js(self, script: str) -> Any:
        async def _eval():
            if not self.page: return None
            return await self.page.evaluate(script)
        return self.submit_task(_eval())

    def open_url(self, url: str) -> str:
        async def _nav():
            if not self.page: return "Browser not initialized"
            await self.page.goto(url, wait_until="domcontentloaded")
            await self.page.bring_to_front()
            return f"Opened {url}"
        return self.submit_task(_nav())

# Singleton instance
_manager = None

def get_browser_manager():
    global _manager
    if not _manager:
        _manager = BrowserManager()
    return _manager

def browser_agent(parameters: dict, player=None) -> str:
    manager = get_browser_manager()
        
    action = parameters.get("action", "")
    if not action:
        return "Error: No action provided."
        
    log.info(f"[BrowserAgent] Executing action: {action} with params: {parameters}")
    return manager.run_action(action, parameters)
