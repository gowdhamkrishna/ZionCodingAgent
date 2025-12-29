"""
Rich display components for Gemini-style output
"""
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich import box
from rich.markup import escape

console = Console()


def show_thinking_message(message: str):
    """Display a thinking/planning message before tool execution."""
    text = Text()
    text.append("✦ ", style="bright_cyan")
    text.append(message, style="white")
    console.print(text)


def show_tool_panel(tool_name: str, description: str, status: str = "running"):
    """
    Show a tool execution panel.
    
    Args:
        tool_name: Name of the tool (e.g., "WriteFile", "Shell")
        description: What the tool is doing (e.g., "Writing to blog/page.tsx")
        status: "running", "success", "error"
    """
    if status == "running":
        icon = "⠏"
        style = "cyan"
    elif status == "success":
        icon = "✓"
        style = "bright_green"
    else:
        icon = "✗"
        style = "bright_red"
    
    title = Text()
    title.append(f"{icon}  ", style=style)
    title.append(tool_name, style="bold white")
    title.append(" ", style="")
    title.append(description, style="dim white")
    
    console.print(title)


def show_command_panel(command: str, output: str, exit_code: int = 0, cwd: str = None):
    """Show command execution in a rich panel."""
    
    # Title
    title_text = Text()
    if exit_code == 0:
        title_text.append("✓  ", style="bright_green")
    else:
        title_text.append("✗  ", style="bright_red")
    
    title_text.append("Shell ", style="bold white")
    title_text.append(command, style="cyan")
    
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
        border_style="cyan" if exit_code == 0 else "red",
        box=box.ROUNDED,
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
        box=box.ROUNDED,
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
        display_diff = '\n'.join(lines[:40]) + f"\n... ({len(lines) - 40} more lines)"
    else:
        display_diff = diff_text
    
    console.print(Panel(
        display_diff if display_diff else "(no changes)",
        title=title_text,
        border_style="bright_green",
        box=box.ROUNDED,
        padding=(0, 1)
    ))


def show_step_separator():
    """Show a visual separator between steps."""
    console.print()
