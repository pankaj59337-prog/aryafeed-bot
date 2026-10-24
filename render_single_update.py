"""Generate and Deliver a Fresh Breaking News Update to Telegram

Topic:
Daily-Wage Worker's Son Cracks IIT-JEE with Top AIR Rank Without Coaching
"""

import json
import logging
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

os.chdir("D:/instagram bot")
sys.path.insert(0, "D:/instagram bot")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("give_update_direct")

import requests
from bot.services.video_engine import render_complete_reel

TELEGRAM_TOKEN = "8804814324:AAGEuKYaivC7Qk8xiVojlhUCMhDDQksTQ8k"
TELEGRAM_CHAT_ID = 5381201341
OUTPUT_DIR = Path("data/output")
TEMP_DIR = Path("data/temp")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


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


def send_telegram_video(video_path: Path, caption: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
    try:
        if not video_path.exists():
            return False
        with open(video_path, "rb") as f:
            r = requests.post(
                url,
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "supports_streaming": True},
                files={"video": (video_path.name, f, "video/mp4")},
                timeout=120,
            )
            return r.status_code == 200
    except Exception as e:
        logger.warning(f"Telegram video error: {e}")
        return False


def get_curated_track(category_preference: str) -> Optional[Path]:
    primary_dir = Path("assets/music") / category_preference
    pool = list(primary_dir.glob("*.mp3")) if primary_dir.exists() else []
    if pool:
        return random.choice(pool)

    combined = (
        list(Path("assets/music/national").glob("*.mp3"))
        + list(Path("assets/music/aura").glob("*.mp3"))
        + list(Path("assets/music/news").glob("*.mp3"))
    )
    return random.choice(combined) if combined else None


def generate_varied_caption(clean_title: str) -> str:
    lead_emojis = ["⚡", "🇮🇳✨", "🔥", "📢", "🚨", "📈"]
    hooks = [
        f"{random.choice(lead_emojis)} Breaking Update: {clean_title}",
        f"{random.choice(lead_emojis)} Inspiring Headline: {clean_title}",
        f"{random.choice(lead_emojis)} National Update: {clean_title}",
        f"Big development today! {random.choice(lead_emojis)}\n{clean_title}",
    ]
    ctas = [
        "What are your thoughts on this? Tell us in the comments 👇",
        "Drop your honest opinion below 👇✨",
        "Share this inspiring story with someone who needs motivation today! 📢",
        "Daily positive news & national pride updates ke liye follow karein @aryafeed.in 🇮🇳",
    ]
    hashtags = [
        ["#aryafeed", "#breakingnews", "#iitjee", "#inspiration", "#upscmotivation", "#viralreels"],
        ["#aryafeed", "#newsupdate", "#trendingnews", "#india", "#reelsindia", "#hardwork"],
        ["#aryafeed", "#headlines", "#todaynews", "#explorepage", "#viralreel", "#success"],
    ]
    h = random.choice(hooks)
    c = random.choice(ctas)
    t = " ".join(random.choice(hashtags))
    return f"{h}\n\n{c}\n\n{t}"


def main():
    logger.info("Generating Fresh Breaking News Update...")

    send_telegram_text(
        "⚡ *Breaking News Update Requested!* 🇮🇳\n\n"
        "Generating fresh AryaFeed reel preview for Telegram queue..."
    )

    clean = "Son of a daily-wage laborer secures top rank in IIT-JEE entrance exam through pure self-study"
    hook = "DAILY-WAGE WORKER'S SON CRACKS *IIT-JEE* WITH TOP AIR RANK WITHOUT COACHING 📚🇮🇳"
    cat = "national"
    details = "Inspirational youth milestone as village student overcomes extreme poverty and study challenges, securing full scholarship at IIT Bombay through pure dedication and self-study."
    img_path = Path("assets/images/categories/news/news_iit_study.jpg")

    reel_id = int(time.time())
    video_file = OUTPUT_DIR / f"aryafeed_update_{reel_id}.mp4"

    audio = get_curated_track(cat)
    audio_name = audio.name if audio else "Default"
    audio_folder = audio.parent.name.upper() if audio else "AUDIO"

    logger.info(f"Rendering News Update: '{clean}'")
    logger.info(f"Image: {img_path.name} | Cat: {cat.upper()} | Track: {audio_name}")

    render_complete_reel(
        media_path=img_path,
        media_type="image",
        text=hook,
        template_key="news_banner",
        audio_path=audio,
        output_path=video_file,
        temp_dir=TEMP_DIR,
        target_duration=7.0,
    )

    logger.info(f"✅ Rendered: {video_file.name} ({round(video_file.stat().st_size/1024/1024, 2)} MB)")

    # Auto-delete used audio
    if audio and audio.exists():
        try:
            audio.unlink()
            logger.info(f"🗑️ Deleted used audio track: {audio_name} from {audio_folder}")
        except Exception as e:
            logger.warning(f"Audio delete warning: {e}")

    caption = generate_varied_caption(clean)

    # Save metadata JSON for automatic Instagram uploading
    meta_file = video_file.with_suffix(".json")
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump({"title": clean, "caption": caption, "category": cat}, f, indent=2)

    # Deliver preview to Telegram
    tele_caption = (
        f"📰 *ARYAFEED FRESH NEWS UPDATE* 🇮🇳\n\n"
        f"📢 *Headline*: {clean}\n\n"
        f"📝 *Details*: {details}\n\n"
        f"🎵 *Soundtrack*: {audio_name} ({audio_folder})\n"
        f"✨ *Visual*: 100% Zero Blur HD | Transparent `>> aryafeed.in`\n\n"
        f"👉 *Type `/auto upload` anytime to post this reel live to Instagram @aryafeed.in!*"
    )

    send_ok = send_telegram_video(video_file, tele_caption)
    if send_ok:
        logger.info("📩 Preview delivered to Telegram successfully!")
    else:
        logger.warning("⚠️ Telegram video delivery retry for update")

    logger.info("Update delivery complete!")


if __name__ == "__main__":
    main()
