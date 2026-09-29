"""Tests for zero-repeat image guarantee and dynamic visual generation."""

from pathlib import Path
from PIL import Image
import pytest

from bot.handlers.auto import (
    ALL_IMAGE_OPTIONS,
    get_fresh_image_options,
    build_image_selection_keyboard,
)
from bot.services.ai_image_engine import (
    generate_ai_candid_image,
    fetch_pinterest_candid_image,
    generate_unique_film_graded_image,
)
from database.db import db_manager


@pytest.mark.asyncio
async def test_zero_repeat_across_consecutive_runs():
    chat_id = 888777666
    await db_manager.clear_used_assets(chat_id)

    seen_ids = set()
    cat = "cinematic"

    for _ in range(5):
        opts = await get_fresh_image_options(chat_id, category=cat, limit=5)
        assert len(opts) == 5

        for opt in opts:
            assert opt["id"] not in seen_ids, f"Image {opt['id']} was repeated!"

        chosen = opts[0]["id"]
        seen_ids.add(chosen)
        await db_manager.record_used_asset(chat_id, "image", chosen)


@pytest.mark.asyncio
async def test_zero_repeat_when_all_catalog_images_exhausted():
    chat_id = 555444333
    await db_manager.clear_used_assets(chat_id)

    for opt in ALL_IMAGE_OPTIONS:
        await db_manager.record_used_asset(chat_id, "image", opt["id"])

    fresh = await get_fresh_image_options(chat_id, category="sexy", limit=5)
    assert len(fresh) == 5
    catalog_ids = {opt["id"] for opt in ALL_IMAGE_OPTIONS}
    for item in fresh:
        assert item["id"] not in catalog_ids, f"Item {item['id']} was recycled!"
        assert item["id"].startswith("dyn_ai_")


def test_ai_candid_image_generation(tmp_path: Path):
    out_file, unique_id, title = generate_ai_candid_image("sexy", 12345, output_dir=tmp_path)
    assert out_file.exists()
    assert unique_id.startswith("ai_gen_sexy_")
    assert len(title) > 0
    with Image.open(out_file) as im:
        assert im.size == (1080, 1920)


def test_pinterest_candid_image_fetch(tmp_path: Path):
    out_file, unique_id, title = fetch_pinterest_candid_image("romantic", 12345, output_dir=tmp_path)
    assert out_file.exists()
    assert unique_id.startswith("pin_")
    assert len(title) > 0
    with Image.open(out_file) as im:
        assert im.size == (1080, 1920)


def test_keyboard_contains_new_action_buttons():
    kb = build_image_selection_keyboard(ALL_IMAGE_OPTIONS[:5], category="sexy")
    callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "gen_ai_photo" in callbacks
    assert "fetch_pin_photo" in callbacks
    assert "reset_my_history" in callbacks
    assert "upload_own_img" in callbacks
