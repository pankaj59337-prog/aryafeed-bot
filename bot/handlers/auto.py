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

# Core Categories / Vibes (8 Curated Aesthetic Styles)
CATEGORIES: Dict[str, Dict[str, Any]] = {
    "sexy": {
        "id": "sexy",
        "title": "Sexy / Flirty Desi",
        "icon": "💋",
        "desc": "Bold candid selfies, sultry flirty glances & backless aesthetic",
        "style": "sexy",
    },
    "baddie": {
        "id": "baddie",
        "title": "Hot & Baddie / Attitude",
        "icon": "🔥",
        "desc": "Sassy attitude, baddie vibes, mirror selfies & self-love",
        "style": "baddie",
    },
    "bestie": {
        "id": "bestie",
        "title": "Bestie Love / Duo Goals",
        "icon": "👯‍♀️",
        "desc": "Cute bestie bonds, crime partners, sisterhood & duo aesthetics",
        "style": "bestie",
    },
    "romantic": {
        "id": "romantic",
        "title": "Romantic / Love",
        "icon": "💖",
        "desc": "Pastel sarees, soulmate quotes & emotional love tracks",
        "style": "romantic",
    },
    "cinematic": {
        "id": "cinematic",
        "title": "Late Night / Cinematic",
        "icon": "🎬",
        "desc": "Moody streetlights, car drives, city bokeh & deep thoughts",
        "style": "cinematic",
    },
    "traditional": {
        "id": "traditional",
        "title": "Desi Traditional",
        "icon": "👑",
        "desc": "Royal silk sarees, classic Indian poise & timeless shayari",
        "style": "traditional",
    },
    "broken": {
        "id": "broken",
        "title": "Broken Heart / Dard",
        "icon": "💔",
        "desc": "Emotional heartbreak, deep pain, sad poetry & melancholic melodies",
        "style": "cinematic",
    },
    "aesthetic": {
        "id": "aesthetic",
        "title": "Aesthetic / Soft Glow",
        "icon": "✨",
        "desc": "Golden hour glow, peaceful vibes, soft lifestyle & calm soul",
        "style": "minimal",
    },
    "news": {
        "id": "news",
        "title": "AryaFeed Viral News",
        "icon": "⚡",
        "desc": "High-curiosity news, trending Indian milestones, CCTV & relatable culture",
        "style": "news_banner",
    },
}

# 30 Curated Authentic Candid Reference Aesthetics (100% real photo aesthetic, zero CGI)
ALL_IMAGE_OPTIONS: List[Dict[str, Any]] = [
    {
        "id": "sheer_saree",
        "title": "Sheer Saree Mirror",
        "filename": "sheer_saree_mirror_selfie.jpg",
        "icon": "🖤",
        "desc": "Black sheer saree bedroom mirror selfie",
        "categories": ["sexy", "romantic", "traditional"],
    },
    {
        "id": "red_saree",
        "title": "Crimson Saree Mirror",
        "filename": "red_saree_candid_selfie.jpg",
        "icon": "🌹",
        "desc": "Crimson red chiffon saree bedroom mirror selfie",
        "categories": ["sexy", "romantic", "traditional"],
    },
    {
        "id": "balcony_saree",
        "title": "Balcony Night Saree",
        "filename": "saree_night_balcony.jpg",
        "icon": "🍷",
        "desc": "Burgundy silk saree with midnight city bokeh",
        "categories": ["cinematic", "romantic", "sexy"],
    },
    {
        "id": "slipdress_bedroom",
        "title": "Bedroom Lace Slipdress",
        "filename": "bedroom_slipdress_selfie.jpg",
        "icon": "🤍",
        "desc": "White lace slipdress bedroom mirror candid",
        "categories": ["sexy", "cinematic"],
    },
    {
        "id": "backless_saree",
        "title": "Backless Dori Saree",
        "filename": "desi_backless_blouse_candid.jpg",
        "icon": "💖",
        "desc": "Magenta pink saree with backless dori blouse",
        "categories": ["sexy", "traditional", "romantic"],
    },
    {
        "id": "royal_saree",
        "title": "Royal Emerald Saree",
        "filename": "royal_green_saree.jpg",
        "icon": "💚",
        "desc": "Royal emerald silk saree candid grace",
        "categories": ["traditional", "romantic", "cinematic"],
    },
    {
        "id": "halter_denim",
        "title": "Halter Top & Denim",
        "filename": "halter_denim_candid.jpg",
        "icon": "💛",
        "desc": "Yellow halter crop top with blue denim mirror",
        "categories": ["sexy", "cinematic"],
    },
    {
        "id": "croptop_mirror",
        "title": "Scoop Crop Top Mirror",
        "filename": "candid_croptop_mirror_selfie.jpg",
        "icon": "✨",
        "desc": "Black scoop crop top with white linen pants",
        "categories": ["sexy", "cinematic"],
    },
    {
        "id": "pastel_saree",
        "title": "Pastel Floral Saree",
        "filename": "pastel_saree_romantic.jpg",
        "icon": "🌸",
        "desc": "Lavender floral organza saree golden hour",
        "categories": ["romantic", "traditional"],
    },
    {
        "id": "desi_lamp_saree",
        "title": "Midnight Lamp Saree",
        "filename": "desi_saree_candid_selfie.jpg",
        "icon": "🕯️",
        "desc": "Black saree with warm bedroom night lamp",
        "categories": ["cinematic", "sexy", "traditional"],
    },
    {
        "id": "night_drive",
        "title": "Cinematic Night Drive",
        "filename": "cinematic_night_drive.jpg",
        "icon": "🌃",
        "desc": "Car passenger seat late night city neon bokeh",
        "categories": ["cinematic", "romantic"],
    },
    {
        "id": "candid_real_selfie",
        "title": "Golden Hour Glow",
        "filename": "candid_real_selfie.jpg",
        "icon": "🌅",
        "desc": "Warm golden hour natural candid selfie",
        "categories": ["romantic", "cinematic", "sexy"],
    },
    {
        "id": "sultry_bedroom_candid",
        "title": "Midnight Silk Slipdress",
        "filename": "sultry_bedroom_candid.jpg",
        "icon": "🖤",
        "desc": "Moody midnight bedroom silk candid aesthetic",
        "categories": ["sexy", "cinematic"],
    },
    {
        "id": "sultry_cinematic_portrait",
        "title": "Streetlights Cinematic",
        "filename": "sultry_cinematic_portrait.jpg",
        "icon": "🎬",
        "desc": "Evening ambient streetlights portrait with film grain",
        "categories": ["cinematic", "romantic"],
    },
    {
        "id": "sultry_lounge_portrait",
        "title": "Amber Lounge Candid",
        "filename": "sultry_lounge_portrait.jpg",
        "icon": "🍸",
        "desc": "Warm amber cocktail lounge candid elegance",
        "categories": ["sexy", "cinematic", "romantic"],
    },
    {
        "id": "sultry_night_elegance",
        "title": "Night City Elegance",
        "filename": "sultry_night_elegance.jpg",
        "icon": "✨",
        "desc": "Midnight city lights black evening dress candid",
        "categories": ["cinematic", "sexy", "romantic"],
    },
    {
        "id": "candid_black_saree_mirror",
        "title": "Black Saree Mirror",
        "filename": "candid_black_saree_mirror.jpg",
        "icon": "🖤",
        "desc": "Moody black chiffon saree with ornate earrings",
        "categories": ["sexy", "romantic", "traditional"],
    },
    {
        "id": "candid_wine_saree_balcony",
        "title": "Wine Chiffon Balcony",
        "filename": "candid_wine_saree_balcony.jpg",
        "icon": "🍷",
        "desc": "Deep wine red saree overlooking twinkling evening skyline",
        "categories": ["sexy", "romantic", "cinematic"],
    },
    {
        "id": "candid_cozy_sweater_coffee",
        "title": "Cozy Knit Coffee Candid",
        "filename": "candid_cozy_sweater_coffee.jpg",
        "icon": "☕",
        "desc": "Oversized warm knit sweater holding ceramic coffee mug",
        "categories": ["romantic", "cinematic"],
    },
    {
        "id": "candid_golden_hour_saree",
        "title": "Golden Hour Organza Saree",
        "filename": "candid_golden_hour_saree.jpg",
        "icon": "🌅",
        "desc": "Warm mustard & marigold sheer saree in setting sunbeams",
        "categories": ["romantic", "traditional"],
    },
    {
        "id": "candid_neon_car_passenger",
        "title": "Midnight Neon Car Drive",
        "filename": "candid_neon_car_passenger.jpg",
        "icon": "🚗",
        "desc": "Passenger seat candid with reflections of city neon lights",
        "categories": ["cinematic", "romantic"],
    },
    {
        "id": "candid_rooftop_midnight_lights",
        "title": "Rooftop City Lights",
        "filename": "candid_rooftop_midnight_lights.jpg",
        "icon": "🌃",
        "desc": "Midnight rooftop silhouette overlooking illuminated skyline",
        "categories": ["cinematic", "sexy", "romantic"],
    },
    {
        "id": "candid_temple_silk_saree",
        "title": "Kanjeevaram Temple Saree",
        "filename": "candid_temple_silk_saree.jpg",
        "icon": "🛕",
        "desc": "Deep crimson Kanjeevaram silk saree with rich antique gold zari",
        "categories": ["traditional", "romantic"],
    },
    {
        "id": "candid_banarasi_diya_courtyard",
        "title": "Banarasi Diya Courtyard",
        "filename": "candid_banarasi_diya_courtyard.jpg",
        "icon": "🪔",
        "desc": "Royal emerald Banarasi silk by flickering brass oil lamps",
        "categories": ["traditional", "romantic", "cinematic"],
    },
    {
        "id": "pin_saree_portrait_1",
        "title": "Vintage Silk Portrait",
        "filename": "pin_saree_portrait_1.jpg",
        "icon": "👑",
        "desc": "Vintage portrait in handcrafted silk saree with delicate pallu",
        "categories": ["traditional", "cinematic", "romantic"],
    },
    {
        "id": "pin_saree_portrait_2",
        "title": "Golden Zari Candid",
        "filename": "pin_saree_portrait_2.jpg",
        "icon": "✨",
        "desc": "Warm sunlit portrait with shimmering golden zari borders",
        "categories": ["traditional", "romantic"],
    },
    {
        "id": "pin_desi_candid_3",
        "title": "Desi Courtyard Sunlight",
        "filename": "pin_desi_candid_3.jpg",
        "icon": "🌞",
        "desc": "Natural candid sunlit courtyard moment with traditional jhumkas",
        "categories": ["traditional", "romantic"],
    },
    {
        "id": "pin_aesthetic_bedroom_4",
        "title": "Fairylight Bedroom Candid",
        "filename": "pin_aesthetic_bedroom_4.jpg",
        "icon": "💫",
        "desc": "Warm bedroom ambient bokeh with delicate string fairylights",
        "categories": ["sexy", "romantic", "cinematic"],
    },
    {
        "id": "pin_saree_candid_5",
        "title": "Emerald Chiffon Mirror",
        "filename": "pin_saree_candid_5.jpg",
        "icon": "💚",
        "desc": "Forest green chiffon saree mirror selfie with natural waves",
        "categories": ["sexy", "traditional", "romantic"],
    },
    {
        "id": "pin_saree_candid_6",
        "title": "Ruby Velvet Evening Saree",
        "filename": "pin_saree_candid_6.jpg",
        "icon": "🌹",
        "desc": "Rich ruby velvet evening saree with modern sleeveless blouse",
        "categories": ["sexy", "romantic", "cinematic"],
    },
    {
        "id": "pin_sexy_01",
        "title": "Sensual Silk Studio",
        "filename": "pin_sexy_01.jpg",
        "icon": "🖤",
        "desc": "Deep sultry elegance with studio rim lighting",
        "categories": ["sexy", "romantic"],
    },
    {
        "id": "pin_sexy_02",
        "title": "Midnight Saree Poise",
        "filename": "pin_sexy_02.jpg",
        "icon": "🔥",
        "desc": "Chic contemporary saree selfie with subtle shadows",
        "categories": ["sexy", "cinematic"],
    },
    {
        "id": "pin_sexy_03",
        "title": "Velvet Romance Silhouette",
        "filename": "pin_sexy_03.jpg",
        "icon": "💋",
        "desc": "Intimate evening portrait with rich texture",
        "categories": ["sexy", "romantic"],
    },
    {
        "id": "pin_sexy_04",
        "title": "Modern Desi Charm",
        "filename": "pin_sexy_04.jpg",
        "icon": "🌹",
        "desc": "Backless designer blouse with confident posture",
        "categories": ["sexy", "traditional"],
    },
    {
        "id": "pin_sexy_05",
        "title": "Warm Glow Bedroom",
        "filename": "pin_sexy_05.jpg",
        "icon": "🌙",
        "desc": "Soft lamplight candid bedroom aesthetic",
        "categories": ["sexy", "romantic"],
    },
    {
        "id": "pin_sexy_06",
        "title": "Bold Chiffon Drape",
        "filename": "pin_sexy_06.jpg",
        "icon": "✨",
        "desc": "Flowing chiffon saree with sleek hair styling",
        "categories": ["sexy", "traditional"],
    },
    {
        "id": "pin_sexy_07",
        "title": "Urban Golden Hour",
        "filename": "pin_sexy_07.jpg",
        "icon": "🍷",
        "desc": "Sun-kissed city terrace candid golden hour",
        "categories": ["sexy", "cinematic"],
    },
    {
        "id": "pin_sexy_08",
        "title": "Crimson Satin Glow",
        "filename": "pin_sexy_08.jpg",
        "icon": "🖤",
        "desc": "Striking satin night aesthetic with moody backdrop",
        "categories": ["sexy", "romantic"],
    },
    {
        "id": "pin_sexy_09",
        "title": "Minimalist Black Look",
        "filename": "pin_sexy_09.jpg",
        "icon": "🔥",
        "desc": "Understated classy black sleeveless aesthetic",
        "categories": ["sexy", "cinematic"],
    },
    {
        "id": "pin_sexy_10",
        "title": "Mirror Reflection Mood",
        "filename": "pin_sexy_10.jpg",
        "icon": "💋",
        "desc": "Authentic smartphone mirror selfie with warm tone",
        "categories": ["sexy", "romantic"],
    },
    {
        "id": "pin_sexy_11",
        "title": "Emerald Saree Grace",
        "filename": "pin_sexy_11.jpg",
        "icon": "🌹",
        "desc": "Deep green saree with modern back design",
        "categories": ["sexy", "traditional"],
    },
    {
        "id": "pin_sexy_12",
        "title": "Sultry Balcony Breeze",
        "filename": "pin_sexy_12.jpg",
        "icon": "🌙",
        "desc": "Windblown hair and city skyline night bokeh",
        "categories": ["sexy", "cinematic"],
    },
    {
        "id": "pin_sexy_13",
        "title": "Smoky Eyes Portrait",
        "filename": "pin_sexy_13.jpg",
        "icon": "✨",
        "desc": "Expressive intense gaze with candid close-up",
        "categories": ["sexy", "romantic"],
    },
    {
        "id": "pin_sexy_14",
        "title": "Royal Maroon Saree",
        "filename": "pin_sexy_14.jpg",
        "icon": "🍷",
        "desc": "Rich wine drape with delicate golden borders",
        "categories": ["sexy", "traditional"],
    },
    {
        "id": "pin_sexy_15",
        "title": "Velvet Midnight Muse",
        "filename": "pin_sexy_15.jpg",
        "icon": "🔥",
        "desc": "Sensual midnight lighting with velvet allure",
        "categories": ["sexy", "cinematic"],
    },
    {
        "id": "pin_romantic_01",
        "title": "Soft Daylight Window",
        "filename": "pin_romantic_01.jpg",
        "icon": "💖",
        "desc": "Gentle morning window light with subtle smile",
        "categories": ["romantic", "cinematic"],
    },
    {
        "id": "pin_romantic_02",
        "title": "Dreamy Fairylight Glow",
        "filename": "pin_romantic_02.jpg",
        "icon": "🌸",
        "desc": "Soft string light bokeh with warm cozy aura",
        "categories": ["romantic", "sexy"],
    },
    {
        "id": "pin_romantic_03",
        "title": "Pastel Chiffon Breeze",
        "filename": "pin_romantic_03.jpg",
        "icon": "🤍",
        "desc": "Delicate pastel saree with romantic windswept hair",
        "categories": ["romantic", "traditional"],
    },
    {
        "id": "pin_romantic_04",
        "title": "Cafe Solitude Mood",
        "filename": "pin_romantic_04.jpg",
        "icon": "🥀",
        "desc": "Intimate quiet cafe corner candid with warm tea",
        "categories": ["romantic", "cinematic"],
    },
    {
        "id": "pin_romantic_05",
        "title": "Blush Pink Elegance",
        "filename": "pin_romantic_05.jpg",
        "icon": "🌙",
        "desc": "Soft blush tone outfit with dreamy soft focus",
        "categories": ["romantic", "sexy"],
    },
    {
        "id": "pin_romantic_06",
        "title": "Golden Dusk Terrace",
        "filename": "pin_romantic_06.jpg",
        "icon": "✨",
        "desc": "Warm dusk sunlight kissing gentle hair highlights",
        "categories": ["romantic", "cinematic"],
    },
    {
        "id": "pin_romantic_07",
        "title": "Vintage Romance Gaze",
        "filename": "pin_romantic_07.jpg",
        "icon": "💫",
        "desc": "Nostalgic film camera color profile and tender look",
        "categories": ["romantic", "traditional"],
    },
    {
        "id": "pin_romantic_08",
        "title": "Rainy Window Reflection",
        "filename": "pin_romantic_08.jpg",
        "icon": "🌷",
        "desc": "Melancholic romantic monsoon drizzle aesthetic",
        "categories": ["romantic", "cinematic"],
    },
    {
        "id": "pin_romantic_09",
        "title": "Lovers Whisper Portrait",
        "filename": "pin_romantic_09.jpg",
        "icon": "💌",
        "desc": "Quiet intimate close portrait with natural lighting",
        "categories": ["romantic", "sexy"],
    },
    {
        "id": "pin_romantic_10",
        "title": "Moonlit Balcony Calm",
        "filename": "pin_romantic_10.jpg",
        "icon": "🌹",
        "desc": "Cool night tones with warm ambient room spill",
        "categories": ["romantic", "cinematic"],
    },
    {
        "id": "pin_romantic_11",
        "title": "Floral Silk Tenderness",
        "filename": "pin_romantic_11.jpg",
        "icon": "🤍",
        "desc": "Dainty floral print saree with innocent charm",
        "categories": ["romantic", "traditional"],
    },
    {
        "id": "pin_romantic_12",
        "title": "Cozy Blanket Evening",
        "filename": "pin_romantic_12.jpg",
        "icon": "💖",
        "desc": "Warm indoor sweater aesthetic with soft candlelight",
        "categories": ["romantic", "sexy"],
    },
    {
        "id": "pin_romantic_13",
        "title": "Twilight Garden Walk",
        "filename": "pin_romantic_13.jpg",
        "icon": "🌸",
        "desc": "Peaceful twilight hues among gentle greenery",
        "categories": ["romantic", "cinematic"],
    },
    {
        "id": "pin_romantic_14",
        "title": "Timeless Musings",
        "filename": "pin_romantic_14.jpg",
        "icon": "🌙",
        "desc": "Thoughtful candid gaze holding delicate dupatta",
        "categories": ["romantic", "traditional"],
    },
    {
        "id": "pin_romantic_15",
        "title": "Soft Heartstrings",
        "filename": "pin_romantic_15.jpg",
        "icon": "🥀",
        "desc": "Authentic warm smile illuminated by gentle sunset",
        "categories": ["romantic", "cinematic"],
    },
    {
        "id": "pin_cinematic_01",
        "title": "Neon Rain Odyssey",
        "filename": "pin_cinematic_01.jpg",
        "icon": "🎬",
        "desc": "Cyber-moody teal and magenta street reflections",
        "categories": ["cinematic", "sexy"],
    },
    {
        "id": "pin_cinematic_02",
        "title": "Cab Window Bokeh",
        "filename": "pin_cinematic_02.jpg",
        "icon": "🌃",
        "desc": "Passing city streetlight streaks through car glass",
        "categories": ["cinematic", "romantic"],
    },
    {
        "id": "pin_cinematic_03",
        "title": "Vintage 35mm Grain",
        "filename": "pin_cinematic_03.jpg",
        "icon": "⚡",
        "desc": "Authentic Kodak film aesthetic with deep shadows",
        "categories": ["cinematic", "traditional"],
    },
    {
        "id": "pin_cinematic_04",
        "title": "Rooftop Midnight Smoke",
        "filename": "pin_cinematic_04.jpg",
        "icon": "🍸",
        "desc": "Dramatic city horizon with cold cinematic rim light",
        "categories": ["cinematic", "sexy"],
    },
    {
        "id": "pin_cinematic_05",
        "title": "Amber Lounge Noir",
        "filename": "pin_cinematic_05.jpg",
        "icon": "🌆",
        "desc": "Speakeasy golden amber bar ambience with silhouette",
        "categories": ["cinematic", "romantic"],
    },
    {
        "id": "pin_cinematic_06",
        "title": "Metro Station Solitude",
        "filename": "pin_cinematic_06.jpg",
        "icon": "🌙",
        "desc": "High-contrast architectural framing with transit lights",
        "categories": ["cinematic", "sexy"],
    },
    {
        "id": "pin_cinematic_07",
        "title": "Teal and Orange Sunset",
        "filename": "pin_cinematic_07.jpg",
        "icon": "🎥",
        "desc": "Vibrant blockbuster color grading on city bridge",
        "categories": ["cinematic", "romantic"],
    },
    {
        "id": "pin_cinematic_08",
        "title": "Dark Velvet Mystery",
        "filename": "pin_cinematic_08.jpg",
        "icon": "🖤",
        "desc": "Moody low-key illumination with captivating eyes",
        "categories": ["cinematic", "sexy"],
    },
    {
        "id": "pin_cinematic_09",
        "title": "Monsoon Street Glare",
        "filename": "pin_cinematic_09.jpg",
        "icon": "🍷",
        "desc": "Wet asphalt reflections and misty urban headlights",
        "categories": ["cinematic", "romantic"],
    },
    {
        "id": "pin_cinematic_10",
        "title": "Neon Sign Reflections",
        "filename": "pin_cinematic_10.jpg",
        "icon": "🌟",
        "desc": "Vivid neon signage cast across candid profile",
        "categories": ["cinematic", "sexy"],
    },
    {
        "id": "pin_cinematic_11",
        "title": "Film Noir Monochrome",
        "filename": "pin_cinematic_11.jpg",
        "icon": "🏙️",
        "desc": "Expressive monochrome contrast with dramatic chiaroscuro",
        "categories": ["cinematic", "traditional"],
    },
    {
        "id": "pin_cinematic_12",
        "title": "Golden Skyline Vista",
        "filename": "pin_cinematic_12.jpg",
        "icon": "🌌",
        "desc": "Panoramic evening metropolis backdrop in sharp focus",
        "categories": ["cinematic", "romantic"],
    },
    {
        "id": "pin_cinematic_13",
        "title": "Subway Drift Portrait",
        "filename": "pin_cinematic_13.jpg",
        "icon": "🎭",
        "desc": "Motion-blurred subway train behind still portrait",
        "categories": ["cinematic", "sexy"],
    },
    {
        "id": "pin_cinematic_14",
        "title": "Late Night Diner Light",
        "filename": "pin_cinematic_14.jpg",
        "icon": "💫",
        "desc": "Warm vintage diner neon through misty windowpane",
        "categories": ["cinematic", "romantic"],
    },
    {
        "id": "pin_cinematic_15",
        "title": "Shadow and Starlight",
        "filename": "pin_cinematic_15.jpg",
        "icon": "💎",
        "desc": "Dramatic hard rim light against pitch black midnight",
        "categories": ["cinematic", "sexy"],
    },
    {
        "id": "pin_traditional_01",
        "title": "Banarasi Gold Heritage",
        "filename": "pin_traditional_01.jpg",
        "icon": "👑",
        "desc": "Regal red Banarasi silk saree with authentic gold zari",
        "categories": ["traditional", "romantic"],
    },
    {
        "id": "pin_traditional_02",
        "title": "Temple Bells and Silk",
        "filename": "pin_traditional_02.jpg",
        "icon": "🪔",
        "desc": "Classic Kanjeevaram silk drape in sacred temple pillars",
        "categories": ["traditional", "cinematic"],
    },
    {
        "id": "pin_traditional_03",
        "title": "Diwali Diya Glow",
        "filename": "pin_traditional_03.jpg",
        "icon": "🌸",
        "desc": "Warm clay oil lamp light reflecting on jhumkas",
        "categories": ["traditional", "romantic"],
    },
    {
        "id": "pin_traditional_04",
        "title": "Courtyard Mehndi Pose",
        "filename": "pin_traditional_04.jpg",
        "icon": "🥻",
        "desc": "Intricate henna hands with traditional marigold yellow saree",
        "categories": ["traditional", "romantic"],
    },
    {
        "id": "pin_traditional_05",
        "title": "Royal Emerald Paithani",
        "filename": "pin_traditional_05.jpg",
        "icon": "🌺",
        "desc": "Maharashtra royal silk border with graceful pallu drape",
        "categories": ["traditional", "sexy"],
    },
    {
        "id": "pin_traditional_06",
        "title": "Jhumka Swag Portrait",
        "filename": "pin_traditional_06.jpg",
        "icon": "✨",
        "desc": "Heavy antique oxidized earrings catching golden afternoon rays",
        "categories": ["traditional", "romantic"],
    },
    {
        "id": "pin_traditional_07",
        "title": "Haveli Arch Royalty",
        "filename": "pin_traditional_07.jpg",
        "icon": "📿",
        "desc": "Vintage sandstone archway framing heritage royal posture",
        "categories": ["traditional", "cinematic"],
    },
    {
        "id": "pin_traditional_08",
        "title": "Sunset Ghagra Choli",
        "filename": "pin_traditional_08.jpg",
        "icon": "🧡",
        "desc": "Vibrant mirrorwork embroidery spinning in golden sunset",
        "categories": ["traditional", "romantic"],
    },
    {
        "id": "pin_traditional_09",
        "title": "Bindi and Kohl Gaze",
        "filename": "pin_traditional_09.jpg",
        "icon": "💫",
        "desc": "Classic Indian beauty with dark kohl eyes and crimson bindi",
        "categories": ["traditional", "sexy"],
    },
    {
        "id": "pin_traditional_10",
        "title": "Marigold Festivity",
        "filename": "pin_traditional_10.jpg",
        "icon": "🏮",
        "desc": "Fresh floral garlands decorating historic stone patio",
        "categories": ["traditional", "romantic"],
    },
    {
        "id": "pin_traditional_11",
        "title": "Chikankari White Charm",
        "filename": "pin_traditional_11.jpg",
        "icon": "🌼",
        "desc": "Intricate Lucknowi hand-embroidery in pristine ivory",
        "categories": ["traditional", "cinematic"],
    },
    {
        "id": "pin_traditional_12",
        "title": "Silk Dupatta Flutter",
        "filename": "pin_traditional_12.jpg",
        "icon": "🌟",
        "desc": "Breezy zari-bordered dupatta dancing in evening terrace wind",
        "categories": ["traditional", "romantic"],
    },
    {
        "id": "pin_traditional_13",
        "title": "Gotta Patti Splendor",
        "filename": "pin_traditional_13.jpg",
        "icon": "👑",
        "desc": "Rajasthani festive attire with radiant pink and gold trims",
        "categories": ["traditional", "sexy"],
    },
    {
        "id": "pin_traditional_14",
        "title": "Brass Urli Reflections",
        "filename": "pin_traditional_14.jpg",
        "icon": "🪔",
        "desc": "Floating rose petals and candles around traditional brass vessel",
        "categories": ["traditional", "romantic"],
    },
    {
        "id": "pin_traditional_15",
        "title": "Timeless Desi Poise",
        "filename": "pin_traditional_15.jpg",
        "icon": "🥻",
        "desc": "Authentic timeless Indian grace with folded hands or serene glance",
        "categories": ["traditional", "cinematic"],
    },
]

# Curated Viral Lyrical Hindi/Hinglish Hooks & Quotes categorized across 8 vibes
ALL_HOOK_OPTIONS: List[Dict[str, Any]] = [
    # AryaFeed Viral News, Trending & Cultural Hooks
    {'id': 'h_news_1', 'text': '22 FRIENDS STUDIED TOGETHER, *21 CRACKED* THE EXAM 🥹🎓', 'categories': ['news']},
    {'id': 'h_news_2', 'text': 'TEA VENDOR\'S DAUGHTER CRACKS *UPSC EXAM* IN FIRST ATTEMPT 🇮🇳✨', 'categories': ['news']},
    {'id': 'h_news_3', 'text': 'SWIGGY DELIVERY GUY RETURNS *₹15 LAKH CASH* LEFT IN CAB 👏🛵', 'categories': ['news']},
    {'id': 'h_news_4', 'text': 'MAN BUYS OLD SCOOTER FOR ₹20,000, FINDS *₹50 LAKH GOLD* HIDDEN 🤯🪙', 'categories': ['news']},
    {'id': 'h_news_5', 'text': 'INDIA WINS *HISTORIC GOLD* AFTER 48 YEARS, STADIUM TEARS UP 🇮🇳🏆', 'categories': ['news']},
    {'id': 'h_news_6', 'text': 'VIRAL CCTV: BOY RISKS LIFE TO SAVE STREET DOG FROM *SPEEDING TRUCK* 🐶💔', 'categories': ['news']},
    {'id': 'h_news_7', 'text': 'FATHER WORKED AS LABOURER FOR 25 YEARS TO MAKE SON *IPS OFFICER* 🫡🇮🇳', 'categories': ['news']},
    {'id': 'h_news_8', 'text': 'VIRAL: CRICKETER SCORES CENTURY ON HIS *MOTHER\'S BIRTHDAY* 🏏❤️', 'categories': ['news']},
    {'id': 'h_sex_1', 'text': 'hume dekh kar muskurana aapki aadat hai ya niyat? 💋', 'categories': ['sexy']},
    {'id': 'h_sex_2', 'text': 'teri ek jhalak hi kafi hai madhosh karne ke liye... 🔥', 'categories': ['sexy']},
    {'id': 'h_sex_3', 'text': 'itni haseen ho ki nazar hatana gunah lagta hai... 💋', 'categories': ['sexy']},
    {'id': 'h_sex_4', 'text': 'thodi si ziddi, thodi si shaitaan, par jaan se zyada pyari... 🖤', 'categories': ['sexy']},
    {'id': 'h_sex_5', 'text': 'nazar milte hi dil dhadakne lage toh samajh lo kissa shuru... 💋', 'categories': ['sexy']},
    {'id': 'h_sex_6', 'text': 'bold, beautiful, and unapologetically *desi* 🔥', 'categories': ['sexy']},
    {'id': 'h_sex_7', 'text': 'nasha aankhon mein hai, log bewajah sharab ko badnaam karte hain... 🍷', 'categories': ['sexy']},
    {'id': 'h_sex_8', 'text': 'husn ka kya kaam saadgi ke aage, par unki ada ne maar daala... 💋', 'categories': ['sexy']},
    {'id': 'h_sex_9', 'text': 'teri *nigahein* sidha dil par teer chalati hain... 🖤', 'categories': ['sexy']},
    {'id': 'h_sex_10', 'text': 'dil sambhal kar rakhna, humari ek muskurahat hi kafi hai... 🔥', 'categories': ['sexy']},
    {'id': 'h_sex_11', 'text': 'itna mat dekho hume, kahin ishq na ho jaaye... 💋', 'categories': ['sexy']},
    {'id': 'h_sex_12', 'text': 'aankhon se shuru hui thi baat, ab baat rooh tak pahunch chuki hai... 🖤', 'categories': ['sexy']},
    {'id': 'h_sex_13', 'text': 'unhe laga saree mein masoom lagungi, unhe kya pata aag pallu mein hai... 💋🔥', 'categories': ['sexy']},
    {'id': 'h_sex_14', 'text': 'ek toh ye kali saree, upar se tumhari ye nigahein... bachna mushkil hai 🖤✨', 'categories': ['sexy']},
    {'id': 'h_sex_15', 'text': 'saree pehnu ya western, tera dhyan toh bas ek hi jagah rukna hai 🙈🔥', 'categories': ['sexy']},
    {'id': 'h_sex_16', 'text': 'kabhi fursat mein aana, dikhaungi sharafat ke piche kya chhipa hai 💋', 'categories': ['sexy']},
    {'id': 'h_sex_17', 'text': 'raat ke 2 baje tumhara khayal aur ye thandi hawa... mood kharab kar rahi hai 🌚💋', 'categories': ['sexy']},
    {'id': 'h_sex_18', 'text': 'don\'t look at my lips while I\'m talking, warna baat adhoori reh jayegi 💋✨', 'categories': ['sexy']},
    {'id': 'h_sex_19', 'text': 'jitna tum innocent bante ho na, utne hi khatarnaak tumhare iraade hain 🔥', 'categories': ['sexy']},
    {'id': 'h_sex_20', 'text': 'bas ek baar pyaar se pakad lo, saari zidd ek second mein pighal jayegi 🖤', 'categories': ['sexy']},
    {'id': 'h_sex_21', 'text': 'late night mirror selfie sirf isliye, taaki tumhari neend thodi aur udd sake 💋', 'categories': ['sexy']},
    {'id': 'h_sex_22', 'text': 'zulfein bandh ke rakhu ya kholi chhod du? batao kis mein hosh khone ka irada hai 💋✨', 'categories': ['sexy']},
    {'id': 'h_sex_23', 'text': 'teri ek nazar kafi hai mere dil ka thermostat badhane ke liye 🔥🙈', 'categories': ['sexy']},
    {'id': 'h_sex_24', 'text': 'raat ko itni der tak jaagte ho, kaho toh neend udane ka koi solid bahana ban jau? 🌚💋', 'categories': ['sexy']},
    {'id': 'h_sex_25', 'text': 'seedha bolo na ki meri kamar ke til pe dil aa gaya hai, ye sharmaane ka natak kyu? 🔥', 'categories': ['sexy']},
    {'id': 'h_sex_26', 'text': 'tumhe lagta hai main ignore kar rahi hoon? main toh bas dekh rahi hoon kab tak tadap sakte ho 💋✨', 'categories': ['sexy']},
    {'id': 'h_sex_27', 'text': 'itna sweet ban ke mat dekho, sugar nahi seedha addiction ho jayega 🌚💋', 'categories': ['sexy']},
    {'id': 'h_sex_28', 'text': 'one late night ride with you, and zero promises for what happens in the car 🙈🔥', 'categories': ['sexy']},
    {'id': 'h_sex_29', 'text': 'saree ka pallu sambhalu ya tumhare irade? dono hi haath se nikalte ja rahe hain 💋🔥', 'categories': ['sexy']},
    {'id': 'h_sex_30', 'text': 'you\'re cute, but I bet you\'d look better under my bad influence 💋✨', 'categories': ['sexy']},
    {'id': 'h_sex_31', 'text': 'thoda aur paas aao... kuch aisi baat kehni hai jo hawa bhi na sun sake 🖤🔥', 'categories': ['sexy']},
    {'id': 'h_sex_32', 'text': 'meri aankhon mein dekh kar baat karo, floor par dekhne se control nahi aayega 💋🙈', 'categories': ['sexy']},
    {'id': 'h_sex_33', 'text': 'aankhein band karo aur socho: main, tum aur ek band kamra... ab bolo neend aayegi? 🔥', 'categories': ['sexy']},
    {'id': 'h_sex_34', 'text': 'flirt back karne ki galti mat karna, aadat lag gayi toh chhutti nahi milegi 🌚💋', 'categories': ['sexy']},
    {'id': 'h_sex_35', 'text': 'kaash tum yaha hote, meri nightdress ka ribbon tumse hi bandhwati 💋✨', 'categories': ['sexy']},
    {'id': 'h_sex_36', 'text': 'they told me to dress my age, so I wore a backless blouse and raised the temperature 🔥', 'categories': ['sexy']},
    {'id': 'h_sex_37', 'text': 'aadha pagal toh teri muskaan ne kiya tha, baaki ka kaam ye late night texts kar rahe hain 💋', 'categories': ['sexy']},
    {'id': 'h_sex_38', 'text': 'maine flirt back kardiya na to ladle tu subah tak so nahi payega 🔥', 'categories': ['sexy']},
    {'id': 'h_sex_39', 'text': 'hum toh chup chap baithte hain, par ye nigahein gustakhi kar hi jaati hain 💋', 'categories': ['sexy']},
    {'id': 'h_sex_40', 'text': 'teri baatein itni meethi hain ki har dafa niyat fisal jaati hai 🖤✨', 'categories': ['sexy']},
    {'id': 'h_bad_1', 'text': 'main khud apni *favorite* hoon, kisi aur ki validation ki zaroorat nahi 💅✨', 'categories': ['baddie']},
    {'id': 'h_bad_2', 'text': 'too *pretty* to be stressing over anybody 💋', 'categories': ['baddie']},
    {'id': 'h_bad_3', 'text': 'hot girls don\'t chase, they get chased 🔥', 'categories': ['baddie']},
    {'id': 'h_bad_4', 'text': 'not everyone\'s cup of tea, I\'m expensive *champagne* 🥂', 'categories': ['baddie']},
    {'id': 'h_bad_5', 'text': 'tera *standard* match karne ke liye hume drop hona padega darling 💅', 'categories': ['baddie']},
    {'id': 'h_bad_6', 'text': 'she looked like art, but walked like a *storm* 🔥', 'categories': ['baddie']},
    {'id': 'h_bad_7', 'text': 'cutie with a little bit of *savage* 💋', 'categories': ['baddie']},
    {'id': 'h_bad_8', 'text': 'unbothered, moisturized, in my own lane 💅✨', 'categories': ['baddie']},
    {'id': 'h_bad_9', 'text': 'my *vibe* is rare, handle with care 🖤', 'categories': ['baddie']},
    {'id': 'h_bad_10', 'text': 'they stare because they can\'t afford me 🔥', 'categories': ['baddie']},
    {'id': 'h_bad_11', 'text': 'pretty face, killer *attitude* 💋', 'categories': ['baddie']},
    {'id': 'h_bad_12', 'text': 'born to stand out, never to fit in 💎', 'categories': ['baddie']},
    {'id': 'h_bad_13', 'text': 'she got that quiet confidence that screams loud 🔥', 'categories': ['baddie']},
    {'id': 'h_bad_14', 'text': 'hume dekh kar ignore karna toh namumkin hai darling 💋', 'categories': ['baddie']},
    {'id': 'h_bad_15', 'text': 'sweet as sugar, cold as ice, hurt me once, I\'ll break you twice 🖤', 'categories': ['baddie']},
    {'id': 'h_bad_16', 'text': 'expensive taste, dangerous mind 🔥', 'categories': ['baddie']},
    {'id': 'h_bad_17', 'text': 'apna *standard* itna high hai ki log bas dekhte reh jaate hain 💅', 'categories': ['baddie']},
    {'id': 'h_bad_18', 'text': 'confidence level: selfie with zero filter ✨', 'categories': ['baddie']},
    {'id': 'h_bad_19', 'text': 'sabki pasand banne ka shauk nahi, hum khud ke liye kaafi hain 👑', 'categories': ['baddie']},
    {'id': 'h_bad_20', 'text': 'pretty in picture, deadly in person 💋', 'categories': ['baddie']},
    {'id': 'h_bad_21', 'text': 'mirror selfies hit different when you know you\'re the *prize* 🪞✨', 'categories': ['baddie']},
    {'id': 'h_bad_22', 'text': 'i am my own biggest *crush* 💋✨', 'categories': ['baddie']},
    {'id': 'h_bad_23', 'text': 'making heads turn without even trying 🔥', 'categories': ['baddie']},
    {'id': 'h_bad_24', 'text': 'too glam to give a damn 💅', 'categories': ['baddie']},
    {'id': 'h_bad_25', 'text': 'you couldn\'t handle me even if I came with instructions 💋', 'categories': ['baddie']},
    {'id': 'h_bad_26', 'text': 'main replacement nahi, benchmark hoon darling 💅👑', 'categories': ['baddie']},
    {'id': 'h_bad_27', 'text': 'attitude unko dikhati hoon jinhe tameez samajh nahi aati 🔥', 'categories': ['baddie']},
    {'id': 'h_bad_28', 'text': 'my circle is small because I\'m into quality, not quantity 🖤', 'categories': ['baddie']},
    {'id': 'h_bad_29', 'text': 'apni kahani ki villain bhi main hoon aur rani bhi 👑✨', 'categories': ['baddie']},
    {'id': 'h_bad_30', 'text': 'dil jeetna mere bas ka nahi, aukaat dikhana mera roz ka kaam hai 💅', 'categories': ['baddie']},
    {'id': 'h_bad_31', 'text': 'they talk about me because if they spoke about themselves nobody would listen 💋', 'categories': ['baddie']},
    {'id': 'h_bad_32', 'text': 'pehle khud ko mere layak bana, fir aake baat kar 🔥', 'categories': ['baddie']},
    {'id': 'h_bad_33', 'text': 'beauty with brains, lethal combination 💎✨', 'categories': ['baddie']},
    {'id': 'h_bad_34', 'text': 'silence is my attitude when words are too cheap for them 🖤', 'categories': ['baddie']},
    {'id': 'h_bad_35', 'text': 'I don\'t need a king to be a queen 👑💅', 'categories': ['baddie']},
    {'id': 'h_bad_36', 'text': 'apna khauf itna hi kaafi hai ki log naam sun kar rasta badal lete hain 🔥', 'categories': ['baddie']},
    {'id': 'h_bad_37', 'text': 'I know who I am, your opinion is not required 💋', 'categories': ['baddie']},
    {'id': 'h_bad_38', 'text': 'a smart girl knows her limits, a baddie knows she has none 💅✨', 'categories': ['baddie']},
    {'id': 'h_bad_39', 'text': 'I\'m the girl you\'ll never be able to forget 🖤🔥', 'categories': ['baddie']},
    {'id': 'h_bad_40', 'text': 'classy, sassy, and a bit bad-assy 💅💋', 'categories': ['baddie']},
    {'id': 'h_bes_1', 'text': 'nazar na lage meri cute *bestie* ko 🧿✨', 'categories': ['bestie']},
    {'id': 'h_bes_2', 'text': 'meri jaan, meri *crime* partner, meri forever bestie 👯‍♀️❤️', 'categories': ['bestie']},
    {'id': 'h_bes_3', 'text': 'us: 99% *drama*, 1% innocent, 100% unbreakable 👯‍♀️', 'categories': ['bestie']},
    {'id': 'h_bes_4', 'text': 'duniya ek taraf, meri *bestie* ek taraf 🧿👑', 'categories': ['bestie']},
    {'id': 'h_bes_5', 'text': 'tera mera *rishta* kuch aisa hai, bina bole sab samajh aana 🤍', 'categories': ['bestie']},
    {'id': 'h_bes_6', 'text': 'bestie *goals*: finding someone just as unhinged as me 💖', 'categories': ['bestie']},
    {'id': 'h_bes_7', 'text': 'bhagwan ne shakal cute di hai, aur *bestie* thodi pagal 🤪', 'categories': ['bestie']},
    {'id': 'h_bes_8', 'text': 'you\'re the *sister* I got to choose 👯‍♀️💕', 'categories': ['bestie']},
    {'id': 'h_bes_9', 'text': 'humesha sath rehna meri pagal *bestie*, tere bina sab boring hai 🌸', 'categories': ['bestie']},
    {'id': 'h_bes_10', 'text': 'partners in *crime* and late night gossip 🥂✨', 'categories': ['bestie']},
    {'id': 'h_bes_11', 'text': 'tere jaisi pagal *bestie* sabko mile, par meri wali sirf meri hai 🧿❤️', 'categories': ['bestie']},
    {'id': 'h_bes_12', 'text': 'two pretty best *friends* making memories everywhere 👯‍♀️', 'categories': ['bestie']},
    {'id': 'h_bes_13', 'text': 'she knows all my secrets and still *loves* me 🤍', 'categories': ['bestie']},
    {'id': 'h_bes_14', 'text': 'bestie ke sath *drama* bhi aesthetic lagta hai 💅✨', 'categories': ['bestie']},
    {'id': 'h_bes_15', 'text': 'real *queens* fix each other\'s crowns 👑✨', 'categories': ['bestie']},
    {'id': 'h_bes_16', 'text': 'forever grateful for a *bestie* like you 🧿💫', 'categories': ['bestie']},
    {'id': 'h_bes_17', 'text': 'main aur meri bestie: maximum *chaos*, pure love 👯‍♀️🔥', 'categories': ['bestie']},
    {'id': 'h_bes_18', 'text': 'humaari *dosti* par kisi ki nazar na lage 🧿❤️', 'categories': ['bestie']},
    {'id': 'h_bes_19', 'text': 'life was meant for best *friends* and good adventures 🥂✨', 'categories': ['bestie']},
    {'id': 'h_bes_20', 'text': 'tera mera sath janam janam ka hai *bestie* 💖', 'categories': ['bestie']},
    {'id': 'h_bes_21', 'text': 'bestie ko phone lagana is cheaper than therapy 👯‍♀️✨', 'categories': ['bestie']},
    {'id': 'h_bes_22', 'text': 'hum dono mil jayein toh mohalla hosh kho deta hai 🤪🔥', 'categories': ['bestie']},
    {'id': 'h_bes_23', 'text': 'meri har stupid harkat ki sabse badi supporter meri bestie hai 🤍', 'categories': ['bestie']},
    {'id': 'h_bes_24', 'text': 'ek bestie hi hai jo bina filter ke sach bol sakti hai 💅👯‍♀️', 'categories': ['bestie']},
    {'id': 'h_bes_25', 'text': 'dosti aisi honi chahiye ki teesre insaan ko jalan ho jaye 🧿✨', 'categories': ['bestie']},
    {'id': 'h_bes_26', 'text': 'teri shaadi mein sabse zyada hungama main hi machaungi bestie 🥂💃', 'categories': ['bestie']},
    {'id': 'h_bes_27', 'text': 'humari dosti koi dosti nahi, biological sisterhood hai ❤️', 'categories': ['bestie']},
    {'id': 'h_bes_28', 'text': 'bestie ke sath 2 minute ki baat poore din ka stress gayab kar deti hai 🌸', 'categories': ['bestie']},
    {'id': 'h_bes_29', 'text': 'hum dono jab sath hote hain, common sense offline chali jaati hai 🤪✨', 'categories': ['bestie']},
    {'id': 'h_bes_30', 'text': 'duniya chhod sakti hoon, par bestie ki chugli session nahi 👯‍♀️🍵', 'categories': ['bestie']},
    {'id': 'h_bes_31', 'text': 'teri meri dosti ka koi expiration date nahi hai 💖', 'categories': ['bestie']},
    {'id': 'h_bes_32', 'text': 'bestie ke bina photo shoot adhoora lagta hai 📸✨', 'categories': ['bestie']},
    {'id': 'h_bes_33', 'text': 'jis din hum dono serious ho gaye, us din chamatkar ho jayega 😂', 'categories': ['bestie']},
    {'id': 'h_bes_34', 'text': 'tum meri safe place ho bestie, chahe kitna bhi andhera ho 🤍🕊️', 'categories': ['bestie']},
    {'id': 'h_bes_35', 'text': 'meri khushi mein mujhse zyada khush hone wali meri bestie hai 🧿❤️', 'categories': ['bestie']},
    {'id': 'h_bes_36', 'text': 'teri kharab aadat bhi mujhe pyari lagti hai bestie 👯‍♀️💕', 'categories': ['bestie']},
    {'id': 'h_bes_37', 'text': 'ek achhi dost kismat se milti hai, aur tu toh lottery hai 💎✨', 'categories': ['bestie']},
    {'id': 'h_bes_38', 'text': 'god made us best friends because no mother could handle us as sisters 👯‍♀️🔥', 'categories': ['bestie']},
    {'id': 'h_bes_39', 'text': 'har mushkil aasan lagti hai jab tu sath hoti hai bestie 🌸🤍', 'categories': ['bestie']},
    {'id': 'h_bes_40', 'text': 'forever and always, tu meri number one person hai 🧿👑', 'categories': ['bestie']},
    {'id': 'h_rom_1', 'text': 'teri *aankhon* mein doob jane ka mann karta hai... 🖤', 'categories': ['romantic']},
    {'id': 'h_rom_2', 'text': 'kuch log *dil* mein aise bas jaate hain ki unke baad koi accha nahi lagta... 🥀', 'categories': ['romantic']},
    {'id': 'h_rom_3', 'text': 'tum paas nahi ho, fir bhi sabse *kareeb* ho... ✨', 'categories': ['romantic']},
    {'id': 'h_rom_4', 'text': 'ek tera *deedar* hi kaafi hai mere poore din ko haseen banane ke liye... 💖', 'categories': ['romantic']},
    {'id': 'h_rom_5', 'text': 'tere bina ab sham nahi dhaltee, har lamha sirf tera hi *intezaar* hai... 🌙', 'categories': ['romantic']},
    {'id': 'h_rom_6', 'text': 'kisi ko chaho toh is qadar chaho ki koi aur *chahat* na rahe... 🌹', 'categories': ['romantic']},
    {'id': 'h_rom_7', 'text': 'meri har subah tere khayal se aur har raat teri *yaadon* se mukammal hoti hai... 💫', 'categories': ['romantic']},
    {'id': 'h_rom_8', 'text': 'tujhse milne ke baad samjh aaya ki *sukoon* kise kehte hain... 🤍', 'categories': ['romantic']},
    {'id': 'h_rom_9', 'text': 'tumhe dekhne ke baad kisi aur ko dekhne ki zaroorat nahi mehsoos hoti... 💋', 'categories': ['romantic']},
    {'id': 'h_rom_10', 'text': '*dil* ka sukoon ho tum, jiske bina sab adhoora lagta hai... 🌸', 'categories': ['romantic']},
    {'id': 'h_rom_11', 'text': 'tere saath beeta har lamha kisi *khwab* jaisa haseen lagta hai... 🕊️', 'categories': ['romantic']},
    {'id': 'h_rom_12', 'text': '*ishq* wahi jo aankhon se shuru ho aur rooh mein utar jaaye... 🖤', 'categories': ['romantic']},
    {'id': 'h_rom_13', 'text': 'tum mil gaye toh jaise saari *duniya* mil gayi... 💖', 'categories': ['romantic']},
    {'id': 'h_rom_14', 'text': 'hamesha saath rehna, kyunki tumhare bina mera koi *wajood* nahi... 🕊️', 'categories': ['romantic']},
    {'id': 'h_rom_15', 'text': '*mohabbat* lafzon ki mohtaj nahi hoti, bas do dilon ka ehsaas kaafi hai... 💌', 'categories': ['romantic']},
    {'id': 'h_rom_16', 'text': 'tum sirf meri aadat nahi, meri ibadat ban chuke ho 🤍✨', 'categories': ['romantic']},
    {'id': 'h_rom_17', 'text': 'tere haathon mein mera haath ho, aur waqt wahi thehar jaaye 🕊️💖', 'categories': ['romantic']},
    {'id': 'h_rom_18', 'text': 'kitna ajeeb hai na, hazaron chehron mein sirf tera hi chehra dikhta hai 🌸', 'categories': ['romantic']},
    {'id': 'h_rom_19', 'text': 'tera naam sunte hi dil ka muskurana, ishq nahi toh aur kya hai? 💌', 'categories': ['romantic']},
    {'id': 'h_rom_20', 'text': 'kash hum dono kisi aisi duniya mein hote jahan sirf tum aur main hote 🌙🤍', 'categories': ['romantic']},
    {'id': 'h_rom_21', 'text': 'har dua mein sirf tera naam maanga hai, khuda se bhi pehle 🥀', 'categories': ['romantic']},
    {'id': 'h_rom_22', 'text': 'tera ehsaas itna gehra hai ki faasle bhi be-asar lagte hain ✨', 'categories': ['romantic']},
    {'id': 'h_rom_23', 'text': 'teri ek hasi par hum apni poori zindagi waar dein 💖', 'categories': ['romantic']},
    {'id': 'h_rom_24', 'text': 'tumhe paane ki chahat nahi, bas tumhe khush dekhne ki zid hai 🤍', 'categories': ['romantic']},
    {'id': 'h_rom_25', 'text': 'jo sukoon tere kandhe par sar rakh kar milta hai, wo kahi nahi 🕊️✨', 'categories': ['romantic']},
    {'id': 'h_rom_26', 'text': 'pyaar shabdon ka mohtaj nahi, teri aankhon ki nami sab keh deti hai 🥀', 'categories': ['romantic']},
    {'id': 'h_rom_27', 'text': 'tujhe chaha hai maine apni har saans se zyada 💖', 'categories': ['romantic']},
    {'id': 'h_rom_28', 'text': 'tum mere wo khwab ho jo main jaagte huye dekhna chahta hoon 🌙✨', 'categories': ['romantic']},
    {'id': 'h_rom_29', 'text': 'dil karta hai saari umar teri nigaahon ke pehre mein guzaar du 🤍', 'categories': ['romantic']},
    {'id': 'h_rom_30', 'text': 'tera saath hona hi mere har zakhm ka marham hai 🌸', 'categories': ['romantic']},
    {'id': 'h_rom_31', 'text': 'tere bina ye dil kisi bhi bheed mein akela mehsoos karta hai 🥀', 'categories': ['romantic']},
    {'id': 'h_rom_32', 'text': 'ishq mein har shart harkar bhi jo jeet lage, wo tum ho 💖', 'categories': ['romantic']},
    {'id': 'h_rom_33', 'text': 'teri ek jhalak ke liye ghanto dua maangi hai 🕊️', 'categories': ['romantic']},
    {'id': 'h_rom_34', 'text': 'kash ye raat kabhi khatam na ho aur hum baatein karte rahein 🌙✨', 'categories': ['romantic']},
    {'id': 'h_rom_35', 'text': 'tum meri zindagi ka sabse khoobsurat ittefaq ho 🤍', 'categories': ['romantic']},
    {'id': 'h_rom_36', 'text': 'teri muskurahat mere dil ki thakan mita deti hai 🌸💖', 'categories': ['romantic']},
    {'id': 'h_rom_37', 'text': 'main aur tum jab ek hote hain, toh khuda bhi muskurata hoga 🕊️', 'categories': ['romantic']},
    {'id': 'h_rom_38', 'text': 'mohabbat agar ibadat hai toh mera har sajda tere naam hai 🥀', 'categories': ['romantic']},
    {'id': 'h_rom_39', 'text': 'tere bina ye dil kisi soone aangan jaisa ban jata hai 🌙', 'categories': ['romantic']},
    {'id': 'h_rom_40', 'text': 'zindagi ka sabse meetha nasha sirf tumhara khayal hai 💖✨', 'categories': ['romantic']},
    {'id': 'h_cin_1', 'text': 'kuch baatein lafzon se nahi, bas ek nazar dekh kar bayaan ho jaati hain... 👁️', 'categories': ['cinematic']},
    {'id': 'h_cin_2', 'text': 'ab toh aadat si ho gayi hai har waqt tera *khayal* aane ki... 🥀', 'categories': ['cinematic']},
    {'id': 'h_cin_3', 'text': 'duniya ke liye tum ek shakhs ho sakte ho, par kisi ke liye poori duniya ho... 🌍', 'categories': ['cinematic']},
    {'id': 'h_cin_4', 'text': 'kuch kahaniyaan adhoori reh kar bhi sabse *khoobsurat* hoti hain... 🖤', 'categories': ['cinematic']},
    {'id': 'h_cin_5', 'text': '*khamoshi* sabse gehri aawaz hoti hai, bas sunne wala chahiye... 🕯️', 'categories': ['cinematic']},
    {'id': 'h_cin_6', 'text': 'shehar ki roshniyon mein hum aksar apna hi sukoon kho baithe 🌃✨', 'categories': ['cinematic']},
    {'id': 'h_cin_7', 'text': 'raat ke 3 baje ki thandi hawayein bohot kuch yaad dila deti hain 🌙', 'categories': ['cinematic']},
    {'id': 'h_cin_8', 'text': 'some silences are heavier than the loudest confessions 🖤', 'categories': ['cinematic']},
    {'id': 'h_cin_9', 'text': 'hum dono ek hi aasmaan ke neeche hain, fir bhi itne door 🌌', 'categories': ['cinematic']},
    {'id': 'h_cin_10', 'text': 'car ki khidki se aati hawa aur purane gaane, bas yehi sukoon hai 🚗✨', 'categories': ['cinematic']},
    {'id': 'h_cin_11', 'text': 'chalti hui zindagi mein thehar jaane ka mann karta hai jab shaam dhalti hai 🌅', 'categories': ['cinematic']},
    {'id': 'h_cin_12', 'text': 'we were a poem written in smoke, beautiful until we vanished 🖤', 'categories': ['cinematic']},
    {'id': 'h_cin_13', 'text': 'kuch log bas yaadon ke album mein hi zinda rehte hain 🥀', 'categories': ['cinematic']},
    {'id': 'h_cin_14', 'text': 'ye shehar toh wahi hai, bas isme pehle jaisa rang nahi raha 🌧️', 'categories': ['cinematic']},
    {'id': 'h_cin_15', 'text': 'chupchap baith kar chai peena aur khayalon mein khona... art hai ☕✨', 'categories': ['cinematic']},
    {'id': 'h_cin_16', 'text': 'in a city of millions, you only look for one shadow 🌃🖤', 'categories': ['cinematic']},
    {'id': 'h_cin_17', 'text': 'waqt ke sath sab badal gaya, bas wo ek shaam wahi thehar gayi 🥀', 'categories': ['cinematic']},
    {'id': 'h_cin_18', 'text': 'aankhon mein thakan aur dil mein hazaron unkahi daastaan 🖤🕯️', 'categories': ['cinematic']},
    {'id': 'h_cin_19', 'text': 'chalte chalte raste khatam ho gaye, par unka intezaar nahi ⏳', 'categories': ['cinematic']},
    {'id': 'h_cin_20', 'text': 'kabhi kabhi akelepan mein jo gehraai hoti hai, wo bheed mein kahan 🕊️', 'categories': ['cinematic']},
    {'id': 'h_cin_21', 'text': 'traffic ki red light par bhi tumhara hi chehra zehen mein aaya 🚗🌙', 'categories': ['cinematic']},
    {'id': 'h_cin_22', 'text': 'ye khamoshi kisi tufaan se pehle ki aahat lagti hai 🖤✨', 'categories': ['cinematic']},
    {'id': 'h_cin_23', 'text': 'kuch panne zindagi ke aise hote hain jinhe dobara padhne ki himmat nahi hoti 🥀', 'categories': ['cinematic']},
    {'id': 'h_cin_24', 'text': 'purane shehar ki galiyan aur unka beeta hua daur 🏛️✨', 'categories': ['cinematic']},
    {'id': 'h_cin_25', 'text': 'rooh ko chhoo lene wali baatein aksar sargoshiyon mein hoti hain 🌙', 'categories': ['cinematic']},
    {'id': 'h_cin_26', 'text': 'we don\'t remember days, we remember moments that shook our core 🖤', 'categories': ['cinematic']},
    {'id': 'h_cin_27', 'text': 'chand ko bhi aadat ho chuki hai hamari tanhaai dekhne ki 🌙🕊️', 'categories': ['cinematic']},
    {'id': 'h_cin_28', 'text': 'kabhi fursat mile toh un galiyon mein mud kar dekhna jahan hum the 🥀', 'categories': ['cinematic']},
    {'id': 'h_cin_29', 'text': 'the universe has a strange way of writing incomplete symphonies 🌌', 'categories': ['cinematic']},
    {'id': 'h_cin_30', 'text': 'kisi ka na hona bhi kabhi kabhi itna bhari lagta hai 🖤', 'categories': ['cinematic']},
    {'id': 'h_cin_31', 'text': 'rain on the windshield, lo-fi beats, and a million unspoken thoughts 🌧️🚗', 'categories': ['cinematic']},
    {'id': 'h_cin_32', 'text': 'sab kuch paakar bhi ek khalish si reh jaati hai 🥀', 'categories': ['cinematic']},
    {'id': 'h_cin_33', 'text': 'shab-e-gham ki taareekhiyon mein ek umeed ka diya jalaye rakha hai 🕯️', 'categories': ['cinematic']},
    {'id': 'h_cin_34', 'text': 'some goodbyes are never spoken, they just settle into your bones 🖤', 'categories': ['cinematic']},
    {'id': 'h_cin_35', 'text': 'shehar so gaya, par unka zikr meri deewaron par jaagta raha 🌙✨', 'categories': ['cinematic']},
    {'id': 'h_cin_36', 'text': 'tufaanon ke beech jo tehraav hota hai, wo meri aankhon mein dekh lo 👁️', 'categories': ['cinematic']},
    {'id': 'h_cin_37', 'text': 'purani haveliyon jaisa ho gaya hai dil, khamosh aur pur-israar 🏛️🖤', 'categories': ['cinematic']},
    {'id': 'h_cin_38', 'text': 'every sunset brings the promise of a quiet midnight revelation 🌅✨', 'categories': ['cinematic']},
    {'id': 'h_cin_39', 'text': 'zindagi ke is mod par ab kisi naye musafir ki umeed nahi 🥀', 'categories': ['cinematic']},
    {'id': 'h_cin_40', 'text': 'lafz kam pad gaye the us shaam, jab nazar ne alvida kaha tha 🖤⏳', 'categories': ['cinematic']},
    {'id': 'h_tra_1', 'text': 'hum toh fida the unki *saadgi* par, wo muskuraye aur hum ghayal ho gaye... 💋', 'categories': ['traditional']},
    {'id': 'h_tra_2', 'text': 'kabhi fursat mile toh aana hamare *dil* mein, wahan sirf tumhara hi naam hai... 💌', 'categories': ['traditional']},
    {'id': 'h_tra_3', 'text': 'khushnaseeb hain wo jo roz tera *deedar* karte hain... 💖', 'categories': ['traditional']},
    {'id': 'h_tra_4', 'text': 'jhumke ki chamak aur unki *saadgi*, dil haar baithe hum... 🪔', 'categories': ['traditional']},
    {'id': 'h_tra_5', 'text': 'teri *saadgi* par ye dil fida hai, kisi shringar ki zaroorat nahi... 👑', 'categories': ['traditional']},
    {'id': 'h_tra_6', 'text': 'banarasi libaas mein wo aayi toh laga jaise koi pari zameen par utar aayi... 🌸', 'categories': ['traditional']},
    {'id': 'h_tra_7', 'text': 'kajal se bhari nigahein aur kangan ki khanak, qayamat hai 🪔✨', 'categories': ['traditional']},
    {'id': 'h_tra_8', 'text': 'saree ka pallu jab hawa mein lehrata hai, hosh gawa baithte hain hum 👑💋', 'categories': ['traditional']},
    {'id': 'h_tra_9', 'text': 'unke jhumke ki khanak se dilon ki dhadkan tezz ho jati hai 🌸💫', 'categories': ['traditional']},
    {'id': 'h_tra_10', 'text': 'mehendi lage haath aur unme chhipa tera naam 🌿🤍', 'categories': ['traditional']},
    {'id': 'h_tra_11', 'text': 'sanskari ada aur teekhi nazar, lajawab hai ye desi andaaz 👑✨', 'categories': ['traditional']},
    {'id': 'h_tra_12', 'text': 'chunari ki oat se jab wo muskuraye, zamana thak gaya tareef karte 🪔', 'categories': ['traditional']},
    {'id': 'h_tra_13', 'text': 'bindiya maathe par aisi saji jaise chand par sitara 🌙🌸', 'categories': ['traditional']},
    {'id': 'h_tra_14', 'text': 'payal ki jhankar sunte hi dil unke aane ka sandesh samajh leta hai 💫', 'categories': ['traditional']},
    {'id': 'h_tra_15', 'text': 'unka dupatta girna aur hamara dil fisalna, ek hi lamha tha 👑💋', 'categories': ['traditional']},
    {'id': 'h_tra_16', 'text': 'kohl-rimmed eyes and a silent poetry written in grace 🪔✨', 'categories': ['traditional']},
    {'id': 'h_tra_17', 'text': 'chashme ke peeche se jo teer chalate ho, sidha kaleje mein lagta hai 🌸', 'categories': ['traditional']},
    {'id': 'h_tra_18', 'text': 'desi libaas ki khushbu hi aisi hai ki har koi fida ho jaye 👑', 'categories': ['traditional']},
    {'id': 'h_tra_19', 'text': 'unke maang teeke ki chamak aadhi raat ko bhi roshan kar de 🪔✨', 'categories': ['traditional']},
    {'id': 'h_tra_20', 'text': 'kali saree aur laal jhumka, is se haseen qayamat kya hogi 🖤🌹', 'categories': ['traditional']},
    {'id': 'h_tra_21', 'text': 'chand bhi sharma gaya jab usne unhe aaine ke samne dekha 🌙✨', 'categories': ['traditional']},
    {'id': 'h_tra_22', 'text': 'unke baalon mein gajra dekh kar bahaar bhi rashk karne lagi 🌸🕊️', 'categories': ['traditional']},
    {'id': 'h_tra_23', 'text': 'sadgi aisi ki sitare bhi unke aage pheeke lagte hain 👑', 'categories': ['traditional']},
    {'id': 'h_tra_24', 'text': 'har ada mein tehzeeb aur har baat mein nawazish 🪔🤍', 'categories': ['traditional']},
    {'id': 'h_tra_25', 'text': 'unka dupatta lehrana jaise registan mein pehli baarish hona 🌧️🌸', 'categories': ['traditional']},
    {'id': 'h_tra_26', 'text': 'choodiyan khankte hi mohalle ki neend ud jaati hai 💫💋', 'categories': ['traditional']},
    {'id': 'h_tra_27', 'text': 'desi roop ki taqat ye hai ki western wale bhi sar jhuka lete hain 👑✨', 'categories': ['traditional']},
    {'id': 'h_tra_28', 'text': 'unke haath ki chai aur unki ada, dono hi la-jawab hain ☕🪔', 'categories': ['traditional']},
    {'id': 'h_tra_29', 'text': 'gulaabi dupatta aur aankhon mein kajal, jaan le kar hi maanenge 🌸💋', 'categories': ['traditional']},
    {'id': 'h_tra_30', 'text': 'purani riwayaton jaisi pakki aur shuddh hai unki saadgi 🪔🕊️', 'categories': ['traditional']},
    {'id': 'h_tra_31', 'text': 'unka laal joda dekh kar lage jaise kainaat ka sara rang unhi par thehar gaya 🌹👑', 'categories': ['traditional']},
    {'id': 'h_tra_32', 'text': 'nazaakat aisi ki phool bhi unke aage sar jhukayein 🌸✨', 'categories': ['traditional']},
    {'id': 'h_tra_33', 'text': 'unke mathe ki bindi hamari qismat ka sitara lagti hai 🪔', 'categories': ['traditional']},
    {'id': 'h_tra_34', 'text': 'zulfein jab khuli chhod de wo, mausam badal jaata hai 🌧️🖤', 'categories': ['traditional']},
    {'id': 'h_tra_35', 'text': 'unka aanchal thamna hi mano jannat mil jana hai 🕊️👑', 'categories': ['traditional']},
    {'id': 'h_tra_36', 'text': 'traditional outfit mein jo rani lagti ho, kisi taj ki mohtaj nahi 👑💎', 'categories': ['traditional']},
    {'id': 'h_tra_37', 'text': 'kajal ki lakeer unki aankhon ki hifazat karti hai ya hamara qatal? 💋🪔', 'categories': ['traditional']},
    {'id': 'h_tra_38', 'text': 'unka paanv chhoona aur payal ka bol uthna, sangeet hai 🌸✨', 'categories': ['traditional']},
    {'id': 'h_tra_39', 'text': 'desi tehzeeb ka jadoo hi aisa hai ki dil bas unhi par aake rukta hai 👑🤍', 'categories': ['traditional']},
    {'id': 'h_tra_40', 'text': 'unke aane se aangan mein diwali jaisi roshni ho jati hai 🪔✨', 'categories': ['traditional']},
    {'id': 'h_bro_1', 'text': 'kuch dard aise hote hain jo bayaan nahi kiye jaate, bas chup rehna padta hai... 💔', 'categories': ['broken']},
    {'id': 'h_bro_2', 'text': 'hum unhe *yaad* karte rahe jo hume bhula chuke the... 🥀', 'categories': ['broken']},
    {'id': 'h_bro_3', 'text': 'waqt badalta hai toh log badalte hain, par *dard* wahi rehta hai... 🌧️', 'categories': ['broken']},
    {'id': 'h_bro_4', 'text': 'kash tum samajh paate ki kitna *chahte* the tumhe... 🖤', 'categories': ['broken']},
    {'id': 'h_bro_5', 'text': 'ab kisi se koi shikayat nahi, bas khud se thoda gila hai... 🥀', 'categories': ['broken']},
    {'id': 'h_bro_6', 'text': 'hans kar sehna seekh liya, kyunki aansu pochne wala koi nahi... 💔', 'categories': ['broken']},
    {'id': 'h_bro_7', 'text': 'itna toota hoon ki ab bikharne ka bhi darr nahi lagta... 🕯️', 'categories': ['broken']},
    {'id': 'h_bro_8', 'text': 'unka badalna toh tey tha, par itni berukhi ki umeed na thi 🥀', 'categories': ['broken']},
    {'id': 'h_bro_9', 'text': 'hum unke liye option the, aur wo hamare liye aakhri khwahish 💔', 'categories': ['broken']},
    {'id': 'h_bro_10', 'text': 'ab kisi se dil lagane ki himmat nahi rahi, thak chuka hoon 🌧️', 'categories': ['broken']},
    {'id': 'h_bro_11', 'text': 'raat ko akele rona aur subah muskura kar sab theek kehna... roz ka hai 🖤', 'categories': ['broken']},
    {'id': 'h_bro_12', 'text': 'kash unhone ek baar mud kar dekha hota hamari aankhon ki nami 🥀', 'categories': ['broken']},
    {'id': 'h_bro_13', 'text': 'jo log kehte the hamesha sath rahenge, wahi pehle gayab huye 💔', 'categories': ['broken']},
    {'id': 'h_bro_14', 'text': 'dil unhi se toot tha hai jinke aage humne khud ko khol kar rakh diya tha 🕯️', 'categories': ['broken']},
    {'id': 'h_bro_15', 'text': 'ab unke online hone se bhi koi umeed nahi jaagti 🥀', 'categories': ['broken']},
    {'id': 'h_bro_16', 'text': 'tujhe bhoolne ki koshish mein khud ko kitna kho chuka hoon 🖤', 'categories': ['broken']},
    {'id': 'h_bro_17', 'text': 'kash dil par pathar rakhna itna aasan hota jitna log bolte hain 💔', 'categories': ['broken']},
    {'id': 'h_bro_18', 'text': 'unke diye huye zakhmon par ab hansi aati hai apni bewakoofi dekh kar 🌧️', 'categories': ['broken']},
    {'id': 'h_bro_19', 'text': 'hum wafa karte rahe aur wo timepass samajhte rahe 🥀', 'categories': ['broken']},
    {'id': 'h_bro_20', 'text': 'zindagi mein kuch log sirf ye sikhane aate hain ki kisi par andha vishwas mat karo 🖤', 'categories': ['broken']},
    {'id': 'h_bro_21', 'text': 'ab khamoshi hi meri sabse achhi dost ban gayi hai 🕯️', 'categories': ['broken']},
    {'id': 'h_bro_22', 'text': 'kabhi socha na tha ki jinke bina saans nahi aati thi, unke bina jeena seekh lenge 💔', 'categories': ['broken']},
    {'id': 'h_bro_23', 'text': 'unka aakhri message aaj bhi padh kar dil thoda sa mar jata hai 🥀', 'categories': ['broken']},
    {'id': 'h_bro_24', 'text': 'chhod diya humne bhi unhe unki marzi ke logon ke sath 🌧️', 'categories': ['broken']},
    {'id': 'h_bro_25', 'text': 'hum toh unki ek muskaan ke liye marne ko tayyar the, unhone zinda hi maar diya 💔', 'categories': ['broken']},
    {'id': 'h_bro_26', 'text': 'ab kisi naye insaan ke aane se darr lagta hai, kahi wahi purani kahani na dohraye 🖤', 'categories': ['broken']},
    {'id': 'h_bro_27', 'text': 'tujhe khona meri kismat thi ya meri galti, aaj tak samajh nahi aaya 🥀', 'categories': ['broken']},
    {'id': 'h_bro_28', 'text': 'itna dard sahkar bhi zinda hoon, ye meri sabse badi saza hai 🕯️', 'categories': ['broken']},
    {'id': 'h_bro_29', 'text': 'unhe lagta hai hum khush hain, unhe kya pata andar se banjar ho chuke hain 💔', 'categories': ['broken']},
    {'id': 'h_bro_30', 'text': 'kash koi hamare dard ko bhi bina kahe mehsoos kar pata 🌧️', 'categories': ['broken']},
    {'id': 'h_bro_31', 'text': 'tumne chhod kar accha kiya, hume hamari aukaat pata chal gayi 🥀', 'categories': ['broken']},
    {'id': 'h_bro_32', 'text': 'dil tootne par koi awaz nahi hoti, bas insan andar se mar jata hai 🖤', 'categories': ['broken']},
    {'id': 'h_bro_33', 'text': 'unka diya har tohfa wapas kar diya, par unki yaadein kahan phenku? 💔', 'categories': ['broken']},
    {'id': 'h_bro_34', 'text': 'hum toh unke liye mitti the, unhone dhool samajh kar jhaad diya 🌧️', 'categories': ['broken']},
    {'id': 'h_bro_35', 'text': 'ab kisi ki yaad aane par rona nahi aata, bas ek gehra dard chalta rehta hai 🥀', 'categories': ['broken']},
    {'id': 'h_bro_36', 'text': 'jo chala gaya wo kabhi hamara tha hi nahi, ye tasalli dil ko roz dete hain 🕯️', 'categories': ['broken']},
    {'id': 'h_bro_37', 'text': 'kitni ajeeb baat hai na, wahi insaan rulata hai jisne hasna sikhaya tha 💔', 'categories': ['broken']},
    {'id': 'h_bro_38', 'text': 'kash hum unse mile hi na hote us shaam 🖤', 'categories': ['broken']},
    {'id': 'h_bro_39', 'text': 'dard bayaan karne ki chahat ab khatam ho chuki hai, silence is better 🥀', 'categories': ['broken']},
    {'id': 'h_bro_40', 'text': 'toote huye dil ki dua kabhi khali nahi jati, ye yaad rakhna 🕯️💔', 'categories': ['broken']},
    {'id': 'h_aes_1', 'text': 'romanticizing every little moment of my life 🌸✨', 'categories': ['aesthetic']},
    {'id': 'h_aes_2', 'text': 'soft eyes, warm *heart*, peaceful mind 🕊️', 'categories': ['aesthetic']},
    {'id': 'h_aes_3', 'text': 'chasing sunsets, golden hour *glow* and good energy ✨', 'categories': ['aesthetic']},
    {'id': 'h_aes_4', 'text': 'finding *magic* in the ordinary days 💫', 'categories': ['aesthetic']},
    {'id': 'h_aes_5', 'text': 'collecting moments, not things 🌿✨', 'categories': ['aesthetic']},
    {'id': 'h_aes_6', 'text': 'peace over drama, distance over disrespect 🕊️', 'categories': ['aesthetic']},
    {'id': 'h_aes_7', 'text': 'living gently, loving deeply, dreaming softly 🌸', 'categories': ['aesthetic']},
    {'id': 'h_aes_8', 'text': 'cold breeze, hot tea, and cozy oversized sweater vibes ☕🍂', 'categories': ['aesthetic']},
    {'id': 'h_aes_9', 'text': 'in my soft girl era, protected and deeply at peace ✨🕊️', 'categories': ['aesthetic']},
    {'id': 'h_aes_10', 'text': 'sunlight hitting the room just right at 5 PM 🌇', 'categories': ['aesthetic']},
    {'id': 'h_aes_11', 'text': 'healing quietly, growing gracefully, glowing silently 🌿🌸', 'categories': ['aesthetic']},
    {'id': 'h_aes_12', 'text': 'small joys: rain drops on window, favorite melody on loop 🌧️🎧', 'categories': ['aesthetic']},
    {'id': 'h_aes_13', 'text': 'gratitude turns what we have into enough ✨🤍', 'categories': ['aesthetic']},
    {'id': 'h_aes_14', 'text': 'radiating golden hour warmth and calm aura 🕊️', 'categories': ['aesthetic']},
    {'id': 'h_aes_15', 'text': 'keeping my peace like it\'s the rarest treasure on earth 🌿💎', 'categories': ['aesthetic']},
    {'id': 'h_aes_16', 'text': 'less perfection, more authenticity and soft smiles 🌸', 'categories': ['aesthetic']},
    {'id': 'h_aes_17', 'text': 'sipping chai and letting the world rush past ☕✨', 'categories': ['aesthetic']},
    {'id': 'h_aes_18', 'text': 'making space for slow mornings and quiet sunsets 🌇🕊️', 'categories': ['aesthetic']},
    {'id': 'h_aes_19', 'text': 'a heart that listens, a soul that wanders gently 🌿', 'categories': ['aesthetic']},
    {'id': 'h_aes_20', 'text': 'golden rays, vintage books, and endless daydreams 📖✨', 'categories': ['aesthetic']},
    {'id': 'h_aes_21', 'text': 'blossoming into the person I always wanted to be 🌸🤍', 'categories': ['aesthetic']},
    {'id': 'h_aes_22', 'text': 'nature doesn\'t hurry, yet everything is accomplished 🌿🕊️', 'categories': ['aesthetic']},
    {'id': 'h_aes_23', 'text': 'protecting my peace at all costs ☕✨', 'categories': ['aesthetic']},
    {'id': 'h_aes_24', 'text': 'softness is not weakness, it\'s the deepest strength 🌸', 'categories': ['aesthetic']},
    {'id': 'h_aes_25', 'text': 'starry nights and poetry that smells like old pages 🌌📖', 'categories': ['aesthetic']},
    {'id': 'h_aes_26', 'text': 'embracing the little miracles tucked into mundane days ✨', 'categories': ['aesthetic']},
    {'id': 'h_aes_27', 'text': 'warm lighting, soulful music, and a calm room 🕯️🎧', 'categories': ['aesthetic']},
    {'id': 'h_aes_28', 'text': 'be gentle with yourself, you\'re doing the best you can 🤍🕊️', 'categories': ['aesthetic']},
    {'id': 'h_aes_29', 'text': 'living in harmony with the rhythm of my own heart 🌿', 'categories': ['aesthetic']},
    {'id': 'h_aes_30', 'text': 'cloudy skies, ambient tunes, and hot coffee moments ☕🌧️', 'categories': ['aesthetic']},
    {'id': 'h_aes_31', 'text': 'blooming where life plants me, quietly and beautifully 🌸', 'categories': ['aesthetic']},
    {'id': 'h_aes_32', 'text': 'slow down, the best chapters are read without rushing 📖✨', 'categories': ['aesthetic']},
    {'id': 'h_aes_33', 'text': 'candlelight reflections on a rainy midnight 🕯️🌧️', 'categories': ['aesthetic']},
    {'id': 'h_aes_34', 'text': 'a quiet life with deep meaning over loud chaos 🕊️🌿', 'categories': ['aesthetic']},
    {'id': 'h_aes_35', 'text': 'breathing in gratitude, exhaling everything that feels heavy ✨', 'categories': ['aesthetic']},
    {'id': 'h_aes_36', 'text': 'capturing the soft poetry of daily existence 🌸📸', 'categories': ['aesthetic']},
    {'id': 'h_aes_37', 'text': 'sunsets are proof that endings can be breathtaking too 🌇', 'categories': ['aesthetic']},
    {'id': 'h_aes_38', 'text': 'surrounded by calm thoughts and pastel skies 🕊️✨', 'categories': ['aesthetic']},
    {'id': 'h_aes_39', 'text': 'letting life unfold with grace and effortless trust 🌿🌸', 'categories': ['aesthetic']},
    {'id': 'h_aes_40', 'text': 'stay soft, the world has enough sharp edges 🤍🕊️', 'categories': ['aesthetic']},
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
            "categories": ["sexy", "romantic", "cinematic", "traditional"],
        }
    if img_id.startswith("dyn_") or img_id.startswith("ai_gen_"):
        return {
            "id": img_id,
            "title": "✨ Dynamic AI Candid Photo",
            "filename": f"{img_id}.jpg",
            "icon": "✨",
            "desc": "Dynamic AI visual generated uniquely for you",
            "categories": ["sexy", "romantic", "cinematic", "traditional"],
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
            "categories": ["sexy", "romantic", "cinematic", "traditional"],
        }
    for opt in ALL_IMAGE_OPTIONS:
        if opt["id"] == img_id:
            return opt
    return ALL_IMAGE_OPTIONS[0]


def get_category_info(cat_id: Optional[str]) -> Dict[str, Any]:
    """Retrieve category dictionary or default to 'sexy'."""
    if cat_id and cat_id.lower() in CATEGORIES:
        return CATEGORIES[cat_id.lower()]
    return CATEGORIES["sexy"]


async def get_fresh_image_options(
    chat_id: int,
    category: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Return 5 unused candid images for this user filtered by category, guaranteed zero repeats."""
    used = await db_manager.get_used_assets(chat_id, "image")
    cat = category.lower().strip() if category else None
    if cat:
        if cat in ("sexy", "baddie", "bestie", "aesthetic", "hot"):
            pool = [opt for opt in ALL_IMAGE_OPTIONS if any(c in opt.get("categories", []) for c in ("sexy", "baddie", "bestie", "aesthetic"))]
        elif cat in ("cinematic", "broken"):
            pool = [opt for opt in ALL_IMAGE_OPTIONS if any(c in opt.get("categories", []) for c in ("cinematic", "broken"))]
        else:
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
            "categories": [cat] if cat else ["sexy", "romantic", "cinematic", "traditional"],
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
    """Step 0: Category / Vibe Selection (8 Curated Vibes)."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💋 Sexy / Flirty Desi", callback_data="cat_sexy"),
            InlineKeyboardButton("🔥 Hot & Baddie", callback_data="cat_baddie"),
        ],
        [
            InlineKeyboardButton("👯‍♀️ Bestie Love", callback_data="cat_bestie"),
            InlineKeyboardButton("💖 Romantic Love", callback_data="cat_romantic"),
        ],
        [
            InlineKeyboardButton("🎬 Late Night Cinematic", callback_data="cat_cinematic"),
            InlineKeyboardButton("👑 Desi Traditional", callback_data="cat_traditional"),
        ],
        [
            InlineKeyboardButton("💔 Broken Heart / Dard", callback_data="cat_broken"),
            InlineKeyboardButton("✨ Aesthetic / Soft", callback_data="cat_aesthetic"),
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
    """Handle /auto command - starts Category-first selection flow."""
    msg = (
        "🎬 *Reel Studio: Choose Your Category*\n\n"
        "Please select the vibe / category for your reel first:\n\n"
        "• 💋 *Sexy / Flirty Desi:* Bold candid selfies & sultry vibes\n"
        "• 🔥 *Hot & Baddie / Attitude:* Sassy attitude & self-love\n"
        "• 👯‍♀️ *Bestie Love / Duo Goals:* Cute bestie bonds & sisterhood\n"
        "• 💖 *Romantic / Love:* Pastel sarees & heartwarming love lyrics\n"
        "• 🎬 *Late Night / Cinematic:* Neon bokeh & late night thoughts\n"
        "• 👑 *Desi Traditional:* Royal sarees & timeless shayari\n"
        "• 💔 *Broken Heart / Dard:* Emotional heartbreak & soulful pain\n"
        "• ✨ *Aesthetic / Soft Glow:* Golden hour & peaceful calm vibes\n\n"
        "_(💡 Visuals, text hooks & Bollywood songs will strictly adapt to your choice!)_"
    )
    if update.effective_message:
        await update.effective_message.reply_text(
            msg,
            reply_markup=build_category_selection_keyboard(),
            parse_mode="Markdown",
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
    """Check if user typed quick keywords like 'reel', 'new', 'start'."""
    message = update.effective_message
    if not message or not message.text:
        return False

    raw = message.text.strip().lower()
    if raw in ("reel", "reels", "auto", "start", "new", "image", "video", "create"):
        msg = (
            "🎬 *Reel Studio: Choose Your Category*\n\n"
            "Select the vibe / category for your reel first:\n\n"
            "• 💋 *Sexy / Flirty Desi:* Bold candid selfies & sultry vibes\n"
            "• 🔥 *Hot & Baddie / Attitude:* Sassy attitude & self-love\n"
            "• 👯‍♀️ *Bestie Love / Duo Goals:* Cute bestie bonds & sisterhood\n"
            "• 💖 *Romantic / Love:* Pastel sarees & heartwarming love lyrics\n"
            "• 🎬 *Late Night / Cinematic:* Neon bokeh & late night thoughts\n"
            "• 👑 *Desi Traditional:* Royal sarees & timeless shayari\n"
            "• 💔 *Broken Heart / Dard:* Emotional heartbreak & soulful pain\n"
            "• ✨ *Aesthetic / Soft Glow:* Golden hour & peaceful calm vibes\n\n"
            "_(💡 Your choice determines matching candid images, hooks & songs!)_"
        )
        await message.reply_text(
            msg,
            reply_markup=build_category_selection_keyboard(),
            parse_mode="Markdown",
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

    cat = cat or "romantic"
    img_id = img_id or "balcony_saree"
    hook_text = hook_text or "tere bina ab sham nahi dhaltee, har lamha sirf tera hi intezaar hai... 🌙"

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
    cat = category or context.user_data.get("chosen_cat", "sexy")
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
    cat = context.user_data.get("chosen_cat", "sexy")
    img_id = context.user_data.get("chosen_img", "sheer_saree")
    await send_visual_text_preview(update, context, chat_id, img_id=img_id, hook_text=custom_text, cat_id=cat)




# -------------------------------------------------------------
# Interactive Studio Flow with Used Folder & Instant Previews
# -------------------------------------------------------------

def get_random_category_image(cat_id: str, chat_id: int, used_names_override: Optional[set] = None) -> Path:
    """Pick a random unused image from assets/images/categories/{cat_id}."""
    folder = cat_id.lower().strip() if cat_id else "sexy"
    cat_dir = Path("assets/images/categories") / folder
    used_dir = Path("assets/images/used")

    if not cat_dir.exists():
        cat_dir = Path("assets/images/categories/sexy")

    used_names = set(used_names_override) if used_names_override else set()
    if used_dir.exists():
        for f in used_dir.iterdir():
            if f.is_file():
                used_names.add(f.name)

    files = [f for f in cat_dir.iterdir() if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png")]
    available = [f for f in files if f.name not in used_names]

    if not available:
        available = files

    if not available:
        return Path("assets/images/candid/red_saree_candid_selfie.jpg")

    return random.choice(available)


def build_studio_preview_keyboard() -> InlineKeyboardMarkup:
    """Action buttons attached to the live 1080x1920 preview image."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 Render Reel", callback_data="studio_render")
        ],
        [
            InlineKeyboardButton("⏭️ Skip Photo", callback_data="studio_skip"),
            InlineKeyboardButton("🔄 New Quote", callback_data="studio_new_text"),
        ],
        [
            InlineKeyboardButton("✏️ Custom Text", callback_data="studio_custom_text"),
            InlineKeyboardButton("🔙 Categories", callback_data="back_to_cats"),
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
    cat_id = context.user_data.get("chosen_cat", "sexy")
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

    elif data == "studio_skip":
        cat_id = context.user_data.get("chosen_cat", "sexy")
        try:
            await query.delete_message()
        except Exception:
            pass
        await send_interactive_studio_preview(update, context, cat_id=cat_id, force_new_img=True)
        return

    elif data == "studio_new_text":
        cat_id = context.user_data.get("chosen_cat", "sexy")
        img_p_str = context.user_data.get("studio_img_path")
        img_p = Path(img_p_str) if img_p_str else None
        try:
            await query.delete_message()
        except Exception:
            pass
        await send_interactive_studio_preview(update, context, cat_id=cat_id, image_path=img_p, custom_text=None, force_new_img=False)
        return

    elif data == "studio_custom_text":
        context.user_data["waiting_for_custom_text"] = True
        await db_manager.update_session(chat_id, current_step="WAITING_STUDIO_TEXT")
        msg = (
            "✏️ *Type your custom text / quote:*\n\n"
            "Send your text in this chat, and the bot will instantly render a new preview with your lines on this photo!"
        )
        if query.message:
            await query.message.reply_text(msg, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        return

    elif data == "studio_render":
        cat_id = context.user_data.get("chosen_cat", "sexy")
        img_p_str = context.user_data.get("studio_img_path")
        hook_text = context.user_data.get("studio_text", "teri aankhon mein doob jane ka mann karta hai... 🖤")
        img_p = Path(img_p_str) if (img_p_str and Path(img_p_str).exists()) else get_random_category_image(cat_id, chat_id)

        try:
            await query.edit_message_caption(
                caption=f"⚡ *Reel Rendering Started...*\n\n• Category: *{cat_id.title()}*\n• Image: `{img_p.name}`\n\n_1080x1920 HD video mixing with Bollywood vocals..._",
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
        cat_id = context.user_data.get("chosen_cat", "sexy")
        cat_info = get_category_info(cat_id)
        fresh_images = await get_fresh_image_options(chat_id, category=cat_id, limit=5)
        context.user_data["current_img_options"] = fresh_images

        msg = (
            f"📸 *Step 1 of 3: Choose Visual (Image)*\n\n"
            f"📂 *Category:* {cat_info['icon']} *{cat_info['title']}*\n"
            f"_{cat_info['desc']}_\n\n"
            "Select 1 of 5 authentic candid photo aesthetics below:\n"
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
        msg = (
            "🎬 *Reel Studio: Choose Your Category*\n\n"
            "Please select the vibe / category for your reel first:\n\n"
            "• 💋 *Sexy / Flirty Desi:* Bold candid selfies & sultry vibes\n"
            "• 🔥 *Hot & Baddie / Attitude:* Sassy attitude & self-love\n"
            "• 👯‍♀️ *Bestie Love / Duo Goals:* Cute bestie bonds & sisterhood\n"
            "• 💖 *Romantic / Love:* Pastel sarees & heartwarming love lyrics\n"
            "• 🎬 *Late Night / Cinematic:* Neon bokeh & late night thoughts\n"
            "• 👑 *Desi Traditional:* Royal sarees & timeless shayari\n"
            "• 💔 *Broken Heart / Dard:* Emotional heartbreak & soulful pain\n"
            "• ✨ *Aesthetic / Soft Glow:* Golden hour & peaceful calm vibes\n\n"
            "_(💡 Visuals, text hooks & Bollywood songs will strictly adapt to your choice!)_"
        )
        await query.edit_message_text(
            msg,
            reply_markup=build_category_selection_keyboard(),
            parse_mode="Markdown",
        )

    # -------------------------------------------------------------
    # Upload Own Image Instruction
    # -------------------------------------------------------------
    elif data == "upload_own_img":
        cat_id = context.user_data.get("chosen_cat", "romantic")
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
        cat_id = context.user_data.get("chosen_cat", "sexy")
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
        cat_id = context.user_data.get("chosen_cat", "sexy")
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
        cat_id = context.user_data.get("chosen_cat", "sexy")
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

        cat_id = context.user_data.get("chosen_cat", "sexy")
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
        cat_id = context.user_data.get("chosen_cat", "sexy")
        cat_info = get_category_info(cat_id)
        img_id = context.user_data.get("chosen_img", "sheer_saree")
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
        cat_id = context.user_data.get("chosen_cat", "sexy")
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
        cat_id = context.user_data.get("chosen_cat", "sexy")
        img_id = context.user_data.get("chosen_img", "sheer_saree")

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
        cat_id = context.user_data.get("chosen_cat", "sexy")
        fresh_songs = await get_fresh_song_options(chat_id, category=cat_id, limit=5)
        context.user_data["current_song_options"] = fresh_songs
        await query.edit_message_reply_markup(
            reply_markup=build_song_selection_keyboard(fresh_songs, category=cat_id)
        )

    # -------------------------------------------------------------
    # Back to Hooks from Preview
    # -------------------------------------------------------------
    elif data == "back_to_hooks":
        cat_id = context.user_data.get("chosen_cat", "sexy")
        cat_info = get_category_info(cat_id)
        img_id = context.user_data.get("chosen_img", "sheer_saree")
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

        cat_id = context.user_data.get("chosen_cat", "sexy")
        img_id = context.user_data.get("chosen_img", "sheer_saree")
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

