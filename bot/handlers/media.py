"""Media ingestion handlers: photos, videos, animations."""

import logging
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.commands import restricted
from bot.utils.config import config
from database.db import db_manager

logger = logging.getLogger(__name__)


@restricted
async def reel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reel command: ask user for category / vibe first."""
    chat_id = update.effective_chat.id
    await db_manager.start_reel_session(chat_id)

    from bot.handlers.auto import build_category_selection_keyboard

    prompt = (
        "🎬 *Reel Studio: Choose Your Category*\n\n"
        "Please select the vibe / category for your reel first:\n\n"
        "• 💋 *Sexy / Flirty Desi:* Bold candid selfies & sultry vibes\n"
        "• 🔥 *Hot & Baddie / Attitude:* Sassy attitude & self-love\n"
        "• 👯‍♀️ *Bestie Love / Duo Goals:* Cute bestie bonds & sisterhood\n"
        "• 💖 *Romantic / Love:* Pastel sarees & heartwarming love lyrics\n"
        "• 🎬 *Late Night / Cinematic:* Neon bokeh & late night thoughts\n"
        "• 👑 *Desi Traditional:* Royal sarees & timeless shayari\n"
        "• 💔 *Broken Heart / Dard:* Emotional heartbreak & soulful pain\n"
        "• ✨ *Aesthetic / Soft Glow:* Golden hour & peaceful calm vibes\n\n"
        "_(💡 Visuals, Bollywood songs & hooks will strictly adapt to your choice!)_"
    )
    if update.effective_message:
        await update.effective_message.reply_text(
            prompt,
            reply_markup=build_category_selection_keyboard(),
            parse_mode="Markdown"
        )


@restricted
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle custom photo upload from user: seamlessly plugs into interactive reel creation flow!"""
    chat_id = update.effective_chat.id
    session = await db_manager.get_session(chat_id)

    photos = update.effective_message.photo
    if not photos:
        return

    # Select largest photo
    photo = photos[-1]

    # Download file
    file = await photo.get_file()
    dest_path = config.input_dir / f"{chat_id}_{photo.file_unique_id}.jpg"
    await file.download_to_drive(custom_path=dest_path)

    logger.info(f"Custom user photo saved for chat {chat_id}: {dest_path}")

    # Set context so subsequent steps know user uploaded their own image
    context.user_data["custom_media_path"] = str(dest_path)
    context.user_data["chosen_img"] = "custom_upload"
    cat = context.user_data.get("chosen_cat") or (session.get("selected_template") if session else None) or "romantic"
    context.user_data["chosen_cat"] = cat

    await db_manager.start_reel_session(chat_id)
    await db_manager.update_session(
        chat_id,
        current_step="WAITING_TEXT_SELECTION",
        media_path=str(dest_path),
        media_type="image",
        selected_template=cat,
    )

    from bot.handlers.auto import get_fresh_hook_options, build_hook_selection_keyboard, get_category_info
    cat_info = get_category_info(cat)
    fresh_hooks = await get_fresh_hook_options(chat_id, category=cat, limit=5)
    context.user_data["current_hook_options"] = fresh_hooks

    hooks_text = "\n".join([f"{idx}️⃣ _{h['text']}_" for idx, h in enumerate(fresh_hooks, start=1)])

    msg = (
        f"📸 *Custom Image Received & Loaded!*\n\n"
        f"📂 *Vibe Style:* {cat_info['icon']} *{cat_info['title']}*\n\n"
        f"Select 1 of 5 viral text quotes below, or type your own hook in chat:\n\n"
        f"{hooks_text}\n\n"
        f"_(💡 Next, an instant 1080x1920 preview with your photo + text will be shown!)_"
    )

    await update.effective_message.reply_text(
        msg,
        reply_markup=build_hook_selection_keyboard(fresh_hooks, category=cat),
        parse_mode="Markdown",
    )


@restricted
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle video upload from user."""
    chat_id = update.effective_chat.id
    session = await db_manager.get_session(chat_id)

    if not session or session.get("current_step") not in ("WAITING_MEDIA", "IDLE"):
        await db_manager.start_reel_session(chat_id)

    video = update.effective_message.video or update.effective_message.animation
    if not video:
        return

    # Check file size limit
    max_bytes = config.max_video_size_mb * 1024 * 1024
    if video.file_size and video.file_size > max_bytes:
        await update.effective_message.reply_text(
            f"❌ Video exceeds maximum size limit of {config.max_video_size_mb} MB. Please upload a smaller video."
        )
        return

    # Download file
    file = await video.get_file()
    ext = ".mp4" if not video.file_name else Path(video.file_name).suffix or ".mp4"
    dest_path = config.input_dir / f"{chat_id}_{video.file_unique_id}{ext}"
    await file.download_to_drive(custom_path=dest_path)

    logger.info(f"Video saved for chat {chat_id}: {dest_path}")

    # Update database
    await db_manager.update_session(
        chat_id,
        current_step="WAITING_TEXT",
        media_path=str(dest_path),
        media_type="video",
    )

    # Required progress message
    await update.effective_message.reply_text("Media received")
    await update.effective_message.reply_text("Send the text you want on the reel")


@restricted
async def handle_document_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document uploads that might be image or video files."""
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

        # Set context so subsequent steps know user uploaded their own image
        context.user_data["custom_media_path"] = str(dest_path)
        context.user_data["chosen_img"] = "custom_upload"
        cat = context.user_data.get("chosen_cat") or "romantic"
        context.user_data["chosen_cat"] = cat

        await db_manager.start_reel_session(chat_id)
        await db_manager.update_session(
            chat_id,
            current_step="WAITING_TEXT_SELECTION",
            media_path=str(dest_path),
            media_type="image",
            selected_template=cat,
        )

        from bot.handlers.auto import get_fresh_hook_options, build_hook_selection_keyboard, get_category_info
        cat_info = get_category_info(cat)
        fresh_hooks = await get_fresh_hook_options(chat_id, category=cat, limit=5)
        context.user_data["current_hook_options"] = fresh_hooks

        hooks_text = "\n".join([f"{idx}️⃣ _{h['text']}_" for idx, h in enumerate(fresh_hooks, start=1)])

        msg = (
            f"📸 *Custom Image Received & Loaded!*\n\n"
            f"📂 *Vibe Style:* {cat_info['icon']} *{cat_info['title']}*\n\n"
            f"Select 1 of 5 viral text quotes below, or type your own hook in chat:\n\n"
            f"{hooks_text}\n\n"
            f"_(💡 Next, an instant 1080x1920 preview with your photo + text will be shown!)_"
        )

        await update.effective_message.reply_text(
            msg,
            reply_markup=build_hook_selection_keyboard(fresh_hooks, category=cat),
            parse_mode="Markdown",
        )

    elif mime.startswith("video/"):
        max_bytes = config.max_video_size_mb * 1024 * 1024
        if doc.file_size and doc.file_size > max_bytes:
            await update.effective_message.reply_text(
                f"❌ File exceeds maximum size limit of {config.max_video_size_mb} MB."
            )
            return

        file = await doc.get_file()
        ext = Path(doc.file_name).suffix if doc.file_name else ".mp4"
        dest_path = config.input_dir / f"{chat_id}_{doc.file_unique_id}{ext}"
        await file.download_to_drive(custom_path=dest_path)

        await db_manager.update_session(
            chat_id,
            current_step="WAITING_TEXT",
            media_path=str(dest_path),
            media_type="video",
        )
        await update.effective_message.reply_text("Media received")
        await update.effective_message.reply_text("Send the text you want on the reel")
