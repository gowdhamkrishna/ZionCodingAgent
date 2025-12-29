"""
UI Components for Zion Agent CLI.
Premium Rich-based components for a stunning terminal experience.
"""
import time
import os
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.table import Table
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.columns import Columns
from rich.rule import Rule
from rich import box

console = Console()

# Color scheme
COLORS = {
    "primary": "cyan",
    "secondary": "magenta",
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "muted": "dim white",
    "accent": "bright_blue",
}


def show_welcome_banner() -> None:
    """Display premium animated welcome banner."""
    
    # Gradient-style banner
    banner = """
[bold bright_cyan]╔═══════════════════════════════════════════════════════════════╗[/]
[bold bright_cyan]║[/] [bold bright_magenta]███████╗[/][bold cyan]██╗[/] [bold bright_magenta]██████╗[/] [bold cyan]███╗   ██╗[/]                            [bold bright_cyan]║[/]
[bold bright_cyan]║[/] [bold magenta]╚══███╔╝[/][bold cyan]██║[/][bold magenta]██╔═══██╗[/][bold cyan]████╗  ██║[/]                            [bold bright_cyan]║[/]
[bold bright_cyan]║[/]   [bold bright_magenta]███╔╝[/] [bold cyan]██║[/][bold bright_magenta]██║   ██║[/][bold cyan]██╔██╗ ██║[/]    [bold white]AI Coding Agent[/]          [bold bright_cyan]║[/]
[bold bright_cyan]║[/]  [bold magenta]███╔╝[/]  [bold cyan]██║[/][bold magenta]██║   ██║[/][bold cyan]██║╚██╗██║[/]    [dim]v2.0 • Local • Fast[/]       [bold bright_cyan]║[/]
[bold bright_cyan]║[/] [bold bright_magenta]███████╗[/][bold cyan]██║[/][bold bright_magenta]╚██████╔╝[/][bold cyan]██║ ╚████║[/]                            [bold bright_cyan]║[/]
[bold bright_cyan]║[/] [bold magenta]╚══════╝[/][bold cyan]╚═╝[/] [bold magenta]╚═════╝[/] [bold cyan]╚═╝  ╚═══╝[/]                            [bold bright_cyan]║[/]
[bold bright_cyan]╚═══════════════════════════════════════════════════════════════╝[/]"""
    
    console.print(banner)


def show_agent_header(provider: str = "ollama", model_name: str = "qwen2.5-coder:7b", base_dir: str = None) -> None:
    """Display enhanced system status header."""
    
    # Get system info
    now = datetime.now().strftime("%H:%M")
    dir_name = os.path.basename(base_dir or os.getcwd())
    
    # Create a grid for the header
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(justify="left", ratio=1)
    grid.add_column(justify="right", ratio=1)
    
    # Left side - Model info
    left = Text()
    left.append("⚡ ", style="bright_yellow")
    left.append(f"[{provider.upper()}] ", style="bold magenta")
    left.append("Model: ", style="dim")
    left.append(model_name, style="bold cyan")
    
    # Right side - Workspace
    right = Text()
    right.append("📁 ", style="bright_blue")
    right.append(dir_name, style="bold white")
    right.append(f" • {now}", style="dim")
    
    grid.add_row(left, right)
    
    console.print(Panel(
        grid,
        border_style="bright_blue",
        box=box.DOUBLE_EDGE,
        padding=(0, 1),
    ))


def show_help_bar() -> None:
    """Display compact help commands bar."""
    commands = [
        ("paste", "multi-line"),
        ("undo", "restore"),
        ("history", "versions"),
        ("clear", "screen"),
        ("exit", "quit"),
    ]
    
    help_text = Text()
    help_text.append("  ", style="dim")
    for i, (cmd, desc) in enumerate(commands):
        if i > 0:
            help_text.append(" │ ", style="dim")
        help_text.append(cmd, style="bold cyan")
        help_text.append(f":{desc}", style="dim")
    
    console.print(help_text)
    console.print()


def show_thinking_indicator() -> Text:
    """Create thinking indicator text."""
    text = Text()
    text.append("◐ ", style="bold yellow animate")
    text.append("Thinking", style="dim italic")
    text.append("...", style="dim")
    return text


def show_code_preview(code: str, file_path: str, language: str = None) -> None:
    """Display beautiful syntax-highlighted code preview."""
    if language is None:
        ext_map = {
            ".py": "python", ".js": "javascript", ".jsx": "javascript",
            ".ts": "typescript", ".tsx": "typescript", ".html": "html",
            ".css": "css", ".json": "json", ".md": "markdown",
            ".sh": "bash", ".yaml": "yaml", ".yml": "yaml",
        }
        ext = "." + file_path.split(".")[-1] if "." in file_path else ""
        language = ext_map.get(ext, "text")
    
    # Truncate if too long
    lines = code.split("\n")
    max_lines = 25
    truncated = len(lines) > max_lines
    display_code = "\n".join(lines[:max_lines])
    if truncated:
        display_code += f"\n... ({len(lines) - max_lines} more lines)"
    
    syntax = Syntax(
        display_code,
        language,
        theme="monokai",
        line_numbers=True,
        word_wrap=True,
    )
    
    filename = os.path.basename(file_path)
    
    console.print(Panel(
        syntax,
        title=f"[bold bright_cyan]📄 {filename}[/]",
        subtitle=f"[dim]{language}[/]",
        border_style="bright_blue",
        box=box.ROUNDED,
        padding=(0, 1),
    ))


def show_tool_status(tool_name: str, status: str, details: str = None) -> None:
    """Display tool execution status with styled indicators."""
    icons = {
        "running": ("◐", "bright_yellow"),
        "success": ("✓", "bright_green"),
        "error": ("✗", "bright_red"),
    }
    
    icon, color = icons.get(status, ("•", "white"))
    
    status_text = Text()
    status_text.append(f" {icon} ", style=f"bold {color}")
    status_text.append(tool_name, style="bold white")
    
    if details:
        # Truncate long details
        if len(details) > 50:
            details = details[:47] + "..."
        status_text.append(f" → {details}", style="dim cyan")
    
    console.print(status_text)


def show_file_diff(file_path: str, old_content: str, new_content: str) -> None:
    """Display a beautiful unified diff."""
    import difflib
    
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"before",
        tofile=f"after",
        lineterm=""
    )
    
    diff_text = Text()
    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            diff_text.append(line + "\n", style="bright_green")
        elif line.startswith("-") and not line.startswith("---"):
            diff_text.append(line + "\n", style="bright_red")
        elif line.startswith("@@"):
            diff_text.append(line + "\n", style="bright_cyan")
        else:
            diff_text.append(line + "\n", style="dim")
    
    if diff_text:
        console.print(Panel(
            diff_text,
            title=f"[bold yellow]📝 Changes: {os.path.basename(file_path)}[/]",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(0, 1),
        ))


def show_command_output(command: str, output: str, is_error: bool = False) -> None:
    """Display command output with error detection and styling."""
    import re
    
    # Remove ANSI codes
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\][^\x07]*\x07|\r')
    output = ansi_pattern.sub('', output)
    
    # Detect errors
    error_keywords = ["error", "Error", "ERROR", "failed", "Failed", "FAILED", 
                      "exception", "Exception", "Traceback", "fatal", "Fatal"]
    has_error = is_error or any(kw in output for kw in error_keywords)
    
    # Truncate long output
    lines = output.split("\n")
    max_lines = 20
    if len(lines) > max_lines:
        display = "\n".join(lines[:8] + ["...", f"({len(lines) - 16} lines hidden)", "..."] + lines[-8:])
    else:
        display = output
    
    # Style output
    output_text = Text()
    for line in display.split("\n"):
        if any(kw in line for kw in error_keywords):
            output_text.append(line + "\n", style="bold bright_red")
        elif "warning" in line.lower() or "warn" in line.lower():
            output_text.append(line + "\n", style="bright_yellow")
        elif line.startswith("+"):
            output_text.append(line + "\n", style="bright_green")
        elif line.startswith("-"):
            output_text.append(line + "\n", style="bright_red")
        else:
            output_text.append(line + "\n", style="dim")
    
    border = "bright_red" if has_error else "dim"
    icon = "❌" if has_error else "💻"
    display_cmd = command[:55] + "..." if len(command) > 55 else command
    
    console.print(Panel(
        output_text,
        title=f"[bold]{icon} {display_cmd}[/]",
        border_style=border,
        box=box.ROUNDED,
        padding=(0, 1),
    ))


def show_agent_response(message: str) -> None:
    """Display agent response in a styled panel."""
    console.print(Panel(
        Markdown(message),
        title="[bold bright_magenta]🤖 Zion[/]",
        border_style="bright_magenta",
        box=box.ROUNDED,
        padding=(0, 1),
    ))


def show_task_complete() -> None:
    """Display task completion indicator."""
    console.print(Text(" ✓ Task Complete", style="bold bright_green"))


def show_divider(title: str = None) -> None:
    """Show a styled divider."""
    if title:
        console.print(Rule(title, style="dim"))
    else:
        console.print(Rule(style="dim"))
