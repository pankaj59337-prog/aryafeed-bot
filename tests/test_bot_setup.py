"""Unit tests for bot startup and configuration validation."""

import os
import pytest
from bot.utils.config import AppConfig, mask_token
from bot.utils.ffmpeg_check import check_ffmpeg_installed, check_ffprobe_installed


def test_token_masking():
    """Verify bot token is masked properly in logs and representations."""
    token = "123456789:ABCdefGhIjkLmNoPqRsTuVwXyZ"
    masked = mask_token(token)
    assert "123456789:ABCd****" in masked
    assert "GhIjkLmNoPqRsTuVwXyZ" not in masked


def test_ffmpeg_environment_checks():
    """Verify FFmpeg and FFprobe binaries are present in test environment."""
    assert check_ffmpeg_installed() is True
    assert check_ffprobe_installed() is True


def test_config_loader():
    """Verify configuration loading with default values."""
    config = AppConfig.load()
    assert config.max_video_size_mb >= 10
    assert config.max_audio_size_mb >= 5
    assert config.output_duration_seconds >= 5
    assert config.font_path.exists()
