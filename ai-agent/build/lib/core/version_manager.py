"""
Version Manager for Zion Agent.
Keeps backups of files with commit messages for undo/restore.
"""
import os
import json
import shutil
from datetime import datetime
from typing import Optional, List, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markup import escape

console = Console()


class VersionManager:
    """Manages file versions with commit messages."""
    
    def __init__(self, workspace: str):
        self.workspace = workspace
        self.backup_dir = os.path.join(workspace, ".zion_backups")
        self.history_file = os.path.join(self.backup_dir, "history.json")
        self.history: List[Dict] = []
        self.current_message: str = ""
        self.current_task_id: str = ""  # Groups files changed in same task
        self._ensure_backup_dir()
        self._load_history()
    
    def set_commit_message(self, message: str):
        """Set the commit message for upcoming changes."""
        self.current_message = message[:100] if len(message) > 100 else message
        # Generate unique task ID for grouping
        self.current_task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _ensure_backup_dir(self):
        """Create backup directory if it doesn't exist."""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            gitignore = os.path.join(self.workspace, ".gitignore")
            try:
                with open(gitignore, "a") as f:
                    f.write("\n# Zion Agent backups\n.zion_backups/\n")
            except:
                pass
    
    def _load_history(self):
        """Load history from file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    self.history = json.load(f)
            except:
                self.history = []
    
    def _save_history(self):
        """Save history to file."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.history[-100:], f, indent=2)
        except:
            pass
    
    def backup_file(self, file_path: str, action: str = "modify") -> Optional[str]:
        """Create a backup of a file before modification."""
        if not os.path.exists(file_path):
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        rel_path = os.path.relpath(file_path, self.workspace)
        safe_name = rel_path.replace("/", "_").replace("\\", "_")
        backup_name = f"{timestamp}_{safe_name}"
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        try:
            shutil.copy2(file_path, backup_path)
            
            entry = {
                "id": len(self.history),
                "task_id": self.current_task_id,
                "timestamp": timestamp,
                "time_display": datetime.now().strftime("%H:%M:%S"),
                "action": action,
                "file_path": file_path,
                "backup_path": backup_path,
                "rel_path": rel_path,
                "message": self.current_message or "No message"
            }
            self.history.append(entry)
            self._save_history()
            
            return backup_path
        except Exception as e:
            return None
    
    def restore_file(self, index: int = -1) -> bool:
        """Restore a single file from backup."""
        if not self.history:
            console.print("[yellow]No backups available[/yellow]")
            return False
        
        try:
            entry = self.history[index]
            backup_path = entry["backup_path"]
            file_path = entry["file_path"]
            
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, file_path)
                console.print(f"[green]✓ Restored[/green] {entry['rel_path']}")
                return True
            else:
                console.print(f"[red]Backup not found[/red]")
                return False
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return False
    
    def undo_last(self) -> bool:
        """Undo the last file modification."""
        return self.restore_file(-1)
    
    def undo_task(self, task_id: str = None) -> int:
        """
        Undo all files changed in a task (same commit message/task_id).
        Returns number of files restored.
        """
        if not self.history:
            console.print("[yellow]No backups available[/yellow]")
            return 0
        
        # If no task_id provided, find the most recent task
        if task_id is None:
            last_entry = self.history[-1]
            task_id = last_entry.get("task_id", "")
            if not task_id:
                # Fallback: just undo the last file
                self.restore_file(-1)
                return 1
        
        # Find all entries with this task_id
        task_entries = [e for e in self.history if e.get("task_id") == task_id]
        
        if not task_entries:
            console.print(f"[yellow]No entries found for task[/yellow]")
            return 0
        
        # Restore all files (in reverse order to handle dependencies)
        restored = 0
        console.print(f"[bold cyan]Undoing task: {task_entries[0].get('message', 'Unknown')}[/bold cyan]")
        
        for entry in reversed(task_entries):
            backup_path = entry["backup_path"]
            file_path = entry["file_path"]
            
            if os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, file_path)
                    console.print(f"  [green]✓[/green] {entry['rel_path']}")
                    restored += 1
                except:
                    console.print(f"  [red]✗[/red] {entry['rel_path']}")
        
        console.print(f"[green]Restored {restored} file(s)[/green]")
        return restored
    
    def show_history(self, count: int = 15):
        """Display recent backup history grouped by task."""
        if not self.history:
            console.print("[dim]No history available[/dim]")
            return
        
        table = Table(title="📋 Version History", show_lines=True)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Time", style="dim", width=8)
        table.add_column("Files", style="bright_blue", width=8)
        table.add_column("Task", style="yellow")
        
        # Group by task_id
        tasks = {}
        for entry in self.history:
            task_id = entry.get("task_id", entry["timestamp"])
            if task_id not in tasks:
                tasks[task_id] = {
                    "files": [],
                    "message": entry.get("message", ""),
                    "time": entry.get("time_display", ""),
                    "first_id": entry.get("id", 0)
                }
            tasks[task_id]["files"].append(entry["rel_path"])
        
        # Show recent tasks
        recent_tasks = list(tasks.items())[-count:]
        for task_id, info in reversed(recent_tasks):
            table.add_row(
                str(info["first_id"]),
                info["time"],
                str(len(info["files"])),
                info["message"][:45]
            )
        
        console.print(table)
        console.print()
        console.print("[dim]Commands:[/dim]")
        console.print("[dim]  undo         - Undo last task (all files)[/dim]")
        console.print("[dim]  undo N       - Undo specific entry[/dim]")
        console.print("[dim]  undo --file  - Undo only last file[/dim]")
        console.print("[dim]  show N       - View backup content[/dim]")
    
    def show_backup(self, index: int):
        """Show the content of a backup file."""
        if not self.history or index >= len(self.history):
            console.print("[yellow]Invalid backup index[/yellow]")
            return
        
        entry = self.history[index]
        backup_path = entry["backup_path"]
        
        if not os.path.exists(backup_path):
            console.print("[red]Backup file not found[/red]")
            return
        
        try:
            with open(backup_path, 'r') as f:
                content = f.read()
            
            ext = entry["rel_path"].split(".")[-1] if "." in entry["rel_path"] else "text"
            lang_map = {"js": "javascript", "jsx": "javascript", "ts": "typescript", 
                       "tsx": "typescript", "py": "python", "json": "json", "css": "css",
                       "html": "html", "md": "markdown"}
            lang = lang_map.get(ext, "text")
            
            syntax = Syntax(content[:2000], lang, line_numbers=True, theme="monokai")
            
            console.print(Panel(
                syntax,
                title=f"[bold cyan]#{index} - {entry['rel_path']}[/bold cyan]",
                subtitle=f"[dim]{escape(entry.get('message', ''))}[/dim]",
                border_style="blue"
            ))
            
            if len(content) > 2000:
                console.print(f"[dim]... ({len(content) - 2000} more characters)[/dim]")
                
        except Exception as e:
            console.print(f"[red]Error reading backup: {e}[/red]")
    
    def show_diff(self, index: int):
        """Show diff between backup and current file."""
        import difflib
        
        if not self.history or index >= len(self.history):
            console.print("[yellow]Invalid backup index[/yellow]")
            return
        
        entry = self.history[index]
        backup_path = entry["backup_path"]
        current_path = entry["file_path"]
        
        try:
            with open(backup_path, 'r') as f:
                backup_content = f.readlines()
            
            if os.path.exists(current_path):
                with open(current_path, 'r') as f:
                    current_content = f.readlines()
            else:
                current_content = ["(file deleted)"]
            
            diff = difflib.unified_diff(
                backup_content, current_content,
                fromfile=f"backup #{index}",
                tofile="current",
                lineterm=""
            )
            
            diff_text = "\n".join(diff)
            if not diff_text:
                console.print("[green]No differences - files are identical[/green]")
                return
            
            from rich.text import Text
            output = Text()
            for line in diff_text.split("\n"):
                if line.startswith("+") and not line.startswith("+++"):
                    output.append(line + "\n", style="green")
                elif line.startswith("-") and not line.startswith("---"):
                    output.append(line + "\n", style="red")
                elif line.startswith("@@"):
                    output.append(line + "\n", style="cyan")
                else:
                    output.append(line + "\n", style="dim")
            
            console.print(Panel(
                output,
                title=f"[bold yellow]Diff: #{index} vs Current[/bold yellow]",
                border_style="yellow"
            ))
            
        except Exception as e:
            console.print(f"[red]Error showing diff: {e}[/red]")
