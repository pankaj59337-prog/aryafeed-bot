"""Unit tests for Instagram Account Integration & Caption Engine."""

import pytest
from pathlib import Path
from bot.services.caption_generator import generate_instagram_caption
from bot.services.instagram_service import instagram_service
from database.db import DatabaseManager


def test_caption_generator_structure():
    hook = "Maine flirt back kar diya na toh ladle tu so nahi payega ????"
    caption = generate_instagram_caption(hook, style="sexy", custom_tag_count=12)
    assert hook in caption
    assert "#" in caption
    assert "?" in caption
    # Verify hashtags exist
    tags = [w for w in caption.split() if w.startswith("#")]
    assert len(tags) >= 10


@pytest.mark.asyncio
async def test_database_instagram_account_flow(tmp_path: Path):
    db_file = tmp_path / "test_insta.db"
    mgr = DatabaseManager(db_file)
    await mgr.init_db()

    # Initial state
    acc = await mgr.get_instagram_account(999)
    assert acc is None

    # Save account
    await mgr.save_instagram_account(999, "creator_test", str(tmp_path / "sess.json"), auto_post=0)
    acc = await mgr.get_instagram_account(999)
    assert acc is not None
    assert acc["username"] == "creator_test"
    assert acc["auto_post"] == 0

    # Toggle autopost
    await mgr.set_instagram_autopost(999, True)
    acc = await mgr.get_instagram_account(999)
    assert acc["auto_post"] == 1

    # Delete account
    await mgr.delete_instagram_account(999)
    acc = await mgr.get_instagram_account(999)
    assert acc is None
