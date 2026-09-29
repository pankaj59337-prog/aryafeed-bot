"""Auto-Caption & Viral Hashtag Generation Engine for Instagram Reels."""

import random
from typing import List, Optional

# High-CTR CTAs tailored for flirty, aesthetic & viral reels
CTAS: List[str] = [
    "Drop a '🖤' if you agree...",
    "Save this for late night vibes 🌙✨",
    "Tag your 2 AM person 🥀",
    "Double tap if this hit home ❤️‍🩹",
    "Share with someone who needs to see this 💬",
    "Comment your mood in one emoji 🌚",
    "Rehne do cutie, sach bolna allowed nahi hai 🤫",
    "Don't forget to save this 📌",
]

# Naughty / flirty contextual teasers
TEASERS: List[str] = [
    "Some thoughts are just better left unspoken... or maybe not 🥀🖤",
    "Sharafat ka zamana gaya, late night vibes only 🌙",
    "If you know, you know 🤫",
    "Main kuch nahi bol rahi, bas aankhein bol rahi hain ✨",
    "2 AM rules are always unwritten 🥀",
    "Ek glance hi kafi tha hosh udane ke liye 💋",
    "Don't blame me, blame the vibe 🌙✨",
]

# Curated high-reach hashtags for explore page algorithms
GENERAL_HASHTAGS: List[str] = [
    "#reels", "#explorepage", "#viralreels", "#trendingreels",
    "#reelitfeelit", "#fyp", "#foryou", "#explore", "#viral",
    "#instadaily", "#trending", "#reelsinstagram"
]

STYLE_HASHTAGS = {
    "sexy": [
        "#seductivelook", "#latenightvibes", "#flirty", "#desi",
        "#sareelover", "#desiattire", "#indianbeauty", "#moodygrams",
        "#aestheticvibes", "#desiaesthetic", "#boldlook", "#nightowl"
    ],
    "romantic": [
        "#romanticvibes", "#lovequotes", "#romance", "#feelings",
        "#deepthoughts", "#couplesgoals", "#soulmate", "#aesthetic",
        "#emotionalquotes", "#silentlove"
    ],
    "cinematic": [
        "#cinematicreels", "#visualart", "#moodyedits", "#filmphotography",
        "#darkaesthetic", "#cinematography", "#aestheticfeed", "#storytelling"
    ],
    "meme": [
        "#relatablememes", "#funnymemes", "#humor", "#memesdaily",
        "#dailymemes", "#indianmemes", "#dankmemes", "#relatable"
    ],
    "news_banner": [
        "#aryafeed", "#trendingnews", "#indiannews", "#exploreindia",
        "#rvcjinsta", "#dailynews", "#breakingnews", "#viralnews",
        "#reelsindia", "#cricketnews", "#factsindia", "#currentaffairs"
    ],
    "news_card": [
        "#aryafeed", "#trendingnews", "#indiannews", "#exploreindia",
        "#rvcjinsta", "#curiousfacts", "#newsupdate", "#bharatnews",
        "#reelsindia", "#topstories", "#viralpost", "#facts"
    ],
    "news": [
        "#aryafeed", "#trendingnews", "#indiannews", "#exploreindia",
        "#rvcjinsta", "#dailynews", "#breakingnews", "#viralnews"
    ],
}


def generate_instagram_caption(
    hook_text: str,
    style: str = "news_banner",
    custom_tag_count: int = 12,
) -> str:
    """Generate an Instagram-ready caption complete with hook, teaser/debate CTA, and targeted hashtags."""
    clean_hook = hook_text.strip()
    style_key = style.lower().strip()

    # Specialized AryaFeed Viral News / Infotainment format
    if style_key in ("news_banner", "news_card", "news"):
        specific_tags = STYLE_HASHTAGS.get(style_key, STYLE_HASHTAGS["news_banner"])
        hashtag_block = " ".join(specific_tags[:custom_tag_count])
        debate_cta = "What are your thoughts on this? Tell us in the comments 👇"
        parts = [
            clean_hook,
            "",
            "⚡ The Daily Pulse of India | Stories That Matter",
            f"👉 {debate_cta}",
            "",
            "📩 Follow @aryafeed.in for daily viral news & updates.",
            ".",
            ".",
            hashtag_block
        ]
        return "\n".join(parts)

    # Pick teaser and CTA for aesthetic & late-night reels
    teaser = random.choice(TEASERS)
    cta = random.choice(CTAS)

    specific_tags = STYLE_HASHTAGS.get(style_key, STYLE_HASHTAGS["news_banner"])
    all_tags = list(set(GENERAL_HASHTAGS + specific_tags))
    random.shuffle(all_tags)
    selected_tags = all_tags[:custom_tag_count]
    hashtag_block = " ".join(selected_tags)

    parts = [
        clean_hook,
        "",
        teaser,
        "",
        f"• {cta}",
        "• Follow @aryafeed.in for daily news & updates ⚡",
        "",
        ".",
        ".",
        ".",
        hashtag_block
    ]
    return "\n".join(parts)

