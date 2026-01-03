"""Database management for BMCForge."""

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from .config import ensure_app_dir

DB_PATH = Path.home() / ".bmcforge" / "bmcforge.db"

SCHEMA = """
-- Core content items (videos, posts, etc.)
CREATE TABLE IF NOT EXISTS content (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'idea',
    content_type TEXT DEFAULT 'video',
    scheduled_date DATE,
    publish_date DATE,
    platform TEXT,
    script_id INTEGER REFERENCES scripts(id),
    shot_list_id INTEGER REFERENCES shot_lists(id),
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scripts with versioning
CREATE TABLE IF NOT EXISTS scripts (
    id INTEGER PRIMARY KEY,
    content_id INTEGER REFERENCES content(id),
    version INTEGER DEFAULT 1,
    body TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Shot lists (linked to scripts, not content directly)
CREATE TABLE IF NOT EXISTS shot_lists (
    id INTEGER PRIMARY KEY,
    script_id INTEGER REFERENCES scripts(id),
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shots (
    id INTEGER PRIMARY KEY,
    shot_list_id INTEGER REFERENCES shot_lists(id),
    sequence INTEGER,
    description TEXT NOT NULL,
    shot_type TEXT,
    duration_estimate INTEGER,
    location TEXT,
    notes TEXT,
    completed BOOLEAN DEFAULT FALSE
);

-- Asset registry (doesn't copy files, just tracks them)
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    asset_type TEXT NOT NULL,
    file_type TEXT,
    file_size INTEGER,
    duration REAL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tags for assets
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    category TEXT
);

CREATE TABLE IF NOT EXISTS asset_tags (
    asset_id INTEGER REFERENCES assets(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (asset_id, tag_id)
);

-- Link assets to content
CREATE TABLE IF NOT EXISTS content_assets (
    content_id INTEGER REFERENCES content(id) ON DELETE CASCADE,
    asset_id INTEGER REFERENCES assets(id) ON DELETE CASCADE,
    usage_type TEXT,
    timestamp_start REAL,
    notes TEXT,
    PRIMARY KEY (content_id, asset_id)
);

-- LLM-generated ideas
CREATE TABLE IF NOT EXISTS ideas (
    id INTEGER PRIMARY KEY,
    prompt TEXT,
    response TEXT,
    model TEXT,
    tokens_used INTEGER,
    rating INTEGER,
    converted_to_content_id INTEGER REFERENCES content(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Track published content
CREATE TABLE IF NOT EXISTS publications (
    id INTEGER PRIMARY KEY,
    content_id INTEGER REFERENCES content(id),
    platform TEXT NOT NULL,
    post_id TEXT,
    post_url TEXT,
    status TEXT DEFAULT 'pending',
    scheduled_for TIMESTAMP,
    published_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_content_status ON content(status);
CREATE INDEX IF NOT EXISTS idx_content_scheduled ON content(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_shots_list ON shots(shot_list_id);
CREATE INDEX IF NOT EXISTS idx_shot_lists_script ON shot_lists(script_id);
CREATE INDEX IF NOT EXISTS idx_publications_content ON publications(content_id);
CREATE INDEX IF NOT EXISTS idx_publications_platform ON publications(platform);
"""

MIGRATIONS = [
    # Migration 1: Add script_id to shot_lists if it doesn't exist
    """
    -- Check if we need to migrate shot_lists from content_id to script_id
    -- This handles the schema change where shots are now linked to scripts
    """,
]


def get_db_path() -> Path:
    """Get the database file path."""
    return DB_PATH


def init_db() -> None:
    """Initialize the database with schema."""
    ensure_app_dir()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()

    # Run migrations
    _run_migrations(conn)

    conn.close()


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Run database migrations for schema changes."""
    cursor = conn.cursor()

    # Clean up any partial migration state
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shot_lists_new'")
    if cursor.fetchone():
        cursor.execute("DROP TABLE shot_lists_new")
        conn.commit()

    # Check if shot_lists has old schema (content_id instead of script_id)
    cursor.execute("PRAGMA table_info(shot_lists)")
    columns = {row[1] for row in cursor.fetchall()}

    if "content_id" in columns and "script_id" not in columns:
        # Disable foreign keys for migration
        cursor.execute("PRAGMA foreign_keys = OFF")

        # Migration: shot_lists content_id -> script_id
        cursor.executescript("""
            -- Create new table with correct schema
            CREATE TABLE shot_lists_new (
                id INTEGER PRIMARY KEY,
                script_id INTEGER REFERENCES scripts(id),
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Migrate data: link shot_lists to scripts via content
            INSERT INTO shot_lists_new (id, script_id, name, created_at)
            SELECT sl.id, s.id, sl.name, sl.created_at
            FROM shot_lists sl
            LEFT JOIN scripts s ON sl.content_id = s.content_id;

            -- Drop old table and rename new one
            DROP TABLE shot_lists;
            ALTER TABLE shot_lists_new RENAME TO shot_lists;

            -- Recreate index
            CREATE INDEX IF NOT EXISTS idx_shot_lists_script ON shot_lists(script_id);
        """)
        conn.commit()

        # Re-enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()


def get_connection() -> sqlite3.Connection:
    """Get a database connection, initializing if needed."""
    needs_init = not DB_PATH.exists()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    if needs_init:
        conn.executescript(SCHEMA)
        conn.commit()

    # Always check for migrations
    _run_migrations(conn)

    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
