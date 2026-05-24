import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.admin import ProxygenAdmin
from app.models.plan import ProxygenPlan
from app.models.license import ProxygenLicense
from app.schemas.plan import PlanCreate, PlanUpdate, PlanOut
from app.core.deps import get_current_proxygen_admin

router = APIRouter(prefix="/plans", tags=["Plans"])


async def _plan_to_out(db: AsyncSession, plan: ProxygenPlan) -> PlanOut:
    """Enrichit un plan avec le nombre de gestionnaires qui l'utilisent."""
    count_result = await db.execute(
        select(func.count(ProxygenLicense.id)).where(ProxygenLicense.plan_id == plan.id)
    )
    count = count_result.scalar_one_or_none() or 0
    out = PlanOut.model_validate(plan)
    out.gestionnaire_count = count
    return out


@router.get("", response_model=List[PlanOut])
async def list_plans(
    db: AsyncSession = Depends(get_db),
    _: ProxygenAdmin = Depends(get_current_proxygen_admin),
):
    """Liste tous les plans actifs."""
    result = await db.execute(
        select(ProxygenPlan).where(ProxygenPlan.is_active == True).order_by(ProxygenPlan.monthly_price)
    )
    plans = result.scalars().all()
    return [await _plan_to_out(db, p) for p in plans]


@router.post("", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
async def create_plan(
    data: PlanCreate,
    db: AsyncSession = Depends(get_db),
    _: ProxygenAdmin = Depends(get_current_proxygen_admin),
):
    """Crée un nouveau plan tarifaire."""
    # Vérifie l'unicité du nom
    existing = await db.execute(select(ProxygenPlan).where(ProxygenPlan.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Un plan nommé '{data.name}' existe déjà")

    plan = ProxygenPlan(**data.model_dump())
    db.add(plan)
    await db.flush()
    return await _plan_to_out(db, plan)


@router.patch("/{plan_id}", response_model=PlanOut)
async def update_plan(
    plan_id: uuid.UUID,
    data: PlanUpdate,
    db: AsyncSession = Depends(get_db),
    _: ProxygenAdmin = Depends(get_current_proxygen_admin),
):
    """Modifie un plan existant."""
    result = await db.execute(select(ProxygenPlan).where(ProxygenPlan.id == plan_id))
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
    _: ProxygenAdmin = Depends(get_current_proxygen_admin),
):
    """Désactive un plan (soft delete — is_active = False)."""
    result = await db.execute(select(ProxygenPlan).where(ProxygenPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan introuvable")

    plan.is_active = False
