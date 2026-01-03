# BMCForge

A local-first CLI tool for video creators to manage content pipelines, organize assets, and generate ideas.

## Overview

BMCForge fills a gap between generic task managers and enterprise DAM systems. It's designed for solo creators or small teams who:

- Work primarily from the terminal
- Need to track content from idea to published
- Want organized B-roll and SFX libraries with tagging
- Use LLMs for brainstorming but want local-first data
- Prefer lightweight, portable tools over web apps

## Features

- **Content Pipeline Management** - Track videos through stages: idea, scripted, filming, editing, scheduled, published
- **Asset Registry** - Tag and search B-roll, SFX, music, and graphics without copying files
- **Script Versioning** - Create, edit, and track script history
- **Shot Lists** - Build and manage shot checklists for production
- **LLM Integration** - Generate content ideas via OpenRouter API with customizable prompts
- **Panic Mode** - Quick video idea generation with --funny, --relevant, --interesting, or --remake flags
- **Multi-Platform Publishing** - Publish to YouTube, Instagram, and TikTok
- **Calendar View** - Visualize scheduled content
- **Local-First** - All data stored locally in SQLite

## Installation

### Quick Install (recommended)

```bash
# Using pipx (handles venv automatically)
pipx install bmcforge

# Or from source
git clone https://github.com/you/bmcforge
cd bmcforge
./install.sh
```

### Development Install

```bash
git clone https://github.com/you/bmcforge
cd bmcforge
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
source .venv/bin/activate
```

### With Publishing Support

```bash
pipx install "bmcforge[publishing]"
# or
./install.sh && .venv/bin/pip install -e ".[publishing]"
```

### First Run

```bash
bmc config set api.openrouter_key "your-key-here"
bmc content add "My First Video"
```

## Quick Start

```bash
# Add new content
bmc content add "10 Vim Tricks" --type video --platform youtube

# Register assets
bmc assets add ~/Videos/broll/cityscape.mp4 --type broll
bmc assets tag 1 "urban" "night" "cinematic"

# Generate ideas
bmc ideas generate "video ideas about neovim productivity"

# Publish to platforms
bmc publish 1 --platform youtube instagram

# View pipeline status
bmc status
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         BMCForge CLI                            │
├─────────────────────────────────────────────────────────────────┤
│  Commands                                                       │
│  ├── content    (schedule, list, status, publish)              │
│  ├── assets     (add, tag, search, link)                       │
│  ├── scripts    (create, edit, version)                        │
│  ├── shots      (create, assign, checklist)                    │
│  ├── panic      (--funny, --relevant, --remake)  ← Quick LLM   │
│  ├── ideas      (generate, brainstorm, expand)   ← LLM         │
│  ├── publish    (youtube, instagram, tiktok)     ← Multi-plat  │
│  └── config     (setup, api-key, defaults)                     │
├─────────────────────────────────────────────────────────────────┤
│  Core Services                                                  │
│  ├── ContentService      │  AssetService                       │
│  ├── ScriptService       │  ShotListService                    │
│  ├── IdeaService (LLM)   │  CalendarService                    │
│  ├── PublishService      │  SearchService                      │
│  └── YouTubePublisher    │  InstagramPublisher                 │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer                                                     │
│  ├── SQLite Database (~/.bmcforge/bmcforge.db)                 │
│  ├── Asset Registry (symlinks + metadata, not file copies)     │
│  └── Config Store (~/.bmcforge/config.toml)                    │
├─────────────────────────────────────────────────────────────────┤
│  External                                                       │
│  ├── OpenRouter API (LLM for idea generation)                  │
│  ├── YouTube Data API v3 (publishing)                          │
│  ├── Meta Graph API (Instagram publishing)                     │
│  ├── Playwright (TikTok automation - future)                   │
│  └── File System (B-roll, SFX directories)                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component     | Choice                       | Rationale                                           |
| ------------- | ---------------------------- | --------------------------------------------------- |
| CLI Framework | **Typer**                    | Type hints, auto-help, minimal code, built on Click |
| Database      | **SQLite**                   | Zero-config, JSON support, single file, portable    |
| ORM/DB Utils  | **sqlite-utils**             | Great JSON handling, or raw sqlite3 for control     |
| Config        | **TOML**                     | Human-readable, Python 3.11+ native support         |
| LLM API       | **OpenRouter**               | Single API for multiple models, OpenAI-compatible   |
| HTTP Client   | **httpx**                    | Modern, async support, cleaner than requests        |
| Rich Output   | **rich**                     | Tables, progress bars, markdown rendering           |
| Date Handling | **pendulum**                 | Better than datetime for scheduling                 |
| YouTube API   | **google-api-python-client** | Official Google library                             |
| Instagram API | **httpx**                    | Direct Graph API calls                              |
| TikTok        | **Playwright**               | Browser automation (future)                         |

---

## Project Structure

```
bmcforge/
├── pyproject.toml
├── README.md
├── src/
│   └── bmcforge/
│       ├── __init__.py
│       ├── __main__.py          # Entry point
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py          # Typer app, command groups
│       │   ├── content.py       # content subcommands
│       │   ├── assets.py        # assets subcommands
│       │   ├── scripts.py       # scripts subcommands
│       │   ├── shots.py         # shot list subcommands
│       │   ├── panic.py         # quick LLM idea generation
│       │   ├── ideas.py         # LLM idea generation
│       │   ├── publish.py       # publishing commands
│       │   └── config.py        # configuration commands
│       ├── core/
│       │   ├── __init__.py
│       │   ├── database.py      # SQLite connection, migrations
│       │   ├── config.py        # Config loading/saving
│       │   └── models.py        # Pydantic models / dataclasses
│       ├── services/
│       │   ├── __init__.py
│       │   ├── llm.py           # OpenRouter API client
│       │   ├── content.py       # Content CRUD operations
│       │   ├── assets.py        # Asset management
│       │   ├── scripts.py       # Script versioning
│       │   ├── shots.py         # Shot list management
│       │   ├── ideas.py         # OpenRouter integration
│       │   ├── search.py        # Full-text search
│       │   └── publishers/
│       │       ├── __init__.py
│       │       ├── base.py      # Publisher interface
│       │       ├── youtube.py   # YouTube Data API
│       │       ├── instagram.py # Meta Graph API
│       │       └── tiktok.py    # Playwright automation
│       └── utils/
│           ├── __init__.py
│           ├── display.py       # Rich tables, formatting
│           ├── dates.py         # Date parsing helpers
│           └── files.py         # File metadata extraction
└── tests/
```

---

## CLI Commands

### Content Management

```bash
# Add new content
bmc content add "10 Vim Tricks" --type video --platform youtube

# List content by status
bmc content list                     # all
bmc content list --status scripted   # filter by status
bmc content list --upcoming          # scheduled in next 7 days

# Update content
bmc content status 1 filming         # change status
bmc content schedule 1 2025-01-15    # set publish date
bmc content link-asset 1 42          # link asset to content

# Calendar view
bmc content calendar                 # show month view
bmc content calendar --week          # show week view
```

### Asset Management

```bash
# Register assets (doesn't copy, just tracks)
bmc assets add ~/Videos/broll/cityscape.mp4 --type broll
bmc assets add ~/Audio/sfx/ --type sfx --recursive  # bulk add

# Tagging
bmc assets tag 1 "urban" "night" "cinematic"
bmc assets untag 1 "night"

# Search
bmc assets search "urban cinematic"       # by tags
bmc assets search --type broll            # by type
bmc assets search --unused                # not linked to any content
bmc assets list --type sfx                # list all of type
```

### Scripts

```bash
bmc scripts create 1                      # create for content #1
bmc scripts edit 1                        # open in $EDITOR
bmc scripts show 1                        # display script
bmc scripts history 1                     # show versions
```

### Shot Lists

Shot lists are linked to scripts, not content directly. Each script version has its own independent shot list. When you create a new script version (via `bmc scripts edit`), the shot list is automatically copied from the previous version.

```bash
# Add shots (to latest script version by default)
bmc shots add 1 "Wide establishing shot of office" --type wide
bmc shots add 1 "Close-up of typing" --type close --duration 5

# List shots
bmc shots list 1                          # show shots for latest version
bmc shots list 1 --version 2              # show shots for specific version
bmc shots all                             # list all shots across all scripts
bmc shots all --pending                   # only show pending shots

# Manage shots (all commands support --version flag)
bmc shots check 1 3                       # mark shot #3 complete
bmc shots check 1 3 --version 1           # mark shot in specific version
bmc shots reorder 1 3 1                   # move shot 3 to position 1
bmc shots edit 1 2 --desc "New description"
bmc shots remove 1 3
```

### Panic Mode (Quick LLM Ideas)

Generate video ideas that can be filmed and edited in under 2 hours. Choose one mode per run.

```bash
# Generate a funny video idea
bmc panic --funny

# Generate a timely, trending idea
bmc panic --relevant

# Generate an educational idea
bmc panic --interesting

# Remix 5 random existing scripts into a fresh idea
bmc panic --remake
```

The command displays the generated idea and prompts you to save it as a new content entry with script.

**How it works:**

All modes automatically include 5 random scripts from your database to give the LLM context about your topics and style. This helps generate ideas that fit your content niche.

**Configuration:**

The prompts config file `~/.bmcforge/prompts.toml` is created automatically on first run of any `bmc` command. The default model is `tngtech/deepseek-r1t2-chimera:free` (a free model on OpenRouter).

**Customizing prompts:**

Edit `~/.bmcforge/prompts.toml` to customize prompts and models:

```toml
[funny]
model = "tngtech/deepseek-r1t2-chimera:free"
prompt = """Your custom prompt here...

Here are some of my existing scripts for context on topics and style:
{scripts}

Be specific and actionable."""
```

The `{scripts}` placeholder is replaced with 5 random scripts from your database. If you have no scripts yet, it will show "(No existing scripts yet)".

### Idea Generation (LLM)

```bash
# Generate ideas
bmc ideas generate "video ideas about neovim productivity"
bmc ideas generate --from-content 1       # expand on existing content
bmc ideas brainstorm "coding tutorials"   # multiple ideas

# Manage ideas
bmc ideas list                            # show saved ideas
bmc ideas rate 5 4                        # rate idea #5 as 4 stars
bmc ideas convert 5                       # convert idea to content item

# Interactive mode
bmc ideas chat                            # conversational brainstorming
```

### Publishing

```bash
# Authenticate platforms (one-time setup)
bmc publish auth youtube              # Opens browser for OAuth
bmc publish auth instagram            # Guides through Meta developer setup

# Publish content
bmc publish 1 --platform youtube      # Single platform
bmc publish 1 --platform youtube instagram  # Multiple platforms

# Schedule publishing
bmc publish 1 --platform youtube --schedule "2025-01-15T10:00:00"

# Check publish status
bmc publish status 1                  # Show where content #1 is published
```

### Configuration

```bash
bmc config init                           # first-time setup
bmc config set openrouter_key "sk-..."    # set API key
bmc config set default_platform youtube
bmc config set broll_dir ~/Videos/broll
bmc config set sfx_dir ~/Audio/sfx
bmc config show                           # display current config
```

---

## Platform Publishing Integration

### Platform Comparison

| Platform      | API Type              | Auth Method     | Difficulty |
| ------------- | --------------------- | --------------- | ---------- |
| **YouTube**   | Official API          | OAuth 2.0       | Medium     |
| **Instagram** | Graph API (Meta)      | OAuth 2.0       | Medium     |
| **TikTok**    | Playwright automation | Browser session | Medium     |

### YouTube Integration

Best option. Google provides official Python libraries and the API is mature.

```python
# services/publishers/youtube.py
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

class YouTubePublisher:
    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path
        self.youtube = None

    def authenticate(self):
        """OAuth flow - opens browser first time, then uses stored token."""
        creds = None
        token_path = os.path.expanduser("~/.bmcforge/youtube_token.json")

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=8080)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        self.youtube = build('youtube', 'v3', credentials=creds)

    def upload(
        self,
        file_path: str,
        title: str,
        description: str,
        tags: list[str],
        category_id: str = "22",  # People & Blogs
        privacy: str = "private",
        scheduled_time: str = None  # ISO 8601 format
    ) -> str:
        """Upload video and return video ID."""

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy,
                'selfDeclaredMadeForKids': False
            }
        }

        if scheduled_time and privacy == 'private':
            body['status']['publishAt'] = scheduled_time

        media = MediaFileUpload(file_path, chunksize=-1, resumable=True)

        request = self.youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        response = request.execute()
        return response['id']
```

**Setup requirements:**

1. Create project at https://console.cloud.google.com
2. Enable YouTube Data API v3
3. Create OAuth 2.0 credentials (Desktop app)
4. Download `client_secrets.json`
5. First run opens browser for auth

### Instagram Integration

Requires Business or Creator account linked to a Facebook Page.

```python
# services/publishers/instagram.py
import httpx
import time

class InstagramPublisher:
    GRAPH_URL = "https://graph.facebook.com/v18.0"

    def __init__(self, access_token: str, ig_user_id: str):
        self.access_token = access_token
        self.ig_user_id = ig_user_id

    async def publish_reel(
        self,
        video_url: str,  # Must be publicly accessible URL
        caption: str,
        share_to_feed: bool = True
    ) -> str:
        """Publish a Reel to Instagram."""

        async with httpx.AsyncClient() as client:
            # Step 1: Create media container
            create_response = await client.post(
                f"{self.GRAPH_URL}/{self.ig_user_id}/media",
                params={
                    "access_token": self.access_token,
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": caption,
                    "share_to_feed": str(share_to_feed).lower()
                }
            )
            container_id = create_response.json()["id"]

            # Step 2: Wait for processing
            while True:
                status_response = await client.get(
                    f"{self.GRAPH_URL}/{container_id}",
                    params={
                        "access_token": self.access_token,
                        "fields": "status_code"
                    }
                )
                status = status_response.json().get("status_code")
                if status == "FINISHED":
                    break
                elif status == "ERROR":
                    raise Exception("Video processing failed")
                time.sleep(5)

            # Step 3: Publish
            publish_response = await client.post(
                f"{self.GRAPH_URL}/{self.ig_user_id}/media_publish",
                params={
                    "access_token": self.access_token,
                    "creation_id": container_id
                }
            )

            return publish_response.json()["id"]
```

**Note:** Instagram requires videos to be hosted at a public URL. Options:

- Upload to your own server/S3 first
- Use a temporary file hosting service
- Use `instagrapi` library (unofficial, uses private API)

### TikTok Integration (Future)

TikTok's official API requires app audits and has visibility restrictions. Using Playwright-based browser automation instead.

```python
# services/publishers/tiktok.py
from playwright.sync_api import sync_playwright
from pathlib import Path

class TikTokPublisher:
    AUTH_STATE = Path("~/.bmcforge/tiktok_auth.json").expanduser()

    def login(self):
        """Interactive login - saves session for future use."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            page.goto("https://www.tiktok.com/login")
            input("Complete login in browser, then press Enter...")

            context.storage_state(path=str(self.AUTH_STATE))
            browser.close()

    def upload(
        self,
        video_path: str,
        description: str,
        hashtags: list[str]
    ) -> bool:
        """Upload video using saved session."""

        caption = f"{description} {' '.join('#' + t for t in hashtags)}"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(storage_state=str(self.AUTH_STATE))
            page = context.new_page()

            page.goto("https://www.tiktok.com/upload")
            page.wait_for_load_state("networkidle")

            page.set_input_files('input[type="file"]', video_path)
            page.wait_for_timeout(3000)

            page.fill('[data-e2e="caption-input"]', caption)
            page.click('[data-e2e="post-button"]')
            page.wait_for_timeout(5000)

            context.storage_state(path=str(self.AUTH_STATE))
            browser.close()

            return True
```

### Unified Publishing Interface

```python
# services/publisher.py
from enum import Enum
from typing import Optional
from dataclasses import dataclass

class Platform(Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"

@dataclass
class PublishResult:
    platform: Platform
    success: bool
    post_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None

class PublishService:
    def __init__(self, config):
        self.youtube = YouTubePublisher(config.youtube_credentials)
        self.instagram = InstagramPublisher(
            config.instagram_token,
            config.instagram_user_id
        )

    async def publish(
        self,
        content_id: int,
        platforms: list[Platform],
        video_path: str,
        title: str,
        description: str,
        tags: list[str]
    ) -> list[PublishResult]:
        """Publish content to multiple platforms."""
        results = []

        for platform in platforms:
            try:
                if platform == Platform.YOUTUBE:
                    post_id = self.youtube.upload(
                        video_path, title, description, tags
                    )
                    url = f"https://youtube.com/watch?v={post_id}"

                elif platform == Platform.INSTAGRAM:
                    post_id = await self.instagram.publish_reel(
                        video_url, f"{description} {' '.join('#'+t for t in tags)}"
                    )
                    url = f"https://instagram.com/reel/{post_id}"

                results.append(PublishResult(
                    platform=platform,
                    success=True,
                    post_id=post_id,
                    url=url
                ))

            except Exception as e:
                results.append(PublishResult(
                    platform=platform,
                    success=False,
                    error=str(e)
                ))

        return results
```

---

## OpenRouter Integration

```python
# services/llm.py
import httpx
from typing import Optional
from ..core.config import get_config

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

class IdeaService:
    def __init__(self):
        config = get_config()
        self.api_key = config.openrouter_key
        self.default_model = config.get("llm_model", "tngtech/deepseek-r1t2-chimera:free")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None
    ) -> dict:
        """Generate content ideas using OpenRouter."""

        if not system_prompt:
            system_prompt = """You are a creative assistant for a video content creator.
            Generate engaging, specific, and actionable content ideas.
            Consider SEO, audience engagement, and practical production feasibility."""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OPENROUTER_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model or self.default_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            response.raise_for_status()
            data = response.json()

            return {
                "content": data["choices"][0]["message"]["content"],
                "model": data["model"],
                "tokens": data.get("usage", {}).get("total_tokens", 0)
            }

    async def brainstorm(self, topic: str, count: int = 5) -> list[str]:
        """Generate multiple content ideas on a topic."""
        prompt = f"""Generate {count} unique video content ideas about: {topic}

        For each idea, provide:
        1. A catchy title
        2. A one-sentence hook
        3. Key talking points (3-5 bullets)

        Format as numbered list."""

        result = await self.generate(prompt)
        return result
```

---

## Configuration

Configuration is stored in `~/.bmcforge/config.toml`.

LLM prompts are stored in `~/.bmcforge/prompts.toml` (created automatically on first run):

```toml
[general]
default_platform = "youtube"
editor = "nvim"  # or $EDITOR

[paths]
broll_dir = "~/Videos/broll"
sfx_dir = "~/Audio/sfx"
music_dir = "~/Audio/music"
exports_dir = "~/Videos/exports"

[api]
openrouter_key = ""  # set via `bmc config set openrouter_key`
llm_model = "tngtech/deepseek-r1t2-chimera:free"  # free model default

[youtube]
credentials_path = "~/.bmcforge/youtube_client_secrets.json"

[instagram]
access_token = ""
user_id = ""

[display]
date_format = "%Y-%m-%d"
show_file_sizes = true
color_theme = "auto"  # auto, dark, light

[defaults]
content_type = "video"
shot_duration = 5  # seconds
```

---

## Database Schema

```sql
-- Core content items (videos, posts, etc.)
CREATE TABLE content (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'idea',  -- idea, scripted, filming, editing, scheduled, published
    content_type TEXT DEFAULT 'video',  -- video, short, post, reel
    scheduled_date DATE,
    publish_date DATE,
    platform TEXT,  -- youtube, tiktok, instagram, etc.
    script_id INTEGER REFERENCES scripts(id),
    shot_list_id INTEGER REFERENCES shot_lists(id),
    metadata JSON,  -- flexible extra data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scripts with versioning
CREATE TABLE scripts (
    id INTEGER PRIMARY KEY,
    content_id INTEGER REFERENCES content(id),
    version INTEGER DEFAULT 1,
    body TEXT,
    notes TEXT,
    word_count INTEGER GENERATED ALWAYS AS (
        length(body) - length(replace(body, ' ', '')) + 1
    ) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Shot lists (linked to scripts, not content)
CREATE TABLE shot_lists (
    id INTEGER PRIMARY KEY,
    script_id INTEGER REFERENCES scripts(id),
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE shots (
    id INTEGER PRIMARY KEY,
    shot_list_id INTEGER REFERENCES shot_lists(id),
    sequence INTEGER,  -- order in the list
    description TEXT NOT NULL,
    shot_type TEXT,  -- wide, medium, close, broll, talking_head
    duration_estimate INTEGER,  -- seconds
    location TEXT,
    notes TEXT,
    completed BOOLEAN DEFAULT FALSE
);

-- Asset registry (doesn't copy files, just tracks them)
CREATE TABLE assets (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,  -- absolute path to actual file
    asset_type TEXT NOT NULL,  -- broll, sfx, music, graphic, footage
    file_type TEXT,  -- mp4, wav, mp3, png, etc.
    file_size INTEGER,
    duration REAL,  -- for video/audio, in seconds
    metadata JSON,  -- resolution, codec, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tags for assets
CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    category TEXT  -- mood, location, subject, etc.
);

CREATE TABLE asset_tags (
    asset_id INTEGER REFERENCES assets(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (asset_id, tag_id)
);

-- Link assets to content
CREATE TABLE content_assets (
    content_id INTEGER REFERENCES content(id) ON DELETE CASCADE,
    asset_id INTEGER REFERENCES assets(id) ON DELETE CASCADE,
    usage_type TEXT,  -- broll, intro, outro, sfx, etc.
    timestamp_start REAL,  -- where in the video (optional)
    notes TEXT,
    PRIMARY KEY (content_id, asset_id)
);

-- LLM-generated ideas
CREATE TABLE ideas (
    id INTEGER PRIMARY KEY,
    prompt TEXT,
    response TEXT,
    model TEXT,
    tokens_used INTEGER,
    rating INTEGER,  -- 1-5 user rating
    converted_to_content_id INTEGER REFERENCES content(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Track published content
CREATE TABLE publications (
    id INTEGER PRIMARY KEY,
    content_id INTEGER REFERENCES content(id),
    platform TEXT NOT NULL,  -- youtube, tiktok, instagram
    post_id TEXT,            -- Platform-specific ID
    post_url TEXT,
    status TEXT DEFAULT 'pending',  -- pending, published, failed, scheduled
    scheduled_for TIMESTAMP,
    published_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_content_status ON content(status);
CREATE INDEX idx_content_scheduled ON content(scheduled_date);
CREATE INDEX idx_assets_type ON assets(asset_type);
CREATE INDEX idx_shots_list ON shots(shot_list_id);
CREATE INDEX idx_shot_lists_script ON shot_lists(script_id);
CREATE INDEX idx_publications_content ON publications(content_id);
CREATE INDEX idx_publications_platform ON publications(platform);
```

---

## Development Plan

### Phase 1: Core Foundation ✅

- [x] Project setup (pyproject.toml, structure)
- [x] Database schema and migrations
- [x] Configuration system
- [x] Basic content CRUD commands
- [x] Rich output formatting

### Phase 2: Asset Management ✅

- [x] Asset registration (file scanning)
- [x] Tagging system
- [x] Asset search (tags, type, metadata)
- [x] Content-asset linking

### Phase 3: Production Tools ✅

- [x] Script management with versioning
- [x] Shot list creation and management
- [x] Calendar view for scheduling
- [x] Status workflow tracking

### Phase 4: LLM Integration

- [x] OpenRouter service implementation (`services/llm.py`)
- [x] Panic command for quick idea generation
- [x] Customizable prompts via `prompts.toml`
- [x] Idea-to-content conversion (interactive)
- [ ] Idea generation commands (`bmc ideas`)
- [ ] Brainstorming mode
- [ ] Token usage tracking

### Phase 5: Publishing Integration

- [ ] YouTube publisher (OAuth, upload, scheduling)
- [ ] Instagram publisher (Graph API, Reels)
- [ ] Unified publish command
- [ ] Publication status tracking

### Phase 6: Polish

- [ ] Full-text search (SQLite FTS5)
- [ ] Export functions (markdown, json)
- [ ] Shell completions
- [ ] Error handling improvements
- [ ] Documentation

---

## Future Expansion

- **TikTok Publishing** - Playwright-based browser automation with session persistence
- **TUI Mode** - Full terminal UI using `textual` for visual calendar/kanban
- **DaVinci Resolve Integration** - Export EDLs, import project metadata
- **Analytics Sync** - Pull view counts, engagement from each platform
- **Template System** - Script templates, shot list presets
- **Analytics Dashboard** - Track content performance across platforms
- **Multi-channel Support** - Manage multiple creator accounts per platform
- **Collaboration** - Git-like sync for team workflows
- **Thumbnail Generation** - LLM-suggested thumbnails via image gen API

---

## Quick Start Implementation

```python
# src/bmcforge/cli/main.py
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="bmc",
    help="BMCForge: Video content management for creators"
)
console = Console()

# Import and register command groups
from . import content, assets, scripts, shots, ideas, publish, config

app.add_typer(content.app, name="content")
app.add_typer(assets.app, name="assets")
app.add_typer(scripts.app, name="scripts")
app.add_typer(shots.app, name="shots")
app.add_typer(ideas.app, name="ideas")
app.add_typer(publish.app, name="publish")
app.add_typer(config.app, name="config")

@app.command()
def status():
    """Show overview of content pipeline."""
    table = Table(title="Content Pipeline")
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right")

    statuses = [
        ("Ideas", 12),
        ("Scripted", 3),
        ("Filming", 1),
        ("Editing", 2),
        ("Scheduled", 4),
    ]

    for status, count in statuses:
        table.add_row(status, str(count))

    console.print(table)

if __name__ == "__main__":
    app()
```

---

## Dependencies

```toml
[project.dependencies]
typer = ">=0.9.0"
rich = ">=13.0.0"
httpx = ">=0.25.0"
pendulum = ">=3.0.0"
tomli-w = ">=1.0.0"  # tomllib is built-in for Python 3.12+

[project.optional-dependencies]
publishing = [
    "google-api-python-client>=2.0.0",
    "google-auth-oauthlib>=1.0.0",
]
tiktok = [
    "playwright>=1.40.0",
]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
]
```

---

## Requirements

- Python 3.12+
- SQLite 3.35+ (for JSON support)

## License

MIT
