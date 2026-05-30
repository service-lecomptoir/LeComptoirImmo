"""API Abonnement — informations de licence Alice pour le gestionnaire connecté."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.database import get_db
from app.api.deps import get_current_user
from app.core.permissions import Role
from app.models.user import User
from app.models.property import Property

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscription", tags=["Abonnement"])


class SubscriptionInfo(BaseModel):
    plan_name: Optional[str]
    is_blocked: bool
    property_limit: Optional[int]
    property_count: int
    can_create_property: bool


@router.get("", response_model=SubscriptionInfo, summary="Mon abonnement Alice")
async def get_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retourne les informations d'abonnement Alice du gestionnaire connecté."""
    role = Role(current_user.role)
    if role not in (Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO):
        raise HTTPException(status_code=403, detail="Réservé aux gestionnaires")

    # Nombre de biens actuels
    property_count = (await db.execute(
        select(func.count(Property.id)).where(Property.created_by == current_user.id)
    )).scalar_one_or_none() or 0

    # Infos licence depuis Alice
    plan_name: Optional[str] = None
    is_blocked = False
    property_limit: Optional[int] = None

    try:
        import httpx
        from app.config import get_settings
        cfg = get_settings()
        async with httpx.AsyncClient(timeout=5.0) as hc:
            resp = await hc.get(
                f"{cfg.ALICE_URL}/api/v1/internal/license/{current_user.id}",
                headers={"X-Internal-Key": cfg.ALICE_INTERNAL_KEY},
            )
        if resp.status_code == 200:
            data = resp.json()
            plan_name = data.get("plan_name")
            is_blocked = data.get("is_blocked", False)
            property_limit = data.get("property_limit")
        elif resp.status_code == 404:
            # Pas de licence → considéré comme bloqué
            is_blocked = True
    except Exception as exc:
        logger.warning(f"Alice subscription check failed for {current_user.id}: {exc}")
        # Alice indisponible — on retourne ce qu'on sait de la DB locale
        from sqlalchemy import text as sa_text
        try:
            row = (await db.execute(
                sa_text("SELECT is_blocked FROM alice_licenses WHERE gestionnaire_user_id = :uid")
                .bindparams(uid=current_user.id)
            )).fetchone()
            if row:
                is_blocked = row[0]
        except Exception:
            pass

    can_create = not is_blocked and (property_limit is None or property_count < property_limit)

    return SubscriptionInfo(
        plan_name=plan_name,
        is_blocked=is_blocked,
        property_limit=property_limit,
        property_count=property_count,
        can_create_property=can_create,
    )
