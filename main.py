"""Main application entrypoint for Telegram Reel Maker Bot."""

import os
import sys
import threading
import time
import urllib.request
import traceback
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# ---------------------------------------------------------------------------
# 1. Early Healthcheck & Keepalive Server (Booted immediately for Cloud Platforms)
# ---------------------------------------------------------------------------
def _run_early_health_server() -> None:
    port_str = os.environ.get("PORT", "10000").strip()
    try:
        port = int(port_str) if port_str else 10000
    except ValueError:
        port = 10000

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/", "/health"):
                body = b"Telegram Reel Maker Bot is running!"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path == "/logs":
                content = ""
                if os.path.exists("crash.log"):
                    try:
                        with open("crash.log", "r", encoding="utf-8", errors="replace") as f:
                            content += "=== CRASH LOG ===\n" + f.read() + "\n\n"
                    except Exception as e:
                        content += f"Error reading crash.log: {e}\n"
                if os.path.exists("bot.log"):
                    try:
                        with open("bot.log", "r", encoding="utf-8", errors="replace") as f:
                            lines = f.readlines()
                            content += "=== BOT LOG (last 100 lines) ===\n" + "".join(lines[-100:])
                    except Exception as e:
                        content += f"Error reading bot.log: {e}\n"
                if not content:
                    content = f"Bot status: RUNNING 24/7. Current Time: {time.ctime()}\n"
                body = content.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path.startswith("/media/"):
                import shutil
                raw_filename = self.path[len("/media/"):].split("?")[0].strip()
                safe_name = os.path.basename(raw_filename)
                target_file = Path("data/output") / safe_name
                if not target_file.exists():
                    target_file = Path("data/temp") / safe_name
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
                    except Exception:
                        pass
                body = b"Media Not Found"
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            body = b"Telegram Reel Maker Bot is running!"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=False)
        thread.start()
        print(f"[HealthServer] Immediate health server listening on port {port}", flush=True)
    except Exception as e:
        print(f"[HealthServer] Warning: Could not bind port {port}: {e}", file=sys.stderr, flush=True)

    def _daemon_pinger():
        time.sleep(15)
        url = "https://insta-reel-maker-bot.onrender.com/"
        while True:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "DaemonKeepAlive/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    pass
            except Exception:
                pass
            time.sleep(120)

    pinger_thread = threading.Thread(target=_daemon_pinger, daemon=True)
    pinger_thread.start()


# Fire health server before any heavy imports
_run_early_health_server()

# ---------------------------------------------------------------------------
# 2. Crash Diagnostics & Global Logging Setup
# ---------------------------------------------------------------------------
def handle_unhandled_exception(exc_type, exc_value, exc_tb):
    err_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(f"\n--- UNCAUGHT EXCEPTION ---\n{err_text}", file=sys.stderr, flush=True)
    print(f"\n--- UNCAUGHT EXCEPTION ---\n{err_text}", file=sys.stdout, flush=True)
    try:
        with open("crash.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- CRASH AT {time.ctime()} ---\n{err_text}\n")
    except Exception:
        pass

sys.excepthook = handle_unhandled_exception

import asyncio
import logging

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
    news_command,
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

# Configure logging
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
    url = "https://insta-reel-maker-bot.onrender.com/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RenderKeepAlive/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            logger.info(f"[KeepAlive] Render web service pinged successfully (HTTP {resp.status})")
    except Exception as e:
        logger.warning(f"[KeepAlive] Render ping failed: {e}")


async def setup_bot() -> Application:
    """Verify prerequisites, restore sessions, initialize database, and register handlers."""
    logger.info("Verifying environment...")
    if not check_ffmpeg_installed():
        logger.error("❌ FFmpeg is not installed or not found in system PATH!")
        raise RuntimeError("FFmpeg is not installed or not found in system PATH")
    if not check_ffprobe_installed():
        logger.error("❌ FFprobe is not installed or not found in system PATH!")
        raise RuntimeError("FFprobe is not installed or not found in system PATH")

    logger.info(f"FFmpeg detected: {get_ffmpeg_version()}")
    logger.info(f"Configuration loaded: {config}")

    if not config.bot_token:
        logger.error(
            "❌ TELEGRAM_BOT_TOKEN is not configured!\n"
            "Please create a .env file from .env.example and set your TELEGRAM_BOT_TOKEN from @BotFather."
        )
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    # 1. Restore Instagram session files from environment variables if passed
    session_dir = Path("data/sessions")
    session_dir.mkdir(parents=True, exist_ok=True)

    ig_env = os.environ.get("INSTAGRAM_SESSION_DATA", "").strip()
    if ig_env and len(ig_env) > 50:
        try:
            (session_dir / "instagram_5381201341.json").write_text(ig_env, encoding="utf-8")
            logger.info("Restored Instagram session from INSTAGRAM_SESSION_DATA env var")
        except Exception as e:
            logger.warning(f"Could not restore Instagram session from env: {e}")

    sync_env = os.environ.get("AUDIO_SYNC_SESSION_DATA", "").strip()
    if sync_env and len(sync_env) > 50:
        try:
            (session_dir / "audio_sync_5381201341.json").write_text(sync_env, encoding="utf-8")
            logger.info("Restored Audio Sync session from AUDIO_SYNC_SESSION_DATA env var")
        except Exception as e:
            logger.warning(f"Could not restore Audio Sync session from env: {e}")

    # 2. Initialize SQLite database
    await db_manager.init_db()

    # Ensure @aryafeed.in is registered in DB if session file exists
    try:
        target_chat_id = config.admin_telegram_id or 5381201341
        session_file = session_dir / f"instagram_{target_chat_id}.json"
        if session_file.exists():
            await db_manager.save_instagram_account(
                chat_id=target_chat_id,
                username="aryafeed.in",
                session_file=str(session_file),
                auto_post=0
            )
            await db_manager.save_managed_account(
                chat_id=target_chat_id,
                alias="aryafeed",
                username="aryafeed.in",
                session_file=str(session_file),
                auto_post=0,
                engine_type="news",
                set_active=True
            )
            logger.info("Verified @aryafeed.in account in database (Auto-Post: STOPPED)")
    except Exception as e:
        logger.warning(f"Could not verify instagram account in db: {e}")

    # 3. Load previously synced Instagram songs into playlist
    try:
        from bot.services.audio_sync_service import audio_sync_service
        await audio_sync_service.load_synced_tracks_into_playlist()
    except Exception as e:
        logger.warning(f"Could not load synced tracks at startup: {e}")

    # 4. Configure robust connection and upload timeouts for video reels
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
    app.add_handler(CommandHandler(["news", "breaking"], news_command))

    # Register Global Error Handler
    app.add_error_handler(global_error_handler)

    async def periodic_news_monitor_job(context: ContextTypes.DEFAULT_TYPE) -> None:
        """Autonomous news scout: checks for breaking stories, renders and delivers/posts."""
        if os.environ.get("AUTO_NEWS_REELS", "false").lower() not in ("true", "1", "yes"):
            return
        from bot.services.live_news_service import live_news_service
        try:
            target_chat = config.admin_telegram_id or 5381201341
            active = await db_manager.get_active_account(target_chat)
            should_post = bool(active.get("auto_post", 0)) if active else False
            logger.info(f"[PeriodicNews] Scanning breaking news for chat {target_chat} (Auto-Post: {should_post})...")
            await live_news_service.create_and_publish_news_reel(
                chat_id=target_chat,
                auto_post=should_post,
                bot=context.bot,
            )
        except Exception as e:
            logger.warning(f"[PeriodicNews] Autonomous news check error: {e}")

    # Register Periodic Cleanup Job, Keep-Alive Job & Daily AutoPilot Schedulers
    if app.job_queue:
        app.job_queue.run_repeating(periodic_cleanup_job, interval=3600, first=60)
        logger.info("Scheduled retention cleanup job (interval: 1 hour)")
        app.job_queue.run_repeating(render_keep_alive_job, interval=180, first=30)
        logger.info("Registered 24/7 Keep-Alive ping job (interval: 3 mins)")
        app.job_queue.run_repeating(periodic_news_monitor_job, interval=7200, first=120)
        logger.info("Registered Autonomous Breaking News monitor job (interval: 2 hours)")
        register_autopilot_jobs(app)

    return app


async def main_async() -> None:
    """Async main routine running in a single consistent event loop with supervisor."""
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

    # 24/7 Polling Supervisor: keep container alive and restart updater if interrupted
    try:
        while True:
            await asyncio.sleep(10)
            if app.updater and not app.updater.running:
                logger.warning("[Supervisor] Updater stopped (transient conflict/network drop). Attempting restart...")
                try:
                    await app.updater.start_polling(drop_pending_updates=True, bootstrap_retries=5)
                    logger.info("[Supervisor] Updater restarted successfully!")
                except Exception as poll_err:
                    if "Conflict" in str(poll_err) or "terminated by other getUpdates" in str(poll_err):
                        logger.warning(f"[Supervisor] Transient conflict while restarting: {poll_err}. Will retry in 10s.")
                    else:
                        logger.error(f"[Supervisor] Error restarting updater: {poll_err}")
    finally:
        if app.updater and app.updater.running:
            await app.updater.stop()
        if app.running:
            await app.stop()
        await app.shutdown()


def main() -> None:
    """Run bot polling with global exception protection and persistent resurrection."""
    print(f"[{time.ctime()}] Bot process started. Main execution loop active.", flush=True)
    while True:
        try:
            print(f"[{time.ctime()}] Starting bot main_async()...", flush=True)
            asyncio.run(main_async())
        except KeyboardInterrupt:
            print(f"[{time.ctime()}] KeyboardInterrupt received. Exiting.", flush=True)
            break
        except BaseException as e:
            err_msg = traceback.format_exc()
            print(f"\n[{time.ctime()}] [RECOVERED CRITICAL EXCEPTION] {type(e).__name__}: {e}\n{err_msg}", file=sys.stderr, flush=True)
            print(f"\n[{time.ctime()}] [RECOVERED CRITICAL EXCEPTION] {type(e).__name__}: {e}\n{err_msg}", file=sys.stdout, flush=True)
            try:
                with open("crash.log", "a", encoding="utf-8") as f:
                    f.write(f"\n[{time.ctime()}] [CRITICAL {type(e).__name__}]: {e}\n{err_msg}\n")
            except Exception:
                pass
            time.sleep(5)


if __name__ == "__main__":
    main()
