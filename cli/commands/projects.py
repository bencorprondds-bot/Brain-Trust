"""
Projects Command - Manage Legion projects.
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(help="Manage projects")
console = Console()


# Known projects (from implementation plan)
PROJECTS = {
    "life_with_ai": {
        "name": "Life with AI",
        "description": "Stories, scripts, and world-building",
        "team": "Editorial",
        "quality_gate": "Pipeline approval",
    },
    "coloring_book": {
        "name": "Coloring Book",
        "description": "Coloring pages, PDFs, and sales",
        "team": "Production + Art Gen",
        "quality_gate": "Daughter approval",
    },
    "diamond_age_primer": {
        "name": "Diamond Age Primer",
        "description": "Interactive educational code",
        "team": "Technical",
        "quality_gate": "Engagement metrics",
    },
    "idle_game": {
        "name": "Life with AI Idle Game",
        "description": "Game code development",
        "team": "Technical",
        "quality_gate": "Playability, code review",
    },
}


@app.callback(invoke_without_command=True)
def projects_main(ctx: typer.Context):
    """List all projects."""
    if ctx.invoked_subcommand is not None:
        return

    table = Table(title="Legion Projects")
    table.add_column("Key", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Team")
    table.add_column("Quality Gate")

    for key, project in PROJECTS.items():
        table.add_row(
            key,
            project["name"],
            project["team"],
            project["quality_gate"],
        )

    console.print(table)


@app.command(name="info")
def project_info(project_key: str):
    """Show details for a specific project."""
    if project_key not in PROJECTS:
        console.print(f"[red]Unknown project: {project_key}[/red]")
        console.print(f"Available: {', '.join(PROJECTS.keys())}")
        return

    project = PROJECTS[project_key]

    console.print(Panel(
        f"[bold]{project['name']}[/bold]\n\n"
        f"[cyan]Description:[/cyan] {project['description']}\n"
        f"[cyan]Team:[/cyan] {project['team']}\n"
        f"[cyan]Quality Gate:[/cyan] {project['quality_gate']}",
        title=f"Project: {project_key}",
        border_style="green",
    ))

    # Show recent approvals for this project
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('cli', 1)[0])
        from backend.app.core.preference_memory import get_preference_memory

        memory = get_preference_memory()
        approvals = memory.get_approvals_for_project(project_key, limit=5)

        if approvals:
            console.print("\n[bold]Recent Approvals:[/bold]")
            for approval in approvals:
                console.print(f"  - [{approval.output_type}] {approval.content_summary or 'No summary'}")
    except Exception:
        pass


@app.command(name="set")
def set_project(project_key: str):
    """Set the active project context."""
    if project_key not in PROJECTS:
        console.print(f"[red]Unknown project: {project_key}[/red]")
        return

    # In a full implementation, this would set context for Willow
    console.print(f"[green]Active project set to: {PROJECTS[project_key]['name']}[/green]")
