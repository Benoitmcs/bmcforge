"""Asset management commands for BMCForge."""

import os
from pathlib import Path
from typing import Optional

import typer

from ..core.database import get_db
from ..core.models import AssetType
from ..utils.display import console, print_success, print_error

app = typer.Typer(help="Manage assets (B-roll, SFX, music, graphics)")


def get_file_info(file_path: Path) -> dict:
    """Extract file metadata."""
    stat = file_path.stat()
    suffix = file_path.suffix.lower().lstrip(".")

    return {
        "name": file_path.name,
        "file_type": suffix,
        "file_size": stat.st_size,
    }


@app.command()
def add(
    path: str = typer.Argument(..., help="File or directory path"),
    asset_type: str = typer.Option(..., "--type", "-t", help="Asset type (broll, sfx, music, graphic, footage)"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Scan directory recursively"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Custom name (file name if not provided)"),
):
    """Register an asset or directory of assets."""
    # Validate asset type
    try:
        atype = AssetType(asset_type)
    except ValueError:
        print_error(f"Invalid asset type: {asset_type}")
        valid = ", ".join(t.value for t in AssetType)
        console.print(f"[dim]Valid types: {valid}[/dim]")
        raise typer.Exit(1)

    target = Path(path).expanduser().resolve()

    if not target.exists():
        print_error(f"Path not found: {target}")
        raise typer.Exit(1)

    files_to_add = []

    if target.is_file():
        files_to_add.append((target, name or target.name))
    elif target.is_dir():
        if recursive:
            for f in target.rglob("*"):
                if f.is_file() and not f.name.startswith("."):
                    files_to_add.append((f, f.name))
        else:
            for f in target.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    files_to_add.append((f, f.name))
    else:
        print_error(f"Invalid path: {target}")
        raise typer.Exit(1)

    if not files_to_add:
        console.print("[dim]No files found to add.[/dim]")
        return

    added = 0
    skipped = 0

    with get_db() as conn:
        for file_path, file_name in files_to_add:
            info = get_file_info(file_path)

            try:
                conn.execute(
                    """
                    INSERT INTO assets (name, file_path, asset_type, file_type, file_size)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (file_name, str(file_path), atype.value, info["file_type"], info["file_size"]),
                )
                added += 1
            except Exception:
                skipped += 1  # Likely duplicate path

    if added:
        print_success(f"Added {added} asset(s)")
    if skipped:
        console.print(f"[dim]Skipped {skipped} (already registered)[/dim]")


@app.command("list")
def list_assets(
    asset_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum items"),
):
    """List registered assets."""
    query = "SELECT a.*, GROUP_CONCAT(t.name) as tags FROM assets a LEFT JOIN asset_tags at ON a.id = at.asset_id LEFT JOIN tags t ON at.tag_id = t.id"
    params = []
    conditions = []

    if asset_type:
        try:
            AssetType(asset_type)
            conditions.append("a.asset_type = ?")
            params.append(asset_type)
        except ValueError:
            print_error(f"Invalid asset type: {asset_type}")
            raise typer.Exit(1)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " GROUP BY a.id ORDER BY a.created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

    if not rows:
        console.print("[dim]No assets found.[/dim]")
        return

    from rich.table import Table

    table = Table(title="Assets")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Name", style="bold")
    table.add_column("Type")
    table.add_column("Tags", style="cyan")
    table.add_column("Size", justify="right", style="dim")

    for row in rows:
        size = format_size(row["file_size"]) if row["file_size"] else "-"
        tags = row["tags"] or ""
        table.add_row(
            str(row["id"]),
            row["name"],
            row["asset_type"],
            tags,
            size,
        )

    console.print(table)


@app.command()
def show(
    asset_id: int = typer.Argument(..., help="Asset ID"),
):
    """Show asset details."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT a.*, GROUP_CONCAT(t.name) as tags
            FROM assets a
            LEFT JOIN asset_tags at ON a.id = at.asset_id
            LEFT JOIN tags t ON at.tag_id = t.id
            WHERE a.id = ?
            GROUP BY a.id
            """,
            (asset_id,),
        )
        row = cursor.fetchone()

    if not row:
        print_error(f"Asset #{asset_id} not found")
        raise typer.Exit(1)

    from rich.panel import Panel

    lines = [
        f"[bold]Name:[/bold] {row['name']}",
        f"[bold]Type:[/bold] {row['asset_type']}",
        f"[bold]Path:[/bold] {row['file_path']}",
        f"[bold]File Type:[/bold] {row['file_type'] or 'unknown'}",
        f"[bold]Size:[/bold] {format_size(row['file_size']) if row['file_size'] else 'unknown'}",
    ]

    if row["tags"]:
        lines.append(f"[bold]Tags:[/bold] {row['tags']}")

    if row["duration"]:
        lines.append(f"[bold]Duration:[/bold] {row['duration']:.1f}s")

    # Check if file exists
    if not Path(row["file_path"]).exists():
        lines.append("[red]Warning: File not found at path[/red]")

    panel = Panel("\n".join(lines), title=f"Asset #{asset_id}", border_style="blue")
    console.print(panel)


@app.command()
def tag(
    asset_id: int = typer.Argument(..., help="Asset ID"),
    tags: list[str] = typer.Argument(..., help="Tags to add"),
):
    """Add tags to an asset."""
    with get_db() as conn:
        # Verify asset exists
        cursor = conn.execute("SELECT id FROM assets WHERE id = ?", (asset_id,))
        if not cursor.fetchone():
            print_error(f"Asset #{asset_id} not found")
            raise typer.Exit(1)

        added = 0
        for tag_name in tags:
            tag_name = tag_name.lower().strip()
            if not tag_name:
                continue

            # Get or create tag
            cursor = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            row = cursor.fetchone()

            if row:
                tag_id = row["id"]
            else:
                cursor = conn.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
                tag_id = cursor.lastrowid

            # Link tag to asset
            try:
                conn.execute(
                    "INSERT INTO asset_tags (asset_id, tag_id) VALUES (?, ?)",
                    (asset_id, tag_id),
                )
                added += 1
            except Exception:
                pass  # Already tagged

    if added:
        print_success(f"Added {added} tag(s) to asset #{asset_id}")
    else:
        console.print("[dim]No new tags added (already applied)[/dim]")


@app.command()
def untag(
    asset_id: int = typer.Argument(..., help="Asset ID"),
    tags: list[str] = typer.Argument(..., help="Tags to remove"),
):
    """Remove tags from an asset."""
    with get_db() as conn:
        removed = 0
        for tag_name in tags:
            tag_name = tag_name.lower().strip()

            cursor = conn.execute(
                """
                DELETE FROM asset_tags
                WHERE asset_id = ? AND tag_id = (SELECT id FROM tags WHERE name = ?)
                """,
                (asset_id, tag_name),
            )
            removed += cursor.rowcount

    if removed:
        print_success(f"Removed {removed} tag(s) from asset #{asset_id}")
    else:
        console.print("[dim]No tags removed[/dim]")


@app.command()
def search(
    query: Optional[str] = typer.Argument(None, help="Search tags (space-separated)"),
    asset_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type"),
    unused: bool = typer.Option(False, "--unused", help="Only show assets not linked to content"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum results"),
):
    """Search assets by tags or type."""
    sql = """
        SELECT a.*, GROUP_CONCAT(DISTINCT t.name) as tags
        FROM assets a
        LEFT JOIN asset_tags at ON a.id = at.asset_id
        LEFT JOIN tags t ON at.tag_id = t.id
    """
    conditions = []
    params = []

    if query:
        # Search for assets with any of the specified tags
        tag_list = [tag.lower().strip() for tag in query.split()]
        placeholders = ",".join("?" * len(tag_list))
        sql = f"""
            SELECT a.*, GROUP_CONCAT(DISTINCT t.name) as tags
            FROM assets a
            JOIN asset_tags at ON a.id = at.asset_id
            JOIN tags t ON at.tag_id = t.id
            WHERE t.name IN ({placeholders})
        """
        params.extend(tag_list)

        if asset_type:
            conditions.append("a.asset_type = ?")
            params.append(asset_type)

        if unused:
            conditions.append("a.id NOT IN (SELECT asset_id FROM content_assets)")

        if conditions:
            sql += " AND " + " AND ".join(conditions)

        sql += " GROUP BY a.id ORDER BY a.created_at DESC LIMIT ?"
    else:
        if asset_type:
            conditions.append("a.asset_type = ?")
            params.append(asset_type)

        if unused:
            conditions.append("a.id NOT IN (SELECT asset_id FROM content_assets)")

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " GROUP BY a.id ORDER BY a.created_at DESC LIMIT ?"

    params.append(limit)

    with get_db() as conn:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()

    if not rows:
        console.print("[dim]No assets found matching criteria.[/dim]")
        return

    from rich.table import Table

    title = "Search Results"
    if query:
        title += f" for '{query}'"

    table = Table(title=title)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Name", style="bold")
    table.add_column("Type")
    table.add_column("Tags", style="cyan")
    table.add_column("Size", justify="right", style="dim")

    for row in rows:
        size = format_size(row["file_size"]) if row["file_size"] else "-"
        tags = row["tags"] or ""
        table.add_row(
            str(row["id"]),
            row["name"],
            row["asset_type"],
            tags,
            size,
        )

    console.print(table)


@app.command()
def link(
    asset_id: int = typer.Argument(..., help="Asset ID"),
    content_id: int = typer.Argument(..., help="Content ID to link to"),
    usage: Optional[str] = typer.Option(None, "--usage", "-u", help="Usage type (broll, intro, sfx, etc.)"),
):
    """Link an asset to content."""
    with get_db() as conn:
        # Verify both exist
        cursor = conn.execute("SELECT id FROM assets WHERE id = ?", (asset_id,))
        if not cursor.fetchone():
            print_error(f"Asset #{asset_id} not found")
            raise typer.Exit(1)

        cursor = conn.execute("SELECT id FROM content WHERE id = ?", (content_id,))
        if not cursor.fetchone():
            print_error(f"Content #{content_id} not found")
            raise typer.Exit(1)

        try:
            conn.execute(
                "INSERT INTO content_assets (content_id, asset_id, usage_type) VALUES (?, ?, ?)",
                (content_id, asset_id, usage),
            )
            print_success(f"Linked asset #{asset_id} to content #{content_id}")
        except Exception:
            print_error("Asset already linked to this content")
            raise typer.Exit(1)


@app.command()
def unlink(
    asset_id: int = typer.Argument(..., help="Asset ID"),
    content_id: int = typer.Argument(..., help="Content ID to unlink from"),
):
    """Unlink an asset from content."""
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM content_assets WHERE asset_id = ? AND content_id = ?",
            (asset_id, content_id),
        )

        if cursor.rowcount:
            print_success(f"Unlinked asset #{asset_id} from content #{content_id}")
        else:
            console.print("[dim]No link found to remove[/dim]")


@app.command()
def delete(
    asset_id: int = typer.Argument(..., help="Asset ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Remove an asset from the registry (does not delete the file)."""
    with get_db() as conn:
        cursor = conn.execute("SELECT name FROM assets WHERE id = ?", (asset_id,))
        row = cursor.fetchone()

        if not row:
            print_error(f"Asset #{asset_id} not found")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Remove '{row['name']}' from registry?")
            if not confirm:
                raise typer.Abort()

        conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))

    print_success(f"Removed asset #{asset_id} from registry")


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"
