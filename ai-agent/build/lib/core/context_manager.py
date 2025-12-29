import os
from typing import Set

class ContextManager:
    def __init__(self):
        self.focused_files: Set[str] = set()

    def add_focus(self, file_path: str) -> str:
        """Adds a file to the focused context."""
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return f"Error: File {abs_path} does not exist."
        
        self.focused_files.add(abs_path)
        return f"Added {abs_path} to focus."

    def remove_focus(self, file_path: str) -> str:
        """Removes a file from the focused context."""
        abs_path = os.path.abspath(file_path)
        if abs_path in self.focused_files:
            self.focused_files.remove(abs_path)
            return f"Removed {abs_path} from focus."
        return f"File {abs_path} was not in focus."

    def get_context_formatted(self) -> str:
        """Returns the content of all focused files formatted for the LLM."""
        if not self.focused_files:
            return ""

        context_str = "\n=== ACTIVE CONTEXT (FOCUSED FILES) ===\n"
        
        for file_path in sorted(list(self.focused_files)):
            context_str += f"\nFile: {file_path}\n"
            context_str += "--------------------------------------\n"
            try:
                # Read file content, limit to first 200 lines to prevent context overflow
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    content = "".join(lines[:200])
                    if len(lines) > 200:
                        content += "\n... (truncated after 200 lines) ...\n"
                    context_str += content
            except Exception as e:
                context_str += f"[Error reading file: {e}]\n"
            context_str += "--------------------------------------\n"
            
        context_str += "======================================\n"
        return context_str
