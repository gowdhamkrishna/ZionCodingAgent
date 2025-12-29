from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseTool(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        pass

    def to_schema(self) -> Dict[str, Any]:
        """
        Returns JSON schema for the tool (simplified for Ollama/Local LLM).
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.get_parameters_schema()
        }

    @abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        pass
