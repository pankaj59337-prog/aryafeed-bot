"""Telegram command handlers: /start, /help, /templates, /status, /cancel."""

import logging
from functools import wraps
from typing import Callable
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.templates.styles import TEMPLATES
from bot.utils.cleanup import cleanup_chat_files
from bot.utils.config import config
from database.db import db_manager

logger = logging.getLogger(__name__)


def restricted(func: Callable):
    """Decorator to enforce ADMIN_TELEGRAM_ID restriction if configured."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user and not config.is_admin(user.id):
            logger.warning(f"Unauthorized access attempt by user {user.id} ({user.username})")
            if update.effective_message:
                await update.effective_message.reply_text("⛔ You are not authorized to use this bot.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


@restricted
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - welcome user to AryaFeed Engine."""
    welcome_msg = (
        "⚡ *Welcome to AryaFeed Engine \\(@aryafeed\\.in\\)\\!*\n\n"
        "I create high\\-retention, vertical *9:16 News & Curiosity Reels* "
        "autonomously with AI or from your breaking headlines\\.\n\n"
        "📰 *AryaFeed Signature Features:*\n"
        "• Yellow brand pill watermark `[ ARYAFEED.IN ]`\n"
        "• Source citation badge support `[Per Source]`\n"
        "• High\\-contrast news banner and dark scrim card styles\n"
        "• Viral debate captions & niche hashtag engine\n\n"
        "⚡ *Quick Commands:*\n"
        "• `/auto` \\- One\\-tap viral news & studio reel generator\n"
        "• `/reel` \\- Manual reel creator \\(photo/video \\+ headline \\+ music\\)\n"
        "• `/templates` \\- Browse styles \\(AryaFeed News ⚡ / Card 📰\\)\n"
        "• `/status` \\- Check active render job\n"
        "• `/account` \\- Check active publishing account\n"
        "• `/help` \\- Full command manual"
    )
    if update.effective_message:
        await update.effective_message.reply_text(welcome_msg, parse_mode="MarkdownV2")


@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "📖 *Reel Maker Bot Guide & Dual-Engine Architecture*\n\n"
        "🚀 *Dual-Engine Account Switching:*\n"
        "• `/account night` — @night_thought_12 (Engine 1: Aesthetic Autopilot)\n"
        "• `/account arya` — @aryafeed.in (Engine 2: AryaFeed Viral News)\n\n"
        "*Step 1: Media*\n"
        "• Send photos (JPG, PNG, WebP) or videos (MP4, MOV, MKV).\n"
        "• Images automatically get a smooth Ken Burns pan/zoom.\n"
        "• Non-9:16 media is intelligently fitted with a blurred background.\n"
        f"• Max video size: {config.max_video_size_mb} MB.\n\n"
        "*Step 2: Text*\n"
        "• Text wraps automatically and fits Instagram safe margins.\n"
        "• Yellow highlight accent auto-applied to impact words.\n\n"
        "*Step 3: Music*\n"
        "• Send any audio/MP3, or type /skip to keep original audio or silent track.\n"
        f"• Max audio size: {config.max_audio_size_mb} MB.\n\n"
        "*Step 4: Templates*\n"
        "• Choose from styles including AryaFeed News ⚡, AryaFeed Card 📰, Cinematic 🎬, Meme 😂, etc.\n\n"
        "Use /cancel anytime to discard an active draft."
    )
    if update.effective_message:
        await update.effective_message.reply_text(help_text, parse_mode="Markdown")


@restricted
async def templates_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /templates command."""
    msg = ["🎨 *Available Reel Templates:*\n"]
    for idx, (key, style) in enumerate(TEMPLATES.items(), 1):
        msg.append(f"*{idx}. {style.display_name}*")
        msg.append(f"_{style.description}_\n")

    msg.append("Ready to make one? Type /reel to start!")
    if update.effective_message:
        await update.effective_message.reply_text("\n".join(msg), parse_mode="Markdown")


@restricted
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    chat_id = update.effective_chat.id
    session = await db_manager.get_session(chat_id)

    if not session or session.get("current_step") == "IDLE":
        text = "ℹ️ You currently have no active reel job. Type /reel to begin!"
    else:
        step = session.get("current_step", "UNKNOWN")
        m_type = session.get("media_type") or "Not uploaded"
        has_txt = "Yes" if session.get("overlay_text") else "Pending"
        has_mus = "Yes" if session.get("music_path") else "Pending / Skipped"
        tmpl = session.get("selected_template") or "Not selected"

        text = (
            f"📊 *Current Job Status*\n\n"
            f"• *Step:* `{step}`\n"
            f"• *Media:* `{m_type}`\n"
            f"• *Text:* `{has_txt}`\n"
            f"• *Music:* `{has_mus}`\n"
            f"• *Template:* `{tmpl}`\n\n"
            f"Type /cancel to discard this draft."
        )

    if update.effective_message:
        await update.effective_message.reply_text(text, parse_mode="Markdown")


@restricted
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command."""
    chat_id = update.effective_chat.id
    await db_manager.reset_session(chat_id)
    cleanup_chat_files(chat_id)

    if update.effective_message:
        await update.effective_message.reply_text("🛑 Current reel creation cancelled. Type /reel to start fresh!")


@restricted
async def sync_music_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /sync_music command to pull saved & liked reels audio from Instagram into playlist."""
    chat_id = update.effective_chat.id
    status_msg = None
    if update.effective_message:
        status_msg = await update.effective_message.reply_text(
            "🔄 *Scanning your Instagram Saved & Liked Reels for trending audio...*\nPlease wait a moment.",
            parse_mode="Markdown",
        )

    try:
        from bot.services.audio_sync_service import audio_sync_service
        from bot.services.music_service import VOCAL_TRACKS

        synced = await audio_sync_service.sync_from_instagram(chat_id)

        if synced:
            lines = [f"🎵 *Synced {len(synced)} New Trending Song(s) from Instagram!*\n"]
            for s in synced:
                lines.append(f"• *{s['title']}* — _{s['artist']}_")
            lines.append(f"\n🎧 *Total Active Playlist Size:* {len(VOCAL_TRACKS)} tracks")
            lines.append("⚡ _These sounds will now be automatically featured in your upcoming scheduled reels!_")
            text = "\n".join(lines)
        else:
            text = (
                f"✅ *Audio Library is Up to Date!*\n\n"
                f"• Active Tracks in Playlist: *{len(VOCAL_TRACKS)}*\n"
                f"• No new unsynced saved/liked reels found.\n\n"
                f"💡 _Tip: Like (❤️) or Save (🔖) any reel on Instagram while scrolling, then run /sync_music!_"
            )

        if status_msg:
            await status_msg.edit_text(text, parse_mode="Markdown")
        elif update.effective_message:
            await update.effective_message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        err_text = f"⚠️ *Error syncing Instagram music:*\n{e}"
        if status_msg:
            await status_msg.edit_text(err_text, parse_mode="Markdown")
        elif update.effective_message:
            await update.effective_message.reply_text(err_text, parse_mode="Markdown")


@restricted
async def sync_folder_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /sync_folder command to select or view the Instagram Saved collection used for music sync."""
    chat_id = update.effective_chat.id
    from bot.services.audio_sync_service import audio_sync_service

    status_msg = None
    if update.effective_message:
        status_msg = await update.effective_message.reply_text("📂 *Loading your Instagram Saved Folders...*", parse_mode="Markdown")

    try:
        colls = await audio_sync_service.get_collections(chat_id)
        if not colls:
            msg = "⚠️ *Could not fetch Instagram folders.*\nEnsure your scout account is connected with `/scout_session <cookie>`."
            if status_msg:
                await status_msg.edit_text(msg, parse_mode="Markdown")
            return

        current_target = await audio_sync_service.get_target_collection(chat_id)
        current_id = current_target.get("id") or "ALL_MEDIA_AUTO_COLLECTION"

        # Check if user passed folder name as argument: /sync_folder <name>
        args = context.args or []
        if args:
            search_name = " ".join(args).strip().lower()
            matched = next((c for c in colls if search_name in c["name"].lower()), None)
            if matched:
                await audio_sync_service.set_target_collection(chat_id, matched["id"], matched["name"])
                text = (
                    f"✅ *Audio Sync Folder Updated!*\n\n"
                    f"📁 **Active Folder:** `{matched['name']}`\n\n"
                    f"Ab se aap Instagram par jab bhi iss folder me koi reel save karenge, "
                    f"bot `/sync_music` chalane par sirf isi folder se trending music pick karega! 🎧"
                )
                if status_msg:
                    await status_msg.edit_text(text, parse_mode="Markdown")
                return
            else:
                avail = ", ".join([f"`{c['name']}`" for c in colls])
                text = f"❌ *Folder '{search_name}' not found.*\nAvailable folders: {avail}"
                if status_msg:
                    await status_msg.edit_text(text, parse_mode="Markdown")
                return

        # Render interactive buttons
        buttons = []
        for c in colls:
            is_active = (c["id"] == current_id)
            label = f"{'✅ ' if is_active else '📁 '}{c['name']}"
            buttons.append([InlineKeyboardButton(text=label, callback_data=f"sync_fold_{c['id']}")])

        # Option for all posts
        is_all = (current_id == "ALL_MEDIA_AUTO_COLLECTION" or not current_id)
        buttons.append([InlineKeyboardButton(
            text=f"{'✅ ' if is_all else '🌐 '}All Saved Posts (Default)",
            callback_data="sync_fold_ALL_MEDIA_AUTO_COLLECTION"
        )])

        reply_markup = InlineKeyboardMarkup(buttons)
        text = (
            "📁 *Select Instagram Saved Folder for Music Sync:*\n\n"
            "Choose the folder where you save reels with trending songs.\n"
            "The bot will scout audio *only* from your chosen folder!\n\n"
            f"• Current Active: *{current_target.get('name') or 'All Saved Posts'}*"
        )
        if status_msg:
            await status_msg.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        elif update.effective_message:
            await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        err = f"⚠️ *Error getting folders:* {e}"
        if status_msg:
            await status_msg.edit_text(err, parse_mode="Markdown")


async def handle_sync_folder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle clicking on a folder selection button."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    chat_id = update.effective_chat.id
    target_id = data.replace("sync_fold_", "").strip()

    from bot.services.audio_sync_service import audio_sync_service

    if target_id == "ALL_MEDIA_AUTO_COLLECTION":
        await audio_sync_service.set_target_collection(chat_id, "ALL_MEDIA_AUTO_COLLECTION", "All Saved Posts")
        folder_name = "All Saved Posts"
    else:
        colls = await audio_sync_service.get_collections(chat_id)
        matched = next((c for c in colls if c["id"] == target_id), None)
        folder_name = matched["name"] if matched else "Selected Folder"
        await audio_sync_service.set_target_collection(chat_id, target_id, folder_name)

    await query.edit_message_text(
        f"✅ *Audio Sync Folder Updated!*\n\n"
        f"📁 **Active Folder:** `{folder_name}`\n\n"
        f"Ab se aap jab bhi Instagram par iss folder me koi reel save karenge, "
        f"bot `/sync_music` me sirf isi folder se trending audio pick karega! 🎧\n\n"
        f"_Tip: Try saving 1-2 reels into this folder, then type /sync_music!_",
        parse_mode="Markdown"
    )


@restricted
async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch latest breaking news, render 1080x1920 reel with [ ARYAFEED ], and deliver/post."""
    chat_id = update.effective_chat.id
    msg = await update.effective_message.reply_text("⚡ *Scanning breaking Indian news feeds...*", parse_mode="Markdown")

    from bot.services.live_news_service import live_news_service
    try:
        args = context.args or []
        should_post = "post" in [a.lower() for a in args] or False

        await msg.edit_text("📰 *Found breaking story! Rendering 1080x1920 ARYAFEED Reel...*", parse_mode="Markdown")

        res = await live_news_service.create_and_publish_news_reel(
            chat_id=chat_id,
            auto_post=should_post,
            bot=context.bot,
        )

        if not res.get("success"):
            await msg.edit_text(f"⚠️ *News Reel Error:* {res.get('error')}", parse_mode="Markdown")
            return

        try:
            await msg.delete()
        except Exception:
            pass
    except Exception as e:
        logger.exception(f"Error in news_command: {e}")
        await msg.edit_text(f"⚠️ *Error generating news reel:* {e}", parse_mode="Markdown")

