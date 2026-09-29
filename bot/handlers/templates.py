"""Audio ingestion, template selection, and final reel rendering."""

import logging
from pathlib import Path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.handlers.commands import restricted
from bot.services.caption_generator import generate_instagram_caption
from bot.services.instagram_service import instagram_service
from bot.services.render_service import execute_render_job
from bot.templates.styles import TEMPLATES
from bot.utils.cleanup import cleanup_chat_files
from bot.utils.config import config
from database.db import db_manager

logger = logging.getLogger(__name__)


def build_template_keyboard() -> InlineKeyboardMarkup:
    """Build interactive inline buttons for available templates."""
    keyboard = [
        [
            InlineKeyboardButton("⚡ AryaFeed News", callback_data="tmpl_news_banner"),
            InlineKeyboardButton("📰 AryaFeed Card", callback_data="tmpl_news_card"),
        ],
        [
            InlineKeyboardButton("🎬 Cinematic", callback_data="tmpl_cinematic"),
            InlineKeyboardButton("😂 Meme", callback_data="tmpl_meme"),
        ],
        [
            InlineKeyboardButton("💖 Romantic", callback_data="tmpl_romantic"),
            InlineKeyboardButton("📜 Quote", callback_data="tmpl_quote"),
        ],
        [
            InlineKeyboardButton("✨ Minimal", callback_data="tmpl_minimal"),
            InlineKeyboardButton("💋 Sexy / Hot", callback_data="tmpl_sexy"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


@restricted
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle audio/mp3/voice message when in WAITING_MUSIC step."""
    chat_id = update.effective_chat.id
    session = await db_manager.get_session(chat_id)

    if not session or session.get("current_step") != "WAITING_MUSIC":
        return

    audio = update.effective_message.audio or update.effective_message.voice
    if not audio:
        # Check if sent as audio document
        doc = update.effective_message.document
        if doc and doc.mime_type and doc.mime_type.startswith("audio/"):
            audio = doc

    if not audio:
        await update.effective_message.reply_text(
            "Please send a valid audio/MP3 file, or type /skip to proceed without custom music."
        )
        return

    # Check file size
    max_bytes = config.max_audio_size_mb * 1024 * 1024
    if audio.file_size and audio.file_size > max_bytes:
        await update.effective_message.reply_text(
            f"❌ Audio file exceeds maximum limit of {config.max_audio_size_mb} MB. Send a smaller file or /skip."
        )
        return

    file = await audio.get_file()
    dest_path = config.audio_dir / f"{chat_id}_{audio.file_unique_id}.mp3"
    await file.download_to_drive(custom_path=dest_path)

    # Update database
    await db_manager.update_session(
        chat_id,
        current_step="WAITING_TEMPLATE",
        music_path=str(dest_path),
    )

    # Required progress message
    await update.effective_message.reply_text("Music received")

    # Ask user to select template
    await update.effective_message.reply_text(
        "Choose a template style for your reel:",
        reply_markup=build_template_keyboard(),
    )


@restricted
async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /skip command to proceed without custom audio."""
    chat_id = update.effective_chat.id
    session = await db_manager.get_session(chat_id)

    if not session or session.get("current_step") != "WAITING_MUSIC":
        await update.effective_message.reply_text("Nothing to skip right now. Type /reel to start a new reel.")
        return

    await db_manager.update_session(
        chat_id,
        current_step="WAITING_TEMPLATE",
        music_path=None,
    )

    await update.effective_message.reply_text("Music skipped.")
    await update.effective_message.reply_text(
        "Choose a template style for your reel:",
        reply_markup=build_template_keyboard(),
    )


@restricted
async def handle_template_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle template button callback and trigger rendering."""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    data = query.data or ""

    if not data.startswith("tmpl_"):
        return

    template_key = data.replace("tmpl_", "")
    if template_key not in TEMPLATES:
        template_key = "cinematic"

    session = await db_manager.get_session(chat_id)
    if not session:
        await query.edit_message_text("Session expired. Please type /reel to start again.")
        return

    await db_manager.update_session(
        chat_id,
        selected_template=template_key,
    )

    # Edit callback message with confirmation
    style = TEMPLATES[template_key]
    await query.edit_message_text(f"Selected: *{style.display_name}*", parse_mode="Markdown")

    # Required progress message
    status_msg = await context.bot.send_message(chat_id=chat_id, text="Rendering your reel...")

    # 1. Execute rendering job
    try:
        final_video_path = await execute_render_job(chat_id)
    except Exception as e:
        logger.exception(f"Rendering failed for chat {chat_id}: {e}")
        # Required user-facing error message
        await context.bot.send_message(
            chat_id=chat_id,
            text="Rendering failed. Please try again.",
        )
        return

    # 2. Send final video to Telegram with generous timeouts
    try:
        insta_acc = await instagram_service.is_connected(chat_id)
        reply_markup = None
        if insta_acc and not insta_acc.get("auto_post"):
            reply_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("🚀 Post to Instagram Now", callback_data="post_insta")
            ]])

        with open(final_video_path, "rb") as video_file:
            await context.bot.send_video(
                chat_id=chat_id,
                video=video_file,
                caption="🎬 *Your Reel is Ready!*",
                parse_mode="Markdown",
                supports_streaming=True,
                width=1080,
                height=1920,
                reply_markup=reply_markup,
                write_timeout=180.0,
                read_timeout=180.0,
            )

        if insta_acc and insta_acc.get("auto_post"):
            async def _bg_publish_tmpl():
                try:
                    hook_text = session.get("overlay_text") or "Late night thoughts 🌚💋"
                    ig_caption = generate_instagram_caption(hook_text, style=template_key)
                    res = await instagram_service.upload_reel(chat_id, final_video_path, caption=ig_caption)
                    if res.get("success"):
                        url = res.get("url") or "Instagram Feed"
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"🚀 *Auto-Posted to Instagram!*\n🔗 [View Reel on Instagram]({url})",
                            parse_mode="Markdown"
                        )
                except Exception as ex:
                    logger.warning(f"Auto-post failed in template flow: {ex}")

            asyncio.create_task(_bg_publish_tmpl())

        # Cleanup intermediate user files
        cleanup_chat_files(chat_id)
    except Exception as upload_err:
        logger.warning(f"Notice during video upload for chat {chat_id}: {upload_err}")
