"""
Config Command - Configuration management.
"""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
import json

app = typer.Typer(help="Manage configuration")
console = Console()

CONFIG_PATH = Path.home() / ".pai" / "legion_config.json"


def load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    """Save configuration to file."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


@app.callback(invoke_without_command=True)
def config_main(ctx: typer.Context):
    """Show current configuration."""
    if ctx.invoked_subcommand is not None:
        return

    config = load_config()

    if config:
        table = Table(title="Legion Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value")

        def flatten(d, prefix=""):
            for key, value in d.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    flatten(value, full_key)
                else:
                    table.add_row(full_key, str(value))

        flatten(config)
        console.print(table)
    else:
        console.print("[yellow]No configuration set.[/yellow]")
        console.print("Use 'legion config set <key> <value>' to configure.")


@app.command(name="set")
def set_config(
    key: str = typer.Argument(..., help="Configuration key (e.g., discord.channel)"),
    value: str = typer.Argument(..., help="Configuration value"),
):
    """Set a configuration value."""
    config = load_config()

    # Handle nested keys
    keys = key.split(".")
    current = config

    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    current[keys[-1]] = value
    save_config(config)

    console.print(f"[green]Set {key} = {value}[/green]")


@app.command(name="get")
def get_config(key: str = typer.Argument(..., help="Configuration key")):
    """Get a configuration value."""
    config = load_config()

    keys = key.split(".")
    current = config

    try:
        for k in keys:
            current = current[k]
        console.print(f"{key} = {current}")
    except (KeyError, TypeError):
        console.print(f"[yellow]Key not found: {key}[/yellow]")


@app.command(name="delete")
def delete_config(key: str = typer.Argument(..., help="Configuration key to delete")):
    """Delete a configuration value."""
    config = load_config()

    keys = key.split(".")
    current = config

    try:
        for k in keys[:-1]:
            current = current[k]
        del current[keys[-1]]
        save_config(config)
        console.print(f"[green]Deleted {key}[/green]")
    except (KeyError, TypeError):
        console.print(f"[yellow]Key not found: {key}[/yellow]")


@app.command(name="path")
def show_path():
    """Show configuration file path."""
    console.print(f"Config file: {CONFIG_PATH}")
    if CONFIG_PATH.exists():
        console.print("[green]File exists[/green]")
    else:
        console.print("[yellow]File does not exist yet[/yellow]")
