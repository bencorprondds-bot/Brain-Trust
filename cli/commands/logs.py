"""
Logs Command - View execution logs.
"""

import typer
from typing import Optional
from datetime import date, timedelta
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="View execution logs")
console = Console()


@app.callback(invoke_without_command=True)
def logs_main(
    ctx: typer.Context,
    today: bool = typer.Option(False, "--today", help="Show only today's logs"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of entries"),
):
    """View recent execution logs."""
    if ctx.invoked_subcommand is not None:
        return

    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('cli', 1)[0])
        from backend.app.core.preference_memory import get_preference_memory

        memory = get_preference_memory()

        if project:
            approvals = memory.get_approvals_for_project(project, limit=limit)
        else:
            # Get recent from all projects
            approvals = []
            for proj in ["life_with_ai", "coloring_book", "diamond_age_primer", "idle_game"]:
                approvals.extend(memory.get_approvals_for_project(proj, limit=limit // 4))

        # Sort by date
        approvals.sort(key=lambda a: a.approved_at, reverse=True)

        if today:
            today_date = date.today()
            approvals = [a for a in approvals if a.approved_at.date() == today_date]

        if approvals:
            table = Table(title="Execution Log")
            table.add_column("Date", style="dim")
            table.add_column("Project", style="cyan")
            table.add_column("Type")
            table.add_column("Summary")

            for approval in approvals[:limit]:
                table.add_row(
                    approval.approved_at.strftime("%Y-%m-%d %H:%M"),
                    approval.project,
                    approval.output_type,
                    (approval.content_summary or "")[:50],
                )

            console.print(table)
        else:
            console.print("[yellow]No log entries found.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command(name="digest")
def show_digest(
    date_str: Optional[str] = typer.Argument(None, help="Date (YYYY-MM-DD) or 'today'"),
):
    """Show daily digest for a specific date."""
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('cli', 1)[0])
        from backend.app.core.preference_memory import get_preference_memory

        memory = get_preference_memory()

        if date_str is None or date_str == "today":
            target_date = date.today()
        else:
            target_date = date.fromisoformat(date_str)

        digest = memory.get_digest(target_date)

        if digest:
            console.print(f"\n[bold]Daily Digest: {target_date}[/bold]")

            if digest.escalation_requests:
                console.print(f"\n[yellow]Escalations ({len(digest.escalation_requests)}):[/yellow]")
                for esc in digest.escalation_requests:
                    console.print(f"  - {esc}")

            if digest.decisions_made:
                console.print(f"\n[green]Decisions ({len(digest.decisions_made)}):[/green]")
                for dec in digest.decisions_made:
                    console.print(f"  - {dec}")

            if digest.outputs_delivered:
                console.print(f"\n[cyan]Delivered ({len(digest.outputs_delivered)}):[/cyan]")
                for out in digest.outputs_delivered:
                    console.print(f"  - {out}")

            if digest.delivered_at:
                console.print(f"\n[dim]Delivered via {digest.delivery_channel} at {digest.delivered_at}[/dim]")
        else:
            console.print(f"[yellow]No digest for {target_date}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
