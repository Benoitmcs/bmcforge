"""Publishing commands for BMCForge."""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..core.database import get_db
from ..core.config import get_config_value, set_config_value, APP_DIR
from ..core.models import Platform, Publication, PublicationStatus
from ..utils.display import console, print_success, print_error, print_warning

app = typer.Typer(help="Publish content to platforms")

# Dependencies for each platform
PLATFORM_DEPS = {
    "youtube": [
        "google-api-python-client>=2.0.0",
        "google-auth-oauthlib>=1.0.0",
    ],
    "instagram": [
        "httpx>=0.25.0",
    ],
    "tiktok": [
        "playwright>=1.40.0",
    ],
}


def _check_youtube_available() -> bool:
    """Check if YouTube dependencies are installed."""
    try:
        from ..services.publishers.youtube import check_youtube_available

        return check_youtube_available()
    except ImportError:
        return False


def _get_youtube_publisher():
    """Get a YouTube publisher instance."""
    from ..services.publishers.youtube import YouTubePublisher

    credentials_path = get_config_value("youtube.credentials_path")
    if credentials_path:
        credentials_path = Path(credentials_path).expanduser()

    return YouTubePublisher(credentials_path)


def _check_instagram_available() -> bool:
    """Check if Instagram dependencies are installed."""
    try:
        from ..services.publishers.instagram import check_instagram_available

        return check_instagram_available()
    except ImportError:
        return False


def _get_instagram_publisher():
    """Get an Instagram publisher instance."""
    from ..services.publishers.instagram import InstagramPublisher

    access_token = get_config_value("instagram.access_token")
    user_id = get_config_value("instagram.user_id")

    return InstagramPublisher(access_token=access_token, user_id=user_id)


@app.command()
def setup(
    platform: str = typer.Argument(
        "youtube",
        help="Platform to set up (youtube, tiktok, or 'all')",
    ),
):
    """Install dependencies for a publishing platform."""
    platform = platform.lower()

    if platform == "all":
        platforms = list(PLATFORM_DEPS.keys())
    elif platform in PLATFORM_DEPS:
        platforms = [platform]
    else:
        print_error(f"Unknown platform: {platform}")
        valid = ", ".join(list(PLATFORM_DEPS.keys()) + ["all"])
        console.print(f"[dim]Valid options: {valid}[/dim]")
        raise typer.Exit(1)

    for plat in platforms:
        deps = PLATFORM_DEPS[plat]
        console.print(f"\n[bold]Installing {plat} dependencies...[/bold]")

        for dep in deps:
            console.print(f"  Installing {dep}...")

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet"] + deps,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print_error(f"Failed to install {plat} dependencies")
                if result.stderr:
                    console.print(f"[dim]{result.stderr}[/dim]")
                raise typer.Exit(1)

            print_success(f"{plat.capitalize()} dependencies installed!")

            # Special post-install for playwright
            if plat == "tiktok":
                console.print("  Installing Playwright browsers...")
                subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    capture_output=True,
                )
                print_success("Playwright browsers installed!")

        except Exception as e:
            print_error(f"Installation failed: {e}")
            raise typer.Exit(1)

    console.print(f"\n[green]Setup complete![/green]")
    console.print(f"[dim]Run 'bmc publish auth {platforms[0]}' to authenticate.[/dim]")


@app.command()
def auth(
    platform: str = typer.Argument(..., help="Platform to authenticate (youtube, instagram, tiktok)"),
):
    """Authenticate with a publishing platform."""
    try:
        plat = Platform(platform.lower())
    except ValueError:
        print_error(f"Unknown platform: {platform}")
        valid = ", ".join(p.value for p in Platform)
        console.print(f"[dim]Valid platforms: {valid}[/dim]")
        raise typer.Exit(1)

    if plat == Platform.YOUTUBE:
        if not _check_youtube_available():
            print_error(
                "YouTube publishing requires additional dependencies.\n"
                "Run: bmc publish setup youtube"
            )
            raise typer.Exit(1)

        # Check for credentials file
        credentials_path = get_config_value("youtube.credentials_path")
        if not credentials_path:
            credentials_path = str(APP_DIR / "youtube_client_secrets.json")

        creds_file = Path(credentials_path).expanduser()
        if not creds_file.exists():
            console.print("\n[bold]YouTube Setup Instructions:[/bold]\n")
            console.print("1. Go to https://console.cloud.google.com")
            console.print("2. Create a new project (or select existing)")
            console.print("3. Enable the 'YouTube Data API v3'")
            console.print("4. Go to 'Credentials' > 'Create Credentials' > 'OAuth client ID'")
            console.print("5. Select 'Desktop app' as the application type")
            console.print("6. Download the JSON file")
            console.print(f"7. Save it as: [cyan]{creds_file}[/cyan]\n")
            console.print("Then run this command again.")
            raise typer.Exit(1)

        try:
            publisher = _get_youtube_publisher()
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Opening browser for authentication...", total=None)
                publisher.authenticate()

            print_success("YouTube authentication successful!")
            console.print("[dim]Token saved for future use.[/dim]")

        except Exception as e:
            print_error(f"Authentication failed: {e}")
            raise typer.Exit(1)

    elif plat == Platform.INSTAGRAM:
        if not _check_instagram_available():
            print_error(
                "Instagram publishing requires httpx.\n"
                "Run: bmc publish setup instagram"
            )
            raise typer.Exit(1)

        # Check if credentials are configured
        access_token = get_config_value("instagram.access_token")
        user_id = get_config_value("instagram.user_id")

        if not access_token or not user_id:
            console.print("\n[bold]Instagram Content Publishing Setup[/bold]\n")
            console.print("[yellow]Important:[/yellow] You need a [bold]Facebook Page Access Token[/bold],")
            console.print("NOT an Instagram token. Tokens starting with 'IGAA' won't work.\n")
            console.print("[cyan]Step 1:[/cyan] Prerequisites")
            console.print("  - Instagram Business or Creator account")
            console.print("  - Facebook Page linked to that Instagram account")
            console.print("  - Meta Developer account (developers.facebook.com)\n")
            console.print("[cyan]Step 2:[/cyan] Create Meta App")
            console.print("  - Create app → Select 'Business' type")
            console.print("  - Add product: 'Instagram Graph API'\n")
            console.print("[cyan]Step 3:[/cyan] Get Page Access Token")
            console.print("  - Go to Graph API Explorer (developers.facebook.com/tools/explorer)")
            console.print("  - Select your app")
            console.print("  - Click 'Get Token' → 'Get Page Access Token'")
            console.print("  - Select your Facebook Page linked to Instagram")
            console.print("  - Add permissions: instagram_basic, instagram_content_publish,")
            console.print("    pages_read_engagement, pages_show_list")
            console.print("  - Token should start with 'EAA...'\n")
            console.print("[cyan]Step 4:[/cyan] Get Instagram Business Account ID")
            console.print("  In Graph API Explorer, query: [dim]me/accounts?fields=instagram_business_account[/dim]")
            console.print("  Copy the 'instagram_business_account.id' value\n")
            console.print("[cyan]Step 5:[/cyan] (Optional) Get Long-Lived Token")
            console.print("  Exchange for 60-day token via: [dim]oauth/access_token?grant_type=fb_exchange_token...[/dim]\n")
            console.print("[cyan]Step 6:[/cyan] Configure BMCForge")
            console.print("  [green]bmc config set instagram.access_token EAA...[/green]")
            console.print("  [green]bmc config set instagram.user_id YOUR_IG_BUSINESS_ID[/green]\n")
            raise typer.Exit(1)

        try:
            publisher = _get_instagram_publisher()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Validating Instagram credentials...", total=None)
                publisher.authenticate()

            # Show account info
            info = publisher.get_account_info()
            if "username" in info:
                console.print(f"\n[bold]Connected as:[/bold] @{info['username']}")
                if "followers_count" in info:
                    console.print(f"[dim]Followers: {info['followers_count']:,}[/dim]")

            print_success("Instagram authentication verified!")

        except Exception as e:
            print_error(f"Authentication failed: {e}")
            # Try to debug the token
            console.print("\n[dim]Debugging token...[/dim]")
            try:
                debug_info = publisher.debug_token()
                if "error" in debug_info:
                    console.print(f"[red]Token debug error:[/red] {debug_info['error']}")
                    if "hint" in debug_info:
                        console.print(f"[yellow]{debug_info['hint']}[/yellow]")
                else:
                    console.print(f"[dim]Token type: {debug_info.get('type', 'unknown')}[/dim]")
                    console.print(f"[dim]Valid: {debug_info.get('is_valid', 'unknown')}[/dim]")
                    console.print(f"[dim]Scopes: {debug_info.get('scopes', [])}[/dim]")
            except Exception:
                pass
            console.print(f"\n[dim]Token prefix: {access_token[:10]}...[/dim]")
            console.print(f"[dim]User ID: {user_id}[/dim]")
            raise typer.Exit(1)

    elif plat == Platform.TIKTOK:
        console.print("\n[bold]TikTok Setup:[/bold]\n")
        console.print("TikTok publishing uses browser automation.")
        print_warning("TikTok publishing is not yet implemented.")


@app.command()
def upload(
    content_id: int = typer.Argument(..., help="Content ID to publish"),
    video: str = typer.Argument(..., help="Path to video file"),
    platform: str = typer.Option("youtube", "--platform", "-p", help="Platform (youtube, instagram, tiktok)"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Override content title"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Override description"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
    schedule: Optional[str] = typer.Option(
        None,
        "--schedule",
        "-s",
        help="Schedule for later (ISO 8601: 2025-01-15T10:00:00)",
    ),
    privacy: str = typer.Option("private", "--privacy", help="Privacy: private, public, unlisted"),
    category: str = typer.Option("people_blogs", "--category", "-c", help="YouTube category"),
):
    """Upload a video to a platform."""
    try:
        plat = Platform(platform.lower())
    except ValueError:
        print_error(f"Unknown platform: {platform}")
        raise typer.Exit(1)

    # Validate video file
    video_path = Path(video).expanduser()
    if not video_path.exists():
        print_error(f"Video file not found: {video}")
        raise typer.Exit(1)

    # Get content from database
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT id, title, description FROM content WHERE id = ?",
            (content_id,),
        )
        row = cursor.fetchone()

        if not row:
            print_error(f"Content #{content_id} not found")
            raise typer.Exit(1)

        content_title = title or row["title"]
        content_desc = description or row["description"] or ""

    # Parse tags
    tag_list = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    if plat == Platform.YOUTUBE:
        if not _check_youtube_available():
            print_error(
                "YouTube publishing requires additional dependencies.\n"
                "Run: bmc publish setup youtube"
            )
            raise typer.Exit(1)

        # Get category ID
        from ..services.publishers.youtube import CATEGORY_IDS

        category_id = CATEGORY_IDS.get(category.lower().replace(" ", "_"), "22")

        publisher = _get_youtube_publisher()

        # Check authentication
        if not publisher.is_authenticated():
            console.print("[yellow]Not authenticated. Starting OAuth flow...[/yellow]")
            try:
                publisher.authenticate()
            except Exception as e:
                print_error(f"Authentication failed: {e}")
                raise typer.Exit(1)

        console.print(f"\n[bold]Uploading to YouTube:[/bold]")
        console.print(f"  Title: {content_title}")
        console.print(f"  File: {video_path}")
        console.print(f"  Privacy: {privacy}")
        if schedule:
            console.print(f"  Scheduled: {schedule}")
        console.print()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Uploading video...", total=None)

            result = publisher.upload(
                file_path=str(video_path),
                title=content_title,
                description=content_desc,
                tags=tag_list,
                scheduled_time=schedule,
                category_id=category_id,
                privacy=privacy,
            )

        if result.success:
            # Record publication in database
            with get_db() as conn:
                conn.execute(
                    """
                    INSERT INTO publications (
                        content_id, platform, post_id, post_url, status,
                        scheduled_for, published_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        content_id,
                        plat.value,
                        result.post_id,
                        result.post_url,
                        result.status.value,
                        schedule,
                        datetime.now().isoformat() if not schedule else None,
                    ),
                )

                # Update content status if published
                if result.status.value == "published":
                    conn.execute(
                        """
                        UPDATE content
                        SET status = 'published', publish_date = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (datetime.now().date().isoformat(), content_id),
                    )

            print_success(f"Video uploaded successfully!")
            console.print(f"[bold]Video ID:[/bold] {result.post_id}")
            console.print(f"[bold]URL:[/bold] {result.post_url}")
        else:
            # Record failed publication
            with get_db() as conn:
                conn.execute(
                    """
                    INSERT INTO publications (
                        content_id, platform, status, error_message
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (content_id, plat.value, "failed", result.error),
                )

            print_error(f"Upload failed: {result.error}")
            raise typer.Exit(1)

    elif plat == Platform.INSTAGRAM:
        if not _check_instagram_available():
            print_error(
                "Instagram publishing requires httpx.\n"
                "Run: bmc publish setup instagram"
            )
            raise typer.Exit(1)

        publisher = _get_instagram_publisher()

        # Check authentication
        if not publisher.is_authenticated():
            print_error(
                "Not authenticated with Instagram.\n"
                "Run: bmc publish auth instagram"
            )
            raise typer.Exit(1)

        console.print(f"\n[bold]Uploading to Instagram (Reel):[/bold]")
        console.print(f"  Caption: {content_desc[:50]}..." if len(content_desc) > 50 else f"  Caption: {content_desc}")
        console.print(f"  File: {video_path}")
        if tag_list:
            console.print(f"  Hashtags: {len(tag_list)} tags")
        console.print()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Uploading and processing video...", total=None)

            result = publisher.upload(
                file_path=str(video_path),
                title=content_title,  # Not used by Instagram but required by interface
                description=content_desc,
                tags=tag_list,
            )

        if result.success:
            # Record publication in database
            with get_db() as conn:
                conn.execute(
                    """
                    INSERT INTO publications (
                        content_id, platform, post_id, post_url, status,
                        published_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        content_id,
                        plat.value,
                        result.post_id,
                        result.post_url,
                        result.status.value,
                        datetime.now().isoformat(),
                    ),
                )

                # Update content status
                conn.execute(
                    """
                    UPDATE content
                    SET status = 'published', publish_date = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (datetime.now().date().isoformat(), content_id),
                )

            print_success("Reel published successfully!")
            console.print(f"[bold]Media ID:[/bold] {result.post_id}")
            if result.post_url:
                console.print(f"[bold]URL:[/bold] {result.post_url}")
        else:
            # Record failed publication
            with get_db() as conn:
                conn.execute(
                    """
                    INSERT INTO publications (
                        content_id, platform, status, error_message
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (content_id, plat.value, "failed", result.error),
                )

            print_error(f"Upload failed: {result.error}")
            raise typer.Exit(1)

    else:
        print_error(f"{plat.value.capitalize()} publishing is not yet implemented.")
        raise typer.Exit(1)


@app.command("status")
def publication_status(
    content_id: int = typer.Argument(..., help="Content ID to check"),
):
    """Check publication status for content."""
    with get_db() as conn:
        # Check content exists
        cursor = conn.execute("SELECT title FROM content WHERE id = ?", (content_id,))
        content_row = cursor.fetchone()

        if not content_row:
            print_error(f"Content #{content_id} not found")
            raise typer.Exit(1)

        # Get publications
        cursor = conn.execute(
            """
            SELECT * FROM publications
            WHERE content_id = ?
            ORDER BY created_at DESC
            """,
            (content_id,),
        )
        rows = cursor.fetchall()

    if not rows:
        console.print(f"[dim]No publications found for content #{content_id}[/dim]")
        return

    console.print(f"\n[bold]Publications for:[/bold] {content_row['title']}\n")

    table = Table()
    table.add_column("Platform", style="cyan")
    table.add_column("Status")
    table.add_column("Post ID", style="dim")
    table.add_column("URL")
    table.add_column("Published", style="dim")

    status_colors = {
        "pending": "yellow",
        "uploading": "yellow",
        "processing": "yellow",
        "published": "green",
        "scheduled": "blue",
        "failed": "red",
    }

    for row in rows:
        status = row["status"]
        status_style = status_colors.get(status, "white")

        url = row["post_url"] or "-"
        if len(url) > 40:
            url = url[:37] + "..."

        published = row["published_at"] or row["scheduled_for"] or "-"
        if published != "-":
            published = published[:10]  # Just the date

        table.add_row(
            row["platform"],
            f"[{status_style}]{status}[/{status_style}]",
            row["post_id"] or "-",
            url,
            published,
        )

        if row["error_message"]:
            table.add_row("", f"[red]Error: {row['error_message']}[/red]", "", "", "")

    console.print(table)


@app.command("list")
def list_publications(
    platform: Optional[str] = typer.Option(None, "--platform", "-p", help="Filter by platform"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum items"),
):
    """List all publications."""
    query = """
        SELECT p.*, c.title as content_title
        FROM publications p
        JOIN content c ON p.content_id = c.id
    """
    params = []
    conditions = []

    if platform:
        conditions.append("p.platform = ?")
        params.append(platform.lower())

    if status:
        conditions.append("p.status = ?")
        params.append(status.lower())

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY p.created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

    if not rows:
        console.print("[dim]No publications found.[/dim]")
        return

    table = Table(title="Publications")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Content", style="bold")
    table.add_column("Platform", style="cyan")
    table.add_column("Status")
    table.add_column("URL", style="dim")

    status_colors = {
        "pending": "yellow",
        "uploading": "yellow",
        "processing": "yellow",
        "published": "green",
        "scheduled": "blue",
        "failed": "red",
    }

    for row in rows:
        status = row["status"]
        status_style = status_colors.get(status, "white")

        url = row["post_url"] or "-"
        if len(url) > 35:
            url = url[:32] + "..."

        content_title = row["content_title"]
        if len(content_title) > 30:
            content_title = content_title[:27] + "..."

        table.add_row(
            str(row["id"]),
            content_title,
            row["platform"],
            f"[{status_style}]{status}[/{status_style}]",
            url,
        )

    console.print(table)


@app.command()
def revoke(
    platform: str = typer.Argument(..., help="Platform to revoke authentication"),
):
    """Revoke authentication for a platform."""
    try:
        plat = Platform(platform.lower())
    except ValueError:
        print_error(f"Unknown platform: {platform}")
        raise typer.Exit(1)

    if plat == Platform.YOUTUBE:
        if not _check_youtube_available():
            print_error("YouTube publishing dependencies not installed.")
            raise typer.Exit(1)

        publisher = _get_youtube_publisher()
        if publisher.revoke():
            print_success("YouTube authentication revoked.")
        else:
            console.print("[dim]No YouTube authentication found.[/dim]")

    elif plat == Platform.INSTAGRAM:
        if not _check_instagram_available():
            print_error("Instagram publishing dependencies not installed.")
            raise typer.Exit(1)

        publisher = _get_instagram_publisher()
        if publisher.revoke():
            print_success("Instagram credentials removed.")
        else:
            console.print("[dim]No Instagram credentials found.[/dim]")

    else:
        print_error(f"Revoke not implemented for {plat.value}")


@app.command()
def categories():
    """List available YouTube categories."""
    from ..services.publishers.youtube import CATEGORY_IDS

    table = Table(title="YouTube Categories")
    table.add_column("Category", style="cyan")
    table.add_column("ID", style="dim")

    for name, cat_id in sorted(CATEGORY_IDS.items()):
        display_name = name.replace("_", " ").title()
        table.add_row(display_name, cat_id)

    console.print(table)
