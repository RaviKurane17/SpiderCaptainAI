from .provider import VisionProvider
from .gemini_provider import GeminiVisionProvider

# Expose a default provider instance
vision_provider: VisionProvider = GeminiVisionProvider()
