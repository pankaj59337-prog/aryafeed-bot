"""Media ingestion handlers: photos, videos, animations.
Auto-stamps [ ARYAFEED ] watermark pill on bottom-right and provides 1-tap Instagram posting!
"""

import asyncio
import logging
from pathlib import Path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.handlers.commands import restricted
from bot.services.video_engine import stamp_image_watermark, stamp_video_watermark
from bot.utils.config import config
from database.db import db_manager

logger = logging.getLogger(__name__)


@restricted
async def reel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reel command: directly launch the AryaFeed News Studio Preview."""
    chat_id = update.effective_chat.id
    await db_manager.start_reel_session(chat_id)

    from bot.handlers.auto import send_interactive_studio_preview

    cat_id = "news_banner"
    context.user_data["chosen_cat"] = cat_id
    await send_interactive_studio_preview(
        update,
        context,
        cat_id=cat_id,
        force_new_img=True,
    )


@restricted
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle custom photo / meme card upload from user:
    Immediately stamps [ ARYAFEED ] watermark (bottom-right yellow pill),
    generates viral caption, and provides 1-tap Instagram post button + animated reel option!
    """
    chat_id = update.effective_chat.id
    photos = update.effective_message.photo
    if not photos:
        return

    # Select highest resolution photo
    photo = photos[-1]
    file = await photo.get_file()
    dest_path = config.input_dir / f"{chat_id}_{photo.file_unique_id}.jpg"
    await file.download_to_drive(custom_path=dest_path)
    logger.info(f"Custom user photo saved for chat {chat_id}: {dest_path}")

    # 1. Stamp signature [ ARYAFEED ] yellow pill watermark at bottom-right
    stamped_path = config.output_dir / f"stamped_{chat_id}_{photo.file_unique_id}.jpg"
    try:
        await asyncio.to_thread(stamp_image_watermark, dest_path, stamped_path, "ARYAFEED")
    except Exception as e:
        logger.exception(f"Failed to stamp image watermark: {e}")
        stamped_path = dest_path

    # 2. Extract or generate caption
    user_caption = update.effective_message.caption
    if user_caption and len(user_caption.strip()) > 3:
        clean_caption = user_caption.strip()
        if "#aryafeed" not in clean_caption.lower():
            clean_caption += "\n\n⚡ Follow @aryafeed.in for daily buzz & humor\n#aryafeed #trending #viral #memes #india"
    else:
        clean_caption = (
            "⚡ Daily dose of viral stories, memes & thoughts!\n\n"
            "👉 Follow @aryafeed.in for daily buzz 🔔\n"
            "📩 DM for credits / collabs\n\n"
            "#aryafeed #viral #trending #reels #memes #explore #india"
        )

    # 3. Save into DB session
    await db_manager.start_reel_session(chat_id)
    await db_manager.update_session(
        chat_id,
        current_step="READY_TO_POST",
        media_path=str(dest_path),
        media_type="image",
        output_path=str(stamped_path),
        selected_template="news_banner",
        custom_caption=clean_caption,
    )

    context.user_data["custom_media_path"] = str(dest_path)
    context.user_data["chosen_img"] = "custom_upload"
    context.user_data["chosen_cat"] = "news_banner"

    # 4. Inline keyboard with 1-tap post & animated reel options
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 1-Tap Post to Instagram", callback_data="post_insta"),
        ],
        [
            InlineKeyboardButton("🎬 Convert to 7s Animated Reel", callback_data="auto_render_custom_reel"),
        ]
    ])

    # 5. Send stamped photo back to Telegram
    with open(stamped_path, "rb") as pf:
        await update.effective_message.reply_photo(
            photo=pf,
            caption=(
                "⚡ *[ ARYAFEED ] Watermark Stamped!*\n\n"
                "🏷️ **Brand:** `[ ARYAFEED ]` (Bottom Right)\n"
                f"📝 **Caption:**\n_{clean_caption[:280]}..._\n\n"
                "Tap below to publish live to `@aryafeed.in`:"
            ),
            reply_markup=keyboard,
            parse_mode="Markdown",
        )


@restricted
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle video / reel / clip upload:
    Immediately embeds [ ARYAFEED ] watermark (bottom-right yellow pill) via FFmpeg,
    generates caption, and provides 1-tap Instagram Reel post button!
    """
    chat_id = update.effective_chat.id
    video = update.effective_message.video or update.effective_message.animation
    if not video:
        return

    max_bytes = config.max_video_size_mb * 1024 * 1024
    if video.file_size and video.file_size > max_bytes:
        await update.effective_message.reply_text(
            f"❌ Video exceeds maximum size limit of {config.max_video_size_mb} MB."
        )
        return

    progress_msg = await update.effective_message.reply_text("⚡ *Downloading video...*", parse_mode="Markdown")

    file = await video.get_file()
    ext = ".mp4" if not video.file_name else Path(video.file_name).suffix or ".mp4"
    dest_path = config.input_dir / f"{chat_id}_{video.file_unique_id}{ext}"
    await file.download_to_drive(custom_path=dest_path)

    await progress_msg.edit_text("⚡ *Embedding [ ARYAFEED ] watermark into video...*", parse_mode="Markdown")

    stamped_video_path = config.output_dir / f"stamped_{chat_id}_{video.file_unique_id}.mp4"
    try:
        await asyncio.to_thread(stamp_video_watermark, dest_path, stamped_video_path, "ARYAFEED")
    except Exception as e:
        logger.exception(f"Video watermarking failed: {e}")
        stamped_video_path = dest_path

    # Extract or generate caption
    user_caption = update.effective_message.caption
    if user_caption and len(user_caption.strip()) > 3:
        clean_caption = user_caption.strip()
        if "#aryafeed" not in clean_caption.lower():
            clean_caption += "\n\n⚡ Follow @aryafeed.in for daily buzz & humor\n#aryafeed #trending #viral #reels #india"
    else:
        clean_caption = (
            "⚡ Daily dose of viral stories & reels!\n\n"
            "👉 Follow @aryafeed.in for more 🔔\n"
            "📩 DM for credits / collabs\n\n"
            "#aryafeed #viral #trending #reels #explore #india"
        )

    await db_manager.start_reel_session(chat_id)
    await db_manager.update_session(
        chat_id,
        current_step="READY_TO_POST",
        media_path=str(dest_path),
        media_type="video",
        output_path=str(stamped_video_path),
        custom_caption=clean_caption,
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 1-Tap Post Reel to Instagram", callback_data="post_insta"),
        ]
    ])

    try:
        await progress_msg.delete()
    except Exception:
        pass

    with open(stamped_video_path, "rb") as vf:
        await update.effective_message.reply_video(
            video=vf,
            caption=(
                "⚡ *[ ARYAFEED ] Watermark Embedded!*\n\n"
                "🏷️ **Brand:** `[ ARYAFEED ]` (Bottom Right)\n"
                f"📝 **Caption:**\n_{clean_caption[:280]}..._\n\n"
                "Tap below to publish reel live to `@aryafeed.in`:"
            ),
            reply_markup=keyboard,
            parse_mode="Markdown",
        )


@restricted
async def handle_document_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle uncompressed document uploads that are images or videos."""
    chat_id = update.effective_chat.id
    doc = update.effective_message.document
    if not doc or not doc.mime_type:
        return

    mime = doc.mime_type.lower()
    if mime.startswith("image/"):
        file = await doc.get_file()
        ext = Path(doc.file_name).suffix if doc.file_name else ".jpg"
        dest_path = config.input_dir / f"{chat_id}_{doc.file_unique_id}{ext}"
        await file.download_to_drive(custom_path=dest_path)

        stamped_path = config.output_dir / f"stamped_{chat_id}_{doc.file_unique_id}.jpg"
        try:
            await asyncio.to_thread(stamp_image_watermark, dest_path, stamped_path, "ARYAFEED")
        except Exception as e:
            logger.exception(f"Failed to stamp image watermark: {e}")
            stamped_path = dest_path

        user_caption = update.effective_message.caption
        if user_caption and len(user_caption.strip()) > 3:
            clean_caption = user_caption.strip()
            if "#aryafeed" not in clean_caption.lower():
                clean_caption += "\n\n⚡ Follow @aryafeed.in for daily buzz & humor\n#aryafeed #trending #viral #memes #india"
        else:
            clean_caption = (
                "⚡ Daily dose of viral stories, memes & thoughts!\n\n"
                "👉 Follow @aryafeed.in for daily buzz 🔔\n"
                "#aryafeed #viral #trending #reels #memes #explore #india"
            )

        await db_manager.start_reel_session(chat_id)
        await db_manager.update_session(
            chat_id,
            current_step="READY_TO_POST",
            media_path=str(dest_path),
            media_type="image",
            output_path=str(stamped_path),
            selected_template="news_banner",
            custom_caption=clean_caption,
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🚀 1-Tap Post to Instagram", callback_data="post_insta"),
            ],
            [
                InlineKeyboardButton("🎬 Convert to 7s Animated Reel", callback_data="auto_render_custom_reel"),
            ]
        ])

        with open(stamped_path, "rb") as pf:
            await update.effective_message.reply_photo(
                photo=pf,
                caption=(
                    "⚡ *[ ARYAFEED ] Watermark Stamped!*\n\n"
                    "🏷️ **Brand:** `[ ARYAFEED ]` (Bottom Right)\n"
                    f"📝 **Caption:**\n_{clean_caption[:280]}..._\n\n"
                    "Tap below to publish live to `@aryafeed.in`:"
                ),
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

    elif mime.startswith("video/"):
        max_bytes = config.max_video_size_mb * 1024 * 1024
        if doc.file_size and doc.file_size > max_bytes:
            await update.effective_message.reply_text(
                f"❌ File exceeds maximum size limit of {config.max_video_size_mb} MB."
            )
            return

        progress_msg = await update.effective_message.reply_text("⚡ *Downloading video document...*", parse_mode="Markdown")

        file = await doc.get_file()
        ext = Path(doc.file_name).suffix if doc.file_name else ".mp4"
        dest_path = config.input_dir / f"{chat_id}_{doc.file_unique_id}{ext}"
        await file.download_to_drive(custom_path=dest_path)

        await progress_msg.edit_text("⚡ *Embedding [ ARYAFEED ] watermark into video...*", parse_mode="Markdown")

        stamped_video_path = config.output_dir / f"stamped_{chat_id}_{doc.file_unique_id}.mp4"
        try:
            await asyncio.to_thread(stamp_video_watermark, dest_path, stamped_video_path, "ARYAFEED")
        except Exception as e:
            logger.exception(f"Video watermarking failed: {e}")
            stamped_video_path = dest_path

        user_caption = update.effective_message.caption
        if user_caption and len(user_caption.strip()) > 3:
            clean_caption = user_caption.strip()
            if "#aryafeed" not in clean_caption.lower():
                clean_caption += "\n\n⚡ Follow @aryafeed.in for daily buzz & humor\n#aryafeed #trending #viral #reels #india"
        else:
            clean_caption = (
                "⚡ Daily dose of viral stories & reels!\n\n"
                "👉 Follow @aryafeed.in for more 🔔\n"
                "#aryafeed #viral #trending #reels #explore #india"
            )

        await db_manager.start_reel_session(chat_id)
        await db_manager.update_session(
            chat_id,
            current_step="READY_TO_POST",
            media_path=str(dest_path),
            media_type="video",
            output_path=str(stamped_video_path),
            custom_caption=clean_caption,
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🚀 1-Tap Post Reel to Instagram", callback_data="post_insta"),
            ]
        ])

        try:
            await progress_msg.delete()
        except Exception:
            pass

        with open(stamped_video_path, "rb") as vf:
            await update.effective_message.reply_video(
                video=vf,
                caption=(
                    "⚡ *[ ARYAFEED ] Watermark Embedded!*\n\n"
                    "🏷️ **Brand:** `[ ARYAFEED ]` (Bottom Right)\n"
                    f"📝 **Caption:**\n_{clean_caption[:280]}..._\n\n"
                    "Tap below to publish reel live to `@aryafeed.in`:"
                ),
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
