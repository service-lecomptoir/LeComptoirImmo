import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.api.v1._isolation import agency_tenant_ids, assert_ticket_access
from app.models.user import User
from app.models.ticket import Ticket
from app.models.lease import Lease
from app.models.property import Property
from app.core.permissions import Role
from app.schemas.ticket import (
    TicketCreate, TicketUpdate, TicketMessageCreate,
)
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["Tickets"])


def _enrich_ticket(ticket, include_messages: bool = False) -> dict:
    data = {
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "category": ticket.category,
        "topic": getattr(ticket, "topic", None),
        "status": ticket.status,
        "priority": ticket.priority,
        "tenant_id": ticket.tenant_id,
        "tenant_name": ticket.tenant.full_name if ticket.tenant else None,
        "lease_id": ticket.lease_id,
        "assigned_to_id": ticket.assigned_to_id,
        "assigned_to_name": ticket.assigned_to.full_name if ticket.assigned_to else None,
        "closed_at": ticket.closed_at,
        "photo_url": ("/" + ticket.photo_path.replace("\\", "/").lstrip("/")) if getattr(ticket, "photo_path", None) else None,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
    }
    if include_messages:
        data["messages"] = [
            {
                "id": m.id,
                "ticket_id": m.ticket_id,
                "author_id": m.author_id,
                "author_name": m.author.full_name if m.author else None,
                "author_role": m.author.role if m.author else None,
                "content": m.content,
                "is_internal": m.is_internal,
                "created_at": m.created_at,
            }
            for m in ticket.messages
        ]
    return data


# ── Routes Locataire ─────────────────────────────────────────────────────────

@router.get("/mine", summary="Mes tickets (locataire)")
async def my_tickets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tickets = await TicketService.list_for_locataire(db, current_user.id)
    return [_enrich_ticket(t) for t in tickets]


@router.post("/{ticket_id}/photo", summary="Joindre une photo à une démarche")
async def attach_ticket_photo(
    ticket_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.utils.file_handler import save_file
    ticket = await TicketService.get(db, ticket_id)
    await assert_ticket_access(db, current_user, ticket)
    path, _size = await save_file(file, "ticket", str(ticket.id))
    ticket.photo_path = path
    await db.commit()
    await db.refresh(ticket)
    return {"photo_url": ("/" + path.replace("\\", "/").lstrip("/"))}


@router.post("", status_code=201, summary="Créer un ticket")
async def create_ticket(
    data: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await TicketService.create(db, data, current_user.id)
    await db.commit()
    await db.refresh(ticket)
    # Push « agent IA » : prévient spontanément le gestionnaire du locataire,
    # via l'agent compétent selon le sujet déclaré (best-effort, non bloquant).
    try:
        from app.models.tenant import Tenant
        from app.services import agent_events
        tenant = await db.get(Tenant, ticket.tenant_id)
        manager_id = getattr(tenant, "created_by", None) if tenant else None
        tenant_name = (getattr(tenant, "full_name", None) if tenant else None) or "Un locataire"
        detail = (ticket.description or "").strip()
        if len(detail) > 240:
            detail = detail[:240].rstrip() + "…"
        body = f"{tenant_name} signale : « {ticket.title} »."
        if detail and detail != ticket.title:
            body += f"\n{detail}"
        await agent_events.notify_manager(
            db, manager_id, ticket.topic or "autre", body,
            cta="Ouvrez la démarche dans l'application pour répondre.",
        )
    except Exception:  # noqa: BLE001 : la notification ne doit jamais bloquer la création
        pass
    return {"id": ticket.id, "status": ticket.status}


# ── Routes Gestionnaire / Admin ───────────────────────────────────────────────

@router.get("", summary="Liste tous les tickets")
async def list_tickets(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    if Role(current_user.role) == Role.GESTIONNAIRE_PROPRIO:
        prop_ids = [p.id for p in (await db.execute(
            select(Property).where(Property.owner_user_id == current_user.id)
        )).scalars().all()]
        if not prop_ids:
            return {"total": 0, "items": []}
        tenant_ids = [row[0] for row in (await db.execute(
            select(Lease.tenant_id).where(Lease.property_id.in_(prop_ids)).distinct()
        )).all()]
        if not tenant_ids:
            return {"total": 0, "items": []}
        q = (
            select(Ticket)
            .options(selectinload(Ticket.tenant), selectinload(Ticket.assigned_to))
            .where(Ticket.tenant_id.in_(tenant_ids))
        )
        if status:
            q = q.where(Ticket.status == status)
        q = q.order_by(Ticket.created_at.desc()).limit(limit).offset(offset)
        tickets = list((await db.execute(q)).scalars().all())
        return {"total": len(tickets), "items": [_enrich_ticket(t) for t in tickets]}

    # Gestionnaire mandataire : uniquement les tickets des locataires de SON agence
    if Role(current_user.role) == Role.GESTIONNAIRE:
        allowed = await agency_tenant_ids(db, current_user)
        all_items, _ = await TicketService.list_all(db, status=status, limit=5000, offset=0)
        filtered = [t for t in all_items if t.tenant_id in allowed]
        page = filtered[offset: offset + limit]
        return {"total": len(filtered), "items": [_enrich_ticket(t) for t in page]}

    items, total = await TicketService.list_all(db, status=status, limit=limit, offset=offset)
    return {
        "total": total,
        "items": [_enrich_ticket(t) for t in items],
    }


@router.get("/stats", summary="Statistiques tickets")
async def ticket_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    from sqlalchemy import func
    from app.models.tenant import Tenant
    role = Role(current_user.role)
    if role == Role.ADMIN:
        return {"open": await TicketService.count_open(db)}
    q = select(func.count(Ticket.id)).where(Ticket.status == "open")
    if role == Role.GESTIONNAIRE_PROPRIO:
        tenant_ids = list((await db.execute(
            select(Tenant.id).where(Tenant.created_by == current_user.id)
        )).scalars().all())
        if not tenant_ids:
            return {"open": 0}
        q = q.where(Ticket.tenant_id.in_(tenant_ids))
    else:  # mandataire : uniquement les locataires de SON agence
        allowed = await agency_tenant_ids(db, current_user)
        if not allowed:
            return {"open": 0}
        q = q.where(Ticket.tenant_id.in_(allowed))
    return {"open": (await db.execute(q)).scalar_one()}


@router.get("/proprietaire", summary="Tickets des biens du propriétaire")
async def proprietaire_tickets(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les tickets des locataires pour les biens appartenant au propriétaire connecté."""
    # Trouver les biens du propriétaire
    props_res = await db.execute(
        select(Property).where(Property.owner_user_id == current_user.id)
    )
    prop_ids = [p.id for p in props_res.scalars().all()]

    if not prop_ids:
        return {"total": 0, "items": []}

    # Trouver les tenant_ids pour ces biens via les baux
    leases_res = await db.execute(
        select(Lease.tenant_id).where(
            Lease.property_id.in_(prop_ids),
        ).distinct()
    )
    tenant_ids = [row[0] for row in leases_res.all()]

    if not tenant_ids:
        return {"total": 0, "items": []}

    # Lister les tickets de ces locataires
    q = (
        select(Ticket)
        .options(selectinload(Ticket.tenant))
        .options(selectinload(Ticket.assigned_to))
        .where(Ticket.tenant_id.in_(tenant_ids))
    )
    if status:
        q = q.where(Ticket.status == status)
    q = q.order_by(Ticket.created_at.desc())

    result = await db.execute(q)
    tickets = list(result.scalars().all())

    return {
        "total": len(tickets),
        "items": [_enrich_ticket(t) for t in tickets],
    }


@router.get("/{ticket_id}", summary="Détail d'un ticket")
async def get_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await TicketService.get(db, ticket_id)
    await assert_ticket_access(db, current_user, ticket)
    return _enrich_ticket(ticket, include_messages=True)


@router.patch("/{ticket_id}", summary="Mettre à jour un ticket")
async def update_ticket(
    ticket_id: uuid.UUID,
    data: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    existing = await TicketService.get(db, ticket_id)
    await assert_ticket_access(db, current_user, existing, manager_only=True)
    ticket = await TicketService.update(db, ticket_id, data)
    await db.commit()
    ticket = await TicketService.get(db, ticket_id)
    return _enrich_ticket(ticket)


@router.post("/{ticket_id}/messages", status_code=201, summary="Ajouter un message")
async def add_message(
    ticket_id: uuid.UUID,
    data: TicketMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _t = await TicketService.get(db, ticket_id)
    await assert_ticket_access(db, current_user, _t)
    msg = await TicketService.add_message(db, ticket_id, data, current_user.id)
    await db.commit()
    return {
        "id": msg.id,
        "ticket_id": msg.ticket_id,
        "author_id": msg.author_id,
        "author_name": msg.author.full_name if msg.author else None,
        "author_role": msg.author.role if msg.author else None,
        "content": msg.content,
        "is_internal": msg.is_internal,
        "created_at": msg.created_at,
    }


# ── Workflow de démarche : clôture proposée / validée / refusée, relance ─────
from pydantic import BaseModel
from app.models.tenant import Tenant


class _CommentIn(BaseModel):
    comment: Optional[str] = None


class _DraftIn(BaseModel):
    topic: Optional[str] = None
    hint: Optional[str] = None


@router.post("/draft", summary="Rédiger une démarche avec l'IA (aide locataire)")
async def draft_ticket(
    data: _DraftIn,
    current_user: User = Depends(get_current_user),
):
    """Propose un Sujet + une Description selon le type de signalement choisi
    (et un éventuel mot du locataire). Non enregistré : à éditer puis envoyer."""
    from app.services.ticket_ai import generate_ticket_draft
    return await generate_ticket_draft(data.topic, data.hint)


class _EditMsgIn(BaseModel):
    content: str


async def _assert_requester(db: AsyncSession, ticket, user: User) -> None:
    """Le locataire demandeur (ou un admin) uniquement."""
    if Role(user.role) == Role.ADMIN:
        return
    tenant = await db.get(Tenant, ticket.tenant_id)
    if not tenant or str(getattr(tenant, "user_id", None)) != str(user.id):
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("Cette démarche ne vous appartient pas.")


@router.post("/{ticket_id}/propose-closure", summary="Proposer la clôture (gestionnaire)")
async def propose_closure(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    _t = await TicketService.get(db, ticket_id)
    await assert_ticket_access(db, current_user, _t, manager_only=True)
    await TicketService.propose_closure(db, ticket_id, current_user.id)
    await db.commit()
    return _enrich_ticket(await TicketService.get(db, ticket_id), include_messages=True)


@router.post("/{ticket_id}/validate-closure", summary="Valider la clôture (demandeur)")
async def validate_closure(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await TicketService.get(db, ticket_id)
    await _assert_requester(db, ticket, current_user)
    await TicketService.validate_closure(db, ticket_id, current_user.id)
    await db.commit()
    return _enrich_ticket(await TicketService.get(db, ticket_id), include_messages=True)


@router.post("/{ticket_id}/refuse-closure", summary="Refuser la clôture (demandeur)")
async def refuse_closure(
    ticket_id: uuid.UUID,
    data: _CommentIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await TicketService.get(db, ticket_id)
    await _assert_requester(db, ticket, current_user)
    await TicketService.refuse_closure(db, ticket_id, current_user.id, data.comment)
    await db.commit()
    return _enrich_ticket(await TicketService.get(db, ticket_id), include_messages=True)


@router.post("/{ticket_id}/relancer", summary="Relancer une démarche (demandeur)")
async def relancer(
    ticket_id: uuid.UUID,
    data: _CommentIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await TicketService.get(db, ticket_id)
    await _assert_requester(db, ticket, current_user)
    await TicketService.relancer(db, ticket_id, current_user.id, data.comment)
    await db.commit()
    return _enrich_ticket(await TicketService.get(db, ticket_id), include_messages=True)


@router.patch("/{ticket_id}/messages/{message_id}", summary="Modifier son commentaire")
async def edit_message(
    ticket_id: uuid.UUID,
    message_id: uuid.UUID,
    data: _EditMsgIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    msg = await TicketService.edit_message(db, ticket_id, message_id, current_user.id, data.content)
    await db.commit()
    return {
        "id": msg.id, "ticket_id": msg.ticket_id, "author_id": msg.author_id,
        "author_name": msg.author.full_name if msg.author else None,
        "author_role": msg.author.role if msg.author else None,
        "content": msg.content, "is_internal": msg.is_internal, "created_at": msg.created_at,
    }
