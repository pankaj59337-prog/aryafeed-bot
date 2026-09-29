import asyncio
from pathlib import Path
from telegram import Bot
from telegram.request import HTTPXRequest

async def main():
    token = "8963056930:AAFgtXdrKY3Y4tEkgC4_ecJgefs82fd8tRI"
    chat_id = 5381201341
    video_path = Path("data/output/fixed_ai_reel.mp4")

    req = HTTPXRequest(connect_timeout=30.0, read_timeout=180.0, write_timeout=180.0)
    bot = Bot(token=token, request=req)

    caption = (
        "🔥 Fixed Reel with Authentic Selfie & Perfect Text Wrapping!\n\n"
        "• Realistic Photo: Natural candid smartphone mirror selfie (No plastic AI look)\n"
        "• Text Wrapping: Properly wrapped into 3 compact lines (Max width 661px - Zero clipping!)\n"
        "• iOS Typography: Authentic Apple SF Pro font + Apple iOS emojis (🌚💋)\n"
        "• Synced Motion: 10% smooth linear zoom & synchronized soft fade-in/fade-out\n\n"
        "Hook: \"Ghar pe sab so rahe hain... aur mera dimaag tumhari shararaton me uljha hua hai 🌚💋\""
    )

    print(f"Sending video ({video_path.stat().st_size} bytes) to chat {chat_id}...")
    with open(video_path, "rb") as f:
        msg = await bot.send_video(
            chat_id=chat_id,
            video=f,
            caption=caption,
            supports_streaming=True,
            width=1080,
            height=1920,
        )
    print("Fixed reel sent to Telegram! Message ID:", msg.message_id)

if __name__ == "__main__":
    asyncio.run(main())
