import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.core.permissions import Role
from app.models.user import User
from app.models.tenant import Tenant
from app.models.property import Property
from app.models.unit import Unit
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
    current_user: User = Depends(get_current_user),
):
    """
    Liste les baux.
    - Gestionnaire/Admin : tous les baux
    - Propriétaire : baux de ses biens
    - Locataire : uniquement son propre bail
    """
    role = Role(current_user.role)

    # ── Locataire : uniquement son bail ─────────────────────────────────────────
    if role == Role.LOCATAIRE:
        tenant = (await db.execute(
            select(Tenant).where(Tenant.user_id == current_user.id)
        )).scalar_one_or_none()
        if not tenant:
            return LeaseListResponse(items=[], total=0, skip=skip, limit=limit)
        tenant_id = tenant.id

    # ── Propriétaire : baux de ses biens ─────────────────────────────────────────
    elif role == Role.PROPRIETAIRE:
        props = (await db.execute(
            select(Property).where(Property.owner_user_id == current_user.id)
        )).scalars().all()
        prop_ids = [p.id for p in props]
        if not prop_ids:
            return LeaseListResponse(items=[], total=0, skip=skip, limit=limit)
        # Si property_id spécifié et n'appartient pas au proprio → interdit
        if property_id and property_id not in prop_ids:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
        if not property_id:
            # On ne peut pas passer tous les property_ids comme filtre directement
            # → on passe par les unit_ids des biens du proprio
            units = (await db.execute(
                select(Unit).where(Unit.property_id.in_(prop_ids))
            )).scalars().all()
            unit_ids_proprio = [u.id for u in units]
            if not unit_ids_proprio:
                return LeaseListResponse(items=[], total=0, skip=skip, limit=limit)
            # Pour filtrer on va utiliser une liste — on passe property_ids directement
            # en filtrant dans le service (ou on boucle)
            leases_all = []
            for pid in prop_ids:
                l2, _ = await LeaseService.list_all(
                    db, property_id=pid, is_active=is_active, skip=0, limit=200
                )
                leases_all.extend(l2)
            items = [LeaseService.to_list_item(l) for l in leases_all]
            return LeaseListResponse(items=items, total=len(items), skip=0, limit=limit)

    # ── Gestionnaire/Admin/Comptable ──────────────────────────────────────────────
    # pas de filtrage supplémentaire

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
    current_user: User = Depends(get_current_user),
):
    lease = await LeaseService.get_by_id(db, lease_id, load_relations=True)

    # Contrôle d'accès locataire
    if Role(current_user.role) == Role.LOCATAIRE:
        tenant = (await db.execute(
            select(Tenant).where(Tenant.user_id == current_user.id)
        )).scalar_one_or_none()
        if not tenant or lease.tenant_id != tenant.id:
            raise HTTPException(status_code=403, detail="Accès non autorisé")

    return lease


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
    current_user: User = Depends(get_current_user),
):
    lease = await LeaseService.get_by_id(db, lease_id, load_relations=True)

    # Contrôle d'accès locataire
    if Role(current_user.role) == Role.LOCATAIRE:
        tenant = (await db.execute(
            select(Tenant).where(Tenant.user_id == current_user.id)
        )).scalar_one_or_none()
        if not tenant or lease.tenant_id != tenant.id:
            raise HTTPException(status_code=403, detail="Accès non autorisé")

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
