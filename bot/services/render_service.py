"""Rendering orchestration service for Telegram bot sessions."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from bot.services.video_engine import render_complete_reel
from bot.utils.cleanup import safe_remove_file
from bot.utils.config import config
from database.db import db_manager

logger = logging.getLogger(__name__)


async def execute_render_job(chat_id: int) -> Path:
    """Orchestrate rendering job for a given chat ID asynchronously."""
    session = await db_manager.get_session(chat_id)
    if not session:
        raise ValueError(f"No active session found for chat_id {chat_id}")

    media_path_str = session.get("media_path")
    media_type = session.get("media_type")
    overlay_text = session.get("overlay_text") or ""
    music_path_str = session.get("music_path")
    template_key = session.get("selected_template") or "cinematic"

    if not media_path_str:
        raise ValueError("Missing media file for rendering")

    media_path = Path(media_path_str)
    if not media_path.exists():
        raise FileNotFoundError(f"Media file not found: {media_path}")

    from bot.services.music_service import music_service

    audio_path = Path(music_path_str) if music_path_str and Path(music_path_str).exists() else None
    if not audio_path:
        audio_path = music_service.get_bollywood_track(template_key)
        if audio_path:
            logger.info(f"Auto-selected Bollywood background soundtrack: {audio_path.name} for {template_key}")

    # Update database step to RENDERING
    await db_manager.update_session(chat_id, current_step="RENDERING")

    output_filename = f"reel_{chat_id}_{int(asyncio.get_event_loop().time())}.mp4"
    output_path = config.output_dir / output_filename

    # Execute heavy FFmpeg processing in separate thread to avoid blocking asyncio loop
    try:
        final_video = await asyncio.to_thread(
            render_complete_reel,
            media_path=media_path,
            media_type=media_type,
            text=overlay_text,
            template_key=template_key,
            audio_path=audio_path,
            output_path=output_path,
            temp_dir=config.temp_dir,
            target_duration=float(config.output_duration_seconds),
        )

        # Update database with output path
        await db_manager.update_session(
            chat_id,
            current_step="COMPLETED",
            output_path=str(final_video),
        )

        # Clean temporary intermediate files if configured
        if config.cleanup_temp_files:
            stem = media_path.stem
            safe_remove_file(config.temp_dir / f"{stem}_text_overlay.png")
            safe_remove_file(config.temp_dir / f"{stem}_base.mp4")
            safe_remove_file(config.temp_dir / f"{stem}_with_audio.mp4")

        return final_video

    except Exception as e:
        logger.exception(f"Rendering failed for chat_id {chat_id}: {e}")
        await db_manager.update_session(chat_id, current_step="FAILED")
        raise
