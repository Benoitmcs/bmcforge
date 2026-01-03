"""Script management commands for BMCForge."""

import os
import subprocess
import tempfile
from typing import Optional

import typer

from ..core.database import get_db
from ..core.config import get_config_value
from ..utils.display import console, print_success, print_error

MARKDOWN_GUIDE = (
    "[dim]Markdown:[/] "
    "[cyan]# Header[/], [cyan]## Subheader[/], "
    "[cyan]**bold**[/], [cyan]*italic*[/], "
    "[cyan]- list[/], [cyan]1. numbered[/], "
    "[cyan]> quote[/], [cyan]`code`[/]"
)

app = typer.Typer(
    help="Manage scripts for content",
    epilog=MARKDOWN_GUIDE,
    rich_markup_mode="rich",
)


def copy_shot_list(conn, from_script_id: int, to_script_id: int) -> bool:
    """Copy shot list from one script version to another.

    Returns True if a shot list was copied, False if source had no shots.
    """
    # Get the source shot list
    cursor = conn.execute(
        "SELECT id, name FROM shot_lists WHERE script_id = ?",
        (from_script_id,),
    )
    source_list = cursor.fetchone()

    if not source_list:
        return False

    # Create new shot list for the new script
    cursor = conn.execute(
        "INSERT INTO shot_lists (script_id, name) VALUES (?, ?)",
        (to_script_id, source_list["name"]),
    )
    new_list_id = cursor.lastrowid

    # Copy all shots
    cursor = conn.execute(
        """
        SELECT sequence, description, shot_type, duration_estimate, location, notes, completed
        FROM shots
        WHERE shot_list_id = ?
        ORDER BY sequence
        """,
        (source_list["id"],),
    )
    shots = cursor.fetchall()

    for shot in shots:
        conn.execute(
            """
            INSERT INTO shots (shot_list_id, sequence, description, shot_type,
                             duration_estimate, location, notes, completed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (new_list_id, shot["sequence"], shot["description"], shot["shot_type"],
             shot["duration_estimate"], shot["location"], shot["notes"], shot["completed"]),
        )

    return True


def get_editor() -> str:
    """Get the editor to use."""
    # Check config first, then environment
    editor = get_config_value("general.editor")
    if editor:
        return editor
    return os.environ.get("EDITOR", os.environ.get("VISUAL", "nano"))


@app.command()
def create(
    content_id: int = typer.Argument(..., help="Content ID to create script for"),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="Initial script text"),
):
    """Create a new script for content."""
    with get_db() as conn:
        # Verify content exists
        cursor = conn.execute("SELECT id, title FROM content WHERE id = ?", (content_id,))
        content = cursor.fetchone()
        if not content:
            print_error(f"Content #{content_id} not found")
            raise typer.Exit(1)

        # Check if script already exists
        cursor = conn.execute(
            "SELECT id FROM scripts WHERE content_id = ? ORDER BY version DESC LIMIT 1",
            (content_id,),
        )
        existing = cursor.fetchone()

        if existing:
            console.print(f"[dim]Script already exists. Use 'bmc scripts edit {content_id}' to modify.[/dim]")
            raise typer.Exit(1)

        # Create script
        cursor = conn.execute(
            "INSERT INTO scripts (content_id, version, body) VALUES (?, 1, ?)",
            (content_id, body or ""),
        )
        script_id = cursor.lastrowid

        # Update content reference
        conn.execute("UPDATE content SET script_id = ? WHERE id = ?", (script_id, content_id))

    print_success(f"Created script for '{content['title']}'")

    if not body:
        console.print(f"[dim]Edit with: bmc scripts edit {content_id}[/dim]")


@app.command()
def edit(
    content_id: int = typer.Argument(..., help="Content ID"),
):
    """Edit a script in your editor."""
    with get_db() as conn:
        # Get latest script version
        cursor = conn.execute(
            """
            SELECT s.id, s.body, s.version, c.title
            FROM scripts s
            JOIN content c ON s.content_id = c.id
            WHERE s.content_id = ?
            ORDER BY s.version DESC
            LIMIT 1
            """,
            (content_id,),
        )
        row = cursor.fetchone()

        if not row:
            print_error(f"No script found for content #{content_id}")
            console.print(f"[dim]Create one with: bmc scripts create {content_id}[/dim]")
            raise typer.Exit(1)

        script_id = row["id"]
        current_body = row["body"] or ""
        current_version = row["version"]
        title = row["title"]

    # Open in editor
    editor = get_editor()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(current_body)
        temp_path = f.name

    try:
        subprocess.run([editor, temp_path], check=True)

        with open(temp_path, "r") as f:
            new_body = f.read()

        if new_body == current_body:
            console.print("[dim]No changes made.[/dim]")
            return

        # Save as new version
        with get_db() as conn:
            new_version = current_version + 1
            cursor = conn.execute(
                "INSERT INTO scripts (content_id, version, body) VALUES (?, ?, ?)",
                (content_id, new_version, new_body),
            )
            new_script_id = cursor.lastrowid

            # Copy shot list from previous version
            shots_copied = copy_shot_list(conn, script_id, new_script_id)

            # Update content reference to latest
            conn.execute("UPDATE content SET script_id = ? WHERE id = ?", (new_script_id, content_id))

        word_count = len(new_body.split())
        print_success(f"Saved script v{new_version} for '{title}' ({word_count} words)")
        if shots_copied:
            console.print("[dim]Shot list carried over from previous version[/dim]")

    finally:
        os.unlink(temp_path)


@app.command()
def show(
    content_id: int = typer.Argument(..., help="Content ID"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Specific version"),
):
    """Display a script with Markdown rendering."""
    with get_db() as conn:
        if version:
            cursor = conn.execute(
                """
                SELECT s.body, s.version, c.title
                FROM scripts s
                JOIN content c ON s.content_id = c.id
                WHERE s.content_id = ? AND s.version = ?
                """,
                (content_id, version),
            )
        else:
            cursor = conn.execute(
                """
                SELECT s.body, s.version, c.title
                FROM scripts s
                JOIN content c ON s.content_id = c.id
                WHERE s.content_id = ?
                ORDER BY s.version DESC
                LIMIT 1
                """,
                (content_id,),
            )

        row = cursor.fetchone()

    if not row:
        print_error(f"No script found for content #{content_id}")
        raise typer.Exit(1)

    from rich.panel import Panel
    from rich.markdown import Markdown

    body = row["body"] or "[dim]Empty script[/dim]"
    word_count = len(body.split()) if row["body"] else 0

    # Render as markdown
    md = Markdown(body)
    panel = Panel(
        md,
        title=f"{row['title']} - Script v{row['version']} ({word_count} words)",
        border_style="blue",
    )
    console.print(panel)


@app.command()
def history(
    content_id: int = typer.Argument(..., help="Content ID"),
):
    """Show script version history."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT s.version, s.created_at,
                   LENGTH(s.body) - LENGTH(REPLACE(s.body, ' ', '')) + 1 as word_count
            FROM scripts s
            WHERE s.content_id = ?
            ORDER BY s.version DESC
            """,
            (content_id,),
        )
        rows = cursor.fetchall()

        # Get content title
        cursor = conn.execute("SELECT title FROM content WHERE id = ?", (content_id,))
        content = cursor.fetchone()

    if not rows:
        print_error(f"No scripts found for content #{content_id}")
        raise typer.Exit(1)

    from rich.table import Table

    table = Table(title=f"Script History: {content['title']}")
    table.add_column("Version", style="bold")
    table.add_column("Words", justify="right")
    table.add_column("Created", style="dim")

    for row in rows:
        table.add_row(
            f"v{row['version']}",
            str(row["word_count"] or 0),
            row["created_at"][:16] if row["created_at"] else "-",
        )

    console.print(table)
    console.print(f"\n[dim]View specific version: bmc scripts show {content_id} --version N[/dim]")


@app.command()
def delete(
    content_id: int = typer.Argument(..., help="Content ID"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Delete specific version"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete script(s) for content."""
    with get_db() as conn:
        if version:
            # Delete specific version
            cursor = conn.execute(
                "SELECT id FROM scripts WHERE content_id = ? AND version = ?",
                (content_id, version),
            )
            if not cursor.fetchone():
                print_error(f"Script v{version} not found for content #{content_id}")
                raise typer.Exit(1)

            if not force:
                confirm = typer.confirm(f"Delete script v{version}?")
                if not confirm:
                    raise typer.Abort()

            conn.execute(
                "DELETE FROM scripts WHERE content_id = ? AND version = ?",
                (content_id, version),
            )
            print_success(f"Deleted script v{version}")
        else:
            # Delete all versions
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM scripts WHERE content_id = ?",
                (content_id,),
            )
            count = cursor.fetchone()["count"]

            if count == 0:
                print_error(f"No scripts found for content #{content_id}")
                raise typer.Exit(1)

            if not force:
                confirm = typer.confirm(f"Delete all {count} script version(s)?")
                if not confirm:
                    raise typer.Abort()

            conn.execute("DELETE FROM scripts WHERE content_id = ?", (content_id,))
            conn.execute("UPDATE content SET script_id = NULL WHERE id = ?", (content_id,))
            print_success(f"Deleted {count} script version(s)")
