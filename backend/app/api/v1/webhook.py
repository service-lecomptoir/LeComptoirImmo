"""Webhook interne Alice → LeCI — notifie les changements de statut/plan."""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal/webhook", tags=["Webhook interne"])

_VALID_EVENTS = {"blocked", "unblocked", "plan_changed"}


class AliceWebhookPayload(BaseModel):
    user_id: uuid.UUID
    event: str
    is_blocked: bool
    plan_name: Optional[str] = None
    property_limit: Optional[int] = None


@router.post("/alice", status_code=204, summary="Webhook Alice → LeCI")
async def alice_webhook(
    payload: AliceWebhookPayload,
    x_internal_key: Optional[str] = Header(None),
) -> None:
    """
    Reçoit une notification de Alice lors d'un blocage, déblocage ou
    changement de plan. Valide la clé interne et logue l'événement.
    Aucune synchronisation DB nécessaire : Alice et LeCI partagent la
    même base de données — les changements sont déjà visibles.
    """
    cfg = get_settings()
    if x_internal_key != cfg.ALICE_INTERNAL_KEY:
        raise HTTPException(status_code=401, detail="Clé interne invalide")

    if payload.event not in _VALID_EVENTS:
        raise HTTPException(status_code=422, detail=f"Événement inconnu: {payload.event}")

    logger.info(
        "Webhook Alice reçu | event=%s user_id=%s is_blocked=%s plan=%s limit=%s",
        payload.event,
        payload.user_id,
        payload.is_blocked,
        payload.plan_name,
        payload.property_limit,
    )
