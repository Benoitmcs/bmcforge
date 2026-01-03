# BMCForge CLI Instructions

This document provides instructions for using BMCForge (`bmc`), a CLI tool for video content creators to manage content pipelines, organize assets, and generate ideas.

## Command Overview

| Command | Purpose |
|---------|---------|
| `bmc status` | Show pipeline overview |
| `bmc content` | Manage content items (videos, posts) |
| `bmc assets` | Register and tag media assets |
| `bmc scripts` | Create and version scripts |
| `bmc shots` | Manage shot lists |
| `bmc panic` | Quick LLM idea generation |
| `bmc ideas` | Full LLM brainstorming |
| `bmc publish` | Publish to platforms |
| `bmc config` | Configure settings |

---

## Content Management

### Add new content
```bash
bmc content add "<title>" [--type <type>] [--platform <platform>]
```
- `<title>`: Required. The content title in quotes.
- `--type`: Optional. Content type: `video`, `short`, `post`, `reel`. Default: `video`.
- `--platform`: Optional. Target platform: `youtube`, `instagram`, `tiktok`.

**Examples:**
```bash
bmc content add "10 Vim Tricks"
bmc content add "Quick CSS Tip" --type short --platform tiktok
```

### List content
```bash
bmc content list [--status <status>] [--upcoming]
```
- `--status`: Filter by status: `idea`, `scripted`, `filming`, `editing`, `scheduled`, `published`.
- `--upcoming`: Show content scheduled in the next 7 days.

**Examples:**
```bash
bmc content list
bmc content list --status scripted
bmc content list --upcoming
```

### Update content status
```bash
bmc content status <id> <new_status>
```
- `<id>`: Content ID (integer).
- `<new_status>`: New status: `idea`, `scripted`, `filming`, `editing`, `scheduled`, `published`.

**Example:**
```bash
bmc content status 1 filming
```

### Schedule content
```bash
bmc content schedule <id> <date>
```
- `<id>`: Content ID.
- `<date>`: Publish date in `YYYY-MM-DD` format.

**Example:**
```bash
bmc content schedule 1 2025-01-15
```

### Link asset to content
```bash
bmc content link-asset <content_id> <asset_id>
```

**Example:**
```bash
bmc content link-asset 1 42
```

### View calendar
```bash
bmc content calendar [--week]
```
- Default: Month view.
- `--week`: Show week view instead.

---

## Asset Management

### Add assets
```bash
bmc assets add <path> --type <type> [--recursive]
```
- `<path>`: File or directory path.
- `--type`: Required. Asset type: `broll`, `sfx`, `music`, `graphic`, `footage`.
- `--recursive`: For directories, add all files recursively.

**Examples:**
```bash
bmc assets add ~/Videos/broll/cityscape.mp4 --type broll
bmc assets add ~/Audio/sfx/ --type sfx --recursive
```

### Tag assets
```bash
bmc assets tag <asset_id> "<tag1>" "<tag2>" ...
```

**Example:**
```bash
bmc assets tag 1 "urban" "night" "cinematic"
```

### Remove tags
```bash
bmc assets untag <asset_id> "<tag>"
```

**Example:**
```bash
bmc assets untag 1 "night"
```

### Search assets
```bash
bmc assets search "<query>" [--type <type>] [--unused]
```
- `<query>`: Search by tags (space-separated).
- `--type`: Filter by asset type.
- `--unused`: Show assets not linked to any content.

**Examples:**
```bash
bmc assets search "urban cinematic"
bmc assets search --type broll
bmc assets search --unused
```

### List assets
```bash
bmc assets list [--type <type>]
```

**Example:**
```bash
bmc assets list --type sfx
```

---

## Scripts

### Create script
```bash
bmc scripts create <content_id>
```
Creates a new script for the specified content item.

**Example:**
```bash
bmc scripts create 1
```

### Edit script
```bash
bmc scripts edit <content_id>
```
Opens the script in `$EDITOR` (or configured editor). Creates a new version on save.

**Example:**
```bash
bmc scripts edit 1
```

### Show script
```bash
bmc scripts show <content_id>
```
Displays the current script content.

### View script history
```bash
bmc scripts history <content_id>
```
Shows all versions of the script.

---

## Shot Lists

Shot lists are linked to scripts, not content directly. Each script version has its own shot list.

### Add shot
```bash
bmc shots add <content_id> "<description>" [--type <type>] [--duration <seconds>]
```
- `--type`: Shot type: `wide`, `medium`, `close`, `broll`, `talking_head`.
- `--duration`: Estimated duration in seconds.

**Examples:**
```bash
bmc shots add 1 "Wide establishing shot of office" --type wide
bmc shots add 1 "Close-up of typing" --type close --duration 5
```

### List shots
```bash
bmc shots list <content_id> [--version <version>]
```
- Default: Shows shots for the latest script version.
- `--version`: Specify a script version number.

**Examples:**
```bash
bmc shots list 1
bmc shots list 1 --version 2
```

### List all shots
```bash
bmc shots all [--pending]
```
- `--pending`: Only show incomplete shots.

### Mark shot complete
```bash
bmc shots check <content_id> <shot_number> [--version <version>]
```

**Examples:**
```bash
bmc shots check 1 3
bmc shots check 1 3 --version 1
```

### Reorder shot
```bash
bmc shots reorder <content_id> <shot_number> <new_position>
```

**Example:**
```bash
bmc shots reorder 1 3 1
```

### Edit shot
```bash
bmc shots edit <content_id> <shot_number> --desc "<new_description>"
```

### Remove shot
```bash
bmc shots remove <content_id> <shot_number>
```

---

## Panic Mode (Quick LLM Ideas)

Generate video ideas that can be filmed and edited in under 2 hours. Choose ONE mode per run.

```bash
bmc panic --funny      # Generate a funny video idea
bmc panic --relevant   # Generate a timely, trending idea
bmc panic --interesting # Generate an educational idea
bmc panic --remake     # Remix 5 random existing scripts
```

The command displays the generated idea and prompts to save it as new content.

**Configuration:** Edit `~/.bmcforge/prompts.toml` to customize prompts and models.

---

## Idea Generation (LLM)

### Generate ideas
```bash
bmc ideas generate "<prompt>" [--from-content <id>]
```
- `--from-content`: Expand on an existing content item.

**Examples:**
```bash
bmc ideas generate "video ideas about neovim productivity"
bmc ideas generate --from-content 1
```

### Brainstorm
```bash
bmc ideas brainstorm "<topic>"
```
Generates multiple ideas on a topic.

**Example:**
```bash
bmc ideas brainstorm "coding tutorials"
```

### List saved ideas
```bash
bmc ideas list
```

### Rate an idea
```bash
bmc ideas rate <idea_id> <rating>
```
- `<rating>`: 1-5 stars.

**Example:**
```bash
bmc ideas rate 5 4
```

### Convert idea to content
```bash
bmc ideas convert <idea_id>
```
Creates a new content item from the idea.

### Interactive chat
```bash
bmc ideas chat
```
Opens conversational brainstorming mode.

---

## Publishing

### Authenticate platform
```bash
bmc publish auth <platform>
```
- `youtube`: Opens browser for OAuth.
- `instagram`: Guides through Meta developer setup.

**Examples:**
```bash
bmc publish auth youtube
bmc publish auth instagram
```

### Publish content
```bash
bmc publish <content_id> --platform <platform> [<platform2>...] [--schedule "<datetime>"]
```
- Multiple platforms can be specified.
- `--schedule`: ISO 8601 datetime for scheduled publishing.

**Examples:**
```bash
bmc publish 1 --platform youtube
bmc publish 1 --platform youtube instagram
bmc publish 1 --platform youtube --schedule "2025-01-15T10:00:00"
```

### Check publish status
```bash
bmc publish status <content_id>
```
Shows where content is published.

---

## Configuration

### Initialize configuration
```bash
bmc config init
```
First-time setup wizard.

### Set configuration value
```bash
bmc config set <key> "<value>"
```

**Common keys:**
- `api.openrouter_key`: OpenRouter API key for LLM features.
- `default_platform`: Default publishing platform.
- `broll_dir`: B-roll directory path.
- `sfx_dir`: Sound effects directory path.

**Examples:**
```bash
bmc config set api.openrouter_key "sk-..."
bmc config set default_platform youtube
bmc config set broll_dir ~/Videos/broll
```

### Show configuration
```bash
bmc config show
```

---

## Pipeline Status

```bash
bmc status
```
Shows an overview table of content by status (ideas, scripted, filming, editing, scheduled).

---

## Typical Workflows

### Starting a new video project
```bash
bmc content add "My Video Title" --type video --platform youtube
bmc scripts create 1
bmc scripts edit 1
bmc shots add 1 "Opening shot" --type wide
bmc shots add 1 "Main content" --type talking_head
```

### Finding and linking assets
```bash
bmc assets search "urban night"
bmc content link-asset 1 42
```

### Quick content idea when stuck
```bash
bmc panic --funny
# or
bmc panic --relevant
```

### Publishing workflow
```bash
bmc content status 1 editing
bmc content schedule 1 2025-01-20
bmc publish 1 --platform youtube instagram
```

---

## Important Notes

1. **Local-first**: All data is stored in `~/.bmcforge/bmcforge.db` (SQLite).
2. **Assets are not copied**: The asset registry tracks file paths, not copies.
3. **API key required**: LLM features (`panic`, `ideas`) require an OpenRouter API key.
4. **Shot lists follow scripts**: New script versions automatically copy the shot list.
5. **Content IDs**: Most commands use integer content IDs. Use `bmc content list` to find IDs.
