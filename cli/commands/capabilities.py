"""
Capabilities Command - List and manage Legion capabilities.
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Manage Legion capabilities")
console = Console()


@app.callback(invoke_without_command=True)
def capabilities_main(
    ctx: typer.Context,
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Filter by team"),
):
    """List available Legion capabilities."""
    if ctx.invoked_subcommand is not None:
        return

    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('cli', 1)[0])
        from backend.app.core.capability_registry import get_capability_registry, CapabilityCategory

        registry = get_capability_registry()

        if category:
            try:
                cat_enum = CapabilityCategory(category)
                caps = registry.get_by_category(cat_enum)
            except ValueError:
                console.print(f"[red]Unknown category: {category}[/red]")
                return
        elif team:
            caps = registry.get_by_team(team)
        else:
            caps = registry.get_all_capabilities()

        table = Table(title=f"Legion Capabilities ({len(caps)})")
        table.add_column("Name", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Category")
        table.add_column("Success Rate")
        table.add_column("Executions")

        for cap in caps:
            table.add_row(
                cap.name,
                cap.agent_role,
                cap.category.value,
                f"{cap.success_rate:.0%}",
                str(cap.execution_count),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command(name="search")
def search_capabilities(query: str):
    """Search capabilities by keyword."""
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('cli', 1)[0])
        from backend.app.core.capability_registry import get_capability_registry

        registry = get_capability_registry()
        results = registry.search(query)

        if results:
            console.print(f"\n[bold]Found {len(results)} capabilities for '{query}':[/bold]")
            for cap in results:
                console.print(f"  - {cap.name} ({cap.agent_role}): {cap.description}")
        else:
            console.print(f"[yellow]No capabilities found for '{query}'[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def list_gaps():
    """List capability gaps (called from main app)."""
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('cli', 1)[0])
        from backend.app.core.capability_registry import get_capability_registry

        registry = get_capability_registry()
        gaps = registry.get_open_gaps()

        if gaps:
            table = Table(title=f"Capability Gaps ({len(gaps)})")
            table.add_column("ID", style="dim")
            table.add_column("Description", style="cyan")
            table.add_column("Priority", style="yellow")
            table.add_column("Status")

            for gap in gaps:
                table.add_row(
                    gap.id,
                    gap.description,
                    gap.priority,
                    gap.status,
                )

            console.print(table)
        else:
            console.print("[green]No capability gaps![/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def list_agents():
    """List available agents (called from main app)."""
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('cli', 1)[0])
        from backend.app.core.capability_registry import get_capability_registry

        registry = get_capability_registry()
        caps = registry.get_all_capabilities()

        # Group by agent
        agents = {}
        for cap in caps:
            if cap.agent_role not in agents:
                agents[cap.agent_role] = []
            agents[cap.agent_role].append(cap.name)

        console.print(f"\n[bold]Legion Agents ({len(agents)}):[/bold]")
        for agent, capabilities in sorted(agents.items()):
            console.print(f"\n  [cyan]{agent}[/cyan]")
            for cap_name in capabilities:
                console.print(f"    - {cap_name}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
