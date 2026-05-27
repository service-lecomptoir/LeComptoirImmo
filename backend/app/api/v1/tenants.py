import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from app.database import get_db
from app.api.deps import get_current_user, get_current_gestionnaire
from app.core.permissions import Role
from app.api.v1._isolation import gp_tenant_ids as _gp_tenant_ids
from app.models.user import User
from app.models.document import EntityType, DocumentType
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse, TenantListItem
from app.schemas.document import DocumentResponse
from app.services.tenant_service import TenantService
from app.services.document_service import DocumentService

router = APIRouter(prefix="/tenants", tags=["Locataires"])


@router.get("", response_model=dict, summary="Liste des locataires")
async def list_tenants(
    search: Optional[str] = Query(None, description="Recherche par nom, email, téléphone"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    available_only: bool = Query(False, description="Exclure les locataires ayant déjà un bail actif"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste paginée avec recherche full-text."""
    if Role(current_user.role) == Role.LOCATAIRE:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    from app.models.lease import Lease

    if Role(current_user.role) == Role.GESTIONNAIRE_PROPRIO:
        from app.models.property import Property
        # Ses locataires = ceux qu'il a créés (created_by) OU rattachés à un bail
        # sur l'un de ses biens. (On s'aligne sur list_users : un locataire créé
        # mais pas encore sous contrat doit rester visible.)
        prop_ids = [p for p in (await db.execute(
            select(Property.id).where(Property.owner_user_id == current_user.id)
        )).scalars().all()]
        lease_tenant_ids: set = set()
        if prop_ids:
            lease_tenant_ids = {tid for tid in (await db.execute(
                select(Lease.tenant_id).where(Lease.property_id.in_(prop_ids), Lease.tenant_id.isnot(None))
            )).scalars().all()}
        all_tenants, _ = await TenantService.list_all(db, search=search, skip=0, limit=2000)
        own = [t for t in all_tenants if t.created_by == current_user.id or t.id in lease_tenant_ids]
        if available_only:
            active_ids = {l.tenant_id for l in (await db.execute(
                select(Lease).where(Lease.is_active.is_(True), Lease.tenant_id.isnot(None))
            )).scalars().all()}
            own = [t for t in own if t.id not in active_ids]
        total = len(own)
        page = own[skip: skip + limit]
        return {"items": [TenantListItem.model_validate(t) for t in page], "total": total, "skip": skip, "limit": limit}

    tenants, total = await TenantService.list_all(db, search=search, skip=0, limit=2000)

    # Gestionnaire mandataire : exclure les locataires des gestionnaire_proprio
    if Role(current_user.role) == Role.GESTIONNAIRE:
        excluded = await _gp_tenant_ids(db)
        tenants = [t for t in tenants if t.id not in excluded]

    if available_only:
        active_ids = {l.tenant_id for l in (await db.execute(
            select(Lease).where(Lease.is_active.is_(True), Lease.tenant_id.isnot(None))
        )).scalars().all()}
        tenants = [t for t in tenants if t.id not in active_ids]

    total = len(tenants)
    page = tenants[skip: skip + limit]
    return {
        "items": [TenantListItem.model_validate(t) for t in page],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("", response_model=TenantResponse, status_code=201, summary="Créer un locataire")
async def create_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    return await TenantService.create(db, data, created_by=current_user.id)


@router.get("/{tenant_id}", response_model=TenantResponse, summary="Fiche locataire")
async def get_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await TenantService.get_by_id(db, tenant_id)


@router.put("/{tenant_id}", response_model=TenantResponse, summary="Modifier un locataire")
async def update_tenant(
    tenant_id: uuid.UUID,
    data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_gestionnaire),
):
    return await TenantService.update(db, tenant_id, data)


@router.delete("/{tenant_id}", status_code=204, summary="Supprimer un locataire")
async def delete_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_gestionnaire),
):
    await TenantService.delete(db, tenant_id)


# ── Documents du locataire ────────────────────────────────────────────────────
@router.get("/{tenant_id}/documents", response_model=List[DocumentResponse])
async def list_tenant_documents(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await TenantService.get_by_id(db, tenant_id)  # vérif existence
    return await DocumentService.list_by_entity(db, EntityType.TENANT, tenant_id)
