"""Pillow-based transparent PNG text overlay generator."""

import logging
import re
from pathlib import Path
from typing import List, Optional, Set, Tuple
from PIL import Image, ImageDraw, ImageFont

try:
    from pilmoji import Pilmoji
    import emoji
    HAS_PILMOJI = True
except ImportError:
    HAS_PILMOJI = False
    emoji = None

from bot.templates.styles import TemplateStyle, get_template
from bot.utils.config import config

logger = logging.getLogger(__name__)

# Reel canvas dimensions
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920

# Safe zone boundaries (Instagram Reel UI margins)
SAFE_MARGIN_X = 90
SAFE_MARGIN_TOP = 220
SAFE_MARGIN_BOTTOM = 320
USABLE_WIDTH = CANVAS_WIDTH - (SAFE_MARGIN_X * 2)
USABLE_HEIGHT = CANVAS_HEIGHT - SAFE_MARGIN_TOP - SAFE_MARGIN_BOTTOM

# Core emotional and impact keywords for automatic aesthetic highlighting
HIGHLIGHT_KEYWORDS: Set[str] = {
    # Hindi / Urdu emotional keywords
    "dil", "ishq", "pyar", "pyaar", "mohabbat", "rooh", "khwab", "khwaab", "nasha",
    "nigahein", "aankhon", "aankhein", "haseen", "khoobsurat", "chaahat", "intezaar",
    "judaai", "ehsaas", "kareeb", "saansein", "dhadkan", "sanam", "pagal", "jaan",
    "zindagi", "khushi", "wafaa", "sukoon", "shiddat", "junoon", "ibaadat", "ibadat", "duaa",
    "khuda", "deewana", "deewani", "muskurahat", "tasveer", "yaad", "yaadein",
    "baatein", "lamha", "lamhe", "khamoshi", "raat", "chaand", "chand", "sitaron",
    "saadgi", "shringar", "dosti", "rishta", "darling",
    # English emotional, hot baddie & bestie keywords
    "love", "forever", "vibe", "magic", "dream", "eyes", "heart", "soul", "queen", "queens",
    "cutie", "sexy", "hot", "beautiful", "gorgeous", "special", "obsessed",
    "bestie", "besties", "baddie", "savage", "attitude", "favorite", "drama", "unbreakable",
    "unbothered", "champagne", "standard", "glam", "aesthetic", "goals", "chaos",
    "prize", "crush", "storm", "friends", "friend", "sister", "unhinged",
    # Viral News, Cricket, Exam & Culture keywords (AryaFeed Engine)
    "crore", "crores", "lakh", "lakhs", "arrested", "cracked", "exam", "won", "wins",
    "world", "record", "viral", "police", "gold", "shocking", "historic", "scam",
    "trophy", "champion", "ipl", "bcci", "india", "isro", "scandal", "unbelievable",
    "secret", "hero", "shameful", "justice", "truth", "revealed", "cctv", "caught",
    "ias", "ips", "upsc", "neet", "jee", "billionaire", "richest", "shocker",
}


def extract_highlight_targets(raw_text: str) -> Tuple[str, Set[str]]:
    """Extract explicit words in *asterisks* or detect key emotional keywords for accent highlighting."""
    raw_matches = re.findall(r"\*([^*]+)\*", raw_text)
    explicit_matches = set()
    for m in raw_matches:
        for w in m.split():
            clean_w = re.sub(r'^[^\w]+|[^\w]+$', '', w).lower()
            if clean_w:
                explicit_matches.add(clean_w)

    clean_text = re.sub(r"\*([^*]+)\*", r"\1", raw_text)

    if explicit_matches:
        return clean_text, explicit_matches

    # Auto-detect up to 2 emotional words if no explicit marks
    auto_matches: Set[str] = set()
    count = 0
    words = re.findall(r"[a-zA-Z]+", clean_text)
    for w in words:
        if w.lower() in HIGHLIGHT_KEYWORDS and count < 2:
            auto_matches.add(w.lower())
            count += 1

    return clean_text, auto_matches


def load_font(font_path: Path, size: int) -> ImageFont.FreeTypeFont:
    """Load TrueType font with fallbacks."""
    try:
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size)
    except Exception as e:
        logger.warning(f"Could not load font {font_path}: {e}")

    # Fallback to system fonts or default
    fallbacks = [
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fb in fallbacks:
        p = Path(fb)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                continue

    return ImageFont.load_default()


def extract_source_tag(raw_text: str) -> Tuple[str, Optional[str]]:
    """Extract source citation like [Per NDTV] or 'Per Hindustan Times' if present."""
    m = re.match(r"^\[?(Per\s+[A-Za-z0-9\s]+|Source:\s*[A-Za-z0-9\s]+)\]?\s*[:-]?\s*", raw_text, re.IGNORECASE)
    if m:
        source = m.group(1).strip("[] ")
        rest = raw_text[m.end():].strip()
        return rest, source
    return raw_text, None


def draw_brand_watermark(
    canvas: Image.Image,
    brand: str = ">> aryafeed.in",
    font_path: Optional[Path] = None,
    position: str = "top",
    bg_color: Tuple[int, int, int, int] = (255, 220, 0, 255),
    text_color: Tuple[int, int, int, int] = (10, 10, 10, 255),
    source_text: Optional[str] = None,
) -> None:
    """Draw signature [ >> aryafeed.in ] brand title watermark badge on canvas."""
    draw = ImageDraw.Draw(canvas)
    brand_raw = brand.strip()
    if not brand_raw:
        return

    if font_path is None:
        font_path = config.font_path

    # Check if this is the signature AryaFeed brand title
    is_aryafeed = "aryafeed" in brand_raw.lower()

    if is_aryafeed:
        # Signature '>> aryafeed.in' title styling requested by user
        badge_font_size = 38
        badge_font = load_font(font_path, badge_font_size)

        p1 = ">> "
        p2 = "aryafeed."
        p3 = "in"

        c_red = (235, 35, 35, 255)
        c_white = (255, 255, 255, 255)

        w1 = draw.textlength(p1, font=badge_font)
        w2 = draw.textlength(p2, font=badge_font)
        w3 = draw.textlength(p3, font=badge_font)
        total_w = int(w1 + w2 + w3)
        total_h = 42

        pad_x = 24
        pad_y = 10
        badge_w = total_w + (pad_x * 2)
        badge_h = total_h + (pad_y * 2)
        radius = 16

        if position == "top":
            badge_x = (CANVAS_WIDTH - badge_w) // 2
            badge_y = SAFE_MARGIN_TOP + 15
        elif position == "top_left":
            badge_x = SAFE_MARGIN_X
            badge_y = SAFE_MARGIN_TOP + 15
        elif position == "bottom_right":
            badge_x = CANVAS_WIDTH - SAFE_MARGIN_X - badge_w
            badge_y = CANVAS_HEIGHT - SAFE_MARGIN_BOTTOM - badge_h - 10
        else:  # bottom
            badge_x = (CANVAS_WIDTH - badge_w) // 2
            badge_y = CANVAS_HEIGHT - SAFE_MARGIN_BOTTOM - badge_h - 15

        # Zero Black Background: Draw clean floating text with crisp drop shadow
        tx = badge_x
        ty = badge_y

        # Soft drop shadow on text only (NO black box/pill!)
        for dx, dy in [(2, 2), (3, 3)]:
            draw.text((tx + dx, ty + dy), p1, font=badge_font, fill=(0, 0, 0, 220))
            draw.text((tx + w1 + dx, ty + dy), p2, font=badge_font, fill=(0, 0, 0, 220))
            draw.text((tx + w1 + w2 + dx, ty + dy), p3, font=badge_font, fill=(0, 0, 0, 220))

        # Vibrant colored text with thin protective dark stroke
        draw.text((tx, ty), p1, font=badge_font, fill=c_red, stroke_width=2, stroke_fill=(10, 10, 10, 220))
        draw.text((tx + w1, ty), p2, font=badge_font, fill=c_white, stroke_width=2, stroke_fill=(10, 10, 10, 220))
        draw.text((tx + w1 + w2, ty), p3, font=badge_font, fill=c_red, stroke_width=2, stroke_fill=(10, 10, 10, 220))

    else:
        badge_font_size = 36
        badge_font = load_font(font_path, badge_font_size)
        bbox = draw.textbbox((0, 0), brand_raw.upper(), font=badge_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        pad_x = 28
        pad_y = 10
        badge_w = tw + (pad_x * 2)
        badge_h = th + (pad_y * 2)
        radius = 16

        if position == "top":
            badge_x = (CANVAS_WIDTH - badge_w) // 2
            badge_y = SAFE_MARGIN_TOP + 20
        elif position == "top_left":
            badge_x = SAFE_MARGIN_X
            badge_y = SAFE_MARGIN_TOP + 20
        else:  # bottom
            badge_x = (CANVAS_WIDTH - badge_w) // 2
            badge_y = CANVAS_HEIGHT - SAFE_MARGIN_BOTTOM - badge_h - 20

        draw.rounded_rectangle(
            (badge_x - 1, badge_y + 4, badge_x + badge_w + 1, badge_y + badge_h + 5),
            radius=radius,
            fill=(0, 0, 0, 160),
        )
        draw.rounded_rectangle(
            (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h),
            radius=radius,
            fill=bg_color,
        )
        draw.text((badge_x + pad_x - bbox[0], badge_y + pad_y - bbox[1]), brand_raw.upper(), font=badge_font, fill=text_color)

    # 4. Optional source citation badge (e.g. "Per NDTV")
    if source_text:
        src_clean = source_text.strip().upper()
        src_font_size = 28
        src_font = load_font(font_path, src_font_size)
        s_bbox = draw.textbbox((0, 0), src_clean, font=src_font)
        s_tw = s_bbox[2] - s_bbox[0]
        s_th = s_bbox[3] - s_bbox[1]
        s_pad_x = 18
        s_pad_y = 6
        s_w = s_tw + (s_pad_x * 2)
        s_h = s_th + (s_pad_y * 2)
        s_x = (CANVAS_WIDTH - s_w) // 2
        s_y = badge_y + badge_h + 12

        # Translucent dark pill for source
        draw.rounded_rectangle(
            (s_x, s_y, s_x + s_w, s_y + s_h),
            radius=12,
            fill=(20, 20, 20, 190),
        )
        draw.text((s_x + s_pad_x - s_bbox[0], s_y + s_pad_y - s_bbox[1]), src_clean, font=src_font, fill=(230, 230, 230, 240))


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Wrap text so every line fits within max_width."""
    lines: List[str] = []
    paragraphs = text.split("\n")

    for para in paragraphs:
        words = para.strip().split()
        if not words:
            lines.append("")
            continue

        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]

            if line_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    # Single word exceeds max_width: break it character by character
                    sub_word = ""
                    for char in word:
                        if draw.textbbox((0, 0), sub_word + char, font=font)[2] <= max_width:
                            sub_word += char
                        else:
                            if sub_word:
                                lines.append(sub_word)
                            sub_word = char
                    if sub_word:
                        current_line = [sub_word]

        if current_line:
            lines.append(" ".join(current_line))

    return lines


def calculate_text_layout(
    text: str,
    font_path: Path,
    base_size: int,
    max_width: int,
    max_height: int,
) -> Tuple[ImageFont.ImageFont, List[str], int, int, int]:
    """Adaptively scale font size to guarantee text fits within safe bounds."""
    dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy_img)

    size = base_size
    min_size = 28

    while size >= min_size:
        font = load_font(font_path, size)
        lines = wrap_text(text, font, max_width, draw)

        line_heights = []
        line_widths = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_widths.append(bbox[2] - bbox[0])
            line_heights.append(bbox[3] - bbox[1])

        line_spacing = int(size * 0.35)
        max_line_h = max(line_heights) if line_heights else size
        total_h = (len(lines) * max_line_h) + (max(0, len(lines) - 1) * line_spacing)
        max_w = max(line_widths) if line_widths else 0

        if total_h <= max_height and max_w <= max_width:
            return font, lines, max_w, total_h, line_spacing

        size -= 4

    # Minimum size reached, return current layout
    font = load_font(font_path, min_size)
    lines = wrap_text(text, font, max_width, draw)
    line_spacing = int(min_size * 0.3)
    max_line_h = min_size
    total_h = (len(lines) * max_line_h) + (max(0, len(lines) - 1) * line_spacing)
    return font, lines, max_width, total_h, line_spacing


def create_text_overlay(
    text: str,
    template: TemplateStyle,
    output_png_path: Path,
    font_path: Optional[Path] = None,
    brand: Optional[str] = None,
) -> Path:
    """Generate 1080x1920 transparent PNG with styled, wrapped text."""
    if font_path is None:
        font_path = config.font_path

    # Extract source citation if present (e.g. [Per NDTV] or 'Per Hindustan Times')
    clean_raw, source_tag = extract_source_tag(text.strip())

    # Extract highlighted words (*asterisks* or auto-detected emotional/news keywords)
    clean_text, target_highlights = extract_highlight_targets(clean_raw)

    # Pre-process text according to template
    if template.is_uppercase:
        clean_text = clean_text.upper()
        target_highlights = set(h.upper() for h in target_highlights)
    if template.quote_marks and not (clean_text.startswith('"') or clean_text.startswith('“')):
        clean_text = f"“{clean_text}”"

    # Create transparent canvas
    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Draw Brand Watermark Pill if requested by template or explicit brand parameter
    should_badge = (brand is not None) or getattr(template, "brand_badge", False)
    if should_badge and template.key != "news_banner":
        brand_name = brand or getattr(template, "brand_text", ">> aryafeed.in")
        badge_bg = getattr(template, "brand_badge_color", (255, 220, 0, 255))
        draw_brand_watermark(
            canvas=canvas,
            brand=brand_name,
            font_path=font_path,
            position="top",
            bg_color=badge_bg,
            source_text=source_tag,
        )

    # Adapt layout
    font, lines, text_w, text_h, line_spacing = calculate_text_layout(
        clean_text,
        font_path,
        template.base_font_size,
        USABLE_WIDTH,
        USABLE_HEIGHT,
    )

    # Determine Y start position based on vertical alignment
    if template.vertical_align == "top":
        start_y = SAFE_MARGIN_TOP + 40
    elif template.vertical_align == "bottom":
        start_y = CANVAS_HEIGHT - SAFE_MARGIN_BOTTOM - text_h - 40
    elif template.vertical_align == "lower_center":
        # Cinematic lower-third / subtitle position (approx 62% down)
        target_center = int(CANVAS_HEIGHT * 0.62)
        start_y = target_center - (text_h // 2)
        start_y = min(start_y, CANVAS_HEIGHT - SAFE_MARGIN_BOTTOM - text_h)
    else:  # "center"
        start_y = SAFE_MARGIN_TOP + (USABLE_HEIGHT - text_h) // 2

    # Draw background scrim card if requested
    if template.box_scrim and lines:
        pad = template.scrim_padding
        card_x0 = max(SAFE_MARGIN_X // 2, ((CANVAS_WIDTH - text_w) // 2) - pad)
        card_y0 = max(SAFE_MARGIN_TOP // 2, start_y - pad)
        card_x1 = min(CANVAS_WIDTH - (SAFE_MARGIN_X // 2), ((CANVAS_WIDTH + text_w) // 2) + pad)
        card_y1 = min(CANVAS_HEIGHT - (SAFE_MARGIN_BOTTOM // 2), start_y + text_h + pad)

        draw.rounded_rectangle(
            (card_x0, card_y0, card_x1, card_y1),
            radius=template.scrim_radius,
            fill=template.scrim_color,
        )

    target_highlights_lower = set(h.lower() for h in target_highlights)

    # Render each line with shadow and stroke
    current_y = start_y
    for line in lines:
        if not line:
            current_y += line_spacing + 20
            continue

        words = line.split(" ")
        space_w = draw.textlength(" ", font=font)

        # Measure each word width using Pilmoji if available
        word_widths = []
        for w in words:
            try:
                if HAS_PILMOJI:
                    with Pilmoji(canvas) as p_draw:
                        ww = p_draw.getsize(w, font=font)[0]
                else:
                    ww = draw.textlength(w, font=font)
            except Exception:
                ww = draw.textlength(w, font=font)
            word_widths.append(ww)

        line_w = sum(word_widths) + (space_w * max(0, len(words) - 1))
        line_x = int((CANVAS_WIDTH - line_w) // 2)

        # 1. Drop shadow (render on text without duplicating full-color emoji icons)
        if template.shadow_color and template.shadow_offset != (0, 0):
            sx, sy = template.shadow_offset
            shad_x = line_x
            for w, ww in zip(words, word_widths):
                shadow_text = emoji.replace_emoji(w, replace=" ") if (emoji and HAS_PILMOJI) else w
                for dx, dy in [(sx, sy), (sx + 1, sy + 1)]:
                    draw.text(
                        (shad_x + dx, current_y + dy),
                        shadow_text,
                        font=font,
                        fill=template.shadow_color,
                    )
                shad_x += ww + space_w

        # 2. Main text with stroke outline, emoji support, and highlight color
        rendered_with_pilmoji = False
        if HAS_PILMOJI:
            try:
                with Pilmoji(canvas) as p_draw:
                    text_x = line_x
                    for w, ww in zip(words, word_widths):
                        clean_w = re.sub(r'^[^\w]+|[^\w]+$', '', w).lower()
                        is_hl = clean_w in target_highlights_lower
                        w_color = template.highlight_color if is_hl else template.text_color
                        p_draw.text(
                            (text_x, current_y),
                            w,
                            font=font,
                            fill=w_color,
                            stroke_width=template.stroke_width,
                            stroke_fill=template.stroke_color if template.stroke_color else (0, 0, 0, 0),
                        )
                        text_x += ww + space_w
                rendered_with_pilmoji = True
            except Exception as e:
                logger.warning(f"Pilmoji render failed for line '{line}': {e}")

        if not rendered_with_pilmoji:
            # Fallback: strip emojis to avoid missing-glyph cross boxes (⯐)
            text_x = line_x
            for w, ww in zip(words, word_widths):
                clean_w = re.sub(r'^[^\w]+|[^\w]+$', '', w).lower()
                is_hl = clean_w in target_highlights_lower
                w_color = template.highlight_color if is_hl else template.text_color
                fallback_w = emoji.replace_emoji(w, replace="").strip() if emoji else w
                draw.text(
                    (text_x, current_y),
                    fallback_w,
                    font=font,
                    fill=w_color,
                    stroke_width=template.stroke_width,
                    stroke_fill=template.stroke_color if template.stroke_color else (0, 0, 0, 0),
                )
                text_x += ww + space_w

        bbox = draw.textbbox((0, 0), line, font=font)
        line_h = bbox[3] - bbox[1]
        current_y += line_h + line_spacing

    # Always ensure signature '>> aryafeed.in' title watermark is stamped on news templates
    if template.key in ("news_banner", "news_card") or should_badge:
        draw_brand_watermark(
            canvas=canvas,
            brand=">> aryafeed.in",
            font_path=font_path,
            position="bottom_right",
        )

    # Save PNG
    output_png_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(output_png_path), format="PNG")
    logger.info(f"Generated text overlay at {output_png_path}")
    return output_png_path


def generate_preview_composite(
    image_path: Path,
    text: str,
    template_key: str,
    output_path: Path,
) -> Path:
    """Composite text overlay directly on top of candid image to produce a 1080x1920 preview."""
    temp_overlay = output_path.parent / f"temp_overlay_{output_path.stem}.png"
    template = get_template(template_key)
    create_text_overlay(text, template, temp_overlay)

    with Image.open(image_path) as raw_img:
        raw_img = raw_img.convert("RGBA")
        img_w, img_h = raw_img.size

        # Perfectly cover 1080x1920 with crisp Lanczos scaling - ZERO blur
        scale = max(CANVAS_WIDTH / img_w, CANVAS_HEIGHT / img_h)
        new_w = max(CANVAS_WIDTH, int(img_w * scale + 0.5))
        new_h = max(CANVAS_HEIGHT, int(img_h * scale + 0.5))
        resized = raw_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        left = max(0, (new_w - CANVAS_WIDTH) // 2)
        top = int((new_h - CANVAS_HEIGHT) * 0.22) if new_h > CANVAS_HEIGHT else 0
        top = max(0, min(top, new_h - CANVAS_HEIGHT))

        bg = resized.crop((left, top, left + CANVAS_WIDTH, top + CANVAS_HEIGHT))

        with Image.open(temp_overlay) as txt_img:
            composite = Image.alpha_composite(bg, txt_img.convert("RGBA"))

        final_rgb = composite.convert("RGB")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_rgb.save(str(output_path), format="JPEG", quality=95)

    try:
        temp_overlay.unlink(missing_ok=True)
    except Exception:
        pass

    logger.info(f"Generated visual text preview composite at {output_path}")
    return output_path

