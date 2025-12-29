import os
from .base import BaseTool
from typing import Dict, Any, Optional

# Global version manager instance (set by orchestrator)
_version_manager = None

def set_version_manager(vm):
    global _version_manager
    _version_manager = vm

def get_version_manager():
    return _version_manager


class ReadFileTool(BaseTool):
    def __init__(self):
        super().__init__("read_file", "Read content of a file")

    def execute(self, file_path: str, start_line: int = 1, end_line: int = -1) -> str:
        try:
            if not os.path.exists(file_path):
                return f"Error: File {file_path} not found."

            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if start_line < 1:
                start_line = 1
            
            if end_line == -1 or end_line > len(lines):
                end_line = len(lines)

            selected_lines = lines[start_line-1:end_line]
            content = "".join(selected_lines)
            return content
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute path to the file"},
                "start_line": {"type": "integer", "description": "Start line number"},
                "end_line": {"type": "integer", "description": "End line number"}
            },
            "required": ["file_path"]
        }


class WriteFileTool(BaseTool):
    def __init__(self):
        super().__init__("write_file", "Write content to a file (with automatic backup)")
        self.approval_manager = None  # Set by orchestrator

    def execute(self, file_path: str, content: str) -> str:
        try:
            if not content:
                return "Error: Content cannot be empty."
            
            # Get old content if file exists
            old_content = None
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        old_content = f.read()
                except:
                    pass
            
            # Check for approval if manager is set
            if self.approval_manager:
                approval = self.approval_manager.should_approve(file_path, content, old_content)
                
                if approval == 'no':
                    return "File write cancelled by user."
                elif approval == 'editor':
                    return "External editor not implemented yet. File write cancelled."
                # 'once' and 'session' both proceed with write
            
            # CONTENT QUALITY VALIDATION: Reject placeholder/comment-only writes
            content_stripped = content.strip()
            lines = content_stripped.split('\n')
            non_empty_lines = [l.strip() for l in lines if l.strip()]
            
            # Check if content is suspiciously short (less than 3 lines)
            if len(non_empty_lines) < 3:
                # Check if it's just comments or placeholders
                is_placeholder = all(
                    line.startswith('<!--') or  # HTML comment
                    line.startswith('//') or    # JS comment
                    line.startswith('#') or     # Python comment
                    'placeholder' in line.lower() or
                    'updated' in line.lower() or
                    'modified' in line.lower()
                    for line in non_empty_lines
                )
                
                if is_placeholder:
                    return (f"VIOLATION: Content appears to be a placeholder comment, not real code. "
                           f"You must write the ACTUAL implementation, not a comment about it. "
                           f"Rejected content: {content_stripped[:100]}")
            
            # Backup existing file before overwriting
            vm = get_version_manager()
            if vm and os.path.exists(file_path):
                vm.backup_file(file_path, "modify")
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            action = "created" if not old_content else "updated"
            return f"Successfully {action} {file_path}"
        except Exception as e:
            return f"Error writing to file {file_path}: {str(e)}"


    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file"},
                "content": {"type": "string", "description": "Content to write"}
            },
            "required": ["file_path", "content"]
        }


class EditFileTool(BaseTool):
    def __init__(self):
        super().__init__("edit_file", "Edit a file by replacing text (with automatic backup)")

    def execute(self, file_path: str, target: str, replacement: str) -> str:
        try:
            if not target or not target.strip():
                return "Error: `target` cannot be empty."
            
            if not os.path.exists(file_path):
                return f"Error: File {file_path} does not exist. Use `write_file` for new files."

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if target not in content:
                return f"Error: Target text not found in {file_path}"
            
            if content.count(target) > 1:
                return f"Error: Target found {content.count(target)} times. Must be unique."
            
            # Backup before editing
            vm = get_version_manager()
            if vm:
                vm.backup_file(file_path, "edit")
            
            new_content = content.replace(target, replacement)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            return f"Successfully edited {file_path}"
        except Exception as e:
            return f"Error editing file {file_path}: {str(e)}"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file"},
                "target": {"type": "string", "description": "Text to replace"},
                "replacement": {"type": "string", "description": "Replacement text"}
            },
            "required": ["file_path", "target", "replacement"]
        }


class ListDirTool(BaseTool):
    def __init__(self):
        super().__init__("list_dir", "List files in a directory")

    def execute(self, dir_path: str) -> str:
        try:
            if not os.path.isdir(dir_path):
                return f"Error: Directory {dir_path} not found."
            
            output = []
            items = sorted(os.listdir(dir_path))
            for item in items:
                if item.startswith('.'):  # Skip hidden files
                    continue
                path = os.path.join(dir_path, item)
                type_str = "[DIR]" if os.path.isdir(path) else "[FILE]"
                output.append(f"{type_str} {item}")
            
            return "\n".join(output) if output else "(empty directory)"
        except Exception as e:
            return f"Error listing directory {dir_path}: {str(e)}"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "dir_path": {"type": "string", "description": "Path to the directory"}
            },
            "required": ["dir_path"]
        }


class SearchFileTool(BaseTool):
    def __init__(self):
        super().__init__("search_files", "Search for text in files")

    def execute(self, dir_path: str, search_term: str) -> str:
        try:
            if not os.path.isdir(dir_path):
                return f"Error: Directory {dir_path} not found."
            
            results = []
            for root, _, files in os.walk(dir_path):
                # Skip hidden and backup directories
                if '/.git' in root or '/.zion_backups' in root or '/node_modules' in root:
                    continue
                    
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for i, line in enumerate(f, 1):
                                if search_term in line:
                                    results.append(f"{file_path}:{i}: {line.strip()[:80]}")
                                    if len(results) >= 30:
                                        return "\n".join(results) + "\n... (limit reached)"
                    except:
                        continue
            
            return "\n".join(results) if results else "No matches found."
        except Exception as e:
            return f"Error searching: {str(e)}"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "dir_path": {"type": "string", "description": "Directory to search"},
                "search_term": {"type": "string", "description": "Text to find"}
            },
            "required": ["dir_path", "search_term"]
        }


class PatchFileTool(BaseTool):
    """Advanced targeted editing tool for surgical file modifications."""
    
    def __init__(self):
        super().__init__("patch_file", "Make targeted edits to a file without rewriting everything")

    def execute(self, file_path: str, operation: str = None, **kwargs) -> str:
        """
        Perform targeted file edits.
        
        Operations:
        - insert_at_line: Insert content at a specific line number
        - replace_lines: Replace a range of lines
        - append: Add content at end of file
        - prepend: Add content at start of file
        - add_after: Add content after a marker line
        - add_before: Add content before a marker line
        """
        try:
            if not operation:
                return "Error: 'operation' argument is required. Valid operations: insert_at_line, replace_lines, append, prepend, add_after, add_before, delete_lines."

            if not os.path.exists(file_path):
                return f"Error: File {file_path} not found."
            
            # Backup before patching
            vm = get_version_manager()
            if vm:
                vm.backup_file(file_path, "patch")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            original_len = len(lines)
            
            if operation == "insert_at_line":
                line_num = kwargs.get("line", 1)
                content = kwargs.get("content", "")
                if line_num < 1:
                    line_num = 1
                if line_num > len(lines) + 1:
                    line_num = len(lines) + 1
                # Insert at position (0-indexed)
                if not content.endswith("\n"):
                    content += "\n"
                lines.insert(line_num - 1, content)
                result = f"Inserted at line {line_num}"
                
            elif operation == "replace_lines":
                start = kwargs.get("start_line", 1)
                end = kwargs.get("end_line", start)
                content = kwargs.get("content", "")
                if start < 1:
                    start = 1
                if end > len(lines):
                    end = len(lines)
                if not content.endswith("\n"):
                    content += "\n"
                lines[start-1:end] = [content]
                result = f"Replaced lines {start}-{end}"
                
            elif operation == "append":
                content = kwargs.get("content", "")
                if not content.startswith("\n") and lines and not lines[-1].endswith("\n"):
                    content = "\n" + content
                if not content.endswith("\n"):
                    content += "\n"
                lines.append(content)
                result = "Appended to file"
                
            elif operation == "prepend":
                content = kwargs.get("content", "")
                if not content.endswith("\n"):
                    content += "\n"
                lines.insert(0, content)
                result = "Prepended to file"
                
            elif operation == "add_after":
                marker = kwargs.get("marker", "")
                content = kwargs.get("content", "")
                if not marker:
                    return "Error: 'marker' is required for add_after"
                
                found = False
                for i, line in enumerate(lines):
                    if marker in line:
                        if not content.endswith("\n"):
                            content += "\n"
                        lines.insert(i + 1, content)
                        found = True
                        result = f"Added after line {i + 1}"
                        break
                
                if not found:
                    return f"Error: Marker '{marker[:30]}...' not found in file"
                    
            elif operation == "add_before":
                marker = kwargs.get("marker", "")
                content = kwargs.get("content", "")
                if not marker:
                    return "Error: 'marker' is required for add_before"
                
                found = False
                for i, line in enumerate(lines):
                    if marker in line:
                        if not content.endswith("\n"):
                            content += "\n"
                        lines.insert(i, content)
                        found = True
                        result = f"Added before line {i + 1}"
                        break
                
                if not found:
                    return f"Error: Marker '{marker[:30]}...' not found in file"
                    
            elif operation == "delete_lines":
                start = kwargs.get("start_line", 1)
                end = kwargs.get("end_line", start)
                if start < 1:
                    start = 1
                if end > len(lines):
                    end = len(lines)
                del lines[start-1:end]
                result = f"Deleted lines {start}-{end}"
                
            else:
                return f"Error: Unknown operation '{operation}'. Use: insert_at_line, replace_lines, append, prepend, add_after, add_before, delete_lines"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return f"Success: {result} (was {original_len} lines, now {len(lines)} lines)"
            
        except Exception as e:
            return f"Error patching file: {str(e)}"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file"},
                "operation": {
                    "type": "string",
                    "description": "Operation: insert_at_line, replace_lines, append, prepend, add_after, add_before, delete_lines"
                },
                "line": {"type": "integer", "description": "Line number for insert_at_line"},
                "start_line": {"type": "integer", "description": "Start line for replace_lines/delete_lines"},
                "end_line": {"type": "integer", "description": "End line for replace_lines/delete_lines"},
                "marker": {"type": "string", "description": "Text to find for add_after/add_before"},
                "content": {"type": "string", "description": "Content to insert/add"}
            },
            "required": ["file_path", "operation"]
        }
