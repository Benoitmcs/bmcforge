"""Instagram publisher using Meta Graph API."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from .base import Publisher, PublishResult, PublishStatus

# Instagram API dependencies are optional
try:
    import httpx

    INSTAGRAM_AVAILABLE = True
except ImportError:
    httpx = None  # type: ignore
    INSTAGRAM_AVAILABLE = False

if TYPE_CHECKING:
    import httpx

# Default paths
APP_DIR = Path.home() / ".bmcforge"
TOKEN_PATH = APP_DIR / "instagram_token.json"

# Instagram Graph API base URLs (v24.0 released October 2025)
# Use graph.instagram.com for IGAA tokens, graph.facebook.com for EAA tokens
INSTAGRAM_API_BASE = "https://graph.instagram.com/v24.0"
FACEBOOK_API_BASE = "https://graph.facebook.com/v24.0"

# Required permissions for content publishing
REQUIRED_SCOPES = [
    "instagram_basic",
    "instagram_content_publish",
    "pages_read_engagement",
    "pages_show_list",
]


class InstagramPublisher(Publisher):
    """Instagram publisher using Meta Graph API for Reels."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Initialize the Instagram publisher.

        Args:
            access_token: Long-lived access token for Instagram Graph API.
            user_id: Instagram Business/Creator account user ID.
        """
        if not INSTAGRAM_AVAILABLE:
            raise ImportError(
                "Instagram publishing requires httpx. "
                "Install with: pip install httpx"
            )

        self._access_token = access_token
        self._user_id = user_id
        self._client: Optional[httpx.Client] = None
        self._api_base: Optional[str] = None

    def _get_api_base(self) -> str:
        """Get the appropriate API base URL based on token type."""
        if self._api_base:
            return self._api_base
        # IGAA tokens use graph.instagram.com, EAA tokens use graph.facebook.com
        if self._access_token and self._access_token.startswith("IGAA"):
            self._api_base = INSTAGRAM_API_BASE
        else:
            self._api_base = FACEBOOK_API_BASE
        return self._api_base

    def _load_credentials(self) -> bool:
        """Load credentials from stored token file."""
        if TOKEN_PATH.exists():
            try:
                with open(TOKEN_PATH) as f:
                    data = json.load(f)
                    self._access_token = data.get("access_token")
                    self._user_id = data.get("user_id")
                    return bool(self._access_token and self._user_id)
            except Exception:
                return False
        return False

    def _save_credentials(self) -> None:
        """Save credentials to token file."""
        APP_DIR.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_PATH, "w") as f:
            json.dump(
                {
                    "access_token": self._access_token,
                    "user_id": self._user_id,
                },
                f,
            )

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=300.0)  # 5 min timeout for uploads
        return self._client

    def authenticate(self) -> bool:
        """Authenticate with Instagram Graph API.

        For Instagram, authentication is done by providing a long-lived
        access token obtained from Meta Developer Console.

        Returns:
            True if credentials are valid
        """
        # Try loading stored credentials first
        if not self._access_token or not self._user_id:
            self._load_credentials()

        if not self._access_token or not self._user_id:
            raise ValueError(
                "Instagram credentials not configured.\n"
                "Set access_token and user_id via:\n"
                "  bmc config set instagram.access_token YOUR_TOKEN\n"
                "  bmc config set instagram.user_id YOUR_USER_ID"
            )

        # Validate token by fetching user info
        client = self._get_client()
        response = client.get(
            f"{self._get_api_base()}/{self._user_id}",
            params={
                "fields": "id,username",
                "access_token": self._access_token,
            },
        )

        if response.status_code != 200:
            error = response.json().get("error", {})
            raise ValueError(
                f"Invalid Instagram credentials: {error.get('message', 'Unknown error')}"
            )

        # Save valid credentials
        self._save_credentials()
        return True

    def is_authenticated(self) -> bool:
        """Check if currently authenticated with valid credentials."""
        if not self._access_token or not self._user_id:
            if not self._load_credentials():
                return False

        try:
            client = self._get_client()
            response = client.get(
                f"{self._get_api_base()}/{self._user_id}",
                params={
                    "fields": "id",
                    "access_token": self._access_token,
                },
            )
            return response.status_code == 200
        except Exception:
            return False

    def revoke(self) -> bool:
        """Remove stored credentials.

        Note: This doesn't revoke the token on Meta's servers,
        just removes local storage. To fully revoke, user should
        remove app access in Facebook settings.

        Returns:
            True if credentials were removed
        """
        if TOKEN_PATH.exists():
            TOKEN_PATH.unlink()
            self._access_token = None
            self._user_id = None
            if self._client:
                self._client.close()
                self._client = None
            return True
        return False

    def upload(
        self,
        file_path: str,
        title: str,
        description: str,
        tags: list[str],
        scheduled_time: Optional[str] = None,
        video_url: Optional[str] = None,
        cover_url: Optional[str] = None,
        share_to_feed: bool = True,
    ) -> PublishResult:
        """Upload a video as an Instagram Reel.

        Instagram requires videos to be accessible via public URL.
        You can either:
        1. Provide video_url pointing to a publicly accessible video
        2. Provide file_path and the video will be uploaded directly
           (requires the video to be under 1GB)

        Args:
            file_path: Path to the video file (used if video_url not provided)
            title: Not used for Instagram (included for interface compatibility)
            description: Caption for the Reel (max 2200 characters)
            tags: List of hashtags (will be appended to description)
            scheduled_time: Not currently supported for Reels
            video_url: Public URL to the video file (optional)
            cover_url: Public URL to custom thumbnail (optional)
            share_to_feed: Whether to also share to main feed (default True)

        Returns:
            PublishResult with media ID and URL on success
        """
        if not self._access_token or not self._user_id:
            try:
                self.authenticate()
            except Exception as e:
                return PublishResult(
                    success=False,
                    error=f"Authentication failed: {e}",
                    status=PublishStatus.FAILED,
                )

        # Build caption with hashtags
        caption = description[:2200] if description else ""
        if tags:
            hashtags = " ".join(f"#{tag.strip('#')}" for tag in tags[:30])
            # Ensure we don't exceed caption limit
            if len(caption) + len(hashtags) + 2 <= 2200:
                caption = f"{caption}\n\n{hashtags}" if caption else hashtags

        client = self._get_client()

        try:
            # Step 1: Create media container
            container_params = {
                "media_type": "REELS",
                "caption": caption,
                "share_to_feed": str(share_to_feed).lower(),
                "access_token": self._access_token,
            }

            # Use video_url if provided, otherwise use direct upload
            if video_url:
                container_params["video_url"] = video_url
            else:
                # For direct upload, we use the resumable upload flow
                video_path = Path(file_path).expanduser()
                if not video_path.exists():
                    return PublishResult(
                        success=False,
                        error=f"Video file not found: {file_path}",
                        status=PublishStatus.FAILED,
                    )

                # Initialize resumable upload session
                init_response = client.post(
                    f"{self._get_api_base()}/{self._user_id}/media",
                    params={
                        "media_type": "REELS",
                        "upload_type": "resumable",
                        "access_token": self._access_token,
                    },
                )

                if init_response.status_code != 200:
                    error = init_response.json().get("error", {})
                    return PublishResult(
                        success=False,
                        error=f"Failed to initialize upload: {error.get('message', 'Unknown error')}",
                        status=PublishStatus.FAILED,
                    )

                init_data = init_response.json()
                upload_url = init_data.get("uri")
                container_id = init_data.get("id")

                if not upload_url:
                    return PublishResult(
                        success=False,
                        error="No upload URL received from Instagram",
                        status=PublishStatus.FAILED,
                    )

                # Upload the video file
                file_size = video_path.stat().st_size
                with open(video_path, "rb") as video_file:
                    upload_response = client.post(
                        upload_url,
                        headers={
                            "Authorization": f"OAuth {self._access_token}",
                            "offset": "0",
                            "file_size": str(file_size),
                        },
                        content=video_file.read(),
                    )

                if upload_response.status_code not in (200, 201):
                    return PublishResult(
                        success=False,
                        error=f"Video upload failed: {upload_response.text}",
                        status=PublishStatus.FAILED,
                    )

                # Now update the container with caption
                update_response = client.post(
                    f"{self._get_api_base()}/{container_id}",
                    params={
                        "caption": caption,
                        "share_to_feed": str(share_to_feed).lower(),
                        "access_token": self._access_token,
                    },
                )

                # Wait for processing and publish
                return self._wait_and_publish(container_id, client)

            # For URL-based upload
            if cover_url:
                container_params["cover_url"] = cover_url

            response = client.post(
                f"{self._get_api_base()}/{self._user_id}/media",
                params=container_params,
            )

            if response.status_code != 200:
                error = response.json().get("error", {})
                return PublishResult(
                    success=False,
                    error=f"Failed to create media container: {error.get('message', 'Unknown error')}",
                    status=PublishStatus.FAILED,
                )

            container_id = response.json().get("id")
            if not container_id:
                return PublishResult(
                    success=False,
                    error="No container ID received from Instagram",
                    status=PublishStatus.FAILED,
                )

            return self._wait_and_publish(container_id, client)

        except httpx.TimeoutException:
            return PublishResult(
                success=False,
                error="Request timed out. The video may still be processing.",
                status=PublishStatus.FAILED,
            )
        except Exception as e:
            return PublishResult(
                success=False,
                error=f"Upload failed: {e}",
                status=PublishStatus.FAILED,
            )

    def _wait_and_publish(
        self,
        container_id: str,
        client: httpx.Client,
        max_wait: int = 300,
        poll_interval: int = 5,
    ) -> PublishResult:
        """Wait for video processing and publish.

        Args:
            container_id: The media container ID
            client: HTTP client
            max_wait: Maximum seconds to wait for processing
            poll_interval: Seconds between status checks

        Returns:
            PublishResult with final status
        """
        # Step 2: Wait for video processing
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status_response = client.get(
                f"{self._get_api_base()}/{container_id}",
                params={
                    "fields": "status_code,status",
                    "access_token": self._access_token,
                },
            )

            if status_response.status_code != 200:
                error = status_response.json().get("error", {})
                return PublishResult(
                    success=False,
                    error=f"Failed to check status: {error.get('message', 'Unknown error')}",
                    status=PublishStatus.FAILED,
                )

            status_data = status_response.json()
            status_code = status_data.get("status_code")

            if status_code == "FINISHED":
                break
            elif status_code == "ERROR":
                return PublishResult(
                    success=False,
                    error=f"Video processing failed: {status_data.get('status', 'Unknown error')}",
                    status=PublishStatus.FAILED,
                )
            elif status_code in ("EXPIRED", "CANCELLED"):
                return PublishResult(
                    success=False,
                    error=f"Upload {status_code.lower()}",
                    status=PublishStatus.FAILED,
                )

            time.sleep(poll_interval)
        else:
            return PublishResult(
                success=False,
                error=f"Video processing timed out after {max_wait} seconds",
                status=PublishStatus.PROCESSING,
            )

        # Step 3: Publish the media
        publish_response = client.post(
            f"{self._get_api_base()}/{self._user_id}/media_publish",
            params={
                "creation_id": container_id,
                "access_token": self._access_token,
            },
        )

        if publish_response.status_code != 200:
            error = publish_response.json().get("error", {})
            return PublishResult(
                success=False,
                error=f"Failed to publish: {error.get('message', 'Unknown error')}",
                status=PublishStatus.FAILED,
            )

        media_id = publish_response.json().get("id")

        # Get the permalink
        permalink_response = client.get(
            f"{self._get_api_base()}/{media_id}",
            params={
                "fields": "permalink",
                "access_token": self._access_token,
            },
        )

        permalink = None
        if permalink_response.status_code == 200:
            permalink = permalink_response.json().get("permalink")

        return PublishResult(
            success=True,
            post_id=media_id,
            post_url=permalink,
            status=PublishStatus.PUBLISHED,
        )

    def get_upload_status(self, container_id: str) -> dict:
        """Get the processing status of an upload.

        Args:
            container_id: The media container ID

        Returns:
            Dictionary with status information
        """
        if not self._access_token:
            self._load_credentials()

        if not self._access_token:
            return {"error": "Not authenticated"}

        try:
            client = self._get_client()
            response = client.get(
                f"{self._get_api_base()}/{container_id}",
                params={
                    "fields": "status_code,status",
                    "access_token": self._access_token,
                },
            )

            if response.status_code != 200:
                return {"error": response.json().get("error", {}).get("message", "Unknown error")}

            data = response.json()
            return {
                "status_code": data.get("status_code"),
                "status": data.get("status"),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_account_info(self) -> dict:
        """Get Instagram account information.

        Returns:
            Dictionary with account info (username, followers, etc.)
        """
        if not self._access_token or not self._user_id:
            self._load_credentials()

        if not self._access_token or not self._user_id:
            return {"error": "Not authenticated"}

        try:
            client = self._get_client()
            response = client.get(
                f"{self._get_api_base()}/{self._user_id}",
                params={
                    "fields": "id,username,name,profile_picture_url,followers_count,follows_count,media_count",
                    "access_token": self._access_token,
                },
            )

            if response.status_code != 200:
                return {"error": response.json().get("error", {}).get("message", "Unknown error")}

            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def debug_token(self) -> dict:
        """Debug the access token to check its validity and permissions.

        Returns:
            Dictionary with token debug info
        """
        if not self._access_token:
            self._load_credentials()

        if not self._access_token:
            return {"error": "No access token configured"}

        try:
            client = self._get_client()
            # Use the debug_token endpoint
            response = client.get(
                f"{self._get_api_base()}/debug_token",
                params={
                    "input_token": self._access_token,
                    "access_token": self._access_token,
                },
            )

            if response.status_code != 200:
                error = response.json().get("error", {})
                return {
                    "error": error.get("message", "Unknown error"),
                    "hint": self._get_token_hint(),
                }

            data = response.json().get("data", {})
            return {
                "app_id": data.get("app_id"),
                "type": data.get("type"),
                "is_valid": data.get("is_valid"),
                "expires_at": data.get("expires_at"),
                "scopes": data.get("scopes", []),
                "granular_scopes": data.get("granular_scopes", []),
                "user_id": data.get("user_id"),
            }
        except Exception as e:
            return {"error": str(e), "hint": self._get_token_hint()}

    def _get_token_hint(self) -> str:
        """Return a hint based on token prefix."""
        if not self._access_token:
            return "No token configured"
        if self._access_token.startswith("IGAA"):
            return (
                "Token starts with 'IGAA' - this is an Instagram Basic Display API token. "
                "For Content Publishing, you need a Facebook Page Access Token instead. "
                "Use Graph API Explorer with your Facebook Page to get the correct token."
            )
        if self._access_token.startswith("EAA"):
            return "Token starts with 'EAA' - this is a Facebook token (correct type)."
        return "Unknown token format"

    def __del__(self):
        """Clean up HTTP client on deletion."""
        if self._client:
            self._client.close()


def check_instagram_available() -> bool:
    """Check if Instagram publishing dependencies are available."""
    return INSTAGRAM_AVAILABLE
