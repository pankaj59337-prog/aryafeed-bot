"""FFmpeg and FFprobe utility checks and media inspection."""

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def check_ffmpeg_installed() -> bool:
    """Check if ffmpeg executable exists in PATH."""
    return shutil.which("ffmpeg") is not None


def check_ffprobe_installed() -> bool:
    """Check if ffprobe executable exists in PATH."""
    return shutil.which("ffprobe") is not None


def get_ffmpeg_version() -> str:
    """Return version string of installed ffmpeg."""
    try:
        res = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return res.stdout.splitlines()[0] if res.stdout else "Unknown"
    except Exception as e:
        logger.error(f"Error checking ffmpeg version: {e}")
        return "Not available"


def probe_media(file_path: Path) -> Dict[str, Any]:
    """Inspect media file using ffprobe and return metadata."""
    if not check_ffprobe_installed():
        raise RuntimeError("ffprobe is not installed or not in PATH")

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(res.stdout)
    except Exception as e:
        logger.error(f"ffprobe failed for {file_path}: {e}")
        raise RuntimeError(f"Failed to probe media file: {e}")

    streams = data.get("streams", [])
    format_info = data.get("format", {})

    has_video = False
    has_audio = False
    width = 0
    height = 0
    video_codec = ""
    audio_codec = ""
    duration = 0.0

    for s in streams:
        codec_type = s.get("codec_type")
        if codec_type == "video" and not has_video:
            has_video = True
            width = int(s.get("width", 0))
            height = int(s.get("height", 0))
            video_codec = s.get("codec_name", "")
            if "duration" in s:
                try:
                    duration = max(duration, float(s["duration"]))
                except (ValueError, TypeError):
                    pass
        elif codec_type == "audio" and not has_audio:
            has_audio = True
            audio_codec = s.get("codec_name", "")
            if "duration" in s:
                try:
                    duration = max(duration, float(s["duration"]))
                except (ValueError, TypeError):
                    pass

    if duration == 0.0 and "duration" in format_info:
        try:
            duration = float(format_info["duration"])
        except (ValueError, TypeError):
            pass

    return {
        "has_video": has_video,
        "has_audio": has_audio,
        "width": width,
        "height": height,
        "video_codec": video_codec,
        "audio_codec": audio_codec,
        "duration": duration,
        "format_name": format_info.get("format_name", ""),
        "size_bytes": int(format_info.get("size", 0)),
    }
