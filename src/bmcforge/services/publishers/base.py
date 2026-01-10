"""Base publisher interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PublishStatus(str, Enum):
    """Status of a publication."""

    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    PUBLISHED = "published"
    SCHEDULED = "scheduled"
    FAILED = "failed"


@dataclass
class PublishResult:
    """Result of a publish operation."""

    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error: Optional[str] = None
    status: PublishStatus = PublishStatus.PENDING


class Publisher(ABC):
    """Abstract base class for platform publishers."""

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the platform.

        Returns True if authentication is successful.
        """
        pass

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        pass

    @abstractmethod
    def upload(
        self,
        file_path: str,
        title: str,
        description: str,
        tags: list[str],
        scheduled_time: Optional[str] = None,
    ) -> PublishResult:
        """Upload content to the platform.

        Args:
            file_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of tags/keywords
            scheduled_time: Optional ISO 8601 datetime for scheduled publishing

        Returns:
            PublishResult with success status and post details
        """
        pass
