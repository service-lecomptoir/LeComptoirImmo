import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.core.permissions import Role
from app.api.v1._isolation import agency_lease_ids, assert_manager_scope, assert_lease_access
from app.models.user import User
from app.models.tenant import Tenant
from app.models.property import Property
from app.models.lease import Lease
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

    # ── Propriétaire / Gestionnaire-Propriétaire : baux de ses biens ────────────
    elif role in (Role.PROPRIETAIRE, Role.GESTIONNAIRE_PROPRIO):
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
            # Tous les biens du proprio : on boucle sur ses property_ids
            leases_all = []
            for pid in prop_ids:
                l2, _ = await LeaseService.list_all(
                    db, property_id=pid, is_active=is_active, skip=0, limit=200
                )
                leases_all.extend(l2)
            items = [LeaseService.to_list_item(l) for l in leases_all]
            return LeaseListResponse(items=items, total=len(items), skip=0, limit=limit)

    # ── Gestionnaire mandataire : uniquement les baux de SON agence ─────────────
    if role == Role.GESTIONNAIRE:
        allowed = await agency_lease_ids(db, current_user)
        all_leases, _ = await LeaseService.list_all(
            db, search=search, tenant_id=tenant_id,
            property_id=property_id, is_active=is_active, skip=0, limit=2000,
        )
        filtered = [l for l in all_leases if l.id in allowed]
        items = [LeaseService.to_list_item(l) for l in filtered[skip: skip + limit]]
        return LeaseListResponse(items=items, total=len(filtered), skip=skip, limit=limit)

    # ── Admin/Comptable ───────────────────────────────────────────────────────────
    leases, total = await LeaseService.list_all(
        db,
        search=search,
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
    await db.flush()
    # Auto-générer le paiement du mois de début de bail
    from datetime import date
    from app.services.payment_service import PaymentService
    from app.services import audit_service
    from app.core.exceptions import ConflictException as _Conflict
    today = date.today()
    start = lease.start_date if hasattr(lease.start_date, 'year') else date.fromisoformat(str(lease.start_date))
    gen_year = start.year if (start.year, start.month) >= (today.year, today.month) else today.year
    gen_month = start.month if (start.year, start.month) >= (today.year, today.month) else today.month
    try:
        await PaymentService.generate_for_lease(db, lease, gen_year, gen_month, current_user.id)
    except _Conflict:
        pass
    await audit_service.log(
        db, action=audit_service.LEASE_CREATE,
        user_id=current_user.id, user_email=current_user.email,
        entity_type="lease", entity_id=lease.id,
    )
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
    await assert_lease_access(db, current_user, lease)
    return lease


@router.put("/{lease_id}", response_model=LeaseResponse)
async def update_lease(
    lease_id: uuid.UUID,
    data: LeaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    existing = await LeaseService.get_by_id(db, lease_id, load_relations=True)
    await assert_lease_access(db, current_user, existing, write=True)
    lease = await LeaseService.update(db, lease_id, data)
    await db.commit()
    return await LeaseService.get_by_id(db, lease.id, load_relations=True)


@router.post("/{lease_id}/terminate", response_model=LeaseResponse)
async def terminate_lease(
    lease_id: uuid.UUID,
    data: LeaseTerminate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    from app.services import audit_service
    existing = await LeaseService.get_by_id(db, lease_id, load_relations=True)
    await assert_lease_access(db, current_user, existing, write=True)
    lease = await LeaseService.terminate(db, lease_id, data)
    await audit_service.log(
        db, action=audit_service.LEASE_TERMINATE,
        user_id=current_user.id, user_email=current_user.email,
        entity_type="lease", entity_id=lease.id,
    )
    await db.commit()
    return await LeaseService.get_by_id(db, lease.id, load_relations=True)


@router.get("/{lease_id}/pdf")
async def download_lease_pdf(
    lease_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lease = await LeaseService.get_by_id(db, lease_id, load_relations=True)
    await assert_lease_access(db, current_user, lease)

    # Bailleur = fiche propriétaire du bien ; mandataire = gestionnaire (rôle mandataire)
    owner = None
    prop = getattr(lease, "parent_property", None)
    if prop is not None and getattr(prop, "owner_id", None):
        from app.models.owner import Owner
        owner = (await db.execute(select(Owner).where(Owner.id == prop.owner_id))).scalar_one_or_none()
    is_mandataire = Role(current_user.role) == Role.GESTIONNAIRE

    pdf_bytes = generate_lease_pdf(lease, owner=owner, manager=current_user, is_mandataire=is_mandataire)
    from app.utils.filename import doc_filename
    _prop = lease.parent_property.name if getattr(lease, "parent_property", None) else None
    filename = doc_filename(
        "bail",
        tenant=lease.tenant.full_name if lease.tenant else None,
        property_name=_prop,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{lease_id}", status_code=204)
async def delete_lease(
    lease_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    existing = await LeaseService.get_by_id(db, lease_id, load_relations=True)
    await assert_lease_access(db, current_user, existing, write=True)
    await LeaseService.delete(db, lease_id)
    await db.commit()


# ── Suivi de la relation locataire (alimente le scoring) ─────────────────────
from datetime import datetime as _dt, date as _date
from pydantic import BaseModel as _BaseModel
from app.services.scoring_service import KIND_META


class _RelationEventIn(_BaseModel):
    kind: str
    note: Optional[str] = None
    event_date: Optional[str] = None  # ISO ; défaut = aujourd'hui


def _enrich_events(events) -> list:
    out = []
    for e in (events or []):
        meta = KIND_META.get(e.get("kind", ""), {})
        out.append({**e, "kind_label": meta.get("label", e.get("kind")),
                    "polarity": meta.get("polarity", "neutre")})
    out.sort(key=lambda x: x.get("date", ""), reverse=True)
    return out


async def _get_lease_scoped(db, lease_id, current_user) -> Lease:
    lease = await db.get(Lease, lease_id)
    if not lease:
        raise HTTPException(status_code=404, detail="Contrat introuvable")
    await assert_manager_scope(db, current_user, lease.created_by, "ce contrat")
    return lease


@router.get("/{lease_id}/relationship-events", summary="Événements de relation du contrat")
async def list_relationship_events(
    lease_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    lease = await _get_lease_scoped(db, lease_id, current_user)
    return _enrich_events(lease.relationship_events)


@router.post("/{lease_id}/relationship-events", status_code=201, summary="Ajouter un événement de relation")
async def add_relationship_event(
    lease_id: uuid.UUID,
    data: _RelationEventIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    if data.kind not in KIND_META:
        raise HTTPException(status_code=400, detail="Type d'événement inconnu")
    lease = await _get_lease_scoped(db, lease_id, current_user)
    ev = {
        "id": str(uuid.uuid4()),
        "date": (data.event_date or _date.today().isoformat()),
        "kind": data.kind,
        "note": (data.note or "").strip() or None,
        "author_name": getattr(current_user, "full_name", None),
        "created_at": _dt.utcnow().isoformat(),
    }
    # Réassignation (et non mutation en place) pour que SQLAlchemy détecte le changement JSONB.
    lease.relationship_events = list(lease.relationship_events or []) + [ev]
    await db.commit()
    return _enrich_events(lease.relationship_events)


@router.delete("/{lease_id}/relationship-events/{event_id}", status_code=200,
               summary="Supprimer un événement de relation")
async def delete_relationship_event(
    lease_id: uuid.UUID,
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    lease = await _get_lease_scoped(db, lease_id, current_user)
    lease.relationship_events = [e for e in (lease.relationship_events or []) if e.get("id") != event_id]
    await db.commit()
    return _enrich_events(lease.relationship_events)
