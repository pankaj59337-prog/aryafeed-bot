"""Main application entrypoint for Telegram Reel Maker Bot."""

import asyncio
import logging
import sys
import traceback

def handle_unhandled_exception(exc_type, exc_value, exc_tb):
    with open("crash.log", "a", encoding="utf-8") as f:
        f.write(f"\n--- CRASH AT {asyncio.get_event_loop() if hasattr(asyncio, 'get_event_loop') else ''} ---\n")
        traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
sys.excepthook = handle_unhandled_exception

from telegram import Update
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.handlers.commands import (
    cancel_command,
    help_command,
    start_command,
    status_command,
    sync_music_command,
    sync_folder_command,
    handle_sync_folder_callback,
    templates_command,
)
from bot.handlers.media import (
    handle_document_media,
    handle_photo,
    handle_video,
    reel_command,
)
from bot.handlers.templates import (
    handle_audio,
    handle_template_selection,
    skip_command,
)
from bot.handlers.text import handle_overlay_text
from bot.handlers.auto import (
    auto_command,
    handle_auto_callbacks,
    reset_history_command,
    set_gemini_key_command,
    set_openai_key_command,
)
from bot.services.autopilot import (
    autopilot_command,
    handle_autopilot_callbacks,
    register_autopilot_jobs,
    testing_mode_command,
)
from bot.handlers.instagram_handler import (
    insta_login_command,
    insta_2fa_command,
    insta_session_command,
    scout_session_command,
    insta_status_command,
    insta_autopost_command,
    insta_logout_command,
    handle_post_to_insta_callback,
    insta_graph_command,
    insta_graph_status_command,
    account_command,
    handle_account_callbacks,
)
from bot.utils.cleanup import cleanup_expired_outputs
from bot.utils.config import config, mask_token
from bot.utils.ffmpeg_check import check_ffmpeg_installed, check_ffprobe_installed, get_ffmpeg_version
from database.db import db_manager

# Ensure UTF-8 output encoding across Windows and POSIX (console & pythonw safe)
log_handlers = [logging.FileHandler("bot.log", encoding="utf-8")]
if sys.stdout is not None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    log_handlers.append(logging.StreamHandler(sys.stdout))

# Configure logging
logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s",
    level=logging.INFO,
    handlers=log_handlers,
)
logger = logging.getLogger("reel_bot")


async def periodic_cleanup_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scheduled task to clean expired output files."""
    cleaned = cleanup_expired_outputs(config.output_retention_hours)
    if cleaned > 0:
        logger.info(f"Periodic cleanup: deleted {cleaned} expired output reels")


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log uncaught exceptions to prevent bot from crashing."""
    err_str = str(context.error) if context and context.error else ""
    if "Conflict" in err_str or "terminated by other getUpdates" in err_str:
        logger.warning(f"[Deploy] Handled transient Telegram conflict during container handoff: {err_str}")
        return

    logger.error("Exception occurred while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ An unexpected error occurred. Please try again with /reel or type /cancel."
            )
        except Exception:
            pass


async def render_keep_alive_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodically ping Render web service to prevent Free Tier from sleeping."""
    import urllib.request
    url = "https://insta-reel-maker-bot.onrender.com/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RenderKeepAlive/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            logger.info(f"[KeepAlive] Render web service pinged successfully (HTTP {resp.status})")
    except Exception as e:
        logger.warning(f"[KeepAlive] Render ping failed: {e}")


async def setup_bot() -> Application:
    """Verify prerequisites, initialize database, and register handlers."""
    logger.info("Verifying environment...")
    if not check_ffmpeg_installed():
        logger.error("❌ FFmpeg is not installed or not found in system PATH!")
        sys.exit(1)
    if not check_ffprobe_installed():
        logger.error("❌ FFprobe is not installed or not found in system PATH!")
        sys.exit(1)

    logger.info(f"FFmpeg detected: {get_ffmpeg_version()}")
    logger.info(f"Configuration loaded: {config}")

    if not config.bot_token:
        logger.error(
            "❌ TELEGRAM_BOT_TOKEN is not configured!\n"
            "Please create a .env file from .env.example and set your TELEGRAM_BOT_TOKEN from @BotFather."
        )
        sys.exit(1)

    # Initialize SQLite database
    await db_manager.init_db()

    # Load previously synced Instagram songs into playlist
    try:
        from bot.services.audio_sync_service import audio_sync_service
        await audio_sync_service.load_synced_tracks_into_playlist()
    except Exception as e:
        logger.warning(f"Could not load synced tracks at startup: {e}")

    # Configure robust connection and upload timeouts for video reels
    request_config = HTTPXRequest(
        connection_pool_size=16,
        connect_timeout=30.0,
        read_timeout=180.0,
        write_timeout=180.0,
    )

    # Build Telegram Bot application
    app = ApplicationBuilder().token(config.bot_token).request(request_config).build()

    # Register Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("templates", templates_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("reel", reel_command))
    app.add_handler(CommandHandler("skip", skip_command))
    app.add_handler(CommandHandler("auto", auto_command))
    app.add_handler(CommandHandler("reset_history", reset_history_command))
    app.add_handler(CommandHandler("set_gemini_key", set_gemini_key_command))
    app.add_handler(CommandHandler("set_openai_key", set_openai_key_command))
    app.add_handler(CommandHandler(["sync_music", "sync_audio", "sync_songs"], sync_music_command))
    app.add_handler(CommandHandler(["sync_folder", "scout_folder"], sync_folder_command))

    # Register Media & Content Handlers
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO | filters.ANIMATION, handle_video))
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, handle_audio))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_overlay_text))

    # Register Callback Query Handlers (Template selection & Autonomous)
    app.add_handler(CallbackQueryHandler(handle_template_selection, pattern=r"^tmpl_"))
    app.add_handler(CallbackQueryHandler(handle_auto_callbacks, pattern=r"^(cat_|pick_|shuffle_|back_|auto_|reel_|gen_|fetch_|reset_|upload_|studio_)"))
    app.add_handler(CallbackQueryHandler(handle_post_to_insta_callback, pattern=r"^post_insta"))
    app.add_handler(CallbackQueryHandler(handle_autopilot_callbacks, pattern=r"^(autopilot_|cancel_autopost_|post_now_|user_posting_)"))
    app.add_handler(CallbackQueryHandler(handle_account_callbacks, pattern=r"^switch_acc_"))
    app.add_handler(CallbackQueryHandler(handle_sync_folder_callback, pattern=r"^sync_fold_"))

    # Register Autopilot & Instagram Commands
    app.add_handler(CommandHandler(["autopilot", "schedule"], autopilot_command))
    app.add_handler(CommandHandler(["testing_mode", "test_mode", "testing"], testing_mode_command))
    app.add_handler(CommandHandler(["account", "accounts"], account_command))
    app.add_handler(CommandHandler("insta_login", insta_login_command))
    app.add_handler(CommandHandler("insta_2fa", insta_2fa_command))
    app.add_handler(CommandHandler("insta_session", insta_session_command))
    app.add_handler(CommandHandler(["scout_session", "sync_session"], scout_session_command))
    app.add_handler(CommandHandler("insta_status", insta_status_command))
    app.add_handler(CommandHandler("insta_autopost", insta_autopost_command))
    app.add_handler(CommandHandler("insta_logout", insta_logout_command))
    app.add_handler(CommandHandler("insta_graph", insta_graph_command))
    app.add_handler(CommandHandler("insta_graph_status", insta_graph_status_command))

    # Register Global Error Handler
    app.add_error_handler(global_error_handler)

    # Register Periodic Cleanup Job, Keep-Alive Job & Daily AutoPilot Schedulers
    if app.job_queue:
        app.job_queue.run_repeating(periodic_cleanup_job, interval=3600, first=60)
        logger.info("Scheduled retention cleanup job (interval: 1 hour)")
        app.job_queue.run_repeating(render_keep_alive_job, interval=180, first=30)
        logger.info("Registered 24/7 Keep-Alive ping job (interval: 3 mins)")
        register_autopilot_jobs(app)

    return app


def start_health_server() -> None:
    """Run lightweight HTTP healthcheck server for cloud hosting (Render, Koyeb, Railway)."""
    import os
    import threading
    import time
    import urllib.request
    from http.server import HTTPServer, BaseHTTPRequestHandler

    port_str = os.environ.get("PORT")
    if not port_str:
        return

    port = int(port_str)

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/logs":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                try:
                    with open("bot.log", "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                        self.wfile.write("".join(lines[-100:]).encode("utf-8"))
                except Exception as e:
                    self.wfile.write(f"Error reading bot.log: {e}".encode("utf-8"))
                return
            if self.path.startswith("/media/"):
                import shutil
                from bot.utils.config import config
                raw_filename = self.path[len("/media/"):].split("?")[0].strip()
                safe_name = os.path.basename(raw_filename)
                target_file = config.output_dir / safe_name
                if not target_file.exists():
                    target_file = config.temp_dir / safe_name
                if target_file.exists() and target_file.is_file():
                    try:
                        file_size = target_file.stat().st_size
                        self.send_response(200)
                        self.send_header("Content-Type", "video/mp4")
                        self.send_header("Content-Length", str(file_size))
                        self.send_header("Accept-Ranges", "bytes")
                        self.end_headers()
                        with open(target_file, "rb") as f:
                            shutil.copyfileobj(f, self.wfile)
                        return
                    except Exception as e:
                        logger.warning(f"Error streaming media {safe_name}: {e}")
                        return
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Media Not Found")
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Telegram Reel Maker Bot is running!")

        def log_message(self, format, *args):
            pass

    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"Healthcheck server listening on port {port}")

        # Additional daemon thread pinger for Render 24/7 uptime
        def _daemon_pinger():
            time.sleep(45)
            url = "https://insta-reel-maker-bot.onrender.com/"
            while True:
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "DaemonKeepAlive/1.0"})
                    urllib.request.urlopen(req, timeout=20)
                except Exception:
                    pass
                time.sleep(180)

        pinger_thread = threading.Thread(target=_daemon_pinger, daemon=True)
        pinger_thread.start()
        logger.info("Keep-alive daemon thread started (pings every 3 minutes)")
    except Exception as e:
        logger.warning(f"Could not start healthcheck server on port {port}: {e}")


async def main_async() -> None:
    """Async main routine running in a single consistent event loop."""
    app = await setup_bot()
    await app.initialize()
    await app.start()
    if app.updater:
        for attempt in range(12):
            try:
                await app.updater.start_polling(drop_pending_updates=True, bootstrap_retries=5)
                break
            except Exception as e:
                if "Conflict" in str(e) or "terminated by other getUpdates" in str(e):
                    logger.warning(f"[Deploy] Telegram conflict (old instance shutting down). Retrying in 5s (attempt {attempt+1}/12)...")
                    await asyncio.sleep(5)
                else:
                    raise
    logger.info("🚀 Night Thought Reel Bot is running and polling for updates...")

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        if app.updater and app.updater.running:
            await app.updater.stop()
        if app.running:
            await app.stop()
        await app.shutdown()


def main() -> None:
    """Run bot polling."""
    try:
        start_health_server()
        asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        with open("crash.log", "a", encoding="utf-8") as f:
            f.write(f"\n[FATAL MAIN EXCEPTION]: {traceback.format_exc()}\n")
        logger.error(f"Fatal error in main: {e}", exc_info=True)




if __name__ == "__main__":
    main()
