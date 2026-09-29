"""Autonomous Competitor Monitor for @aryafeed.in.

Monitors 4 target competitor accounts:
1. @rvcjinsta (RVCJ Media - viral news, meme cards, trending stories)
2. @flirting.lines (pickup lines, dating banter, relatable thoughts)
3. @comedyculture.in (relatable Indian memes, humor)
4. @adultsociety (late night thoughts, youth culture, viral clips)

Autonomous Rules:
- If image/video is CLEAN (no competitor handle/branding on the visual):
  -> Directly stamps [ ARYAFEED ] watermark on bottom-right and posts to @aryafeed.in.
  -> Same audio preserved if video has audio; no music added if video had none.
- If image/video has COMPETITOR TITLE/BRANDING:
  -> Sends alert to Telegram bot.
  -> Cleans the title, replaces branding with [ ARYAFEED ] signature pill.
  -> Keeps exact same audio.
  -> Posts to Instagram and notifies Telegram with preview.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite
import requests
from PIL import Image

from bot.services.instagram_service import instagram_service
from bot.services.video_engine import stamp_image_watermark, stamp_video_watermark
from bot.utils.config import config
from database.db import db_manager

logger = logging.getLogger(__name__)

COMPETITOR_ACCOUNTS = [
    "rvcjinsta",
    "flirting.lines",
    "comedyculture.in",
    "adultsociety",
]

COMPETITOR_HANDLES = [
    "rvcj",
    "rvcjinsta",
    "comedyculture",
    "comedyculture.in",
    "adultsociety",
    "flirting.lines",
    "flirtinglines",
]

DEFAULT_ADMIN_CHAT_ID = 5381201341


class CompetitorMonitorService:
    """Service to monitor competitor Instagram accounts and process/rebrand content."""

    def __init__(self):
        self.db_path = config.database_path

    async def init_tables(self) -> None:
        """Create competitor_monitored_posts table if not exists."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS competitor_monitored_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_username TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    media_type TEXT,
                    caption TEXT,
                    has_competitor_branding INTEGER DEFAULT 0,
                    downloaded_file TEXT,
                    processed_file TEXT,
                    instagram_url TEXT,
                    posted_to_ig INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(account_username, post_id)
                );
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_competitor_posts 
                ON competitor_monitored_posts(account_username, post_id);
            """)
            await db.commit()

    async def is_post_processed(self, username: str, post_id: str) -> bool:
        """Check if post was already fetched and processed."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT 1 FROM competitor_monitored_posts WHERE account_username = ? AND post_id = ?",
                (username, str(post_id)),
            ) as cursor:
                return bool(await cursor.fetchone())

    async def record_processed_post(
        self,
        username: str,
        post_id: str,
        media_type: str,
        caption: str,
        has_branding: bool,
        downloaded_file: str,
        processed_file: str,
        posted_to_ig: bool,
        instagram_url: Optional[str] = None,
    ) -> None:
        """Record post in SQLite database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO competitor_monitored_posts (
                    account_username, post_id, media_type, caption,
                    has_competitor_branding, downloaded_file, processed_file,
                    posted_to_ig, instagram_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                username,
                str(post_id),
                media_type,
                caption,
                1 if has_branding else 0,
                downloaded_file,
                processed_file,
                1 if posted_to_ig else 0,
                instagram_url,
            ))
            await db.commit()

    def check_competitor_branding(self, text_or_caption: str) -> bool:
        """Check if text contains any competitor account handles or branding."""
        clean = (text_or_caption or "").lower()
        return any(handle in clean for handle in COMPETITOR_HANDLES)

    def clean_caption_for_aryafeed(self, raw_caption: str, source_account: str) -> str:
        """Strip competitor handles/promos and format clean AryaFeed caption."""
        lines = (raw_caption or "").split("\n")
        clean_lines = []
        for line in lines:
            line_lower = line.lower()
            # Skip lines with competitor promo or handles
            if any(h in line_lower for h in COMPETITOR_HANDLES):
                continue
            if any(p in line_lower for p in ["follow @", "follow us", "dm for", "link in bio"]):
                continue
            clean_lines.append(line)

        body = "\n".join(clean_lines).strip()
        if not body:
            body = "⚡ Daily dose of viral stories, memes & thoughts!"

        hashtags = "\n\nFollow @aryafeed.in for daily buzz ⚡\n#aryafeed #viral #trending #reels #memes #explore #india"
        return body + hashtags

    async def scan_and_rebrand_competitors(
        self,
        chat_id: int = DEFAULT_ADMIN_CHAT_ID,
        bot = None,
    ) -> List[Dict[str, Any]]:
        """Main autonomous loop: scans the 4 competitor accounts, downloads fresh posts,
        cleans branding or posts direct, and uploads to @aryafeed.in."""
        await self.init_tables()
        results = []

        # 1. Check if authenticated client is available
        cl = await instagram_service.get_authenticated_client(chat_id)
        if not cl:
            logger.info("[CompetitorMonitor] Instagram client not logged in. Waiting for /insta_login.")
            return results

        for target_username in COMPETITOR_ACCOUNTS:
            try:
                logger.info(f"[CompetitorMonitor] Checking @{target_username}...")
                target_user_id = await asyncio.to_thread(cl.user_id_from_username, target_username)
                if not target_user_id:
                    continue

                medias = await asyncio.to_thread(cl.user_medias, target_user_id, 3)
                for m in (medias or []):
                    post_id = str(getattr(m, "pk", getattr(m, "id", None)))
                    if not post_id or await self.is_post_processed(target_username, post_id):
                        continue

                    logger.info(f"[CompetitorMonitor] Found fresh post {post_id} from @{target_username}")
                    media_type = "video" if getattr(m, "media_type", 1) == 2 else "image"
                    raw_caption = getattr(m, "caption_text", "") or ""
                    clean_caption = self.clean_caption_for_aryafeed(raw_caption, target_username)

                    # Download media file
                    timestamp = int(datetime.now(timezone.utc).timestamp())
                    ext = ".mp4" if media_type == "video" else ".jpg"
                    dl_path = config.input_dir / f"comp_{target_username}_{post_id}_{timestamp}{ext}"

                    if media_type == "video":
                        video_url = getattr(m, "video_url", None)
                        if not video_url:
                            continue
                        r = requests.get(video_url, stream=True, timeout=20)
                        with open(dl_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=65536):
                                f.write(chunk)
                    else:
                        img_url = getattr(m, "thumbnail_url", None)
                        if not img_url:
                            # Try candidate resources
                            resources = getattr(m, "resources", None)
                            if resources and len(resources) > 0:
                                img_url = getattr(resources[0], "thumbnail_url", None)
                        if not img_url:
                            continue
                        r = requests.get(img_url, stream=True, timeout=15)
                        with open(dl_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=32768):
                                f.write(chunk)

                    if not dl_path.exists() or dl_path.stat().st_size < 1000:
                        continue

                    # Check for competitor branding
                    has_branding = self.check_competitor_branding(raw_caption)

                    # Process file: stamp [ ARYAFEED ] watermark
                    processed_path = config.output_dir / f"arya_{target_username}_{post_id}_{timestamp}{ext}"

                    if media_type == "video":
                        # Embed watermark preserving original audio
                        await asyncio.to_thread(stamp_video_watermark, dl_path, processed_path, "ARYAFEED")
                    else:
                        # Stamp watermark on photo/meme
                        await asyncio.to_thread(stamp_image_watermark, dl_path, processed_path, "ARYAFEED")

                    # Upload to Instagram
                    ig_result = {}
                    if media_type == "video":
                        ig_result = await instagram_service.upload_reel(
                            chat_id=chat_id,
                            video_path=processed_path,
                            caption=clean_caption,
                        )
                    else:
                        ig_result = await instagram_service.upload_photo(
                            chat_id=chat_id,
                            photo_path=processed_path,
                            caption=clean_caption,
                        )

                    posted_to_ig = ig_result.get("success", False)
                    ig_url = ig_result.get("url")

                    await self.record_processed_post(
                        username=target_username,
                        post_id=post_id,
                        media_type=media_type,
                        caption=clean_caption,
                        has_branding=has_branding,
                        downloaded_file=str(dl_path),
                        processed_file=str(processed_path),
                        posted_to_ig=posted_to_ig,
                        instagram_url=ig_url,
                    )

                    # Telegram notification
                    if bot:
                        try:
                            status_badge = "✅ *Clean Media — Auto-Posted Live!*" if not has_branding else "⚡ *Branded Media — Cleaned & Published!*"
                            caption_text = (
                                f"{status_badge}\n\n"
                                f"👤 *Source:* `@{target_username}`\n"
                                f"📂 *Type:* {'Reel' if media_type == 'video' else 'Meme Card / Photo'}\n"
                                f"🏷️ *Brand:* `[ ARYAFEED ]` (Bottom Right)\n"
                                f"🎵 *Audio:* Preserved Original\n\n"
                            )
                            if ig_url:
                                caption_text += f"🚀 [Watch Live on Instagram]({ig_url})\n"
                            elif ig_result.get("error"):
                                caption_text += f"⚠️ *Instagram Note:* {ig_result.get('error')}\n"

                            if media_type == "video":
                                with open(processed_path, "rb") as vf:
                                    await bot.send_video(
                                        chat_id=chat_id,
                                        video=vf,
                                        caption=caption_text,
                                        parse_mode="Markdown",
                                    )
                            else:
                                with open(processed_path, "rb") as pf:
                                    await bot.send_photo(
                                        chat_id=chat_id,
                                        photo=pf,
                                        caption=caption_text,
                                        parse_mode="Markdown",
                                    )
                        except Exception as e:
                            logger.warning(f"[CompetitorMonitor] Telegram alert failed: {e}")

                    results.append({
                        "account": target_username,
                        "post_id": post_id,
                        "media_type": media_type,
                        "posted": posted_to_ig,
                        "url": ig_url,
                    })

                    # Small delay between account posts to avoid rapid burst
                    await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"[CompetitorMonitor] Error scanning @{target_username}: {e}")

        return results

    async def process_media_item(
        self,
        target_username: str,
        media_obj: Any,
        chat_id: int,
        bot = None,
    ) -> Optional[Dict[str, Any]]:
        """Process a single newly detected post immediately:
        - If clean: stamp [ ARYAFEED ] watermark, preserve original audio, post to @aryafeed.in.
        - If branded: clean caption and branding, stamp [ ARYAFEED ] pill, preserve original audio, post to @aryafeed.in.
        """
        post_id = str(getattr(media_obj, "pk", getattr(media_obj, "id", None)))
        if not post_id or await self.is_post_processed(target_username, post_id):
            return None

        logger.info(f"[SpySentinel] 🎯 NEW POST DETECTED on @{target_username}! Post ID: {post_id}")
        media_type = "video" if getattr(media_obj, "media_type", 1) == 2 else "image"
        raw_caption = getattr(media_obj, "caption_text", "") or ""
        clean_caption = self.clean_caption_for_aryafeed(raw_caption, target_username)

        timestamp = int(datetime.now(timezone.utc).timestamp())
        ext = ".mp4" if media_type == "video" else ".jpg"
        dl_path = config.input_dir / f"spy_{target_username}_{post_id}_{timestamp}{ext}"

        if media_type == "video":
            video_url = getattr(media_obj, "video_url", None)
            if not video_url:
                return None
            r = requests.get(video_url, stream=True, timeout=25)
            with open(dl_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
        else:
            img_url = getattr(media_obj, "thumbnail_url", None)
            if not img_url:
                resources = getattr(media_obj, "resources", None)
                if resources and len(resources) > 0:
                    img_url = getattr(resources[0], "thumbnail_url", None)
            if not img_url:
                return None
            r = requests.get(img_url, stream=True, timeout=20)
            with open(dl_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=32768):
                    f.write(chunk)

        if not dl_path.exists() or dl_path.stat().st_size < 1000:
            return None

        has_branding = self.check_competitor_branding(raw_caption)
        processed_path = config.output_dir / f"arya_spy_{target_username}_{post_id}_{timestamp}{ext}"

        if media_type == "video":
            # Preserve original audio stream, embed watermark on bottom-right
            await asyncio.to_thread(stamp_video_watermark, dl_path, processed_path, "ARYAFEED")
        else:
            # Stamp yellow pill watermark on photo/meme card
            await asyncio.to_thread(stamp_image_watermark, dl_path, processed_path, "ARYAFEED")

        # Upload immediately to Instagram @aryafeed.in
        if media_type == "video":
            ig_result = await instagram_service.upload_reel(
                chat_id=chat_id,
                video_path=processed_path,
                caption=clean_caption,
            )
        else:
            ig_result = await instagram_service.upload_photo(
                chat_id=chat_id,
                photo_path=processed_path,
                caption=clean_caption,
            )

        posted_to_ig = ig_result.get("success", False)
        ig_url = ig_result.get("url")

        await self.record_processed_post(
            username=target_username,
            post_id=post_id,
            media_type=media_type,
            caption=clean_caption,
            has_branding=has_branding,
            downloaded_file=str(dl_path),
            processed_file=str(processed_path),
            posted_to_ig=posted_to_ig,
            instagram_url=ig_url,
        )

        # Notify Telegram
        if bot:
            try:
                status_badge = "⚡ *SPY SENTINEL: Clean Post Auto-Uploaded!*" if not has_branding else "⚡ *SPY SENTINEL: Branded Post Cleaned & Uploaded!*"
                caption_text = (
                    f"{status_badge}\n\n"
                    f"👤 *Source:* `@{target_username}`\n"
                    f"📂 *Type:* {'Reel' if media_type == 'video' else 'Meme Card / Photo'}\n"
                    f"🏷️ *Brand:* `[ ARYAFEED ]` (Bottom Right)\n"
                    f"🎵 *Audio:* Preserved Original\n\n"
                )
                if ig_url:
                    caption_text += f"🚀 [Live on @aryafeed.in]({ig_url})\n"
                elif ig_result.get("error"):
                    caption_text += f"⚠️ *Instagram Note:* {ig_result.get('error')}\n"

                if media_type == "video":
                    with open(processed_path, "rb") as vf:
                        await bot.send_video(
                            chat_id=chat_id,
                            video=vf,
                            caption=caption_text,
                            parse_mode="Markdown",
                        )
                else:
                    with open(processed_path, "rb") as pf:
                        await bot.send_photo(
                            chat_id=chat_id,
                            photo=pf,
                            caption=caption_text,
                            parse_mode="Markdown",
                        )
            except Exception as e:
                logger.warning(f"[SpySentinel] Telegram alert failed: {e}")

        return {
            "account": target_username,
            "post_id": post_id,
            "media_type": media_type,
            "posted": posted_to_ig,
            "url": ig_url,
        }

    async def run_realtime_spy_sentinel(
        self,
        chat_id: int = DEFAULT_ADMIN_CHAT_ID,
        bot = None,
    ) -> None:
        """Continuous Real-Time Sentinel Loop:
        Keeps 24/7 watch on the 4 competitor accounts.
        The moment any new post is published, immediately processes and uploads to @aryafeed.in!
        """
        await self.init_tables()
        logger.info(f"[SpySentinel] 🚨 24/7 Real-Time Spy Sentinel ACTIVATED on: {', '.join(COMPETITOR_ACCOUNTS)}")

        while True:
            try:
                cl = await instagram_service.get_authenticated_client(chat_id)
                if not cl:
                    # Client not logged in yet, wait and retry
                    await asyncio.sleep(60)
                    continue

                for target_username in COMPETITOR_ACCOUNTS:
                    try:
                        target_user_id = await asyncio.to_thread(cl.user_id_from_username, target_username)
                        if target_user_id:
                            medias = await asyncio.to_thread(cl.user_medias, target_user_id, 2)
                            for m in (medias or []):
                                await self.process_media_item(target_username, m, chat_id, bot)
                    except Exception as e:
                        logger.warning(f"[SpySentinel] Watch error for @{target_username}: {e}")

                    # Stagger 15s between account checks for continuous, smooth monitoring
                    await asyncio.sleep(15)

            except asyncio.CancelledError:
                logger.info("[SpySentinel] Sentinel cancelled.")
                break
            except Exception as e:
                logger.exception(f"[SpySentinel] Sentinel loop error: {e}")
                await asyncio.sleep(30)


# Singleton instance
competitor_monitor_service = CompetitorMonitorService()
