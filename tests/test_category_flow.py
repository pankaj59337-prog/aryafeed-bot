"""Unit tests for Category-First dynamic filtering, image preview generation, and song name resolution."""

from pathlib import Path
import pytest
from bot.handlers.auto import (
    CATEGORIES,
    ALL_IMAGE_OPTIONS,
    ALL_HOOK_OPTIONS,
    get_fresh_image_options,
    get_fresh_song_options,
    get_fresh_hook_options,
    build_category_selection_keyboard,
    build_image_selection_keyboard,
    build_song_selection_keyboard,
    build_hook_selection_keyboard,
)
from bot.services.music_service import music_service
from bot.services.text_overlay import generate_preview_composite
from database.db import db_manager


@pytest.mark.asyncio
async def test_category_options_coverage():
    """Verify all categories exist and have sufficient assets."""
    assert len(CATEGORIES) >= 8
    for cat in ["sexy", "baddie", "bestie", "romantic", "cinematic", "traditional", "broken", "aesthetic"]:
        assert cat in CATEGORIES
        cat_info = CATEGORIES[cat]
        assert "title" in cat_info
        assert "icon" in cat_info


@pytest.mark.asyncio
async def test_category_dynamic_filtering():
    """Verify category-specific filtering returns 5 items for all categories."""
    chat_id = 999888777
    await db_manager.clear_used_assets(chat_id)

    for cat in ["sexy", "baddie", "bestie", "romantic", "cinematic", "traditional", "broken", "aesthetic"]:
        images = await get_fresh_image_options(chat_id, category=cat, limit=5)
        assert len(images) == 5, f"Category {cat} should have 5 image options"

        songs = await get_fresh_song_options(chat_id, category=cat, limit=5)
        assert len(songs) == 5, f"Category {cat} should have 5 vocal song options"

        hooks = await get_fresh_hook_options(chat_id, category=cat, limit=5)
        assert len(hooks) == 5, f"Category {cat} should have 5 hook options"


@pytest.mark.asyncio
async def test_category_keyboards_structure():
    """Verify keyboard structures include navigation and shuffle buttons."""
    cat_kb = build_category_selection_keyboard()
    flat_cat = [btn.callback_data for row in cat_kb.inline_keyboard for btn in row]
    assert "cat_sexy" in flat_cat
    assert "cat_baddie" in flat_cat
    assert "cat_bestie" in flat_cat
    assert "cat_romantic" in flat_cat
    assert "cat_cinematic" in flat_cat
    assert "cat_traditional" in flat_cat
    assert "cat_broken" in flat_cat
    assert "cat_aesthetic" in flat_cat

    # Image keyboard
    sample_imgs = ALL_IMAGE_OPTIONS[:5]
    img_kb = build_image_selection_keyboard(sample_imgs, category="sexy")
    flat_img = [btn.callback_data for row in img_kb.inline_keyboard for btn in row]
    assert "shuffle_imgs" in flat_img
    assert "back_to_cats" in flat_img
    assert "pick_img_random" in flat_img
    assert f"pick_img_{sample_imgs[0]['id']}" in flat_img

    # Hook keyboard (Step 2: leads back to images)
    sample_hooks = ALL_HOOK_OPTIONS[:5]
    hook_kb = build_hook_selection_keyboard(sample_hooks, category="sexy")
    flat_hook = [btn.callback_data for row in hook_kb.inline_keyboard for btn in row]
    assert "shuffle_hooks" in flat_hook
    assert "back_to_imgs" in flat_hook
    assert "pick_hook_custom" in flat_hook
    assert "pick_hook_0" in flat_hook

    # Song keyboard (Step 3: leads back to hooks)
    sample_songs = await get_fresh_song_options(999888777, category="sexy", limit=5)
    song_kb = build_song_selection_keyboard(sample_songs, category="sexy")
    flat_song = [btn.callback_data for row in song_kb.inline_keyboard for btn in row]
    assert "shuffle_songs" in flat_song
    assert "back_to_hooks" in flat_song
    assert "pick_song_random" in flat_song


@pytest.mark.asyncio
async def test_category_used_history_deduplication():
    """Verify used assets are excluded from options in subsequent rounds."""
    chat_id = 999111222
    await db_manager.clear_used_assets(chat_id)

    cat = "sexy"
    round1_imgs = await get_fresh_image_options(chat_id, category=cat, limit=5)
    chosen_img = round1_imgs[0]["id"]
    await db_manager.record_used_asset(chat_id, "image", chosen_img)

    round1_songs = await get_fresh_song_options(chat_id, category=cat, limit=5)
    chosen_song = round1_songs[0]["id"]
    await db_manager.record_used_asset(chat_id, "music", chosen_song)

    round1_hooks = await get_fresh_hook_options(chat_id, category=cat, limit=5)
    chosen_hook = round1_hooks[0]["text"]
    await db_manager.record_used_asset(chat_id, "text", chosen_hook)

    # Next round should not contain the recorded items
    round2_imgs = await get_fresh_image_options(chat_id, category=cat, limit=5)
    assert chosen_img not in [img["id"] for img in round2_imgs]

    round2_songs = await get_fresh_song_options(chat_id, category=cat, limit=5)
    assert chosen_song not in [s["id"] for s in round2_songs]

    round2_hooks = await get_fresh_hook_options(chat_id, category=cat, limit=5)
    assert chosen_hook not in [h["text"] for h in round2_hooks]


def test_preview_image_composite_generation(tmp_path: Path):
    """Verify generate_preview_composite creates a valid 1080x1920 image."""
    base_img = Path("assets/images/candid/sheer_saree_mirror_selfie.jpg")
    output_preview = tmp_path / "test_preview.jpg"

    res = generate_preview_composite(
        image_path=base_img,
        text="meri aankhon mein doob jane ka mann karta hai... 🖤",
        template_key="sexy",
        output_path=output_preview,
    )

    assert res.exists()
    assert res.stat().st_size > 50000  # High res JPEG


def test_resolve_song_by_name():
    """Verify song name resolution matches user queries accurately."""
    # Exact / partial title
    p1, name1 = music_service.resolve_song_by_name("Pee Loon")
    assert "Pee Loon" in name1
    assert p1.exists()

    p2, name2 = music_service.resolve_song_by_name("kesariya")
    assert "Kesariya" in name2
    assert p2.exists()

    p3, name3 = music_service.resolve_song_by_name("zara sa kk")
    assert "Zara Sa" in name3
    assert p3.exists()

    p4, name4 = music_service.resolve_song_by_name("tum hi ho arijit")
    assert "Tum Hi Ho" in name4
    assert p4.exists()
