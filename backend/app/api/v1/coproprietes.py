import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_gestionnaire, get_current_manager
from app.api.v1._isolation import agency_member_ids, assert_manager_scope
from app.core.permissions import Role
from app.database import get_db
from app.models.copropriete import CoproLot, CoproLotTantieme
from app.models.user import User
from app.schemas.copropriete import (
    CoproprieteCreate,
    CoproprieteDetail,
    CoproprieteListItem,
    CoproprieteUpdate,
    LotCreate,
    LotResponse,
    LotUpdate,
    RepartitionKeyCreate,
    RepartitionKeyResponse,
    RepartitionKeyUpdate,
)
from app.services.copropriete_service import CoproprieteService

router = APIRouter(prefix="/coproprietes", tags=["Syndic (copropriété)"])


async def _scope_member_ids(db: AsyncSession, user: User) -> set[uuid.UUID] | None:
    """Périmètre de visibilité : None = tout (admin) ; sinon set d'ids autorisés."""
    role = Role(user.role)
    if role == Role.ADMIN:
        return None
    if role == Role.GESTIONNAIRE_PROPRIO:
        return {user.id}
    # Gestionnaire mandataire / comptable : périmètre agence.
    return await agency_member_ids(db, user)


async def _serialize_lot(db: AsyncSession, lot: CoproLot) -> LotResponse:
    rows = (
        (await db.execute(select(CoproLotTantieme).where(CoproLotTantieme.lot_id == lot.id)))
        .scalars()
        .all()
    )
    return LotResponse(
        id=lot.id,
        numero=lot.numero,
        lot_type=lot.lot_type,
        floor=lot.floor,
        description=lot.description,
        owner_id=lot.owner_id,
        owner_name=await CoproprieteService.owner_name(db, lot.owner_id),
        property_id=lot.property_id,
        tantiemes={str(r.key_id): float(r.tantiemes or 0) for r in rows},
    )


# ── Copropriétés ───────────────────────────────────────────────────────────────
@router.get("", response_model=list[CoproprieteListItem], summary="Liste des copropriétés")
async def list_coproprietes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    member_ids = await _scope_member_ids(db, current_user)
    return await CoproprieteService.list_for_member_ids(db, member_ids)


@router.post("", response_model=CoproprieteDetail, status_code=201, summary="Créer une copropriété")
async def create_copropriete(
    data: CoproprieteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    copro = await CoproprieteService.create(db, data, created_by=current_user.id)
    return await CoproprieteService.get_detail(db, copro.id)


@router.get("/{copro_id}", response_model=CoproprieteDetail, summary="Détail d'une copropriété")
async def get_copropriete(
    copro_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    copro = await CoproprieteService.get_by_id(db, copro_id)
    await assert_manager_scope(db, current_user, copro.created_by, "cette copropriété")
    return await CoproprieteService.get_detail(db, copro_id)


@router.put("/{copro_id}", response_model=CoproprieteDetail, summary="Modifier une copropriété")
async def update_copropriete(
    copro_id: uuid.UUID,
    data: CoproprieteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    copro = await CoproprieteService.get_by_id(db, copro_id)
    await assert_manager_scope(db, current_user, copro.created_by, "cette copropriété")
    await CoproprieteService.update(db, copro_id, data)
    return await CoproprieteService.get_detail(db, copro_id)


@router.delete("/{copro_id}", status_code=204, summary="Supprimer une copropriété")
async def delete_copropriete(
    copro_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    copro = await CoproprieteService.get_by_id(db, copro_id)
    await assert_manager_scope(db, current_user, copro.created_by, "cette copropriété")
    await CoproprieteService.delete(db, copro_id)


# ── Clés de répartition ────────────────────────────────────────────────────────
async def _assert_copro(db: AsyncSession, user: User, copro_id: uuid.UUID):
    copro = await CoproprieteService.get_by_id(db, copro_id)
    await assert_manager_scope(db, user, copro.created_by, "cette copropriété")
    return copro


@router.post(
    "/{copro_id}/keys",
    response_model=RepartitionKeyResponse,
    status_code=201,
    summary="Ajouter une clé de répartition",
)
async def add_key(
    copro_id: uuid.UUID,
    data: RepartitionKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    key = await CoproprieteService.add_key(db, copro_id, data)
    return RepartitionKeyResponse(
        id=key.id,
        name=key.name,
        total_tantiemes=key.total_tantiemes,
        is_general=key.is_general,
        position=key.position,
        assigned_tantiemes=0,
        balanced=(key.total_tantiemes == 0),
    )


@router.put(
    "/{copro_id}/keys/{key_id}",
    response_model=RepartitionKeyResponse,
    summary="Modifier une clé de répartition",
)
async def update_key(
    copro_id: uuid.UUID,
    key_id: uuid.UUID,
    data: RepartitionKeyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    key = await CoproprieteService.update_key(db, copro_id, key_id, data)
    return RepartitionKeyResponse(
        id=key.id,
        name=key.name,
        total_tantiemes=key.total_tantiemes,
        is_general=key.is_general,
        position=key.position,
    )


@router.delete("/{copro_id}/keys/{key_id}", status_code=204, summary="Supprimer une clé")
async def delete_key(
    copro_id: uuid.UUID,
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    await CoproprieteService.delete_key(db, copro_id, key_id)


# ── Lots ───────────────────────────────────────────────────────────────────────
@router.post(
    "/{copro_id}/lots",
    response_model=LotResponse,
    status_code=201,
    summary="Ajouter un lot",
)
async def create_lot(
    copro_id: uuid.UUID,
    data: LotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    lot = await CoproprieteService.create_lot(db, copro_id, data)
    return await _serialize_lot(db, lot)


@router.put("/{copro_id}/lots/{lot_id}", response_model=LotResponse, summary="Modifier un lot")
async def update_lot(
    copro_id: uuid.UUID,
    lot_id: uuid.UUID,
    data: LotUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    lot = await CoproprieteService.update_lot(db, copro_id, lot_id, data)
    return await _serialize_lot(db, lot)


@router.delete("/{copro_id}/lots/{lot_id}", status_code=204, summary="Supprimer un lot")
async def delete_lot(
    copro_id: uuid.UUID,
    lot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    await CoproprieteService.delete_lot(db, copro_id, lot_id)
