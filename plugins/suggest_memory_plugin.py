from typing import Dict, Any

class Plugin:
    def __init__(self):
        self.name = "suggest_memory"
        self.description = "Suggest to remember an important fact, preference, or goal about the user."
        self.parameters = {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "A short, descriptive title for the memory (e.g. 'User Name', 'Favourite Editor')"
                },
                "summary": {
                    "type": "STRING",
                    "description": "The actual fact or preference to remember (e.g. 'The user's name is Ravi.')"
                },
                "category": {
                    "type": "STRING",
                    "description": "Category of the memory: Personal, Education, Work, Projects, Coding, Preferences, Schedule, Goals, Custom"
                }
            },
            "required": ["title", "summary", "category"]
        }

    async def execute(self, params: Dict[str, Any], ui, speak, speak_error, perf_state) -> str:
        # Instead of directly saving, we send an AI suggestion to the UI to ask the user.
        # This aligns with the "never save automatically" rule.
        
        # We broadcast the suggestion so the UI can render an interactive card in the chat
        if hasattr(ui, 'broadcast'):
            ui.broadcast({
                "type": "memory_suggestion",
                "title": params.get("title"),
                "summary": params.get("summary"),
                "category": params.get("category")
            })
            return "Successfully sent the memory suggestion to the user for approval. Do NOT ask them yourself, the UI will display a prompt."
        
        return "Error: Could not broadcast memory suggestion. UI not connected."
