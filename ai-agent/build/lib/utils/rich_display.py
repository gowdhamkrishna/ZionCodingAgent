"""
Rich display components for Gemini-style output
"""
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich import box
from rich.markup import escape
from utils.ui_components import COLORS

console = Console()


def show_thinking_message(message: str):
    """Display a thinking/planning message before tool execution."""
    text = Text()
    text.append("✦ ", style="bright_cyan")
    text.append(message, style="white")
    console.print(text)


def show_tool_panel(tool_name: str, description: str, status: str = "running"):
    """
    Show a tool execution panel styled as a System Log.
    """
    # Badges for different modules
    tool_lower = tool_name.lower()
    if "run" in tool_lower:
        badge = "[ EXEC ]"
        color = "bright_magenta"
    elif "write" in tool_lower or "edit" in tool_lower:
        badge = "[ WRIT ]"
        color = "spring_green1"
    elif "read" in tool_lower or "list" in tool_lower:
        badge = "[ READ ]"
        color = "deep_sky_blue1"
    else:
        badge = "[ SYS  ]"
        color = "white"

    if status == "running":
        icon = "⠏"
        status_color = color
    elif status == "success":
        icon = "✓"
        status_color = "bright_green"
    else:
        icon = "✗"
        status_color = "red1"
    
    # Format: [BADGE] ToolName :: Description
    text = Text()
    text.append(f"{badge} ", style=f"bold {color}")
    text.append(f"{tool_name.upper()}", style="bold dim white")
    text.append(" :: ", style="dim")
    text.append(description, style="white")
    text.append(f" {icon}", style=f"bold {status_color}")
    
    console.print(Panel(
        text,
        border_style=status_color,
        box=box.HEAVY, # Changed to HEAVY for cyber feel
        padding=(0, 1)
    ))


def show_command_panel(command: str, output: str, exit_code: int = 0, cwd: str = None):
    """Show command execution in a rich panel."""
    
    # Title
    title_text = Text()
    if exit_code == 0:
        title_text.append("✓  ", style=COLORS["success"])
        border_color = "bright_magenta" # Shell theme
    else:
        title_text.append("✗  ", style=COLORS["error"])
        border_color = COLORS["error"]
    
    title_text.append("Shell ", style="bold white")
    title_text.append(command, style="bright_magenta")
    
    if cwd:
        title_text.append(f" [in {cwd}]", style="dim")
    
    # Truncate output if too long
    lines = output.strip().split('\n')
    if len(lines) > 20:
        display_output = '\n'.join(lines[:20]) + f"\n... ({len(lines) - 20} more lines)"
    else:
        display_output = output.strip()
    
    console.print(Panel(
        escape(display_output) if display_output else "(no output)",
        title=title_text,
        border_style=border_color,
        box=box.HEAVY_EDGE, # Changed to HEAVY_EDGE
        padding=(0, 1)
    ))


def show_file_write_panel(file_path: str, content: str, status: str = "success"):
    """Show file write operation in a panel."""
    
    # Title
    title_text = Text()
    if status == "success":
        title_text.append("✓  ", style="bright_green")
    else:
        title_text.append("✗  ", style="bright_red")
    
    title_text.append("WriteFile ", style="bold white")
    title_text.append(f"Writing to {file_path}", style="cyan")
    
    # Detect language
    ext = file_path.split('.')[-1] if '.' in file_path else 'txt'
    lang_map = {
        'js': 'javascript', 'jsx': 'javascript', 'ts': 'typescript',
        'tsx': 'typescript', 'py': 'python', 'css': 'css',
        'html': 'html', 'json': 'json', 'md': 'markdown'
    }
    lang = lang_map.get(ext, 'text')
    
    # Limit display to first 30 lines
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
        title=title_text,
        border_style="bright_green" if status == "success" else "red",
        box=box.HEAVY_EDGE,
        padding=(0, 1)
    ))


def show_file_edit_panel(file_path: str, old_content: str, new_content: str):
    """Show file edit with diff in a panel."""
    import difflib
    
    title_text = Text()
    title_text.append("✓  ", style="bright_green")
    title_text.append("Edit ", style="bold white")
    title_text.append(f"{file_path}", style="cyan")
    
    # Generate simple diff
    old_lines = old_content.split('\n')
    new_lines = new_content.split('\n')
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        lineterm='',
        n=1  # Context lines
    )
    
    diff_text = ""
    line_num = 1
    for line in diff:
        if line.startswith('---') or line.startswith('+++'):
            continue
        if line.startswith('@@'):
            continue
        
        if line.startswith('+'):
            diff_text += f"{line_num:3} + {line[1:]}\n"
        elif line.startswith('-'):
            diff_text += f"{line_num:3} - {line[1:]}\n"
        else:
            diff_text += f"{line_num:3}   {line[1:] if line.startswith(' ') else line}\n"
        line_num += 1
    
    # Limit display
    lines = diff_text.split('\n')
    if len(lines) > 40:
        display_diff = '\n'.join(lines[:40]) + f"\n... ({len(lines) - 40} lines hidden)"
    else:
        display_diff = diff_text
    
    # Styled Panel
    console.print(Panel(
        display_diff if display_diff else "[italic dim]No changes detected[/]",
        title=f"[bold bright_cyan]EDITING :: {os.path.basename(file_path)}[/]",
        subtitle="[dim]Diff View[/dim]",
        border_style="spring_green1",
        box=box.DOUBLE, # Changed to DOUBLE for variety
        padding=(0, 1)
    ))


def show_step_separator():
    """Show a visual separator between steps."""
    console.print()
