"""File cleanup utilities for temporary and retention management."""

import logging
import os
import time
from pathlib import Path
from typing import Union
from bot.utils.config import config

logger = logging.getLogger(__name__)


def safe_remove_file(file_path: Union[str, Path, None]) -> bool:
    """Safely remove a file if it exists."""
    if not file_path:
        return False
    try:
        p = Path(file_path)
        if p.exists() and p.is_file():
            p.unlink()
            logger.debug(f"Removed file: {p}")
            return True
    except Exception as e:
        logger.warning(f"Failed to remove file {file_path}: {e}")
    return False


def clean_temp_files(pattern_or_prefix: str = "") -> int:
    """Clean all temporary rendering files matching prefix in temp_dir."""
    count = 0
    temp_dir = config.temp_dir
    if not temp_dir.exists():
        return count

    for item in temp_dir.iterdir():
        if item.is_file() and (not pattern_or_prefix or pattern_or_prefix in item.name):
            if safe_remove_file(item):
                count += 1
    return count


def cleanup_chat_files(chat_id: int) -> None:
    """Remove temporary files associated with a specific chat ID."""
    prefix = f"{chat_id}_"
    # Clean temp dir
    for f in config.temp_dir.glob(f"{prefix}*"):
        safe_remove_file(f)


def cleanup_expired_outputs(max_age_hours: int = 24) -> int:
    """Remove rendered output videos older than max_age_hours."""
    count = 0
    cutoff = time.time() - (max_age_hours * 3600)
    for f in config.output_dir.iterdir():
        if f.is_file() and f.suffix.lower() == ".mp4":
            try:
                if f.stat().st_mtime < cutoff:
                    if safe_remove_file(f):
                        count += 1
            except Exception as e:
                logger.warning(f"Error checking age of output file {f}: {e}")
    return count
