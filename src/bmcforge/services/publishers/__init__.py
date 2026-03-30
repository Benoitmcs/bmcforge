"""Publishers for various platforms."""

from .base import Publisher, PublishResult, PublishStatus
from .youtube import YouTubePublisher

__all__ = [
    "Publisher",
    "PublishResult",
    "PublishStatus",
    "YouTubePublisher",
]

# Optional Instagram publisher (requires httpx)
try:
    from .instagram import InstagramPublisher

    __all__.append("InstagramPublisher")
except ImportError:
    pass
