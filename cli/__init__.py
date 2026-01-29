"""
Legion CLI

Command-line interface for interacting with Willow and the Legion.

Usage:
    legion                          # Interactive session
    legion "I want to finish chapter 3"   # Direct intent
    legion status                   # Check status
    legion approve                  # Approve pending work
    legion capabilities             # List capabilities
    legion eval run                 # Run evaluations
"""

import sys

# Fix Windows console encoding for emoji support
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        # Python < 3.7 fallback
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import typer
from typing import Optional
from rich.console import Console

from .interactive import interactive_session
from .commands import status, approve, capabilities, projects, logs, eval_cmd, config

# Create the main Typer app
app = typer.Typer(
    name="legion",
    help="Legion CLI - Command the Legion through Willow",
    add_completion=False,
)

console = Console()

# Add command groups
app.add_typer(status.app, name="status")
app.add_typer(approve.app, name="approve")
app.add_typer(capabilities.app, name="capabilities")
app.add_typer(projects.app, name="projects")
app.add_typer(logs.app, name="logs")
app.add_typer(eval_cmd.app, name="eval")
app.add_typer(config.app, name="config")


@app.command(name="gaps")
def list_gaps():
    """List capability gaps."""
    capabilities.list_gaps()


@app.command(name="agents")
def list_agents():
    """List available agents."""
    capabilities.list_agents()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    intent: Optional[str] = typer.Argument(None, help="Intent to send to Willow"),
):
    """
    Legion CLI - Interact with Willow and the Legion.

    Run without arguments for interactive mode.
    Run with an intent string to process directly.
    """
    # If a subcommand was invoked, don't run main logic
    if ctx.invoked_subcommand is not None:
        return

    if intent:
        # Process single intent
        from .interactive import process_single_intent
        process_single_intent(intent)
    else:
        # Enter interactive mode
        interactive_session()


def run():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    run()
