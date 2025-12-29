from .base import BaseTool
from core.context_manager import ContextManager
from typing import Dict, Any

class FocusFileTool(BaseTool):
    def __init__(self, context_manager: ContextManager):
        super().__init__("focus_file", "Add a file to active context (memory)")
        self.context_manager = context_manager

    def execute(self, file_path: str) -> str:
        return self.context_manager.add_focus(file_path)

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute path to the file to focus on"}
            },
            "required": ["file_path"]
        }

class UnfocusFileTool(BaseTool):
    def __init__(self, context_manager: ContextManager):
        super().__init__("unfocus_file", "Remove a file from active context")
        self.context_manager = context_manager

    def execute(self, file_path: str) -> str:
        return self.context_manager.remove_focus(file_path)

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute path to the file to unfocus"}
            },
            "required": ["file_path"]
        }
