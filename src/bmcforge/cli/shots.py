"""Shot list management commands for BMCForge."""

from typing import Optional

import typer

from ..core.database import get_db
from ..core.models import ShotType
from ..utils.display import console, print_success, print_error

app = typer.Typer(help="Manage shot lists for scripts")


def get_script_for_content(conn, content_id: int, version: Optional[int] = None) -> Optional[dict]:
    """Get script info for a content item.

    If version is None, returns the latest version.
    Returns dict with id, version, content_id, title or None if not found.
    """
    if version:
        cursor = conn.execute(
            """
            SELECT s.id, s.version, s.content_id, c.title
            FROM scripts s
            JOIN content c ON s.content_id = c.id
            WHERE s.content_id = ? AND s.version = ?
            """,
            (content_id, version),
        )
    else:
        cursor = conn.execute(
            """
            SELECT s.id, s.version, s.content_id, c.title
            FROM scripts s
            JOIN content c ON s.content_id = c.id
            WHERE s.content_id = ?
            ORDER BY s.version DESC
            LIMIT 1
            """,
            (content_id,),
        )
    return cursor.fetchone()


def get_script_info(conn, script_id: int) -> Optional[dict]:
    """Get script info including content title."""
    cursor = conn.execute(
        """
        SELECT s.id, s.version, s.content_id, c.title
        FROM scripts s
        JOIN content c ON s.content_id = c.id
        WHERE s.id = ?
        """,
        (script_id,),
    )
    return cursor.fetchone()


@app.command()
def create(
    content_id: int = typer.Argument(..., help="Content ID"),
    name: str = typer.Argument("Shot List", help="Shot list name"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Script version (default: latest)"),
):
    """Create a shot list for a script."""
    with get_db() as conn:
        # Get script for this content/version
        script = get_script_for_content(conn, content_id, version)
        if not script:
            if version:
                print_error(f"Script v{version} not found for content #{content_id}")
            else:
                print_error(f"No script found for content #{content_id}")
                console.print(f"[dim]Create one with: bmc scripts create {content_id}[/dim]")
            raise typer.Exit(1)

        script_id = script["id"]

        # Check if shot list already exists
        cursor = conn.execute(
            "SELECT id FROM shot_lists WHERE script_id = ?",
            (script_id,),
        )
        if cursor.fetchone():
            console.print("[dim]Shot list already exists. Use 'bmc shots add' to add shots.[/dim]")
            raise typer.Exit(1)

        # Create shot list
        conn.execute(
            "INSERT INTO shot_lists (script_id, name) VALUES (?, ?)",
            (script_id, name),
        )

    print_success(f"Created shot list '{name}' for '{script['title']}' v{script['version']}")


@app.command()
def add(
    content_id: int = typer.Argument(..., help="Content ID"),
    description: str = typer.Argument(..., help="Shot description"),
    shot_type: Optional[str] = typer.Option(None, "--type", "-t", help="Shot type (wide, medium, close, broll, talking_head)"),
    duration: Optional[int] = typer.Option(None, "--duration", "-d", help="Estimated duration in seconds"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Filming location"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Script version (default: latest)"),
):
    """Add a shot to a script's shot list."""
    # Validate shot type if provided
    if shot_type:
        try:
            ShotType(shot_type)
        except ValueError:
            print_error(f"Invalid shot type: {shot_type}")
            valid = ", ".join(t.value for t in ShotType)
            console.print(f"[dim]Valid types: {valid}[/dim]")
            raise typer.Exit(1)

    with get_db() as conn:
        # Get script for this content/version
        script = get_script_for_content(conn, content_id, version)
        if not script:
            if version:
                print_error(f"Script v{version} not found for content #{content_id}")
            else:
                print_error(f"No script found for content #{content_id}")
                console.print(f"[dim]Create one with: bmc scripts create {content_id}[/dim]")
            raise typer.Exit(1)

        script_id = script["id"]

        # Get shot list for this script
        cursor = conn.execute(
            "SELECT id FROM shot_lists WHERE script_id = ?",
            (script_id,),
        )
        shot_list = cursor.fetchone()

        if not shot_list:
            # Auto-create shot list
            cursor = conn.execute(
                "INSERT INTO shot_lists (script_id, name) VALUES (?, ?)",
                (script_id, "Shot List"),
            )
            shot_list_id = cursor.lastrowid
            console.print(f"[dim]Created shot list for '{script['title']}' v{script['version']}[/dim]")
        else:
            shot_list_id = shot_list["id"]

        # Get next sequence number
        cursor = conn.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 as next_seq FROM shots WHERE shot_list_id = ?",
            (shot_list_id,),
        )
        next_seq = cursor.fetchone()["next_seq"]

        # Insert shot
        conn.execute(
            """
            INSERT INTO shots (shot_list_id, sequence, description, shot_type, duration_estimate, location)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (shot_list_id, next_seq, description, shot_type, duration, location),
        )

    print_success(f"Added shot #{next_seq}: {description[:40]}...")


@app.command("list")
def list_shots(
    content_id: int = typer.Argument(..., help="Content ID"),
    show_completed: bool = typer.Option(True, "--completed/--pending", help="Show completed shots"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Script version (default: latest)"),
):
    """List shots for a script version."""
    with get_db() as conn:
        # Get script for this content/version
        script = get_script_for_content(conn, content_id, version)
        if not script:
            if version:
                print_error(f"Script v{version} not found for content #{content_id}")
            else:
                print_error(f"No script found for content #{content_id}")
                console.print(f"[dim]Create one with: bmc scripts create {content_id}[/dim]")
            raise typer.Exit(1)

        script_id = script["id"]

        # Get shot list info
        cursor = conn.execute(
            """
            SELECT sl.id, sl.name, s.version, c.title
            FROM shot_lists sl
            JOIN scripts s ON sl.script_id = s.id
            JOIN content c ON s.content_id = c.id
            WHERE sl.script_id = ?
            """,
            (script_id,),
        )
        shot_list = cursor.fetchone()

        if not shot_list:
            print_error(f"No shot list for '{script['title']}' v{script['version']}")
            console.print(f"[dim]Create one with: bmc shots add {content_id} \"First shot\"[/dim]")
            raise typer.Exit(1)

        query = "SELECT * FROM shots WHERE shot_list_id = ?"
        params = [shot_list["id"]]

        if not show_completed:
            query += " AND completed = FALSE"

        query += " ORDER BY sequence"

        cursor = conn.execute(query, params)
        shots = cursor.fetchall()

        # Get available versions for hint
        cursor = conn.execute(
            """
            SELECT s.version FROM scripts s
            JOIN shot_lists sl ON sl.script_id = s.id
            WHERE s.content_id = ?
            ORDER BY s.version DESC
            """,
            (content_id,),
        )
        available_versions = [row["version"] for row in cursor.fetchall()]

    if not shots:
        console.print("[dim]No shots in list.[/dim]")
        if len(available_versions) > 1:
            versions_str = ", ".join(f"v{v}" for v in available_versions)
            console.print(f"[dim]Available versions: {versions_str}[/dim]")
        return

    _print_shot_table(shots, f"{shot_list['title']} v{shot_list['version']} - {shot_list['name']}")

    # Show hint about other versions if available
    if len(available_versions) > 1:
        other_versions = [v for v in available_versions if v != shot_list["version"]]
        if other_versions:
            console.print(f"[dim]Other versions with shots: {', '.join(f'v{v}' for v in other_versions)}[/dim]")


@app.command("all")
def list_all_shots(
    pending_only: bool = typer.Option(False, "--pending", "-p", help="Only show pending shots"),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum shots to show"),
):
    """List all shots across all scripts."""
    with get_db() as conn:
        query = """
            SELECT sh.*, sl.name as list_name, s.id as script_id, s.version, c.title
            FROM shots sh
            JOIN shot_lists sl ON sh.shot_list_id = sl.id
            JOIN scripts s ON sl.script_id = s.id
            JOIN content c ON s.content_id = c.id
        """

        if pending_only:
            query += " WHERE sh.completed = FALSE"

        query += " ORDER BY c.title, s.version, sh.sequence LIMIT ?"

        cursor = conn.execute(query, (limit,))
        shots = cursor.fetchall()

    if not shots:
        console.print("[dim]No shots found.[/dim]")
        return

    from rich.table import Table

    table = Table(title="All Shots")
    table.add_column("#", style="dim", width=3)
    table.add_column("Content", width=20)
    table.add_column("Script", width=6)
    table.add_column("Description")
    table.add_column("Type", style="cyan", width=12)
    table.add_column("Done", justify="center", width=4)

    for shot in shots:
        done = "[green]✓[/green]" if shot["completed"] else "[dim]○[/dim]"
        style = "dim" if shot["completed"] else None

        table.add_row(
            str(shot["sequence"]),
            shot["title"][:20],
            f"v{shot['version']}",
            shot["description"][:35] + ("..." if len(shot["description"]) > 35 else ""),
            shot["shot_type"] or "-",
            done,
            style=style,
        )

    console.print(table)

    # Summary
    total = len(shots)
    completed = sum(1 for s in shots if s["completed"])
    console.print(f"\n[dim]Showing {total} shots | {completed} completed, {total - completed} pending[/dim]")


@app.command()
def check(
    content_id: int = typer.Argument(..., help="Content ID"),
    shot_num: int = typer.Argument(..., help="Shot sequence number"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Script version (default: latest)"),
):
    """Mark a shot as completed."""
    with get_db() as conn:
        script = get_script_for_content(conn, content_id, version)
        if not script:
            if version:
                print_error(f"Script v{version} not found for content #{content_id}")
            else:
                print_error(f"No script found for content #{content_id}")
            raise typer.Exit(1)

        cursor = conn.execute(
            """
            UPDATE shots
            SET completed = TRUE
            WHERE shot_list_id = (SELECT id FROM shot_lists WHERE script_id = ?)
              AND sequence = ?
            """,
            (script["id"], shot_num),
        )

        if cursor.rowcount == 0:
            print_error(f"Shot #{shot_num} not found for '{script['title']}' v{script['version']}")
            raise typer.Exit(1)

    print_success(f"Shot #{shot_num} marked complete")


@app.command()
def uncheck(
    content_id: int = typer.Argument(..., help="Content ID"),
    shot_num: int = typer.Argument(..., help="Shot sequence number"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Script version (default: latest)"),
):
    """Mark a shot as not completed."""
    with get_db() as conn:
        script = get_script_for_content(conn, content_id, version)
        if not script:
            if version:
                print_error(f"Script v{version} not found for content #{content_id}")
            else:
                print_error(f"No script found for content #{content_id}")
            raise typer.Exit(1)

        cursor = conn.execute(
            """
            UPDATE shots
            SET completed = FALSE
            WHERE shot_list_id = (SELECT id FROM shot_lists WHERE script_id = ?)
              AND sequence = ?
            """,
            (script["id"], shot_num),
        )

        if cursor.rowcount == 0:
            print_error(f"Shot #{shot_num} not found for '{script['title']}' v{script['version']}")
            raise typer.Exit(1)

    print_success(f"Shot #{shot_num} marked incomplete")


@app.command()
def reorder(
    content_id: int = typer.Argument(..., help="Content ID"),
    shot_num: int = typer.Argument(..., help="Shot to move"),
    new_position: int = typer.Argument(..., help="New position"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Script version (default: latest)"),
):
    """Move a shot to a new position."""
    with get_db() as conn:
        script = get_script_for_content(conn, content_id, version)
        if not script:
            if version:
                print_error(f"Script v{version} not found for content #{content_id}")
            else:
                print_error(f"No script found for content #{content_id}")
            raise typer.Exit(1)

        # Get shot list ID
        cursor = conn.execute(
            "SELECT id FROM shot_lists WHERE script_id = ?",
            (script["id"],),
        )
        shot_list = cursor.fetchone()
        if not shot_list:
            print_error(f"No shot list for '{script['title']}' v{script['version']}")
            raise typer.Exit(1)

        shot_list_id = shot_list["id"]

        # Get the shot to move
        cursor = conn.execute(
            "SELECT id FROM shots WHERE shot_list_id = ? AND sequence = ?",
            (shot_list_id, shot_num),
        )
        shot = cursor.fetchone()
        if not shot:
            print_error(f"Shot #{shot_num} not found")
            raise typer.Exit(1)

        shot_id = shot["id"]

        if shot_num == new_position:
            console.print("[dim]No change needed.[/dim]")
            return

        # Reorder
        if new_position < shot_num:
            conn.execute(
                """
                UPDATE shots
                SET sequence = sequence + 1
                WHERE shot_list_id = ? AND sequence >= ? AND sequence < ?
                """,
                (shot_list_id, new_position, shot_num),
            )
        else:
            conn.execute(
                """
                UPDATE shots
                SET sequence = sequence - 1
                WHERE shot_list_id = ? AND sequence > ? AND sequence <= ?
                """,
                (shot_list_id, shot_num, new_position),
            )

        conn.execute(
            "UPDATE shots SET sequence = ? WHERE id = ?",
            (new_position, shot_id),
        )

    print_success(f"Moved shot #{shot_num} to position {new_position}")


@app.command()
def edit(
    content_id: int = typer.Argument(..., help="Content ID"),
    shot_num: int = typer.Argument(..., help="Shot sequence number"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="New description"),
    shot_type: Optional[str] = typer.Option(None, "--type", "-t", help="New shot type"),
    duration: Optional[int] = typer.Option(None, "--duration", help="New duration"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="New location"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Script version (default: latest)"),
):
    """Edit a shot's details."""
    updates = []
    params = []

    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if shot_type is not None:
        try:
            ShotType(shot_type)
        except ValueError:
            print_error(f"Invalid shot type: {shot_type}")
            raise typer.Exit(1)
        updates.append("shot_type = ?")
        params.append(shot_type)
    if duration is not None:
        updates.append("duration_estimate = ?")
        params.append(duration)
    if location is not None:
        updates.append("location = ?")
        params.append(location)

    if not updates:
        print_error("No updates specified")
        raise typer.Exit(1)

    with get_db() as conn:
        script = get_script_for_content(conn, content_id, version)
        if not script:
            if version:
                print_error(f"Script v{version} not found for content #{content_id}")
            else:
                print_error(f"No script found for content #{content_id}")
            raise typer.Exit(1)

        query = f"""
            UPDATE shots
            SET {', '.join(updates)}
            WHERE shot_list_id = (SELECT id FROM shot_lists WHERE script_id = ?)
              AND sequence = ?
        """
        params.extend([script["id"], shot_num])

        cursor = conn.execute(query, params)

        if cursor.rowcount == 0:
            print_error(f"Shot #{shot_num} not found for '{script['title']}' v{script['version']}")
            raise typer.Exit(1)

    print_success(f"Updated shot #{shot_num}")


@app.command()
def remove(
    content_id: int = typer.Argument(..., help="Content ID"),
    shot_num: int = typer.Argument(..., help="Shot sequence number"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Script version (default: latest)"),
):
    """Remove a shot from the list."""
    with get_db() as conn:
        script = get_script_for_content(conn, content_id, version)
        if not script:
            if version:
                print_error(f"Script v{version} not found for content #{content_id}")
            else:
                print_error(f"No script found for content #{content_id}")
            raise typer.Exit(1)

        # Get shot list ID
        cursor = conn.execute(
            "SELECT id FROM shot_lists WHERE script_id = ?",
            (script["id"],),
        )
        shot_list = cursor.fetchone()
        if not shot_list:
            print_error(f"No shot list for '{script['title']}' v{script['version']}")
            raise typer.Exit(1)

        shot_list_id = shot_list["id"]

        # Get shot description for confirmation
        cursor = conn.execute(
            "SELECT description FROM shots WHERE shot_list_id = ? AND sequence = ?",
            (shot_list_id, shot_num),
        )
        shot = cursor.fetchone()
        if not shot:
            print_error(f"Shot #{shot_num} not found")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Remove shot #{shot_num}: '{shot['description'][:40]}...'?")
            if not confirm:
                raise typer.Abort()

        # Delete shot
        conn.execute(
            "DELETE FROM shots WHERE shot_list_id = ? AND sequence = ?",
            (shot_list_id, shot_num),
        )

        # Resequence remaining shots
        conn.execute(
            """
            UPDATE shots
            SET sequence = sequence - 1
            WHERE shot_list_id = ? AND sequence > ?
            """,
            (shot_list_id, shot_num),
        )

    print_success(f"Removed shot #{shot_num}")


def _print_shot_table(shots, title: str) -> None:
    """Print a table of shots."""
    from rich.table import Table

    table = Table(title=title)
    table.add_column("#", style="dim", width=3)
    table.add_column("Description")
    table.add_column("Type", style="cyan", width=12)
    table.add_column("Duration", justify="right", width=8)
    table.add_column("Done", justify="center", width=4)

    total_duration = 0
    completed = 0

    for shot in shots:
        duration_str = f"{shot['duration_estimate']}s" if shot["duration_estimate"] else "-"
        if shot["duration_estimate"]:
            total_duration += shot["duration_estimate"]

        done = "[green]✓[/green]" if shot["completed"] else "[dim]○[/dim]"
        if shot["completed"]:
            completed += 1

        style = "dim" if shot["completed"] else None

        table.add_row(
            str(shot["sequence"]),
            shot["description"],
            shot["shot_type"] or "-",
            duration_str,
            done,
            style=style,
        )

    console.print(table)
    console.print(f"\n[dim]Progress: {completed}/{len(shots)} shots | Est. duration: {total_duration}s[/dim]")
