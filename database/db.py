"""SQLite database management for Telegram Reel Maker Bot user sessions."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiosqlite

from bot.utils.config import config

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    telegram_chat_id INTEGER PRIMARY KEY,
    current_step TEXT NOT NULL DEFAULT 'IDLE',
    media_path TEXT,
    media_type TEXT,
    overlay_text TEXT,
    music_path TEXT,
    selected_template TEXT,
    output_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS instagram_accounts (
    telegram_chat_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    session_file TEXT NOT NULL,
    auto_post INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS used_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_chat_id INTEGER NOT NULL,
    asset_type TEXT NOT NULL,
    asset_identifier TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_used_history ON used_history(telegram_chat_id, asset_type);

CREATE TABLE IF NOT EXISTS bot_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS synced_instagram_audio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audio_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    artist TEXT,
    file_path TEXT NOT NULL,
    media_pk TEXT,
    source TEXT DEFAULT 'instagram',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_synced_audio ON synced_instagram_audio(audio_id);

CREATE TABLE IF NOT EXISTS managed_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_chat_id INTEGER NOT NULL,
    alias TEXT NOT NULL,
    username TEXT NOT NULL,
    engine_type TEXT DEFAULT 'news',
    session_file TEXT,
    graph_account_id TEXT,
    graph_token TEXT,
    auto_post INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(telegram_chat_id, alias)
);
CREATE INDEX IF NOT EXISTS idx_managed_accounts ON managed_accounts(telegram_chat_id, alias);
"""


class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    async def init_db(self) -> None:
        """Initialize SQLite database tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(CREATE_TABLE_SQL)
            # Default to production mode (testing_mode = 0)
            await db.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('testing_mode', '0');")
            # Auto-seed existing session file if present
            session_file = Path("data/sessions/instagram_5381201341.json")
            if session_file.exists():
                await db.execute("""
                    INSERT OR REPLACE INTO instagram_accounts (
                        telegram_chat_id, username, session_file, auto_post
                    ) VALUES (5381201341, 'night_thought_12', 'data/sessions/instagram_5381201341.json', 1);
                """)

            # Seed Managed Accounts for user 5381201341 (AryaFeed Default)
            now = datetime.now(timezone.utc).isoformat()
            # Engine 1: @aryafeed.in (AryaFeed Media / Viral News - Active)
            await db.execute("""
                INSERT OR IGNORE INTO managed_accounts (
                    telegram_chat_id, alias, username, engine_type, session_file, auto_post, is_active, created_at, updated_at
                ) VALUES (
                    5381201341, 'arya', 'aryafeed.in', 'news', 'data/sessions/instagram_aryafeed.json', 0, 1, ?, ?
                );
            """, (now, now))

            # Engine 2: @night_thought_12 (Aesthetic Autopilot)
            await db.execute("""
                INSERT OR IGNORE INTO managed_accounts (
                    telegram_chat_id, alias, username, engine_type, session_file, auto_post, is_active, created_at, updated_at
                ) VALUES (
                    5381201341, 'night', 'night_thought_12', 'aesthetic', 'data/sessions/instagram_5381201341.json', 1, 0, ?, ?
                );
            """, (now, now))

            # Ensure arya is marked active
            async with db.execute("SELECT 1 FROM managed_accounts WHERE telegram_chat_id = 5381201341 AND is_active = 1") as cur:
                if not await cur.fetchone():
                    await db.execute("UPDATE managed_accounts SET is_active = 1 WHERE telegram_chat_id = 5381201341 AND alias = 'arya'")


            await db.commit()
            logger.info(f"Database initialized at {self.db_path} with Dual-Engine accounts")

    async def get_session(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve the active session dictionary for a specific Telegram chat ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM sessions WHERE telegram_chat_id = ?",
                (chat_id,),
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def start_reel_session(self, chat_id: int) -> None:
        """Start or reset a session into WAITING_MEDIA step."""
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO sessions (
                    telegram_chat_id, current_step, media_path, media_type,
                    overlay_text, music_path, selected_template, output_path,
                    created_at, updated_at
                ) VALUES (?, 'WAITING_MEDIA', NULL, NULL, NULL, NULL, NULL, NULL, ?, ?)
                ON CONFLICT(telegram_chat_id) DO UPDATE SET
                    current_step='WAITING_MEDIA',
                    media_path=NULL,
                    media_type=NULL,
                    overlay_text=NULL,
                    music_path=NULL,
                    selected_template=NULL,
                    output_path=NULL,
                    updated_at=excluded.updated_at;
                """,
                (chat_id, now, now),
            )
            await db.commit()

    async def update_session(self, chat_id: int, **kwargs: Any) -> None:
        """Update arbitrary columns for a user's session."""
        if not kwargs:
            return

        kwargs["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [chat_id]

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE sessions SET {set_clause} WHERE telegram_chat_id = ?",
                values,
            )
            await db.commit()

    async def reset_session(self, chat_id: int) -> None:
        """Reset session to IDLE state."""
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE sessions SET
                    current_step='IDLE',
                    media_path=NULL,
                    media_type=NULL,
                    overlay_text=NULL,
                    music_path=NULL,
                    selected_template=NULL,
                    output_path=NULL,
                    updated_at=?
                WHERE telegram_chat_id = ?
                """,
                (now, chat_id),
            )
            await db.commit()

    async def save_instagram_account(
        self,
        chat_id: int,
        username: str,
        session_file: str,
        auto_post: int = 0,
    ) -> None:
        """Save or update an authenticated Instagram account session."""
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO instagram_accounts (
                    telegram_chat_id, username, session_file, auto_post, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_chat_id) DO UPDATE SET
                    username=excluded.username,
                    session_file=excluded.session_file,
                    auto_post=excluded.auto_post,
                    updated_at=excluded.updated_at;
                """,
                (chat_id, username, session_file, auto_post, now, now),
            )
            await db.commit()

    async def get_instagram_account(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve Instagram account details for a chat ID (delegates to active managed account)."""
        active = await self.get_active_account(chat_id)
        if active:
            return active
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM instagram_accounts WHERE telegram_chat_id = ?",
                (chat_id,),
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def list_managed_accounts(self, chat_id: int) -> List[Dict[str, Any]]:
        """List all configured Instagram accounts for this chat."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM managed_accounts WHERE telegram_chat_id = ? ORDER BY id ASC",
                (chat_id,),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_active_account(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve the currently active Instagram account for this chat."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM managed_accounts WHERE telegram_chat_id = ? AND is_active = 1 LIMIT 1",
                (chat_id,),
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)

            # Fallback: first account in managed_accounts
            cursor = await db.execute(
                "SELECT * FROM managed_accounts WHERE telegram_chat_id = ? ORDER BY id ASC LIMIT 1",
                (chat_id,),
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)

            # Fallback: legacy instagram_accounts table
            cursor = await db.execute(
                "SELECT * FROM instagram_accounts WHERE telegram_chat_id = ?",
                (chat_id,),
            )
            row = await cursor.fetchone()
            if row:
                d = dict(row)
                d["alias"] = "night"
                d["engine_type"] = "aesthetic"
                d["is_active"] = 1
                return d
            return None

    async def switch_active_account(self, chat_id: int, target: str) -> Optional[Dict[str, Any]]:
        """Switch active account by alias or username (e.g. 'night', 'arya', 'aryafeed.in')."""
        t = target.lower().strip().lstrip("@")
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM managed_accounts 
                WHERE telegram_chat_id = ? AND (LOWER(alias) = ? OR LOWER(username) = ? OR LOWER(alias) LIKE ?)
                LIMIT 1
                """,
                (chat_id, t, t, f"{t}%"),
            )
            match = await cursor.fetchone()
            if not match:
                return None

            matched_dict = dict(match)
            matched_alias = matched_dict["alias"]

            # Set all to inactive then activate target
            await db.execute(
                "UPDATE managed_accounts SET is_active = 0 WHERE telegram_chat_id = ?",
                (chat_id,),
            )
            await db.execute(
                "UPDATE managed_accounts SET is_active = 1 WHERE telegram_chat_id = ? AND alias = ?",
                (chat_id, matched_alias),
            )
            # Sync to legacy table for backward compatibility
            await db.execute(
                """
                INSERT OR REPLACE INTO instagram_accounts (
                    telegram_chat_id, username, session_file, auto_post
                ) VALUES (?, ?, ?, ?)
                """,
                (chat_id, matched_dict["username"], matched_dict.get("session_file") or "", matched_dict.get("auto_post", 0)),
            )
            await db.commit()
            matched_dict["is_active"] = 1
            return matched_dict

    async def save_managed_account(
        self,
        chat_id: int,
        alias: str,
        username: str,
        session_file: Optional[str] = None,
        graph_account_id: Optional[str] = None,
        graph_token: Optional[str] = None,
        auto_post: int = 0,
        engine_type: str = "news",
        set_active: bool = False,
    ) -> None:
        """Create or update a managed Instagram account."""
        now = datetime.now(timezone.utc).isoformat()
        clean_alias = alias.lower().strip()
        clean_user = username.strip().lstrip("@")
        async with aiosqlite.connect(self.db_path) as db:
            if set_active:
                await db.execute("UPDATE managed_accounts SET is_active = 0 WHERE telegram_chat_id = ?", (chat_id,))

            await db.execute(
                """
                INSERT INTO managed_accounts (
                    telegram_chat_id, alias, username, engine_type, session_file,
                    graph_account_id, graph_token, auto_post, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_chat_id, alias) DO UPDATE SET
                    username=excluded.username,
                    engine_type=excluded.engine_type,
                    session_file=COALESCE(excluded.session_file, managed_accounts.session_file),
                    graph_account_id=COALESCE(excluded.graph_account_id, managed_accounts.graph_account_id),
                    graph_token=COALESCE(excluded.graph_token, managed_accounts.graph_token),
                    auto_post=excluded.auto_post,
                    is_active=CASE WHEN ? = 1 THEN 1 ELSE managed_accounts.is_active END,
                    updated_at=excluded.updated_at;
                """,
                (
                    chat_id, clean_alias, clean_user, engine_type, session_file,
                    graph_account_id, graph_token, auto_post, 1 if set_active else 0,
                    now, now, 1 if set_active else 0
                ),
            )
            await db.commit()

    async def set_instagram_autopost(self, chat_id: int, auto_post: bool) -> None:
        """Toggle auto_post flag for a user's Instagram account."""
        now = datetime.now(timezone.utc).isoformat()
        val = 1 if auto_post else 0
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE instagram_accounts SET auto_post = ?, updated_at = ? WHERE telegram_chat_id = ?",
                (val, now, chat_id),
            )
            await db.commit()

    async def delete_instagram_account(self, chat_id: int) -> None:
        """Disconnect and delete Instagram account record for a chat ID."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM instagram_accounts WHERE telegram_chat_id = ?",
                (chat_id,),
            )
            await db.commit()

    async def record_used_asset(self, chat_id: int, asset_type: str, asset_identifier: str) -> None:
        """Record an asset (image, music, text) as used so it won't be repeated."""
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO used_history (telegram_chat_id, asset_type, asset_identifier, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (chat_id, asset_type, asset_identifier, now),
            )
            await db.commit()

    async def get_used_assets(self, chat_id: int, asset_type: str) -> set:
        """Get set of all asset identifiers already used by this chat."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT asset_identifier FROM used_history WHERE telegram_chat_id = ? AND asset_type = ?",
                (chat_id, asset_type),
            )
            rows = await cursor.fetchall()
            return {row[0] for row in rows}

    async def clear_used_assets(self, chat_id: int, asset_type: Optional[str] = None) -> None:
        """Reset used assets for a user (if needed)."""
        async with aiosqlite.connect(self.db_path) as db:
            if asset_type:
                await db.execute(
                    "DELETE FROM used_history WHERE telegram_chat_id = ? AND asset_type = ?",
                    (chat_id, asset_type),
                )
            else:
                await db.execute(
                    "DELETE FROM used_history WHERE telegram_chat_id = ?",
                    (chat_id,),
                )
            await db.commit()

    async def is_testing_mode(self) -> bool:
        """Check if bot is in testing mode (default False for live production)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT);")
            async with db.execute("SELECT value FROM bot_settings WHERE key = 'testing_mode'") as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0] == "1"
                return False

    async def set_testing_mode(self, is_testing: bool) -> None:
        """Toggle testing mode."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT);")
            await db.execute(
                "INSERT INTO bot_settings (key, value) VALUES ('testing_mode', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = ?;",
                ("1" if is_testing else "0", "1" if is_testing else "0"),
            )
            await db.commit()

    async def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve arbitrary setting from bot_settings."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT);")
            async with db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0]
                return default

    async def set_setting(self, key: str, value: str) -> None:
        """Store arbitrary setting into bot_settings."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT);")
            await db.execute(
                "INSERT INTO bot_settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = ?;",
                (key, value, value),
            )
            await db.commit()

    async def record_synced_audio(
        self,
        audio_id: str,
        title: str,
        artist: str,
        file_path: str,
        media_pk: Optional[str] = None,
        source: str = "instagram",
    ) -> None:
        """Store newly extracted audio track from Instagram saved/liked reels."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR IGNORE INTO synced_instagram_audio
                (audio_id, title, artist, file_path, media_pk, source)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (audio_id, title, artist, file_path, media_pk, source),
            )
            await db.commit()

    async def get_all_synced_audio(self) -> List[Dict[str, Any]]:
        """Retrieve all synced audio records."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT audio_id, title, artist, file_path, media_pk, source FROM synced_instagram_audio ORDER BY id ASC;"
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "audio_id": r[0],
                        "title": r[1],
                        "artist": r[2] or "Instagram Sound",
                        "file_path": r[3],
                        "media_pk": r[4],
                        "source": r[5],
                    }
                    for r in rows
                ]

    async def is_audio_already_synced(self, audio_id: str) -> bool:
        """Check if an audio ID or media PK has already been downloaded."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT 1 FROM synced_instagram_audio WHERE audio_id = ? OR media_pk = ? LIMIT 1;",
                (audio_id, audio_id),
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None


# Singleton instance
db_manager = DatabaseManager(config.database_path)

