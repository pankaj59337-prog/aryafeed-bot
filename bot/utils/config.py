"""Configuration management for Telegram Reel Maker Bot."""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def mask_token(token: str) -> str:
    """Safely mask Telegram bot token for logging."""
    if not token:
        return "<NOT SET>"
    parts = token.split(":")
    if len(parts) == 2:
        bot_id, secret = parts
        visible = secret[:4] if len(secret) >= 4 else ""
        return f"{bot_id}:{visible}****"
    return token[:4] + "****" if len(token) > 4 else "****"


@dataclass(frozen=True)
class AppConfig:
    bot_token: str
    admin_telegram_id: int | None
    max_video_size_mb: int
    max_audio_size_mb: int
    output_duration_seconds: int
    font_path: Path
    cleanup_temp_files: bool
    output_retention_hours: int

    # Directory layout
    project_root: Path
    data_dir: Path
    input_dir: Path
    audio_dir: Path
    output_dir: Path
    temp_dir: Path
    database_path: Path

    @classmethod
    def load(cls) -> "AppConfig":
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

        admin_id_raw = os.getenv("ADMIN_TELEGRAM_ID", "").strip()
        admin_id = int(admin_id_raw) if admin_id_raw.isdigit() else None

        max_video_mb = int(os.getenv("MAX_VIDEO_SIZE_MB", "100"))
        max_audio_mb = int(os.getenv("MAX_AUDIO_SIZE_MB", "30"))
        duration_sec = int(os.getenv("OUTPUT_DURATION_SECONDS", "15"))

        font_path_str = os.getenv("FONT_PATH", "assets/fonts/Roboto-Bold.ttf").strip()
        font_path = (PROJECT_ROOT / font_path_str) if not Path(font_path_str).is_absolute() else Path(font_path_str)

        cleanup = os.getenv("CLEANUP_TEMP_FILES", "true").lower() in ("true", "1", "yes")
        retention = int(os.getenv("OUTPUT_RETENTION_HOURS", "24"))

        data_dir = PROJECT_ROOT / "data"
        input_dir = data_dir / "input"
        audio_dir = data_dir / "audio"
        output_dir = data_dir / "output"
        temp_dir = data_dir / "temp"
        db_path = PROJECT_ROOT / "database" / "reel_bot.db"

        # Ensure directories exist
        for d in (input_dir, audio_dir, output_dir, temp_dir, db_path.parent):
            d.mkdir(parents=True, exist_ok=True)

        return cls(
            bot_token=bot_token,
            admin_telegram_id=admin_id,
            max_video_size_mb=max_video_mb,
            max_audio_size_mb=max_audio_mb,
            output_duration_seconds=duration_sec,
            font_path=font_path,
            cleanup_temp_files=cleanup,
            output_retention_hours=retention,
            project_root=PROJECT_ROOT,
            data_dir=data_dir,
            input_dir=input_dir,
            audio_dir=audio_dir,
            output_dir=output_dir,
            temp_dir=temp_dir,
            database_path=db_path,
        )

    def is_admin(self, user_id: int) -> bool:
        """Check if user_id is authorized when ADMIN_TELEGRAM_ID is configured."""
        if self.admin_telegram_id is None:
            return True
        return user_id == self.admin_telegram_id

    def __repr__(self) -> str:
        return (
            f"AppConfig("
            f"bot_token='{mask_token(self.bot_token)}', "
            f"admin_id={self.admin_telegram_id}, "
            f"max_video_mb={self.max_video_size_mb}, "
            f"duration={self.output_duration_seconds}s, "
            f"font='{self.font_path.name}')"
        )


# Global singleton instance
config = AppConfig.load()
