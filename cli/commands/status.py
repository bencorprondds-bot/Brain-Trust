"""
Status Command - Check Legion status and progress.
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(help="Check Legion status")
console = Console()


@app.callback(invoke_without_command=True)
def status_main(
    ctx: typer.Context,
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project"),
):
    """Show current Legion status."""
    if ctx.invoked_subcommand is not None:
        return

    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('cli', 1)[0])
        from backend.app.agents import get_willow
        from backend.app.core.capability_registry import get_capability_registry

        willow = get_willow()
        registry = get_capability_registry()

        # Status table
        table = Table(title="Legion Status", show_header=True)
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")

        # Willow status
        plan_status = "Active plan" if willow.current_plan else "Ready"
        table.add_row(
            "Willow",
            plan_status,
            willow.current_plan.intent_summary if willow.current_plan else "Awaiting commands",
        )

        # Capabilities
        caps = registry.get_all_capabilities()
        gaps = registry.get_open_gaps()
        table.add_row(
            "Capabilities",
            f"{len(caps)} available",
            f"{len(gaps)} gaps identified",
        )

        # Conversation
        table.add_row(
            "Conversation",
            f"{len(willow.conversation_history)} messages",
            "",
        )

        console.print(table)

        # Show current plan if any
        if willow.current_plan:
            console.print(Panel(
                willow.current_plan.to_display_string(),
                title="Current Plan",
                border_style="blue",
            ))

    except Exception as e:
        console.print(f"[red]Error getting status: {e}[/red]")


@app.command(name="plan")
def show_plan():
    """Show the current execution plan in detail."""
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('cli', 1)[0])
        from backend.app.agents import get_willow

        willow = get_willow()

        if willow.current_plan:
            console.print(Panel(
                willow.current_plan.to_display_string(),
                title="Current Plan",
                border_style="blue",
            ))
        else:
            console.print("[yellow]No active plan.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
