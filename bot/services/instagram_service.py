"""Instagram Reels Publishing & Account Management Service.

Provides:
1. Direct Local Reel Publishing via instagrapi (Session persistence & local upload)
2. Challenge / 2FA Handling
3. Auto-Posting Integration
"""
from __future__ import annotations

import asyncio
import logging
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional
from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword,
    TwoFactorRequired,
    ChallengeRequired,
    FeedbackRequired,
    LoginRequired
)

from database.db import db_manager

# Ensure moviepy has VideoFileClip for instagrapi compatibility
try:
    import moviepy
    if not hasattr(moviepy, "VideoFileClip"):
        from moviepy.editor import VideoFileClip
        moviepy.VideoFileClip = VideoFileClip
except Exception:
    pass

logger = logging.getLogger(__name__)

SESSION_DIR = Path("data/sessions")


class InstagramService:
    """Unified Instagram Publishing and Session Manager."""

    def __init__(self, session_dir: Path = SESSION_DIR):
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_path(self, chat_id: int) -> Path:
        return self.session_dir / f"instagram_{chat_id}.json"

    def _get_sync_session_path(self, chat_id: int) -> Path:
        return self.session_dir / f"audio_sync_{chat_id}.json"

    def _create_client(self) -> Client:
        cl = Client()
        cl.delay_range = [1, 3]
        return cl

    async def login_user(
        self,
        chat_id: int,
        username: str,
        password: str,
        verification_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Authenticate Instagram account, save session cookie file, and record in DB."""
        session_path = self._get_session_path(chat_id)
        cl = self._create_client()

        def _do_login():
            try:
                # If session exists, try loading it first
                if session_path.exists():
                    try:
                        cl.load_settings(session_path)
                    except Exception:
                        pass
                
                if verification_code:
                    cl.login(username, password, verification_code=verification_code)
                else:
                    cl.login(username, password)

                cl.dump_settings(session_path)
                user_info = cl.user_info(cl.user_id)
                return {
                    "success": True,
                    "username": username,
                    "full_name": user_info.full_name,
                    "pk": cl.user_id,
                }
            except BadPassword:
                return {"success": False, "error": "Invalid password. Please check your credentials."}
            except TwoFactorRequired:
                return {
                    "success": False,
                    "error": "Two-Factor Authentication (2FA) required. Run `/insta_2fa <code>` to verify.",
                    "requires_2fa": True
                }
            except ChallengeRequired:
                return {
                    "success": False,
                    "error": "Instagram security challenge required. Please open Instagram app on your phone, approve the login, and try again."
                }
            except FeedbackRequired as e:
                return {"success": False, "error": f"Instagram rate limit/feedback required: {e}"}
            except Exception as e:
                logger.exception(f"Instagram login failed: {e}")
                return {"success": False, "error": str(e)}

        result = await asyncio.to_thread(_do_login)
        if result.get("success"):
            await db_manager.save_instagram_account(
                chat_id=chat_id,
                username=username,
                session_file=str(session_path),
                auto_post=0
            )
            logger.info(f"Instagram user @{username} successfully connected for chat {chat_id}")
        return result

    async def login_with_sessionid(
        self,
        chat_id: int,
        sessionid: str
    ) -> Dict[str, Any]:
        """Authenticate using browser sessionid cookie, save session, and record in DB."""
        session_path = self._get_session_path(chat_id)
        cl = self._create_client()

        def _do_login():
            try:
                clean_sid = urllib.parse.unquote(sessionid.strip().strip('"').strip("'"))
                cl.login_by_sessionid(clean_sid)
                cl.dump_settings(session_path)
                username = cl.username
                user_info = cl.user_info(cl.user_id)
                return {
                    "success": True,
                    "username": username,
                    "full_name": user_info.full_name,
                    "pk": cl.user_id,
                }
            except Exception as e:
                logger.exception(f"Instagram session login failed: {e}")
                return {"success": False, "error": str(e)}

        result = await asyncio.to_thread(_do_login)
        if result.get("success"):
            await db_manager.save_instagram_account(
                chat_id=chat_id,
                username=result["username"],
                session_file=str(session_path),
                auto_post=0
            )
            logger.info(f"Instagram user @{result['username']} connected via sessionid for chat {chat_id}")
        return result

    async def login_sync_sessionid(
        self,
        chat_id: int,
        sessionid: str
    ) -> Dict[str, Any]:
        """Authenticate audio scouting account using browser sessionid cookie and save session."""
        session_path = self._get_sync_session_path(chat_id)
        cl = self._create_client()

        def _do_login():
            try:
                clean_sid = urllib.parse.unquote(sessionid.strip().strip('"').strip("'"))
                cl.login_by_sessionid(clean_sid)
                cl.dump_settings(session_path)
                username = cl.username
                user_info = cl.user_info(cl.user_id)
                return {
                    "success": True,
                    "username": username,
                    "full_name": user_info.full_name,
                    "pk": cl.user_id,
                }
            except Exception as e:
                logger.exception(f"Audio sync Instagram session login failed: {e}")
                return {"success": False, "error": str(e)}

        result = await asyncio.to_thread(_do_login)
        if result.get("success"):
            logger.info(f"Instagram audio scout user @{result['username']} connected via sessionid for chat {chat_id}")
        return result

    async def get_sync_client(self, chat_id: int) -> Optional[Client]:
        """Retrieve instagrapi Client for audio scouting (saved/liked reels).
        Prefers dedicated scout account (audio_sync_{chat_id}.json),
        falling back to regular authenticated client if not present.
        """
        sync_path = self._get_sync_session_path(chat_id)
        if sync_path.exists():
            cl = self._create_client()
            try:
                cl.load_settings(sync_path)
                return cl
            except Exception as e:
                logger.warning(f"Could not load audio sync session for {chat_id}: {e}")

        # Fallback to main client
        return await self.get_authenticated_client(chat_id)

    async def get_authenticated_client(self, chat_id: int) -> Optional[Client]:
        """Retrieve instagrapi Client with active session."""
        session_path = self._get_session_path(chat_id)
        acc = await db_manager.get_instagram_account(chat_id)
        if acc:
            session_path = Path(acc["session_file"])

        if not session_path.exists():
            return None

        cl = self._create_client()
        try:
            cl.load_settings(session_path)
            return cl
        except Exception as e:
            logger.warning(f"Could not load Instagram session for {chat_id}: {e}")
            return None

    # Alias for convenience
    get_client = get_authenticated_client

    async def get_graph_credentials(self, chat_id: int) -> Optional[Dict[str, str]]:
        """Check for official Graph API account ID and access token for the active account."""
        import os
        active = await db_manager.get_active_account(chat_id)
        if active and active.get("graph_account_id") and active.get("graph_token"):
            return {
                "account_id": active["graph_account_id"].strip(),
                "access_token": active["graph_token"].strip(),
                "username": active.get("username", "instagram"),
            }

        # User-specific DB credentials
        acct_id = await db_manager.get_setting(f"graph_account_{chat_id}")
        token = await db_manager.get_setting(f"graph_token_{chat_id}")
        username = await db_manager.get_setting(f"graph_user_{chat_id}")

        # Global DB or environment variables fallback
        if not (acct_id and token):
            acct_id = await db_manager.get_setting("graph_account_id") or os.environ.get("INSTAGRAM_GRAPH_ACCOUNT_ID")
            token = await db_manager.get_setting("graph_access_token") or os.environ.get("INSTAGRAM_GRAPH_ACCESS_TOKEN")
            username = await db_manager.get_setting("graph_username") or os.environ.get("INSTAGRAM_GRAPH_USERNAME")

        if acct_id and token:
            return {
                "account_id": acct_id.strip(),
                "access_token": token.strip(),
                "username": username or (active.get("username") if active else "aryafeed.in"),
            }
        return None

    async def set_graph_credentials(self, chat_id: int, account_id: str, access_token: str, username: Optional[str] = None) -> None:
        """Store official Graph API credentials."""
        await db_manager.set_setting(f"graph_account_{chat_id}", account_id.strip())
        await db_manager.set_setting(f"graph_token_{chat_id}", access_token.strip())
        if username:
            await db_manager.set_setting(f"graph_user_{chat_id}", username.strip())

    async def is_connected(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Check if an active Instagram account is linked (Graph API or instagrapi)."""
        active = await db_manager.get_active_account(chat_id)
        graph_creds = await self.get_graph_credentials(chat_id)
        if graph_creds:
            return {
                "username": graph_creds.get("username", active.get("username", "aryafeed.in") if active else "aryafeed.in"),
                "account_id": graph_creds.get("account_id"),
                "type": "meta_graph_api",
                "alias": active.get("alias", "aryafeed") if active else "aryafeed",
                "engine_type": active.get("engine_type", "aryafeed") if active else "aryafeed",
                "auto_post": active.get("auto_post", 1) if active else 1,
            }
        if active:
            s_file = Path(active["session_file"]) if active.get("session_file") else self._get_session_path(chat_id)
            if s_file.exists():
                return active

        # Auto-recover from existing session file on disk (resilient across DB resets / cloud redeploys)
        session_path = self._get_session_path(chat_id)
        if session_path.exists():
            try:
                username = "aryafeed.in"
                await db_manager.save_managed_account(
                    chat_id=chat_id,
                    alias="aryafeed",
                    username=username,
                    session_file=str(session_path),
                    auto_post=1,
                    engine_type="aryafeed",
                    set_active=True,
                )
                logger.info(f"[InstagramService] Auto-recovered active session for @{username} (chat {chat_id})")
                return await db_manager.get_active_account(chat_id)
            except Exception as e:
                logger.warning(f"[InstagramService] Failed to auto-recover session: {e}")
        return None

    async def switch_account(self, chat_id: int, target: str) -> Optional[Dict[str, Any]]:
        """Switch active account between Engine 1 (@night_thought_12) and Engine 2 (@aryafeed.in)."""
        return await db_manager.switch_active_account(chat_id, target)

    async def list_accounts(self, chat_id: int) -> List[Dict[str, Any]]:
        """List all accounts configured for this chat."""
        return await db_manager.list_managed_accounts(chat_id)

    async def get_active_account(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get currently active account."""
        return await db_manager.get_active_account(chat_id)

    async def set_autopost(self, chat_id: int, enabled: bool) -> bool:
        """Enable or disable automatic posting on reel creation."""
        acc = await self.is_connected(chat_id)
        if not acc:
            return False
        await db_manager.set_instagram_autopost(chat_id, enabled)
        return True

    async def logout(self, chat_id: int) -> bool:
        """Disconnect Instagram account and delete stored session file."""
        # Clear Graph credentials
        await db_manager.set_setting(f"graph_account_{chat_id}", "")
        await db_manager.set_setting(f"graph_token_{chat_id}", "")
        session_path = self._get_session_path(chat_id)
        if session_path.exists():
            try:
                session_path.unlink()
            except Exception:
                pass
        await db_manager.delete_instagram_account(chat_id)
        return True

    async def upload_reel(
        self,
        chat_id: int,
        video_path: Path,
        caption: str = ""
    ) -> Dict[str, Any]:
        """Upload a 1080x1920 MP4 reel directly to user's Instagram feed/reels."""
        if not video_path.exists():
            return {"success": False, "error": f"Video file not found: {video_path}"}

        # 1. First priority: Official Meta Graph API (Zero Ban Risk)
        from bot.services.graph_api_service import graph_api_service
        graph_creds = await self.get_graph_credentials(chat_id)
        if graph_creds:
            logger.info(f"[InstagramService] Publishing via official Meta Graph API (Account: {graph_creds['account_id']})")
            graph_res = await graph_api_service.publish_reel(
                video_path=video_path,
                caption=caption,
                account_id=graph_creds["account_id"],
                access_token=graph_creds["access_token"],
            )
            if graph_res.get("success"):
                return graph_res
            logger.warning(f"[InstagramService] Meta Graph API returned error: {graph_res.get('error')}. Falling back to instagrapi...")

        # 2. Second priority: Fallback to instagrapi session
        cl = await self.get_authenticated_client(chat_id)
        if not cl:
            return {
                "success": False,
                "error": "Instagram account not connected. Use `/insta_graph account_id access_token` or `/insta_login`."
            }

        # Generate custom thumbnail at 2.0s using FFmpeg to avoid MoviePy thumbnailer
        thumb_path = video_path.with_suffix(".thumb.jpg")
        if not thumb_path.exists():
            try:
                import subprocess
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-ss", "00:00:02",
                        "-i", str(video_path),
                        "-vframes", "1",
                        "-q:v", "2",
                        str(thumb_path),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10,
                )
            except Exception as e:
                logger.warning(f"Could not generate ffmpeg thumbnail: {e}")

        def _do_upload():
            try:
                logger.info(f"Uploading clip {video_path} to Instagram...")
                media = cl.clip_upload(
                    path=str(video_path),
                    caption=caption,
                    thumbnail=str(thumb_path) if thumb_path.exists() else None,
                )
                media_code = getattr(media, "code", None)
                media_id = getattr(media, "id", None)
                post_url = f"https://www.instagram.com/reel/{media_code}/" if media_code else None
                return {
                    "success": True,
                    "media_id": media_id,
                    "code": media_code,
                    "url": post_url
                }
            except LoginRequired:
                return {"success": False, "error": "Instagram session expired. Please re-login with /insta_login."}
            except Exception as e:
                logger.exception(f"Failed to upload reel to Instagram: {e}")
                return {"success": False, "error": str(e)}

        return await asyncio.to_thread(_do_upload)


# Singleton instance
instagram_service = InstagramService()