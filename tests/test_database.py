"""Unit tests for SQLite user session management."""

from pathlib import Path
import pytest
from database.db import DatabaseManager


@pytest.mark.asyncio
async def test_session_lifecycle(tmp_path: Path):
    """Test session creation, updating, retrieval, and resetting."""
    db_file = tmp_path / "test_sessions.db"
    mgr = DatabaseManager(db_file)
    await mgr.init_db()

    chat_id = 123456789

    # Initially None
    session = await mgr.get_session(chat_id)
    assert session is None

    # Start session
    await mgr.start_reel_session(chat_id)
    session = await mgr.get_session(chat_id)
    assert session is not None
    assert session["current_step"] == "WAITING_MEDIA"
    assert session["telegram_chat_id"] == chat_id

    # Update media
    await mgr.update_session(
        chat_id,
        current_step="WAITING_TEXT",
        media_path="/path/to/image.jpg",
        media_type="image",
    )
    session = await mgr.get_session(chat_id)
    assert session["current_step"] == "WAITING_TEXT"
    assert session["media_path"] == "/path/to/image.jpg"
    assert session["media_type"] == "image"

    # Update text and template
    await mgr.update_session(
        chat_id,
        overlay_text="Hello World",
        selected_template="cinematic",
    )
    session = await mgr.get_session(chat_id)
    assert session["overlay_text"] == "Hello World"
    assert session["selected_template"] == "cinematic"

    # Reset
    await mgr.reset_session(chat_id)
    session = await mgr.get_session(chat_id)
    assert session["current_step"] == "IDLE"
    assert session["media_path"] is None


@pytest.mark.asyncio
async def test_testing_mode_toggle(tmp_path: Path):
    """Test testing mode default and toggling in database."""
    db_file = tmp_path / "test_settings.db"
    mgr = DatabaseManager(db_file)
    await mgr.init_db()

    # Default is False (Production mode)
    is_testing = await mgr.is_testing_mode()
    assert is_testing is False

    # Toggle to True
    await mgr.set_testing_mode(True)
    assert await mgr.is_testing_mode() is True

    # Toggle back to False
    await mgr.set_testing_mode(False)
    assert await mgr.is_testing_mode() is False
