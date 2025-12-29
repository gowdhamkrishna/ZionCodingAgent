import json
import re
import os
import ast
from typing import Optional, Dict, Any, List
from core.llm_client import LLMClient
from config import config
from core.memory import Memory
from core.prompt_templates import MASTER_PROMPT
from tools.filesystem_tools import ReadFileTool, WriteFileTool, ListDirTool, EditFileTool, SearchFileTool, PatchFileTool
from tools.shell_tools import RunCommandTool
from tools.context_tools import FocusFileTool, UnfocusFileTool
from core.context_manager import ContextManager
from rich.markdown import Markdown
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from utils.ui_components import (
    show_code_preview, 
    show_tool_status,
    show_file_diff,
    show_command_output
)
from utils.approval_manager import FileApprovalManager
from utils.rich_display import (
    show_thinking_message,
    show_tool_panel,
    show_command_panel,
    show_file_write_panel,
    show_file_edit_panel,
    show_step_separator
)

console = Console()

class AgentOrchestrator:
    def __init__(self, base_dir: str = None, provider: str = None, model_name: str = None, enable_approvals: bool = False):  # Disabled by default
        self.base_dir = base_dir or os.getcwd()
        self.llm = LLMClient(provider=provider or config.provider, model_name=model_name or config.model_name)
        self.memory = Memory()
        self.context_manager = ContextManager()
        self.approval_manager = FileApprovalManager() if enable_approvals else None
        
        self.tools = {
            "read_file": ReadFileTool(),
            "write_file": WriteFileTool(),
            "edit_file": EditFileTool(),
            "patch_file": PatchFileTool(),
            "search_files": SearchFileTool(),
            "list_dir": ListDirTool(),
            "run_command": RunCommandTool(),
            "focus_file": FocusFileTool(self.context_manager),
            "unfocus_file": UnfocusFileTool(self.context_manager)
        }
        
        # Set approval manager on write tool
        if self.approval_manager:
            self.tools["write_file"].approval_manager = self.approval_manager
        
        self.SAFE_TOOLS = {"read_file", "list_dir", "search_files", "focus_file", "unfocus_file", "write_file", "edit_file", "patch_file", "run_command"}
        
        self.load_context()
        
    def load_context(self):
        """Scans the workspace to populate initial context."""
        try:
            # List root files
            list_tool = self.tools["list_dir"]
            files = list_tool.execute(self.base_dir)
            
            # Read README if exists
            readme_content = ""
            readme_path = os.path.join(self.base_dir, "README.md")
            if os.path.exists(readme_path):
                read_tool = self.tools["read_file"]
                # proper usage: execute(file_path, start_line=1, end_line=50)
                # But since we are calling it directly as a class method in python (not via LLM json), 
                # we can just call it. Wait, the tool.execute signature is: file_path, start_line, end_line
                readme_content = read_tool.execute(readme_path, start_line=1, end_line=50)
            
            context_msg = f"""
PROJECT CONTEXT INITIALIZATION
-----------------------------
Base Directory: {self.base_dir}

Root Files:
{files}

README Summary (First 50 lines):
{readme_content or "No README.md found."}
-----------------------------
"""
            self.memory.add_user_message(context_msg)
            console.print(f"[dim]Loaded project context from {self.base_dir}[/dim]")
            
        except Exception as e:
            console.print(f"[bold red]Failed to load context: {e}[/bold red]")
        
        # State
        self.status = "idle" # idle, thinking, waiting_approval, error
        self.status = "idle" # idle, thinking, waiting_approval, error
        self.plan: List[Dict[str, str]] = [] # [{"text": "step", "status": "pending"}]
        self.current_thought = ""
        self.last_action = ""
        self.pending_tool_call: Optional[Dict[str, Any]] = None
        self.error_message = ""
        self.tool_history = [] # Track recent tool calls to prevent loops

    def reset(self):
        self.memory.clear()
        self.status = "idle"
        self.plan = []
        self.current_thought = ""
        self.last_action = ""
        self.pending_tool_call = None
        self.error_message = ""
        self.tool_history = []

    def set_goal(self, goal: str):
        self.reset()
        self.memory.add_user_message(goal)
        self.status = "thinking"
        # In a real async system, we'd trigger a background task here.
        # For this implementation, the "step()" method will be called by the server.

    def _preprocess_response(self, text: str) -> str:
        """Convert Python-style triple-quoted strings to valid JSON strings."""
        # Find triple-quoted strings and convert them
        result = text
        
        # Pattern to find: "key": """content"""
        triple_quote_pattern = re.compile(r':\s*"""(.*?)"""', re.DOTALL)
        
        def replace_triple_quotes(match):
            content = match.group(1)
            # Escape for JSON: handle newlines, quotes, backslashes
            content = content.replace('\\', '\\\\')
            content = content.replace('"', '\\"')
            content = content.replace('\n', '\\n')
            content = content.replace('\r', '\\r')
            content = content.replace('\t', '\\t')
            return f': "{content}"'
        
        result = triple_quote_pattern.sub(replace_triple_quotes, result)
        return result

    def parse_response(self, text: str):
        """Parses the LLM response to extract Plan and Tool Calls."""
        self.pending_tool_call = None
        
        # Preprocess to handle Python-style triple quotes
        text = self._preprocess_response(text)
        
        # Method 1: Find JSON in code blocks first (most reliable)
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                if "tool" in parsed and "args" in parsed:
                    self.pending_tool_call = parsed
                    return
            except:
                pass
        
        # Method 2: Find {"tool": by scanning for balanced braces
        tool_pattern_start = re.search(r'\{\s*"tool"\s*:', text)
        if tool_pattern_start:
            start_idx = tool_pattern_start.start()
            # Count braces to find complete JSON object
            brace_count = 0
            in_string = False
            escape_next = False
            end_idx = start_idx
            
            for i, char in enumerate(text[start_idx:], start=start_idx):
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            if brace_count == 0 and end_idx > start_idx:
                tool_code = text[start_idx:end_idx]
                try:
                    self.pending_tool_call = json.loads(tool_code)
                    return
                except json.JSONDecodeError:
                    # Try ast.literal_eval for Python-style dicts
                    try:
                        self.pending_tool_call = ast.literal_eval(tool_code)
                        return
                    except:
                        pass
        
        # Method 3: Parse "tool_name: {args}" format (e.g., "read_file: {"file_path": "..."}")
        alt_pattern = re.search(r'(read_file|write_file|run_command|list_dir|edit_file):\s*(\{[^}]+\})', text)
        if alt_pattern:
            tool_name = alt_pattern.group(1)
            args_str = alt_pattern.group(2)
            try:
                args = json.loads(args_str)
                self.pending_tool_call = {"tool": tool_name, "args": args}
                return
            except:
                pass

    def step(self):
        """Advances the agent state by one step."""
        if self.status == "waiting_approval":
            return # Blocked
        
        if self.status == "idle" and self.memory.get_messages():
            self.status = "thinking"

        if self.status == "thinking":
            # Call LLM
            # Inject Active Context
            active_context = self.context_manager.get_context_formatted()
            
            system_msg = {"role": "system", "content": MASTER_PROMPT}
            history = self.memory.get_messages()
            
            # Insert active context as a high-priority system message before history
            if active_context:
                context_msg = {"role": "system", "content": active_context}
                messages = [system_msg, context_msg] + history
            else:
                messages = [system_msg] + history
            
            # Retry logic for LLM calls
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        console.print(f"[yellow]Retrying ({attempt + 1}/{max_retries})...[/yellow]")
                    
                    response_text = self.llm.chat(messages)
                    
                    # Check if response indicates timeout error
                    if "timed out" in response_text.lower() or "timeout" in response_text.lower():
                        last_error = "LLM request timed out"
                        continue

                    # Check for massive repetition (LLM breakdown)
                    # If more than 30 lines and unique lines are less than 20%
                    lines = [l.strip() for l in response_text.split('\n') if l.strip()]
                    if len(lines) > 30:
                        unique_lines = set(lines)
                        if len(unique_lines) / len(lines) < 0.2:
                             error_msg = ("CRITICAL: Your response is extremely repetitive. "
                                        "Stop repeating the same sentences. "
                                        "Focus on the task and use the appropriate tool.")
                             messages.append({"role": "user", "content": error_msg})
                             console.print("[red]⚠ Massive repetition detected (LLM breakdown). Retrying...[/red]")
                             continue
                    
                    self.parse_response(response_text)
                    
                    # HARD GUARD: Anti-Simulation Protocol
                    # If response contains code blocks (```) but NO tool call, reject it.
                    if "```" in response_text and not self.pending_tool_call:
                        # Allow "plan" blocks if they are short, but reject big code blocks
                        code_block_match = re.search(r"```(?!json|plan)\w*\n.*?\n```", response_text, re.DOTALL)
                        if code_block_match:
                            error_msg = ("VIOLATION: You wrote code in the chat. "
                                       "This is strictly FORBIDDEN. "
                                       "You MUST use the 'write_file' tool to create code. "
                                       "Retry and use the tool.")
                            messages.append({"role": "user", "content": error_msg})
                            console.print("[red]⚠ Rejected simulation attempt (Ghost Code detected). Retrying...[/red]")
                            continue
                    
                    # Detect if tool mentioned but not called
                    if not self.pending_tool_call:
                        detected_tool = None
                        for t in self.tools.keys():
                            if f"\"{t}\"" in response_text or f"'{t}'" in response_text or f"Command: {t}" in response_text:
                                detected_tool = t
                                break
                        
                        if detected_tool:
                             error_msg = (f"VIOLATION: You mentioned using '{detected_tool}' but did not provide the JSON tool call. "
                                        "You MUST output tool calls in the format: "
                                        "{\"tool\": \"name\", \"args\": {...}} inside a code block.")
                             messages.append({"role": "user", "content": error_msg})
                             console.print(f"[red]⚠ Tool call missing for '{detected_tool}'. Retrying...[/red]")
                             continue

                    self.memory.add_assistant_message(response_text)
                    self.last_action = "Generated response"
                    
                    if self.pending_tool_call:
                        self.status = "waiting_approval"
                    else:
                        self.status = "idle"
                    
                    return response_text
                    
                except Exception as e:
                    last_error = str(e)
                    if attempt < max_retries - 1:
                        continue
            
            # All retries failed
            self.status = "idle"  # Return to idle so user can try again
            error_msg = f"LLM failed after {max_retries} attempts: {last_error}"
            console.print(f"[red]⚠ {error_msg}[/red]")
            console.print("[dim]Tip: Try simplifying your request or check if ollama is running[/dim]")
            self.last_action = "Error (recoverable)"
            return None

    def approve_tool(self):
        """Executes the pending tool call."""
        if not self.pending_tool_call:
            return

        tool_name = self.pending_tool_call.get("tool")
        args = self.pending_tool_call.get("args", {})
        
        # Track tool call for loop detection
        call_id = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
        self.tool_history.append(call_id)
        if len(self.tool_history) > 10:
            self.tool_history.pop(0)

        if tool_name in self.tools:
            tool_instance = self.tools[tool_name]
            try:
                # Show tool panel before execution
                short_args = str(args)[:50] + "..." if len(str(args)) > 50 else str(args)
                show_tool_panel(tool_name, short_args, "running")
                
                result = tool_instance.execute(**args)
                
                # Intelligent error detection in result string
                is_actual_error = False
                if isinstance(result, str) and (result.startswith("Error:") or result.startswith("VIOLATION:")):
                    is_actual_error = True
                
                # Show enhanced output panels
                if tool_name == "run_command":
                    cmd = args.get("command", "")
                    exit_code = 0
                    if "exit code:" in result.lower():
                        try:
                            exit_code = int(result.split("exit code:")[-1].strip())
                        except:
                            pass
                    if is_actual_error: exit_code = 1
                    show_command_panel(cmd, result, exit_code)
                elif tool_name == "write_file":
                    file_path = args.get("file_path", "")
                    content = args.get("content", "")
                    show_file_write_panel(file_path, content, "error" if is_actual_error else "success")
                elif tool_name == "edit_file":
                    file_path = args.get("file_path", "")
                    old_content = ""
                    new_content = args.get("new_content", "") or args.get("replacement", "")
                    try:
                        if os.path.exists(file_path):
                            with open(file_path, 'r') as f:
                                old_content = f.read()
                    except:
                        pass
                    if not is_actual_error and old_content:
                        show_file_edit_panel(file_path, old_content, new_content)
                    else:
                        console.print(f"[red]✗ {tool_name}: {result}[/red]")
                else:
                    status = "error" if is_actual_error else "success"
                    show_tool_panel(tool_name, result[:100], status)
                
                result_msg = f"Tool '{tool_name}' Output:\n{result}"
                self.memory.add_user_message(result_msg)
                self.last_action = f"Executed {tool_name}"
                
                if is_actual_error:
                    self.status = "thinking" # Loop back, but LLM will see error
            except Exception as e:
                error_msg = f"Tool execution fatal error: {str(e)}"
                self.memory.add_user_message(error_msg)
                self.last_action = f"Fatal error: {e}"
                console.print(f"[bold red]FATAL ✗ {tool_name}: {str(e)}[/bold red]")
        else:
            self.memory.add_user_message(f"Error: Tool '{tool_name}' not found.")
        
        self.pending_tool_call = None
        self.status = "thinking" # Loop back to LLM

    def reject_tool(self):
        """Cancels the pending tool call."""
        self.pending_tool_call = None
        self.memory.add_user_message("Tool execution cancelled by user.")
        self.status = "thinking" # Loop back to LLM

    def run(self, message: str):
        """Main execution loop for CLI with enhanced UI."""
        self.memory.add_user_message(message)
        self.status = "thinking"
        self.tool_history = []
        
        MAX_ITERATIONS = 30 # Increased for complex tasks
        iteration = 0

        try:
            while self.status in ["thinking", "waiting_approval"] and iteration < MAX_ITERATIONS:
                iteration += 1
                
                # Enhanced Loop Detection
                if len(self.tool_history) >= 3:
                    last_three = self.tool_history[-3:]
                    
                    # Pattern 1: Same tool+args 3 times in a row
                    if last_three[0] == last_three[1] == last_three[2]:
                        warning_msg = (f"LOOP DETECTED: You have called {last_three[0]} three times in a row. "
                                     "If you have already received the output, YOU HAVE THE DATA. "
                                     "STOP REPEATING and MOVE TO THE NEXT PHASE (Plan or Execute). "
                                     "If you are stuck, try listing the directory or searching for files.")
                        self.memory.add_user_message(warning_msg)
                        console.print("[yellow]⚠ Intervention: Loop detected. Forceful warning sent to agent.[/yellow]")
                    
                    # Pattern 2: Repeated read/patch on same file
                    if len(self.tool_history) >= 6:
                        last_six = self.tool_history[-6:]
                        # Extract file paths from tool history
                        file_operations = []
                        for call in last_six:
                            if 'read_file:' in call or 'patch_file:' in call or 'edit_file:' in call or 'write_file:' in call:
                                # Extract the file path from the call
                                try:
                                    import json
                                    _, args_str = call.split(':', 1)
                                    args = json.loads(args_str)
                                    file_path = args.get('file_path', '')
                                    if file_path:
                                        file_operations.append(file_path)
                                except:
                                    pass
                        
                        # If we're operating on the same file 5+ times, intervene
                        if len(file_operations) >= 5:
                            from collections import Counter
                            file_counts = Counter(file_operations)
                            most_common_file, count = file_counts.most_common(1)[0]
                            if count >= 4:
                                warning_msg = (f"LOOP DETECTED: You have operated on '{most_common_file}' {count} times recently. "
                                             "The task appears to be complete. "
                                             "STOP MODIFYING THIS FILE and declare the task complete. "
                                             "Do NOT read, patch, or edit it again unless there is a clear error.")
                                self.memory.add_user_message(warning_msg)
                                console.print(f"[bold red]⚠ CRITICAL: File modification loop detected on {most_common_file}. Forcing stop.[/bold red]")
                
                # Show thinking animation
                from rich.live import Live
                from rich.spinner import Spinner
                
                thinking_text = Text()
                thinking_text.append("  ", style="")
                thinking_text.append("🤔 ", style="")
                thinking_text.append("Thinking", style="bold cyan")
                thinking_text.append("...", style="dim")
                
                spinner = Spinner("dots", text=thinking_text, style="cyan")
                
                with Live(spinner, console=console, refresh_per_second=10, transient=True):
                    response = self.step()
                
                if response:
                    # Check if task is complete (no tool call)
                    if not self.pending_tool_call:
                        console.print(Panel(
                            Markdown(response),
                            title="[bold green]Zion Agent[/bold green]",
                            border_style="green",
                            expand=True
                        ))
                        show_tool_status("Task", "success", "Complete")
                        break
                
                if self.status == "waiting_approval":
                    tool_call = self.pending_tool_call
                    tool_name = tool_call.get("tool")
                    args = tool_call.get("args", {})
                    
                    # Show code preview for write_file
                    if tool_name == "write_file" and "content" in args and "file_path" in args:
                        show_code_preview(args["content"], args["file_path"])
                    
                    # Show diff preview for edit_file
                    if tool_name == "edit_file" and "file_path" in args:
                        file_path = args["file_path"]
                        if os.path.exists(file_path):
                            try:
                                with open(file_path, "r") as f:
                                    old_content = f.read()
                                target = args.get("target", "")
                                replacement = args.get("replacement", "")
                                new_content = old_content.replace(target, replacement)
                                show_file_diff(file_path, old_content, new_content)
                            except:
                                pass
                    
                    # Check for auto-approval
                    if tool_name in self.SAFE_TOOLS:
                        # Show meaningful status based on tool type
                        if tool_name == "run_command":
                            show_tool_status(
                                tool_name,
                                "running",
                                f"Executing: {args.get('command', 'N/A')}"
                            )
                        else:
                            show_tool_status(tool_name, "running", "Auto-approved")
                        self.approve_tool()
                        
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠ Task cancelled by user[/yellow]")
            self.status = "idle"
            self.pending_tool_call = None
            return None
        """Main execution loop for CLI with enhanced UI."""
        self.memory.add_user_message(message)
        self.status = "thinking"
        self.tool_history = []
        
        MAX_ITERATIONS = 30 # Increased for complex tasks
        iteration = 0

        while self.status in ["thinking", "waiting_approval"] and iteration < MAX_ITERATIONS:
            iteration += 1
            
            # Enhanced Loop Detection
            if len(self.tool_history) >= 3:
                last_three = self.tool_history[-3:]
                
                # Pattern 1: Same tool+args 3 times in a row
                if last_three[0] == last_three[1] == last_three[2]:
                    warning_msg = (f"LOOP DETECTED: You have called {last_three[0]} three times in a row. "
                                 "If you have already received the output, YOU HAVE THE DATA. "
                                 "STOP REPEATING and MOVE TO THE NEXT PHASE (Plan or Execute). "
                                 "If you are stuck, try listing the directory or searching for files.")
                    self.memory.add_user_message(warning_msg)
                    console.print("[yellow]⚠ Intervention: Loop detected. Forceful warning sent to agent.[/yellow]")
                
                # Pattern 2: Repeated read/patch on same file
                if len(self.tool_history) >= 6:
                    last_six = self.tool_history[-6:]
                    # Extract file paths from tool history
                    file_operations = []
                    for call in last_six:
                        if 'read_file:' in call or 'patch_file:' in call or 'edit_file:' in call or 'write_file:' in call:
                            # Extract the file path from the call
                            try:
                                import json
                                _, args_str = call.split(':', 1)
                                args = json.loads(args_str)
                                file_path = args.get('file_path', '')
                                if file_path:
                                    file_operations.append(file_path)
                            except:
                                pass
                    
                    # If we're operating on the same file 5+ times, intervene
                    if len(file_operations) >= 5:
                        from collections import Counter
                        file_counts = Counter(file_operations)
                        most_common_file, count = file_counts.most_common(1)[0]
                        if count >= 4:
                            warning_msg = (f"LOOP DETECTED: You have operated on '{most_common_file}' {count} times recently. "
                                         "The task appears to be complete. "
                                         "STOP MODIFYING THIS FILE and declare the task complete. "
                                         "Do NOT read, patch, or edit it again unless there is a clear error.")
                            self.memory.add_user_message(warning_msg)
                            console.print(f"[bold red]⚠ CRITICAL: File modification loop detected on {most_common_file}. Forcing stop.[/bold red]")
            
            # Show thinking status
            # console.print("[dim]◐ Thinking...[/dim]", end="\r")
            response = self.step()
            # console.print(" " * 20, end="\r") 
            
            if response:
                # Check if task is complete (no tool call)
                if not self.pending_tool_call:
                    console.print(Panel(
                        Markdown(response),
                        title="[bold green]Zion Agent[/bold green]",
                        border_style="green",
                        expand=True
                    ))
                    show_tool_status("Task", "success", "Complete")
                    break
            
            if self.status == "waiting_approval":
                tool_call = self.pending_tool_call
                tool_name = tool_call.get("tool")
                args = tool_call.get("args", {})
                
                # Show code preview for write_file
                if tool_name == "write_file" and "content" in args and "file_path" in args:
                    show_code_preview(args["content"], args["file_path"])
                
                # Show diff preview for edit_file
                if tool_name == "edit_file" and "file_path" in args:
                    file_path = args["file_path"]
                    if os.path.exists(file_path):
                        try:
                            with open(file_path, "r") as f:
                                old_content = f.read()
                            target = args.get("target", "")
                            replacement = args.get("replacement", "")
                            new_content = old_content.replace(target, replacement)
                            show_file_diff(file_path, old_content, new_content)
                        except:
                            pass
                
                # Check for auto-approval
                if tool_name in self.SAFE_TOOLS:
                    # Show meaningful status based on tool type
                    if tool_name == "run_command":
                        cmd = args.get("command", "")[:50]  # Truncate long commands
                        show_tool_status("run", "running", cmd)
                    elif tool_name == "write_file":
                        show_tool_status("write", "running", os.path.basename(args.get("file_path", "")))
                    elif tool_name == "read_file":
                        show_tool_status("read", "running", os.path.basename(args.get("file_path", "")))
                    elif tool_name == "list_dir":
                        show_tool_status("list", "running", args.get("dir_path", "")[-30:])
                    else:
                        show_tool_status(tool_name, "running")
                    
                    self.approve_tool()
                    
                    # Show success with result
                    if tool_name == "run_command":
                        show_tool_status("run", "success", cmd)
                    elif tool_name in ["write_file", "edit_file"]:
                        show_tool_status("write", "success", os.path.basename(args.get("file_path", "")))
                    else:
                        show_tool_status(tool_name, "success")
                    continue
                
                # Manual approval needed
                tool_panel = Panel(
                    f"Tool: [cyan]{tool_name}[/cyan]\n"
                    f"Args: {json.dumps(args, indent=2)}",
                    title="[bold yellow]⚠ Approval Required[/bold yellow]",
                    border_style="yellow"
                )
                console.print(tool_panel)
                
                user_response = console.input("[bold yellow]Approve? (y/n) > [/bold yellow]")
                if user_response.lower() == 'y':
                    show_tool_status(tool_name, "running")
                    self.approve_tool()
                    show_tool_status(tool_name, "success")
                else:
                    self.reject_tool()
                    show_tool_status(tool_name, "error", "Rejected by user")
            
            if self.status == "error":
                show_tool_status("Error", "error", self.error_message)
                break
            
            if self.status == "idle":
                show_tool_status("Task", "success", "Complete")
                break
        
        if iteration >= MAX_ITERATIONS:
            console.print(f"[yellow]⚠ Reached max iterations ({MAX_ITERATIONS}). Stopping.[/yellow]")
