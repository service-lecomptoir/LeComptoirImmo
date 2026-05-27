import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from app.database import get_db
from app.api.deps import get_current_user, get_current_gestionnaire
from app.core.permissions import Role
from app.api.v1._isolation import gp_owner_ids as _gp_owner_ids
from app.models.user import User
from app.models.document import EntityType
from app.schemas.owner import OwnerCreate, OwnerUpdate, OwnerResponse, OwnerListItem
from app.schemas.document import DocumentResponse
from app.services.owner_service import OwnerService
from app.services.document_service import DocumentService

router = APIRouter(prefix="/owners", tags=["Propriétaires"])


@router.get("", response_model=dict, summary="Liste des propriétaires")
async def list_owners(
    search: Optional[str] = Query(None, description="Recherche par nom, société, email, téléphone"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    available_only: bool = Query(False, description="Exclure les propriétaires déjà rattachés à un bien"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste paginée des fiches propriétaire (réservé aux rôles de gestion)."""
    role = Role(current_user.role)
    if role in (Role.LOCATAIRE, Role.PROPRIETAIRE):
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    owners, _ = await OwnerService.list_all(db, search=search, skip=0, limit=2000)

    if role == Role.GESTIONNAIRE:
        # Gestionnaire mandataire : exclure les propriétaires des gestionnaire_proprio
        excluded = await _gp_owner_ids(db)
        owners = [o for o in owners if o.id not in excluded]
    elif role == Role.GESTIONNAIRE_PROPRIO:
        owners = [o for o in owners if o.created_by == current_user.id]

    if available_only:
        from app.models.property import Property
        linked_ids = {
            oid for oid in (await db.execute(
                select(Property.owner_id).where(Property.owner_id.isnot(None))
            )).scalars().all()
        }
        owners = [o for o in owners if o.id not in linked_ids]

    total = len(owners)
    page = owners[skip: skip + limit]
    return {
        "items": [OwnerListItem.model_validate(o) for o in page],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("", response_model=OwnerResponse, status_code=201, summary="Créer un propriétaire")
async def create_owner(
    data: OwnerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    return await OwnerService.create(db, data, created_by=current_user.id)


@router.get("/{owner_id}", response_model=OwnerResponse, summary="Fiche propriétaire")
async def get_owner(
    owner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await OwnerService.get_by_id(db, owner_id)


@router.put("/{owner_id}", response_model=OwnerResponse, summary="Modifier un propriétaire")
async def update_owner(
    owner_id: uuid.UUID,
    data: OwnerUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_gestionnaire),
):
    return await OwnerService.update(db, owner_id, data)


@router.delete("/{owner_id}", status_code=204, summary="Supprimer un propriétaire")
async def delete_owner(
    owner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_gestionnaire),
):
    await OwnerService.delete(db, owner_id)


# ── Documents du propriétaire ──────────────────────────────────────────────────
@router.get("/{owner_id}/documents", response_model=List[DocumentResponse])
async def list_owner_documents(
    owner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await OwnerService.get_by_id(db, owner_id)  # vérif existence
    return await DocumentService.list_by_entity(db, EntityType.OWNER, owner_id)
