import subprocess
import os
import re
from .base import BaseTool
from typing import Dict, Any
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

console = Console()


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\][^\x07]*\x07|\r')
    return ansi_pattern.sub('', text)


class RunCommandTool(BaseTool):
    def __init__(self):
        super().__init__("run_command", "Run a shell command")

    def execute(self, command: str, timeout: int = 120, interactive: bool = False) -> str:
        """
        Execute a shell command with timeout.
        
        Args:
            command: The command to run
            timeout: Max seconds to wait (default 120)
            interactive: If True, run in interactive mode for user input
        """
        # Check if this is a scaffolding command that needs interaction
        scaffolding_commands = ["create-next-app", "create-react-app", "create-vite", "npm init", "npx create"]
        is_scaffolding = any(cmd in command for cmd in scaffolding_commands)
        
        if is_scaffolding or interactive:
            return self._run_interactive(command, timeout)
        else:
            return self._run_standard(command, timeout)
    
    def _run_interactive(self, command: str, timeout: int) -> str:
        """Run command interactively using subprocess with live output."""
        console.print(Panel(
            f"[bold cyan]Running:[/bold cyan] {escape(command)}\n\n"
            "[dim]This command may ask for input. Respond in terminal.[/dim]\n"
            "[dim]Press Ctrl+C to cancel.[/dim]",
            title="[bold green]Interactive Mode[/bold green]",
            border_style="green"
        ))
        
        try:
            # Use subprocess with live output
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                cwd=os.getcwd(),
                text=True,
                bufsize=1,
                env={**os.environ, "TERM": "dumb", "CI": "false"}  # dumb term for cleaner output
            )
            
            output_lines = []
            try:
                for line in iter(process.stdout.readline, ''):
                    if not line:
                        break
                    clean_line = strip_ansi_codes(line.rstrip())
                    if clean_line.strip():  # Only print non-empty lines
                        console.print(f"[dim]{escape(clean_line)}[/dim]")
                        output_lines.append(clean_line)
                    
                process.wait(timeout=timeout)
                
            except subprocess.TimeoutExpired:
                process.kill()
                return f"Command timed out after {timeout} seconds."
            except KeyboardInterrupt:
                process.terminate()
                console.print("\n[yellow]Command cancelled[/yellow]")
                return "Command cancelled by user"
            
            return_code = process.returncode
            output = "\n".join(output_lines)
            
            if return_code == 0:
                console.print("[green]✓ Command completed[/green]")
            else:
                console.print(f"[red]✗ Command failed (exit {return_code})[/red]")
            
            return output if output else f"Exit code: {return_code}"
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _run_standard(self, command: str, timeout: int) -> str:
        """Run command in standard non-interactive mode."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd(),
                env={**os.environ, "CI": "true", "TERM": "dumb"}
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}"
            
            # Clean ANSI codes
            output = strip_ansi_codes(output)
            
            if not output.strip():
                if result.returncode == 0:
                    return "Command completed successfully"
                else:
                    return f"Command failed with exit code {result.returncode}"
            
            return output
            
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds."
        except Exception as e:
            return f"Error running command: {str(e)}"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 120)"},
                "interactive": {"type": "boolean", "description": "Run in interactive mode"}
            },
            "required": ["command"]
        }
