# -*- coding: utf-8 -*-
"""Canal Telegram (gratuit) pour l'équipe d'agents IA.

Envoi best-effort : si TELEGRAM_BOT_TOKEN est vide, `send_message` est un no-op
(l'application reste fonctionnelle). Le canal n'engage aucun coût côté Telegram.
"""
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
_API = "https://api.telegram.org"


async def send_message(chat_id: str, text: str) -> bool:
    """Envoie un message Telegram. Retourne True si envoyé, False sinon (no-op/erreur)."""
    s = get_settings()
    if not s.TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{_API}/bot{s.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                      "disable_web_page_preview": True},
            )
        if resp.status_code != 200:
            logger.warning("Telegram sendMessage %s: %s", resp.status_code, resp.text[:200])
            return False
        return True
    except Exception as exc:  # noqa
        logger.warning("Telegram sendMessage échec: %r", exc)
        return False
