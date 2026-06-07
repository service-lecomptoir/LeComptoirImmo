"""
Endpoints publics (sans authentification) — page d'accueil Le Comptoir Immo.

Les plans et les demandes de souscription/démo proviennent d'Alice (source de
vérité, base dédiée) via son API /internal (app.services.alice_client) — plus
aucune lecture/écriture directe des tables alice_*.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field

from app.services import alice_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/public", tags=["Public"])


class PublicPlanOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    property_limit: Optional[int] = None
    monthly_price: float
    features: Optional[List[str]] = None


@router.get("/plans", response_model=List[PublicPlanOut], summary="Plans tarifaires publics")
async def list_public_plans():
    """Plans actifs pour la page Tarification publique (via l'API Alice).
    `features = null` ⇒ toutes les fonctionnalités. Fail-soft → [] si Alice KO."""
    plans = await alice_client.list_plans()
    return [
        PublicPlanOut(
            id=str(p.get("id")),
            name=p.get("name"),
            description=p.get("description"),
            property_limit=p.get("property_limit"),
            monthly_price=float(p.get("monthly_price") or 0),
            features=p.get("features") if isinstance(p.get("features"), list) else None,
        )
        for p in plans
    ]


async def _notify_team(data: "SubscriptionRequestIn") -> None:
    """Best-effort : notifie l'équipe par email (n'échoue jamais la requête)."""
    try:
        from app.config import get_settings
        from app.services.email_service import send_subscription_lead_notification
        cfg = get_settings()
        recipient = cfg.LEADS_NOTIFY_EMAIL or cfg.FIRST_ADMIN_EMAIL
        await send_subscription_lead_notification(
            to=recipient,
            full_name=data.full_name.strip(),
            email=str(data.email).lower(),
            phone=data.phone,
            company=data.company,
            message=data.message,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Notification de souscription non envoyée : %s", exc)


class SubscriptionRequestIn(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(..., min_length=6, max_length=30)
    company: Optional[str] = Field(None, max_length=200)
    message: Optional[str] = Field(None, max_length=2000)


@router.post("/subscription-requests", status_code=201, summary="Demande de souscription / démo")
async def create_subscription_request(
    data: SubscriptionRequestIn,
    background: BackgroundTasks,
):
    """Enregistre une demande publique côté Alice (à traiter dans « Demandes »)."""
    await alice_client.create_lead(
        full_name=data.full_name.strip(),
        email=str(data.email).lower(),
        phone=data.phone,
        company=data.company,
        message=data.message,
        source="site_lecomptoir",
    )
    background.add_task(_notify_team, data)
    return {"status": "received"}
