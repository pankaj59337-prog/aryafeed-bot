# 🎬 Telegram Reel Maker Bot

An autonomous, self-hosted Telegram bot that creates vertical **9:16 Instagram Reels (1080x1920 MP4, H.264, AAC)** from photos or videos, with styled text overlays across 5 customizable templates, Ken Burns motion, and intelligent background audio ducking.

---

## 🌟 Features

- **📱 True 9:16 Vertical Video (1080x1920)**: Instagram Reels and TikTok compatible.
- **🖼️ Photo & Video Ingestion**:
  - **Photos**: Converts images into 10–15s dynamic reels with smooth Ken Burns zoom/pan and blurred background aspect fitting.
  - **Videos**: Smartly centers or pads horizontal/square videos with blurred margins; preserves aspect ratio without distortion.
- **✍️ Pillow Transparent Overlay System**:
  - Generates transparent 1080x1920 PNG overlays directly with Pillow (avoiding fragile FFmpeg drawtext font escaping).
  - Enforces Instagram Reel safe margins (respects top header and bottom UI icons).
  - Dynamic font size adaptation for long text / quotes.
  - Text stroke, shadows, and clean unicode support.
- **🎨 5 Distinct Built-in Templates**:
  1. **Cinematic 🎬**: White text, subtle dark shadow, lower-center positioning, smooth alpha fade-in/fade-out, slow zoom.
  2. **Meme 😂**: Bold uppercase white text, thick black outline, high-impact readability.
  3. **Romantic 💖**: Warm tone, soft scrim badge, slow gentle zoom, smooth transitions.
  4. **Quote 📜**: Dimmed background scrim card, centered quote marks styling, high contrast.
  5. **Minimal ✨**: Clean modern typography, small uncluttered aesthetic.
- **🎵 Smart Audio Mixing & Ducking**:
  - Automatically loops or trims custom MP3/audio to match video duration.
  - Adds 0.5s audio fade-in and fade-out.
  - Normalizes audio volume.
  - Ducks original video dialogue under background music (or vice versa).
  - Generates silent AAC track if user skips audio, ensuring platform compliance.
- **🛡️ Multi-User & Resilient**:
  - SQLite database persists independent session state per Telegram chat.
  - Handles cancellations (`/cancel`), restarts, and unexpected inputs.
  - Asynchronous non-blocking rendering (`asyncio.to_thread`).
  - Scheduled retention cleanup of temporary and old media files.
- **🔒 Security**:
  - Secret token masking in logs.
  - Optional `ADMIN_TELEGRAM_ID` restriction.

---

## 🚀 Quick Start Guide

### 1. Create Your Telegram Bot with BotFather
1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts to choose a name and username (e.g. `MyReelMakerBot`).
3. BotFather will provide an HTTP API token (e.g. `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`). Copy this token.

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and paste your Telegram bot token:
```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Optional: Restrict bot usage to your own Telegram ID
# (Get your numeric ID from @userinfobot on Telegram)
ADMIN_TELEGRAM_ID=

# File Limits & Rendering Defaults
MAX_VIDEO_SIZE_MB=100
MAX_AUDIO_SIZE_MB=30
OUTPUT_DURATION_SECONDS=15
FONT_PATH=assets/fonts/Roboto-Bold.ttf
CLEANUP_TEMP_FILES=true
OUTPUT_RETENTION_HOURS=24
```

---

## 🐳 Docker Deployment (Recommended for Production)

### Prerequisites
Install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/).

### Starting the Bot
```bash
# Build image and start in background
docker compose up -d
```

### Viewing Logs
```bash
docker compose logs -f
```

### Stopping and Restarting
```bash
# Stop the bot
docker compose stop

# Restart the bot
docker compose restart

# Stop and remove containers (data remains safe in ./data and ./database volumes)
docker compose down
```

### Updating the Bot
```bash
git pull
docker compose build --no-cache
docker compose up -d
```

---

## 💻 Local Installation (Windows & Linux)

### Prerequisites
- **Python 3.10+** (Tested on Python 3.11 & 3.14)
- **FFmpeg & FFprobe** installed and added to system `PATH`
  - **Windows**: Install via `winget install Gyan.FFmpeg` or download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
  - **Linux (Ubuntu/Debian)**: `sudo apt update && sudo apt install -y ffmpeg fonts-dejavu`

### Setup Steps
```bash
# 1. Clone or navigate to the project directory
cd telegram-reel-maker-bot

# 2. (Optional) Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run automated test suite
pytest -v

# 5. Start the bot
python main.py
```

---

## 📱 Bot Commands & User Workflow

| Command | Description |
| :--- | :--- |
| `/start` | Welcomes the user and explains features |
| `/reel` | Begins the step-by-step reel creation workflow |
| `/templates` | Previews the 5 styling templates |
| `/status` | Shows current draft step or active rendering progress |
| `/skip` | Skips background music upload when prompted |
| `/cancel` | Cancels the active draft and clears temporary files |
| `/help` | Complete instructions and tips |

### Creation Workflow
1. User sends `/reel`.
2. Bot prompts: *"Send image or video"*.
3. User uploads image/video $\rightarrow$ Bot replies: `"Media received"`.
4. Bot prompts: *"Send the text you want on the reel"*.
5. User sends text $\rightarrow$ Bot replies: `"Text received"`.
6. Bot prompts: *"Send an MP3/audio file or type /skip"*.
7. User uploads MP3 or sends `/skip` $\rightarrow$ Bot replies: `"Music received"` or `"Music skipped"`.
8. Bot displays interactive buttons for the 5 templates:
   - `1. Cinematic 🎬`
   - `2. Meme 😂`
   - `3. Romantic 💖`
   - `4. Quote 📜`
   - `5. Minimal ✨`
9. User taps a template button $\rightarrow$ Bot replies: `"Rendering your reel..."`.
10. Bot sends rendered 1080x1920 MP4 with caption: `"Reel ready"`.

---

## 🛠️ Common FFmpeg Troubleshooting

1. **`ffmpeg: command not found`**:
   - Ensure FFmpeg binary directory is included in your system's `PATH`. Run `ffmpeg -version` in a terminal to confirm.
2. **Missing Codec (`libx264` or `aac`)**:
   - On Linux, install `ffmpeg` from official package repos. On Windows, use full builds from Gyan.dev.
3. **Out of Memory on Large Videos**:
   - Limit `MAX_VIDEO_SIZE_MB` in `.env` (default is 100 MB).

---

## 🔮 Phase 2: Official Meta / Instagram Graph API Architecture

Phase 1 provides complete Telegram $\rightarrow$ Rendering $\rightarrow$ Telegram delivery.
Phase 2 interfaces are designed in [`bot/services/instagram_service.py`](file:///C:/Users/PANKAJ/.gemini/antigravity/scratch/telegram-reel-maker-bot/bot/services/instagram_service.py) for official Meta Graph API auto-posting without browser automation:

```
+-------------------+      POST /{ig-user-id}/media       +-------------------------+
| Telegram Bot Host | ----------------------------------> | Meta Reels Container API |
|                   |   (media_type=REELS, video_url)     +-------------------------+
|                   |                                                  |
|                   |      GET /{container_id}?fields=status           v
|                   | ----------------------------------> [ Status Check: FINISHED ]
|                   |                                                  |
|                   |      POST /{ig-user-id}/media_publish            v
|                   | ----------------------------------> [ Published to Instagram! ]
+-------------------+
```

### Requirements for Phase 2:
1. Register a Meta Developer App (`Business` type).
2. Connect an Instagram Professional / Business account to a Facebook Page.
3. Grant permissions: `instagram_basic`, `instagram_content_publish`.
4. Host generated reels on a public HTTPS URL (e.g. AWS S3, Cloudflare R2, or reverse proxy) so Meta's servers can ingest the video container.
