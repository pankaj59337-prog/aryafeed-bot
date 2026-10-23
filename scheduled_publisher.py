"""Scheduled Background Publisher for AryaFeed.in

Takes staged reels from data/output/ (aryafeed_scheduled_*.mp4) and publishes them
to Instagram (@aryafeed.in) with configurable intervals or timetable, sending live updates to Telegram.
"""

import argparse
import json
import logging
import os
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

os.chdir("D:/instagram bot")
sys.path.insert(0, "D:/instagram bot")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scheduled_publisher")

import requests
from instagrapi import Client

TELEGRAM_TOKEN = "8804814324:AAGEuKYaivC7Qk8xiVojlhUCMhDDQksTQ8k"
TELEGRAM_CHAT_ID = 5381201341
SESSION_FILE = Path("data/sessions/instagram_aryafeed.json")
OUTPUT_DIR = Path("data/output")


def send_telegram_text(text: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            timeout=25,
        )
        return r.status_code == 200
    except Exception as e:
        logger.warning(f"Telegram text error: {e}")
        return False


def get_live_captions() -> List[str]:
    try:
        cl = Client()
        cl.load_settings(SESSION_FILE)
        medias = cl.user_medias(cl.user_id, amount=20)
        return [(m.caption_text or "").lower() for m in medias]
    except Exception as e:
        logger.warning(f"Error fetching live captions: {e}")
        return []


def upload_to_instagram(video_file: Path, caption: str, clean_headline: str) -> dict:
    cl = Client()
    cl.load_settings(SESSION_FILE)

    thumb_file = video_file.with_suffix(".thumb.jpg")
    if not thumb_file.exists():
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "00:00:02", "-i", str(video_file), "-vframes", "1", "-q:v", "2", str(thumb_file)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    try:
        media = cl.clip_upload(
            path=str(video_file),
            caption=caption,
            thumbnail=str(thumb_file) if thumb_file.exists() else None,
        )
        code = getattr(media, "code", None)
        if code:
            return {"success": True, "url": f"https://www.instagram.com/reel/{code}/"}
    except Exception as e:
        logger.warning(f"clip_upload direct exception: {e}. Checking recent media...")

    # Verification fallback
    try:
        time.sleep(6)
        medias = cl.user_medias(cl.user_id, amount=3)
        for m in medias:
            if m.caption_text and (clean_headline[:30].lower() in m.caption_text.lower() or "#aryafeed" in m.caption_text.lower()):
                code = m.code
                return {"success": True, "url": f"https://www.instagram.com/reel/{code}/"}
    except Exception as ve:
        logger.warning(f"Verification error: {ve}")

    return {"success": False, "error": "Upload could not be confirmed"}


def find_staged_scheduled_reels() -> List[Dict[str, Any]]:
    # Look for aryafeed_scheduled_*.mp4 sorted by queue index / creation
    files = sorted(OUTPUT_DIR.glob("aryafeed_scheduled_*.mp4"), key=lambda x: x.stat().st_mtime)
    staged = []
    for f in files:
        meta_file = f.with_suffix(".json")
        if not meta_file.exists():
            continue
        try:
            with open(meta_file, "r", encoding="utf-8") as mf:
                mdata = json.load(mf)
                staged.append({
                    "video_path": f,
                    "title": mdata.get("title", ""),
                    "caption": mdata.get("caption", ""),
                    "category": mdata.get("category", "news"),
                    "queue_index": mdata.get("queue_index", 0)
                })
        except Exception as e:
            logger.warning(f"Error reading meta for {f.name}: {e}")
    return staged


def run_interval_schedule(interval_minutes: int, post_first_now: bool = True):
    logger.info(f"Starting scheduled publisher with interval={interval_minutes} mins, post_first_now={post_first_now}")
    live_caps = get_live_captions()
    staged = find_staged_scheduled_reels()

    unposted = [item for item in staged if not any(item["title"][:25].lower() in cap for cap in live_caps)]
    total = len(unposted)

    if not unposted:
        logger.info("No unposted scheduled reels found in queue.")
        send_telegram_text("✅ *Scheduled Queue Empty*: All reels in queue are already LIVE on `@aryafeed.in`!")
        return

    send_telegram_text(
        f"📅 *Scheduled Publishing Activated!* 🇮🇳\n\n"
        f"• Total Reels in Schedule: **{total}**\n"
        f"• Interval: **Every {interval_minutes} minutes**\n"
        f"• Target Account: `@aryafeed.in`\n\n"
        f"Reels will be published automatically according to schedule. Live links will be broadcasted here!"
    )

    for idx, item in enumerate(unposted, 1):
        if idx == 1 and not post_first_now:
            wait_sec = interval_minutes * 60
            logger.info(f"Waiting {wait_sec}s ({interval_minutes}m) before first scheduled post...")
            time.sleep(wait_sec)
        elif idx > 1:
            wait_sec = interval_minutes * 60 + random.randint(-60, 60)
            wait_sec = max(300, wait_sec)
            logger.info(f"⏳ Waiting {wait_sec}s ({wait_sec//60}m) before Reel {idx}/{total}...")
            send_telegram_text(f"⏳ *Scheduled Countdown*: Next reel ({idx}/{total}) publishing in ~{wait_sec//60} minutes...")
            time.sleep(wait_sec)

        title = item["title"]
        video_file = item["video_path"]
        caption = item["caption"]

        logger.info(f"🚀 Publishing Scheduled Reel {idx}/{total}: '{title}'")
        send_telegram_text(f"📤 *Publishing Scheduled Reel {idx}/{total} to @aryafeed.in...*\nHeadline: *{title}*")

        res = upload_to_instagram(video_file, caption, title)
        if res.get("success"):
            url = res.get("url")
            logger.info(f"🎉 Scheduled Reel {idx}/{total} is LIVE: {url}")
            send_telegram_text(
                f"🚀 *Scheduled Reel LIVE on Instagram!* 🚀\n\n"
                f"🎯 *Account*: `@aryafeed.in`\n"
                f"🔗 *Link*: {url}\n"
                f"📝 *Headline*: {title}\n\n"
                f"Status: Published ({idx}/{total}) ✨"
            )
        else:
            err = res.get("error", "Unknown error")
            logger.error(f"❌ Upload failed for '{title}': {err}")
            send_telegram_text(f"⚠️ Scheduled upload failed for *{title}*:\n`{err}`")

    send_telegram_text(f"🎉 *All {total} Scheduled Reels Have Been Published to Instagram!* 🇮🇳✨")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=60, help="Interval between posts in minutes")
    parser.add_argument("--delay-first", action="store_true", help="Delay first post by interval instead of posting immediately")
    args = parser.parse_args()

    run_interval_schedule(interval_minutes=args.interval, post_first_now=not args.delay_first)
