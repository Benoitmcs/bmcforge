"""Data models for BMCForge."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class ContentStatus(str, Enum):
    """Status of content in the pipeline."""

    IDEA = "idea"
    SCRIPTED = "scripted"
    FILMING = "filming"
    EDITING = "editing"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"


class ContentType(str, Enum):
    """Type of content."""

    VIDEO = "video"
    SHORT = "short"
    POST = "post"
    REEL = "reel"


class AssetType(str, Enum):
    """Type of asset."""

    BROLL = "broll"
    SFX = "sfx"
    MUSIC = "music"
    GRAPHIC = "graphic"
    FOOTAGE = "footage"


class ShotType(str, Enum):
    """Type of shot."""

    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE = "close"
    BROLL = "broll"
    TALKING_HEAD = "talking_head"


class Platform(str, Enum):
    """Publishing platform."""

    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"


@dataclass
class Content:
    """A content item in the pipeline."""

    id: Optional[int] = None
    title: str = ""
    description: Optional[str] = None
    status: ContentStatus = ContentStatus.IDEA
    content_type: ContentType = ContentType.VIDEO
    scheduled_date: Optional[date] = None
    publish_date: Optional[date] = None
    platform: Optional[str] = None
    script_id: Optional[int] = None
    shot_list_id: Optional[int] = None
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row) -> "Content":
        """Create Content from a database row."""
        return cls(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=ContentStatus(row["status"]) if row["status"] else ContentStatus.IDEA,
            content_type=ContentType(row["content_type"]) if row["content_type"] else ContentType.VIDEO,
            scheduled_date=date.fromisoformat(row["scheduled_date"]) if row["scheduled_date"] else None,
            publish_date=date.fromisoformat(row["publish_date"]) if row["publish_date"] else None,
            platform=row["platform"],
            script_id=row["script_id"],
            shot_list_id=row["shot_list_id"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )


@dataclass
class Script:
    """A script for a content item."""

    id: Optional[int] = None
    content_id: Optional[int] = None
    version: int = 1
    body: str = ""
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    @property
    def word_count(self) -> int:
        """Calculate word count."""
        return len(self.body.split()) if self.body else 0


@dataclass
class Shot:
    """A shot in a shot list."""

    id: Optional[int] = None
    shot_list_id: Optional[int] = None
    sequence: int = 0
    description: str = ""
    shot_type: Optional[ShotType] = None
    duration_estimate: Optional[int] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    completed: bool = False


@dataclass
class Asset:
    """An asset in the registry."""

    id: Optional[int] = None
    name: str = ""
    file_path: str = ""
    asset_type: AssetType = AssetType.BROLL
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[float] = None
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None
    tags: list[str] = field(default_factory=list)


@dataclass
class Idea:
    """An LLM-generated idea."""

    id: Optional[int] = None
    prompt: str = ""
    response: str = ""
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    rating: Optional[int] = None
    converted_to_content_id: Optional[int] = None
    created_at: Optional[datetime] = None
