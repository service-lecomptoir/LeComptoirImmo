# -*- coding: utf-8 -*-
"""Gestion des candidatures locatives.

Centralisation des dossiers candidats (déposés depuis la page d'annonce publique
ou saisis manuellement), vérification des pièces justificatives (checklist),
analyse et comparaison des profils (taux d'effort, complétude, garant) pour
aider à la sélection du locataire le plus adapté.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.permissions import Role
from app.database import get_db
from app.models.candidature import Candidature, CANDIDATURE_DOC_KEYS
from app.models.property import Property
from app.models.publishing import Listing
from app.models.user import User

router = APIRouter(prefix="/candidatures", tags=["Candidatures"])

_STATUSES = ("nouvelle", "en_etude", "retenue", "refusee")


def default_docs() -> list[dict]:
    return [{"key": k, "provided": False, "verified": False} for k, _ in CANDIDATURE_DOC_KEYS]


# ── Schémas ────────────────────────────────────────────────────────────────────
class CandidatureIn(BaseModel):
    property_id: uuid.UUID
    full_name: str = Field(..., min_length=1, max_length=200)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=30)
    employment: Optional[str] = Field(None, max_length=150)
    monthly_income: Optional[float] = Field(None, ge=0)
    has_guarantor: bool = False
    message: Optional[str] = Field(None, max_length=4000)


class CandidatureUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=30)
    employment: Optional[str] = Field(None, max_length=150)
    monthly_income: Optional[float] = Field(None, ge=0)
    has_guarantor: Optional[bool] = None
    message: Optional[str] = Field(None, max_length=4000)
    status: Optional[str] = Field(None, pattern="^(nouvelle|en_etude|retenue|refusee)$")
    docs: Optional[list] = None
    notes: Optional[str] = Field(None, max_length=4000)


# ── Périmètre ──────────────────────────────────────────────────────────────────
async def _scope_property_ids(db: AsyncSession, user: User) -> Optional[set]:
    role = Role(user.role)
    if role == Role.ADMIN:
        return None
    if role == Role.GESTIONNAIRE_PROPRIO:
        return set((await db.execute(
            select(Property.id).where(
                (Property.created_by == user.id) | (Property.owner_user_id == user.id)
            )
        )).scalars().all())
    from app.api.v1._isolation import agency_property_ids
    return await agency_property_ids(db, user)


async def _accessible(db: AsyncSession, user: User, candidature_id: uuid.UUID) -> Candidature:
    c = await db.get(Candidature, candidature_id)
    if not c:
        raise NotFoundException("Candidature", str(candidature_id))
    ids = await _scope_property_ids(db, user)
    if ids is not None and c.property_id not in ids:
        raise ForbiddenException("Cette candidature n'est pas dans votre périmètre.")
    return c


def _metrics(c: Candidature, rent_ref: Optional[float]) -> dict:
    """Indicateurs d'analyse d'un dossier (taux d'effort, complétude, score)."""
    docs = c.docs or []
    total = max(1, len(docs))
    provided = sum(1 for d in docs if d.get("provided"))
    verified = sum(1 for d in docs if d.get("verified"))
    completeness = round(100 * (provided + verified) / (2 * total))
    income = float(c.monthly_income) if c.monthly_income is not None else None
    effort = round(rent_ref / income, 3) if (rent_ref and income) else None
    # Score d'aide à la sélection (0-100) : effort 50 pts, dossier 30 pts, garant 20 pts.
    pts = 0.0
    if effort is not None:
        pts += 50 * max(0.0, min(1.0, (0.5 - effort) / 0.3))  # 33 % d'effort ≈ 28/50 ; ≤20 % = 50/50
    pts += 30 * completeness / 100
    pts += 20 if c.has_guarantor else 0
    return {
        "effort_ratio": effort,
        "completeness_pct": completeness,
        "docs_provided": provided,
        "docs_verified": verified,
        "docs_total": len(docs),
        "score": round(pts),
    }


def _out(c: Candidature, rent_ref: Optional[float] = None) -> dict:
    return {
        "id": c.id,
        "property_id": c.property_id,
        "full_name": c.full_name,
        "email": c.email,
        "phone": c.phone,
        "employment": c.employment,
        "monthly_income": float(c.monthly_income) if c.monthly_income is not None else None,
        "has_guarantor": c.has_guarantor,
        "message": c.message,
        "status": c.status,
        "docs": c.docs or [],
        "notes": c.notes,
        "source": c.source,
        "created_at": c.created_at,
        "metrics": _metrics(c, rent_ref),
    }


async def _rent_ref(db: AsyncSession, property_id) -> Optional[float]:
    """Loyer de référence pour le taux d'effort : prix de l'annonce du bien."""
    listing = (await db.execute(
        select(Listing).where(Listing.property_id == property_id)
    )).scalar_one_or_none()
    return float(listing.price) if (listing and listing.price is not None) else None


# ── Endpoints ──────────────────────────────────────────────────────────────────
@router.get("", summary="Liste des candidatures")
async def list_candidatures(
    property_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    ids = await _scope_property_ids(db, user)
    q = select(Candidature).order_by(Candidature.created_at.desc())
    if ids is not None:
        if not ids:
            return []
        q = q.where(Candidature.property_id.in_(ids))
    if property_id:
        q = q.where(Candidature.property_id == property_id)
    if status in _STATUSES:
        q = q.where(Candidature.status == status)
    rows = (await db.execute(q)).scalars().all()
    # Loyer de référence par bien (une requête par bien distinct, volumes faibles)
    rents: dict = {}
    for c in rows:
        if c.property_id not in rents:
            rents[c.property_id] = await _rent_ref(db, c.property_id)
    return [_out(c, rents.get(c.property_id)) for c in rows]


@router.post("", status_code=201, summary="Ajouter une candidature (saisie manuelle)")
async def create_candidature(
    data: CandidatureIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    ids = await _scope_property_ids(db, user)
    if ids is not None and data.property_id not in ids:
        raise ForbiddenException("Ce bien n'est pas dans votre périmètre.")
    c = Candidature(
        property_id=data.property_id,
        full_name=data.full_name.strip(),
        email=(data.email or "").strip() or None,
        phone=(data.phone or "").strip() or None,
        employment=(data.employment or "").strip() or None,
        monthly_income=data.monthly_income,
        has_guarantor=data.has_guarantor,
        message=(data.message or "").strip() or None,
        docs=default_docs(),
        source="manuel",
        created_by=user.id,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _out(c, await _rent_ref(db, c.property_id))


@router.get("/doc-keys", summary="Checklist standard des pièces")
async def doc_keys():
    return [{"key": k, "label": lbl} for k, lbl in CANDIDATURE_DOC_KEYS]


@router.get("/compare/{property_id}", summary="Comparaison des candidatures d'un bien")
async def compare_candidatures(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Profils côte à côte (hors refusées), triés par score décroissant — le premier
    est le candidat recommandé."""
    ids = await _scope_property_ids(db, user)
    if ids is not None and property_id not in ids:
        raise ForbiddenException("Ce bien n'est pas dans votre périmètre.")
    rent = await _rent_ref(db, property_id)
    rows = (await db.execute(
        select(Candidature).where(
            Candidature.property_id == property_id,
            Candidature.status != "refusee",
        )
    )).scalars().all()
    out = [_out(c, rent) for c in rows]
    out.sort(key=lambda x: x["metrics"]["score"], reverse=True)
    return {"rent_reference": rent, "candidates": out}


@router.get("/{candidature_id}", summary="Détail d'une candidature")
async def get_candidature(
    candidature_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    c = await _accessible(db, user, candidature_id)
    return _out(c, await _rent_ref(db, c.property_id))


@router.patch("/{candidature_id}", summary="Mettre à jour une candidature")
async def update_candidature(
    candidature_id: uuid.UUID,
    data: CandidatureUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    c = await _accessible(db, user, candidature_id)
    fields = data.model_dump(exclude_unset=True)
    if "docs" in fields and fields["docs"] is not None:
        # Ne conserve que les clés connues, avec drapeaux booléens.
        allowed = {k for k, _ in CANDIDATURE_DOC_KEYS}
        c.docs = [
            {"key": d.get("key"), "provided": bool(d.get("provided")), "verified": bool(d.get("verified"))}
            for d in fields.pop("docs") if d.get("key") in allowed
        ]
    for k, v in fields.items():
        setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return _out(c, await _rent_ref(db, c.property_id))


@router.delete("/{candidature_id}", status_code=204, summary="Supprimer une candidature")
async def delete_candidature(
    candidature_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    c = await _accessible(db, user, candidature_id)
    await db.delete(c)
    await db.commit()
