"""
Approve Command - Approval workflow for Legion outputs.
"""

import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

app = typer.Typer(help="Approve Legion work")
console = Console()


@app.callback(invoke_without_command=True)
def approve_main(
    ctx: typer.Context,
    output_id: Optional[str] = typer.Option(None, "--id", help="Specific output ID to approve"),
):
    """Approve pending work or a specific output."""
    if ctx.invoked_subcommand is not None:
        return

    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('cli', 1)[0])
        from backend.app.agents import get_willow

        willow = get_willow()

        if willow.current_plan:
            console.print(Panel(
                willow.current_plan.to_display_string(),
                title="Plan to Approve",
                border_style="yellow",
            ))

            if Confirm.ask("Approve and execute this plan?"):
                with console.status("[cyan]Executing...[/cyan]"):
                    response = willow.approve_and_execute()

                if response.execution_result and response.execution_result.success:
                    console.print("[green]Plan executed successfully![/green]")
                    if response.execution_result.final_output:
                        console.print(Panel(
                            response.execution_result.final_output[:1000],
                            title="Result",
                            border_style="green",
                        ))
                else:
                    console.print("[red]Plan execution had issues.[/red]")
                    console.print(response.message)
            else:
                console.print("[yellow]Approval cancelled.[/yellow]")
        else:
            console.print("[yellow]No pending plan to approve.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command(name="list")
def list_pending():
    """List pending approvals."""
    console.print("[yellow]Pending approval tracking not yet implemented.[/yellow]")
    console.print("Use 'legion status' to see current plan.")
