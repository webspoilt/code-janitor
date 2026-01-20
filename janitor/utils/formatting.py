"""
Formatting and console output utilities using Rich.
"""

from typing import Optional, List
import difflib

try:
    from rich.console import Console
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.theme import Theme
except ImportError:
    # Fallback to standard print if rich is not installed
    Console = None  # type: ignore

class RichConsole:
    """Wrapper around rich.console for consistent output styling."""
    
    def __init__(self):
        if Console:
            self.console = Console(theme=Theme({
                "info": "cyan",
                "warning": "yellow",
                "error": "bold red",
                "success": "bold green",
                "code": "bold magenta"
            }))
        else:
            self.console = None

    def print(self, *args, **kwargs):
        """Print to console."""
        if self.console:
            self.console.print(*args, **kwargs)
        else:
            print(*args, **kwargs)

    def log_info(self, message: str):
        """Log info message."""
        if self.console:
            self.console.print(f"[info]ℹ[/info] {message}")
        else:
            print(f"[INFO] {message}")

    def log_warning(self, message: str):
        """Log warning message."""
        if self.console:
            self.console.print(f"[warning]⚠[/warning] {message}")
        else:
            print(f"[WARNING] {message}")

    def log_error(self, message: str):
        """Log error message."""
        if self.console:
            self.console.print(f"[error]✖ {message}[/error]")
        else:
            print(f"[ERROR] {message}")
            
    def log_success(self, message: str):
        """Log success message."""
        if self.console:
            self.console.print(f"[success]✔[/success] {message}")
        else:
            print(f"[SUCCESS] {message}")

    def print_diff(self, original: str, modified: str, filename: str = "Code"):
        """Print a side-by-side or unified diff."""
        if not self.console:
            diff = difflib.unified_diff(
                original.splitlines(),
                modified.splitlines(),
                fromfile=f"Original {filename}",
                tofile=f"Modified {filename}",
                lineterm=""
            )
            print("\n".join(diff))
            return

        # Create a unified diff syntax highlight
        diff_lines = list(difflib.unified_diff(
            original.splitlines(),
            modified.splitlines(),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        ))
        
        if not diff_lines:
            self.log_info(f"No changes detected in {filename}")
            return
            
        diff_text = "\n".join(diff_lines)
        syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
        
        self.console.print(Panel(
            syntax,
            title=f"Diff: {filename}",
            border_style="blue",
            expand=False
        ))

    def print_panel(self, content: str, title: str = "", style: str = "white"):
        """Print a panel."""
        if self.console:
            self.console.print(Panel(content, title=title, border_style=style))
        else:
            print(f"\n--- {title} ---\n{content}\n----------------")
