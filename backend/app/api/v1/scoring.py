import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_role
from app.api.v1._isolation import agency_member_ids, assert_manager_scope
from app.core.permissions import Role
from app.database import get_db
from app.models.lease import Lease
from app.models.payment import Payment
from app.models.tenant import Tenant
from app.models.user import User
from app.services.scoring_service import KIND_META, compute, event_kinds

router = APIRouter(prefix="/scoring", tags=["Scoring locataires"])


async def _tenant_scope_ids(db: AsyncSession, current_user: User):
    """IDs des locataires visibles selon le rôle, ou None pour « tous » (admin)."""
    role = Role(current_user.role)
    if role == Role.GESTIONNAIRE_PROPRIO:
        rows = await db.execute(select(Tenant.id).where(Tenant.created_by == current_user.id))
        return list(rows.scalars().all())
    if role == Role.GESTIONNAIRE:
        members = await agency_member_ids(db, current_user)
        if not members:
            return []
        rows = await db.execute(select(Tenant.id).where(Tenant.created_by.in_(members)))
        return list(rows.scalars().all())
    return None  # admin


@router.get("/event-kinds", summary="Catalogue des types d'événements de relation")
async def get_event_kinds(_: User = Depends(require_role(Role.GESTIONNAIRE_PROPRIO))):
    return event_kinds()


@router.get("", summary="Scoring de tous les locataires (trié par risque)")
async def list_scoring(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE_PROPRIO)),
):
    ids = await _tenant_scope_ids(db, current_user)
    tq = select(Tenant)
    if ids is not None:
        if not ids:
            return {"total": 0, "items": []}
        tq = tq.where(Tenant.id.in_(ids))
    tenants = list((await db.execute(tq)).scalars().all())
    tid_list = [t.id for t in tenants]
    if not tid_list:
        return {"total": 0, "items": []}

    # Bail actif (principal) par locataire
    leases = list(
        (
            await db.execute(
                select(Lease)
                .options(selectinload(Lease.parent_property))
                .where(Lease.tenant_id.in_(tid_list), Lease.is_active.is_(True))
            )
        )
        .scalars()
        .all()
    )
    lease_by_tenant: dict = {}
    for le in leases:
        lease_by_tenant.setdefault(le.tenant_id, le)

    # Paiements groupés par locataire
    payments = list(
        (await db.execute(select(Payment).where(Payment.tenant_id.in_(tid_list)))).scalars().all()
    )
    pay_by_tenant: dict = {}
    for p in payments:
        pay_by_tenant.setdefault(p.tenant_id, []).append(p)

    # Propriétaire (bailleur) par bien → permet le regroupement côté mandataire
    from app.models.owner import Owner

    owner_ids = {
        le.parent_property.owner_id
        for le in leases
        if getattr(le, "parent_property", None) and le.parent_property.owner_id
    }
    owner_names: dict = {}
    if owner_ids:
        for o in (await db.execute(select(Owner).where(Owner.id.in_(owner_ids)))).scalars().all():
            owner_names[o.id] = o.full_name

    def _owner_of(lease):
        prop = getattr(lease, "parent_property", None) if lease else None
        if not prop:
            return None, "Sans propriétaire"
        name = owner_names.get(prop.owner_id) or prop.owner_name or "Sans propriétaire"
        return (str(prop.owner_id) if prop.owner_id else None), name

    items = []
    for t in tenants:
        lease = lease_by_tenant.get(t.id)
        res = compute(t, lease, pay_by_tenant.get(t.id, []))
        prop = getattr(lease, "parent_property", None) if lease else None
        owner_id, owner_name = _owner_of(lease)
        items.append(
            {
                "tenant_id": str(t.id),
                "tenant_name": t.full_name,
                "lease_id": str(lease.id) if lease else None,
                "property_label": (prop.name if prop else None),
                "owner_id": owner_id,
                "owner_name": owner_name,
                "has_active_lease": lease is not None,
                "score": res["score"],
                "grade": res["grade"],
                "strategy": res["strategy"],
                "income": res["stats"]["income"],
                "effort_rate": res["stats"]["effort_rate"],
                "on_time_rate": res["stats"]["on_time_rate"],
                "overdue_count": res["stats"]["overdue_count"],
                "outstanding": res["stats"]["outstanding"],
            }
        )
    # Pire score en premier (priorité d'action)
    items.sort(key=lambda x: x["score"])
    return {"total": len(items), "items": items}


@router.get("/{tenant_id}", summary="Détail du scoring d'un locataire")
async def get_scoring_detail(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE_PROPRIO)),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Locataire introuvable")
    await assert_manager_scope(db, current_user, tenant.created_by, "ce locataire")

    lease = (
        (
            await db.execute(
                select(Lease)
                .options(selectinload(Lease.parent_property))
                .where(Lease.tenant_id == tenant_id, Lease.is_active.is_(True))
                .order_by(Lease.start_date.desc())
            )
        )
        .scalars()
        .first()
    )
    payments = list(
        (await db.execute(select(Payment).where(Payment.tenant_id == tenant_id))).scalars().all()
    )

    res = compute(tenant, lease, payments)
    prop = getattr(lease, "parent_property", None) if lease else None

    # Événements de relation enrichis (libellé + polarité), plus récents d'abord
    events = []
    for e in getattr(lease, "relationship_events", None) or [] if lease else []:
        meta = KIND_META.get(e.get("kind", ""), {})
        events.append(
            {
                **e,
                "kind_label": meta.get("label", e.get("kind")),
                "polarity": meta.get("polarity", "neutre"),
            }
        )
    events.sort(key=lambda x: x.get("date", ""), reverse=True)

    return {
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.full_name,
        "tenant_phone": getattr(tenant, "phone", None),
        "tenant_email": getattr(tenant, "email", None),
        "income_source": getattr(tenant, "income_source", None),
        "lease_id": str(lease.id) if lease else None,
        "property_label": (prop.name if prop else None),
        "has_active_lease": lease is not None,
        **res,
        "relationship_events": events,
    }


@router.get("/{tenant_id}/analysis", summary="Analyse IA d'aide à la décision (scoring)")
async def scoring_ai_analysis(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE_PROPRIO)),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Locataire introuvable")
    await assert_manager_scope(db, current_user, tenant.created_by, "ce locataire")

    lease = (
        (
            await db.execute(
                select(Lease)
                .options(selectinload(Lease.parent_property))
                .where(Lease.tenant_id == tenant_id, Lease.is_active.is_(True))
                .order_by(Lease.start_date.desc())
            )
        )
        .scalars()
        .first()
    )
    payments = list(
        (await db.execute(select(Payment).where(Payment.tenant_id == tenant_id))).scalars().all()
    )
    res = compute(tenant, lease, payments)

    from app.services import llm_service

    if not llm_service.enabled():
        return {"analysis": None, "enabled": False}

    prop = getattr(lease, "parent_property", None) if lease else None
    facts = [
        f"Locataire : {tenant.full_name}",
        f"Note de qualité de payeur : {res['grade']} ({res['score']}/100)",
        f"Bien : {prop.name if prop else 'non renseigné'}",
        f"Source de revenus : {getattr(tenant, 'income_source', None) or 'non renseignée'}",
    ]
    for f in res.get("factors", []):
        facts.append(f"{f['label']} : {f['score']}/100 (poids {f['weight']} %) : {f['detail']}")
    evs = (getattr(lease, "relationship_events", None) or []) if lease else []
    if evs:
        labels = [
            KIND_META.get(e.get("kind", ""), {}).get("label", e.get("kind")) for e in evs[-8:]
        ]
        facts.append("Événements de relation récents : " + ", ".join(str(x) for x in labels))

    system = (
        "Tu es un analyste expert en gestion locative en France, spécialiste de l'évaluation du "
        "risque d'impayé. À partir des DONNÉES déjà calculées d'un locataire, tu aides le gestionnaire "
        "à décider. Sois factuel, nuancé et concret ; ne juge pas la personne, base-toi uniquement sur "
        "les données, n'invente rien. Réponds en français, en 4 à 6 lignes maximum, sous la forme :\n"
        "• Forces : …\n• Points de vigilance : …\n• Recommandation : une action concrète et proportionnée.\n"
        "Reste sobre et orienté décision."
    )
    text = await llm_service.chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": "DONNÉES DU LOCATAIRE :\n- " + "\n- ".join(facts)},
        ],
        temperature=0.4,
        max_tokens=420,
    )
    return {"analysis": text, "enabled": True}
