# VS Code Extension Development Plan

1.  **Scaffold**: Use `yo code` (React Webview).
2.  **WebviewProvider**:
    *   Bridge between VS Code and React.
    *   Fetch state from `http://localhost:8000/state`.
    *   Post intent to `http://localhost:8000/goal`.
3.  **UI Components** (React):
    *   `StatusPill`: Green/Yellow/Red.
    *   `IntentInput`: Textarea with "Refine" button.
    *   `PlanView`: List of steps.
    *   `ToolApproval`: Show `pending_tool_call` with Approve/Reject buttons.
    *   `DiffView`: Use `monaco-editor` diff or VS Code's native `vscode.diff` command (preferred).

## Native Diff Strategy
Instead of rendering a diff *inside* the webview, we should use VS Code's native diff editor.
- When `pending_tool_call` is `write_file`:
    - Fetch content from `read_file` (current) and `args.content` (new).
    - Write temp file for new content.
    - Execute command `vscode.diff(current_uri, new_uri)`.
