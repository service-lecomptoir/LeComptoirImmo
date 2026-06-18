# -*- coding: utf-8 -*-
"""Gestion des candidatures locatives.

Centralisation des dossiers candidats (déposés depuis la page d'annonce publique
ou saisis manuellement), vérification des pièces justificatives (checklist),
analyse et comparaison des profils (taux d'effort, complétude, garant) pour
aider à la sélection du locataire le plus adapté.
"""
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role, get_manager_or_owner
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.permissions import Role
from app.database import get_db
from app.models.candidature import Candidature, CANDIDATURE_DOC_KEYS
from app.models.property import Property
from app.models.publishing import Listing
from app.models.user import User
from app.models.visit import PropertyVisitSlot
from app.utils.file_handler import get_file_path

router = APIRouter(prefix="/candidatures", tags=["Candidatures"])

_STATUSES = ("nouvelle", "documents_demandes", "en_etude", "retenue", "refusee")
_DOC_LABELS = {k: lbl for k, lbl in CANDIDATURE_DOC_KEYS}


def default_docs() -> list[dict]:
    return [
        {"key": k, "required": False, "provided": False, "verified": False,
         "file_path": None, "filename": None, "uploaded_at": None}
        for k, _ in CANDIDATURE_DOC_KEYS
    ]


def candidature_upload_url(token: str) -> str:
    from app.config import get_settings
    return f"{get_settings().PUBLIC_APP_URL.rstrip('/')}/candidature/{token}"


def candidature_visit_url(token: str) -> str:
    from app.config import get_settings
    return f"{get_settings().PUBLIC_APP_URL.rstrip('/')}/candidature/{token}/visite"


def format_property_address(prop) -> Optional[str]:
    """Adresse postale du bien (sans le nom du logement) : rue, CP ville, pays."""
    if prop is None:
        return None
    line1 = ", ".join(p for p in [(prop.address or "").strip(), (getattr(prop, "address2", None) or "").strip()] if p)
    line2 = " ".join(p for p in [(prop.zip_code or "").strip(), (prop.city or "").strip()] if p)
    country = (getattr(prop, "country", None) or "").strip()
    if country and country.lower() == "france":
        country = ""
    parts = [p for p in [line1, line2, country] if p]
    return ", ".join(parts) or None


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
    status: Optional[str] = Field(None, pattern="^(nouvelle|documents_demandes|en_etude|retenue|refusee)$")
    docs: Optional[list] = None
    notes: Optional[str] = Field(None, max_length=4000)


class RequestDocumentsIn(BaseModel):
    doc_keys: List[str] = Field(..., min_length=1)
    message: Optional[str] = Field(None, max_length=2000)


class MessageIn(BaseModel):
    message: Optional[str] = Field(None, max_length=2000)


class VisitSlotIn(BaseModel):
    property_id: uuid.UUID
    starts_at: datetime
    duration_min: int = Field(30, ge=5, le=480)
    capacity: int = Field(1, ge=1, le=50)
    notes: Optional[str] = Field(None, max_length=300)


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
    # Propriétaire (lecture seule) : strictement SES biens (bailleur rattaché).
    if role == Role.PROPRIETAIRE:
        return set((await db.execute(
            select(Property.id).where(Property.owner_user_id == user.id)
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


def _doc_out(d: dict) -> dict:
    """Pièce de la checklist enrichie pour l'affichage gestionnaire."""
    return {
        "key": d.get("key"),
        "label": _DOC_LABELS.get(d.get("key"), d.get("key")),
        "required": bool(d.get("required")),
        "provided": bool(d.get("provided")),
        "verified": bool(d.get("verified")),
        "filename": d.get("filename"),
        "uploaded_at": d.get("uploaded_at"),
        "has_file": bool(d.get("file_path")),
    }


def _out(c: Candidature, rent_ref: Optional[float] = None,
         prop_ref: Optional[str] = None, visit_at=None) -> dict:
    # Normalise pour l'affichage : inclut les nouvelles pièces standard même pour
    # les dossiers créés avant leur ajout (sans modifier la base).
    docs = _ensure_doc_fields(c.docs)
    return {
        "id": c.id,
        "property_id": c.property_id,
        "property_ref": prop_ref,
        "full_name": c.full_name,
        "email": c.email,
        "phone": c.phone,
        "employment": c.employment,
        "monthly_income": float(c.monthly_income) if c.monthly_income is not None else None,
        "has_guarantor": c.has_guarantor,
        "message": c.message,
        "status": c.status,
        "docs": [_doc_out(d) for d in docs],
        "notes": c.notes,
        "source": c.source,
        "created_at": c.created_at,
        "upload_token": c.upload_token,
        "upload_url": candidature_upload_url(c.upload_token) if c.upload_token else None,
        "visit_url": candidature_visit_url(c.upload_token) if c.upload_token else None,
        "visit_invited": bool(c.visit_invited_at),
        "visit_slot_id": str(c.visit_slot_id) if c.visit_slot_id else None,
        "visit_booked_at": visit_at,
        "metrics": _metrics(c, rent_ref),
    }


async def _rent_ref(db: AsyncSession, property_id) -> Optional[float]:
    """Loyer de référence pour le taux d'effort : prix de l'annonce du bien."""
    listing = (await db.execute(
        select(Listing).where(Listing.property_id == property_id)
    )).scalar_one_or_none()
    return float(listing.price) if (listing and listing.price is not None) else None


async def _full_out(db: AsyncSession, c: Candidature) -> dict:
    """Sérialise une candidature avec sa réf. de bien et son créneau de visite."""
    rent = await _rent_ref(db, c.property_id)
    prop = await db.get(Property, c.property_id)
    prop_ref = getattr(prop, "ref_code", None) if prop else None
    visit_at = None
    if c.visit_slot_id:
        slot = await db.get(PropertyVisitSlot, c.visit_slot_id)
        visit_at = slot.starts_at.isoformat() if slot else None
    return _out(c, rent, prop_ref, visit_at)


async def _listing_pricing(db: AsyncSession, property_id):
    """(loyer hors charges, charges) du bien : depuis l'annonce en priorité, sinon
    repli sur le bail le plus récent du bien (utile pour une candidature sans
    annonce publiée)."""
    listing = (await db.execute(
        select(Listing).where(Listing.property_id == property_id)
        .order_by(Listing.created_at.desc())
    )).scalars().first()
    price = float(listing.price) if (listing and listing.price is not None) else None
    charges = float(listing.charges) if (listing and getattr(listing, "charges", None) is not None) else None
    if price is None:
        from app.models.lease import Lease
        lease = (await db.execute(
            select(Lease).where(Lease.property_id == property_id)
            .order_by(Lease.created_at.desc())
        )).scalars().first()
        if lease is not None:
            if lease.rent_amount is not None:
                price = float(lease.rent_amount)
            if charges is None and lease.charges_amount is not None:
                charges = float(lease.charges_amount)
    return price, charges


async def _property_block(db: AsyncSession, prop) -> dict:
    """Descriptif du logement pour les e-mails candidat : adresse, caractéristiques,
    loyer hors charges + charges + total (jamais le nom du logement).
    Retourne {ref, address, price, html}."""
    ref = getattr(prop, "ref_code", None) if prop else None
    address = format_property_address(prop)
    price, charges = (await _listing_pricing(db, prop.id)) if prop else (None, None)
    chips: list[str] = []
    if prop:
        pt = (getattr(prop, "property_type", None) or "").strip()
        if pt:
            chips.append(pt.capitalize())
        if getattr(prop, "typology", None):
            chips.append(str(prop.typology))
        if getattr(prop, "area_sqm", None) is not None:
            chips.append(f"{float(prop.area_sqm):g} m²")
        if getattr(prop, "furnished", False):
            chips.append("Meublé")
    rows = []
    if address:
        rows.append(f'<p style="margin:2px 0;color:#374151"><strong>Adresse :</strong> {address}</p>')
    if chips:
        rows.append(f'<p style="margin:2px 0;color:#374151"><strong>Caractéristiques :</strong> {" · ".join(chips)}</p>')
    if price is not None:
        rows.append(f'<p style="margin:2px 0;color:#374151"><strong>Loyer hors charges :</strong> {price:.0f} € / mois</p>')
    if charges is not None:
        rows.append(f'<p style="margin:2px 0;color:#374151"><strong>Charges :</strong> {charges:.0f} € / mois</p>')
    if price is not None and charges is not None:
        rows.append(f'<p style="margin:2px 0;color:#374151"><strong>Total :</strong> {price + charges:.0f} € charges comprises / mois</p>')
    html = ""
    if rows:
        html = ('<div style="border:1px solid #e5e7eb;border-radius:8px;padding:12px 16px;'
                'margin:16px 0;background:#f9fafb">'
                '<p style="margin:0 0 6px;font-weight:600;color:#0D2F5C">Le logement</p>'
                + "".join(rows) + '</div>')
    return {"ref": ref, "address": address, "price": price, "html": html}


def _fmt_when(dt) -> str:
    """Formate une date/heure (UTC) en heure locale (Europe/Paris) lisible."""
    try:
        from zoneinfo import ZoneInfo
        dt = dt.astimezone(ZoneInfo("Europe/Paris"))
    except Exception:  # noqa: BLE001
        pass
    return dt.strftime("%d/%m/%Y à %Hh%M")


async def send_candidature_visit_reminder(db: AsyncSession, c: Candidature) -> bool:
    """Envoie au candidat la relance avant visite (et marque l'envoi). Réutilisé
    par le bouton manuel et la relance automatique de la veille."""
    if not c.visit_slot_id or not (c.email or "").strip():
        return False
    slot = await db.get(PropertyVisitSlot, c.visit_slot_id)
    if not slot:
        return False
    prop = await db.get(Property, c.property_id)
    block = await _property_block(db, prop)
    from app.services.email_service import send_visit_reminder
    ok = await send_visit_reminder(
        to=c.email, candidate_name=c.full_name,
        property_ref=block["ref"] or "votre dossier",
        when_str=_fmt_when(slot.starts_at), property_html=block["html"],
    )
    c.visit_reminded_at = datetime.now(timezone.utc)
    return ok


# ── Endpoints ──────────────────────────────────────────────────────────────────
@router.get("", summary="Liste des candidatures")
async def list_candidatures(
    property_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_manager_or_owner),
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
    # Loyer + réf. de bien par bien distinct (volumes faibles).
    rents: dict = {}
    refs: dict = {}
    for c in rows:
        if c.property_id not in rents:
            rents[c.property_id] = await _rent_ref(db, c.property_id)
            prop = await db.get(Property, c.property_id)
            refs[c.property_id] = getattr(prop, "ref_code", None) if prop else None
    # Créneaux réservés (une requête groupée).
    slot_ids = [c.visit_slot_id for c in rows if c.visit_slot_id]
    slot_at: dict = {}
    if slot_ids:
        slots = (await db.execute(
            select(PropertyVisitSlot).where(PropertyVisitSlot.id.in_(slot_ids))
        )).scalars().all()
        slot_at = {s.id: s.starts_at.isoformat() for s in slots}
    return [
        _out(c, rents.get(c.property_id), refs.get(c.property_id),
             slot_at.get(c.visit_slot_id) if c.visit_slot_id else None)
        for c in rows
    ]


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
    return await _full_out(db, c)


@router.get("/doc-keys", summary="Checklist standard des pièces")
async def doc_keys():
    return [{"key": k, "label": lbl} for k, lbl in CANDIDATURE_DOC_KEYS]


# ── Créneaux de visite (par bien) ────────────────────────────────────────────────
async def _slot_out(db: AsyncSession, slot: PropertyVisitSlot) -> dict:
    booked = (await db.execute(
        select(func.count(Candidature.id)).where(Candidature.visit_slot_id == slot.id)
    )).scalar() or 0
    return {
        "id": str(slot.id),
        "property_id": str(slot.property_id),
        "starts_at": slot.starts_at.isoformat(),
        "duration_min": slot.duration_min,
        "capacity": slot.capacity,
        "notes": slot.notes,
        "booked_count": int(booked),
        "remaining": max(0, slot.capacity - int(booked)),
    }


@router.get("/visit-slots", summary="Créneaux de visite d'un bien")
async def list_visit_slots(
    property_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_manager_or_owner),
):
    ids = await _scope_property_ids(db, user)
    if ids is not None and property_id not in ids:
        raise ForbiddenException("Ce bien n'est pas dans votre périmètre.")
    slots = (await db.execute(
        select(PropertyVisitSlot).where(PropertyVisitSlot.property_id == property_id)
        .order_by(PropertyVisitSlot.starts_at)
    )).scalars().all()
    return [await _slot_out(db, s) for s in slots]


@router.post("/visit-slots", status_code=201, summary="Ajouter un créneau de visite")
async def create_visit_slot(
    data: VisitSlotIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    ids = await _scope_property_ids(db, user)
    if ids is not None and data.property_id not in ids:
        raise ForbiddenException("Ce bien n'est pas dans votre périmètre.")
    slot = PropertyVisitSlot(
        property_id=data.property_id, starts_at=data.starts_at,
        duration_min=data.duration_min, capacity=data.capacity,
        notes=(data.notes or "").strip() or None, created_by=user.id,
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return await _slot_out(db, slot)


@router.delete("/visit-slots/{slot_id}", status_code=204, summary="Supprimer un créneau de visite")
async def delete_visit_slot(
    slot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    slot = await db.get(PropertyVisitSlot, slot_id)
    if not slot:
        raise NotFoundException("Créneau", str(slot_id))
    ids = await _scope_property_ids(db, user)
    if ids is not None and slot.property_id not in ids:
        raise ForbiddenException("Ce créneau n'est pas dans votre périmètre.")
    await db.delete(slot)
    await db.commit()


@router.get("/compare/{property_id}", summary="Comparaison des candidatures d'un bien")
async def compare_candidatures(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_manager_or_owner),
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


@router.get("/compare/{property_id}/analysis", summary="Analyse IA d'aide à la décision (candidatures)")
async def compare_ai_analysis(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_manager_or_owner),
):
    ids = await _scope_property_ids(db, user)
    if ids is not None and property_id not in ids:
        raise ForbiddenException("Ce bien n'est pas dans votre périmètre.")

    from app.services import llm_service
    if not llm_service.enabled():
        return {"analysis": None, "enabled": False}

    rent = await _rent_ref(db, property_id)
    rows = (await db.execute(
        select(Candidature).where(
            Candidature.property_id == property_id,
            Candidature.status != "refusee",
        )
    )).scalars().all()
    if not rows:
        return {"analysis": None, "enabled": True, "empty": True}

    cands = [_out(c, rent) for c in rows]
    cands.sort(key=lambda x: x["metrics"]["score"], reverse=True)
    lines = []
    for i, c in enumerate(cands, 1):
        m = c["metrics"]
        eff = f"{m['effort_ratio'] * 100:.0f} %" if m.get("effort_ratio") else "non calculé"
        inc = f"{c['monthly_income']:.0f} €" if c.get("monthly_income") is not None else "non renseignés"
        lines.append(
            f"Candidat {i} ({c['full_name']}) : score {m['score']}/100 ; taux d'effort {eff} ; "
            f"dossier complet à {m['completeness_pct']} % ; revenus {inc} ; "
            f"garant {'oui' if c['has_guarantor'] else 'non'} ; statut {c['status']}"
        )
    rent_line = f"Loyer de référence du bien : {rent:.0f} €" if rent else "Loyer de référence inconnu"

    system = (
        "Tu es un expert en sélection de locataires en France, neutre et rigoureux. À partir des "
        "DONNÉES de candidatures (déjà analysées), aide le gestionnaire à choisir. IMPORTANT : "
        "fonde-toi UNIQUEMENT sur la solvabilité et la complétude du dossier (taux d'effort, revenus, "
        "garant, pièces justificatives). N'évoque jamais l'origine, le sexe, l'âge, la situation "
        "familiale ou tout critère discriminatoire (interdits par la loi). N'invente aucune donnée.\n"
        "Réponds en français, 5 lignes maximum :\n"
        "• Recommandation : quel candidat retenir et pourquoi (1 phrase).\n"
        "• Comparatif : 1 à 2 points qui départagent les profils.\n"
        "• Réserves : pièces manquantes ou points à sécuriser avant signature."
    )
    text = await llm_service.chat(
        [{"role": "system", "content": system},
         {"role": "user", "content": rent_line + "\nCANDIDATS :\n- " + "\n- ".join(lines)}],
        temperature=0.4, max_tokens=450,
    )
    return {"analysis": text, "enabled": True}


@router.get("/{candidature_id}", summary="Détail d'une candidature")
async def get_candidature(
    candidature_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_manager_or_owner),
):
    c = await _accessible(db, user, candidature_id)
    return await _full_out(db, c)


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
        # Ne conserve que les clés connues, avec drapeaux booléens. Les
        # métadonnées de fichier déposé (file_path, filename, uploaded_at) et le
        # drapeau « requis » sont préservés depuis l'existant (jamais écrasés par
        # l'UI gestionnaire qui ne fait que basculer provided/verified).
        allowed = {k for k, _ in CANDIDATURE_DOC_KEYS}
        existing = {d.get("key"): d for d in (c.docs or [])}
        merged = []
        for d in fields.pop("docs"):
            key = d.get("key")
            if key not in allowed:
                continue
            ex = existing.get(key, {})
            merged.append({
                "key": key,
                "required": bool(d.get("required", ex.get("required", False))),
                "provided": bool(d.get("provided")),
                "verified": bool(d.get("verified")),
                "file_path": ex.get("file_path"),
                "filename": ex.get("filename"),
                "uploaded_at": ex.get("uploaded_at"),
            })
        c.docs = merged
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(c, "docs")
    for k, v in fields.items():
        setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return await _full_out(db, c)


def _ensure_doc_fields(docs: Optional[list]) -> list[dict]:
    """Normalise une checklist (anciens dossiers sans les champs récents)."""
    by_key = {d.get("key"): d for d in (docs or [])}
    out = []
    for k, _ in CANDIDATURE_DOC_KEYS:
        d = by_key.get(k, {})
        out.append({
            "key": k,
            "required": bool(d.get("required")),
            "provided": bool(d.get("provided")),
            "verified": bool(d.get("verified")),
            "file_path": d.get("file_path"),
            "filename": d.get("filename"),
            "uploaded_at": d.get("uploaded_at"),
        })
    return out


@router.post("/{candidature_id}/request-documents", summary="Demander des pièces au candidat")
async def request_documents(
    candidature_id: uuid.UUID,
    data: RequestDocumentsIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Marque les pièces sélectionnées comme requises, génère (si besoin) un lien
    public de dépôt, passe le dossier en « documents demandés » et envoie au
    candidat un e-mail avec la liste et le lien. Le gestionnaire est mis en copie."""
    c = await _accessible(db, user, candidature_id)
    if not (c.email or "").strip():
        raise BadRequestException(
            "Ce candidat n'a pas d'adresse e-mail : renseignez-la pour lui envoyer la demande."
        )
    allowed = {k for k, _ in CANDIDATURE_DOC_KEYS}
    selected = [k for k in data.doc_keys if k in allowed]
    if not selected:
        raise BadRequestException("Sélectionnez au moins une pièce connue.")

    docs = _ensure_doc_fields(c.docs)
    for d in docs:
        if d["key"] in selected:
            d["required"] = True
    c.docs = docs
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(c, "docs")

    if not c.upload_token:
        c.upload_token = secrets.token_urlsafe(24)
    if c.status not in ("retenue", "refusee"):
        c.status = "documents_demandes"

    await db.commit()
    await db.refresh(c)

    url = candidature_upload_url(c.upload_token)
    labels = [_DOC_LABELS[k] for k in selected]
    email_sent = False
    try:
        from app.services.email_service import send_candidature_documents_request
        email_sent = await send_candidature_documents_request(
            to=c.email,
            candidate_name=c.full_name,
            property_name=(await db.get(Property, c.property_id)).name if c.property_id else "votre bien",
            doc_labels=labels,
            upload_url=url,
            manager_name=getattr(user, "full_name", None),
            custom_message=(data.message or "").strip() or None,
            cc=getattr(user, "email", None),
        )
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning("Demande de pièces non envoyée (%s): %s", candidature_id, exc)

    out = await _full_out(db, c)
    out["upload_url"] = url
    out["email_sent"] = email_sent
    return out


@router.get("/{candidature_id}/documents/{key}/download", summary="Télécharger une pièce déposée")
async def download_candidature_doc(
    candidature_id: uuid.UUID,
    key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_manager_or_owner),
):
    c = await _accessible(db, user, candidature_id)
    doc = next((d for d in (c.docs or []) if d.get("key") == key), None)
    if not doc or not doc.get("file_path"):
        raise NotFoundException("Pièce", key)
    path = get_file_path(doc["file_path"])
    if not path:
        raise NotFoundException("Fichier", key)
    return FileResponse(
        path,
        filename=doc.get("filename") or f"{key}",
    )


@router.post("/{candidature_id}/invite-visit", summary="Inviter le candidat à réserver une visite")
async def invite_visit(
    candidature_id: uuid.UUID,
    data: MessageIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Envoie au candidat qualifié un e-mail l'invitant à réserver un créneau de
    visite. L'e-mail mentionne qu'il y a d'autres candidats, indique la RÉFÉRENCE
    et l'ADRESSE du bien (pour s'y rendre), mais jamais le nom du logement."""
    c = await _accessible(db, user, candidature_id)
    if not (c.email or "").strip():
        raise BadRequestException("Ce candidat n'a pas d'adresse e-mail.")
    # Au moins un créneau futur doit exister pour ce bien.
    now = datetime.now(timezone.utc)
    future = (await db.execute(
        select(func.count(PropertyVisitSlot.id)).where(
            PropertyVisitSlot.property_id == c.property_id,
            PropertyVisitSlot.starts_at >= now,
        )
    )).scalar() or 0
    if not future:
        raise BadRequestException(
            "Ajoutez d'abord au moins un créneau de visite (à venir) pour ce bien."
        )
    if not c.upload_token:
        c.upload_token = secrets.token_urlsafe(24)
    c.visit_invited_at = now
    await db.commit()
    await db.refresh(c)

    prop = await db.get(Property, c.property_id)
    block = await _property_block(db, prop)
    url = candidature_visit_url(c.upload_token)
    email_sent = False
    try:
        from app.services.email_service import send_visit_invitation
        email_sent = await send_visit_invitation(
            to=c.email, candidate_name=c.full_name,
            property_ref=block["ref"] or "votre dossier", booking_url=url,
            property_html=block["html"],
            custom_message=(data.message or "").strip() or None,
            cc=getattr(user, "email", None),
        )
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning("Invitation visite non envoyée (%s): %s", candidature_id, exc)

    out = await _full_out(db, c)
    out["visit_url"] = url
    out["email_sent"] = email_sent
    return out


@router.post("/{candidature_id}/accept", summary="Accepter le candidat (e-mail d'acceptation)")
async def accept_candidature(
    candidature_id: uuid.UUID,
    data: MessageIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Passe le dossier en « retenue » et envoie au candidat un e-mail
    d'acceptation rappelant les prochaines étapes (signature du bail, etc.)."""
    c = await _accessible(db, user, candidature_id)
    c.status = "retenue"
    await db.commit()
    await db.refresh(c)

    email_sent = False
    if (c.email or "").strip():
        prop = await db.get(Property, c.property_id)
        block = await _property_block(db, prop)
        try:
            from app.services.email_service import send_candidature_accepted
            email_sent = await send_candidature_accepted(
                to=c.email, candidate_name=c.full_name,
                property_ref=block["ref"] or "votre dossier",
                property_address=block["address"], property_html=block["html"],
                custom_message=(data.message or "").strip() or None,
                cc=getattr(user, "email", None),
            )
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).warning("E-mail d'acceptation non envoyé (%s): %s", candidature_id, exc)

    out = await _full_out(db, c)
    out["email_sent"] = email_sent
    return out


@router.post("/{candidature_id}/acknowledge", summary="Accuser réception de la candidature")
async def acknowledge_candidature(
    candidature_id: uuid.UUID,
    data: MessageIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Envoie au candidat un e-mail confirmant que sa demande a bien été prise en
    compte, avec le descriptif du logement (adresse, caractéristiques, loyer)."""
    c = await _accessible(db, user, candidature_id)
    if not (c.email or "").strip():
        raise BadRequestException("Ce candidat n'a pas d'adresse e-mail.")
    prop = await db.get(Property, c.property_id)
    block = await _property_block(db, prop)
    email_sent = False
    try:
        from app.services.email_service import send_candidature_acknowledged
        email_sent = await send_candidature_acknowledged(
            to=c.email, candidate_name=c.full_name, property_html=block["html"],
            custom_message=(data.message or "").strip() or None,
            cc=getattr(user, "email", None),
        )
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning("Accusé réception non envoyé (%s): %s", candidature_id, exc)
    out = await _full_out(db, c)
    out["email_sent"] = email_sent
    return out


@router.post("/{candidature_id}/remind-visit", summary="Relancer le candidat avant la visite")
async def remind_visit(
    candidature_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Relance manuelle avant la visite (rappel date + adresse). Nécessite que le
    candidat ait réservé un créneau."""
    c = await _accessible(db, user, candidature_id)
    if not c.visit_slot_id:
        raise BadRequestException("Le candidat n'a pas encore réservé de créneau de visite.")
    email_sent = await send_candidature_visit_reminder(db, c)
    await db.commit()
    await db.refresh(c)
    out = await _full_out(db, c)
    out["email_sent"] = email_sent
    return out


@router.delete("/{candidature_id}", status_code=204, summary="Supprimer une candidature")
async def delete_candidature(
    candidature_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    c = await _accessible(db, user, candidature_id)
    await db.delete(c)
    await db.commit()
