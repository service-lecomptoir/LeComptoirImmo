import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.ticket import TicketCategory, TicketPriority, TicketStatus


class TicketMessageBase(BaseModel):
    content: str
    is_internal: bool = False


class TicketMessageCreate(TicketMessageBase):
    pass


class TicketMessageResponse(TicketMessageBase):
    id: uuid.UUID
    ticket_id: uuid.UUID
    author_id: uuid.UUID
    author_name: str | None = None
    author_role: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketCreate(BaseModel):
    title: str
    description: str
    category: TicketCategory = TicketCategory.AUTRE
    priority: TicketPriority = TicketPriority.MEDIUM
    # Sujet déclaré (voisinage / logement / autre) — route vers l'agent IA notifié.
    topic: str | None = None


class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    assigned_to_id: uuid.UUID | None = None


class TicketResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    category: str
    status: str
    priority: str
    tenant_id: uuid.UUID
    tenant_name: str | None = None
    lease_id: uuid.UUID | None = None
    assigned_to_id: uuid.UUID | None = None
    assigned_to_name: str | None = None
    closed_at: datetime | None = None
    messages: list[TicketMessageResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketListItem(BaseModel):
    id: uuid.UUID
    title: str
    category: str
    status: str
    priority: str
    tenant_id: uuid.UUID
    tenant_name: str | None = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
