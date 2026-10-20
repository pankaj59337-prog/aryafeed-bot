"""Text overlay input handler."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.commands import restricted
from database.db import db_manager

logger = logging.getLogger(__name__)


@restricted
async def handle_overlay_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Capture overlay text from user when in WAITING_TEXT step."""
    chat_id = update.effective_chat.id
    session = await db_manager.get_session(chat_id)

    step = session.get("current_step") if session else None

    if step == "WAITING_STUDIO_TEXT" or context.user_data.get("waiting_for_custom_text"):
        text = update.effective_message.text.strip()
        context.user_data["waiting_for_custom_text"] = False
        from bot.handlers.auto import handle_studio_custom_text_input
        await handle_studio_custom_text_input(update, context, custom_text=text)
        return

    if step in ("WAITING_AI_TEXT", "WAITING_CUSTOM_TEXT"):
        text = update.effective_message.text.strip()
        from bot.handlers.auto import complete_custom_reel_flow
        await complete_custom_reel_flow(update, context, custom_text=text)
        return

    if step == "WAITING_SONG_NAME":
        song_name = update.effective_message.text.strip()
        from bot.handlers.auto import handle_song_name_input
        await handle_song_name_input(update, context, song_name=song_name)
        return

    # Check if user replies that they are posting themselves
    raw_lower = (update.effective_message.text or "").strip().lower()
    user_post_keywords = [
        "mai kar raha", "main kar raha", "mai karunga", "main karunga", "khud karunga",
        "posted", "done", "myself", "i will post", "ill post", "i'll post", "posting",
        "i am posting", "i'm posting", "skip post", "cancel post"
    ]
    if any(k in raw_lower for k in user_post_keywords):
        from bot.services.autopilot import PENDING_AUTO_POSTS
        found_any = False
        for pid, pdata in PENDING_AUTO_POSTS.items():
            if pdata.get("chat_id") == chat_id and pdata.get("status") == "pending":
                pdata["status"] = "user_handled"
                found_any = True
        if found_any:
            await update.effective_message.reply_text(
                "✋ *Auto-Post Cancelled!*\n\n"
                "Marked as self-posting — the bot will **NOT** upload to Instagram to avoid duplicate posts! 👍",
                parse_mode="Markdown",
            )
            return

    if not session or step != "WAITING_TEXT":
        # Check if user sent a quick trigger command like 'image', 'video', 'sexy'
        from bot.handlers.auto import handle_quick_text_triggers
        handled = await handle_quick_text_triggers(update, context)
        if not handled and update.effective_message:
            await update.effective_message.reply_text(
                "💡 *Quick Tip:*\n"
                "• Send /reel to choose style and generate a new reel!\n"
                "• Type `sexy`, `romantic`, or `reel` anytime to begin.",
                parse_mode="Markdown",
            )
        return

    text = update.effective_message.text
    if not text or not text.strip():
        await update.effective_message.reply_text("Please enter non-empty text for your reel.")
        return

    # Update database
    await db_manager.update_session(
        chat_id,
        current_step="WAITING_MUSIC",
        overlay_text=text.strip(),
    )

    # Required progress message
    await update.effective_message.reply_text("Text received")
    await update.effective_message.reply_text("Send an MP3/audio file or type /skip")
