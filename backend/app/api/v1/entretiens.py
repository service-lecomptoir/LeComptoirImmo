import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import require_role, get_current_user
from app.models.user import User
from app.core.permissions import Role
from app.schemas.entretien import (
    PrestataireCreate, PrestataireUpdate, PrestataireResponse,
    EntretienCreate, EntretienUpdate, EntretienResponse,
)
from app.services.entretien_service import PrestataireService, EntretienService

router = APIRouter(tags=["Entretiens"])


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
        "unit_id": e.unit_id,
        "unit_label": e.unit.label if e.unit else None,
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
    _: User = Depends(require_role(Role.LECTURE)),
):
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


@entretiens_router.get("/{entretien_id}", summary="Détail entretien")
async def get_entretien(
    entretien_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.LECTURE)),
):
    e = await EntretienService.get(db, entretien_id)
    return _enrich_entretien(e)


@entretiens_router.patch("/{entretien_id}", summary="Modifier un entretien")
async def update_entretien(
    entretien_id: uuid.UUID,
    data: EntretienUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    await EntretienService.update(db, entretien_id, data)
    await db.commit()
    e = await EntretienService.get(db, entretien_id)
    return _enrich_entretien(e)


@entretiens_router.delete("/{entretien_id}", status_code=204)
async def delete_entretien(
    entretien_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    await EntretienService.delete(db, entretien_id)
    await db.commit()


router.include_router(prestataires_router)
router.include_router(entretiens_router)
