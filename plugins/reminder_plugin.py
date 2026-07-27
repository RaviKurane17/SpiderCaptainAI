"""
CAPTAIN AI Plugin — Set Reminder
Allows the AI to add a reminder to the dashboard calendar.
"""

import json
import os
from datetime import datetime

REMINDERS_PATH = os.path.join("memory", "reminders.json")

def _handler(parameters: dict, player=None, speak=None) -> str:
    title = parameters.get("title", "New Reminder")
    desc = parameters.get("desc", "")
    time_str = parameters.get("time", "Later")
    
    # Load existing reminders
    reminders = []
    if os.path.exists(REMINDERS_PATH):
        try:
            with open(REMINDERS_PATH, "r", encoding="utf-8") as f:
                reminders = json.load(f)
        except Exception:
            pass
            
    # Add new reminder
    new_reminder = {
        "icon": "📅",
        "title": title,
        "desc": desc,
        "time": time_str,
        "color": "#00d4ff" # cyan
    }
    reminders.append(new_reminder)
    
    # Save back
    try:
        os.makedirs(os.path.dirname(REMINDERS_PATH), exist_ok=True)
        with open(REMINDERS_PATH, "w", encoding="utf-8") as f:
            json.dump(reminders, f, indent=2)
            
        try:
            from core.websocket_server import bridge_instance
            if bridge_instance:
                bridge_instance.broadcast({
                    "type": "reminders_data",
                    "data": reminders
                })
        except Exception:
            pass
            
        return f"Successfully added reminder: {title} at {time_str}"
    except Exception as e:
        return f"Failed to save reminder: {e}"

def register() -> dict:
    return {
        "name": "set_reminder",
        "description": (
            "Creates a new reminder or calendar event and saves it to the dashboard. "
            "Use this when the user asks you to remind them about something or schedule an event."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "The main title of the reminder (e.g. 'College Class', 'Call Mom')"
                },
                "desc": {
                    "type": "STRING",
                    "description": "A short description or subtext for the reminder"
                },
                "time": {
                    "type": "STRING",
                    "description": "The time or date the reminder is for, formatted for display (e.g. '09:00 AM\\nTomorrow')"
                }
            },
            "required": ["title", "time"]
        },
        "handler": _handler,
        "author": "Captain AI Core",
        "version": "1.0.0"
    }
