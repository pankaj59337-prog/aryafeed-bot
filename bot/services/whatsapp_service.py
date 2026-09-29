"""WhatsApp Notification Service via Green-API for Reel Alerts.

Sends instant WhatsApp alerts when a scheduled reel is rendered and ready.
"""

import asyncio
import logging
import os
from typing import Any, Dict, Optional
import requests

from database.db import db_manager

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Dispatches WhatsApp alerts for scheduled reel previews and auto-posts."""

    async def get_credentials(self) -> Optional[Dict[str, str]]:
        """Retrieve Green-API credentials from DB or environment."""
        id_instance = await db_manager.get_setting("whatsapp_id_instance") or os.environ.get("WHATSAPP_ID_INSTANCE")
        api_token = await db_manager.get_setting("whatsapp_api_token") or os.environ.get("WHATSAPP_API_TOKEN")
        phone_number = await db_manager.get_setting("whatsapp_phone") or os.environ.get("WHATSAPP_PHONE")
        api_url = await db_manager.get_setting("whatsapp_api_url") or os.environ.get("WHATSAPP_API_URL") or "https://api.green-api.com"

        if id_instance and api_token and phone_number:
            clean_phone = phone_number.replace("+", "").replace(" ", "").replace("-", "").strip()
            return {
                "id_instance": id_instance.strip(),
                "api_token": api_token.strip(),
                "phone": clean_phone,
                "api_url": api_url.rstrip("/"),
            }
        return None

    async def set_credentials(self, id_instance: str, api_token: str, phone: str, api_url: Optional[str] = None) -> None:
        """Store Green-API credentials in database."""
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "").strip()
        await db_manager.set_setting("whatsapp_id_instance", id_instance.strip())
        await db_manager.set_setting("whatsapp_api_token", api_token.strip())
        await db_manager.set_setting("whatsapp_phone", clean_phone)
        if api_url:
            await db_manager.set_setting("whatsapp_api_url", api_url.rstrip("/"))
        logger.info(f"[WhatsAppService] Stored WhatsApp notification target for {clean_phone}")

    async def send_reel_ready_alert(
        self,
        category_title: str,
        category_icon: str,
        photo_name: str,
        song_title: str,
        hook_text: str,
        target_time_str: str,
    ) -> Dict[str, Any]:
        """Send instant WhatsApp alert when a scheduled reel is ready."""
        creds = await self.get_credentials()
        if not creds:
            logger.info("[WhatsAppService] WhatsApp notifications not configured, skipping.")
            return {"success": False, "reason": "not_configured"}

        id_instance = creds["id_instance"]
        api_token = creds["api_token"]
        phone = creds["phone"]
        chat_id = f"{phone}@c.us" if "@" not in phone else phone

        message = (
            f"⏰ *Reel Ready — Scheduled for {target_time_str}* 🚀\n\n"
            f"📂 *Category:* {category_icon} {category_title}\n"
            f"📸 *Photo:* {photo_name}\n"
            f"🎤 *Audio:* {song_title}\n\n"
            f"📝 *Text Overlay:*\n"
            f"_{hook_text}_\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ *10 Minutes Remaining:*\n"
            f"• Check Telegram for the HD video preview & 1-tap buttons.\n"
            f"• If uncancelled, bot will automatically post to Instagram @night_thought_12 at *{target_time_str}*!"
        )

        api_url = creds.get("api_url", "https://api.green-api.com")
        url = f"{api_url}/waInstance{id_instance}/sendMessage/{api_token}"
        payload = {
            "chatId": chat_id,
            "message": message,
        }

        try:
            def _post():
                return requests.post(url, json=payload, timeout=10.0)

            res = await asyncio.to_thread(_post)
            data = res.json()
            if res.status_code == 200 and "idMessage" in data:
                logger.info(f"[WhatsAppService] Alert sent to WhatsApp ({phone}): {data.get('idMessage')}")
                return {"success": True, "idMessage": data.get("idMessage")}
            else:
                logger.warning(f"[WhatsAppService] Green-API returned error: {data}")
                return {"success": False, "error": data}
        except Exception as e:
            logger.error(f"[WhatsAppService] Failed to send WhatsApp alert: {e}")
            return {"success": False, "error": str(e)}


whatsapp_service = WhatsAppService()
