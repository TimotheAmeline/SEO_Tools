# llm_tracker/logger.py

from rich.console import Console

console = Console()

def log_console(message, level="info"):
    """Unified console logger with color-coded messages."""
    if level == "info":
        console.print(f"[cyan][INFO][/cyan] {message}")
    elif level == "success":
        console.print(f"[green][SUCCESS][/green] {message}")
    elif level == "warn":
        console.print(f"[yellow][WARN][/yellow] {message}")
    elif level == "error":
        console.print(f"[bold red][ERROR][/bold red] {message}")
    else:
        console.print(message)
