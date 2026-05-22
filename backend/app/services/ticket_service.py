import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ticket import Ticket, TicketMessage, TicketStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketMessageCreate
from app.core.exceptions import NotFoundException, BadRequestException


class TicketService:

    @staticmethod
    async def _get_tenant_for_user(db: AsyncSession, user_id: uuid.UUID) -> Tenant:
        result = await db.execute(select(Tenant).where(Tenant.user_id == user_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise BadRequestException("Aucun profil locataire associé à ce compte")
        return tenant

    @staticmethod
    async def create(db: AsyncSession, data: TicketCreate, author_user_id: uuid.UUID) -> Ticket:
        tenant = await TicketService._get_tenant_for_user(db, author_user_id)
        ticket = Ticket(
            title=data.title,
            description=data.description,
            category=data.category,
            priority=data.priority,
            tenant_id=tenant.id,
            status=TicketStatus.OPEN,
        )
        db.add(ticket)
        await db.flush()
        await db.refresh(ticket)

        # Premier message = description initiale
        msg = TicketMessage(
            ticket_id=ticket.id,
            author_id=author_user_id,
            content=data.description,
            is_internal=False,
        )
        db.add(msg)
        await db.flush()
        return ticket

    @staticmethod
    async def get(db: AsyncSession, ticket_id: uuid.UUID) -> Ticket:
        result = await db.execute(
            select(Ticket)
            .options(selectinload(Ticket.messages).selectinload(TicketMessage.author))
            .options(selectinload(Ticket.tenant))
            .options(selectinload(Ticket.assigned_to))
            .where(Ticket.id == ticket_id)
        )
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise NotFoundException("Ticket", str(ticket_id))
        return ticket

    @staticmethod
    async def list_all(
        db: AsyncSession,
        *,
        status: Optional[str] = None,
        tenant_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Ticket], int]:
        q = select(Ticket).options(selectinload(Ticket.tenant))
        if status:
            q = q.where(Ticket.status == status)
        if tenant_id:
            q = q.where(Ticket.tenant_id == tenant_id)
        q = q.order_by(Ticket.created_at.desc())

        count_q = select(func.count(Ticket.id))
        if status:
            count_q = count_q.where(Ticket.status == status)
        if tenant_id:
            count_q = count_q.where(Ticket.tenant_id == tenant_id)

        total = (await db.execute(count_q)).scalar_one()
        items = list((await db.execute(q.offset(offset).limit(limit))).scalars().all())
        return items, total

    @staticmethod
    async def list_for_locataire(db: AsyncSession, user_id: uuid.UUID) -> list[Ticket]:
        tenant = await TicketService._get_tenant_for_user(db, user_id)
        result = await db.execute(
            select(Ticket)
            .options(selectinload(Ticket.messages))
            .where(Ticket.tenant_id == tenant.id)
            .order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def update(db: AsyncSession, ticket_id: uuid.UUID, data: TicketUpdate) -> Ticket:
        ticket = await TicketService.get(db, ticket_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(ticket, field, value)
        if data.status in (TicketStatus.CLOSED, TicketStatus.RESOLVED) and not ticket.closed_at:
            ticket.closed_at = datetime.now(timezone.utc)
        await db.flush()
        return ticket

    @staticmethod
    async def add_message(
        db: AsyncSession,
        ticket_id: uuid.UUID,
        data: TicketMessageCreate,
        author_id: uuid.UUID,
    ) -> TicketMessage:
        result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
        if not result.scalar_one_or_none():
            raise NotFoundException("Ticket", str(ticket_id))
        msg = TicketMessage(
            ticket_id=ticket_id,
            author_id=author_id,
            content=data.content,
            is_internal=data.is_internal,
        )
        db.add(msg)
        await db.flush()
        await db.refresh(msg, ["author"])
        return msg

    @staticmethod
    async def count_open(db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.OPEN)
        )
        return result.scalar_one()
