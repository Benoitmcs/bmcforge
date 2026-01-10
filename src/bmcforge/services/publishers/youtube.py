"""YouTube publisher using YouTube Data API v3."""

import json
import os
from pathlib import Path
from typing import Optional

from .base import Publisher, PublishResult, PublishStatus

# YouTube API dependencies are optional
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False

# YouTube API scopes
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Default paths
APP_DIR = Path.home() / ".bmcforge"
TOKEN_PATH = APP_DIR / "youtube_token.json"
DEFAULT_CREDENTIALS_PATH = APP_DIR / "youtube_client_secrets.json"

# YouTube category IDs
CATEGORY_IDS = {
    "film_animation": "1",
    "autos_vehicles": "2",
    "music": "10",
    "pets_animals": "15",
    "sports": "17",
    "short_movies": "18",
    "travel_events": "19",
    "gaming": "20",
    "videoblogging": "21",
    "people_blogs": "22",
    "comedy": "23",
    "entertainment": "24",
    "news_politics": "25",
    "howto_style": "26",
    "education": "27",
    "science_tech": "28",
    "nonprofits_activism": "29",
    "movies": "30",
    "anime_animation": "31",
    "action_adventure": "32",
    "classics": "33",
    "documentary": "35",
    "drama": "36",
    "family": "37",
    "foreign": "38",
    "horror": "39",
    "sci_fi_fantasy": "40",
    "thriller": "41",
    "shorts": "42",
    "shows": "43",
    "trailers": "44",
}


class YouTubePublisher(Publisher):
    """YouTube publisher using official YouTube Data API v3."""

    def __init__(self, credentials_path: Optional[str] = None):
        """Initialize the YouTube publisher.

        Args:
            credentials_path: Path to OAuth client secrets JSON file.
                            If not provided, uses default location.
        """
        if not YOUTUBE_AVAILABLE:
            raise ImportError(
                "YouTube publishing requires additional dependencies. "
                "Install with: pip install bmcforge[publishing]"
            )

        self.credentials_path = Path(
            credentials_path or DEFAULT_CREDENTIALS_PATH
        ).expanduser()
        self.youtube = None
        self._credentials = None

    def authenticate(self) -> bool:
        """Authenticate with YouTube using OAuth 2.0.

        Opens a browser for user authentication on first run,
        then uses stored token for subsequent runs.

        Returns:
            True if authentication is successful
        """
        creds = None

        # Load existing token if available
        if TOKEN_PATH.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
            except Exception:
                creds = None

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None

            if not creds:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"YouTube credentials file not found: {self.credentials_path}\n"
                        "Download from Google Cloud Console and save to this location."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(
                    port=8080,
                    prompt="consent",
                    success_message="Authentication successful! You can close this tab.",
                )

            # Save the token for future runs
            APP_DIR.mkdir(parents=True, exist_ok=True)
            with open(TOKEN_PATH, "w") as token_file:
                token_file.write(creds.to_json())

        self._credentials = creds
        self.youtube = build("youtube", "v3", credentials=creds)
        return True

    def is_authenticated(self) -> bool:
        """Check if currently authenticated with valid credentials."""
        if not TOKEN_PATH.exists():
            return False

        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            return creds.valid
        except Exception:
            return False

    def revoke(self) -> bool:
        """Revoke the current authentication token.

        Returns:
            True if revocation was successful
        """
        if TOKEN_PATH.exists():
            TOKEN_PATH.unlink()
            self.youtube = None
            self._credentials = None
            return True
        return False

    def upload(
        self,
        file_path: str,
        title: str,
        description: str,
        tags: list[str],
        scheduled_time: Optional[str] = None,
        category_id: str = "22",
        privacy: str = "private",
        made_for_kids: bool = False,
        notify_subscribers: bool = True,
    ) -> PublishResult:
        """Upload a video to YouTube.

        Args:
            file_path: Path to the video file
            title: Video title (max 100 characters)
            description: Video description (max 5000 characters)
            tags: List of tags (max 500 characters total)
            scheduled_time: ISO 8601 datetime for scheduled publishing
            category_id: YouTube category ID (default: "22" = People & Blogs)
            privacy: Privacy status: "private", "public", or "unlisted"
            made_for_kids: Whether the video is made for kids
            notify_subscribers: Whether to notify subscribers

        Returns:
            PublishResult with video ID and URL on success
        """
        if not self.youtube:
            try:
                self.authenticate()
            except Exception as e:
                return PublishResult(
                    success=False,
                    error=f"Authentication failed: {e}",
                    status=PublishStatus.FAILED,
                )

        # Validate file exists
        video_path = Path(file_path).expanduser()
        if not video_path.exists():
            return PublishResult(
                success=False,
                error=f"Video file not found: {file_path}",
                status=PublishStatus.FAILED,
            )

        # Truncate title and description if too long
        title = title[:100]
        description = description[:5000]

        # Build request body
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags[:500] if tags else [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }

        # Handle scheduled publishing
        if scheduled_time:
            body["status"]["privacyStatus"] = "private"
            body["status"]["publishAt"] = scheduled_time

        # Disable subscriber notification if requested
        if not notify_subscribers:
            body["status"]["publishAt"] = body["status"].get("publishAt")

        try:
            # Create media upload object with resumable upload
            media = MediaFileUpload(
                str(video_path),
                chunksize=1024 * 1024,  # 1MB chunks
                resumable=True,
            )

            # Create the insert request
            request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media,
                notifySubscribers=notify_subscribers,
            )

            # Execute with resumable upload
            response = None
            while response is None:
                status, response = request.next_chunk()

            video_id = response["id"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            return PublishResult(
                success=True,
                post_id=video_id,
                post_url=video_url,
                status=PublishStatus.SCHEDULED if scheduled_time else PublishStatus.PUBLISHED,
            )

        except HttpError as e:
            error_content = json.loads(e.content.decode("utf-8"))
            error_message = error_content.get("error", {}).get("message", str(e))
            return PublishResult(
                success=False,
                error=f"YouTube API error: {error_message}",
                status=PublishStatus.FAILED,
            )
        except Exception as e:
            return PublishResult(
                success=False,
                error=f"Upload failed: {e}",
                status=PublishStatus.FAILED,
            )

    def get_upload_status(self, video_id: str) -> dict:
        """Get the processing status of an uploaded video.

        Args:
            video_id: The YouTube video ID

        Returns:
            Dictionary with status information
        """
        if not self.youtube:
            self.authenticate()

        try:
            response = (
                self.youtube.videos()
                .list(part="status,processingDetails", id=video_id)
                .execute()
            )

            if not response.get("items"):
                return {"error": "Video not found"}

            video = response["items"][0]
            return {
                "upload_status": video.get("status", {}).get("uploadStatus"),
                "privacy_status": video.get("status", {}).get("privacyStatus"),
                "processing_status": video.get("processingDetails", {}).get(
                    "processingStatus"
                ),
                "processing_progress": video.get("processingDetails", {}).get(
                    "processingProgress", {}
                ),
            }
        except HttpError as e:
            return {"error": str(e)}


def check_youtube_available() -> bool:
    """Check if YouTube publishing dependencies are available."""
    return YOUTUBE_AVAILABLE
