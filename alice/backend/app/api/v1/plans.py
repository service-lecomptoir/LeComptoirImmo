import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.admin import AliceAdmin
from app.models.plan import AlicePlan
from app.models.license import AliceLicense
from app.schemas.plan import PlanCreate, PlanUpdate, PlanOut
from app.core.deps import get_current_alice_admin

router = APIRouter(prefix="/plans", tags=["Plans"])


async def _plan_to_out(db: AsyncSession, plan: AlicePlan) -> PlanOut:
    """Enrichit un plan avec le nombre de gestionnaires qui l'utilisent."""
    count_result = await db.execute(
        select(func.count(AliceLicense.id)).where(AliceLicense.plan_id == plan.id)
    )
    count = count_result.scalar_one_or_none() or 0
    out = PlanOut.model_validate(plan)
    out.gestionnaire_count = count
    return out


@router.get("", response_model=List[PlanOut])
async def list_plans(
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Liste tous les plans actifs, ordonnés par limite de biens croissante
    (« illimité » en dernier)."""
    result = await db.execute(
        select(AlicePlan)
        .where(AlicePlan.is_active == True)
        .order_by(AlicePlan.property_limit.asc().nulls_last(), AlicePlan.monthly_price)
    )
    plans = result.scalars().all()
    return [await _plan_to_out(db, p) for p in plans]


@router.post("", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
async def create_plan(
    data: PlanCreate,
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Crée un nouveau plan tarifaire."""
    # Vérifie l'unicité du nom
    existing = await db.execute(select(AlicePlan).where(AlicePlan.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Un plan nommé '{data.name}' existe déjà")

    plan = AlicePlan(**data.model_dump())
    db.add(plan)
    await db.flush()
    return await _plan_to_out(db, plan)


@router.patch("/{plan_id}", response_model=PlanOut)
async def update_plan(
    plan_id: uuid.UUID,
    data: PlanUpdate,
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Modifie un plan existant."""
    result = await db.execute(select(AlicePlan).where(AlicePlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan introuvable")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)

    await db.flush()
    return await _plan_to_out(db, plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Désactive un plan (soft delete — is_active = False)."""
    result = await db.execute(select(AlicePlan).where(AlicePlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan introuvable")

    plan.is_active = False


@router.post("/{plan_id}/sync-stripe-price", response_model=PlanOut)
async def sync_plan_stripe_price(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """(Re)crée le Product + Price Stripe du plan d'après son tarif actuel.

    À utiliser après modification du `monthly_price` : un Price Stripe étant
    immuable, on en génère un nouveau pour les FUTURS abonnements (les abonnés
    existants conservent leur tarif jusqu'à migration)."""
    from app.services import stripe_service
    if not stripe_service.enabled():
        raise HTTPException(status_code=503, detail="Stripe non activé")
    result = await db.execute(select(AlicePlan).where(AlicePlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan introuvable")
    await stripe_service.ensure_plan_price(db, plan, force=True)
    await db.commit()
    return await _plan_to_out(db, plan)
