"""
File Approval Manager - Handles interactive file write approvals
"""
from typing import Optional, Literal
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt
from rich import box
import difflib

console = Console()

ApprovalMode = Literal['once', 'session', 'editor', 'no']


class FileApprovalManager:
    """Manages file write approvals with interactive prompts."""
    
    def __init__(self):
        self.session_approvals = set()  # Files approved for entire session
        self.auto_approve = False  # Auto-approve all for session
        
    def should_approve(
        self, 
        file_path: str, 
        new_content: str, 
        old_content: Optional[str] = None
    ) -> ApprovalMode:
        """
        Check if file write should be approved.
        Shows diff and prompts user for approval.
        
        Returns:
            'once': Approve this one time
            'session': Approve for this session (all future writes to this file)
            'editor': Open in external editor
            'no': Reject the write
        """
        # If auto-approve is enabled, allow all
        if self.auto_approve:
            return 'session'
        
        # If this file was approved for session, allow
        if file_path in self.session_approvals:
            return 'session'
        
        # Show the diff and prompt
        return self._prompt_for_approval(file_path, new_content, old_content)
    
    def _prompt_for_approval(
        self, 
        file_path: str, 
        new_content: str, 
        old_content: Optional[str] = None
    ) -> ApprovalMode:
        """Show diff and prompt for approval."""
        
        console.print()
        
        # Show file diff
        if old_content:
            self._show_diff(file_path, old_content, new_content)
        else:
            self._show_new_file(file_path, new_content)
        
        console.print()
        
        # Create prompt panel
        prompt_text = "[bold]Apply this change?[/bold]\n\n"
        prompt_text += "  [bold cyan]1.[/bold cyan] Allow once\n"
        prompt_text += "  [bold cyan]2.[/bold cyan] Allow for this session\n"
        prompt_text += "  [bold cyan]3.[/bold cyan] Modify with external editor\n"
        prompt_text += "  [bold cyan]4.[/bold cyan] No, suggest changes (esc)\n"
        
        console.print(Panel(
            prompt_text,
            border_style="bright_cyan",
            box=box.ROUNDED,
            padding=(1, 2)
        ))
        
        # Get user choice
        while True:
            choice = Prompt.ask(
                "Choice",
                choices=["1", "2", "3", "4"],
                default="1"
            )
            
            if choice == "1":
                return 'once'
            elif choice == "2":
                self.session_approvals.add(file_path)
                return 'session'
            elif choice == "3":
                return 'editor'
            elif choice == "4":
                return 'no'
    
    def _show_diff(self, file_path: str, old_content: str, new_content: str):
        """Show a unified diff of the file changes."""
        
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=""
        )
        
        diff_text = ""
        line_num = 1
        for line in diff:
            if line.startswith('---') or line.startswith('+++'):
                continue
            if line.startswith('@@'):
                diff_text += line + "\n"
            else:
                diff_text += f"{line_num:3} {line}\n"
                line_num += 1
        
        # Detect language from file extension
        ext = file_path.split('.')[-1] if '.' in file_path else 'txt'
        lang_map = {
            'js': 'javascript', 'jsx': 'javascript', 'ts': 'typescript',
            'tsx': 'typescript', 'py': 'python', 'css': 'css',
            'html': 'html', 'json': 'json', 'md': 'markdown'
        }
        lang = lang_map.get(ext, 'diff')
        
        syntax = Syntax(
            diff_text if diff_text else new_content,
            lang,
            theme="monokai",
            line_numbers=True,
            background_color="default"
        )
        
        console.print(Panel(
            syntax,
            title=f"[bold bright_cyan]?  WriteFile[/bold bright_cyan] Writing to [cyan]{file_path}[/cyan]",
            border_style="bright_cyan",
            box=box.ROUNDED,
            padding=(0, 1),
            subtitle="[dim]Changes to be applied[/dim]"
        ))
    
    def _show_new_file(self, file_path: str, content: str):
        """Show content of a new file."""
        
        # Detect language
        ext = file_path.split('.')[-1] if '.' in file_path else 'txt'
        lang_map = {
            'js': 'javascript', 'jsx': 'javascript', 'ts': 'typescript',
            'tsx': 'typescript', 'py': 'python', 'css': 'css',
            'html': 'html', 'json': 'json', 'md': 'markdown'
        }
        lang = lang_map.get(ext, 'text')
        
        # Limit to first 30 lines
        lines = content.split('\n')
        truncated = len(lines) > 30
        display_content = '\n'.join(lines[:30])
        if truncated:
            display_content += f"\n... ({len(lines) - 30} more lines)"
        
        syntax = Syntax(
            display_content,
            lang,
            theme="monokai",
            line_numbers=True,
            background_color="default"
        )
        
        console.print(Panel(
            syntax,
            title=f"[bold bright_cyan]?  WriteFile[/bold bright_cyan] Creating [cyan]{file_path}[/cyan]",
            border_style="bright_cyan",
            box=box.ROUNDED,
            padding=(0, 1),
            subtitle=f"[dim]{lang} • New file[/dim]"
        ))
    
    def enable_auto_approve(self):
        """Enable auto-approve for all files in this session."""
        self.auto_approve = True
    
    def disable_auto_approve(self):
        """Disable auto-approve."""
        self.auto_approve = False
