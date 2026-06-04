# -*- coding: utf-8 -*-
"""Cerveau LLM des agents IA (Phase 2) — client compatible API OpenAI.

Un seul connecteur (chat completions) → fonctionne avec Groq (défaut, gratuit),
OpenAI, Google Gemini (endpoint compat), etc. via `base_url` + `model` + clé.

Conception défensive : si aucune clé n'est configurée OU si l'appel échoue,
`chat()` retourne None → l'appelant retombe sur le routeur déterministe
(Phase 1). L'application n'est jamais bloquée par le LLM.
"""
import logging
from typing import Optional, List, Dict

from app.config import get_settings

logger = logging.getLogger(__name__)


def enabled() -> bool:
    return get_settings().agent_llm_enabled


async def chat(
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0.3,
    max_tokens: int = 600,
    timeout: float = 30.0,
) -> Optional[str]:
    """Appelle l'endpoint chat completions. Retourne le texte ou None (repli)."""
    s = get_settings()
    if not s.agent_llm_enabled:
        return None
    url = s.AGENT_LLM_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": s.AGENT_LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    try:
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {s.AGENT_LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if resp.status_code != 200:
            logger.warning("LLM %s: %s", resp.status_code, resp.text[:300])
            return None
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return None
        content = (choices[0].get("message") or {}).get("content")
        return content.strip() if content else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM appel échoué: %r", exc)
        return None
