import subprocess
import os
import sys
import re
import time
import signal
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

    def execute(self, command: str, timeout: int = 300, interactive: bool = True) -> str:
        """
        Execute a shell command with PTY for live interaction.
        
        Args:
            command: The command to run
            timeout: Max seconds to wait (default 300)
            interactive: Always True now, as we use PTY
        """
        return self._run_pty(command, timeout)
    
    def _run_pty(self, command: str, timeout: int) -> str:
        """Run command in a pseudo-terminal to support interaction and colors."""
        import pty
        import select
        import termios
        import tty
        import signal
        import time
        from rich.live import Live
        
        console.print(Panel(
            f"[bold cyan]Running:[/bold cyan] {escape(command)}\n"
            "[dim]Interact directly below. Press Ctrl+C to send SIGINT to process.[/dim]",
            title="[bold green]Live Terminal[/bold green]",
            border_style="green"
        ))

        # Create PTY
        master_fd, slave_fd = pty.openpty()
        
        try:
            # Start process connected to the slave PTY
            process = subprocess.Popen(
                command,
                shell=True,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=os.getcwd(),
                env={**os.environ, "TERM": "xterm-256color"},
                preexec_fn=os.setsid  # Create new session ID
            )
            os.close(slave_fd)  # Close slave in parent
            
            # Buffers
            captured_output = []
            start_time = time.time()
            
            # Save original TTY settings
            old_tty_settings = None
            try:
                old_tty_settings = termios.tcgetattr(sys.stdin)
                tty.setraw(sys.stdin.fileno())
            except:
                pass # Not a TTY (maybe running in pipe)

            try:
                while process.poll() is None:
                    # check timeout
                    if time.time() - start_time > timeout:
                        process.terminate()
                        return f"Error: Command timed out after {timeout}s"
                        
                    # Wait for data on master_fd (process output) or stdin (user input)
                    r, w, x = select.select([master_fd, sys.stdin], [], [], 0.1)
                    
                    if master_fd in r:
                        try:
                            data = os.read(master_fd, 1024)
                            if data:
                                # Write to user's screen (raw)
                                os.write(sys.stdout.fileno(), data)
                                # Buffer for LLM (decode and clean later)
                                captured_output.append(data)
                        except OSError:
                            break # Input/Output error (likely process closed)

                    if sys.stdin in r:
                        # User typed something
                        input_data = os.read(sys.stdin.fileno(), 1024)
                        if input_data:
                            # Forward to process
                            os.write(master_fd, input_data)
                            
            except Exception as e:
                pass
            finally:
                # Restore TTY settings
                if old_tty_settings:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty_settings)
            
            # Get exit code
            process.wait()
            return_code = process.returncode
            
            # Process captured output
            full_output_bytes = b"".join(captured_output)
            full_output_str = full_output_bytes.decode('utf-8', errors='replace')
            clean_output = strip_ansi_codes(full_output_str)
            
            if return_code == 0:
                console.print("\n[green]✓ Command completed[/green]")
            else:
                console.print(f"\n[red]✗ Command failed (exit {return_code})[/red]")
            
            return clean_output

        except Exception as e:
            return f"Error running PTY command: {str(e)}"
        finally:
            try:
                os.close(master_fd)
            except:
                pass
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
