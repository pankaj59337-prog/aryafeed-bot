"""Unit tests for the AutoPilot Daily Scheduler."""

import pytest
from bot.services.autopilot import (
    DAILY_SLOTS,
    IST,
    DEFAULT_ADMIN_CHAT_ID,
    init_autopilot_db,
    is_autopilot_active,
    set_autopilot_status,
    get_active_subscribers,
)


def test_daily_slots_configuration():
    """Verify all 8 curated daily posting slots are correctly configured."""
    assert len(DAILY_SLOTS) == 8

    # Check that all 8 categories exist in DAILY_SLOTS
    expected_categories = {
        "aesthetic", "bestie", "traditional", "broken",
        "romantic", "baddie", "sexy", "cinematic"
    }
    configured_categories = {s["category"] for s in DAILY_SLOTS}
    assert configured_categories == expected_categories

    for slot in DAILY_SLOTS:
        assert "delivery_time_str" in slot
        assert "target_post_time_str" in slot
        assert 0 <= slot["hour"] <= 23
        assert 0 <= slot["minute"] <= 59


@pytest.mark.asyncio
async def test_autopilot_subscription_db():
    """Verify DB settings for autopilot can be read, toggled, and retrieved."""
    test_chat_id = 999333444

    await init_autopilot_db()

    # Default admin is active
    admin_active = await is_autopilot_active(DEFAULT_ADMIN_CHAT_ID)
    assert admin_active is True

    # Toggle on for test chat
    await set_autopilot_status(test_chat_id, True)
    assert await is_autopilot_active(test_chat_id) is True

    subs = await get_active_subscribers()
    assert test_chat_id in subs
    assert DEFAULT_ADMIN_CHAT_ID in subs

    # Toggle off
    await set_autopilot_status(test_chat_id, False)
    assert await is_autopilot_active(test_chat_id) is False
    subs_after = await get_active_subscribers()
    assert test_chat_id not in subs_after
