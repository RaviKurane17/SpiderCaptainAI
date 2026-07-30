import time
import json
import io
import threading
import concurrent.futures
import hashlib
from collections import OrderedDict
from typing import Dict, Any, Optional, Tuple

try:
    import pyautogui
    from PIL import Image
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

from actions.vision import vision_provider
from actions.computer_control import computer_control as legacy_computer_control
from utils.logger import log

VISION_CONFIDENCE = 0.80
MAX_CACHE = 100

_automation_lock = threading.Lock()
_cache_lock = threading.Lock()
_element_cache = OrderedDict()  # Format: { cache_key: (model_x, model_y) }
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def _cache_set(key: Tuple[Any, ...], val: Tuple[int, int]):
    with _cache_lock:
        if key in _element_cache:
            _element_cache.move_to_end(key)
        _element_cache[key] = val
        if len(_element_cache) > MAX_CACHE:
            _element_cache.popitem(last=False)

def _cache_get(key: Tuple[Any, ...]) -> Optional[Tuple[int, int]]:
    with _cache_lock:
        if key in _element_cache:
            _element_cache.move_to_end(key)
            return _element_cache[key]
        return None

def _compress_screenshot(img: 'Image.Image', max_size: int = 1280) -> Tuple[bytes, float, str]:
    tiny_img = img.convert("L").resize((64, 64), Image.Resampling.NEAREST)
    raw_hash = hashlib.sha256(tiny_img.tobytes()).hexdigest()
    
    w, h = img.size
    scale = 1.0
    if max(w, h) > max_size:
        scale = max_size / float(max(w, h))
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
        
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), scale, raw_hash

def _take_screenshot() -> Tuple[bytes, float, str, int, int]:
    if not _PYAUTOGUI:
        raise RuntimeError("PyAutoGUI not available.")
    
    img = None
    offset_x, offset_y = 0, 0
    sw, sh = pyautogui.size()
    
    try:
        import pygetwindow as gw
        window = gw.getActiveWindow()
        if window and window.width > 0 and window.height > 0:
            left = max(0, window.left)
            top = max(0, window.top)
            width = min(sw - left, window.width)
            height = min(sh - top, window.height)
            
            if width > 0 and height > 0:
                img = pyautogui.screenshot(region=(left, top, width, height))
                offset_x, offset_y = left, top
    except Exception:
        pass
        
    if img is None:
        img = pyautogui.screenshot()
        
    img_bytes, scale, raw_hash = _compress_screenshot(img)
    return img_bytes, scale, raw_hash, offset_x, offset_y

def _execute_deterministic_action(action: str, params: dict) -> str:
    if action == "move_mouse":
        params["action"] = "move"
    elif action == "press_key":
        params["action"] = "press"
    elif action in ("find_element", "verify_element"):
        pass 
    else:
        params["action"] = action
    return legacy_computer_control(params)

def _call_with_timeout(func, timeout: float, *args, **kwargs) -> Dict[str, Any]:
    future = _executor.submit(func, *args, **kwargs)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        return {"reason": "TIMEOUT", "message": f"Action timed out after {timeout}s"}
    except Exception as e:
        return {"reason": "EXECUTION_ERROR", "message": str(e)}

def computer_use_action(parameters: dict, player=None) -> str:
    start_time = time.time()
    params = parameters or {}
    action = params.get("action", "").lower().strip()
    target_description = params.get("target_description", "")
    
    verify = params.get("verify", False)
    if action in ("scroll", "wait", "move_mouse", "describe_screen"):
        verify = False
        
    verify_description = params.get("verify_description", "")
    timeout = params.get("timeout", 8.0)
    
    result = {
        "success": False,
        "action": action,
        "target": target_description or action,
        "retry_count": 0
    }

    if not action:
        result["reason"] = "No action specified"
        return json.dumps(result)

    if not _PYAUTOGUI:
        result["reason"] = "PyAutoGUI not installed"
        return json.dumps(result)

    sw, sh = pyautogui.size() if _PYAUTOGUI else (0, 0)
    requires_vision = action in ("click", "double_click", "right_click", "move_mouse", "drag", "find_element") and target_description
    
    if requires_vision:
        capture_start = time.time()
        img_bytes, scale, raw_hash, offset_x, offset_y = _take_screenshot()
        log.info(f"[ComputerUse] Capture Latency: {int((time.time() - capture_start)*1000)} ms")
        
        cache_key = (raw_hash, target_description, sw, sh, scale)
        
        cached_coords = _cache_get(cache_key)
        if cached_coords:
            log.info("[ComputerUse] Cache HIT")
            model_x, model_y = cached_coords
            vision_res = {"found": True, "confidence": 1.0, "x": model_x, "y": model_y}
        else:
            log.info("[ComputerUse] Cache MISS")
            
            max_retries = 1
            vision_res = {"found": False, "reason": "NOT_FOUND"}
            
            for attempt in range(max_retries + 1):
                result["retry_count"] = attempt
                vision_start = time.time()
                
                vision_res = vision_provider.find_element(img_bytes, target_description, timeout=timeout)
                
                log.info(f"[ComputerUse] Vision Latency (Attempt {attempt+1}): {int((time.time() - vision_start)*1000)} ms")
                
                reason = vision_res.get("reason", "")
                # Retry on transient failures
                if vision_res.get("found", False) or reason not in ("NOT_FOUND", "LOW_CONFIDENCE", "TIMEOUT", "INVALID_JSON"):
                    break
                    
                if attempt < max_retries:
                    delay = 0.5 * (2 ** attempt)
                    log.info(f"[ComputerUse] Retry backoff: sleeping {delay}s")
                    time.sleep(delay)
                    
                    capture_start = time.time()
                    img_bytes, scale, new_hash, offset_x, offset_y = _take_screenshot()
                    log.info(f"[ComputerUse] Capture Latency (Retry): {int((time.time() - capture_start)*1000)} ms")
                    
                    if new_hash == raw_hash:
                        log.info("[ComputerUse] Screen hash unchanged, aborting retry.")
                        break 
                    
                    raw_hash = new_hash
                    cache_key = (raw_hash, target_description, sw, sh, scale)

        if not vision_res.get("found", False):
            result["success"] = False
            result["reason"] = vision_res.get("reason", "NOT_FOUND")
            result["message"] = f"Element '{target_description}' not found. " + vision_res.get("message", "")
            result["confidence"] = vision_res.get("confidence", 0.0)
            result["duration_ms"] = int((time.time() - start_time) * 1000)
            return json.dumps(result)
            
        if vision_res.get("confidence", 0) < VISION_CONFIDENCE:
            result["success"] = False
            result["reason"] = "LOW_CONFIDENCE"
            result["message"] = f"Found element but confidence ({vision_res.get('confidence')}) was below threshold ({VISION_CONFIDENCE})."
            result["confidence"] = vision_res.get("confidence")
            result["duration_ms"] = int((time.time() - start_time) * 1000)
            return json.dumps(result)

        model_x = vision_res.get("x", 0)
        model_y = vision_res.get("y", 0)
        
        _cache_set(cache_key, (model_x, model_y))
        
        target_x = int((model_x / scale) + offset_x)
        target_y = int((model_y / scale) + offset_y)
        
        # 3. Validate coordinates against screen boundaries
        if not (0 <= target_x < sw and 0 <= target_y < sh):
            result["success"] = False
            result["reason"] = "INVALID_COORDINATES"
            result["message"] = f"Model returned out of bounds coordinates: ({target_x}, {target_y})"
            result["duration_ms"] = int((time.time() - start_time) * 1000)
            return json.dumps(result)
            
        params["x"] = target_x
        params["y"] = target_y
        result["confidence"] = vision_res.get("confidence", 1.0)
        
        if action == "find_element":
            result["success"] = True
            result["message"] = f"Found element at {params['x']}, {params['y']}"
            result["duration_ms"] = int((time.time() - start_time) * 1000)
            return json.dumps(result)

    # 5. Clear cache on UI mutating actions
    if action in ("click", "double_click", "right_click", "drag", "type", "press_key", "hotkey"):
        with _cache_lock:
            _element_cache.clear()
        log.info("[ComputerUse] Cache Invalidated due to mutating action.")

    try:
        if action in ("click", "double_click", "right_click", "move_mouse", "drag") and not params.get("x") and not params.get("y"):
             result["success"] = False
             result["reason"] = "MISSING_COORDS"
             result["message"] = "Cannot execute mouse action without coordinates or a target_description."
             result["duration_ms"] = int((time.time() - start_time) * 1000)
             return json.dumps(result)
        
        def _do_action():
            with _automation_lock:
                return _execute_deterministic_action(action, params)
            
        exec_timeout = 5.0
        if "wait" in action:
            exec_timeout = timeout
            
        exec_res = _call_with_timeout(_do_action, exec_timeout)
        if isinstance(exec_res, dict) and exec_res.get("reason"):
            result["success"] = False
            result["reason"] = exec_res["reason"]
            result["message"] = exec_res["message"]
            result["duration_ms"] = int((time.time() - start_time) * 1000)
            return json.dumps(result)
            
        result["success"] = True
        result["message"] = exec_res
    except Exception as e:
        result["success"] = False
        result["reason"] = "EXECUTION_ERROR"
        result["message"] = str(e)
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        return json.dumps(result)

    if verify and result["success"]:
        time.sleep(1.0)
        
        cap_v_start = time.time()
        img_bytes, _, _, _, _ = _take_screenshot()
        log.info(f"[ComputerUse] Capture (Verify) Latency: {int((time.time() - cap_v_start)*1000)} ms")
        
        verify_desc = verify_description or f"Did the action '{action}' on '{target_description or action}' succeed?"
        
        ver_start = time.time()
        v_res = vision_provider.verify_state(img_bytes, verify_desc, timeout=timeout)
        log.info(f"[ComputerUse] Verify Vision Latency: {int((time.time() - ver_start)*1000)} ms")
        
        is_verified = v_res.get("verified", False)
        v_confidence = v_res.get("confidence", 0.0)
        
        if is_verified and v_confidence < VISION_CONFIDENCE:
            is_verified = False
            v_res["reason"] = f"Verification true but low confidence ({v_confidence})"
            
        result["verified"] = is_verified
        if not is_verified:
            result["success"] = False
            result["reason"] = v_res.get("reason", "UNEXPECTED_STATE")
            result["message"] = f"Verification failed: {v_res.get('message', '')}"
    else:
        log.info("[ComputerUse] Verify: Skipped")

    if "confidence" not in result:
        result["confidence"] = 1.0 if result["success"] else 0.0

    result["duration_ms"] = int((time.time() - start_time) * 1000)
    log.info(f"[ComputerUse] Total Duration: {result['duration_ms']} ms")
    return json.dumps(result)
