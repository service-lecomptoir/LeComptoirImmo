import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import require_role, get_current_user
from app.api.v1._isolation import agency_property_ids, assert_manager_scope
from app.models.user import User
from app.core.permissions import Role
from app.schemas.entretien import (
    PrestataireCreate, PrestataireUpdate, PrestataireResponse,
    EntretienCreate, EntretienUpdate, EntretienResponse,
)
from app.services.entretien_service import PrestataireService, EntretienService
from app.models.entretien import EntretienStatus

router = APIRouter(tags=["Entretiens"])


async def _assert_entretien_scope(db: AsyncSession, user: User, e) -> None:
    """Isolation d'un entretien via le bien rattaché (created_by de la propriété)."""
    from app.models.property import Property
    created_by = None
    if getattr(e, "property_id", None):
        p = await db.get(Property, e.property_id)
        created_by = getattr(p, "created_by", None) if p else None
    await assert_manager_scope(db, user, created_by, "cet entretien")


async def _autoplan_scope(db: AsyncSession, current_user: User):
    """Retourne (allowed_props, excluded_props) pour borner la planification au périmètre du rôle."""
    role = Role(current_user.role)
    if role == Role.GESTIONNAIRE_PROPRIO:
        from app.models.property import Property
        own = {p.id for p in (await db.execute(
            select(Property).where(Property.owner_user_id == current_user.id)
        )).scalars().all()}
        return own, None
    if role == Role.GESTIONNAIRE:
        # Mandataire : borné aux biens de SON agence
        return await agency_property_ids(db, current_user), None
    return None, None  # admin


def _enrich_entretien(e) -> dict:
    return {
        "id": e.id,
        "title": e.title,
        "description": e.description,
        "type": e.type,
        "status": e.status,
        "frequency": e.frequency,
        "scheduled_date": e.scheduled_date,
        "completed_date": e.completed_date,
        "next_date": e.next_date,
        "cost": float(e.cost) if e.cost else None,
        "property_id": e.property_id,
        "property_label": e.property.address if e.property else None,
        "prestataire_id": e.prestataire_id,
        "prestataire_name": e.prestataire.name if e.prestataire else None,
        "notes": e.notes,
        "created_at": e.created_at,
        "updated_at": e.updated_at,
    }


# ── Prestataires ──────────────────────────────────────────────────────────────

prestataires_router = APIRouter(prefix="/prestataires")


@prestataires_router.get("", summary="Liste des prestataires")
async def list_prestataires(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.LECTURE)),
):
    items = await PrestataireService.list_all(db, active_only=active_only)
    return items


@prestataires_router.post("", status_code=201, summary="Créer un prestataire")
async def create_prestataire(
    data: PrestataireCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    p = await PrestataireService.create(db, data)
    await db.commit()
    return p


@prestataires_router.get("/{prestataire_id}", response_model=PrestataireResponse)
async def get_prestataire(
    prestataire_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.LECTURE)),
):
    return await PrestataireService.get(db, prestataire_id)


@prestataires_router.patch("/{prestataire_id}", response_model=PrestataireResponse)
async def update_prestataire(
    prestataire_id: uuid.UUID,
    data: PrestataireUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    p = await PrestataireService.update(db, prestataire_id, data)
    await db.commit()
    return p


@prestataires_router.delete("/{prestataire_id}", status_code=204)
async def delete_prestataire(
    prestataire_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    await PrestataireService.delete(db, prestataire_id)
    await db.commit()


# ── Entretiens ────────────────────────────────────────────────────────────────

entretiens_router = APIRouter(prefix="/entretiens")


@entretiens_router.get("", summary="Liste des entretiens")
async def list_entretiens(
    status: Optional[str] = Query(None),
    property_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.LECTURE)),
):
    if Role(current_user.role) == Role.GESTIONNAIRE_PROPRIO:
        from app.models.property import Property
        own_prop_ids = [p.id for p in (await db.execute(
            select(Property).where(Property.owner_user_id == current_user.id)
        )).scalars().all()]
        if not own_prop_ids:
            return {"total": 0, "items": []}
        # Respecter le filtre property_id si fourni, mais uniquement parmi ses biens
        pid = property_id if (property_id and property_id in own_prop_ids) else None
        if property_id and property_id not in own_prop_ids:
            return {"total": 0, "items": []}
        all_items = []
        for oid in (own_prop_ids if not pid else [pid]):
            chunk, _ = await EntretienService.list_all(db, status=status, property_id=oid, limit=limit, offset=0)
            all_items.extend(chunk)
        return {"total": len(all_items), "items": [_enrich_entretien(e) for e in all_items]}

    # Gestionnaire mandataire : uniquement les entretiens des biens de SON agence
    if Role(current_user.role) == Role.GESTIONNAIRE:
        allowed = await agency_property_ids(db, current_user)
        if property_id and property_id not in allowed:
            return {"total": 0, "items": []}
        all_items, _ = await EntretienService.list_all(db, status=status, property_id=property_id, limit=5000, offset=0)
        filtered = [e for e in all_items if e.property_id in allowed]
        page = filtered[offset: offset + limit]
        return {"total": len(filtered), "items": [_enrich_entretien(e) for e in page]}

    items, total = await EntretienService.list_all(
        db, status=status, property_id=property_id, limit=limit, offset=offset
    )
    return {"total": total, "items": [_enrich_entretien(e) for e in items]}


@entretiens_router.post("", status_code=201, summary="Créer un entretien")
async def create_entretien(
    data: EntretienCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    e = await EntretienService.create(db, data)
    await db.commit()
    return {"id": e.id}


@entretiens_router.post("/autoplan", summary="Planifier automatiquement d'après l'historique")
async def autoplan_entretiens(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Analyse l'historique des entretiens terminés et crée la prochaine
    maintenance de chaque série récurrente (statut Planifié). Idempotent."""
    allowed, excluded = await _autoplan_scope(db, current_user)
    created = await EntretienService.autoplan(db, allowed_props=allowed, excluded_props=excluded)
    await db.commit()
    return {"created": len(created), "items": created}


@entretiens_router.get("/{entretien_id}", summary="Détail entretien")
async def get_entretien(
    entretien_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.LECTURE)),
):
    e = await EntretienService.get(db, entretien_id)
    await _assert_entretien_scope(db, current_user, e)
    return _enrich_entretien(e)


@entretiens_router.patch("/{entretien_id}", summary="Modifier un entretien")
async def update_entretien(
    entretien_id: uuid.UUID,
    data: EntretienUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    _existing = await EntretienService.get(db, entretien_id)
    await _assert_entretien_scope(db, current_user, _existing)
    await EntretienService.update(db, entretien_id, data)
    e = await EntretienService.get(db, entretien_id)
    # Planification automatique : un entretien marqué « terminé » planifie la suivante.
    if str(e.status) == EntretienStatus.TERMINE.value and e.property_id is not None:
        await EntretienService.autoplan(db, allowed_props={e.property_id})
    await db.commit()
    e = await EntretienService.get(db, entretien_id)
    return _enrich_entretien(e)


@entretiens_router.delete("/{entretien_id}", status_code=204)
async def delete_entretien(
    entretien_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    _existing = await EntretienService.get(db, entretien_id)
    await _assert_entretien_scope(db, current_user, _existing)
    await EntretienService.delete(db, entretien_id)
    await db.commit()


router.include_router(prestataires_router)
router.include_router(entretiens_router)
