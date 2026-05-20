import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, get_current_gestionnaire
from app.models.user import User
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyResponse, PropertyListItem
from app.schemas.unit import UnitResponse, UnitListItem
from app.services.property_service import PropertyService
from app.services.unit_service import UnitService

router = APIRouter(prefix="/properties", tags=["Biens immobiliers"])


@router.get("", response_model=dict, summary="Liste des biens")
async def list_properties(
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    properties, total = await PropertyService.list_all(db, search=search, skip=skip, limit=limit)

    items = []
    for prop in properties:
        units = await UnitService.list_by_property(db, prop.id)
        occupied = sum(1 for u in units if u.is_occupied)
        item = PropertyListItem.model_validate(prop)
        item_dict = item.model_dump()
        item_dict["unit_count"] = len(units)
        item_dict["occupied_count"] = occupied
        items.append(item_dict)

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("", response_model=PropertyResponse, status_code=201, summary="Créer un bien")
async def create_property(
    data: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
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
