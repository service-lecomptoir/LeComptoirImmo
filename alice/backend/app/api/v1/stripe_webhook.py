# -*- coding: utf-8 -*-
"""Webhook Stripe (public) — synchronise abonnements/factures côté Alice.

Endpoint appelé par Stripe (pas par un humain). La sécurité repose sur la
vérification de la SIGNATURE (`Stripe-Signature` + STRIPE_WEBHOOK_SECRET).
"""
import logging
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import stripe_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Stripe"])


@router.post("/stripe/webhook", summary="Webhook Stripe (abonnements)")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    if not stripe_service.enabled():
        # Intégration désactivée : on accuse réception sans traiter.
        return {"received": True, "ignored": True}
    payload = await request.body()
    try:
        event = stripe_service.construct_event(payload, stripe_signature)
    except Exception as exc:  # noqa: BLE001 — signature invalide / secret manquant
        logger.warning("Webhook Stripe rejeté: %r", exc)
        raise HTTPException(status_code=400, detail="Signature webhook invalide")
    try:
        await stripe_service.handle_event(db, event)
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        logger.error("Webhook Stripe %s erreur: %r", event.get("type"), exc)
        # 200 quand même pour éviter des retours en boucle sur une erreur non-réessayable :
        # on log ; les états restent cohérents (rollback). Stripe réessaiera sur 5xx.
        raise HTTPException(status_code=500, detail="Erreur de traitement")
    return {"received": True, "type": event.get("type")}
