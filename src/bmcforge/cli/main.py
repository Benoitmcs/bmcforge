"""Main CLI application for BMCForge."""

import typer

from ..core.database import get_db
from ..services.llm import load_prompts
from ..utils.display import console, print_status_summary, print_banner

from . import content as content_cmd
from . import config as config_cmd
from . import assets as assets_cmd
from . import scripts as scripts_cmd
from . import shots as shots_cmd
from . import panic as panic_cmd
from . import publish as publish_cmd

app = typer.Typer(
    name="bmc",
    help="BMCForge: Video content management for creators",
)


@app.callback(invoke_without_command=True)
def init(ctx: typer.Context):
    """Initialize app resources on startup."""
    # Ensure prompts.toml exists with defaults
    load_prompts()

    # Show banner and help when no command is provided
    if ctx.invoked_subcommand is None:
        print_banner()
        console.print(ctx.get_help())

# Register subcommand groups
app.add_typer(content_cmd.app, name="content", help="Manage content items")
app.add_typer(assets_cmd.app, name="assets", help="Manage assets")
app.add_typer(scripts_cmd.app, name="scripts", help="Manage scripts")
app.add_typer(shots_cmd.app, name="shots", help="Manage shot lists")
app.add_typer(config_cmd.app, name="config", help="Manage configuration")
app.add_typer(panic_cmd.app, name="panic", help="Quick video idea generation")
app.add_typer(publish_cmd.app, name="publish", help="Publish content to platforms")


@app.command()
def status():
    """Show overview of content pipeline."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT status, COUNT(*) as count
            FROM content
            GROUP BY status
            """
        )
        rows = cursor.fetchall()

    status_counts = {row["status"]: row["count"] for row in rows}

    if not status_counts:
        console.print("[dim]No content yet. Add some with:[/dim] bmc content add \"My Video\"")
        return

    print_status_summary(status_counts)


@app.command()
def version():
    """Show BMCForge version."""
    console.print("BMCForge v0.1.0")


if __name__ == "__main__":
    app()
