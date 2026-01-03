"""Panic command for quick video idea generation."""

import re

import typer
from rich.panel import Panel
from rich.markdown import Markdown

from ..core.database import get_db
from ..services.llm import get_prompt, generate
from ..utils.display import console, print_success, print_error

app = typer.Typer(help="Quick video idea generation using LLM")


def extract_title(content: str) -> str:
    """Extract title from LLM-generated content.

    Looks for patterns like "Title: ...", "# Title", or first line.
    """
    # Try "Title:" pattern
    match = re.search(r"(?:^|\n)\s*(?:Title|VIDEO TITLE)[:\s]*(.+?)(?:\n|$)", content, re.IGNORECASE)
    if match:
        return match.group(1).strip().strip('"\'*#')

    # Try markdown header
    match = re.search(r"^#\s+(.+?)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"\'*')

    # Fall back to first non-empty line
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            # Truncate if too long
            return line[:100] if len(line) > 100 else line

    return "Untitled Video Idea"


def get_random_scripts(count: int = 5) -> list[dict]:
    """Fetch random scripts from the database."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT s.body, c.title
            FROM scripts s
            JOIN content c ON s.content_id = c.id
            WHERE s.body IS NOT NULL AND s.body != ''
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (count,),
        )
        return [{"title": row["title"], "body": row["body"]} for row in cursor.fetchall()]


def format_scripts_for_prompt(scripts: list[dict]) -> str:
    """Format scripts for injection into the remake prompt."""
    parts = []
    for i, script in enumerate(scripts, 1):
        parts.append(f"--- Script {i}: {script['title']} ---\n{script['body']}")
    return "\n\n".join(parts)


@app.callback(invoke_without_command=True)
def panic(
    ctx: typer.Context,
    funny: bool = typer.Option(False, "--funny", "-f", help="Generate a funny video idea"),
    relevant: bool = typer.Option(False, "--relevant", "-r", help="Generate a timely, relevant video idea"),
    interesting: bool = typer.Option(False, "--interesting", "-i", help="Generate an interesting, educational idea"),
    remake: bool = typer.Option(False, "--remake", "-m", help="Remix 5 random existing scripts into one"),
):
    """Generate a quick video idea using LLM.

    Choose exactly one mode: --funny, --relevant, --interesting, or --remake.
    The generated idea will be displayed and you'll be prompted to save it.
    """
    # Validate exactly one flag is set
    flags = [funny, relevant, interesting, remake]
    flag_count = sum(flags)

    if flag_count == 0:
        console.print("[yellow]Choose one mode:[/yellow]")
        console.print("  --funny, -f      Generate a funny video idea")
        console.print("  --relevant, -r   Generate a timely, relevant idea")
        console.print("  --interesting, -i Generate an educational idea")
        console.print("  --remake, -m     Remix 5 random scripts into one")
        console.print("\n[dim]Example: bmc panic --funny[/dim]")
        raise typer.Exit(0)

    if flag_count > 1:
        print_error("Choose exactly one: --funny, --relevant, --interesting, or --remake")
        raise typer.Exit(1)

    # Determine prompt type
    if funny:
        prompt_type = "funny"
    elif relevant:
        prompt_type = "relevant"
    elif interesting:
        prompt_type = "interesting"
    else:
        prompt_type = "remake"

    # Load prompt config
    prompt_config = get_prompt(prompt_type)
    if not prompt_config:
        print_error(f"Prompt type '{prompt_type}' not found in prompts.toml")
        raise typer.Exit(1)

    model = prompt_config["model"]
    prompt_text = prompt_config["prompt"]

    # Fetch random scripts for context (all modes now use scripts)
    scripts_used = get_random_scripts(5)
    if scripts_used:
        if len(scripts_used) < 5:
            console.print(f"[dim]Using {len(scripts_used)} existing script(s) for context[/dim]")
        scripts_text = format_scripts_for_prompt(scripts_used)
        prompt_text = prompt_text.replace("{scripts}", scripts_text)
    else:
        # No scripts available - remove the placeholder
        prompt_text = prompt_text.replace("{scripts}", "(No existing scripts yet)")

    # Call LLM
    console.print(f"[dim]Generating idea using {model}...[/dim]")

    try:
        result = generate(prompt_text, model)
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        print_error(f"API error: {e}")
        raise typer.Exit(1)

    content = result["content"]
    tokens = result["tokens_used"]

    # Display result
    md = Markdown(content)
    panel = Panel(
        md,
        title=f"Generated Idea ({prompt_type})",
        subtitle=f"Model: {model} | Tokens: {tokens}",
        border_style="green",
    )
    console.print(panel)

    # Interactive confirmation
    console.print()
    if not typer.confirm("Create content entry with this script?"):
        console.print("[dim]Idea not saved.[/dim]")
        raise typer.Exit(0)

    # Extract title and create content + script
    title = extract_title(content)

    with get_db() as conn:
        # Create content entry
        cursor = conn.execute(
            """
            INSERT INTO content (title, description, status, content_type)
            VALUES (?, ?, 'idea', 'video')
            """,
            (title, f"Generated via panic --{prompt_type}"),
        )
        content_id = cursor.lastrowid

        # Create script
        cursor = conn.execute(
            "INSERT INTO scripts (content_id, version, body) VALUES (?, 1, ?)",
            (content_id, content),
        )
        script_id = cursor.lastrowid

        # Update content with script reference
        conn.execute("UPDATE content SET script_id = ? WHERE id = ?", (script_id, content_id))

        # Save to ideas table for history
        conn.execute(
            """
            INSERT INTO ideas (prompt, response, model, tokens_used, converted_to_content_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (prompt_text[:1000], content, model, tokens, content_id),
        )

    print_success(f"Created content #{content_id}: {title}")
    console.print(f"[dim]View script: bmc scripts show {content_id}[/dim]")
