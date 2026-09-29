"""Autonomous Real-Time News Monitor & Breaking Reel Engine for @aryafeed.in.

Fetches latest trending Indian stories, formats high-curiosity headlines with
[ ARYAFEED ] branding badge, acquires the REAL news subject editorial photos
(athletes, celebrities, cricketers, politicians, events), renders 1080x1920 MP4 reel,
and auto-posts to Instagram.
"""

import asyncio
import hashlib
import io
import logging
import random
import re
import shutil
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiosqlite
from PIL import Image, ImageDraw

from bot.services.instagram_service import instagram_service
from bot.services.render_service import execute_render_job
from bot.services.text_overlay import create_text_overlay, generate_preview_composite
from bot.templates.styles import get_template
from bot.utils.config import config
from database.db import db_manager

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_CHAT_ID = 5381201341

# RSS feeds from top Indian publishers with direct high-resolution editorial photos
NEWS_FEEDS = [
    {
        "url": "https://www.rvcj.com/feed/",
        "category": "rvcj",
        "publisher": "RVCJ Media",
    },
    {
        "url": "https://www.hindustantimes.com/feeds/rss/trending/rssfeed.xml",
        "category": "trending",
        "publisher": "Hindustan Times",
    },
    {
        "url": "https://indianexpress.com/feed/",
        "category": "breaking",
        "publisher": "Indian Express",
    },
    {
        "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "category": "top",
        "publisher": "Times of India",
    },
    {
        "url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
        "category": "india",
        "publisher": "Hindustan Times",
    },
    {
        "url": "https://www.indiatoday.in/rss/home",
        "category": "national",
        "publisher": "India Today",
    },
    {
        "url": "https://indianexpress.com/section/sports/feed/",
        "category": "sports",
        "publisher": "Indian Express",
    },
    {
        "url": "https://indianexpress.com/section/entertainment/feed/",
        "category": "entertainment",
        "publisher": "Indian Express",
    },
    {
        "url": "https://news.google.com/rss/headlines/section/topic/NATION?hl=en-IN&gl=IN&ceid=IN:en",
        "category": "india",
        "publisher": "Google News",
    },
]

# Keywords that signal high virality / curiosity
VIRAL_KEYWORDS = [
    "upsc", "exam", "cracks", "ias", "ips", "gold", "crore", "lakh",
    "delivery", "swiggy", "zomato", "historic", "wins", "record",
    "isro", "moon", "nasa", "ai", "police", "arrested", "cctv",
    "saved", "hero", "dog", "scooter", "bizarre", "viral", "world record",
    "first time", "shocking", "millionaire", "success", "achievement",
    "court", "delhi", "panel", "cji", "modi", "kohli", "rohit", "dhoni",
    "flight", "rapido", "fratricide", "encounter", "cisf", "jawan",
]

# Unwanted routine / dry political debate terms to filter out
IGNORE_TERMS = [
    "cwc", "manifesto", "rally", "press meet", "spokesperson",
    "election commission plea", "bench to hear", "adjourned", "submits plea",
]


async def init_news_db() -> None:
    """Initialize news tracking table in SQLite."""
    async with aiosqlite.connect(config.database_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS published_news (
                news_hash TEXT PRIMARY KEY,
                title TEXT,
                source TEXT,
                url TEXT,
                headline_used TEXT,
                posted_to_ig INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()


def clean_source_name(raw_source: str) -> str:
    """Normalize news source name for clean [ PER SOURCE ] badge."""
    src = raw_source.lower().strip()
    src = re.sub(r'https?://|www\.|\.com|\.in|\.co|\.org', '', src)
    if "hindustan" in src or "ht" in src:
        return "HINDUSTAN TIMES"
    if "hindu" in src:
        return "THE HINDU"
    if "ndtv" in src:
        return "NDTV"
    if "times" in src or "toi" in src:
        return "TIMES OF INDIA"
    if "today" in src:
        return "INDIA TODAY"
    if "express" in src:
        return "INDIAN EXPRESS"
    if "aajtak" in src:
        return "AAJ TAK"
    if "ani" in src:
        return "ANI"
    if "reuters" in src:
        return "REUTERS"
    if "al jazeera" in src:
        return "AL JAZEERA"
    return src.upper()[:16] if src else "OFFICIAL"


def format_viral_news_headline(raw_title: str, source: str) -> str:
    """Transform a raw news title into a high-curiosity 2-3 line uppercase hook."""
    # Strip outlet suffixes like ' - The Indian Express' or ' | Hindustan Times'
    clean = re.sub(
        r'\s+[-|]\s+(?:The\s+)?(?:Hindustan Times|Indian Express|Times of India|NDTV|India Today|News18|Zee News|ANI|Reuters|BBC|HT)[^$]*$',
        '',
        raw_title,
        flags=re.IGNORECASE,
    ).strip()
    clean = re.sub(r'[\'"]', '', clean)

    # Highlight monetary figures, achievements, numbers
    clean = re.sub(r'(\₹\s*[\d,]+(?:\s*(?:lakh|crore|cr|k|m|b))?)', r'*\1*', clean, flags=re.IGNORECASE)
    clean = re.sub(r'(\$[\d,]+(?:\s*(?:million|billion|b|m))?)', r'*\1*', clean, flags=re.IGNORECASE)
    clean = re.sub(r'(\b\d+\s*(?:gold|medal|runs|wickets|years?)\b)', r'*\1*', clean, flags=re.IGNORECASE)
    clean = re.sub(r'(\bupsc(?:\s*exam)?\b)', r'*UPSC EXAM*', clean, flags=re.IGNORECASE)
    clean = re.sub(r'(\bisro(?:\s*mission)?\b)', r'*ISRO*', clean, flags=re.IGNORECASE)

    # Choose emoji based on topic
    emoji = "⚡🇮🇳"
    lower_t = clean.lower()
    if any(k in lower_t for k in ["upsc", "exam", "student", "teacher", "cracks"]):
        emoji = "🥹🎓"
    elif any(k in lower_t for k in ["gold", "medal", "wins", "champion", "trophy"]):
        emoji = "🏆🇮🇳"
    elif any(k in lower_t for k in ["swiggy", "zomato", "cash", "crore", "lakh", "money"]):
        emoji = "👏🪙"
    elif any(k in lower_t for k in ["isro", "space", "moon", "nasa", "rocket"]):
        emoji = "🚀🌕"
    elif any(k in lower_t for k in ["cctv", "saved", "dog", "hero", "accident"]):
        emoji = "❤️‍🩹🐾"
    elif any(k in lower_t for k in ["turbulence", "flight", "plane", "airport"]):
        emoji = "✈️⚠️"

    # Truncate to punchy viral hook if too long (max 14 words)
    words = clean.split()
    if len(words) > 14:
        clean = " ".join(words[:14])
        words = clean.split()

    if len(words) > 7:
        mid = len(words) // 2
        line1 = " ".join(words[:mid]).upper()
        line2 = " ".join(words[mid:]).upper()
        hook = f"{line1}\n{line2} {emoji}"
    else:
        hook = f"{clean.upper()} {emoji}"

    # Append source badge tag at bottom
    src_tag = clean_source_name(source)
    return f"{hook} [Per {src_tag}]"


def generate_news_ig_caption(headline: str, source: str) -> str:
    """Generate high-engagement viral caption with AryaFeed hashtags."""
    clean_h = re.sub(r'\[Per [^\]]+\]', '', headline).replace('*', '').strip()
    src = clean_source_name(source)
    return (
        f"{clean_h}\n.\n"
        f"Source: {src}\n.\n"
        f"What is your thought on this? Drop an 🇮🇳 in the comments below! 👇\n.\n"
        f"#aryafeed #breakingnews #indianews #currentaffairs #explorepage #reelsindia #instanews #trending"
    )


def download_editorial_image(url: str, output_path: Path) -> bool:
    """Download news editorial photo with browser headers and convert to RGB JPEG."""
    try:
        parsed = urllib.parse.urlsplit(url)
        safe_path = urllib.parse.quote(parsed.path)
        safe_url = urllib.parse.urlunsplit(parsed._replace(path=safe_path))
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://www.google.com/",
        }
        req = urllib.request.Request(safe_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read()

        with Image.open(io.BytesIO(data)) as im:
            if im.width < 250 or im.height < 180:
                logger.warning(f"[LiveNews] Image too small ({im.size}) from {url}")
                return False
            output_path.parent.mkdir(parents=True, exist_ok=True)
            im.convert("RGB").save(output_path, "JPEG", quality=95)
            logger.info(f"[LiveNews] Successfully saved news photo: {im.size} to {output_path}")
            return True
    except Exception as e:
        logger.warning(f"[LiveNews] Failed downloading article image from {url}: {e}")
        return False


def search_subject_image(query: str, output_path: Path) -> bool:
    """Fallback: Search Bing image index for the exact news subject and save high-res photo."""
    try:
        clean_q = urllib.parse.quote_plus(f"{query} news india")
        url = f"https://www.bing.com/images/async?q={clean_q}&first=1&count=8"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        murls = re.findall(r'murl&quot;:&quot;(https?://[^&]+)&quot;', html)
        for cand_url in murls[:6]:
            if download_editorial_image(cand_url, output_path):
                logger.info(f"[LiveNews] Found and downloaded subject photo via web search: {cand_url}")
                return True
        return False
    except Exception as e:
        logger.warning(f"[LiveNews] Subject search failed for '{query}': {e}")
        return False


def create_editorial_fallback_backdrop(output_path: Path) -> None:
    """Create a sleek, dark editorial news backdrop if all internet image sources fail."""
    cw, ch = 1080, 1920
    im = Image.new("RGB", (cw, ch), (10, 14, 24))
    draw = ImageDraw.Draw(im)
    for y in range(ch):
        r = int(10 + (28 - 10) * (y / ch))
        g = int(14 + (36 - 14) * (y / ch))
        b = int(24 + (52 - 24) * (y / ch))
        draw.line([(0, y), (cw, y)], fill=(r, g, b))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(output_path, "JPEG", quality=95)


class LiveNewsService:
    """Service to fetch, format, render and post breaking news reels."""

    async def fetch_fresh_articles(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch latest news articles from RSS feeds and filter out already processed ones."""
        await init_news_db()
        articles: List[Dict[str, Any]] = []

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        for feed in NEWS_FEEDS:
            try:
                def _do_fetch(feed_url):
                    req = urllib.request.Request(feed_url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        return resp.read()

                xml_data = await asyncio.to_thread(_do_fetch, feed["url"])
                root = ET.fromstring(xml_data)

                for item in root.findall(".//item"):
                    t_elem = item.find("title")
                    l_elem = item.find("link")
                    s_elem = item.find("source")
                    pub_elem = item.find("pubDate")

                    if t_elem is None or not t_elem.text:
                        continue

                    title = t_elem.text.strip()
                    link = l_elem.text.strip() if l_elem is not None and l_elem.text else ""
                    source = s_elem.text.strip() if (s_elem is not None and s_elem.text) else feed.get("publisher", "News")
                    pub_date = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""

                    # Filter out dry political jargon
                    t_lower = title.lower()
                    if any(term in t_lower for term in IGNORE_TERMS):
                        continue

                    # Extract real news subject photo from XML
                    image_url = None
                    for child in item:
                        tag = child.tag.lower()
                        if any(k in tag for k in ['content', 'thumbnail', 'enclosure']):
                            u = child.get('url')
                            if u and ('http' in u):
                                image_url = u
                                break
                    if not image_url:
                        desc = item.find('description')
                        if desc is not None and desc.text:
                            m = re.search(r'src=["\'](https?://[^"\'>\s]+)["\']', desc.text)
                            if m:
                                image_url = m.group(1)
                    if not image_url:
                        for child in item:
                            if 'encoded' in child.tag and child.text:
                                m = re.search(r'src=["\'](https?://[^"\'>\s]+\.(?:jpg|jpeg|png|webp)[^"\'>\s]*)["\']', child.text, re.IGNORECASE)
                                if m:
                                    image_url = m.group(1)
                                    break

                    news_hash = hashlib.md5(title.encode("utf-8")).hexdigest()

                    # Score virality
                    is_viral = any(k in t_lower for k in VIRAL_KEYWORDS)

                    articles.append({
                        "hash": news_hash,
                        "title": title,
                        "link": link,
                        "source": source,
                        "pub_date": pub_date,
                        "image_url": image_url,
                        "is_viral": is_viral,
                    })
            except Exception as e:
                logger.warning(f"[LiveNews] Failed to fetch feed {feed['url']}: {e}")

        # Filter out already published in database
        async with aiosqlite.connect(config.database_path) as db:
            async with db.execute("SELECT news_hash FROM published_news") as cursor:
                rows = await cursor.fetchall()
                published_hashes = {r[0] for r in rows}

        fresh = [a for a in articles if a["hash"] not in published_hashes]

        # Prioritize viral items first, then items with direct editorial photos
        fresh.sort(key=lambda x: (x["is_viral"], bool(x["image_url"])), reverse=True)
        return fresh[:limit]

    async def create_and_publish_news_reel(
        self,
        chat_id: int = DEFAULT_ADMIN_CHAT_ID,
        auto_post: bool = True,
        bot=None,
    ) -> Dict[str, Any]:
        """Fetch top breaking news, acquire real photo, render 1080x1920 reel with [ ARYAFEED ], and post to Instagram."""
        fresh = await self.fetch_fresh_articles(limit=5)
        if not fresh:
            logger.info("[LiveNews] No fresh breaking news available right now.")
            return {"success": False, "error": "No fresh news found."}

        target_article = fresh[0]
        raw_title = target_article["title"]
        source = target_article["source"]
        news_hash = target_article["hash"]

        headline = format_viral_news_headline(raw_title, source)
        caption = generate_news_ig_caption(headline, source)

        logger.info(f"[LiveNews] Processing breaking news: {headline} (Source: {source})")

        # Acquire the REAL news subject photo (NEVER candid girl photos)
        timestamp = int(time.time())
        deployed_img = config.input_dir / f"{chat_id}_news_{timestamp}.jpg"
        img_acquired = False

        if target_article.get("image_url"):
            logger.info(f"[LiveNews] Downloading editorial photo from feed: {target_article['image_url']}")
            img_acquired = await asyncio.to_thread(
                download_editorial_image, target_article["image_url"], deployed_img
            )

        if not img_acquired:
            # Fallback to targeted search for the exact story subject
            search_query = re.sub(r'[^a-zA-Z0-9\s]', ' ', raw_title).strip()
            words = [w for w in search_query.split() if len(w) > 2][:6]
            clean_q = " ".join(words)
            logger.info(f"[LiveNews] Feed image missing/failed, searching news subject image for: {clean_q}")
            img_acquired = await asyncio.to_thread(
                search_subject_image, clean_q, deployed_img
            )

        if not img_acquired:
            # Fallback to sleek editorial news backdrop
            logger.info("[LiveNews] Search failed, generating dark editorial backdrop")
            await asyncio.to_thread(create_editorial_fallback_backdrop, deployed_img)

        # Record in reel session
        await db_manager.start_reel_session(chat_id)
        await db_manager.update_session(
            chat_id,
            media_path=str(deployed_img),
            media_type="image",
            overlay_text=headline,
            selected_template="news_banner",
            music_path=None,
        )

        # Render 1080x1920 high-bitrate video
        video_path = await execute_render_job(chat_id)
        if not video_path or not Path(video_path).exists():
            return {"success": False, "error": "Reel rendering failed."}

        # Mark in published news database
        async with aiosqlite.connect(config.database_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO published_news (
                    news_hash, title, source, url, headline_used, posted_to_ig
                ) VALUES (?, ?, ?, ?, ?, ?);
            """, (news_hash, raw_title, source, target_article["link"], headline, 1 if auto_post else 0))
            await db.commit()

        result = {
            "success": True,
            "headline": headline,
            "source": source,
            "video_path": str(video_path),
            "caption": caption,
            "instagram_url": None,
        }

        # Upload to Instagram if auto_post is enabled
        if auto_post:
            ig_res = await instagram_service.upload_reel(
                chat_id=chat_id,
                video_path=Path(video_path),
                caption=caption,
            )
            if ig_res.get("success"):
                result["instagram_url"] = ig_res.get("url")
                logger.info(f"[LiveNews] Reel successfully posted to Instagram: {result['instagram_url']}")
            else:
                logger.warning(f"[LiveNews] Instagram upload error: {ig_res.get('error')}")
                result["ig_error"] = ig_res.get("error")

        # Send Telegram notification if bot context provided
        if bot:
            try:
                if result.get("instagram_url"):
                    alert_text = (
                        f"✅ *AryaFeed News — POSTED LIVE!*\n\n"
                        f"📰 {headline}\n"
                        f"📌 {source}\n\n"
                        f"🚀 [Watch Reel]({result['instagram_url']})"
                    )
                elif result.get("ig_error"):
                    error_msg = result["ig_error"]
                    is_session_error = any(kw in error_msg.lower() for kw in ("session", "login", "expired", "401", "403"))
                    alert_text = (
                        f"⚡ *AryaFeed News Reel Ready*\n\n"
                        f"📰 {headline}\n"
                        f"📌 {source}\n\n"
                    )
                    if is_session_error:
                        alert_text += "🔴 *Instagram session expired!* Use /insta\\_login to reconnect.\n"
                    else:
                        alert_text += f"⚠️ Upload failed: {error_msg}\n"
                else:
                    alert_text = (
                        f"⚡ *AryaFeed News Reel Ready!*\n\n"
                        f"📰 {headline}\n"
                        f"📌 {source}\n"
                    )

                with open(video_path, "rb") as vf:
                    await bot.send_video(
                        chat_id=chat_id,
                        video=vf,
                        caption=alert_text,
                        parse_mode="Markdown",
                    )
            except Exception as e:
                logger.warning(f"[LiveNews] Failed to send Telegram alert: {e}")

        return result


# Singleton instance
live_news_service = LiveNewsService()
