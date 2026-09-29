"""FFmpeg video rendering engine for generating 9:16 Instagram Reels."""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from bot.services.text_overlay import create_text_overlay
from bot.templates.styles import TemplateStyle, get_template
from bot.utils.cleanup import safe_remove_file
from bot.utils.config import config
from bot.utils.ffmpeg_check import check_ffmpeg_installed, probe_media

logger = logging.getLogger(__name__)


class VideoEngineError(Exception):
    """Custom exception for video engine rendering failures."""
    pass


def run_ffmpeg_command(cmd: list) -> None:
    """Execute ffmpeg command safely with logging."""
    # Ensure loglevel error is present to prevent massive stderr pipe buffering
    if len(cmd) > 1 and "-loglevel" not in cmd:
        cmd = [cmd[0], "-loglevel", "error"] + cmd[1:]
    logger.info(f"Running ffmpeg: {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        logger.error(f"FFmpeg failed with code {result.returncode}:\n{result.stderr}")
        raise VideoEngineError(f"FFmpeg rendering error: {result.stderr[-400:]}")


def prepare_base_image(image_path: Path, output_path: Path) -> Path:
    """Prepare a crisp 1080x1920 base canvas using Pillow (instant, <10MB RAM)."""
    from PIL import Image, ImageFilter
    cw, ch = 1080, 1920
    with Image.open(image_path) as im:
        im = im.convert("RGB")
        im_ratio = im.width / im.height
        c_ratio = cw / ch
        if abs(im_ratio - c_ratio) < 0.02:
            base = im.resize((cw, ch), Image.Resampling.LANCZOS)
        else:
            # Blurred background + fit foreground (fast downscaled blur)
            bg = im.resize((cw // 4, ch // 4), Image.Resampling.BOX).filter(ImageFilter.GaussianBlur(8)).resize((cw, ch), Image.Resampling.BILINEAR)
            scale = min(cw / im.width, ch / im.height)
            new_w, new_h = max(1, int(im.width * scale)), max(1, int(im.height * scale))
            fg = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
            bg.paste(fg, ((cw - new_w) // 2, (ch - new_h) // 2))
            base = bg
        output_path.parent.mkdir(parents=True, exist_ok=True)
        base.save(output_path, "JPEG", quality=95)
    return output_path


def render_single_pass_image_reel(
    image_path: Path,
    overlay_png_path: Path,
    audio_path: Optional[Path],
    output_path: Path,
    duration: float,
    template: TemplateStyle,
    fps: int = 25,
) -> Path:
    """Render complete 1080x1920 MP4 reel in a SINGLE lightning-fast pass (<80MB RAM)."""
    if not check_ffmpeg_installed():
        raise VideoEngineError("FFmpeg is not installed")

    # Step 1: Composite text overlay directly onto the base image using Pillow (instant, <10MB RAM)
    from PIL import Image
    composited_path = output_path.parent / f"{image_path.stem}_comp.jpg"
    with Image.open(image_path) as base_im, Image.open(overlay_png_path) as ov_im:
        base_rgba = base_im.convert("RGBA")
        ov_rgba = ov_im.convert("RGBA")
        comp = Image.alpha_composite(base_rgba, ov_rgba).convert("RGB")
        comp.save(composited_path, "JPEG", quality=95)

    total_frames = int(duration * fps)
    fade_in_d = 0.8
    fade_out_st = max(0.0, duration - 1.5)
    fade_out_d = 1.5

    # Ken Burns motion expression
    if template.ken_burns == "zoom_in":
        zoom_expr = f"zoompan=z='min(1.0+0.0004*on,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1080x1920:fps={fps}"
    elif template.ken_burns == "zoom_out":
        zoom_expr = f"zoompan=z='if(lte(zoom,1.0),1.12,max(1.001,zoom-0.0004*on))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1080x1920:fps={fps}"
    else:
        zoom_expr = "format=yuv420p"

    has_audio = audio_path and audio_path.exists() and audio_path.stat().st_size > 1000

    # Smooth Fade In from black at start and smooth Fade Out to black at end
    filter_complex = (
        f"[0:v]{zoom_expr},fade=t=in:st=0:d={fade_in_d},fade=t=out:st={fade_out_st}:d={fade_out_d},format=yuv420p[v]"
    )

    if has_audio:
        filter_complex += f";[1:a]volume=0.85,afade=t=in:st=0:d=1.0,afade=t=out:st={fade_out_st}:d={fade_out_d}[a]"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(duration), "-i", str(composited_path),
    ]

    if has_audio:
        cmd.extend(["-ss", "0", "-t", str(duration), "-i", str(audio_path)])
    else:
        cmd.extend(["-f", "lavfi", "-t", str(duration), "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "[a]" if has_audio else "1:a",
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-threads", "1",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        run_ffmpeg_command(cmd)
    finally:
        safe_remove_file(composited_path)
    return output_path


def create_image_reel(
    image_path: Path,
    output_path: Path,
    duration: float,
    template: TemplateStyle,
    fps: int = 25,
) -> Path:
    """Convert static image into 9:16 video with Ken Burns effect (<60MB RAM)."""
    if not check_ffmpeg_installed():
        raise VideoEngineError("FFmpeg is not installed")

    total_frames = int(duration * fps)

    if template.ken_burns == "zoom_in":
        zoom_expr = f"zoompan=z='min(1.0+0.0004*on,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1080x1920:fps={fps}"
    elif template.ken_burns == "zoom_out":
        zoom_expr = f"zoompan=z='if(lte(zoom,1.0),1.12,max(1.001,zoom-0.0004*on))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1080x1920:fps={fps}"
    else:
        zoom_expr = "format=yuv420p"

    prep_img = output_path.parent / f"{image_path.stem}_prep_base.jpg"
    prepare_base_image(image_path, prep_img)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(duration), "-i", str(prep_img),
        "-filter_complex", f"[0:v]{zoom_expr},format=yuv420p[v]",
        "-map", "[v]",
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-threads", "2",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]

    run_ffmpeg_command(cmd)
    return output_path


def process_video_reel(
    video_path: Path,
    output_path: Path,
    max_duration: float = 60.0,
    fps: int = 30,
) -> Path:
    """Format video to vertical 9:16 (1080x1920) with blurred background padding."""
    if not check_ffmpeg_installed():
        raise VideoEngineError("FFmpeg is not installed")

    filter_complex = (
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:25,setsar=1[bg];"
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,setsar=1[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,fps={fps},format=yuv420p[v]"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-t", str(max_duration),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-threads", "2",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]

    run_ffmpeg_command(cmd)
    return output_path


def add_music(
    video_path: Path,
    audio_path: Optional[Path],
    output_path: Path,
    duration: float,
) -> Path:
    """Add, mix, or loop background music to video."""
    video_info = probe_media(video_path)
    has_orig_audio = video_info.get("has_audio", False)

    fade_out_st = max(0.0, duration - 2.0)

    if audio_path and audio_path.exists():
        if has_orig_audio:
            # Duck original audio and mix with background music
            filter_complex = (
                f"[0:a]volume=0.3[orig];"
                f"[1:a]volume=0.75,afade=t=in:st=0:d=2.0,afade=t=out:st={fade_out_st}:d=2.0[bg];"
                f"[orig][bg]amix=inputs=2:duration=first:dropout_transition=2[a]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-stream_loop", "-1", "-i", str(audio_path),
                "-filter_complex", filter_complex,
                "-map", "0:v",
                "-map", "[a]",
                "-t", str(duration),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path),
            ]
        else:
            # No original audio: apply background music directly
            filter_complex = (
                f"[1:a]volume=0.85,afade=t=in:st=0:d=2.0,afade=t=out:st={fade_out_st}:d=2.0[a]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-stream_loop", "-1", "-i", str(audio_path),
                "-filter_complex", filter_complex,
                "-map", "0:v",
                "-map", "[a]",
                "-t", str(duration),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path),
            ]
    else:
        # No background music provided
        if has_orig_audio:
            # Keep original audio
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-t", str(duration),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path),
            ]
        else:
            # Synthesize silent AAC audio track for Instagram compatibility
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t", str(duration),
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path),
            ]

    run_ffmpeg_command(cmd)
    return output_path


def render_final_video(
    video_path: Path,
    overlay_png_path: Path,
    output_path: Path,
    duration: float,
    template: TemplateStyle,
) -> Path:
    fade_in_d = 0.8
    fade_out_st = max(0.0, duration - 1.5)
    fade_out_d = 1.5
    text_fade_out_st = max(0.0, duration - 2.0)

    filter_complex = (
        f"[0:v]fade=t=in:st=0:d={fade_in_d},fade=t=out:st={fade_out_st}:d={fade_out_d}[bg];"
        f"[bg][1:v]overlay=0:0:eof_action=repeat[v]"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(overlay_png_path),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a?",
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-threads", "1",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(output_path),
    ]

    run_ffmpeg_command(cmd)
    return output_path


def render_complete_reel(
    media_path: Path,
    media_type: str,  # 'image' or 'video'
    text: str,
    template_key: str,
    audio_path: Optional[Path],
    output_path: Path,
    temp_dir: Path,
    target_duration: Optional[float] = None,
) -> Path:
    """Unified master rendering pipeline producing optimized 1080x1920 MP4 reel."""
    template = get_template(template_key)

    # 1. Determine duration
    if media_type == "image":
        duration = float(target_duration or config.output_duration_seconds)
    else:
        probe = probe_media(media_path)
        vid_dur = probe.get("duration", 0.0)
        duration = min(60.0, vid_dur) if vid_dur > 0.5 else float(target_duration or config.output_duration_seconds)

    stem = media_path.stem
    overlay_png = temp_dir / f"{stem}_text_overlay.png"

    # Step A: Generate Text Overlay PNG
    create_text_overlay(
        text=text,
        template=template,
        output_png_path=overlay_png,
        font_path=config.font_path,
    )

    # Step B: Fast single-pass rendering for images (<80MB RAM, ~4s runtime)
    if media_type == "image":
        prep_image = temp_dir / f"{stem}_prep.jpg"
        prepare_base_image(media_path, prep_image)
        render_single_pass_image_reel(
            image_path=prep_image,
            overlay_png_path=overlay_png,
            audio_path=audio_path,
            output_path=output_path,
            duration=duration,
            template=template,
        )
        return output_path

    # Step C: Fallback pipeline for uploaded video media
    base_video = temp_dir / f"{stem}_base.mp4"
    audiomixed_video = temp_dir / f"{stem}_with_audio.mp4"

    process_video_reel(
        video_path=media_path,
        output_path=base_video,
        max_duration=duration,
    )

    add_music(
        video_path=base_video,
        audio_path=audio_path,
        output_path=audiomixed_video,
        duration=duration,
    )

    render_final_video(
        video_path=audiomixed_video,
        overlay_png_path=overlay_png,
        output_path=output_path,
        duration=duration,
        template=template,
    )

    return output_path
