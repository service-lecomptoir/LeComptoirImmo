import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.permissions import Role
from app.api.deps import require_role
from app.models.user import User
from app.schemas.inspection import (
    InspectionCreate,
    InspectionUpdate,
    InspectionResponse,
    InspectionListResponse,
)
from app.services.inspection_service import InspectionService
from app.api.v1.auth import get_current_user
from app.api.v1._isolation import agency_member_ids, assert_manager_scope

router = APIRouter(prefix="/inspections", tags=["Inspections"])


@router.get("", response_model=InspectionListResponse)
async def list_inspections(
    lease_id: Optional[uuid.UUID] = Query(None),
    property_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.LECTURE)),
):
    items, _total = await InspectionService.list_all(
        db, lease_id=lease_id, property_id=property_id, skip=0, limit=10000
    )
    # Isolation par périmètre (created_by) — sauf admin
    role = Role(current_user.role)
    if role == Role.GESTIONNAIRE_PROPRIO:
        items = [i for i in items if str(getattr(i, "created_by", None)) == str(current_user.id)]
    elif role != Role.ADMIN:
        members = await agency_member_ids(db, current_user)
        items = [i for i in items if getattr(i, "created_by", None) in members]
    total = len(items)
    page = items[skip: skip + limit]
    return InspectionListResponse(items=page, total=total, skip=skip, limit=limit)


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
    current_user: User = Depends(require_role(Role.LECTURE)),
):
    inspection = await InspectionService.get_by_id(db, inspection_id)
    await assert_manager_scope(db, current_user, getattr(inspection, "created_by", None), "cet état des lieux")
    return inspection


@router.put("/{inspection_id}", response_model=InspectionResponse)
async def update_inspection(
    inspection_id: uuid.UUID,
    data: InspectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    _existing = await InspectionService.get_by_id(db, inspection_id)
    await assert_manager_scope(db, current_user, getattr(_existing, "created_by", None), "cet état des lieux")
    inspection = await InspectionService.update(db, inspection_id, data)
    await db.commit()
    return inspection


@router.delete("/{inspection_id}", status_code=204)
async def delete_inspection(
    inspection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    _existing = await InspectionService.get_by_id(db, inspection_id)
    await assert_manager_scope(db, current_user, getattr(_existing, "created_by", None), "cet état des lieux")
    await InspectionService.delete(db, inspection_id)
    await db.commit()
