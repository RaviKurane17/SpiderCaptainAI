"""
CAPTAIN AI Plugin — Read Calendar
Allows the AI to read today's tasks and reminders.
"""

import json
import os

REMINDERS_PATH = os.path.join("memory", "reminders.json")

def _handler(parameters: dict, player=None, speak=None) -> str:
    if not os.path.exists(REMINDERS_PATH):
        return "You have no tasks or reminders scheduled."
        
    try:
        with open(REMINDERS_PATH, "r", encoding="utf-8") as f:
            reminders = json.load(f)
            
        if not reminders:
            return "You have no tasks or reminders scheduled."
            
        res = ["Here is the user's calendar/tasks:"]
        for r in reminders:
            title = r.get("title", "Task")
            time_str = r.get("time", "Later")
            desc = r.get("desc", "")
            res.append(f"- {title} at {time_str} ({desc})")
            
        return "\n".join(res)
    except Exception as e:
        return f"Failed to read calendar: {e}"

def register() -> dict:
    return {
        "name": "read_calendar",
        "description": (
            "Reads the user's calendar, fetching all scheduled tasks and reminders. "
            "Use this when the user asks 'what are my tasks for today', 'read my calendar', 'what do I have scheduled', etc."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": _handler,
        "author": "Captain AI Core",
        "version": "1.0.0"
    }
