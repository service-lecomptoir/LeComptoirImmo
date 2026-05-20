import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.permissions import require_role, Role
from app.models.user import User
from app.schemas.lease import (
    LeaseCreate,
    LeaseUpdate,
    LeaseTerminate,
    LeaseResponse,
    LeaseListItem,
    LeaseListResponse,
)
from app.services.lease_service import LeaseService
from app.services.pdf_service import generate_lease_pdf
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/leases", tags=["Leases"])


@router.get("", response_model=LeaseListResponse)
async def list_leases(
    search: Optional[str] = Query(None),
    unit_id: Optional[uuid.UUID] = Query(None),
    tenant_id: Optional[uuid.UUID] = Query(None),
    property_id: Optional[uuid.UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.LECTURE)),
):
    leases, total = await LeaseService.list_all(
        db,
        search=search,
        unit_id=unit_id,
        tenant_id=tenant_id,
        property_id=property_id,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )
    items = [LeaseService.to_list_item(l) for l in leases]
    return LeaseListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=LeaseResponse, status_code=201)
async def create_lease(
    data: LeaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    lease = await LeaseService.create(db, data, created_by=current_user.id)
    await db.commit()
    lease = await LeaseService.get_by_id(db, lease.id, load_relations=True)
    return lease


@router.get("/{lease_id}", response_model=LeaseResponse)
async def get_lease(
    lease_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.LECTURE)),
):
    return await LeaseService.get_by_id(db, lease_id, load_relations=True)


@router.put("/{lease_id}", response_model=LeaseResponse)
async def update_lease(
    lease_id: uuid.UUID,
    data: LeaseUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    lease = await LeaseService.update(db, lease_id, data)
    await db.commit()
    return await LeaseService.get_by_id(db, lease.id, load_relations=True)


@router.post("/{lease_id}/terminate", response_model=LeaseResponse)
async def terminate_lease(
    lease_id: uuid.UUID,
    data: LeaseTerminate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    lease = await LeaseService.terminate(db, lease_id, data)
    await db.commit()
    return await LeaseService.get_by_id(db, lease.id, load_relations=True)


@router.get("/{lease_id}/pdf")
async def download_lease_pdf(
    lease_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.LECTURE)),
):
    lease = await LeaseService.get_by_id(db, lease_id, load_relations=True)
    pdf_bytes = generate_lease_pdf(lease)
    tenant_name = (
        lease.tenant.full_name.replace(" ", "_")
        if lease.tenant
        else str(lease_id)
    )
    filename = f"bail_{tenant_name}_{lease.start_date}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{lease_id}", status_code=204)
async def delete_lease(
    lease_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    await LeaseService.delete(db, lease_id)
    await db.commit()
