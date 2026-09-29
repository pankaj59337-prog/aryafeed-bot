"""test_aryafeed_integration.py
End-to-End Test Suite for AryaFeed.in Multi-Account Engine & News Banner Templates.
"""

import asyncio
import os
import sys
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from bot.templates.styles import TEMPLATES, get_template
from bot.services.text_overlay import create_text_overlay, generate_preview_composite, draw_brand_watermark, extract_source_tag
from bot.services.instagram_service import instagram_service
from bot.services.caption_generator import generate_instagram_caption
from bot.utils.config import config
from database.db import db_manager


async def test_multi_account_manager():
    print("--- 1. Testing Database & Multi-Account Manager ---")
    await db_manager.init_db()
    chat_id = 5381201341

    accounts = await instagram_service.list_accounts(chat_id)
    print(f"Total managed accounts for chat {chat_id}: {len(accounts)}")
    for acc in accounts:
        status = "ACTIVE" if acc.get("is_active") else "INACTIVE"
        print(f"  • [{status}] @{acc.get('username')} (Alias: {acc.get('alias')}, Engine: {acc.get('engine_type')})")

    assert len(accounts) >= 2, "Expected at least 2 accounts (night and arya)"

    # Test switching to arya
    print("\nSwitching to 'arya' (@aryafeed.in)...")
    switched_arya = await instagram_service.switch_account(chat_id, "arya")
    assert switched_arya is not None, "Failed to switch to arya"
    assert switched_arya["username"] == "aryafeed.in", f"Expected aryafeed.in, got {switched_arya['username']}"
    assert switched_arya["is_active"] == 1

    active = await instagram_service.get_active_account(chat_id)
    print(f"Current active account: @{active['username']} ({active['alias']})")
    assert active["alias"] == "arya"

    # Test switching back to night
    print("\nSwitching back to 'night' (@night_thought_12)...")
    switched_night = await instagram_service.switch_account(chat_id, "night")
    assert switched_night is not None, "Failed to switch to night"
    assert switched_night["username"] == "night_thought_12"
    assert switched_night["is_active"] == 1

    active = await instagram_service.get_active_account(chat_id)
    print(f"Current active account: @{active['username']} ({active['alias']})")
    assert active["alias"] == "night"
    print("Multi-account switching verified 100%!\n")


def test_news_templates_and_watermark():
    print("--- 2. Testing AryaFeed Templates & Watermark Badge ---")
    assert "news_banner" in TEMPLATES, "news_banner template missing from TEMPLATES"
    assert "news_card" in TEMPLATES, "news_card template missing from TEMPLATES"

    banner_tmpl = get_template("news_banner")
    card_tmpl = get_template("news_card")

    assert banner_tmpl.brand_badge is True
    assert banner_tmpl.brand_text == "ARYAFEED.IN"
    assert card_tmpl.brand_badge is True

    print(f"news_banner: display_name='{banner_tmpl.display_name}', font_size={banner_tmpl.base_font_size}, is_uppercase={banner_tmpl.is_uppercase}")
    print(f"news_card: display_name='{card_tmpl.display_name}', box_scrim={card_tmpl.box_scrim}")

    # Test source tag extraction
    raw1 = "[Per NDTV] 22 FRIENDS STUDIED TOGETHER, *21 CRACKED* THE EXAM"
    clean1, src1 = extract_source_tag(raw1)
    assert src1 == "Per NDTV", f"Expected 'Per NDTV', got '{src1}'"
    print(f"Extracted source: '{src1}', clean: '{clean1}'")

    raw2 = "Source: Hindustan Times - Historic Gold won by India"
    clean2, src2 = extract_source_tag(raw2)
    assert src2 == "Source: Hindustan Times", f"Expected 'Source: Hindustan Times', got '{src2}'"
    print(f"Extracted source: '{src2}', clean: '{clean2}'")

    # Generate transparent overlay PNG for news_banner
    test_out_dir = PROJECT_ROOT / "data" / "temp"
    test_out_dir.mkdir(parents=True, exist_ok=True)
    banner_png = test_out_dir / "test_aryafeed_banner_overlay.png"

    print("\nRendering AryaFeed News Banner overlay...")
    create_text_overlay(
        text="22 FRIENDS STUDIED TOGETHER, *21 CRACKED* THE EXAM 🥹🎓",
        template=banner_tmpl,
        output_png_path=banner_png,
    )
    assert banner_png.exists(), "Banner overlay PNG was not created"
    with Image.open(banner_png) as img:
        assert img.size == (1080, 1920), f"Expected 1080x1920, got {img.size}"
        print(f"Banner overlay generated successfully! Size: {img.size}, Mode: {img.mode}")

    # Generate transparent overlay PNG for news_card with source
    card_png = test_out_dir / "test_aryafeed_card_overlay.png"
    print("\nRendering AryaFeed News Card overlay with source citation...")
    create_text_overlay(
        text="[Per NDTV] TEA VENDOR'S DAUGHTER CRACKS *UPSC EXAM* IN FIRST ATTEMPT 🇮🇳✨",
        template=card_tmpl,
        output_png_path=card_png,
    )
    assert card_png.exists(), "Card overlay PNG was not created"
    with Image.open(card_png) as img:
        assert img.size == (1080, 1920)
        print(f"Card overlay generated successfully! Size: {img.size}")

    # Composite over a sample image to produce visual preview
    sample_img = PROJECT_ROOT / "assets" / "images" / "categories" / "cinematic" / "269.jpg"
    if not sample_img.exists():
        # Fallback to any available jpg
        any_jpg = list(PROJECT_ROOT.glob("assets/images/categories/**/*.jpg"))
        sample_img = any_jpg[0] if any_jpg else None

    if sample_img and sample_img.exists():
        preview_jpg = test_out_dir / "test_aryafeed_news_preview.jpg"
        print(f"\nGenerating full 1080x1920 preview with background {sample_img.name}...")
        generate_preview_composite(
            image_path=sample_img,
            text="22 FRIENDS STUDIED TOGETHER, *21 CRACKED* THE EXAM 🥹🎓",
            template_key="news_banner",
            output_path=preview_jpg,
        )
        assert preview_jpg.exists(), "Preview JPG was not created"
        print(f"Preview composite saved at {preview_jpg} ({round(preview_jpg.stat().st_size/1024, 1)} KB)")

        # Also generate news_card preview
        card_preview_jpg = test_out_dir / "test_aryafeed_card_preview.jpg"
        generate_preview_composite(
            image_path=sample_img,
            text="[Per NDTV] TEA VENDOR'S DAUGHTER CRACKS *UPSC EXAM* IN FIRST ATTEMPT 🇮🇳✨",
            template_key="news_card",
            output_path=card_preview_jpg,
        )
        assert card_preview_jpg.exists()
        print(f"Card preview saved at {card_preview_jpg} ({round(card_preview_jpg.stat().st_size/1024, 1)} KB)")

    print("Templates & Watermark badge verified 100%!\n")


def test_caption_generator():
    print("--- 3. Testing AryaFeed Caption Generator ---")
    hook = "22 FRIENDS STUDIED TOGETHER, 21 CRACKED THE EXAM 🥹🎓"
    caption = generate_instagram_caption(hook, style="news_banner")
    print("Generated AryaFeed Caption:\n" + "-"*40)
    print(caption)
    print("-"*40)

    assert "What are your thoughts on this? Tell us in the comments 👇" in caption
    assert "#aryafeed" in caption
    assert "#trendingnews" in caption
    print("AryaFeed caption generation verified 100%!\n")


def test_video_reel_rendering():
    print("--- 4. Testing End-to-End Video Reel Rendering (FFmpeg) ---")
    from bot.services.video_engine import render_complete_reel
    from bot.services.music_service import music_service

    test_out_dir = PROJECT_ROOT / "data" / "temp"
    video_out = test_out_dir / "test_aryafeed_rendered_reel.mp4"
    if video_out.exists():
        video_out.unlink()

    sample_img = PROJECT_ROOT / "assets" / "images" / "categories" / "cinematic" / "269.jpg"
    audio_path = PROJECT_ROOT / "assets" / "music" / "bollywood" / "agar_tum_saath_ho_vocal.mp3"

    print("Rendering 5.0s test MP4 with 'news_banner' template...")
    final_video = render_complete_reel(
        media_path=sample_img,
        media_type="image",
        text="22 FRIENDS STUDIED TOGETHER, *21 CRACKED* THE EXAM 🥹🎓",
        template_key="news_banner",
        audio_path=audio_path,
        output_path=video_out,
        temp_dir=test_out_dir,
        target_duration=5.0,
    )
    assert final_video.exists(), "Rendered MP4 file does not exist"
    size_mb = round(final_video.stat().st_size / (1024 * 1024), 2)
    print(f"Video rendered successfully! Output: {final_video.name}, Size: {size_mb} MB")


async def main():
    await test_multi_account_manager()
    test_news_templates_and_watermark()
    test_caption_generator()
    test_video_reel_rendering()
    print("🎉 ALL ARYAFEED INTEGRATION TESTS PASSED PERFECTLY!")


if __name__ == "__main__":
    asyncio.run(main())
