from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, Any

class VisionProvider(ABC):
    """
    Abstract interface for Vision Providers to decouple computer_use
    from the specific LLM vision implementation.
    """

    @abstractmethod
    def find_element(self, image_bytes: bytes, description: str, timeout: float = 8.0) -> Dict[str, Any]:
        """
        Locates an element on the screen described by `description`.
        Receives compressed image bytes.
        Returns a dict: {"found": bool, "x": int, "y": int, "confidence": float, "reason": str}
        The (x, y) are in the coordinate space of the PROVIDED image_bytes.
        """
        pass

    @abstractmethod
    def verify_state(self, image_bytes: bytes, description: str, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Verifies if the screen state matches the expected `description`.
        Returns a dict: {"verified": bool, "confidence": float, "reason": str}
        """
        pass
