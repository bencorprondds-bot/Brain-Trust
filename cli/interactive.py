"""
Interactive Mode for Legion CLI

Provides an interactive chat session with Willow.
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

console = Console()


def interactive_session():
    """Run an interactive session with Willow."""
    console.print(Panel(
        "[bold cyan]Legion Interactive Mode[/bold cyan]\n\n"
        "Chat with Willow, the Executive Conductor.\n"
        "Type [bold]quit[/bold] or [bold]exit[/bold] to leave.\n"
        "Type [bold]help[/bold] for available commands.",
        title="Welcome to the Legion",
        border_style="cyan",
    ))

    # Initialize Willow
    try:
        sys.path.insert(0, str(__file__).rsplit('cli', 1)[0])
        from backend.app.agents import get_willow
        willow = get_willow()
    except ImportError as e:
        console.print(f"[red]Could not initialize Willow: {e}[/red]")
        console.print("[yellow]Make sure the backend is in your path.[/yellow]")
        return

    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold green]You[/bold green]")

            if not user_input.strip():
                continue

            # Handle exit commands
            if user_input.lower().strip() in ["quit", "exit", "bye", "q"]:
                console.print("\n[cyan]Goodbye! The Legion awaits your return.[/cyan]")
                break

            # Handle help command
            if user_input.lower().strip() == "help":
                _show_help()
                continue

            # Handle special commands
            if user_input.startswith("/"):
                _handle_slash_command(user_input, willow)
                continue

            # Process through Willow
            console.print()
            with console.status("[cyan]Willow is thinking...[/cyan]"):
                response = willow.process(user_input)

            # Display response
            _display_response(response)

        except KeyboardInterrupt:
            console.print("\n[cyan]Interrupted. Type 'quit' to exit.[/cyan]")
            continue
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            continue


def process_single_intent(intent: str):
    """Process a single intent and display result."""
    try:
        sys.path.insert(0, str(__file__).rsplit('cli', 1)[0])
        from backend.app.agents import get_willow
        willow = get_willow()
    except ImportError as e:
        console.print(f"[red]Could not initialize Willow: {e}[/red]")
        return

    console.print(f"\n[bold]Processing:[/bold] {intent}\n")

    with console.status("[cyan]Willow is thinking...[/cyan]"):
        response = willow.process(intent)

    _display_response(response)

    # If needs approval, prompt
    if response.needs_input and response.plan:
        console.print()
        choice = Prompt.ask(
            "Action",
            choices=["begin", "cancel", "details"],
            default="begin",
        )

        if choice == "begin":
            with console.status("[cyan]Executing plan...[/cyan]"):
                result = willow.approve_and_execute()
            _display_response(result)
        elif choice == "details":
            console.print(Panel(
                response.plan.to_display_string(),
                title="Plan Details",
                border_style="blue",
            ))


def _display_response(response):
    """Display a Willow response with formatting."""
    # Main message
    console.print(Panel(
        Markdown(response.message),
        title="[bold cyan]Willow[/bold cyan]",
        border_style="cyan",
    ))

    # Show plan summary if present
    if response.plan and not response.execution_result:
        console.print(Panel(
            response.plan.to_display_string(),
            title="Proposed Plan",
            border_style="blue",
        ))

    # Show execution result if present
    if response.execution_result:
        status_color = "green" if response.execution_result.success else "red"
        console.print(Panel(
            f"Status: {response.execution_result.status.value}\n"
            f"Duration: {response.execution_result.total_duration_seconds:.1f}s",
            title=f"[{status_color}]Execution Result[/{status_color}]",
            border_style=status_color,
        ))

    # Show options if needs input
    if response.needs_input and response.input_options:
        options = " | ".join([f"[bold]{opt}[/bold]" for opt in response.input_options])
        console.print(f"\nOptions: {options}")


def _show_help():
    """Show help information."""
    help_text = """
## Available Commands

### Direct Commands
- **quit** / **exit** - Leave interactive mode
- **help** - Show this help

### Slash Commands
- **/status** - Show current status
- **/plan** - Show current plan details
- **/approve** - Approve current plan
- **/cancel** - Cancel current plan
- **/capabilities** - List Legion capabilities
- **/gaps** - Show capability gaps

### Intent Examples
- "Write a short story about Maya and Pip"
- "Find the Chapter 3 document"
- "Review the latest draft"
- "What's the status of Life with AI?"
"""
    console.print(Panel(
        Markdown(help_text),
        title="Help",
        border_style="green",
    ))


def _handle_slash_command(command: str, willow):
    """Handle slash commands."""
    cmd = command.lower().strip()

    if cmd == "/status":
        if willow.current_plan:
            console.print(Panel(
                willow.current_plan.to_display_string(),
                title="Current Plan",
                border_style="blue",
            ))
        else:
            console.print("[yellow]No active plan.[/yellow]")

    elif cmd == "/plan":
        if willow.current_plan:
            console.print(Panel(
                willow.current_plan.to_display_string(),
                title="Plan Details",
                border_style="blue",
            ))
        else:
            console.print("[yellow]No plan to show.[/yellow]")

    elif cmd == "/approve":
        if willow.current_plan:
            with console.status("[cyan]Executing plan...[/cyan]"):
                response = willow.approve_and_execute()
            _display_response(response)
        else:
            console.print("[yellow]No plan to approve.[/yellow]")

    elif cmd == "/cancel":
        willow.current_plan = None
        console.print("[green]Plan cancelled.[/green]")

    elif cmd == "/capabilities":
        from backend.app.core.capability_registry import get_capability_registry
        registry = get_capability_registry()
        caps = registry.get_all_capabilities()
        console.print(f"\n[bold]Legion Capabilities ({len(caps)} total):[/bold]")
        for cap in caps[:15]:
            console.print(f"  - {cap.name} ({cap.agent_role})")
        if len(caps) > 15:
            console.print(f"  ... and {len(caps) - 15} more")

    elif cmd == "/gaps":
        from backend.app.core.capability_registry import get_capability_registry
        registry = get_capability_registry()
        gaps = registry.get_open_gaps()
        if gaps:
            console.print(f"\n[bold]Capability Gaps ({len(gaps)}):[/bold]")
            for gap in gaps:
                console.print(f"  - [{gap.priority}] {gap.description}")
        else:
            console.print("[green]No capability gaps![/green]")

    else:
        console.print(f"[yellow]Unknown command: {cmd}[/yellow]")
