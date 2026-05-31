"""
Endpoints publics (sans authentification) — page d'accueil Le Comptoir Immo.

La demande de souscription/démo est enregistrée dans la table partagée
`alice_subscription_requests` ; elle est ensuite traitée côté Alice.
"""
import uuid
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

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
async def list_public_plans(db: AsyncSession = Depends(get_db)):
    """Plans actifs pour la page Tarification publique (lecture directe des tables
    Alice partagées). `features = null` ⇒ toutes les fonctionnalités."""
    try:
        rows = (await db.execute(text(
            "SELECT id, name, description, property_limit, monthly_price, features "
            "FROM alice_plans WHERE is_active = true "
            "ORDER BY (property_limit IS NULL), property_limit, monthly_price"
        ))).fetchall()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Lecture des plans publics échouée : %s", exc)
        return []
    return [
        PublicPlanOut(
            id=str(r[0]),
            name=r[1],
            description=r[2],
            property_limit=r[3],
            monthly_price=float(r[4]),
            features=r[5] if isinstance(r[5], list) else None,
        )
        for r in rows
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
    phone: Optional[str] = Field(None, max_length=30)
    company: Optional[str] = Field(None, max_length=200)
    message: Optional[str] = Field(None, max_length=2000)


@router.post("/subscription-requests", status_code=201, summary="Demande de souscription / démo")
async def create_subscription_request(
    data: SubscriptionRequestIn,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Enregistre une demande publique (à traiter par l'équipe Alice)."""
    await db.execute(
        text(
            "INSERT INTO alice_subscription_requests "
            "(id, full_name, email, phone, company, message, source, status, created_at) "
            "VALUES (:id, :full_name, :email, :phone, :company, :message, "
            "'site_lecomptoir', 'nouveau', now())"
        ),
        {
            "id": uuid.uuid4(),
            "full_name": data.full_name.strip(),
            "email": str(data.email).lower(),
            "phone": data.phone,
            "company": data.company,
            "message": data.message,
        },
    )
    await db.commit()
    background.add_task(_notify_team, data)
    return {"status": "received"}
