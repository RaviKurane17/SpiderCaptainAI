import firebase_admin
from firebase_admin import credentials, db
import time
import os
import base64
try:
    from geopy.geocoders import Nominatim
except ImportError:
    Nominatim = None

from utils.config import get_firebase_key_path, get_phone_device_id, get_firebase_db_url
from utils.logger import log

def _ensure_firebase():
    """Ensure Firebase is initialized using config paths."""
    if not firebase_admin._apps:
        try:
            fb_key = get_firebase_key_path()
            if not fb_key.exists():
                log.warning(f"[phone_agent] Firebase key not found at {fb_key}")
                return False
            cred = credentials.Certificate(str(fb_key))
            firebase_admin.initialize_app(cred, {
                'databaseURL': get_firebase_db_url()
            })
            return True
        except Exception as e:
            log.error(f"[phone_agent] Firebase Init Error: {e}")
            return False
    return True

def phone_agent(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Action handler to send a command to the Android phone via Firebase Realtime Database.
    Expects 'action' in parameters (e.g., 'battery', 'location', 'contact_search', 'sms', 'call').
    """
    action = (parameters or {}).get("action", "").strip()

    if not action:
        return "No phone action provided."

    if not _ensure_firebase():
         return "Firebase is not initialized. Check your JSON key path in .env."

    device_id = get_phone_device_id()
    if not device_id:
        return "Phone device ID is not configured in .env."

    try:
        commands_ref = db.reference('commands')
        
        # Create the command payload
        new_command = {
            "targetDeviceId": device_id,
            "action": action,
            "status": "pending",
            "timestamp": int(time.time() * 1000)
        }
        
        # Add additional parameters if present
        if "name" in (parameters or {}):
            new_command["name"] = parameters["name"]
        if "number" in (parameters or {}):
            new_command["number"] = parameters["number"]
        if "message" in (parameters or {}):
            new_command["message"] = parameters["message"]
        if "value" in (parameters or {}):
            new_command["value"] = parameters["value"]
        if "time" in (parameters or {}):
            new_command["time"] = parameters["time"]
            
        if action == "read_notifications":
            notifs_ref = db.reference('notifications')
            results = notifs_ref.order_by_key().limit_to_last(20).get()
            if results:
                msgs = []
                for key, notif in results.items():
                    if isinstance(notif, dict) and notif.get("deviceId") == device_id:
                        app = notif.get("package", "App").replace("com.whatsapp", "WhatsApp").replace("org.telegram.messenger", "Telegram").replace("com.instagram.android", "Instagram")
                        title = notif.get("title", "")
                        text = notif.get("text", "")
                        msgs.append(f"[{app}] {title}: {text}")
                
                if msgs:
                    return "Recent Phone Notifications:\n" + "\n".join(msgs[-5:])
                else:
                    return "You have no recent notifications on your phone."
            else:
                return "You have no recent notifications on your phone."
                
        if action == "read_voice_commands":
            cmds_ref = db.reference('commands')
            results = cmds_ref.order_by_key().limit_to_last(10).get()
            if results:
                msgs = []
                for key, cmd in results.items():
                    if isinstance(cmd, dict) and cmd.get("action") == "voice_command":
                        msgs.append(f"Voice Command: {cmd.get('message', '')}")
                if msgs:
                    return "Recent Voice Commands from your Phone:\n" + "\n".join(msgs)
                else:
                    return "No recent voice commands found."
            else:
                return "No recent voice commands found."
                
        # Push to Realtime Database
        new_cmd_ref = commands_ref.push(new_command)
        command_id = new_cmd_ref.key
        
        if player:
            player.write_log(f"[phone_agent] Sent {action} to phone, waiting for response...")
            
        # Poll for a response
        responses_ref = db.reference('responses')
        timeout = 10  # wait up to 10 seconds
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Fetch the last few responses to avoid needing an index rule
            results = responses_ref.order_by_key().limit_to_last(20).get()
            
            if results:
                for key, response_data in results.items():
                    if isinstance(response_data, dict) and response_data.get("commandId") == command_id:
                        status = response_data.get("status")
                        if status == "success":
                            if action == "battery":
                                return f"Your phone's battery is at {response_data.get('battery', 'unknown')}%."
                            elif action == "location":
                                lat = response_data.get('latitude')
                                lon = response_data.get('longitude')
                                maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                                area_name = ""
                                if Nominatim:
                                    try:
                                        geolocator = Nominatim(user_agent="captain_agent")
                                        location_data = geolocator.reverse(f"{lat}, {lon}")
                                        if location_data and location_data.address:
                                            area_name = f"\nExact Area: {location_data.address}"
                                    except Exception as ge_e:
                                        print(f"Geocoding error: {ge_e}")
                                return f"Your phone is at latitude {lat}, longitude {lon}.{area_name}\nMap Link: {maps_link}"
                            elif action == "contact_search":
                                return f"Found contact number: {response_data.get('number')}"
                            elif action == "open_app":
                                return f"Opened the app on your phone."
                            elif action == "whatsapp":
                                return f"Opened WhatsApp and automatically attempted to send the message to the contact."
                            elif action == "home":
                                return f"Closed apps and returned to the home screen on your phone."
                            elif action == "volume":
                                return f"Set the phone media volume to {parameters.get('value')}%."
                            elif action == "brightness":
                                return f"Set the phone screen brightness to {parameters.get('value')}%."
                            elif action == "alarm":
                                return f"Set an alarm on your phone for {parameters.get('time')}."
                            elif action == "lock_screen":
                                return f"Locked the phone screen."
                            elif action == "screenshot":
                                return f"Took a screenshot on your phone."
                            elif action == "open_notifications":
                                return f"Opened the notification panel on your phone."
                            elif action == "torch":
                                state = "ON" if parameters.get('value') == 1 else "OFF"
                                return f"Turned the phone flashlight {state}."
                            elif action == "bluetooth":
                                state = "ON" if parameters.get('value') == 1 else "OFF"
                                return f"Turned the phone Bluetooth {state}."
                            elif action == "wifi":
                                state = "ON" if parameters.get('value') == 1 else "OFF"
                                return f"Attempted to turn phone Wi-Fi {state}. (Note: On Android 10+, this opens the settings panel instead of silently toggling)."
                            elif action == "sys_info":
                                return f"Phone System Info: {response_data.get('message', 'Unavailable')}"
                            elif action == "read_screen":
                                return f"Phone Screen Content:\n{response_data.get('message', 'No text visible on screen.')}"
                            elif action == "find_phone":
                                return f"Triggered the loud siren on your phone to help you find it!"
                            elif action == "speak":
                                return f"Made your phone speak the message out loud."
                            elif action == "play_media":
                                return f"Playing '{parameters.get('name')}' on your phone (attempting auto-play on YouTube)."
                            elif action == "web_search":
                                return f"Opened the web browser on your phone and searched for '{parameters.get('message')}'."
                            elif action == "copy_to_phone":
                                return f"Copied the text to your phone's clipboard."
                            elif action == "read_sms":
                                return f"Recent SMS messages from your phone:\n{response_data.get('message', 'No messages found.')}"
                            elif action == "read_calls":
                                return f"Recent Call Logs from your phone:\n{response_data.get('message', 'No call logs found.')}"
                            elif action == "take_picture":
                                b64_data = response_data.get('message', '')
                                if b64_data:
                                    try:
                                        img_data = base64.b64decode(b64_data)
                                        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", f"camera_capture_{int(time.time())}.jpg")
                                        with open(desktop_path, "wb") as f:
                                            f.write(img_data)
                                        return f"Successfully captured a picture from your phone's camera! I saved it to your Desktop as {os.path.basename(desktop_path)}"
                                    except Exception as img_e:
                                        return f"Captured picture but failed to decode: {img_e}"
                                return f"Failed to get image data."
                            elif action == "write_note":
                                return f"Opened your Notes app with your dictated text."
                            elif action == "vision_capture":
                                b64_data = response_data.get('message', '')
                                if b64_data:
                                    try:
                                        img_data = base64.b64decode(b64_data)
                                        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", f"screen_vision_{int(time.time())}.jpg")
                                        with open(desktop_path, "wb") as f:
                                            f.write(img_data)
                                        return f"Successfully captured the phone screen! I saved it to your Desktop as {os.path.basename(desktop_path)}"
                                    except Exception as img_e:
                                        return f"Captured screen but failed to decode: {img_e}"
                                return f"Failed to get screen image data."
                            elif action == "auto_click":
                                return f"Successfully clicked the text '{parameters.get('message')}' on the phone screen."
                            elif action == "auto_scroll":
                                return f"Successfully scrolled the phone screen."
                            elif action == "auto_type":
                                return f"Successfully typed the text into the active input field."
                            elif action == "unlock_screen":
                                return f"Successfully woke up the phone, swiped up, and entered the PIN to unlock it."
                            elif action == "reply_notification":
                                return f"Successfully replied '{parameters.get('message')}' to the notification from {parameters.get('number')} on {parameters.get('name')}."
                            else:
                                return f"Phone successfully executed the '{action}' command."
                        else:
                            error_msg = response_data.get('error', 'Unknown error')
                            return f"Phone failed to execute '{action}'. Error: {error_msg}"
                        
            time.sleep(1) # wait 1 second before polling again
            
        return f"Sent '{action}' command to your phone, but it timed out waiting for a response. Check your phone's connection."
        
    except Exception as e:
        print(f"[phone_agent] Error sending command: {e}")
        return f"Failed to send command to phone: {e}"
