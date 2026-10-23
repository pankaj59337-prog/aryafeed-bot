"""Render and Stage 5 Fresh News Reels for Scheduled Publication

Topics:
1. Khavda Mega Renewable Energy Park (World's Largest 30 GW) - AURA
2. Mumbai Undersea Coastal Road Twin Tunnel - AURA
3. India's First Indigenous Hydrogen Train - NATIONAL
4. Indigenous Healthcare AI Humanoid Robot - NEWS
5. IndiaAI Sovereign 10,000+ GPU AI Supercomputing Cluster - AURA

Features:
- 100% Zero Blur HD (1080x1920 Lanczos)
- Transparent floating '>> aryafeed.in' (No black box)
- Audio strictly News Beats, Phonk/Aura, National Pride (auto-delete used tracks)
- Video previews delivered to Telegram (@aryafeed_engine_bot)
- Metadata saved to data/output/*.json ready for scheduled posting
"""

import asyncio
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
logger = logging.getLogger("render_5_scheduled")

import requests
from bot.services.video_engine import render_complete_reel

TELEGRAM_TOKEN = "8804814324:AAGEuKYaivC7Qk8xiVojlhUCMhDDQksTQ8k"
TELEGRAM_CHAT_ID = 5381201341
OUTPUT_DIR = Path("data/output")
TEMP_DIR = Path("data/temp")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

ITEMS_TO_RENDER = [
    {
        "id": "khavda_solar_1",
        "image": "assets/images/categories/news/news_khavda_solar.jpg",
        "hook": "INDIA BUILDS WORLD'S *LARGEST RENEWABLE PARK* IN GUJARAT, VISIBLE FROM SPACE ☀️🇮🇳",
        "clean": "India accelerates construction on world's largest 30 GW solar and wind energy park in Khavda, Gujarat",
        "category": "aura",
        "details": "Spanning 726 square kilometers in Kutch (5 times larger than Paris), the mega hybrid energy park will generate 30,000 MW of green power, powering over 20 million households.",
    },
    {
        "id": "undersea_tunnel_1",
        "image": "assets/images/categories/news/news_undersea_tunnel.jpg",
        "hook": "INDIA'S FIRST *UNDERSEA HIGHWAY TUNNEL* OPENS 20 METERS BELOW SEA LEVEL 🌊🇮🇳",
        "clean": "Mumbai Coastal Road's 2 km undersea twin tunnel begins full operational vehicle transit",
        "category": "aura",
        "details": "Engineering marvel completed 20 meters beneath the Arabian Sea seabed, cutting travel times from 45 minutes to under 10 minutes with state-of-the-art automated ventilation and emergency systems.",
    },
    {
        "id": "hydrogen_train_1",
        "image": "assets/images/categories/news/news_hydrogen_train.jpg",
        "hook": "INDIAN RAILWAYS UNVEILS COUNTRY'S FIRST *HYDROGEN TRAIN* FOR COMMERCIAL TRIALS 🚆🇮🇳",
        "clean": "Indian Railways successfully rolls out India's first zero-emission Hydrogen-powered passenger train",
        "category": "national",
        "details": "Under 'Hydrogen for Heritage', Indian Railways deploys indigenous green hydrogen train on historic heritage routes, completely eliminating carbon emissions and diesel pollution.",
    },
    {
        "id": "healthcare_robot_1",
        "image": "assets/images/categories/news/news_robot_innovation.jpg",
        "hook": "INDIAN LABS UNVEIL ADVANCED INDIGENOUS *HUMANOID ROBOT* FOR HOSPITALS 🤖🇮🇳",
        "clean": "Indian robotics engineers develop indigenous humanoid robot to assist healthcare workers",
        "category": "news",
        "details": "Homegrown robotics team demonstrates autonomous multi-lingual humanoid assistant designed for emergency wards, vitals monitoring, and patient triage assistance.",
    },
    {
        "id": "ai_cluster_1",
        "image": "assets/images/categories/news/news_semiconductor_lab.jpg",
        "hook": "INDIA DEPLOYS SOVEREIGN *10,000+ GPU AI CLUSTER* UNDER HISTORIC INDIAAI MISSION ⚡🇮🇳",
        "clean": "Government establishes sovereign 10,000-GPU AI supercomputing capacity to empower domestic innovators",
        "category": "aura",
        "details": "Under the ₹10,372 Crore IndiaAI Mission, India democratizes compute infrastructure with sovereign high-speed GPU clusters to power indigenous AI models across Indian languages and science.",
    },
]


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
        list(Path("assets/music/news").glob("*.mp3"))
        + list(Path("assets/music/aura").glob("*.mp3"))
        + list(Path("assets/music/national").glob("*.mp3"))
    )
    return random.choice(combined) if combined else None


def generate_varied_caption(clean_title: str) -> str:
    lead_emojis = ["⚡", "🇮🇳✨", "🔥", "📢", "🚨", "📈"]
    hooks = [
        f"{random.choice(lead_emojis)} Breaking Update: {clean_title}",
        f"{random.choice(lead_emojis)} Major Headline: {clean_title}",
        f"{random.choice(lead_emojis)} National Update: {clean_title}",
        f"Big development today! {random.choice(lead_emojis)}\n{clean_title}",
    ]
    ctas = [
        "What are your thoughts on this? Tell us in the comments 👇",
        "Drop your honest opinion below 👇✨",
        "Share this update with someone who needs to know! 📢",
        "Daily breaking news & positive updates ke liye follow karein @aryafeed.in 🇮🇳",
    ]
    hashtags = [
        ["#aryafeed", "#breakingnews", "#indiannews", "#currentaffairs", "#explorepage", "#viralreels"],
        ["#aryafeed", "#newsupdate", "#trendingnews", "#india", "#reelsindia", "#dailynews"],
        ["#aryafeed", "#headlines", "#todaynews", "#explorepage", "#viralreel", "#trendingnow"],
        ["#aryafeed", "#bharatnews", "#indianpride", "#virals", "#explore", "#trendingreels"],
    ]
    h = random.choice(hooks)
    c = random.choice(ctas)
    t = " ".join(random.choice(hashtags))
    return f"{h}\n\n{c}\n\n{t}"


def main():
    total = len(ITEMS_TO_RENDER)
    logger.info(f"Starting render of {total} scheduled news reels...")

    send_telegram_text(
        f"🚀 *Rendering 5 Fresh News Reels for Scheduled Release!* 🇮🇳\n\n"
        f"• Visuals: 100% Zero Blur HD (1080x1920 Lanczos)\n"
        f"• Title Watermark: Floating transparent `>> aryafeed.in`\n"
        f"• Soundtracks: Curated News Beats, Phonk/Aura & National Pride\n\n"
        f"Rendering reels and dispatching previews to Telegram now..."
    )

    rendered_files = []

    for idx, item in enumerate(ITEMS_TO_RENDER, 1):
        clean = item["clean"]
        hook = item["hook"]
        cat = item["category"]
        details = item["details"]
        img_path = Path(item["image"])

        reel_id = int(time.time()) + idx * 10
        video_file = OUTPUT_DIR / f"aryafeed_scheduled_{reel_id}.mp4"

        audio = get_curated_track(cat)
        audio_name = audio.name if audio else "Default"
        audio_folder = audio.parent.name.upper() if audio else "AUDIO"

        logger.info(f"--- [Render {idx}/{total}] '{clean}' ---")
        logger.info(f"    Image: {img_path.name} | Category: {cat.upper()} | Track: {audio_name}")

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

        # Save metadata JSON for scheduled Instagram posting
        meta_file = video_file.with_suffix(".json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "title": clean,
                "caption": caption,
                "category": cat,
                "staged_at": time.time(),
                "queue_index": idx
            }, f, indent=2)

        # Deliver preview to Telegram
        tele_caption = (
            f"📰 *ARYAFEED SCHEDULED REEL ({idx}/{total})* 🇮🇳\n\n"
            f"📢 *Headline*: {clean}\n\n"
            f"📝 *Details*: {details}\n\n"
            f"🎵 *Soundtrack*: {audio_name} ({audio_folder})\n"
            f"✨ *Visual*: 100% Zero Blur HD | Transparent `>> aryafeed.in`\n\n"
            f"🕒 *Status*: Staged in Scheduled Queue for @aryafeed.in"
        )

        send_ok = send_telegram_video(video_file, tele_caption)
        if send_ok:
            logger.info(f"📩 Preview {idx}/{total} delivered to Telegram successfully!")
        else:
            logger.warning(f"⚠️ Telegram video delivery warning for {clean}")

        rendered_files.append((video_file, clean))

    send_telegram_text(
        f"🎉 *Batch Complete! All 5 News Reels Are Rendered & Scheduled in Queue!*\n\n"
        f"1. ☀️ Khavda Solar/Wind Mega-Park (30 GW World's Largest)\n"
        f"2. 🌊 Mumbai Undersea Twin Tunnel Highway\n"
        f"3. 🚆 India's First Hydrogen Train\n"
        f"4. 🤖 Indigenous Healthcare Humanoid Robot\n"
        f"5. ⚡ IndiaAI 10,000+ GPU Sovereign AI Cluster\n\n"
        f"📅 *All 5 reels are staged and ready for automated scheduled publication!*"
    )
    logger.info("Batch render and staging complete!")


if __name__ == "__main__":
    main()
