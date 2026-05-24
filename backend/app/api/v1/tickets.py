import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.api.v1._isolation import gp_tenant_ids
from app.models.user import User
from app.models.ticket import Ticket
from app.models.lease import Lease
from app.models.property import Property
from app.core.permissions import Role
from app.schemas.ticket import (
    TicketCreate, TicketUpdate, TicketResponse, TicketListItem,
    TicketMessageCreate, TicketMessageResponse,
)
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["Tickets"])


def _enrich_ticket(ticket, include_messages: bool = False) -> dict:
    data = {
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "category": ticket.category,
        "status": ticket.status,
        "priority": ticket.priority,
        "tenant_id": ticket.tenant_id,
        "tenant_name": ticket.tenant.full_name if ticket.tenant else None,
        "lease_id": ticket.lease_id,
        "unit_id": ticket.unit_id,
        "assigned_to_id": ticket.assigned_to_id,
        "assigned_to_name": ticket.assigned_to.full_name if ticket.assigned_to else None,
        "closed_at": ticket.closed_at,
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


@router.post("", status_code=201, summary="Créer un ticket")
async def create_ticket(
    data: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await TicketService.create(db, data, current_user.id)
    await db.commit()
    await db.refresh(ticket)
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

    # Gestionnaire mandataire : exclure les tickets des locataires GP
    if Role(current_user.role) == Role.GESTIONNAIRE:
        excluded = await gp_tenant_ids(db)
        all_items, _ = await TicketService.list_all(db, status=status, limit=5000, offset=0)
        filtered = [t for t in all_items if t.tenant_id not in excluded]
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
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    open_count = await TicketService.count_open(db)
    return {"open": open_count}


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
    return _enrich_ticket(ticket, include_messages=True)


@router.patch("/{ticket_id}", summary="Mettre à jour un ticket")
async def update_ticket(
    ticket_id: uuid.UUID,
    data: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
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
