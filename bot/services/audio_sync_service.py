"""Instagram Audio Sync Service.

Automatically scans saved and liked reels from the user's connected Instagram account,
downloads the trending soundtrack/audio, and registers it into the bot's active playlist.
"""

import asyncio
import logging
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from bot.services.instagram_service import instagram_service
from bot.services.music_service import BOLLYWOOD_MUSIC_DIR, TRACK_METADATA, VOCAL_TRACKS
from database.db import db_manager

logger = logging.getLogger(__name__)


class AudioSyncService:
    """Manages automatic extraction and sync of trending audio from Instagram."""

    def __init__(self, music_dir: Path = BOLLYWOOD_MUSIC_DIR):
        self.music_dir = music_dir
        self.music_dir.mkdir(parents=True, exist_ok=True)

    async def load_synced_tracks_into_playlist(self) -> int:
        """Load all previously synced Instagram tracks from DB into the runtime VOCAL_TRACKS pool."""
        try:
            records = await db_manager.get_all_synced_audio()
            loaded = 0
            existing_ids = {t["id"] for t in VOCAL_TRACKS}

            for rec in records:
                audio_id = f"ig_{rec['audio_id']}"
                if audio_id in existing_ids:
                    continue

                file_path = Path(rec["file_path"])
                if not file_path.exists() or file_path.stat().st_size < 1000:
                    continue

                track_entry = {
                    "id": audio_id,
                    "file": file_path.name,
                    "title": rec["title"],
                    "artist": rec["artist"],
                    "lyrics": f"Trending audio from Instagram reel by {rec['artist']}",
                    "icon": "🔥",
                    "style_affinity": [
                        "romantic", "sexy", "cinematic", "baddie",
                        "aesthetic", "traditional", "broken", "bestie",
                    ],
                }
                VOCAL_TRACKS.append(track_entry)
                TRACK_METADATA[file_path.name] = {
                    "title": f"{rec['title']} ({rec['artist']} - IG Trending)",
                    "artist": rec["artist"],
                    "lyrics": track_entry["lyrics"],
                    "style_affinity": track_entry["style_affinity"],
                }
                existing_ids.add(audio_id)
                loaded += 1

            if loaded > 0:
                logger.info(f"[AudioSync] Loaded {loaded} synced Instagram audio track(s) into active pool.")
            return loaded
        except Exception as e:
            logger.error(f"[AudioSync] Failed to load synced tracks from DB: {e}")
            return 0

    async def get_collections(self, chat_id: int) -> List[Dict[str, str]]:
        """Fetch all saved collections (folders) from user's scouting Instagram account."""
        cl = await instagram_service.get_sync_client(chat_id)
        if not cl:
            return [{"name": "Audio (Saved Sounds 🎵)", "id": "SAVED_AUDIO_COLLECTION"}]
        try:
            colls = await asyncio.to_thread(cl.collections)
            out = [{"name": "Audio (Saved Sounds 🎵)", "id": "SAVED_AUDIO_COLLECTION"}]
            for c in colls:
                cid = str(getattr(c, "id", ""))
                cname = getattr(c, "name", "Unnamed")
                if cid != "ALL_MEDIA_AUTO_COLLECTION":
                    out.append({"name": cname, "id": cid})
            return out
        except Exception as e:
            logger.error(f"[AudioSync] Failed to fetch collections for chat {chat_id}: {e}")
            return [{"name": "Audio (Saved Sounds 🎵)", "id": "SAVED_AUDIO_COLLECTION"}]

    async def set_target_collection(self, chat_id: int, coll_id: str, coll_name: str) -> None:
        """Save designated scout folder for a chat."""
        await db_manager.set_setting(f"sync_collection_id_{chat_id}", str(coll_id))
        await db_manager.set_setting(f"sync_collection_name_{chat_id}", str(coll_name))

    async def get_target_collection(self, chat_id: int) -> Dict[str, Optional[str]]:
        """Get designated scout folder info."""
        cid = await db_manager.get_setting(f"sync_collection_id_{chat_id}")
        cname = await db_manager.get_setting(f"sync_collection_name_{chat_id}")
        # Default to Saved Audio collection
        if not cid:
            cid = "SAVED_AUDIO_COLLECTION"
            cname = "Audio (Saved Sounds 🎵)"
        return {"id": cid, "name": cname}

    async def sync_from_instagram(self, chat_id: int, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Scan Saved reels from Instagram (specific folder or saved audio), extract trending audio, and add to playlist."""
        cl = await instagram_service.get_sync_client(chat_id)
        if not cl:
            logger.warning(f"[AudioSync] No active Instagram client for chat {chat_id}")
            return []

        if not folder_id:
            folder_id = await db_manager.get_setting(f"sync_collection_id_{chat_id}")
        folder_name = await db_manager.get_setting(f"sync_collection_name_{chat_id}") or "Audio"

        media_items = []

        is_saved_audio = (
            folder_id == "SAVED_AUDIO_COLLECTION"
            or not folder_id
            or (folder_name and folder_name.lower().strip() in ["audio", "audio (saved sounds 🎵)", "saved audio"])
        )

        if is_saved_audio:
            logger.info(f"[AudioSync] Scanning Instagram Saved Audio feed (Saved -> Audio) for chat {chat_id}...")
            try:
                audio_resp = await asyncio.to_thread(cl.private_request, "feed/saved/audio/")
                for it in audio_resp.get("items", []):
                    snd = it.get("original_sound") or it.get("music_info", {}).get("music_asset_info") or it.get("track") or it
                    audio_id = str(snd.get("audio_asset_id") or snd.get("id") or "")
                    if not audio_id:
                        continue
                    title = snd.get("original_audio_title") or snd.get("title") or "Original Audio"
                    ig = snd.get("ig_artist", {}) if isinstance(snd.get("ig_artist"), dict) else {}
                    artist = ig.get("username") or ig.get("full_name") or snd.get("display_artist") or "Instagram Artist"
                    audio_url = snd.get("progressive_download_url") or snd.get("fast_start_progressive_download_url")
                    if audio_url:
                        media_items.append({
                            "source": "saved_audio",
                            "audio_id": audio_id,
                            "title": title,
                            "artist": artist,
                            "download_url": audio_url,
                            "media_pk": audio_id,
                        })
                logger.info(f"[AudioSync] Found {len(media_items)} items in Saved -> Audio")
            except Exception as e:
                logger.warning(f"[AudioSync] Could not fetch saved audio feed: {e}")

        elif folder_id and folder_id != "ALL_MEDIA_AUTO_COLLECTION":
            logger.info(f"[AudioSync] Scanning specific collection '{folder_name}' (ID: {folder_id}) for chat {chat_id}...")
            try:
                col_medias = await asyncio.to_thread(cl.collection_medias, folder_id, 30)
                for m in col_medias:
                    media_items.append((f"folder:{folder_name}", m))
                logger.info(f"[AudioSync] Found {len(col_medias)} items in folder '{folder_name}'")
            except Exception as e:
                logger.warning(f"[AudioSync] Could not fetch collection medias: {e}")
        else:
            # 1. Fetch from Saved Posts feed
            logger.info(f"[AudioSync] Scanning all saved posts for chat {chat_id}...")
            try:
                saved_resp = await asyncio.to_thread(cl.private_request, "feed/saved/posts/")
                for it in saved_resp.get("items", []):
                    m = it.get("media")
                    if m:
                        media_items.append(("saved", m))
                logger.info(f"[AudioSync] Found {len(saved_resp.get('items', []))} saved item(s)")
            except Exception as e:
                logger.warning(f"[AudioSync] Could not fetch saved posts: {e}")

        newly_synced = []

        for item in media_items:
            try:
                if isinstance(item, dict) and item.get("source") == "saved_audio":
                    source_type = "saved_audio"
                    media_pk = item["media_pk"]
                    audio_id = item["audio_id"]
                    title = item["title"]
                    artist = item["artist"]
                    download_target = item["download_url"]
                    code = audio_id
                else:
                    source_type, m = item
                    if isinstance(m, dict):
                        media_pk = str(m.get("pk", ""))
                        code = m.get("code", "")
                        cm = m.get("clips_metadata") or {}
                        video_url = m.get("video_url")
                    else:
                        media_pk = str(getattr(m, "pk", ""))
                        code = getattr(m, "code", "")
                        cm = getattr(m, "clips_metadata", {}) or {}
                        video_url = getattr(m, "video_url", None)

                    if not media_pk:
                        continue

                    title = None
                    artist = "Instagram Sound"
                    audio_url = None
                    audio_asset_id = None

                    music_info = cm.get("music_info") if isinstance(cm, dict) else getattr(cm, "music_info", None)
                    if music_info:
                        mai = music_info.get("music_asset_info", {}) if isinstance(music_info, dict) else getattr(music_info, "music_asset_info", {})
                        title = mai.get("title")
                        artist = mai.get("display_artist") or artist
                        audio_url = mai.get("progressive_download_url") or mai.get("fast_start_progressive_download_url")
                        audio_asset_id = str(mai.get("audio_asset_id") or media_pk)

                    if not audio_url:
                        orig_sound = cm.get("original_sound_info") if isinstance(cm, dict) else getattr(cm, "original_sound_info", None)
                        if orig_sound:
                            title = orig_sound.get("original_audio_title") or "Original Sound"
                            ig_artist = orig_sound.get("ig_artist") or {}
                            artist = ig_artist.get("full_name") or ig_artist.get("username") or artist
                            audio_url = orig_sound.get("progressive_download_url")
                            audio_asset_id = str(orig_sound.get("audio_asset_id") or media_pk)

                    if not audio_asset_id and isinstance(cm, dict) and cm.get("audio_parts"):
                        p = cm["audio_parts"][0]
                        title = p.get("display_title") or title
                        artist = p.get("display_artist") or artist
                        audio_asset_id = str(p.get("audio_asset_id") or media_pk)

                    audio_id = audio_asset_id or media_pk
                    title = title or f"Trending Reel Audio ({code or media_pk})"
                    download_target = audio_url or video_url

                if not download_target:
                    continue

                # Check if already synced in DB
                if await db_manager.is_audio_already_synced(audio_id):
                    continue

                # Prepare destination file
                safe_slug = re.sub(r"[^a-zA-Z0-9_]", "_", title.lower())[:25]
                out_mp3 = self.music_dir / f"ig_{safe_slug}_{audio_id}_vocal.mp3"
                tmp_dl = self.music_dir / f"tmp_ig_{audio_id}.mp4"

                download_target = audio_url or video_url
                if not download_target:
                    continue

                logger.info(f"[AudioSync] Downloading trending track '{title}' by '{artist}' (PK: {media_pk})...")

                # Download audio stream or video
                def _do_download():
                    req = urllib.request.Request(
                        download_target,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                    )
                    with urllib.request.urlopen(req, timeout=30) as resp, open(tmp_dl, "wb") as f:
                        f.write(resp.read())

                    # Transcode audio to 192k MP3 with ffmpeg
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", str(tmp_dl),
                        "-vn",
                        "-c:a", "libmp3lame",
                        "-b:a", "192k",
                        str(out_mp3),
                    ]
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if tmp_dl.exists():
                        tmp_dl.unlink()

                await asyncio.to_thread(_do_download)

                if out_mp3.exists() and out_mp3.stat().st_size > 1000:
                    # Record in DB
                    await db_manager.record_synced_audio(
                        audio_id=audio_id,
                        title=title,
                        artist=artist,
                        file_path=str(out_mp3),
                        media_pk=media_pk,
                        source=source_type,
                    )

                    # Register dynamically in VOCAL_TRACKS
                    track_id = f"ig_{audio_id}"
                    track_entry = {
                        "id": track_id,
                        "file": out_mp3.name,
                        "title": title,
                        "artist": artist,
                        "lyrics": f"Trending audio from Instagram reel ({artist})",
                        "icon": "🔥",
                        "style_affinity": [
                            "romantic", "sexy", "cinematic", "baddie",
                            "aesthetic", "traditional", "broken", "bestie",
                        ],
                    }
                    VOCAL_TRACKS.append(track_entry)
                    TRACK_METADATA[out_mp3.name] = {
                        "title": f"{title} ({artist} - IG Trending)",
                        "artist": artist,
                        "lyrics": track_entry["lyrics"],
                        "style_affinity": track_entry["style_affinity"],
                    }

                    newly_synced.append(track_entry)
                    logger.info(f"[AudioSync] Successfully synced '{title}' -> {out_mp3.name}")

            except Exception as e:
                logger.warning(f"[AudioSync] Failed to process media {source_type}: {e}")

        logger.info(f"[AudioSync] Finished sync. {len(newly_synced)} new track(s) added to playlist.")
        return newly_synced


# Singleton instance
audio_sync_service = AudioSyncService()
