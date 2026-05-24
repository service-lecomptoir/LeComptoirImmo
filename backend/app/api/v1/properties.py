import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, get_current_gestionnaire
from app.core.permissions import Role
from app.models.user import User
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyResponse, PropertyListItem
from app.schemas.unit import UnitResponse, UnitListItem
from app.services.property_service import PropertyService
from app.services.unit_service import UnitService

router = APIRouter(prefix="/properties", tags=["Biens immobiliers"])


async def _enrich_properties(db, properties):
    """Ajoute unit_count et occupied_count à chaque bien."""
    items = []
    for prop in properties:
        units = await UnitService.list_by_property(db, prop.id)
        occupied = sum(1 for u in units if u.is_occupied)
        item = PropertyListItem.model_validate(prop)
        item_dict = item.model_dump()
        item_dict["unit_count"] = len(units)
        item_dict["occupied_count"] = occupied
        items.append(item_dict)
    return items


@router.get("", response_model=dict, summary="Liste des biens")
async def list_properties(
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = Role(current_user.role)

    # Propriétaire : uniquement ses biens
    if role == Role.PROPRIETAIRE:
        props = (await db.execute(
            select(Property).where(Property.owner_user_id == current_user.id)
        )).scalars().all()
        items = await _enrich_properties(db, props)
        return {"items": items, "total": len(items), "skip": 0, "limit": limit}

    # Locataire : aucun bien à afficher directement
    if role == Role.LOCATAIRE:
        return {"items": [], "total": 0, "skip": skip, "limit": limit}

    # Gestionnaire / Admin / autres
    properties, total = await PropertyService.list_all(db, search=search, skip=skip, limit=limit)
    items = await _enrich_properties(db, properties)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("", response_model=PropertyResponse, status_code=201, summary="Créer un bien")
async def create_property(
    data: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    # ── Vérification limite de biens ProxyGen ─────────────────────────────────
    try:
        from sqlalchemy import text as sa_text
        lic_result = await db.execute(
            sa_text(
                "SELECT property_limit_override, plan_id FROM proxygen_licenses "
                "WHERE gestionnaire_user_id = :uid"
            ).bindparams(uid=current_user.id)
        )
        lic_row = lic_result.fetchone()
        if lic_row:
            effective_limit = lic_row[0]  # property_limit_override
            if effective_limit is None and lic_row[1]:  # pas d'override → vérifier plan
                plan_result = await db.execute(
                    sa_text(
                        "SELECT property_limit FROM proxygen_plans WHERE id = :plan_id"
                    ).bindparams(plan_id=lic_row[1])
                )
                plan_row = plan_result.fetchone()
                if plan_row:
                    effective_limit = plan_row[0]
            if effective_limit is not None:
                count_result = await db.execute(
                    select(func.count(Property.id)).where(
                        Property.created_by == current_user.id
                    )
                )
                current_count = count_result.scalar_one_or_none() or 0
                if current_count >= effective_limit:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=400,
                        detail=f"Limite de biens atteinte pour votre formule ({effective_limit} biens max)"
                    )
    except Exception as exc:
        # Ne pas bloquer si ProxyGen n'est pas disponible
        import logging
        logging.getLogger(__name__).warning(f"ProxyGen license check skipped: {exc}")
    # ─────────────────────────────────────────────────────────────────────────
    return await PropertyService.create(db, data, created_by=current_user.id)


@router.get("/{property_id}", response_model=PropertyResponse, summary="Détail d'un bien")
async def get_property(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    prop = await PropertyService.get_by_id(db, property_id)
    units = await UnitService.list_by_property(db, property_id)
    occupied = sum(1 for u in units if u.is_occupied)
    resp = PropertyResponse.model_validate(prop)
    resp.unit_count = len(units)
    resp.occupied_count = occupied
    return resp


@router.put("/{property_id}", response_model=PropertyResponse, summary="Modifier un bien")
async def update_property(
    property_id: uuid.UUID,
    data: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_gestionnaire),
):
    return await PropertyService.update(db, property_id, data)


@router.delete("/{property_id}", status_code=204, summary="Supprimer un bien")
async def delete_property(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_gestionnaire),
):
    await PropertyService.delete(db, property_id)


@router.get("/{property_id}/units", response_model=List[UnitListItem], summary="Logements du bien")
async def list_property_units(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await PropertyService.get_by_id(db, property_id)
    return await UnitService.list_by_property(db, property_id)


@router.get("/{property_id}/occupancy", summary="Taux d'occupation")
async def get_occupancy(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await PropertyService.get_by_id(db, property_id)
    units = await UnitService.list_by_property(db, property_id)
    total = len(units)
    occupied = sum(1 for u in units if u.is_occupied)
    return {
        "total": total,
        "occupied": occupied,
        "vacant": total - occupied,
        "rate": round((occupied / total * 100), 1) if total > 0 else 0.0,
    }
