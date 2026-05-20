import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.permissions import require_role, Role
from app.models.user import User
from app.schemas.inspection import (
    InspectionCreate,
    InspectionUpdate,
    InspectionResponse,
    InspectionListResponse,
)
from app.services.inspection_service import InspectionService
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/inspections", tags=["Inspections"])


@router.get("", response_model=InspectionListResponse)
async def list_inspections(
    lease_id: Optional[uuid.UUID] = Query(None),
    unit_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.LECTURE)),
):
    items, total = await InspectionService.list_all(
        db, lease_id=lease_id, unit_id=unit_id, skip=skip, limit=limit
    )
    return InspectionListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=InspectionResponse, status_code=201)
async def create_inspection(
    data: InspectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    inspection = await InspectionService.create(db, data, created_by=current_user.id)
    await db.commit()
    return inspection


@router.get("/{inspection_id}", response_model=InspectionResponse)
async def get_inspection(
    inspection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.LECTURE)),
):
    return await InspectionService.get_by_id(db, inspection_id)


@router.put("/{inspection_id}", response_model=InspectionResponse)
async def update_inspection(
    inspection_id: uuid.UUID,
    data: InspectionUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    inspection = await InspectionService.update(db, inspection_id, data)
    await db.commit()
    return inspection


@router.delete("/{inspection_id}", status_code=204)
async def delete_inspection(
    inspection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    await InspectionService.delete(db, inspection_id)
    await db.commit()
