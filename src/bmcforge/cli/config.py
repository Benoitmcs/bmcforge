"""Configuration commands for BMCForge."""

from typing import Optional

import typer
from rich.table import Table

from ..core.config import (
    load_config,
    get_config_value,
    set_config_value,
    ensure_app_dir,
    CONFIG_PATH,
)
from ..core.database import init_db
from ..utils.display import console, print_success

app = typer.Typer(help="Manage configuration")


@app.command()
def init():
    """Initialize BMCForge (create directories and default config)."""
    ensure_app_dir()
    load_config()  # Creates default config if not exists
    init_db()  # Initialize database

    print_success(f"BMCForge initialized at {CONFIG_PATH.parent}")
    console.print("\nNext steps:")
    console.print("  bmc config set api.openrouter_key YOUR_KEY")
    console.print("  bmc content add \"My First Video\"")


@app.command()
def show():
    """Display current configuration."""
    config = load_config()

    def print_section(name: str, section: dict, prefix: str = ""):
        table = Table(title=name, show_header=True)
        table.add_column("Key", style="cyan")
        table.add_column("Value")

        for key, value in section.items():
            if isinstance(value, dict):
                continue  # Skip nested dicts, handle separately
            display_value = str(value) if value else "[dim]not set[/dim]"
            if "key" in key.lower() and value:
                display_value = value[:8] + "..." if len(str(value)) > 8 else value
            table.add_row(f"{prefix}{key}", display_value)

        console.print(table)
        console.print()

    for section_name, section_data in config.items():
        if isinstance(section_data, dict):
            print_section(section_name.capitalize(), section_data, f"{section_name}.")


@app.command("set")
def set_value(
    key: str = typer.Argument(..., help="Config key (e.g., api.openrouter_key)"),
    value: str = typer.Argument(..., help="Value to set"),
):
    """Set a configuration value."""
    # Convert string values to appropriate types
    if value.lower() == "true":
        typed_value = True
    elif value.lower() == "false":
        typed_value = False
    elif value.isdigit():
        typed_value = int(value)
    else:
        typed_value = value

    set_config_value(key, typed_value)
    print_success(f"Set {key} = {value}")


@app.command("get")
def get_value(
    key: str = typer.Argument(..., help="Config key (e.g., api.openrouter_key)"),
):
    """Get a configuration value."""
    value = get_config_value(key)

    if value is None:
        console.print(f"[dim]{key} is not set[/dim]")
    else:
        # Mask sensitive values
        if "key" in key.lower() and value:
            display = value[:8] + "..." if len(str(value)) > 8 else value
        else:
            display = value
        console.print(f"{key} = {display}")


@app.command()
def path():
    """Show config file path."""
    console.print(str(CONFIG_PATH))
