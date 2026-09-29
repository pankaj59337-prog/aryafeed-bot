"""Unit tests for Autonomous AI Text & Visual Generation Engine."""

from pathlib import Path
from PIL import Image
import pytest

from bot.services.ai_image_engine import create_aesthetic_gradient_canvas
from bot.services.ai_text_engine import generate_viral_text
from bot.templates.styles import TEMPLATES, get_template


def test_ai_text_generation_all_styles():
    """Verify viral text is generated cleanly for all 6 styles."""
    styles = ["sexy", "cinematic", "meme", "romantic", "quote", "minimal"]
    for s in styles:
        text = generate_viral_text(s)
        assert text is not None
        assert len(text.strip()) > 3
        assert s in TEMPLATES


def test_sexy_template_style_parameters():
    """Verify 'sexy' template style is configured with high-contrast parameters."""
    style = get_template("sexy")
    assert style.key == "sexy"
    assert style.box_scrim is False
    assert style.base_font_size >= 60


def test_aesthetic_canvas_dimensions(tmp_path: Path):
    """Verify generated canvas is precisely 1080x1920."""
    canvas_path = tmp_path / "test_canvas.jpg"
    res = create_aesthetic_gradient_canvas("sexy", canvas_path)
    assert res.exists()
    with Image.open(res) as img:
        assert img.size == (1080, 1920)
        assert img.mode == "RGB"
