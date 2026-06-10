# -*- coding: utf-8 -*-
"""Déclencheurs « push » de l'équipe d'agents IA.

Lorsqu'un locataire déclare un événement (paiement, problème de voisinage,
problème dans le logement…), l'agent compétent envoie spontanément un message
Telegram au gestionnaire concerné. C'est le pendant « push » des agents, qui
fonctionnaient jusqu'ici en « pull » (le gestionnaire interroge) + rappels
planifiés.

Best-effort : jamais bloquant pour le flux appelant — toute erreur est avalée.

➕ POUR ÉTENDRE À UN NOUVEAU CAS D'USAGE : ajouter une entrée dans EVENT_AGENT
(sujet → clé d'agent) et son libellé dans TOPIC_LABEL. Rien d'autre à câbler :
les points d'appel passent simplement un nouveau `topic`.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telegram_link import TelegramLink
from app.services import telegram_service
from app.services.agent_team_service import AGENTS

logger = logging.getLogger(__name__)

# Sujet d'événement → agent compétent. EXTENSIBLE : une ligne par cas d'usage.
EVENT_AGENT: dict[str, str] = {
    "paiement": "comptable",      # déclaration de paiement       → Agent Comptable
    "voisinage": "securite",      # trouble / conflit de voisinage → Agent Sécurité
    "logement": "administratif",  # problème dans le logement      → Agent Administratif
    "autre": "administratif",     # divers (catch-all)             → Agent Administratif
}

# Libellé humain du sujet (titre du message poussé).
TOPIC_LABEL: dict[str, str] = {
    "paiement": "Paiement déclaré",
    "voisinage": "Problème de voisinage signalé",
    "logement": "Problème dans le logement signalé",
    "autre": "Nouvelle démarche",
}

_DEFAULT_AGENT = "administratif"


def agent_for_topic(topic: Optional[str]) -> dict:
    """Descripteur de l'agent compétent pour un sujet (repli : Administratif)."""
    key = EVENT_AGENT.get((topic or "").strip().lower(), _DEFAULT_AGENT)
    return {"key": key, **AGENTS[key]}


async def notify_manager(
    db: AsyncSession,
    manager_id,
    topic: str,
    body: str,
    *,
    cta: Optional[str] = None,
) -> bool:
    """Pousse un message de l'agent compétent au gestionnaire (Telegram, best-effort).

    Retourne True si un message a été émis, False sinon (pas de lien Telegram,
    opt-out, token absent, erreur réseau…) — sans jamais lever d'exception, afin
    de ne pas casser le flux métier appelant (déclaration de paiement, démarche…).
    """
    try:
        if not manager_id:
            return False
        link = (await db.execute(
            select(TelegramLink).where(TelegramLink.user_id == manager_id)
        )).scalar_one_or_none()
        if not link or not link.chat_id or not link.opt_in:
            return False
        agent = agent_for_topic(topic)
        label = TOPIC_LABEL.get((topic or "").strip().lower(), "Notification")
        lines = [f"{agent['emoji']} <b>{agent['name']}</b>", "", f"<b>{label}</b>", body]
        if cta:
            lines += ["", cta]
        return await telegram_service.send_message(link.chat_id, "\n".join(lines))
    except Exception as exc:  # noqa: BLE001 — ne jamais casser le flux appelant
        logger.warning("agent_events.notify_manager échec: %r", exc)
        return False
