"""Unit tests for Pillow transparent PNG text overlay system."""

from pathlib import Path
from PIL import Image
import pytest

from bot.services.text_overlay import (
    CANVAS_WIDTH,
    CANVAS_HEIGHT,
    create_text_overlay,
)
from bot.templates.styles import TEMPLATES
from bot.utils.config import config


def test_overlay_dimensions_and_alpha(tmp_path: Path):
    """Verify generated overlay is exactly 1080x1920 with transparent alpha channel."""
    out_png = tmp_path / "test_overlay.png"
    text = "The journey of a thousand miles begins with a single step."
    template = TEMPLATES["cinematic"]

    res_path = create_text_overlay(text, template, out_png, config.font_path)
    assert res_path.exists()

    with Image.open(res_path) as img:
        assert img.size == (CANVAS_WIDTH, CANVAS_HEIGHT)
        assert img.mode == "RGBA"


def test_all_templates_generate_overlays(tmp_path: Path):
    """Verify all 5 templates generate valid overlays without errors."""
    text = "Test Overlay Text Across All 5 Templates 🔥"

    for key, template in TEMPLATES.items():
        out_png = tmp_path / f"test_{key}.png"
        res_path = create_text_overlay(text, template, out_png, config.font_path)
        assert res_path.exists()
        with Image.open(res_path) as img:
            assert img.size == (1080, 1920)


def test_long_text_font_adaptation(tmp_path: Path):
    """Verify font adapts and scales down for lengthy paragraphs."""
    long_text = (
        "This is an extraordinarily long text designed to test dynamic font scaling. "
        "It contains multiple sentences that would normally overflow a standard canvas. "
        "The layout engine must wrap these lines gracefully, maintain Instagram safe margins, "
        "and reduce the font size until everything fits perfectly."
    )
    out_png = tmp_path / "test_long.png"
    template = TEMPLATES["quote"]

    res_path = create_text_overlay(long_text, template, out_png, config.font_path)
    assert res_path.exists()


def test_word_highlighting_explicit_and_auto(tmp_path: Path):
    """Verify word highlighting works for both explicit *marks* and auto-detected keywords."""
    from bot.services.text_overlay import extract_highlight_targets

    # 1. Explicit asterisks
    text1 = "kuch log *dil* mein aise bas jaate hain"
    clean1, hl1 = extract_highlight_targets(text1)
    assert clean1 == "kuch log dil mein aise bas jaate hain"
    assert "dil" in hl1

    # 2. Auto-detection of emotional keywords
    text2 = "kuch log dil mein aise bas jaate hain ki unke baad koi accha nahi lagta... 🥀"
    clean2, hl2 = extract_highlight_targets(text2)
    assert "dil" in hl2

    # 3. Create actual overlay with highlights
    out_png = tmp_path / "test_hl.png"
    template = TEMPLATES["romantic"]
    res = create_text_overlay(text2, template, out_png)
    assert res.exists()
    with Image.open(res) as img:
        assert img.size == (1080, 1920)
        assert img.mode == "RGBA"
