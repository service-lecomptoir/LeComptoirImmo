import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, get_current_gestionnaire
from app.models.user import User
from app.schemas.unit import UnitCreate, UnitUpdate, UnitResponse, UnitListItem
from app.services.unit_service import UnitService

router = APIRouter(prefix="/units", tags=["Logements"])


@router.get("", response_model=List[UnitListItem], summary="Liste des logements")
async def list_units(
    property_id: Optional[uuid.UUID] = Query(None),
    available_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await UnitService.list_all(db, property_id=property_id, only_available=available_only)


@router.post("", response_model=UnitResponse, status_code=201, summary="Créer un logement")
async def create_unit(
    data: UnitCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_gestionnaire),
):
    return await UnitService.create(db, data)


@router.get("/{unit_id}", response_model=UnitResponse, summary="Détail d'un logement")
async def get_unit(
    unit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await UnitService.get_by_id(db, unit_id)


@router.put("/{unit_id}", response_model=UnitResponse, summary="Modifier un logement")
async def update_unit(
    unit_id: uuid.UUID,
    data: UnitUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_gestionnaire),
):
    return await UnitService.update(db, unit_id, data)


@router.delete("/{unit_id}", status_code=204, summary="Supprimer un logement")
async def delete_unit(
    unit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_gestionnaire),
):
    await UnitService.delete(db, unit_id)
