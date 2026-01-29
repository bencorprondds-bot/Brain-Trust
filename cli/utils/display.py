"""
Display utilities for the Legion CLI.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def format_plan(plan) -> str:
    """Format a plan for display."""
    return plan.to_display_string()


def format_result(result) -> str:
    """Format an execution result for display."""
    lines = [
        f"Status: {result.status.value}",
        f"Duration: {result.total_duration_seconds:.1f}s",
    ]

    if result.final_output:
        lines.append(f"\nOutput:\n{result.final_output[:500]}")

    return "\n".join(lines)


def print_table(title: str, columns: list, rows: list) -> None:
    """Print a formatted table."""
    table = Table(title=title)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*[str(cell) for cell in row])
    console.print(table)


def print_panel(content: str, title: str = "", style: str = "blue") -> None:
    """Print a panel."""
    console.print(Panel(content, title=title, border_style=style))
