"""Template definitions and visual styling parameters for reels."""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class TemplateStyle:
    key: str
    display_name: str
    description: str
    base_font_size: int
    text_color: Tuple[int, int, int, int]
    stroke_color: Optional[Tuple[int, int, int, int]] = None
    stroke_width: int = 0
    shadow_color: Optional[Tuple[int, int, int, int]] = None
    shadow_offset: Tuple[int, int] = (0, 0)
    vertical_align: str = "center"  # "top", "center", "lower_center", "bottom"
    is_uppercase: bool = False
    quote_marks: bool = False
    box_scrim: bool = False
    scrim_color: Tuple[int, int, int, int] = (0, 0, 0, 110)
    scrim_radius: int = 24
    scrim_padding: int = 36
    ken_burns: str = "zoom_in"  # "zoom_in", "zoom_out", "pan", "none"
    fade_seconds: float = 0.5
    highlight_color: Tuple[int, int, int, int] = (255, 220, 50, 255)
    brand_badge: bool = True
    brand_text: str = "ARYAFEED"
    brand_badge_color: Tuple[int, int, int, int] = (255, 220, 0, 255)
    source_tag: bool = False


TEMPLATES = {
    "cinematic": TemplateStyle(
        key="cinematic",
        display_name="Cinematic 🎬",
        description="White text, thin dark shadow, lower-center placement with smooth fade",
        base_font_size=68,
        text_color=(255, 255, 255, 255),
        stroke_color=(20, 20, 20, 180),
        stroke_width=2,
        shadow_color=(0, 0, 0, 160),
        shadow_offset=(4, 6),
        vertical_align="lower_center",
        is_uppercase=False,
        box_scrim=False,
        ken_burns="zoom_in",
        fade_seconds=0.8,
    ),
    "meme": TemplateStyle(
        key="meme",
        display_name="Meme 😂",
        description="Bold white text with thick black outline, high-impact readability",
        base_font_size=82,
        text_color=(255, 255, 255, 255),
        stroke_color=(0, 0, 0, 255),
        stroke_width=8,
        shadow_color=(0, 0, 0, 220),
        shadow_offset=(5, 5),
        vertical_align="center",
        is_uppercase=True,
        box_scrim=False,
        ken_burns="none",
        fade_seconds=0.2,
    ),
    "romantic": TemplateStyle(
        key="romantic",
        display_name="Romantic 💖",
        description="Elegant styling, soft placement, slow subtle zoom and smooth transitions",
        base_font_size=64,
        text_color=(255, 250, 245, 255),
        stroke_color=(0, 0, 0, 160),
        stroke_width=2,
        shadow_color=(0, 0, 0, 180),
        shadow_offset=(3, 5),
        vertical_align="lower_center",
        is_uppercase=False,
        box_scrim=False,
        ken_burns="zoom_in",
        fade_seconds=1.0,
    ),
    "quote": TemplateStyle(
        key="quote",
        display_name="Quote 📜",
        description="High readability, clean dimmed background card, centered quote marks",
        base_font_size=60,
        text_color=(255, 255, 255, 255),
        stroke_color=None,
        stroke_width=0,
        shadow_color=(0, 0, 0, 180),
        shadow_offset=(3, 4),
        vertical_align="center",
        is_uppercase=False,
        quote_marks=True,
        box_scrim=True,
        scrim_color=(0, 0, 0, 140),
        scrim_radius=32,
        scrim_padding=48,
        ken_burns="zoom_out",
        fade_seconds=0.6,
    ),
    "minimal": TemplateStyle(
        key="minimal",
        display_name="Minimal ✨",
        description="Small clean white text, simple modern layout, understated elegance",
        base_font_size=50,
        text_color=(245, 245, 245, 240),
        stroke_color=(0, 0, 0, 80),
        stroke_width=1,
        shadow_color=(0, 0, 0, 100),
        shadow_offset=(2, 3),
        vertical_align="lower_center",
        is_uppercase=False,
        box_scrim=False,
        ken_burns="none",
        fade_seconds=0.4,
    ),
    "sexy": TemplateStyle(
        key="sexy",
        display_name="Sexy 💋",
        description="Bold late-night vibes, clean floating text, soft shadow, zero background box",
        base_font_size=68,
        text_color=(255, 255, 255, 255),
        stroke_color=(0, 0, 0, 180),
        stroke_width=2,
        shadow_color=(0, 0, 0, 220),
        shadow_offset=(4, 5),
        vertical_align="lower_center",
        is_uppercase=False,
        box_scrim=False,
        ken_burns="zoom_in",
        fade_seconds=0.7,
    ),
    "traditional": TemplateStyle(
        key="traditional",
        display_name="Traditional 👑",
        description="Royal desi aesthetics, clean floating text, soft shadow, zero background box",
        base_font_size=66,
        text_color=(255, 255, 255, 255),
        stroke_color=(0, 0, 0, 180),
        stroke_width=2,
        shadow_color=(0, 0, 0, 220),
        shadow_offset=(4, 5),
        vertical_align="lower_center",
        is_uppercase=False,
        box_scrim=False,
        ken_burns="zoom_in",
        fade_seconds=0.8,
    ),
    "bestie": TemplateStyle(
        key="bestie",
        display_name="Bestie Love 👯‍♀️",
        description="Vibrant bestie vibes, clean floating text, golden word highlight, zero background box",
        base_font_size=68,
        text_color=(255, 255, 255, 255),
        stroke_color=(0, 0, 0, 180),
        stroke_width=2,
        shadow_color=(0, 0, 0, 220),
        shadow_offset=(4, 5),
        vertical_align="lower_center",
        is_uppercase=False,
        box_scrim=False,
        ken_burns="zoom_in",
        fade_seconds=0.7,
        highlight_color=(255, 220, 50, 255),
    ),
    "baddie": TemplateStyle(
        key="baddie",
        display_name="Hot & Baddie 🔥",
        description="Bold attitude styling, clean floating text, soft shadow, radiant golden word highlight",
        base_font_size=68,
        text_color=(255, 255, 255, 255),
        stroke_color=(0, 0, 0, 180),
        stroke_width=2,
        shadow_color=(0, 0, 0, 220),
        shadow_offset=(4, 5),
        vertical_align="lower_center",
        is_uppercase=False,
        box_scrim=False,
        ken_burns="zoom_in",
        fade_seconds=0.7,
        highlight_color=(255, 220, 50, 255),
    ),
    "news_banner": TemplateStyle(
        key="news_banner",
        display_name="AryaFeed News ⚡",
        description="Bold yellow/white breaking news banner with [ARYAFEED.IN] pill and high-impact readability",
        base_font_size=74,
        text_color=(255, 255, 255, 255),
        stroke_color=(0, 0, 0, 255),
        stroke_width=6,
        shadow_color=(0, 0, 0, 230),
        shadow_offset=(4, 6),
        vertical_align="lower_center",
        is_uppercase=True,
        box_scrim=False,
        ken_burns="zoom_in",
        fade_seconds=0.4,
        highlight_color=(255, 220, 0, 255),  # AryaFeed Signature Yellow
        brand_badge=True,
        brand_text="ARYAFEED",
        brand_badge_color=(255, 220, 0, 255),
    ),
    "news_card": TemplateStyle(
        key="news_card",
        display_name="AryaFeed Card 📰",
        description="Curiosity news card with sleek dark card container, yellow accent & top brand pill",
        base_font_size=66,
        text_color=(255, 255, 255, 255),
        stroke_color=None,
        stroke_width=0,
        shadow_color=(0, 0, 0, 220),
        shadow_offset=(3, 5),
        vertical_align="lower_center",
        is_uppercase=True,
        quote_marks=False,
        box_scrim=True,
        scrim_color=(12, 12, 12, 215),  # High-contrast premium dark card
        scrim_radius=28,
        scrim_padding=44,
        ken_burns="none",
        fade_seconds=0.3,
        highlight_color=(255, 220, 0, 255),  # AryaFeed Signature Yellow
        brand_badge=True,
        brand_text="ARYAFEED",
        brand_badge_color=(255, 220, 0, 255),
        source_tag=True,
    ),
}


def get_template(key: Optional[str]) -> TemplateStyle:
    """Retrieve template by key or fallback to news_banner."""
    if not key:
        return TEMPLATES["news_banner"]
    return TEMPLATES.get(key.lower(), TEMPLATES["news_banner"])

