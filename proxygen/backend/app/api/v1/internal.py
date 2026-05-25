"""API interne ProxyGen — service-to-service, accès restreint par clé API."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.config import get_settings
from app.models.license import ProxygenLicense
from app.models.plan import ProxygenPlan

router = APIRouter(prefix="/internal", tags=["Internal"])

settings = get_settings()


def _require_internal_key(x_internal_key: Optional[str] = Header(None)) -> None:
    if x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Clé API interne invalide")


class LicenseInfoResponse(BaseModel):
    gestionnaire_user_id: uuid.UUID
    is_blocked: bool
    property_limit: Optional[int]
    plan_name: Optional[str]


@router.get("/license/{user_id}", response_model=LicenseInfoResponse, dependencies=[Depends(_require_internal_key)])
async def get_license_info(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne les informations de licence d'un gestionnaire.
    Endpoint service-to-service pour LeComptoirImmo.
    Requiert l'en-tête X-Internal-Key.
    """
    lic = (await db.execute(
        select(ProxygenLicense).where(ProxygenLicense.gestionnaire_user_id == user_id)
    )).scalar_one_or_none()

    if lic is None:
        raise HTTPException(status_code=404, detail="Licence introuvable pour cet utilisateur")

    # Résoudre la limite effective
    effective_limit: Optional[int] = lic.property_limit_override
    plan_name: Optional[str] = None

    if lic.plan_id:
        plan = (await db.execute(
            select(ProxygenPlan).where(ProxygenPlan.id == lic.plan_id)
        )).scalar_one_or_none()
        if plan:
            plan_name = plan.name
            if effective_limit is None:
                effective_limit = plan.property_limit  # None = illimité

    return LicenseInfoResponse(
        gestionnaire_user_id=lic.gestionnaire_user_id,
        is_blocked=lic.is_blocked,
        property_limit=effective_limit,
        plan_name=plan_name,
    )
