# providers/base.py

from abc import ABC, abstractmethod
from typing import Dict, Optional

class BaseLLMProvider(ABC):
    @abstractmethod
    def get_decision(self, data: str, context: Optional[Dict]) -> str:
        """Must return a string (preferably JSON-formatted)"""
        pass
