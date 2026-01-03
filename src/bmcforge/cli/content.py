"""Content management commands for BMCForge."""

from datetime import date, timedelta
from typing import Optional

import typer

from ..core.database import get_db
from ..core.models import Content, ContentStatus, ContentType
from ..utils.display import (
    console,
    print_content_table,
    print_content_detail,
    print_success,
    print_error,
)

app = typer.Typer(help="Manage content items")


@app.command()
def add(
    title: str = typer.Argument(..., help="Content title"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Description"),
    content_type: str = typer.Option("video", "--type", "-t", help="Content type (video, short, post, reel)"),
    platform: Optional[str] = typer.Option(None, "--platform", "-p", help="Target platform"),
    scheduled: Optional[str] = typer.Option(None, "--schedule", "-s", help="Scheduled date (YYYY-MM-DD)"),
):
    """Add a new content item."""
    # Validate content type
    try:
        ct = ContentType(content_type)
    except ValueError:
        print_error(f"Invalid content type: {content_type}")
        raise typer.Exit(1)

    # Parse scheduled date
    sched_date = None
    if scheduled:
        try:
            sched_date = date.fromisoformat(scheduled)
        except ValueError:
            print_error(f"Invalid date format: {scheduled} (use YYYY-MM-DD)")
            raise typer.Exit(1)

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO content (title, description, content_type, platform, scheduled_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, description, ct.value, platform, sched_date),
        )
        content_id = cursor.lastrowid

    print_success(f"Created content #{content_id}: {title}")


@app.command("list")
def list_content(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    upcoming: bool = typer.Option(False, "--upcoming", "-u", help="Show scheduled in next 7 days"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum items to show"),
):
    """List content items."""
    query = "SELECT * FROM content"
    params = []
    conditions = []

    if status:
        try:
            ContentStatus(status)
            conditions.append("status = ?")
            params.append(status)
        except ValueError:
            print_error(f"Invalid status: {status}")
            valid = ", ".join(s.value for s in ContentStatus)
            console.print(f"[dim]Valid statuses: {valid}[/dim]")
            raise typer.Exit(1)

    if upcoming:
        today = date.today()
        next_week = today + timedelta(days=7)
        conditions.append("scheduled_date BETWEEN ? AND ?")
        params.extend([today.isoformat(), next_week.isoformat()])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

    if not rows:
        console.print("[dim]No content found.[/dim]")
        return

    contents = [Content.from_row(row) for row in rows]
    title = "Content"
    if status:
        title = f"Content ({status})"
    elif upcoming:
        title = "Upcoming Content (7 days)"

    print_content_table(contents, title=title)


@app.command()
def show(
    content_id: int = typer.Argument(..., help="Content ID"),
):
    """Show details of a content item."""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM content WHERE id = ?", (content_id,))
        row = cursor.fetchone()

    if not row:
        print_error(f"Content #{content_id} not found")
        raise typer.Exit(1)

    content = Content.from_row(row)
    print_content_detail(content)


@app.command("status")
def update_status(
    content_id: int = typer.Argument(..., help="Content ID"),
    new_status: str = typer.Argument(..., help="New status"),
):
    """Update content status."""
    try:
        status = ContentStatus(new_status)
    except ValueError:
        print_error(f"Invalid status: {new_status}")
        valid = ", ".join(s.value for s in ContentStatus)
        console.print(f"[dim]Valid statuses: {valid}[/dim]")
        raise typer.Exit(1)

    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE content SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status.value, content_id),
        )

        if cursor.rowcount == 0:
            print_error(f"Content #{content_id} not found")
            raise typer.Exit(1)

    print_success(f"Content #{content_id} status updated to {status.value}")


@app.command()
def schedule(
    content_id: int = typer.Argument(..., help="Content ID"),
    scheduled_date: str = typer.Argument(..., help="Scheduled date (YYYY-MM-DD)"),
):
    """Schedule content for a date."""
    try:
        sched_date = date.fromisoformat(scheduled_date)
    except ValueError:
        print_error(f"Invalid date format: {scheduled_date} (use YYYY-MM-DD)")
        raise typer.Exit(1)

    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE content
            SET scheduled_date = ?, status = 'scheduled', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (sched_date.isoformat(), content_id),
        )

        if cursor.rowcount == 0:
            print_error(f"Content #{content_id} not found")
            raise typer.Exit(1)

    print_success(f"Content #{content_id} scheduled for {sched_date}")


@app.command()
def delete(
    content_id: int = typer.Argument(..., help="Content ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a content item."""
    with get_db() as conn:
        # Check if exists
        cursor = conn.execute("SELECT title FROM content WHERE id = ?", (content_id,))
        row = cursor.fetchone()

        if not row:
            print_error(f"Content #{content_id} not found")
            raise typer.Exit(1)

        title = row["title"]

        if not force:
            confirm = typer.confirm(f"Delete '{title}'?")
            if not confirm:
                raise typer.Abort()

        # Delete related records in correct order (respecting foreign key dependencies)
        # 1. Delete shots for shot_lists linked to scripts of this content
        conn.execute("""
            DELETE FROM shots WHERE shot_list_id IN (
                SELECT sl.id FROM shot_lists sl
                JOIN scripts s ON sl.script_id = s.id
                WHERE s.content_id = ?
            )
        """, (content_id,))
        # 2. Delete shot_lists linked to scripts of this content
        conn.execute("""
            DELETE FROM shot_lists WHERE script_id IN (
                SELECT id FROM scripts WHERE content_id = ?
            )
        """, (content_id,))
        # 3. Break circular reference: content.script_id -> scripts
        conn.execute("UPDATE content SET script_id = NULL WHERE id = ?", (content_id,))
        # 4. Delete scripts for this content
        conn.execute("DELETE FROM scripts WHERE content_id = ?", (content_id,))
        # 5. Delete publications
        conn.execute("DELETE FROM publications WHERE content_id = ?", (content_id,))
        # 6. Unlink ideas (preserve the idea, just remove reference)
        conn.execute("UPDATE ideas SET converted_to_content_id = NULL WHERE converted_to_content_id = ?", (content_id,))
        # 7. Delete the content
        conn.execute("DELETE FROM content WHERE id = ?", (content_id,))

    print_success(f"Deleted content #{content_id}: {title}")


@app.command()
def edit(
    content_id: int = typer.Argument(..., help="Content ID"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="New title"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="New description"),
    platform: Optional[str] = typer.Option(None, "--platform", "-p", help="New platform"),
):
    """Edit a content item."""
    updates = []
    params = []

    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if platform is not None:
        updates.append("platform = ?")
        params.append(platform)

    if not updates:
        print_error("No updates specified")
        raise typer.Exit(1)

    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(content_id)

    with get_db() as conn:
        query = f"UPDATE content SET {', '.join(updates)} WHERE id = ?"
        cursor = conn.execute(query, params)

        if cursor.rowcount == 0:
            print_error(f"Content #{content_id} not found")
            raise typer.Exit(1)

    print_success(f"Updated content #{content_id}")


@app.command()
def calendar(
    week: bool = typer.Option(False, "--week", "-w", help="Show week view instead of month"),
    month: Optional[str] = typer.Option(None, "--month", "-m", help="Month to show (YYYY-MM)"),
):
    """Show calendar view of scheduled content."""
    import calendar as cal
    from datetime import datetime

    # Determine the target month
    if month:
        try:
            year, mon = map(int, month.split("-"))
        except ValueError:
            print_error("Invalid month format. Use YYYY-MM")
            raise typer.Exit(1)
    else:
        today = date.today()
        year, mon = today.year, today.month

    if week:
        # Week view: show current/next 7 days
        start_date = date.today()
        end_date = start_date + timedelta(days=6)
    else:
        # Month view
        _, last_day = cal.monthrange(year, mon)
        start_date = date(year, mon, 1)
        end_date = date(year, mon, last_day)

    # Fetch scheduled content in range
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT id, title, status, scheduled_date, platform
            FROM content
            WHERE scheduled_date BETWEEN ? AND ?
            ORDER BY scheduled_date
            """,
            (start_date.isoformat(), end_date.isoformat()),
        )
        rows = cursor.fetchall()

    # Group by date
    content_by_date: dict[str, list] = {}
    for row in rows:
        d = row["scheduled_date"]
        if d not in content_by_date:
            content_by_date[d] = []
        content_by_date[d].append(row)

    from rich.table import Table
    from rich.text import Text

    if week:
        # Week view: vertical list
        table = Table(title=f"Week of {start_date.strftime('%b %d, %Y')}")
        table.add_column("Date", style="cyan", width=12)
        table.add_column("Content")
        table.add_column("Status", width=10)

        current = start_date
        while current <= end_date:
            date_str = current.isoformat()
            day_label = current.strftime("%a %b %d")

            if current == date.today():
                day_label = f"[bold]{day_label}[/bold]"

            items = content_by_date.get(date_str, [])
            if items:
                for i, item in enumerate(items):
                    table.add_row(
                        day_label if i == 0 else "",
                        f"#{item['id']} {item['title'][:30]}",
                        item["status"],
                    )
            else:
                table.add_row(day_label, "[dim]-[/dim]", "")

            current += timedelta(days=1)
    else:
        # Month view: calendar grid
        table = Table(title=f"{cal.month_name[mon]} {year}", show_header=True)
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            table.add_column(day, justify="center", width=10)

        # Build calendar weeks
        month_cal = cal.monthcalendar(year, mon)

        for week_days in month_cal:
            row = []
            for day_num in week_days:
                if day_num == 0:
                    row.append("")
                else:
                    d = date(year, mon, day_num)
                    date_str = d.isoformat()
                    items = content_by_date.get(date_str, [])

                    cell = Text()
                    if d == date.today():
                        cell.append(f"[{day_num}]", style="bold cyan")
                    else:
                        cell.append(str(day_num))

                    if items:
                        cell.append("\n")
                        for item in items[:2]:  # Show max 2 per day
                            cell.append(f"•{item['title'][:8]}\n", style="green")
                        if len(items) > 2:
                            cell.append(f"+{len(items)-2} more", style="dim")

                    row.append(cell)
            table.add_row(*row)

    console.print(table)

    # Summary
    total = len(rows)
    if total:
        console.print(f"\n[dim]{total} item(s) scheduled[/dim]")
    else:
        console.print("\n[dim]No content scheduled in this period[/dim]")
