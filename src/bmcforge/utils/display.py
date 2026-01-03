"""Display utilities using Rich."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ..core.models import Content, ContentStatus

console = Console()

BMC_FORGE_BANNER = r"""
 /$$$$$$$  /$$      /$$  /$$$$$$        /$$$$$$$$ /$$$$$$  /$$$$$$$   /$$$$$$  /$$$$$$$$
| $$__  $$| $$$    /$$$ /$$__  $$      | $$_____//$$__  $$| $$__  $$ /$$__  $$| $$_____/
| $$  \ $$| $$$$  /$$$$| $$  \__/      | $$     | $$  \ $$| $$  \ $$| $$  \__/| $$
| $$$$$$$ | $$ $$/$$ $$| $$            | $$$$$  | $$  | $$| $$$$$$$/| $$ /$$$$| $$$$$
| $$__  $$| $$  $$$| $$| $$            | $$__/  | $$  | $$| $$__  $$| $$|_  $$| $$__/
| $$  \ $$| $$\  $ | $$| $$    $$      | $$     | $$  | $$| $$  \ $$| $$  \ $$| $$
| $$$$$$$/| $$ \/  | $$|  $$$$$$/      | $$     |  $$$$$$/| $$  | $$|  $$$$$$/| $$$$$$$$
|_______/ |__/     |__/ \______/       |__/      \______/ |__/  |__/ \______/ |________/
"""


def print_banner() -> None:
    """Print the BMC Forge ASCII art banner."""
    console.print(f"[bold cyan]{BMC_FORGE_BANNER}[/bold cyan]")

STATUS_COLORS = {
    ContentStatus.IDEA: "blue",
    ContentStatus.SCRIPTED: "cyan",
    ContentStatus.FILMING: "yellow",
    ContentStatus.EDITING: "magenta",
    ContentStatus.SCHEDULED: "green",
    ContentStatus.PUBLISHED: "bold green",
}


def get_status_style(status: ContentStatus) -> str:
    """Get the color style for a status."""
    return STATUS_COLORS.get(status, "white")


def print_content_table(contents: list[Content], title: str = "Content") -> None:
    """Print a table of content items."""
    table = Table(title=title)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Title", style="bold")
    table.add_column("Status")
    table.add_column("Type", style="dim")
    table.add_column("Platform", style="dim")
    table.add_column("Scheduled", style="dim")

    for content in contents:
        status_text = Text(content.status.value, style=get_status_style(content.status))
        scheduled = content.scheduled_date.isoformat() if content.scheduled_date else "-"

        table.add_row(
            str(content.id),
            content.title,
            status_text,
            content.content_type.value,
            content.platform or "-",
            scheduled,
        )

    console.print(table)


def print_content_detail(content: Content) -> None:
    """Print detailed view of a single content item."""
    status_text = Text(content.status.value, style=get_status_style(content.status))

    lines = [
        f"[bold]Title:[/bold] {content.title}",
        f"[bold]Status:[/bold] {status_text}",
        f"[bold]Type:[/bold] {content.content_type.value}",
        f"[bold]Platform:[/bold] {content.platform or 'Not set'}",
    ]

    if content.description:
        lines.append(f"[bold]Description:[/bold] {content.description}")

    if content.scheduled_date:
        lines.append(f"[bold]Scheduled:[/bold] {content.scheduled_date.isoformat()}")

    if content.publish_date:
        lines.append(f"[bold]Published:[/bold] {content.publish_date.isoformat()}")

    if content.created_at:
        lines.append(f"[dim]Created:[/dim] {content.created_at.strftime('%Y-%m-%d %H:%M')}")

    panel = Panel("\n".join(lines), title=f"Content #{content.id}", border_style="blue")
    console.print(panel)


def print_status_summary(status_counts: dict[str, int]) -> None:
    """Print a summary of content by status."""
    table = Table(title="Content Pipeline")
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right")

    # Order by pipeline stage
    order = ["idea", "scripted", "filming", "editing", "scheduled", "published"]

    for status in order:
        count = status_counts.get(status, 0)
        if count > 0 or status in ["idea", "scripted", "filming", "editing"]:
            table.add_row(status.capitalize(), str(count))

    console.print(table)


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]{message}[/green]")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red]Error:[/red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]Warning:[/yellow] {message}")
