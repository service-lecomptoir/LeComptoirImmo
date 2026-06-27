"""
Endpoints publics (sans authentification) : page d'accueil Le Comptoir Immo.

Les plans et les demandes de souscription/démo proviennent d'Alice (source de
vérité, base dédiée) via son API /internal (app.services.alice_client) : plus
aucune lecture/écriture directe des tables alice_*.
"""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.property import Property
from app.models.user import User
from app.services import alice_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/public", tags=["Public"])


class PublicPlanOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    property_limit: int | None = None
    monthly_price: float
    manager_type: str | None = None
    features: list[str] | None = None


@router.get("/features", summary="Catalogue des fonctionnalités (source unique)")
async def list_features():
    """Catalogue canonique des fonctionnalités : clé, libellé, description, catégorie.
    Source unique consommée par la page Tarification, le Guide utilisateur et
    l'éditeur de plans LeComptoir Alice (liste dynamique).

    Donnée publique, non authentifiée : CORS ouvert (`*`) pour permettre le fetch
    cross-origin depuis LeComptoir Alice sans dépendre de la liste CORS_ORIGINS."""
    from app.core.feature_catalog import public_catalog

    return JSONResponse(
        content=public_catalog(),
        headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=300"},
    )


@router.get("/plans", response_model=list[PublicPlanOut], summary="Plans tarifaires publics")
async def list_public_plans():
    """Plans actifs pour la page Tarification publique (via l'API Alice).
    `features = null` ⇒ toutes les fonctionnalités. Fail-soft → [] si Alice KO."""
    plans = await alice_client.list_plans()
    return [
        PublicPlanOut(
            id=str(p.get("id")),
            name=p.get("name"),
            description=p.get("description"),
            property_limit=p.get("property_limit"),
            monthly_price=float(p.get("monthly_price") or 0),
            manager_type=p.get("manager_type"),
            features=p.get("features") if isinstance(p.get("features"), list) else None,
        )
        for p in plans
    ]


async def _notify_team(data: "SubscriptionRequestIn", message: str | None) -> None:
    """Best-effort : notifie l'équipe par email (n'échoue jamais la requête).
    `message` inclut éventuellement la formule souhaitée."""
    try:
        from app.config import get_settings
        from app.services.email_service import send_subscription_lead_notification

        cfg = get_settings()
        recipient = cfg.LEADS_NOTIFY_EMAIL or cfg.FIRST_ADMIN_EMAIL
        await send_subscription_lead_notification(
            to=recipient,
            full_name=data.full_name.strip(),
            email=str(data.email).lower(),
            phone=data.phone,
            company=data.company,
            message=message,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Notification de souscription non envoyée : %s", exc)


class SubscriptionRequestIn(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(..., min_length=6, max_length=30)
    company: str | None = Field(None, max_length=200)
    message: str | None = Field(None, max_length=2000)
    plan_id: str | None = Field(None, max_length=64)
    plan_label: str | None = Field(None, max_length=200)


@router.post("/subscription-requests", status_code=201, summary="Demande de souscription / démo")
async def create_subscription_request(
    data: SubscriptionRequestIn,
    background: BackgroundTasks,
):
    """Enregistre une demande publique côté Alice (à traiter dans « Demandes »).
    La formule choisie est jointe au message du lead (visible dans « Demandes »)."""
    plan_line = f"Formule souhaitée : {data.plan_label}" if data.plan_label else None
    composed = "\n\n".join(x for x in (plan_line, data.message) if x) or None
    await alice_client.create_lead(
        full_name=data.full_name.strip(),
        email=str(data.email).lower(),
        phone=data.phone,
        company=data.company,
        message=composed,
        source="site_lecomptoir",
    )
    background.add_task(_notify_team, data, composed)
    return {"status": "received"}


# ── Dépôt des pièces par un candidat (lien public, sans authentification) ────────
async def _candidature_by_token(db: AsyncSession, token: str):
    from app.models.candidature import Candidature

    c = (
        await db.execute(select(Candidature).where(Candidature.upload_token == token))
    ).scalar_one_or_none()
    if not c or c.status == "refusee":
        raise HTTPException(status_code=404, detail="Lien introuvable ou expiré")
    return c


@router.get("/candidature/{token}", summary="Pièces demandées à un candidat (lien public)")
async def public_candidature(token: str, db: AsyncSession = Depends(get_db)):
    from app.models.candidature import CANDIDATURE_DOC_KEYS
    from app.models.property import Property

    c = await _candidature_by_token(db, token)
    labels = {k: lbl for k, lbl in CANDIDATURE_DOC_KEYS}
    prop = await db.get(Property, c.property_id)
    requested = [
        {
            "key": d.get("key"),
            "label": labels.get(d.get("key"), d.get("key")),
            "provided": bool(d.get("provided")),
            "verified": bool(d.get("verified")),
            "filename": d.get("filename"),
        }
        for d in (c.docs or [])
        if d.get("required")
    ]
    return {
        "candidate_name": c.full_name,
        "property_name": prop.name if prop else "le bien",
        "status": c.status,
        "documents": requested,
        "all_provided": bool(requested) and all(d["provided"] for d in requested),
    }


@router.post("/candidature/{token}/upload", summary="Déposer une pièce (candidat)")
async def public_candidature_upload(
    token: str,
    key: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm.attributes import flag_modified

    from app.utils.file_handler import save_file

    c = await _candidature_by_token(db, token)
    docs = [dict(d) for d in (c.docs or [])]  # copie profonde (nouveaux dicts)
    target = next((d for d in docs if d.get("key") == key and d.get("required")), None)
    if target is None:
        raise HTTPException(status_code=400, detail="Cette pièce n'est pas demandée.")

    file_path, _size = await save_file(file, entity_type="candidature", entity_id=str(c.id))
    target["provided"] = True
    target["file_path"] = file_path
    target["filename"] = file.filename
    target["uploaded_at"] = datetime.now(UTC).isoformat()
    # Réassignation + flag_modified : sans cela, la mutation JSONB n'est pas
    # détectée par SQLAlchemy et le dépôt n'est pas persisté.
    c.docs = docs
    flag_modified(c, "docs")
    await db.commit()
    return {"status": "uploaded", "key": key, "filename": file.filename}


@router.post("/candidature/{token}/submit", summary="Confirmer le dépôt des pièces (candidat)")
async def public_candidature_submit(token: str, db: AsyncSession = Depends(get_db)):
    """Le candidat indique avoir transmis ses pièces : notifie le gestionnaire."""
    from app.models.property import Property

    c = await _candidature_by_token(db, token)
    try:
        prop = await db.get(Property, c.property_id)
        mgr = await db.get(User, prop.created_by) if (prop and prop.created_by) else None
        pname = prop.name if prop else "votre bien"
        if mgr and getattr(mgr, "email", None):
            from app.services.email_service import send_email

            await send_email(
                to=mgr.email,
                subject=f"Pièces transmises : {c.full_name} ({pname})",
                html_body=(
                    f"<p><strong>{c.full_name}</strong> a transmis ses pièces justificatives "
                    f"pour <strong>{pname}</strong>.</p>"
                    f"<p>Vous pouvez les consulter et mettre le dossier à l'étude dans « Candidatures ».</p>"
                ),
            )
        if mgr and getattr(mgr, "phone", None):
            from app.services.sms_service import send_sms

            await send_sms(
                mgr.phone, f"Le Comptoir Immo : {c.full_name} a transmis ses pièces ({pname})."
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Notif dépôt pièces échouée: %s", exc)
    return {"status": "submitted"}


# ── Réservation de visite par le candidat (lien public) ──────────────────────────
@router.get("/candidature/{token}/visits", summary="Créneaux de visite proposés (candidat)")
async def public_candidature_visits(token: str, db: AsyncSession = Depends(get_db)):
    from datetime import datetime as _dt

    from sqlalchemy import func as _func

    from app.models.candidature import Candidature
    from app.models.property import Property
    from app.models.visit import PropertyVisitSlot

    c = await _candidature_by_token(db, token)
    prop = await db.get(Property, c.property_id)
    now = _dt.now(UTC)
    slots = (
        (
            await db.execute(
                select(PropertyVisitSlot)
                .where(
                    PropertyVisitSlot.property_id == c.property_id,
                    PropertyVisitSlot.starts_at >= now,
                )
                .order_by(PropertyVisitSlot.starts_at)
            )
        )
        .scalars()
        .all()
    )
    out = []
    for s in slots:
        booked = (
            await db.execute(
                select(_func.count(Candidature.id)).where(Candidature.visit_slot_id == s.id)
            )
        ).scalar() or 0
        out.append(
            {
                "id": str(s.id),
                "starts_at": s.starts_at.isoformat(),
                "duration_min": s.duration_min,
                "remaining": max(0, s.capacity - int(booked)),
            }
        )
    from app.api.v1.candidatures import format_property_address

    return {
        "property_ref": getattr(prop, "ref_code", None) if prop else None,
        "property_address": format_property_address(prop),
        "candidate_name": c.full_name,
        "slots": out,
        "booked_slot_id": str(c.visit_slot_id) if c.visit_slot_id else None,
    }


@router.post("/candidature/{token}/visits/{slot_id}/book", summary="Réserver un créneau de visite")
async def public_candidature_book_visit(
    token: str, slot_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    from datetime import datetime as _dt

    from sqlalchemy import func as _func

    from app.models.candidature import Candidature
    from app.models.property import Property
    from app.models.visit import PropertyVisitSlot

    c = await _candidature_by_token(db, token)
    slot = await db.get(PropertyVisitSlot, slot_id)
    if not slot or slot.property_id != c.property_id:
        raise HTTPException(status_code=404, detail="Créneau introuvable")
    now = _dt.now(UTC)
    if slot.starts_at < now:
        raise HTTPException(status_code=400, detail="Ce créneau est déjà passé.")
    # Place restante (en dehors d'une éventuelle réservation déjà posée par ce candidat).
    booked = (
        await db.execute(
            select(_func.count(Candidature.id)).where(
                Candidature.visit_slot_id == slot.id,
                Candidature.id != c.id,
            )
        )
    ).scalar() or 0
    if int(booked) >= slot.capacity:
        raise HTTPException(status_code=409, detail="Ce créneau est complet.")

    c.visit_slot_id = slot.id
    await db.commit()

    # Notifier le gestionnaire (best-effort).
    try:
        prop = await db.get(Property, c.property_id)
        mgr = await db.get(User, prop.created_by) if (prop and prop.created_by) else None
        when = slot.starts_at.strftime("%d/%m/%Y à %H:%M")
        ref = getattr(prop, "ref_code", None) if prop else None
        if mgr and getattr(mgr, "email", None):
            from app.services.email_service import send_email

            await send_email(
                to=mgr.email,
                subject=f"Visite réservée : {c.full_name} ({ref or 'bien'})",
                html_body=(
                    f"<p><strong>{c.full_name}</strong> a réservé une visite "
                    f"({ref or 'bien'}) le <strong>{when}</strong>.</p>"
                    f"<p>Retrouvez le dossier dans « Candidatures ».</p>"
                ),
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Notif réservation visite échouée: %s", exc)

    return {"status": "booked", "starts_at": slot.starts_at.isoformat()}


@router.get("/listings/{token}", summary="Page d'annonce publique (sans authentification)")
async def public_listing(token: str, db: AsyncSession = Depends(get_db)):
    """Annonce publiée d'un bien, accessible par son jeton. 404 si introuvable ou
    non publiée (brouillon / programmée / dépubliée)."""
    from app.models.document import Document
    from app.models.property import Property
    from app.models.publishing import Listing
    from app.models.user import User
    from app.services.listing_service import build_photo_url

    listing = (
        await db.execute(select(Listing).where(Listing.public_token == token))
    ).scalar_one_or_none()
    if not listing or listing.status != "published":
        raise HTTPException(status_code=404, detail="Annonce introuvable")

    prop = await db.get(Property, listing.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Annonce introuvable")

    # Suivi de performance : chaque consultation publique compte une vue.
    from datetime import datetime as _dt

    listing.views_count = int(listing.views_count or 0) + 1
    listing.last_viewed_at = _dt.now(UTC)

    # Photos sélectionnées (ordre conservé) ; repli sur toutes les images du bien.
    photos: list[str] = []
    ids = [uuid.UUID(x) for x in (listing.photo_ids or []) if x]
    if ids:
        docs = (await db.execute(select(Document).where(Document.id.in_(ids)))).scalars().all()
        by_id = {str(d.id): d for d in docs}
        for x in listing.photo_ids or []:
            d = by_id.get(str(x))
            if d and (d.mime_type or "").lower().startswith("image/"):
                photos.append(build_photo_url(d.file_path))

    contact_name = None
    if listing.created_by:
        mgr = await db.get(User, listing.created_by)
        contact_name = getattr(mgr, "full_name", None) if mgr else None

    await db.commit()  # persiste le compteur de vues

    return {
        "title": listing.title or prop.name,
        "can_apply": True,
        "description": listing.description or prop.description,
        "price": float(listing.price) if listing.price is not None else None,
        "charges": float(listing.charges)
        if getattr(listing, "charges", None) is not None
        else None,
        "photos": photos,
        "published_at": listing.published_at,
        "contact_name": contact_name,
        "property": {
            "city": prop.city,
            "zip_code": prop.zip_code,
            "property_type": prop.property_type,
            "typology": prop.typology,
            "area_sqm": float(prop.area_sqm) if prop.area_sqm is not None else None,
            "floor": prop.floor,
            "bathrooms": prop.bathrooms,
            "energy_class": prop.energy_class,
            "heating_type": prop.heating_type,
            "furnished": prop.furnished,
            "features": {
                "elevator": prop.has_elevator,
                "balcony": prop.has_balcony,
                "terrace": prop.has_terrace,
                "garden": prop.has_garden,
                "parking": prop.has_parking,
                "cellar": prop.has_cellar,
                "fiber": prop.has_fiber,
                "air_conditioning": prop.has_air_conditioning,
            },
        },
    }


class PublicApplicationIn(BaseModel):
    """Dépôt de candidature depuis la page d'annonce publique."""

    full_name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    phone: str | None = Field(None, max_length=30)
    employment: str | None = Field(None, max_length=150)
    monthly_income: float | None = Field(None, ge=0, le=1_000_000)
    has_guarantor: bool = False
    message: str | None = Field(None, max_length=2000)


@router.post("/listings/{token}/apply", status_code=201, summary="Candidater à une annonce")
async def apply_to_listing(
    token: str, data: PublicApplicationIn, db: AsyncSession = Depends(get_db)
):
    """Crée un dossier de candidature pour l'annonce publiée (centralisé dans
    « Candidatures » côté gestionnaire)."""
    from app.api.v1.candidatures import default_docs
    from app.models.candidature import Candidature
    from app.models.publishing import Listing

    listing = (
        await db.execute(select(Listing).where(Listing.public_token == token))
    ).scalar_one_or_none()
    if not listing or listing.status != "published":
        raise HTTPException(status_code=404, detail="Annonce introuvable")

    # Anti-doublon simple : une candidature par e-mail et par bien.
    from app.models.candidature import Candidature as _C

    dup = (
        await db.execute(
            select(_C).where(
                _C.property_id == listing.property_id,
                _C.email == str(data.email).lower(),
            )
        )
    ).scalar_one_or_none()
    if dup:
        return {"status": "already_applied"}

    c = Candidature(
        property_id=listing.property_id,
        full_name=data.full_name.strip(),
        email=str(data.email).lower(),
        phone=(data.phone or "").strip() or None,
        employment=(data.employment or "").strip() or None,
        monthly_income=data.monthly_income,
        has_guarantor=data.has_guarantor,
        message=(data.message or "").strip() or None,
        docs=default_docs(),
        source="annonce",
    )
    db.add(c)
    await db.commit()

    # Notifier le gestionnaire (e-mail + SMS) qu'une nouvelle candidature est arrivée.
    try:
        mgr = await db.get(User, listing.created_by) if listing.created_by else None
        prop = await db.get(Property, listing.property_id)
        _pname = prop.name if prop else "votre bien"
        if mgr is not None:
            if getattr(mgr, "email", None):
                from app.services.email_service import send_email

                await send_email(
                    to=mgr.email,
                    subject=f"Nouvelle candidature : {_pname}",
                    html_body=(
                        f"<p>Une nouvelle candidature vient d'être déposée pour "
                        f"<strong>{_pname}</strong>.</p>"
                        f"<p>Candidat : <strong>{c.full_name}</strong> — {c.email}"
                        f"{(' — ' + c.phone) if c.phone else ''}</p>"
                        f"<p>Retrouvez le dossier dans « Candidatures ».</p>"
                    ),
                )
            if getattr(mgr, "phone", None):
                from app.services.sms_service import send_sms

                await send_sms(
                    mgr.phone,
                    f"Le Comptoir Immo : nouvelle candidature pour {_pname} ({c.full_name}).",
                )
            # Alerte « push » à l'équipe d'agents IA (Telegram) si liée.
            from app.services import agent_events

            await agent_events.notify_manager(
                db,
                listing.created_by,
                "candidature",
                f"<b>{c.full_name}</b> a candidaté pour <b>{_pname}</b>"
                f"{(' (' + c.email + ')') if c.email else ''}.",
                cta="Dossier à étudier dans « Candidatures ».",
            )
    except Exception as _exc:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).warning("Notif candidature échouée: %s", _exc)

    # Accusé de réception AUTOMATIQUE au candidat (à la charte du gestionnaire) :
    # chaque dossier reçoit une réponse immédiate et professionnelle. Best-effort.
    try:
        if (c.email or "").strip():
            from app.api.v1.candidatures import _apply_branding, _cand_overrides, _property_block
            from app.services.email_service import send_candidature_acknowledged

            _prop = await db.get(Property, listing.property_id)
            _block = await _property_block(db, _prop)
            _ov = await _cand_overrides(db, listing.created_by, "candidature_accuse", c, _block)
            if _ov["active"]:  # le gestionnaire peut couper l'accusé de réception auto
                _mgr = await db.get(User, listing.created_by) if listing.created_by else None
                _apply_branding(_mgr)
                await send_candidature_acknowledged(
                    to=c.email,
                    candidate_name=c.full_name,
                    property_html=_block["html"],
                    subject_override=_ov["subject"],
                    body_html_override=_ov["body_html"],
                    signature_override=_ov["signature"],
                )
    except Exception as _exc:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).warning("Accusé réception auto échoué: %s", _exc)

    return {"status": "received"}
