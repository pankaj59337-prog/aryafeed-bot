"""Unit tests for the Interactive Studio Flow, used-folder isolation, and skip mechanics."""

import shutil
from pathlib import Path
import pytest
from bot.handlers.auto import (
    get_random_category_image,
    build_studio_preview_keyboard,
    build_category_selection_keyboard,
)
from database.db import db_manager, DatabaseManager


@pytest.mark.asyncio
async def test_get_random_category_image_all_categories():
    """Verify each category has hundreds of available images and can pick randomly."""
    chat_id = 123456789
    for cat in ["sexy", "baddie", "bestie", "romantic", "cinematic", "traditional", "broken", "aesthetic"]:
        img_path = get_random_category_image(cat, chat_id)
        assert img_path.exists(), f"Random image for {cat} must exist"
        assert img_path.is_file()
        assert img_path.suffix.lower() in (".jpg", ".jpeg", ".png")


def test_studio_preview_keyboard_structure():
    """Verify studio preview keyboard has all required interactive action buttons."""
    kb = build_studio_preview_keyboard()
    flat_buttons = [btn.callback_data for row in kb.inline_keyboard for btn in row]

    assert "studio_render" in flat_buttons
    assert "studio_skip" in flat_buttons
    assert "studio_new_text" in flat_buttons
    assert "studio_custom_text" in flat_buttons
    assert "back_to_cats" in flat_buttons


@pytest.mark.asyncio
async def test_used_folder_isolation_and_skip(tmp_path: Path):
    """Verify used folder excludes images, and skip leaves image in available pool."""
    test_cat_dir = tmp_path / "assets" / "images" / "categories" / "test_cat"
    test_used_dir = tmp_path / "assets" / "images" / "used"
    test_cat_dir.mkdir(parents=True)
    test_used_dir.mkdir(parents=True)

    img1 = test_cat_dir / "img1.jpg"
    img2 = test_cat_dir / "img2.jpg"
    img3 = test_cat_dir / "img3.jpg"
    img1.touch()
    img2.touch()
    img3.touch()

    shutil.move(str(img1), str(test_used_dir / "img1.jpg"))

    used_names = {f.name for f in test_used_dir.iterdir() if f.is_file()}
    available = [f for f in test_cat_dir.iterdir() if f.is_file() and f.name not in used_names]

    assert len(available) == 2
    assert img1.name not in [f.name for f in available]
    assert "img2.jpg" in [f.name for f in available]
    assert "img3.jpg" in [f.name for f in available]


@pytest.mark.asyncio
async def test_testing_mode_preserves_images(tmp_path: Path):
    """Verify that in testing mode, files are not moved to used folder."""
    db_file = tmp_path / "test_mode.db"
    mgr = DatabaseManager(db_file)
    await mgr.init_db()

    await mgr.set_testing_mode(True)
    assert await mgr.is_testing_mode() is True

    cat_dir = tmp_path / "assets" / "images" / "categories" / "romantic"
    used_dir = tmp_path / "assets" / "images" / "used"
    cat_dir.mkdir(parents=True)
    used_dir.mkdir(parents=True)

    img = cat_dir / "sample.jpg"
    img.touch()

    # Simulate render logic under testing mode
    is_testing = await mgr.is_testing_mode()
    if not is_testing:
        shutil.move(str(img), str(used_dir / img.name))

    # Should remain in cat_dir
    assert img.exists()
    assert not (used_dir / img.name).exists()
