"""
Git-based Version Manager for Zion Agent.
Replaces file-copy storage with Git commits.
"""
import os
import subprocess
import shutil
from datetime import datetime
from typing import Optional, List, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markup import escape

console = Console()


class GitVersionManager:
    """Manages file versions using Git."""
    
    def __init__(self, workspace: str):
        self.workspace = os.path.abspath(workspace)
        self.current_message: str = ""
        self.current_task_id: str = ""
        self.task_files: List[str] = [] # Files touched in current task
        self._init_git()
        
    def _run_git(self, args: List[str], check: bool = False) -> subprocess.CompletedProcess:
        """Run a git command in the workspace."""
        cmd = ["git"] + args
        return subprocess.run(
            cmd, 
            cwd=self.workspace, 
            capture_output=True, 
            text=True, 
            check=check,
            encoding='utf-8',
            errors='replace'
        )
    
    def _init_git(self):
        """Initialize git repo if needed."""
        if not os.path.exists(os.path.join(self.workspace, ".git")):
            self._run_git(["init"])
            # Configure user if not set (local to this repo)
            self._run_git(["config", "user.name", "Zion Agent"])
            self._run_git(["config", "user.email", "agent@zion"])
            
            # Create .gitignore for agent internals
            gitignore = os.path.join(self.workspace, ".gitignore")
            if not os.path.exists(gitignore):
                with open(gitignore, "w") as f:
                    f.write(".env\n__pycache__/\n*.pyc\n.zion_backups/\n.gemini/\n")
            else:
                # Append if not present
                with open(gitignore, "r") as f:
                    content = f.read()
                updates = []
                for item in [".env", "__pycache__/", ".zion_backups/", ".gemini/"]:
                    if item not in content:
                        updates.append(item)
                if updates:
                    with open(gitignore, "a") as f:
                        f.write("\n" + "\n".join(updates) + "\n")
                        
            # Initial commit if empty
            self._run_git(["add", ".gitignore"])
            self._run_git(["commit", "-m", "Initial commit by Zion Agent"])

    def set_commit_message(self, message: str):
        """Set the commit message for upcoming changes."""
        self.current_message = message[:100] if len(message) > 100 else message
        self.current_task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.task_files = [] # Reset for new task
    
    def backup_file(self, file_path: str, action: str = "modify") -> Optional[str]:
        """
        Record the current state of the file into Git before modification.
        This effectively commits the 'before' state.
        Returns the commit hash as the 'backup path' identifier.
        """
        if not os.path.exists(file_path):
            return None
        
        rel_path = os.path.relpath(file_path, self.workspace)
        
        # Track file for current task undo
        if rel_path not in self.task_files:
            self.task_files.append(rel_path)
        
        # Add file
        self._run_git(["add", rel_path])
        
        # Check if there are changes to commit
        status = self._run_git(["status", "--porcelain", rel_path])
        if not status.stdout.strip():
            # Nothing to commit (file untouched since last commit)
            # We still return current HEAD as 'backup'
            res = self._run_git(["rev-parse", "HEAD"])
            return res.stdout.strip() if res.returncode == 0 else None
            
        # Commit
        msg = f"Backup: {action} {rel_path}"
        if self.current_message:
            msg += f" - {self.current_message}"
        
        res = self._run_git(["commit", "-m", msg])
        
        if res.returncode == 0:
            # Return new HEAD hash
            res = self._run_git(["rev-parse", "HEAD"])
            return res.stdout.strip()
        return None

    def restore_file(self, index: int = -1) -> bool:
        """
        Restore file to a previous version.
        Index logic: 
         -1: Undo last change (checkout HEAD -- file)
         Other indices (0..N): Restore from specific history entry index.
         
         Note: The original VersionManager used a list index 0..N.
         To map this to Git, we need to adhere to the view provided by existing show_history.
        """
        # If index is -1, we assume we want to discard current changes in working directory
        # effectively restoring to HEAD.
        # BUT, wait. VersionManager.restore_file(-1) restores the LAST BACKUP.
        # Since we commit on 'backup_file', HEAD *is* the last backup.
        # So 'git checkout HEAD -- file' restores the file to the state BEFORE the last write.
        # This is exactly what we want for Undo.
        
        # However, if 'index' is provided (from show_history), it refers to a specific commit.
        # implementation details below.
        
        target_commit = None
        target_file = None
        
        if index == -1:
             # Logic for "Undo Last" - Find the most recent modified file in git log?
             # Or just assume we want to revert the last action on the file currently being edited?
             # VersionManager.undo_last calls restore_file(-1).
             # We need to know WHICH file. VersionManager stores history list.
             # We should fetch the last commit.
             
             log = self._get_history_entries(limit=1)
             if not log:
                 console.print("[yellow]No history available[/yellow]")
                 return False
             
             entry = log[0]
             target_commit = entry["commit_hash"]
             target_file = entry["file_path"]
             
        else:
            # Restore from specific history index (0 is oldest? Or 0 is newest? VM uses append, so 0 is oldest)
            # Git log usually gives newest first.
            # We need to reconstruct the list to match indices.
            history = self._get_history_entries(limit=100)
            # VM history: 0=oldest, -1=newest.
            # Our _get_history_entries returns newest first (git log default).
            # So index i in VM (0..N) corresponds to history[N-1-i] ?
            # Let's align with what show_history displays.
            
            if index < 0 or index >= len(history):
                 console.print("[yellow]Invalid index[/yellow]")
                 return False
            
            # Map VM index (oldest=0) to our list (newest=0)
            # Actually, let's just use the ID we display in show_history.
            # In show_history (below), we will display explicit IDs.
            # But the CLI passes an int index based on user input.
            # Let's assume the user uses the ID shown in the table.
            
            # Let's look up by 'id' field
            target_entry = next((e for e in history if e["id"] == index), None)
            if not target_entry:
                 console.print("[yellow]Entry not found[/yellow]")
                 return False
            
            target_commit = target_entry["commit_hash"]
            target_file = target_entry["file_path"]

        if target_commit and target_file:
            try:
                # git checkout <commit> -- <file>
                self._run_git(["checkout", target_commit, "--", target_file])
                console.print(f"[green]✓ Restored[/green] {target_file}")
                return True
            except Exception as e:
                console.print(f"[red]Error restoring: {e}[/red]")
                return False
                
        return False
        
    def undo_last(self) -> bool:
        """Undo the last file modification."""
        return self.restore_file(-1)

    def undo_task(self, task_id: str = None) -> int:
        """Undo all files changed in a task."""
        
        # Priority: If undoing current task (no ID), use in-memory list
        if task_id is None and self.task_files:
             console.print(f"[bold cyan]Backtracking current task ({len(self.task_files)} files)...[/bold cyan]")
             restored = 0
             for rel_path in reversed(self.task_files):
                 try:
                     # Revert to HEAD (pre-modification state if backup_file was called)
                     self._run_git(["checkout", "HEAD", "--", rel_path])
                     console.print(f"  [green]✓[/green] {rel_path}")
                     restored += 1
                 except Exception as e:
                     console.print(f"  [red]✗[/red] {rel_path} ({e})")
             
             self.task_files = [] # Clear after undo
             return restored

        # Fallback to history-based undo (for previous tasks)
        history = self._get_history_entries(limit=50)
        if not history:
             return 0
             
        if task_id is None:
            # undo last task = undo all commits with same message/timestamp as the last one
            last_entry = history[-1] # Newest
            target_group_id = last_entry.get("task_group_id") # derived from message+time
        else:
            target_group_id = task_id
            
        # Find all files involved in this task
        entries_to_undo = [e for e in history if e.get("task_group_id") == target_group_id]
        
        restored = 0
        console.print(f"[bold cyan]Undoing task: {last_entry.get('message', 'Unknown')}[/bold cyan]")
        
        # Restore in reverse order (Newest -> Oldest) to ensure we end up 
        # at the earliest state if a file was modified multiple times.
        for entry in reversed(entries_to_undo):
            commit = entry["commit_hash"]
            file_path = entry["file_path"]
            
            try:
                self._run_git(["checkout", commit, "--", file_path])
                console.print(f"  [green]✓[/green] {entry['rel_path']}")
                restored += 1
            except Exception as e:
                console.print(f"  [red]✗[/red] {entry['rel_path']} ({e})")
                
        return restored

    def _get_history_entries(self, limit: int = 100) -> List[Dict]:
        """
        Parse git log into structured history.
        Returns list ordered Newest -> Oldest.
        """
        # Format: hash|timestamp|subject
        res = self._run_git([
            "log", 
            f"-n{limit}", 
            "--pretty=format:%H|%ai|%s", 
            "--name-only"
        ])
        
        if res.returncode != 0:
            return []
            
        entries = []
        # Git log with name-only output format:
        # HASH|TIME|MSG
        # file1
        # file2
        # <empty>
        
        lines = res.stdout.split('\n')
        current_header = None
        
        # We need to mimic the sequential ID of the old VM (0..N).
        # We don't have a stable ID unless we count total commits.
        # Let's count them temporarily or use hash.
        # BUT show_history uses integer ID.
        # Let's generate ephemeral IDs 0..N based on valid backup commits.
        
        raw_entries = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if '|' in line and len(line.split('|')) >= 3:
                # Header
                parts = line.split('|')
                current_header = {
                    "hash": parts[0],
                    "time": parts[1],
                    "msg": parts[2]
                }
            elif current_header:
                # File line (git log --name-only lists files after header)
                # Only include if it looks like a backup commit? 
                # Or all commits? All commits are versions.
                
                # Timestamp parsing
                try:
                    dt = datetime.strptime(current_header["time"].split()[0], "%Y-%m-%d")
                    time_display = dt.strftime("%H:%M:%S")
                    time_str = current_header["time"][11:19]
                except:
                    time_str = ""

                # Derive task ID from message (suffix after ' - ')
                task_suffix = current_header["msg"]
                if " - " in task_suffix:
                    task_suffix = task_suffix.split(" - ", 1)[1]
                
                # Use suffix as group ID
                
                entry = {
                    "commit_hash": current_header["hash"],
                    "timestamp": current_header["time"],
                    "time_display": time_str,
                    "message": current_header["msg"],
                    "file_path": line,
                    "rel_path": line,
                    "task_group_id": task_suffix
                }
                raw_entries.append(entry)
        
        # In VM, index 0 satisfies history[0].
        # The list returned here is Newest First.
        # VM history is Oldest First (append).
        # So we should reverse to match VM behavior if we want index 0 to be oldest.
        
        raw_entries.reverse() 
        
        # Assign stable IDs (0 to N)
        for i, e in enumerate(raw_entries):
            e["id"] = i
            
        return raw_entries

    def show_history(self, count: int = 15):
        """Display history."""
        history = self._get_history_entries(limit=count*2) # Get more to filter/group
        if not history:
            console.print("[dim]No history available[/dim]")
            return

        table = Table(title="📋 Version History (Git)", show_lines=True)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Time", style="dim", width=8)
        table.add_column("File", style="bright_blue")
        table.add_column("Message", style="yellow")
        
        # Show recent N entries (Newest first for display usually, but VM used oldest first?)
        # VM show_history reversed the list before printing: `for task_id, info in reversed(recent_tasks):`
        # So VM showed Newest at bottom? Or Top?
        # `reversed(recent_tasks)` means Newest (end of list) comes first? No, reversed([1, 2]) -> 2, 1.
        # So VM showed Newest first.
        
        # Our `history` is Oldest First (0..N).
        # We want to show Newest First.
        
        display_entries = history[-count:] if len(history) > count else history
        
        for entry in reversed(display_entries):
            table.add_row(
                str(entry["id"]),
                entry["time_display"],
                entry["rel_path"],
                entry["message"][:45]
            )
            
        console.print(table)
        console.print()
        console.print("[dim]Commands:[/dim]")
        console.print("[dim]  undo         - Undo last change[/dim]")
        console.print("[dim]  undo N       - Undo specific version[/dim]")
        
    def show_backup(self, index: int):
        """Show content of a specific version."""
        history = self._get_history_entries()
        entry = next((e for e in history if e["id"] == index), None)
        
        if not entry:
            console.print("[yellow]Invalid index[/yellow]")
            return
            
        commit = entry["commit_hash"]
        path = entry["rel_path"]
        
        # git show commit:path
        res = self._run_git(["show", f"{commit}:{path}"])
        if res.returncode != 0:
            console.print(f"[red]Error reading version: {res.stderr}[/red]")
            return
            
        content = res.stdout
        
        ext = path.split(".")[-1] if "." in path else "text"
        lang_map = {"js": "javascript", "jsx": "javascript", "ts": "typescript", 
                   "tsx": "typescript", "py": "python", "json": "json", "css": "css",
                   "html": "html", "md": "markdown"}
        lang = lang_map.get(ext, "text")
        
        syntax = Syntax(content[:2000], lang, line_numbers=True, theme="monokai")
        
        console.print(Panel(
            syntax,
            title=f"[bold cyan]#{index} - {path}[/bold cyan]",
            subtitle=f"[dim]{escape(entry['message'])}[/dim]",
            border_style="blue"
        ))
        
    def show_diff(self, index: int):
        """Show diff between version and current."""
        import difflib # Use rich coloring logic from before
        
        history = self._get_history_entries()
        entry = next((e for e in history if e["id"] == index), None)
        
        if not entry:
            console.print("[yellow]Invalid index[/yellow]")
            return
            
        commit = entry["commit_hash"]
        path = entry["rel_path"]
        
        # git diff commit -- path
        res = self._run_git(["diff", commit, "--", path])
        diff_text = res.stdout
        
        if not diff_text:
             console.print("[green]No differences[/green]")
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
