"""End-to-end integration tests for FFmpeg video and audio rendering pipeline."""

import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
import pytest

from bot.services.video_engine import (
    add_music,
    create_image_reel,
    process_video_reel,
    render_complete_reel,
    render_final_video,
)
from bot.templates.styles import TEMPLATES
from bot.utils.ffmpeg_check import probe_media


@pytest.fixture(scope="module")
def sample_media(tmp_path_factory):
    """Generate synthetic image, video, and audio assets for testing."""
    media_dir = tmp_path_factory.mktemp("sample_assets")

    # 1. Sample Image (800x600 landscape to test smart aspect ratio padding)
    img_path = media_dir / "sample_image.jpg"
    img = Image.new("RGB", (800, 600), color=(52, 152, 219))
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 700, 500], fill=(231, 76, 60))
    img.save(str(img_path))

    # 2. Sample Audio (3 second sine wave MP3)
    audio_path = media_dir / "sample_audio.mp3"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:a", "libmp3lame",
        str(audio_path)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # 3. Sample Video (3 second 640x360 16:9 video with audio)
    video_path = media_dir / "sample_video.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=3:size=640x360:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=880:duration=3",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(video_path)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    return {
        "image": img_path,
        "audio": audio_path,
        "video": video_path,
        "temp_dir": media_dir / "temp",
    }


def test_image_reel_complete_workflow(sample_media, tmp_path: Path):
    """Test full image reel generation and inspect output metadata with ffprobe."""
    output_mp4 = tmp_path / "final_image_reel.mp4"
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    render_complete_reel(
        media_path=sample_media["image"],
        media_type="image",
        text="Never give up on your dreams. The best is yet to come.",
        template_key="cinematic",
        audio_path=sample_media["audio"],
        output_path=output_mp4,
        temp_dir=temp_dir,
        target_duration=3.0,  # Fast 3-second test
    )

    assert output_mp4.exists()
    assert output_mp4.stat().st_size > 10000

    # Inspect with ffprobe
    meta = probe_media(output_mp4)
    assert meta["has_video"] is True
    assert meta["has_audio"] is True
    assert meta["width"] == 1080
    assert meta["height"] == 1920
    assert meta["video_codec"] == "h264"
    assert meta["audio_codec"] == "aac"
    assert meta["duration"] >= 2.5


def test_video_reel_complete_workflow(sample_media, tmp_path: Path):
    """Test full video reel generation with audio ducking and inspect output."""
    output_mp4 = tmp_path / "final_video_reel.mp4"
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    render_complete_reel(
        media_path=sample_media["video"],
        media_type="video",
        text="WHEN YOU FINALLY FIX THAT ONE BUG 😂",
        template_key="meme",
        audio_path=sample_media["audio"],
        output_path=output_mp4,
        temp_dir=temp_dir,
        target_duration=3.0,
    )

    assert output_mp4.exists()
    meta = probe_media(output_mp4)
    assert meta["has_video"] is True
    assert meta["has_audio"] is True
    assert meta["width"] == 1080
    assert meta["height"] == 1920
    assert meta["video_codec"] == "h264"
    assert meta["audio_codec"] == "aac"


def test_skip_music_silent_audio_generation(sample_media, tmp_path: Path):
    """Verify reels generated without music contain valid silent AAC stream for Instagram."""
    output_mp4 = tmp_path / "final_silent_reel.mp4"
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    render_complete_reel(
        media_path=sample_media["image"],
        media_type="image",
        text="Minimalism is not a lack of something. It's simply the perfect amount.",
        template_key="minimal",
        audio_path=None,  # Music skipped!
        output_path=output_mp4,
        temp_dir=temp_dir,
        target_duration=2.0,
    )

    assert output_mp4.exists()
    meta = probe_media(output_mp4)
    assert meta["has_audio"] is True
    assert meta["audio_codec"] == "aac"
    assert meta["width"] == 1080
    assert meta["height"] == 1920


def test_all_five_templates(sample_media, tmp_path: Path):
    """Verify rendering executes across all 5 template styles."""
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    for template_name in ["cinematic", "meme", "romantic", "quote", "minimal"]:
        out = tmp_path / f"reel_{template_name}.mp4"
        render_complete_reel(
            media_path=sample_media["image"],
            media_type="image",
            text=f"Template showcase: {template_name.upper()}",
            template_key=template_name,
            audio_path=sample_media["audio"],
            output_path=out,
            temp_dir=temp_dir,
            target_duration=2.0,
        )
        assert out.exists()
        meta = probe_media(out)
        assert meta["width"] == 1080
        assert meta["height"] == 1920
