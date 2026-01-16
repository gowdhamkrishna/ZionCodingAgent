import sys
import os
import subprocess

# Add the parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.orchestrator import AgentOrchestrator
from core.git_version_manager import GitVersionManager as VersionManager
from tools.filesystem_tools import set_version_manager
from config import config
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
import questionary
from rich import box
from rich.rule import Rule
from rich.markup import escape
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.formatted_text import ANSI

console = Console()

# Global version manager
version_manager = None


def print_banner(provider: str, model_name: str):
    """Print beautiful Rich banner."""
    
    # ASCII art with gradient
    banner = Text()
    banner.append("╔═══════════════════════════════════════════════════════════════╗\n", style="bold bright_cyan")
    banner.append("║ ", style="bold bright_cyan")
    banner.append("███████╗", style="bold bright_magenta")
    banner.append("██╗", style="bold cyan")
    banner.append(" ██████╗ ", style="bold bright_magenta")
    banner.append("███╗   ██╗", style="bold cyan")
    banner.append("                            ", style="")
    banner.append("║\n", style="bold bright_cyan")
    
    banner.append("║ ", style="bold bright_cyan")
    banner.append("╚══███╔╝", style="bold magenta")
    banner.append("██║", style="bold cyan")
    banner.append("██╔═══██╗", style="bold magenta")
    banner.append("████╗  ██║", style="bold cyan")
    banner.append("                            ", style="")
    banner.append("║\n", style="bold bright_cyan")
    
    banner.append("║   ", style="bold bright_cyan")
    banner.append("███╔╝ ", style="bold bright_magenta")
    banner.append("██║", style="bold cyan")
    banner.append("██║   ██║", style="bold bright_magenta")
    banner.append("██╔██╗ ██║", style="bold cyan")
    banner.append("    ", style="")
    banner.append("AI Coding Agent", style="bold white")
    banner.append("          ", style="")
    banner.append("║\n", style="bold bright_cyan")
    
    banner.append("║  ", style="bold bright_cyan")
    banner.append("███╔╝  ", style="bold magenta")
    banner.append("██║", style="bold cyan")
    banner.append("██║   ██║", style="bold magenta")
    banner.append("██║╚██╗██║", style="bold cyan")
    banner.append("    ", style="")
    banner.append("v2.0 • Local • Fast", style="dim white")
    banner.append("       ", style="")
    banner.append("║\n", style="bold bright_cyan")
    
    banner.append("║ ", style="bold bright_cyan")
    banner.append("███████╗", style="bold bright_magenta")
    banner.append("██║", style="bold cyan")
    banner.append("╚██████╔╝", style="bold bright_magenta")
    banner.append("██║ ╚████║", style="bold cyan")
    banner.append("                            ", style="")
    banner.append("║\n", style="bold bright_cyan")
    
    banner.append("║ ", style="bold bright_cyan")
    banner.append("╚══════╝", style="bold magenta")
    banner.append("╚═╝", style="bold cyan")
    banner.append(" ╚═════╝ ", style="bold magenta")
    banner.append("╚═╝  ╚═══╝", style="bold cyan")
    banner.append("                            ", style="")
    banner.append("║\n", style="bold bright_cyan")
    
    banner.append("╚═══════════════════════════════════════════════════════════════╝", style="bold bright_cyan")
    
    console.print(banner)
    console.print()
    
    # Status panel
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    
    left = Text()
    left.append("  ", style="")
    left.append(f"[{provider.upper()}] ", style="bold bright_magenta")
    left.append("Model: ", style="dim")
    left.append(model_name, style="bold cyan")
    
    right = Text()
    right.append("📁 ", style="bright_blue")
    right.append(os.path.basename(os.getcwd()), style="bold white")
    
    grid.add_row(left, right)
    
    console.print(Panel(
        grid,
        border_style="bright_blue",
        box=box.DOUBLE_EDGE,
        padding=(0, 1),
    ))
    console.print()
    
    # Commands bar
    cmd_text = Text()
    cmd_text.append("  ", style="dim")
    commands = [("paste", "multi-line"), ("$", "shell"), ("new", "fresh-chat"), ("undo", "restore"), ("clear", "screen"), ("Ctrl+C", "cancel"), ("exit", "quit")]
    for i, (cmd, desc) in enumerate(commands):
        if i > 0:
            cmd_text.append(" │ ", style="dim")
        cmd_text.append(cmd, style="bold cyan")
        cmd_text.append(f":{desc}", style="dim")
    
    console.print(cmd_text)
    console.print()


def get_multiline_input():
    """Get multi-line input from user."""
    console.print("[dim italic]  📋 Paste mode: Enter content. To submit: Press Ctrl+D (EOF) or type ':q' on a new line.[/]")
    lines = []
    try:
        while True:
            line = input("    │ ")
            if line.strip() == ":q":
                break
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines)


def shell_mode():
    """Interactive shell access."""
    console.print("[bold cyan]Shell Mode[/bold cyan] [dim](type 'exit' to return)[/dim]")
    console.print()
    
    while True:
        try:
            prompt_text = Text()
            prompt_text.append("$ ", style="bold green")
            console.print(prompt_text, end="")
            cmd = input()
            
            if cmd.strip().lower() == "exit":
                console.print("[dim]Exited shell mode[/dim]\n")
                break
            
            if not cmd.strip():
                continue
            
            # Run command directly
            result = subprocess.run(cmd, shell=True, capture_output=False, text=True)
            
        except KeyboardInterrupt:
            console.print("\n[dim]Exited shell mode[/dim]\n")
            break


def main():
    global version_manager
    
    # Selection menu
    provider = questionary.select(
        "Select AI Provider",
        choices=["ollama", "gemini", "cerebras"],
        default=config.provider
    ).ask()
    
    if not provider: return # Handle Ctrl+C
    
    models = config.ollama_models if provider == "ollama" else (
        config.gemini_models if provider == "gemini" else config.cerebras_models
    )
    
    model_name = questionary.select(
        f"Select {provider.upper()} Model",
        choices=models,
        default=models[0]
    ).ask()
    
    if not model_name: return
    
    # Clear screen for a clean start
    console.clear()
    
    # Show banner with selected info
    print_banner(provider, model_name)
    
    workspace = os.getcwd()
    
    # Initialize agent with learning
    from core.learning_orchestrator import LearningOrchestrator
    agent = LearningOrchestrator(
        base_dir=workspace,
        provider=provider,
        model_name=model_name,
        enable_learning=True
    )
    
    # Display learning status
    if hasattr(agent, 'enable_learning'):
        if agent.enable_learning and agent.learner:
            console.print("[green]✓[/green] Learning mode active", style="dim")
        elif agent.enable_learning and not agent.learner:
            console.print("[yellow]⚠[/yellow] Learning mode disabled (initialization failed)", style="dim")
    console.print()
    
    # Initialize version manager
    version_manager = VersionManager(workspace)
    set_version_manager(version_manager)
    
    while True:
        try:
            # Use prompt_toolkit for protected prompt (can't backspace the ❯ symbol)
            from prompt_toolkit.styles import Style
            
            prompt_style = Style.from_dict({
                'prompt': '#00d7ff bold',  # Cyan color
            })
            
            user_input = pt_prompt(
                [('class:prompt', '\n❯ ')],
                style=prompt_style
            )
        except EOFError:
            console.print("\n[dim]  Session ended[/dim]\n")
            break
        except KeyboardInterrupt:
            console.print("\n\n[dim italic]  👋 Goodbye![/]\n")
            break
        
        try:
            cmd = user_input.lower().strip()
            
            # Exit commands
            if cmd in ["exit", "quit", "q"]:
                console.print("\n[dim italic]  👋 Goodbye![/]\n")
                break
            
            # Shell mode
            if cmd == "$" or cmd == "shell":
                shell_mode()
                continue
            
            # Clear screen
            if cmd == "clear" or cmd == "cls":
                console.clear()
                print_banner(agent.llm.provider, agent.llm.model_name)
                continue
            
            # New chat (reset + clear)
            if cmd == "new":
                agent.reset()
                console.clear()
                print_banner(agent.llm.provider, agent.llm.model_name)
                console.print("[dim cyan]  ✨ Started new chat session[/dim cyan]\n")
                continue
            
            # Reset memory
            if cmd == "reset":
                agent.reset()
                console.print("[dim]  🔄 Memory cleared[/dim]")
                continue
            
            # Version control commands
            if cmd == "/stats":
                if hasattr(agent, 'show_learning_stats'):
                    agent.show_learning_stats()
                else:
                    console.print("[yellow]  Learning mode is not available[/yellow]")
                continue
            
            if cmd == "undo":
                version_manager.undo_task()
                continue
            
            if cmd == "undo --file":
                version_manager.undo_last()
                continue
            
            if cmd.startswith("undo "):
                try:
                    idx = int(cmd.split()[1])
                    version_manager.restore_file(idx)
                except:
                    console.print("[red]  Usage: undo [index][/red]")
                continue
            
            if cmd == "history" or cmd == "log":
                version_manager.show_history()
                continue
            
            if cmd.startswith("show "):
                try:
                    idx = int(cmd.split()[1])
                    version_manager.show_backup(idx)
                except:
                    console.print("[red]  Usage: show [index][/red]")
                continue
            
            if cmd.startswith("diff "):
                try:
                    idx = int(cmd.split()[1])
                    version_manager.show_diff(idx)
                except:
                    console.print("[red]  Usage: diff [index][/red]")
                continue
            
            # Paste mode
            if cmd in ["paste", "p", "multi"]:
                user_input = get_multiline_input()
                if not user_input.strip():
                    continue
                lines = user_input.split("\n")
                console.print(f"[dim]  📥 Received {len(lines)} lines[/dim]")
            
            if not user_input.strip():
                continue
            
            # Separator
            console.print(Rule(style="dim"))
            
            # Set commit message before running task
            version_manager.set_commit_message(user_input.strip())
            
            # Run agent
            agent.run(user_input)
            
            # Show completion with enhanced visual
            console.print()
            completion = Text()
            completion.append("  ✓ ", style="bold bright_green")
            completion.append("Task Complete", style="bold white")
            console.print(Panel(
                completion,
                border_style="green",
                box=box.ROUNDED,
                padding=(0, 2)
            ))
            console.print()
            
            # Prompt for backtrack
            if questionary.confirm("Backtrack to last state (undo task)?", default=False).ask():
                version_manager.undo_task()
                console.print()
            
        except Exception as e:
            console.print(f"\n[bold red]  ⚠️  Error: {escape(str(e))}[/bold red]\n")

if __name__ == "__main__":
    main()
