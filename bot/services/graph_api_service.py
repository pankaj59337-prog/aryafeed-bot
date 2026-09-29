"""Official Meta Instagram Graph API Publishing Engine.

Provides zero-ban-risk Reels publishing via official Graph API endpoints:
1. Video hosted statically on Render (/media/<filename>)
2. Container creation (POST /{ig_user_id}/media?media_type=REELS)
3. Status polling (GET /{creation_id}?fields=status_code)
4. Publishing (POST /{ig_user_id}/media_publish?creation_id=...)
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
import httpx

from bot.utils.config import config

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v20.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class MetaGraphAPIService:
    """Zero-Ban-Risk Instagram Graph API Reels Publisher."""

    def __init__(self):
        self.public_media_dir = config.output_dir
        self.public_media_dir.mkdir(parents=True, exist_ok=True)

    def get_public_base_url(self) -> str:
        """Retrieve Render public web service URL."""
        return os.environ.get("RENDER_EXTERNAL_URL", "https://insta-reel-maker-bot.onrender.com").rstrip("/")

    async def verify_credentials(self, account_id: str, access_token: str) -> Dict[str, Any]:
        """Verify Instagram Business Account ID and Access Token."""
        url = f"{GRAPH_BASE_URL}/{account_id}"
        params = {
            "fields": "id,username,name,profile_picture_url",
            "access_token": access_token.strip(),
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, params=params)
                data = res.json()
                if res.status_code == 200 and "username" in data:
                    return {
                        "valid": True,
                        "account_id": data.get("id"),
                        "username": data.get("username"),
                        "name": data.get("name"),
                    }
                err = data.get("error", {}).get("message", res.text)
                return {"valid": False, "error": err}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def publish_reel(
        self,
        video_path: Path,
        caption: str,
        account_id: str,
        access_token: str,
    ) -> Dict[str, Any]:
        """Publish 1080x1920 MP4 reel via official Meta Graph API."""
        if not video_path.exists():
            return {"success": False, "error": f"Video file not found at {video_path}"}

        # 1. Ensure video is in public media directory for Render static serving
        filename = video_path.name
        dest_file = self.public_media_dir / filename
        if video_path.resolve() != dest_file.resolve():
            shutil.copy2(video_path, dest_file)

        base_url = self.get_public_base_url()
        public_video_url = f"{base_url}/media/{filename}"
        logger.info(f"[GraphAPI] Public video URL: {public_video_url}")

        clean_token = access_token.strip()
        clean_account_id = account_id.strip()

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Create Media Container
            container_url = f"{GRAPH_BASE_URL}/{clean_account_id}/media"
            container_payload = {
                "media_type": "REELS",
                "video_url": public_video_url,
                "caption": caption,
                "access_token": clean_token,
            }

            logger.info(f"[GraphAPI] Creating Reels container on account {clean_account_id}...")
            res = await client.post(container_url, data=container_payload)
            init_data = res.json()

            if res.status_code != 200 or "id" not in init_data:
                err_msg = init_data.get("error", {}).get("message", res.text)
                logger.error(f"[GraphAPI] Container creation failed: {err_msg}")
                return {"success": False, "error": f"Graph API Container Error: {err_msg}"}

            creation_id = init_data["id"]
            logger.info(f"[GraphAPI] Reels container created: {creation_id}. Polling status...")

            # Step 2: Poll container status until FINISHED
            status_url = f"{GRAPH_BASE_URL}/{creation_id}"
            status_params = {
                "fields": "status_code,status",
                "access_token": clean_token,
            }

            max_polls = 24  # 24 * 5s = 120 seconds max
            ready = False
            for poll in range(max_polls):
                await asyncio.sleep(5)
                poll_res = await client.get(status_url, params=status_params)
                if poll_res.status_code == 200:
                    status_info = poll_res.json()
                    status_code = status_info.get("status_code", "").upper()
                    logger.info(f"[GraphAPI] Poll {poll+1}/{max_polls}: status_code={status_code}")

                    if status_code == "FINISHED":
                        ready = True
                        break
                    elif status_code in ("ERROR", "EXPIRED"):
                        return {
                            "success": False,
                            "error": f"Meta processing failed with status: {status_code}",
                        }

            if not ready:
                return {
                    "success": False,
                    "error": "Timeout waiting for Meta to download and process the video reel.",
                }

            # Step 3: Publish container
            publish_url = f"{GRAPH_BASE_URL}/{clean_account_id}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": clean_token,
            }

            logger.info(f"[GraphAPI] Publishing container {creation_id}...")
            pub_res = await client.post(publish_url, data=publish_payload)
            pub_data = pub_res.json()

            if pub_res.status_code != 200 or "id" not in pub_data:
                err_msg = pub_data.get("error", {}).get("message", pub_res.text)
                logger.error(f"[GraphAPI] Media publish failed: {err_msg}")
                return {"success": False, "error": f"Graph API Publish Error: {err_msg}"}

            media_id = pub_data["id"]
            logger.info(f"[GraphAPI] Successfully published media ID: {media_id}")

            # Step 4: Fetch published permalink
            permalink_url = f"{GRAPH_BASE_URL}/{media_id}"
            p_res = await client.get(
                permalink_url,
                params={"fields": "permalink,shortcode", "access_token": clean_token},
            )
            permalink = None
            if p_res.status_code == 200:
                p_data = p_res.json()
                permalink = p_data.get("permalink")

            return {
                "success": True,
                "media_id": media_id,
                "url": permalink or f"https://www.instagram.com/p/{media_id}/",
                "method": "official_meta_graph_api",
            }


graph_api_service = MetaGraphAPIService()
