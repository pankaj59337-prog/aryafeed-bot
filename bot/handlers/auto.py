"""Interactive Category-First Reel Studio with Image+Text Preview First and Song Name Input."""

import asyncio
import logging
import os
import random
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.handlers.commands import restricted
from bot.services.ai_image_engine import (
    generate_ai_visual,
    generate_ai_candid_image,
    fetch_pinterest_candid_image,
)
from bot.services.caption_generator import generate_instagram_caption
from bot.services.instagram_service import instagram_service
from bot.services.music_service import music_service
from bot.services.render_service import execute_render_job
from bot.services.text_overlay import generate_preview_composite
from bot.templates.styles import TEMPLATES
from bot.utils.cleanup import cleanup_chat_files
from bot.utils.config import config
from database.db import db_manager

logger = logging.getLogger(__name__)

# AryaFeed Engine Core Categories
CATEGORIES: Dict[str, Dict[str, Any]] = {
    "news": {
        "id": "news",
        "title": "AryaFeed News ⚡",
        "icon": "⚡",
        "desc": "High-curiosity viral news, milestones & debate cards",
        "style": "news_banner",
    },
    "news_banner": {
        "id": "news_banner",
        "title": "AryaFeed Banner ⚡",
        "icon": "⚡",
        "desc": "Bold yellow headline with brand pill",
        "style": "news_banner",
    },
    "news_card": {
        "id": "news_card",
        "title": "AryaFeed Card 📰",
        "icon": "📰",
        "desc": "Dark scrim card with source tag & brand pill",
        "style": "news_card",
    },
}

# 30 Curated Authentic Candid Reference Aesthetics (100% real photo aesthetic, zero CGI)
ALL_IMAGE_OPTIONS: List[Dict[str, Any]] = [
    {
        "id": "news_breaking_1",
        "title": "Breaking News Desk",
        "filename": "10.jpg",
        "icon": "⚡",
        "desc": "High impact viral Indian news backdrop",
        "categories": ["news", "news_banner", "news_card"],
    },
    {
        "id": "news_milestone_2",
        "title": "Milestone and Achievement",
        "filename": "107.jpg",
        "icon": "🏆",
        "desc": "Inspirational triumph and exam cracked visual",
        "categories": ["news", "news_banner", "news_card"],
    },
    {
        "id": "news_tech_3",
        "title": "Tech and Infrastructure",
        "filename": "12.jpg",
        "icon": "🚀",
        "desc": "Modern India growth and technology backdrop",
        "categories": ["news", "news_banner", "news_card"],
    },
    {
        "id": "news_finance_4",
        "title": "Finance and Economy",
        "filename": "123.jpg",
        "icon": "📈",
        "desc": "Market trends and startup unicorn backdrop",
        "categories": ["news", "news_banner", "news_card"],
    },
    {
        "id": "news_debate_5",
        "title": "Public Debate and Opinion",
        "filename": "126.jpg",
        "icon": "🎙️",
        "desc": "Viral social trend and hot debate visual",
        "categories": ["news", "news_banner", "news_card"],
    },
    {
        "id": "news_defense_6",
        "title": "Defense and National Pride",
        "filename": "129.jpg",
        "icon": "🇮🇳",
        "desc": "Indian forces, defense tech and national pride",
        "categories": ["news", "news_banner", "news_card"],
    },
    {
        "id": "news_civic_7",
        "title": "Civic and Society",
        "filename": "133.jpg",
        "icon": "🏛️",
        "desc": "Governance, urban laws and civic developments",
        "categories": ["news", "news_banner", "news_card"],
    },
    {
        "id": "news_science_8",
        "title": "Space and Science",
        "filename": "158.jpg",
        "icon": "🌕",
        "desc": "ISRO space missions and scientific breakthroughs",
        "categories": ["news", "news_banner", "news_card"],
    },
    {
        "id": "news_lifestyle_9",
        "title": "Gen-Z and Career",
        "filename": "176.jpg",
        "icon": "💼",
        "desc": "Jobs, education trends and youth culture",
        "categories": ["news", "news_banner", "news_card"],
    },
    {
        "id": "news_sports_10",
        "title": "Sports and Cricket",
        "filename": "182.jpg",
        "icon": "🏏",
        "desc": "Cricket records, world championships and sports news",
        "categories": ["news", "news_banner", "news_card"],
    },
]
ALL_HOOK_OPTIONS: List[Dict[str, Any]] = [
    {"id": "h_news_1", "text": "22 FRIENDS STUDIED TOGETHER, *21 CRACKED* THE EXAM 🥹🎓", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_2", "text": "TEA VENDOR'S DAUGHTER CRACKS *UPSC EXAM* IN FIRST ATTEMPT 🇮🇳✨", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_3", "text": "SWIGGY DELIVERY GUY RETURNS *₹15 LAKH CASH* LEFT IN CAB 👏🛵", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_4", "text": "MAN BUYS OLD SCOOTER FOR ₹20,000, FINDS *₹50 LAKH GOLD* HIDDEN 🤯🪙", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_5", "text": "INDIA WINS *HISTORIC GOLD* AFTER 48 YEARS, STADIUM TEARS UP 🇮🇳🏆", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_6", "text": "VIRAL CCTV: BOY RISKS LIFE TO SAVE STREET DOG FROM *SPEEDING TRUCK* 🐶💔", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_7", "text": "FATHER WORKED AS LABOURER FOR 25 YEARS TO MAKE SON *IPS OFFICER* 🫡🇮🇳", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_8", "text": "ISRO ANNOUNCES MASSIVE DISCOVERY: WATER ICE CONFIRMED ON *MOON POLE* 🌕🚀", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_9", "text": "GOLD PRICES SMASH ALL-TIME *HISTORIC HIGH* IN INDIA TODAY 🪙📈", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_10", "text": "NEW TRAFFIC RULES: *₹25,000 FINE* FOR THIS MISTAKE FROM TOMORROW 🚨🚗", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_11", "text": "WHATSAPP ROLLS OUT *BIGGEST PRIVACY UPDATE* OF 2026 WORLDWIDE 📱🔒", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_12", "text": "19-YEAR-OLD FROM BIHAR BUILDS *ELECTRIC CAR* FOR UNDER ₹60,000 ⚡🚗", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_13", "text": "TATA GROUP COMMENCES INDIA'S BIGGEST *SEMICONDUCTOR CHIP FAB* 🏭🇮🇳", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_14", "text": "KASHMIR RAIL LINK: WORLD'S HIGHEST *CHENAB BRIDGE* OPENS REGULAR RUNS 🌉❄️", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_15", "text": "HIGHWAY TOLL TAX TO BE *WAIVED OFF* FOR VEHICLES USING GNSS-FASTAG 🛣️🚘", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_16", "text": "IIT GRADUATE REJECTS *₹1.5 CR US JOB* TO TEACH RURAL VILLAGE CHILDREN 📚❤️", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_17", "text": "RBI MANDATES INSTANT *UPI REFUND RULE* FOR FAILED TRANSACTIONS 💸📲", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_18", "text": "SOLAR BOOM: OVER *1 CRORE HOMES* POWERED BY PM SURYA GHAR SCHEME ☀️⚡", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_19", "text": "DELHI TO MUMBAI IN 12 HOURS: EXPRESSWAY'S *FINAL LINK* OPERATIONAL 🛣️🏎️", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_20", "text": "INDIAN AIR FORCE INDUCTS FIRST SQUADRON OF *TEJAS MK-1A FIGHTERS* ✈️🇮🇳", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_21", "text": "STUDENT CRACKS CAT WITH *100 PERCENTILE* WHILE DOING 10-HR NIGHT SHIFTS 🎯📊", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_22", "text": "APPLE EXPANDS: 1 OUT OF EVERY *4 IPHONES* NOW MANUFACTURED IN INDIA 📱🇮🇳", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_23", "text": "IIT MADRAS HYPERLOOP TEST TRACK HITS *400 KM/H SPEED* IN TRIALS 🚅⚡", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_24", "text": "INDIAN PASSPORT STRENGTH SOARS: *VISA-FREE TRAVEL* EXTENDED TO 62 NATIONS 🌍✈️", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_25", "text": "4-DAY WORK WEEK DRAFT: LABOUR MINISTRY CONSIDERS *NEW WORKPLACE RULES* 💼⏰", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_26", "text": "5G SATELLITE DIRECT-TO-MOBILE LAUNCHING: *ZERO CALL DROPS* EVERYWHERE 📡📱", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_27", "text": "TWO 21-YEAR-OLDS FROM JAIPUR BUILD *₹500 CRORE AI STARTUP* IN 18 MONTHS 🦄✨", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_28", "text": "MANDATORY 6-AIRBAG RULE OFFICIALLY EXTENDED TO ALL *BUDGET HATCHBACKS* 🚙🛡️", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_29", "text": "GEOLOGISTS CONFIRM GIANT *FRESHWATER RESERVOIR* FOUND DEEP UNDER THAR 💧🏜️", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_30", "text": "OVER 15 CRORE PILGRIMS VISITED *AYODHYA AND KASHI* THIS YEAR: TOURISM RECORD 🛕🚩", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_31", "text": "VANDE BHARAT SLEEPER TRAINS LAUNCHED ACROSS *15 INTERCITY ROUTES* 🚆🛌", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_32", "text": "WORLD BANK DECLARES INDIA AS THE *FASTEST GROWING ECONOMY* OF 2026 📊🚀", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_33", "text": "INDIAN STARTUP DESIGNS AFFORDABLE *PROSTHETIC LIMB* CONTROLLED BY BRAIN 🦾❤️", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_34", "text": "SURGICAL STRIKE ON CYBER FRAUD: NEW LAW CARRIES *STRICT 10-YR JAIL TERM* ⚖️📵", "categories": ["news", "news_banner", "news_card"]},
    {"id": "h_news_35", "text": "FARMER'S DAUGHTER WINS *RHODES SCHOLARSHIP* TO STUDY AT OXFORD UNIVERSITY 🌟🎓", "categories": ["news", "news_banner", "news_card"]},
]
def get_image_option(img_id: str) -> Dict[str, Any]:
    """Retrieve image option dictionary by ID, custom upload, or dynamic slot."""
    if img_id == "custom_upload":
        return {
            "id": "custom_upload",
            "title": "Custom Uploaded Photo",
            "filename": "custom_upload.jpg",
            "icon": "📸",
            "desc": "User-provided custom image from ChatGPT/Gemini/Gallery",
            "categories": ["news", "news_banner", "news_card"],
        }
    if img_id.startswith("dyn_") or img_id.startswith("ai_gen_"):
        return {
            "id": img_id,
            "title": "✨ Dynamic AI Candid Photo",
            "filename": f"{img_id}.jpg",
            "icon": "✨",
            "desc": "Dynamic AI visual generated uniquely for you",
            "categories": ["news", "news_banner", "news_card"],
        }
    if img_id.startswith("pin_"):
        for opt in ALL_IMAGE_OPTIONS:
            if opt["id"] == img_id:
                return opt
        return {
            "id": img_id,
            "title": "📌 Pinterest Candid Photo",
            "filename": f"{img_id}.jpg",
            "icon": "📌",
            "desc": "Fresh candid visual from Pinterest CDN",
            "categories": ["news", "news_banner", "news_card"],
        }
    for opt in ALL_IMAGE_OPTIONS:
        if opt["id"] == img_id:
            return opt
    return ALL_IMAGE_OPTIONS[0]


def get_category_info(cat_id: Optional[str]) -> Dict[str, Any]:
    """Retrieve category dictionary or default to 'news_banner'."""
    if cat_id and cat_id.lower() in CATEGORIES:
        return CATEGORIES[cat_id.lower()]
    return CATEGORIES["news_banner"]


async def get_fresh_image_options(
    chat_id: int,
    category: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Return 5 unused candid images for this user filtered by category, guaranteed zero repeats."""
    used = await db_manager.get_used_assets(chat_id, "image")
    cat = category.lower().strip() if category else None
    if cat:
        pool = [opt for opt in ALL_IMAGE_OPTIONS if cat in opt.get("categories", [])]
        if not pool:
            pool = ALL_IMAGE_OPTIONS
    else:
        pool = ALL_IMAGE_OPTIONS

    # 1. Unused candidates from requested category
    candidates = [opt for opt in pool if opt["id"] not in used]

    # 2. If fewer than limit, borrow unused images from other categories
    if len(candidates) < limit:
        other_unseen = [opt for opt in ALL_IMAGE_OPTIONS if opt["id"] not in used and opt not in candidates]
        random.shuffle(other_unseen)
        needed = limit - len(candidates)
        for opt in other_unseen[:needed]:
            adapted = dict(opt)
            if cat and cat not in adapted.get("categories", []):
                adapted["categories"] = list(adapted.get("categories", [])) + [cat]
            candidates.append(adapted)

    # 3. ZERO-REPEAT GUARANTEE:
    # If the user has used every single catalog image, generate brand new dynamic slots on the fly!
    # NEVER EVER recycle used images back into candidates!
    while len(candidates) < limit:
        dyn_idx = len(candidates) + 1
        unique_dyn_id = f"dyn_ai_{cat or 'vibe'}_{int(time.time())}_{random.randint(1000, 9999)}"
        candidates.append({
            "id": unique_dyn_id,
            "title": f"Fresh AI Candid #{dyn_idx}",
            "filename": f"{unique_dyn_id}.jpg",
            "icon": "✨",
            "desc": "100% brand new dynamic AI visual generation",
            "categories": [cat] if cat else ["news", "news_banner", "news_card"],
        })

    random.shuffle(candidates)
    return candidates[:limit]


async def get_fresh_song_options(
    chat_id: int,
    category: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Return 5 unused vocal songs for this user filtered by category."""
    used = await db_manager.get_used_assets(chat_id, "music")
    return music_service.get_vocal_options(category=category, exclude_ids=used, limit=limit)


async def get_fresh_hook_options(
    chat_id: int,
    category: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Return 5 unused text hooks for this user filtered by category."""
    used = await db_manager.get_used_assets(chat_id, "text")
    cat = category.lower().strip() if category else None
    if cat:
        cat_pool = [h for h in ALL_HOOK_OPTIONS if cat in h.get("categories", [])]
        pool = cat_pool if cat_pool else ALL_HOOK_OPTIONS
    else:
        pool = ALL_HOOK_OPTIONS

    candidates = [h for h in pool if h["text"] not in used]
    if len(candidates) < limit:
        other_unseen = [h for h in ALL_HOOK_OPTIONS if h["text"] not in used and h not in candidates]
        random.shuffle(other_unseen)
        needed = limit - len(candidates)
        for h in other_unseen[:needed]:
            adapted = dict(h)
            if cat and cat not in adapted.get("categories", []):
                adapted["categories"] = list(adapted.get("categories", [])) + [cat]
            candidates.append(adapted)

    if not candidates:
        candidates = list(pool)

    random.shuffle(candidates)
    return candidates[:limit]


def build_category_selection_keyboard() -> InlineKeyboardMarkup:
    """AryaFeed Studio Layout Styles."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ AryaFeed Banner Style", callback_data="cat_news_banner"),
            InlineKeyboardButton("📰 AryaFeed Card Style", callback_data="cat_news_card"),
        ],
    ])


def build_image_selection_keyboard(options: List[Dict[str, Any]], category: Optional[str] = None) -> InlineKeyboardMarkup:
    """Step 1/3: 5 Image options + AI Generate + Pinterest + Own Photo + Shuffle + Random + Reset + Back."""
    keyboard = []
    row = []
    for idx, opt in enumerate(options, start=1):
        btn = InlineKeyboardButton(f"{opt['icon']} {idx}. {opt['title']}", callback_data=f"pick_img_{opt['id']}")
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Dynamic AI & Pinterest generation buttons
    keyboard.append([
        InlineKeyboardButton("✨ Generate AI Candid Visual", callback_data="gen_ai_photo"),
        InlineKeyboardButton("📌 Fresh Pinterest Photo", callback_data="fetch_pin_photo"),
    ])

    keyboard.append([
        InlineKeyboardButton("📸 Use My Own Uploaded Photo", callback_data="upload_own_img"),
    ])

    # Utility row: Shuffle & Random
    keyboard.append([
        InlineKeyboardButton("🔄 Shuffle / Other 5", callback_data="shuffle_imgs"),
        InlineKeyboardButton("🎲 Random Visual", callback_data="pick_img_random"),
    ])

    # Reset History & Back button
    keyboard.append([
        InlineKeyboardButton("🗑️ Reset History", callback_data="reset_my_history"),
        InlineKeyboardButton("⬅️ Change Category", callback_data="back_to_cats"),
    ])
    return InlineKeyboardMarkup(keyboard)


def build_hook_selection_keyboard(options: List[Dict[str, Any]], category: Optional[str] = None) -> InlineKeyboardMarkup:
    """Step 2/3: 5 viral text hooks + Custom text + Shuffle + Random + Back."""
    keyboard = [
        [
            InlineKeyboardButton("1️⃣ Hook #1", callback_data="pick_hook_0"),
            InlineKeyboardButton("2️⃣ Hook #2", callback_data="pick_hook_1"),
        ],
        [
            InlineKeyboardButton("3️⃣ Hook #3", callback_data="pick_hook_2"),
            InlineKeyboardButton("4️⃣ Hook #4", callback_data="pick_hook_3"),
        ],
        [
            InlineKeyboardButton("5️⃣ Hook #5", callback_data="pick_hook_4"),
            InlineKeyboardButton("🎲 Random Hook", callback_data="pick_hook_random"),
        ],
        [
            InlineKeyboardButton("🔄 Shuffle / Other 5", callback_data="shuffle_hooks"),
        ],
        [
            InlineKeyboardButton("✏️ Type My Own Custom Text", callback_data="pick_hook_custom"),
        ],
        [
            InlineKeyboardButton("⬅️ Back to Visuals", callback_data="back_to_imgs"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_song_selection_keyboard(options: List[Dict[str, Any]], category: Optional[str] = None) -> InlineKeyboardMarkup:
    """Step 3/3: 5 Bollywood vocal tracks + Shuffle + Random + Back."""
    rows = []
    for idx, t in enumerate(options, start=1):
        rows.append([
            InlineKeyboardButton(
                f"{t.get('icon', '🎤')} {idx}. {t['title']} ({t['artist']}) 🎤",
                callback_data=f"pick_song_{t['id']}",
            )
        ])
    rows.append([
        InlineKeyboardButton("🔄 Shuffle / Other 5", callback_data="shuffle_songs"),
        InlineKeyboardButton("🎲 Random Vocal Track", callback_data="pick_song_random"),
    ])
    rows.append([
        InlineKeyboardButton("⬅️ Change Text / Visual", callback_data="back_to_hooks"),
    ])
    return InlineKeyboardMarkup(rows)


@restricted
async def auto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /auto command - directly launches the AryaFeed News Studio Preview."""
    cat_id = "news_banner"
    custom_text = None
    if context.args:
        first_arg = context.args[0].lower().strip()
        if first_arg in ("card", "news_card"):
            cat_id = "news_card"
            if len(context.args) > 1:
                custom_text = " ".join(context.args[1:]).strip()
        elif first_arg in ("banner", "news", "news_banner"):
            cat_id = "news_banner"
            if len(context.args) > 1:
                custom_text = " ".join(context.args[1:]).strip()
        else:
            custom_text = " ".join(context.args).strip()

    context.user_data["chosen_cat"] = cat_id
    await send_interactive_studio_preview(
        update,
        context,
        cat_id=cat_id,
        custom_text=custom_text,
        force_new_img=True,
    )


@restricted
async def reset_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset used asset history for this chat."""
    chat_id = update.effective_chat.id
    await db_manager.clear_used_assets(chat_id)
    if update.effective_message:
        await update.effective_message.reply_text(
            "🔄 *History Cleared!*\nAll previously used images, songs, and hooks are now unlocked again.",
            parse_mode="Markdown",
        )


@restricted
async def handle_quick_text_triggers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user typed quick keywords like 'reel', 'auto', 'news', 'studio'."""
    message = update.effective_message
    if not message or not message.text:
        return False

    raw = message.text.strip().lower()
    if raw in ("reel", "reels", "auto", "start", "new", "image", "video", "create", "news", "studio", "banner", "card"):
        cat_id = "news_card" if raw in ("card", "news_card") else "news_banner"
        context.user_data["chosen_cat"] = cat_id
        await send_interactive_studio_preview(
            update,
            context,
            cat_id=cat_id,
            force_new_img=True,
        )
        return True

    return False
async def send_visual_text_preview(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    img_id: str,
    hook_text: str,
    cat_id: str,
    custom_media_path: Optional[Path] = None,
) -> None:
    """Generate 1080x1920 image composite preview and prompt user for song name."""
    cat_info = get_category_info(cat_id)
    img_opt = get_image_option(img_id)

    # Check for custom uploaded image or library image
    candid_src = None
    if custom_media_path and Path(custom_media_path).exists():
        candid_src = Path(custom_media_path)
    elif img_id == "custom_upload" or context.user_data.get("custom_media_path"):
        ctx_p = context.user_data.get("custom_media_path")
        if ctx_p and Path(ctx_p).exists():
            candid_src = Path(ctx_p)

    if not candid_src or not candid_src.exists():
        direct_p = Path("assets/images/candid") / img_opt.get("filename", "")
        if direct_p.exists():
            candid_src = direct_p
        elif img_id.startswith("pin_"):
            candid_src, _, _ = await asyncio.to_thread(fetch_pinterest_candid_image, category=cat_id, chat_id=chat_id)
        else:
            candid_src, _, _ = await asyncio.to_thread(generate_ai_candid_image, category=cat_id, chat_id=chat_id)

    timestamp = int(asyncio.get_event_loop().time())
    preview_path = config.temp_dir / f"{chat_id}_preview_{timestamp}.jpg"

    if candid_src.exists():
        await asyncio.to_thread(
            generate_preview_composite,
            image_path=candid_src,
            text=hook_text,
            template_key=cat_id,
            output_path=preview_path,
        )
    else:
        # Fallback if source file not found
        shutil.copy(candid_src, preview_path)

    # Save to context & DB session
    context.user_data["chosen_img"] = img_id
    context.user_data["chosen_hook"] = hook_text
    context.user_data["chosen_cat"] = cat_id

    await db_manager.start_reel_session(chat_id)
    await db_manager.update_session(
        chat_id,
        current_step="WAITING_SONG_NAME",
        media_path=str(candid_src),
        overlay_text=hook_text,
        selected_template=cat_id,
    )

    # 5 Fresh song options for this category
    fresh_songs = await get_fresh_song_options(chat_id, category=cat_id, limit=5)
    context.user_data["current_song_options"] = fresh_songs

    caption = (
        "📸 *Visual & Text Preview Ready!*\n\n"
        f"• 📂 *Category:* {cat_info['icon']} *{cat_info['title']}*\n"
        f"• 📸 *Visual:* {img_opt['icon']} {img_opt['title']}\n"
        f"• 📝 *Text:* \"{hook_text}\"\n\n"
        "🎵 *Step 3 of 3: Add Your Bollywood Song*\n"
        "💬 **Type ANY song name in this chat**\n"
        "_(e.g. \"Pee Loon\", \"Kesariya\", \"Zara Sa\", \"Tum Hi Ho\", etc.)_\n\n"
        "👇 **OR tap one of the 5 curated vocal tracks below:**"
    )

    with open(preview_path, "rb") as photo_file:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo_file,
            caption=caption,
            reply_markup=build_song_selection_keyboard(fresh_songs, category=cat_id),
            parse_mode="Markdown",
        )


async def handle_song_name_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    song_name: str,
) -> None:
    """Resolve user-typed song name and proceed to video rendering."""
    chat_id = update.effective_chat.id
    cat = context.user_data.get("chosen_cat")
    img_id = context.user_data.get("chosen_img")
    hook_text = context.user_data.get("chosen_hook")

    session = await db_manager.get_session(chat_id)
    if session:
        if not hook_text and session.get("overlay_text"):
            hook_text = session["overlay_text"]
        if not cat and session.get("selected_template"):
            cat = session["selected_template"]
        if not img_id and session.get("media_path"):
            media_p = session["media_path"]
            for opt in ALL_IMAGE_OPTIONS:
                if opt["filename"] in media_p:
                    img_id = opt["id"]
                    break

    cat = cat or "news_banner"
    img_id = img_id or "news_breaking_1"
    hook_text = hook_text or "22 FRIENDS STUDIED TOGETHER, *21 CRACKED* THE EXAM 🥹🎓"

    resolving_msg = await update.effective_message.reply_text(
        f"🔍 *Matching Bollywood vocal track for \"{song_name}\"...*\nChecking library & vocal chorus...",
        parse_mode="Markdown",
    )

    audio_path, song_display = music_service.resolve_song_by_name(song_name, category=cat)
    song_id = audio_path.stem.replace("_vocal", "").replace("_raw", "")

    try:
        await resolving_msg.delete()
    except Exception:
        pass

    await render_custom_selected_reel(
        update,
        context,
        img_id=img_id,
        song_id=song_id,
        hook_text=hook_text,
        category=cat,
        resolved_audio_path=audio_path,
        resolved_song_title=song_display,
    )


async def render_custom_selected_reel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    img_id: str,
    song_id: str,
    hook_text: str,
    category: Optional[str] = None,
    resolved_audio_path: Optional[Path] = None,
    resolved_song_title: Optional[str] = None,
) -> None:
    """Render 15s 1080x1920 reel with selected non-repeating assets, fade animations and record usage."""
    chat_id = update.effective_chat.id
    cat = category or context.user_data.get("chosen_cat", "news_banner")
    cat_info = get_category_info(cat)
    # 1. Immediately record assets in DB only when NOT in testing mode
    is_testing = await db_manager.is_testing_mode()
    if not is_testing:
        await db_manager.record_used_asset(chat_id, "image", img_opt["id"])
        await db_manager.record_used_asset(chat_id, "music", song_id)
        await db_manager.record_used_asset(chat_id, "text", hook_text)
        logger.info(f"Recorded used assets for chat {chat_id}: img={img_opt['id']}, song={song_id}, cat={cat}")
    else:
        logger.info(f"Testing mode: skipped recording used assets for chat {chat_id}")

    # 2. Resolve vocal track
    if resolved_audio_path and resolved_audio_path.exists():
        vocal_path = resolved_audio_path
        song_title = resolved_song_title or music_service.get_track_title(vocal_path)
    else:
        vocal_path = music_service.get_vocal_track_by_id(song_id)
        if not vocal_path or not vocal_path.exists():
            vocal_path = music_service.get_bollywood_track(cat)
        song_title = music_service.get_track_title(vocal_path)

    # 3. Deploy authentic candid image (custom uploaded photo or library)
    candid_src = None
    if img_id == "custom_upload" or context.user_data.get("custom_media_path"):
        ctx_p = context.user_data.get("custom_media_path")
        if ctx_p and Path(ctx_p).exists():
            candid_src = Path(ctx_p)

    if not candid_src or not candid_src.exists():
        direct_p = Path("assets/images/candid") / img_opt.get("filename", "")
        if direct_p.exists():
            candid_src = direct_p
        elif img_id.startswith("pin_"):
            candid_src, _, _ = await asyncio.to_thread(fetch_pinterest_candid_image, category=cat, chat_id=chat_id)
        else:
            candid_src, _, _ = await asyncio.to_thread(generate_ai_candid_image, category=cat, chat_id=chat_id)

    timestamp = int(asyncio.get_event_loop().time())
    deployed_img = config.input_dir / f"{chat_id}_custom_{timestamp}.jpg"

    if candid_src.exists():
        shutil.copy(candid_src, deployed_img)
    else:
        await asyncio.to_thread(
            generate_ai_visual,
            style=cat,
            output_path=deployed_img,
            text=hook_text,
            use_flux_ai=True,
        )

    # 4. Status notification
    visual_display = "📸 Custom Uploaded Photo" if (img_id == "custom_upload" or context.user_data.get("custom_media_path")) else img_opt["title"]
    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "⚡ *Rendering Your Reel with Smooth Animations...*\n\n"
            f"• 📂 *Category:* {cat_info['icon']} {cat_info['title']}\n"
            f"• 📸 *Visual:* {visual_display}\n"
            f"• 🎤 *Song (Vocals):* {song_title}\n"
            f"• 📝 *Text:* \"{hook_text}\"\n"
            "• 🎬 *Effects:* Smooth Text Fade In/Out + Ken Burns Zoom + Video Fade-to-Black\n\n"
            "Mixing Bollywood vocal chorus & encoding MP4..."
        ),
        parse_mode="Markdown",
    )

    # 5. Save DB session
    await db_manager.start_reel_session(chat_id)
    await db_manager.update_session(
        chat_id,
        media_path=str(deployed_img),
        media_type="image",
        overlay_text=hook_text,
        selected_template=cat,
        music_path=str(vocal_path) if vocal_path else None,
    )

    # 6. Render final video
    try:
        final_video_path = await execute_render_job(chat_id)

        caption = (
            f"🔥 *Reel Ready!*\n\n"
            f"• 📂 *Category:* {cat_info['icon']} {cat_info['title']}\n"
            f"• 📸 *Visual:* {img_opt['title']}\n"
            f"• 📝 *Text:* \"{hook_text}\"\n"
            f"• 🎤 *Vocal Song:* {song_title}\n\n"
            f"Tap below to publish live to Instagram or create another!"
        )

        with open(final_video_path, "rb") as video_file:
            insta_acc = await instagram_service.is_connected(chat_id)
            reply_markup = None
            if insta_acc:
                username = insta_acc.get("username", "Instagram")
                reply_markup = InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🚀 Post to Instagram (@{username})", callback_data="post_insta")
                ]])

            await context.bot.send_video(
                chat_id=chat_id,
                video=video_file,
                caption=caption,
                parse_mode="Markdown",
                supports_streaming=True,
                width=1080,
                height=1920,
                reply_markup=reply_markup,
                write_timeout=180.0,
                read_timeout=180.0,
            )

        # Prepare Instagram caption for auto-post
        ig_caption = generate_instagram_caption(hook_text, style=cat)

        # Auto-post if enabled
        if insta_acc and insta_acc.get("auto_post"):
            async def _bg_publish():
                try:
                    res = await instagram_service.upload_reel(chat_id, final_video_path, caption=ig_caption)
                    if res.get("success"):
                        url = res.get("url") or "Instagram Feed"
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"🚀 *Auto-Posted to Instagram!*\n🔗 [View Reel on Instagram]({url})",
                            parse_mode="Markdown",
                        )
                except Exception as ex:
                    logger.warning(f"Auto-post failed: {ex}")

            asyncio.create_task(_bg_publish())

        cleanup_chat_files(chat_id)
        await status_msg.delete()

    except Exception as e:
        logger.exception(f"Custom reel generation error: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Rendering failed. Please try again with /reel or /auto.",
        )


@restricted
async def complete_custom_reel_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, custom_text: str) -> None:
    """Handle custom text input: generate preview first and ask for song name."""
    chat_id = update.effective_chat.id
    cat = context.user_data.get("chosen_cat", "news_banner")
    img_id = context.user_data.get("chosen_img", "news_breaking_1")
    await send_visual_text_preview(update, context, chat_id, img_id=img_id, hook_text=custom_text, cat_id=cat)




# -------------------------------------------------------------
# Interactive Studio Flow with Used Folder & Instant Previews
# -------------------------------------------------------------

def get_random_category_image(cat_id: str, chat_id: int, used_names_override: Optional[set] = None) -> Path:
    """Pick a random unused image for AryaFeed news."""
    cat_dir = Path("assets/images/categories/news")
    used_dir = Path("assets/images/used")

    used_names = set(used_names_override) if used_names_override else set()
    if used_dir.exists():
        for f in used_dir.iterdir():
            if f.is_file():
                used_names.add(f.name)

    files = [f for f in cat_dir.iterdir() if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png")] if cat_dir.exists() else []
    available = [f for f in files if f.name not in used_names]
    if not available:
        available = files

    if not available:
        return Path("assets/images/categories/news/10.jpg")

    return random.choice(available)


def build_studio_preview_keyboard() -> InlineKeyboardMarkup:
    """Action buttons attached to the live 1080x1920 AryaFeed preview image."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 Render AryaFeed Reel", callback_data="studio_render")
        ],
        [
            InlineKeyboardButton("⏭️ Next Photo", callback_data="studio_skip"),
            InlineKeyboardButton("🔄 New Headline", callback_data="studio_new_text"),
        ],
        [
            InlineKeyboardButton("✏️ Custom Headline", callback_data="studio_custom_text"),
            InlineKeyboardButton("📰 Toggle Card/Banner", callback_data="studio_toggle_style"),
        ],
    ])


async def send_interactive_studio_preview(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    cat_id: str,
    image_path: Optional[Path] = None,
    custom_text: Optional[str] = None,
    force_new_img: bool = False,
) -> None:
    """Generate 1080x1920 preview with text and present Skip/Render/Custom-Text buttons."""
    chat_id = update.effective_chat.id
    cat_info = get_category_info(cat_id)

    # 1. Resolve image
    if force_new_img or not image_path or not image_path.exists():
        image_path = get_random_category_image(cat_id, chat_id)

    # 2. Resolve text
    if not custom_text:
        cat_hooks = [h["text"] for h in ALL_HOOK_OPTIONS if cat_id in h.get("categories", [])]
        if not cat_hooks:
            cat_hooks = [h["text"] for h in ALL_HOOK_OPTIONS]
        chosen_text = random.choice(cat_hooks)
    else:
        chosen_text = custom_text

    # 3. Store in context & session
    context.user_data["chosen_cat"] = cat_id
    context.user_data["studio_img_path"] = str(image_path)
    context.user_data["studio_text"] = chosen_text
    context.user_data["waiting_for_custom_text"] = False

    await db_manager.start_reel_session(chat_id)
    await db_manager.update_session(
        chat_id,
        current_step="STUDIO_PREVIEW",
        media_path=str(image_path),
        overlay_text=chosen_text,
        selected_template=cat_id,
    )

    # 4. Generate composite preview (1080x1920)
    timestamp = int(asyncio.get_event_loop().time())
    preview_path = config.temp_dir / f"{chat_id}_studio_{timestamp}.jpg"

    await asyncio.to_thread(
        generate_preview_composite,
        image_path=image_path,
        text=chosen_text,
        template_key=cat_id,
        output_path=preview_path,
    )

    caption = (
        f"📸 *Live Reel Studio Preview (1080x1920)*\n\n"
        f"• 📂 *Category:* {cat_info['icon']} *{cat_info['title']}*\n"
        f"• 🖼️ *Image:* `{image_path.name}`\n"
        f"• ✍️ *Text:* \"_{chosen_text}_\"\n\n"
        f"👉 Tap **🎬 Render Reel** to finalize video.\n"
        f"👉 Tap **⏭️ Skip Photo** to preview next image.\n"
        f"👉 Tap **✏️ Custom Text** to enter your own lines."
    )

    with open(preview_path, "rb") as photo_f:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo_f,
            caption=caption,
            reply_markup=build_studio_preview_keyboard(),
            parse_mode="Markdown",
        )


async def handle_studio_custom_text_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    custom_text: str,
) -> None:
    """Re-render studio preview with user's custom entered text."""
    cat_id = context.user_data.get("chosen_cat", "news_banner")
    img_p_str = context.user_data.get("studio_img_path")
    img_p = Path(img_p_str) if (img_p_str and Path(img_p_str).exists()) else None

    await send_interactive_studio_preview(
        update,
        context,
        cat_id=cat_id,
        image_path=img_p,
        custom_text=custom_text,
        force_new_img=False,
    )


async def execute_studio_reel_render(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    image_path: Path,
    hook_text: str,
    cat_id: str,
) -> None:
    """Render full 9:16 reel, move image to assets/images/used/ and record in DB."""
    cat_info = get_category_info(cat_id)
    vocal_path = music_service.get_bollywood_track(cat_id)
    song_title = music_service.get_track_title(vocal_path)

    timestamp = int(asyncio.get_event_loop().time())
    deployed_img = config.input_dir / f"{chat_id}_studio_{timestamp}.jpg"
    shutil.copy(image_path, deployed_img)

    await db_manager.start_reel_session(chat_id)
    await db_manager.update_session(
        chat_id,
        media_path=str(deployed_img),
        media_type="image",
        overlay_text=hook_text,
        selected_template=cat_id,
        music_path=str(vocal_path) if vocal_path else None,
    )

    try:
        final_video_path = await execute_render_job(chat_id)

        # 5. Move image to used folder ONLY when NOT in testing mode
        is_testing = await db_manager.is_testing_mode()
        if not is_testing:
            used_dir = Path("assets/images/used")
            used_dir.mkdir(parents=True, exist_ok=True)
            dest_used = used_dir / image_path.name
            try:
                if image_path.exists() and "assets/images/categories" in str(image_path).replace("\\", "/"):
                    shutil.move(str(image_path), str(dest_used))
                    logger.info(f"Image {image_path.name} moved to {dest_used}")
            except Exception as e:
                logger.warning(f"Error moving image to used: {e}")

            await db_manager.record_used_asset(chat_id, "image", image_path.name)
            await db_manager.record_used_asset(chat_id, "text", hook_text)
            status_tag = "*(Moved to Used Folder ✅)*"
        else:
            logger.info(f"Testing mode: kept {image_path.name} in category pool without moving to used")
            status_tag = "*(Testing Mode — Kept in Pool 🔄)*"

        hashtags = "#reels #trending #viral #fyp #explore #explorepage #instareels #aesthetic"
        caption = (
            f"🔥 *Reel Ready!*\n\n"
            f"• 📂 *Category:* {cat_info['icon']} {cat_info['title']}\n"
            f"• 📸 *Image:* `{image_path.name}` {status_tag}\n"
            f"• 🎤 *Song:* {song_title}\n"
            f"• 📝 *Text:* \"{hook_text}\"\n\n"
            f"_{hook_text}_\n\n"
            f"{hashtags}"
        )

        with open(final_video_path, "rb") as video_file:
            await context.bot.send_video(
                chat_id=chat_id,
                video=video_file,
                caption=caption,
                supports_streaming=True,
                parse_mode="Markdown",
                write_timeout=180,
                read_timeout=180,
            )

        await context.bot.send_message(
            chat_id=chat_id,
            text="✨ *Create Another Reel:* Select a category below:",
            reply_markup=build_category_selection_keyboard(),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Studio reel render failed: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Render Error:* {e}\nPlease type /auto to try again.",
            parse_mode="Markdown",
        )


@restricted
async def handle_auto_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle interactive button presses for the Category-First 5-5-5 selection flow."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    chat_id = update.effective_chat.id

    # -------------------------------------------------------------
    # Step 0 -> Step 1: User chose Category
    # -------------------------------------------------------------
    if data.startswith("cat_"):
        cat_id = data.replace("cat_", "")
        context.user_data["chosen_cat"] = cat_id
        try:
            await query.delete_message()
        except Exception:
            pass
        await send_interactive_studio_preview(update, context, cat_id=cat_id, force_new_img=True)
        return

    elif data == "auto_render_custom_reel":
        session = await db_manager.get_session(chat_id)
        img_path = session.get("media_path") if session else None
        if not img_path or not Path(img_path).exists():
            await query.edit_message_caption("❌ Image file not found for reel generation.")
            return

        status_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="🎬 *Rendering 1080x1920 ARYAFEED Animated Reel...*\n\nAdding Ken Burns zoom motion, Bollywood vocal audio & `[ ARYAFEED ]` watermark ⚡",
            parse_mode="Markdown"
        )

        cat_id = "news_banner"
        vocal_path = music_service.get_bollywood_track(cat_id)
        song_title = music_service.get_track_title(vocal_path)

        timestamp = int(asyncio.get_event_loop().time())
        deployed_img = config.input_dir / f"{chat_id}_custom_reel_{timestamp}.jpg"
        shutil.copy(img_path, deployed_img)

        await db_manager.update_session(
            chat_id,
            media_path=str(deployed_img),
            media_type="image",
            selected_template=cat_id,
            music_path=str(vocal_path) if vocal_path else None,
        )

        try:
            final_video = await execute_render_job(chat_id)
            caption = session.get("custom_caption") or "⚡ Daily dose of viral stories & reels @aryafeed.in\n#aryafeed #reels #viral #trending"

            await db_manager.update_session(
                chat_id,
                output_path=str(final_video),
                media_type="video",
                custom_caption=caption,
            )

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🚀 1-Tap Post Reel to Instagram", callback_data="post_insta"),
                ]
            ])

            try:
                await status_msg.delete()
            except Exception:
                pass

            with open(final_video, "rb") as vf:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=vf,
                    caption=(
                        f"🎬 *ARYAFEED 1080x1920 Reel Ready!*\n\n"
                        f"🎵 *Audio:* {song_title}\n"
                        f"🏷️ *Brand:* `[ ARYAFEED ]` (Bottom Right)\n\n"
                        f"Tap below to publish reel live to `@aryafeed.in`:"
                    ),
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.exception(f"Custom reel render failed: {e}")
            await status_msg.edit_text(f"❌ Reel rendering failed: {e}")
        return

    elif data == "studio_skip":
        cat_id = context.user_data.get("chosen_cat", "news_banner")
        try:
            await query.delete_message()
        except Exception:
            pass
        await send_interactive_studio_preview(update, context, cat_id=cat_id, force_new_img=True)
        return

    elif data == "studio_new_text":
        cat_id = context.user_data.get("chosen_cat", "news_banner")
        img_p_str = context.user_data.get("studio_img_path")
        img_p = Path(img_p_str) if img_p_str else None
        try:
            await query.delete_message()
        except Exception:
            pass
        await send_interactive_studio_preview(update, context, cat_id=cat_id, image_path=img_p, custom_text=None, force_new_img=False)
        return

    elif data == "studio_toggle_style":
        curr_cat = context.user_data.get("chosen_cat", "news_banner")
        next_cat = "news_card" if curr_cat != "news_card" else "news_banner"
        context.user_data["chosen_cat"] = next_cat
        img_p_str = context.user_data.get("studio_img_path")
        hook_text = context.user_data.get("studio_text")
        img_p = Path(img_p_str) if img_p_str else None
        try:
            await query.delete_message()
        except Exception:
            pass
        await send_interactive_studio_preview(update, context, cat_id=next_cat, image_path=img_p, custom_text=hook_text, force_new_img=False)
        return

    elif data == "studio_custom_text":
        context.user_data["waiting_for_custom_text"] = True
        await db_manager.update_session(chat_id, current_step="WAITING_STUDIO_TEXT")
        msg = (
            "✏️ *Type your AryaFeed breaking headline / news text:*\n\n"
            "Send your text in this chat, and the bot will instantly render a new preview with `[ ARYAFEED.IN ]` badge on this photo!"
        )
        if query.message:
            await query.message.reply_text(msg, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        return

    elif data == "studio_render":
        cat_id = context.user_data.get("chosen_cat", "news_banner")
        img_p_str = context.user_data.get("studio_img_path")
        hook_text = context.user_data.get("studio_text", "22 FRIENDS STUDIED TOGETHER, *21 CRACKED* THE EXAM 🥹🎓")
        img_p = Path(img_p_str) if (img_p_str and Path(img_p_str).exists()) else get_random_category_image(cat_id, chat_id)

        try:
            await query.edit_message_caption(
                caption=f"⚡ *AryaFeed Reel Rendering Started...*\n\n• Style: *{cat_id.replace('_', ' ').title()}*\n• Media: `{img_p.name}`\n\n_Generating 1080x1920 HD vertical news reel..._",
                parse_mode="Markdown",
            )
        except Exception:
            pass

        await execute_studio_reel_render(update, context, chat_id=chat_id, image_path=img_p, hook_text=hook_text, cat_id=cat_id)
        return

    # -------------------------------------------------------------
    # Shuffle Images for Current Category
    # -------------------------------------------------------------
    elif data == "shuffle_imgs":
        cat_id = context.user_data.get("chosen_cat", "news_banner")
        cat_info = get_category_info(cat_id)
        fresh_images = await get_fresh_image_options(chat_id, category=cat_id, limit=5)
        context.user_data["current_img_options"] = fresh_images

        msg = (
            f"📸 *Step 1 of 3: Choose Visual (Image)*\n\n"
            f"📂 *Category:* {cat_info['icon']} *{cat_info['title']}*\n"
            f"_{cat_info['desc']}_\n\n"
            "Select 1 of 5 photo aesthetics below:\n"
            "_(💡 Shuffled 5 fresh options!)_"
        )
        await query.edit_message_text(
            msg,
            reply_markup=build_image_selection_keyboard(fresh_images, category=cat_id),
            parse_mode="Markdown",
        )

    # -------------------------------------------------------------
    # Back to Categories
    # -------------------------------------------------------------
    elif data == "back_to_cats":
        try:
            await query.delete_message()
        except Exception:
            pass
        await send_interactive_studio_preview(update, context, cat_id="news_banner", force_new_img=True)
        return

    # -------------------------------------------------------------
    # Upload Own Image Instruction
    # -------------------------------------------------------------
    elif data == "upload_own_img":
        cat_id = context.user_data.get("chosen_cat", "news_banner")
        cat_info = get_category_info(cat_id)
        msg = (
            f"📸 *Send Your Custom Image Now:*\n\n"
            f"📂 *Active Category:* {cat_info['icon']} *{cat_info['title']}*\n\n"
            "Apne phone ya computer se ChatGPT Pro, Gemini, ya Gallery ki koi bhi photo **is chat me bhej dein**!\n\n"
            "💡 *Bot automatically:*\n"
            "• 1080x1920 HD vertical fit karega (cinematic blurred background)\n"
            "• Slow-zoom Ken Burns motion lagayega\n"
            "• Aur turant Text Hook & Song selection open karega."
        )
        await query.message.reply_text(msg, parse_mode="Markdown")

    # -------------------------------------------------------------
    # Dynamic AI Photo Generation Button
    # -------------------------------------------------------------
    elif data == "gen_ai_photo":
        cat_id = context.user_data.get("chosen_cat", "news_banner")
        cat_info = get_category_info(cat_id)
        await query.edit_message_text(
            f"✨ *Generating a brand new AI candid photo for {cat_info['title']}...*\n"
            "_(Checking OpenAI / Gemini / Dynamic film synthesis - zero repeats)_",
            parse_mode="Markdown",
        )
        out_file, unique_id, title = await asyncio.to_thread(
            generate_ai_candid_image,
            category=cat_id,
            chat_id=chat_id,
        )
        context.user_data["custom_media_path"] = str(out_file)
        context.user_data["chosen_img"] = unique_id
        if not await db_manager.is_testing_mode():
            await db_manager.record_used_asset(chat_id, "image", unique_id)

        fresh_hooks = await get_fresh_hook_options(chat_id, category=cat_id, limit=5)
        context.user_data["current_hook_options"] = fresh_hooks
        hooks_text = "\n".join([f"{idx}️⃣ _{h['text']}_" for idx, h in enumerate(fresh_hooks, start=1)])

        msg = (
            f"📝 *Step 2 of 3: Choose Reel Text / Hook*\n\n"
            f"📂 *Category:* {cat_info['icon']} *{cat_info['title']}*\n"
            f"📸 *Visual:* {title}\n\n"
            f"Select 1 of 5 viral quotes below, or type your own:\n\n"
            f"{hooks_text}\n\n"
            f"_(💡 Next, an instant visual preview with this AI visual will be created!)_"
        )
        await query.message.reply_text(
            msg,
            reply_markup=build_hook_selection_keyboard(fresh_hooks, category=cat_id),
            parse_mode="Markdown",
        )

    # -------------------------------------------------------------
    # Fetch Pinterest Photo Button
    # -------------------------------------------------------------
    elif data == "fetch_pin_photo":
        cat_id = context.user_data.get("chosen_cat", "news_banner")
        cat_info = get_category_info(cat_id)
        await query.edit_message_text(
            f"📌 *Fetching fresh vertical candid photo from Pinterest CDN...*\n"
            f"_(Category: {cat_info['title']} - zero repetition guarantee)_",
            parse_mode="Markdown",
        )
        out_file, unique_id, title = await asyncio.to_thread(
            fetch_pinterest_candid_image,
            category=cat_id,
            chat_id=chat_id,
        )
        context.user_data["custom_media_path"] = str(out_file)
        context.user_data["chosen_img"] = unique_id
        if not await db_manager.is_testing_mode():
            await db_manager.record_used_asset(chat_id, "image", unique_id)

        fresh_hooks = await get_fresh_hook_options(chat_id, category=cat_id, limit=5)
        context.user_data["current_hook_options"] = fresh_hooks
        hooks_text = "\n".join([f"{idx}️⃣ _{h['text']}_" for idx, h in enumerate(fresh_hooks, start=1)])

        msg = (
            f"📝 *Step 2 of 3: Choose Reel Text / Hook*\n\n"
            f"📂 *Category:* {cat_info['icon']} *{cat_info['title']}*\n"
            f"📸 *Visual:* {title}\n\n"
            f"Select 1 of 5 viral quotes below, or type your own:\n\n"
            f"{hooks_text}\n\n"
            f"_(💡 Next, an instant visual preview with this Pinterest photo will be created!)_"
        )
        await query.message.reply_text(
            msg,
            reply_markup=build_hook_selection_keyboard(fresh_hooks, category=cat_id),
            parse_mode="Markdown",
        )

    # -------------------------------------------------------------
    # Reset History Button
    # -------------------------------------------------------------
    elif data == "reset_my_history":
        await db_manager.clear_used_assets(chat_id, "image")
        cat_id = context.user_data.get("chosen_cat", "news_banner")
        cat_info = get_category_info(cat_id)
        fresh_images = await get_fresh_image_options(chat_id, category=cat_id, limit=5)
        context.user_data["current_img_options"] = fresh_images

        msg = (
            f"🔄 *Image History Cleared!*\n\n"
            f"All 30+ candid aesthetics and dynamic slots are unlocked again.\n\n"
            f"📂 *Category:* {cat_info['icon']} *{cat_info['title']}*\n"
            f"Select 1 of 5 fresh options below:"
        )
        await query.edit_message_text(
            msg,
            reply_markup=build_image_selection_keyboard(fresh_images, category=cat_id),
            parse_mode="Markdown",
        )

    # -------------------------------------------------------------
    # Step 1 -> Step 2: User chose Image -> Show Text Hooks for Category
    # -------------------------------------------------------------
    elif data.startswith("pick_img_"):
        raw_img = data.replace("pick_img_", "")
        current_img_opts = context.user_data.get("current_img_options", ALL_IMAGE_OPTIONS)
        if raw_img == "random":
            chosen_opt = random.choice(current_img_opts)
        else:
            chosen_opt = get_image_option(raw_img)
        context.user_data["chosen_img"] = chosen_opt["id"]

        cat_id = context.user_data.get("chosen_cat", "news_banner")
        cat_info = get_category_info(cat_id)

        # Fetch 5 fresh viral quotes matching this category
        fresh_hooks = await get_fresh_hook_options(chat_id, category=cat_id, limit=5)
        context.user_data["current_hook_options"] = fresh_hooks

        hooks_text = "\n".join([f"{idx}️⃣ _{h['text']}_" for idx, h in enumerate(fresh_hooks, start=1)])

        msg = (
            f"📝 *Step 2 of 3: Choose Reel Text / Hook*\n\n"
            f"📂 *Category:* {cat_info['icon']} *{cat_info['title']}*\n"
            f"📸 *Visual:* {chosen_opt['icon']} {chosen_opt['title']}\n\n"
            f"Select 1 of 5 viral quotes below, or type your own:\n\n"
            f"{hooks_text}\n\n"
            f"_(💡 Next, an instant visual preview with this text will be created!)_"
        )
        await query.edit_message_text(
            msg,
            reply_markup=build_hook_selection_keyboard(fresh_hooks, category=cat_id),
            parse_mode="Markdown",
        )

    # -------------------------------------------------------------
    # Shuffle Hooks for Current Category
    # -------------------------------------------------------------
    elif data == "shuffle_hooks":
        cat_id = context.user_data.get("chosen_cat", "news_banner")
        cat_info = get_category_info(cat_id)
        img_id = context.user_data.get("chosen_img", "news_breaking_1")
        img_opt = get_image_option(img_id)

        fresh_hooks = await get_fresh_hook_options(chat_id, category=cat_id, limit=5)
        context.user_data["current_hook_options"] = fresh_hooks

        hooks_text = "\n".join([f"{idx}️⃣ _{h['text']}_" for idx, h in enumerate(fresh_hooks, start=1)])

        msg = (
            f"📝 *Step 2 of 3: Choose Reel Text / Hook*\n\n"
            f"📂 *Category:* {cat_info['icon']} *{cat_info['title']}*\n"
            f"📸 *Visual:* {img_opt['icon']} {img_opt['title']}\n\n"
            f"Select 1 of 5 viral quotes below, or type your own:\n\n"
            f"{hooks_text}\n\n"
            f"_(💡 Shuffled 5 fresh quotes!)_"
        )
        await query.edit_message_text(
            msg,
            reply_markup=build_hook_selection_keyboard(fresh_hooks, category=cat_id),
            parse_mode="Markdown",
        )

    # -------------------------------------------------------------
    # Back to Visuals
    # -------------------------------------------------------------
    elif data == "back_to_imgs":
        cat_id = context.user_data.get("chosen_cat", "news_banner")
        cat_info = get_category_info(cat_id)
        fresh_images = await get_fresh_image_options(chat_id, category=cat_id, limit=5)
        context.user_data["current_img_options"] = fresh_images

        msg = (
            f"📸 *Step 1 of 3: Choose Visual (Image)*\n\n"
            f"📂 *Category:* {cat_info['icon']} *{cat_info['title']}*\n"
            f"_{cat_info['desc']}_\n\n"
            "Select 1 of 5 authentic candid photo aesthetics below:"
        )
        await query.edit_message_text(
            msg,
            reply_markup=build_image_selection_keyboard(fresh_images, category=cat_id),
            parse_mode="Markdown",
        )

    # -------------------------------------------------------------
    # Step 2 -> Step 3: User chose a Hook -> Generate Instant Preview First!
    # -------------------------------------------------------------
    elif data.startswith("pick_hook_"):
        raw_hook = data.replace("pick_hook_", "")
        cat_id = context.user_data.get("chosen_cat", "news_banner")
        img_id = context.user_data.get("chosen_img", "news_breaking_1")

        if raw_hook == "custom":
            img_opt = get_image_option(img_id)
            await db_manager.start_reel_session(chat_id)
            await db_manager.update_session(chat_id, current_step="WAITING_CUSTOM_TEXT")

            await query.edit_message_text(
                f"✍️ *Type Your Custom Text*\n\n"
                f"📸 *Visual:* {img_opt['icon']} {img_opt['title']}\n\n"
                f"Please reply with your custom text in this chat:\n"
                f"_(Example: \"kisi ko itna chaho ki koi aur chahat na rahe... 💖\")_",
                parse_mode="Markdown",
            )
            return

        current_hook_opts = context.user_data.get("current_hook_options", ALL_HOOK_OPTIONS[:5])
        if raw_hook == "random":
            chosen_hook = random.choice(current_hook_opts)["text"]
        else:
            try:
                idx = int(raw_hook)
                chosen_hook = current_hook_opts[idx]["text"]
            except Exception:
                chosen_hook = current_hook_opts[0]["text"]

        await query.edit_message_text("⚡ Generating your high-definition visual & text preview...")
        await send_visual_text_preview(
            update,
            context,
            chat_id=chat_id,
            img_id=img_id,
            hook_text=chosen_hook,
            cat_id=cat_id,
        )

    # -------------------------------------------------------------
    # Shuffle Songs on Preview Screen
    # -------------------------------------------------------------
    elif data == "shuffle_songs":
        cat_id = context.user_data.get("chosen_cat", "news_banner")
        fresh_songs = await get_fresh_song_options(chat_id, category=cat_id, limit=5)
        context.user_data["current_song_options"] = fresh_songs
        await query.edit_message_reply_markup(
            reply_markup=build_song_selection_keyboard(fresh_songs, category=cat_id)
        )

    # -------------------------------------------------------------
    # Back to Hooks from Preview
    # -------------------------------------------------------------
    elif data == "back_to_hooks":
        cat_id = context.user_data.get("chosen_cat", "news_banner")
        cat_info = get_category_info(cat_id)
        img_id = context.user_data.get("chosen_img", "news_breaking_1")
        img_opt = get_image_option(img_id)

        fresh_hooks = await get_fresh_hook_options(chat_id, category=cat_id, limit=5)
        context.user_data["current_hook_options"] = fresh_hooks
        hooks_text = "\n".join([f"{idx}️⃣ _{h['text']}_" for idx, h in enumerate(fresh_hooks, start=1)])

        msg = (
            f"📝 *Step 2 of 3: Choose Reel Text / Hook*\n\n"
            f"📂 *Category:* {cat_info['icon']} *{cat_info['title']}*\n"
            f"📸 *Visual:* {img_opt['icon']} {img_opt['title']}\n\n"
            f"Select 1 of 5 viral quotes below, or type your own:\n\n"
            f"{hooks_text}"
        )
        await query.edit_message_text(
            msg,
            reply_markup=build_hook_selection_keyboard(fresh_hooks, category=cat_id),
            parse_mode="Markdown",
        )

    # -------------------------------------------------------------
    # Step 3 -> Final Render: User tapped a Song button
    # -------------------------------------------------------------
    elif data.startswith("pick_song_"):
        raw_song = data.replace("pick_song_", "")
        current_song_opts = context.user_data.get("current_song_options", [])
        if raw_song == "random":
            chosen_song = random.choice(current_song_opts) if current_song_opts else {"id": "pee_loon", "title": "Pee Loon"}
            raw_song = chosen_song["id"]

        cat_id = context.user_data.get("chosen_cat", "news_banner")
        img_id = context.user_data.get("chosen_img", "news_breaking_1")
        hook_text = context.user_data.get("chosen_hook", "")

        await query.edit_message_text("⚡ Starting your animated reel generation with vocal audio...")
        await render_custom_selected_reel(
            update,
            context,
            img_id=img_id,
            song_id=raw_song,
            hook_text=hook_text,
            category=cat_id,
        )

    # -------------------------------------------------------------
    # Legacy Fallbacks
    # -------------------------------------------------------------
    elif data.startswith("reel_type_"):
        cat_id = data.replace("reel_type_", "")
        context.user_data["chosen_cat"] = cat_id
        cat_info = get_category_info(cat_id)
        fresh_images = await get_fresh_image_options(chat_id, category=cat_id, limit=5)
        context.user_data["current_img_options"] = fresh_images
        await query.edit_message_text(
            f"📸 *Step 1 of 3: Choose Visual (Image)*\n\n📂 *Category:* {cat_info['title']}\nSelect one of 5 candid aesthetics below:",
            reply_markup=build_image_selection_keyboard(fresh_images, category=cat_id),
            parse_mode="Markdown",
        )


@restricted
async def set_gemini_key_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set or update Google Gemini API key dynamically."""
    message = update.effective_message
    if not message:
        return
    args = context.args or []
    if not args:
        await message.reply_text(
            "🔑 *Usage:* `/set_gemini_key YOUR_GEMINI_API_KEY`\n\n"
            "Get your key starting with `AIzaSy...` from Google AI Studio:\n"
            "https://aistudio.google.com/app/apikey",
            parse_mode="Markdown",
        )
        return

    new_key = args[0].strip()
    os.environ["GEMINI_API_KEY"] = new_key
    try:
        env_file = Path(".env")
        if env_file.exists():
            lines = env_file.read_text(encoding="utf-8").splitlines()
            new_lines = []
            found = False
            for line in lines:
                if line.startswith("GEMINI_API_KEY="):
                    new_lines.append(f"GEMINI_API_KEY={new_key}")
                    found = True
                else:
                    new_lines.append(line)
            if not found:
                new_lines.append(f"GEMINI_API_KEY={new_key}")
            env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except Exception as e:
        logger.warning(f"Could not write to .env: {e}")

    await message.reply_text(
        f"✅ *Google Gemini Key Saved!*\nKey prefix: `{new_key[:8]}...`\nBot will use Gemini Imagen 3 for dynamic AI candid photos!",
        parse_mode="Markdown",
    )


@restricted
async def set_openai_key_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set or update OpenAI API key dynamically."""
    message = update.effective_message
    if not message:
        return
    args = context.args or []
    if not args:
        await message.reply_text(
            "🔑 *Usage:* `/set_openai_key YOUR_OPENAI_API_KEY`\n\n"
            "Get your key from OpenAI Platform:\n"
            "https://platform.openai.com/api-keys",
            parse_mode="Markdown",
        )
        return

    new_key = args[0].strip()
    os.environ["OPENAI_API_KEY"] = new_key
    try:
        env_file = Path(".env")
        if env_file.exists():
            lines = env_file.read_text(encoding="utf-8").splitlines()
            new_lines = []
            found = False
            for line in lines:
                if line.startswith("OPENAI_API_KEY="):
                    new_lines.append(f"OPENAI_API_KEY={new_key}")
                    found = True
                else:
                    new_lines.append(line)
            if not found:
                new_lines.append(f"OPENAI_API_KEY={new_key}")
            env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except Exception as e:
        logger.warning(f"Could not write to .env: {e}")

    await message.reply_text(
        f"✅ *OpenAI Key Saved!*\nKey prefix: `{new_key[:8]}...`\nBot will use DALL-E 3 for dynamic AI candid photos!",
        parse_mode="Markdown",
    )

