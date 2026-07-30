import json
import sys
from pathlib import Path
from typing import Dict, Any

def _get_api_key() -> str:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent.parent.parent

    config_path = base / "config" / "api_keys.json"
    try:
        return json.loads(config_path.read_text(encoding="utf-8")).get("gemini_api_key", "")
    except Exception:
        return ""

from actions.vision.provider import VisionProvider

class GeminiVisionProvider(VisionProvider):
    def __init__(self):
        self.api_key = _get_api_key()
        self.client = None
        if not self.api_key:
            print("[GeminiVisionProvider] ⚠️ No API key found for Gemini.")
        else:
            try:
                from google import genai
                # Initialize client once
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[GeminiVisionProvider] ⚠️ Failed to init client: {e}")

    def find_element(self, image_bytes: bytes, description: str, timeout: float = 8.0) -> Dict[str, Any]:
        result = {"found": False, "reason": "NOT_FOUND"}
        if not self.client:
            result["reason"] = "NO_API_KEY"
            return result

        try:
            from google.genai import types as gtypes
            
            prompt = (
                "You are analysing a Windows desktop screenshot.\n"
                f"Find the exact center of: '{description}'\n\n"
                "Return ONLY JSON.\n"
                '{\n "found":true,\n "x":415,\n "y":320,\n "confidence":0.97\n}\n\n'
                "Rules:\n"
                "- Do not explain.\n"
                "- Do not use markdown.\n"
                "- Coordinates must refer to the uploaded image.\n"
                "- If uncertain or not visible:\n"
                '{\n "found":false,\n "reason":"LOW_CONFIDENCE"\n}'
            )

            # Pass timeout via http_options natively so we don't leave orphaned threads
            config = gtypes.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
                http_options=gtypes.HttpOptions(timeout=timeout)
            )

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    gtypes.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    prompt,
                ],
                config=config
            )

            text = (response.text or "").strip()
            # Clean potential markdown wrapping
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            try:
                data = json.loads(text.strip())
            except json.JSONDecodeError:
                result["reason"] = "INVALID_JSON"
                result["message"] = "Model returned malformed JSON"
                return result
            
            result["found"] = data.get("found", False)
            if result["found"]:
                result["x"] = data.get("x", 0)
                result["y"] = data.get("y", 0)
                result["confidence"] = data.get("confidence", 1.0)
            else:
                result["reason"] = data.get("reason", "NOT_FOUND")

            return result

        except Exception as e:
            err_msg = str(e).lower()
            if "timeout" in err_msg or "deadline" in err_msg:
                result["reason"] = "TIMEOUT"
            else:
                result["reason"] = "API_ERROR"
            result["message"] = str(e)
            print(f"[GeminiVisionProvider] ⚠️ find_element failed: {e}")
            return result

    def verify_state(self, image_bytes: bytes, description: str, timeout: float = 5.0) -> Dict[str, Any]:
        result = {"verified": False, "reason": "NOT_VERIFIED"}
        if not self.client:
            result["reason"] = "NO_API_KEY"
            return result

        try:
            from google.genai import types as gtypes
            
            prompt = (
                f"Verify the following outcome on the screen: '{description}'.\n"
                "Return ONLY a JSON response in exactly this format:\n"
                '{\n "verified": true,\n "confidence": 0.95,\n "reason": "Short explanation"\n}\n'
                "Rules:\n"
                "- Do not explain outside JSON.\n"
                "- Do not use markdown."
            )

            config = gtypes.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
                http_options=gtypes.HttpOptions(timeout=timeout)
            )

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    gtypes.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    prompt,
                ],
                config=config
            )

            text = (response.text or "").strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
                
            try:
                data = json.loads(text.strip())
            except json.JSONDecodeError:
                result["reason"] = "INVALID_JSON"
                result["message"] = "Model returned malformed JSON"
                return result
            
            result["verified"] = data.get("verified", False)
            result["confidence"] = data.get("confidence", 0.0)
            result["reason"] = data.get("reason", "Unknown reason")

            return result
            
        except Exception as e:
            err_msg = str(e).lower()
            if "timeout" in err_msg or "deadline" in err_msg:
                result["reason"] = "TIMEOUT"
            else:
                result["reason"] = "API_ERROR"
            result["message"] = str(e)
            print(f"[GeminiVisionProvider] ⚠️ verify_state failed: {e}")
            return result
